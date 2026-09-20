"""
Wholevegan.co - Sales Analytics Dashboard

Queries the `analytics` schema built by dbt (dim_customers, dim_products,
fct_orders, fct_order_items) — never the raw public schema tables directly.

Setup:
    Copy your .env (with DATABASE_URL=...) into this folder, or point
    load_dotenv() at the one in ../scripts/.env (see below).

Run:
    streamlit run app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

# On Streamlit Cloud, the connection string comes from st.secrets (set in the
# app's "Secrets" settings). Locally, it falls back to a .env file.
if "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]
else:
    load_dotenv()
    load_dotenv(dotenv_path="../scripts/.env")
    DATABASE_URL = os.environ["DATABASE_URL"]

st.set_page_config(page_title="Wholevegan.co Analytics", layout="wide")


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL)


@st.cache_data(ttl=600)
def run_query(sql):
    return pd.read_sql(sql, get_engine())


st.title("🥦 Wholevegan.co — Sales Analytics")
st.caption("Data modeled with dbt · staging → marts · tested with dbt tests")

# ---------- KPI row ----------
kpis = run_query("""
    select
        round(sum(net_revenue) filter (where status = 'completed'), 2) as total_revenue,
        count(*) filter (where status = 'completed') as completed_orders,
        round(100.0 * count(*) filter (where status = 'abandoned_cart') / count(*), 1) as abandonment_pct
    from analytics.fct_orders
""").iloc[0]

repeat_rate = run_query("""
    select round(100.0 * sum(case when order_count > 1 then 1 else 0 end) / count(*), 1) as repeat_pct
    from (
        select customer_id, count(*) as order_count
        from analytics.fct_orders
        where status = 'completed'
        group by customer_id
    ) t
""").iloc[0]["repeat_pct"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}")
c2.metric("Completed Orders", f"{kpis['completed_orders']:,}")
c3.metric("Cart Abandonment", f"{kpis['abandonment_pct']}%")
c4.metric("Repeat Customer Rate", f"{repeat_rate}%")

st.divider()

# ---------- Revenue trend ----------
st.subheader("Monthly Revenue")
revenue = run_query("""
    select to_char(date_trunc('month', order_date), 'YYYY-MM') as month,
           round(sum(net_revenue), 2) as revenue
    from analytics.fct_orders
    where status = 'completed'
    group by 1 order by 1
""")
st.plotly_chart(px.line(revenue, x="month", y="revenue", markers=True), use_container_width=True)

col_a, col_b = st.columns(2)

# ---------- Top products ----------
with col_a:
    st.subheader("Top Products by Revenue")
    top_products = run_query("""
        select product_name, round(sum(line_total), 2) as revenue
        from analytics.fct_order_items
        where status = 'completed'
        group by product_name
        order by revenue desc
        limit 10
    """)
    st.plotly_chart(px.bar(top_products, x="revenue", y="product_name", orientation="h"),
                     use_container_width=True)

# ---------- Cart abandonment by channel ----------
with col_b:
    st.subheader("Cart Abandonment by Channel")
    abandon_by_channel = run_query("""
        select channel,
               round(100.0 * count(*) filter (where status = 'abandoned_cart') / count(*), 1) as abandonment_pct
        from analytics.fct_orders
        group by channel
        order by abandonment_pct desc
    """)
    st.plotly_chart(px.bar(abandon_by_channel, x="channel", y="abandonment_pct"),
                     use_container_width=True)

st.divider()

# ---------- Cohort retention ----------
st.subheader("Cohort Retention (% of cohort active in each month since first order)")
cohort = run_query("""
    with first_order as (
        select customer_id, date_trunc('month', min(order_date)) as cohort_month
        from analytics.fct_orders
        where status = 'completed'
        group by customer_id
    ),
    activity as (
        select f.customer_id, fo.cohort_month,
               date_trunc('month', f.order_date) as order_month
        from analytics.fct_orders f
        join first_order fo using (customer_id)
        where f.status = 'completed'
    ),
    sized as (
        select cohort_month, count(distinct customer_id) as cohort_size
        from first_order group by cohort_month
    )
    select
        to_char(a.cohort_month, 'YYYY-MM') as cohort_month,
        extract(month from age(a.order_month, a.cohort_month))::int as months_since_first,
        round(100.0 * count(distinct a.customer_id) / s.cohort_size, 1) as pct_active
    from activity a
    join sized s using (cohort_month)
    group by 1, 2, s.cohort_size
    order by 1, 2
""")
if not cohort.empty:
    pivot = cohort.pivot(index="cohort_month", columns="months_since_first", values="pct_active")
    st.plotly_chart(px.imshow(pivot, text_auto=True, color_continuous_scale="Greens",
                               labels=dict(color="% active")), use_container_width=True)

st.divider()

# ---------- RFM segmentation ----------
st.subheader("Customer Segments (declared) vs. Revenue Contribution")
segment_rev = run_query("""
    select c.segment,
           count(distinct c.customer_id) as customers,
           round(sum(f.net_revenue), 2) as revenue
    from analytics.dim_customers c
    join analytics.fct_orders f on c.customer_id = f.customer_id
    where f.status = 'completed'
    group by c.segment
    order by revenue desc
""")
st.plotly_chart(px.pie(segment_rev, names="segment", values="revenue",
                        title="Revenue Share by Customer Segment"), use_container_width=True)
st.dataframe(segment_rev, use_container_width=True, hide_index=True)