"""
Synthetic order-data generator for wholevegan.co analytics layer.

Unlike a purely uniform-random generator, this script builds in the kind of
structure a real BI/analytics interviewer expects to see in the data:

  - Customer SEGMENTS with different buying behavior (loyal / occasional / one-time)
  - SEASONALITY (Nov/Dec spike, summer lull) so revenue trends actually look real
  - ACQUISITION CHANNELS on both customers and orders (for CAC/ROI analysis)
  - DISCOUNTS and a separate RETURNS table (for margin / return-rate analysis)
  - A configurable random seed for reproducibility

Run:
    pip install pandas faker numpy
    python generate_data.py
"""

import random
from datetime import timedelta

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

N_PRODUCTS = 40
N_CUSTOMERS = 300
HISTORY_MONTHS = 12
END_DATE = pd.Timestamp.today().normalize()
START_DATE = END_DATE - pd.DateOffset(months=HISTORY_MONTHS)

CATEGORIES = ["Snacks", "Dairy Alternatives", "Ready Meals", "Bakery", "Beverages"]
CHANNELS = ["organic", "instagram_ads", "google_ads", "email", "referral"]

# Segment definition: weight = share of customer base,
# orders_per_active_month = (min, max) orders while the customer is active,
# active_months = (min, max) how many months (out of HISTORY_MONTHS) they order at all,
# discount_rate = how often an order in this segment carries a discount code.
SEGMENTS = {
    "loyal":      {"weight": 0.15, "orders_per_active_month": (2, 5), "active_months": (6, 12), "discount_rate": 0.10},
    "occasional": {"weight": 0.55, "orders_per_active_month": (0, 1), "active_months": (1, 6),  "discount_rate": 0.20},
    "one_time":   {"weight": 0.30, "orders_per_active_month": (0, 1), "active_months": (1, 1),  "discount_rate": 0.35},
}

# Relative order-volume multiplier by calendar month (1=Jan ... 12=Dec).
# Nov/Dec holiday spike, July/Aug summer lull, everything else ~baseline.
SEASONALITY = {1: 0.9, 2: 0.9, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.95,
               7: 0.8, 8: 0.8, 9: 1.0, 10: 1.1, 11: 1.6, 12: 1.8}


def month_range(start, end):
    months = pd.date_range(start, end, freq="MS")
    return list(months)


def make_products():
    rows = []
    for i in range(N_PRODUCTS):
        rows.append({
            "product_id": i + 1,
            "product_name": f"{fake.word().capitalize()} {random.choice(['Bites', 'Milk', 'Bowl', 'Loaf', 'Juice'])}",
            "category": random.choice(CATEGORIES),
            "price": round(random.uniform(3, 25), 2),
        })
    return pd.DataFrame(rows)


def make_customers():
    rows = []
    segment_names = list(SEGMENTS.keys())
    segment_weights = [SEGMENTS[s]["weight"] for s in segment_names]
    for i in range(N_CUSTOMERS):
        segment = random.choices(segment_names, weights=segment_weights)[0]
        signup_date = fake.date_between(start_date=START_DATE, end_date=END_DATE)
        rows.append({
            "customer_id": i + 1,
            "name": fake.name(),
            "region": fake.state(),
            "signup_date": signup_date,
            "segment": segment,
            "acquisition_channel": random.choice(CHANNELS),
        })
    return pd.DataFrame(rows)


def make_orders_and_items(customers_df, products_df):
    orders, order_items = [], []
    order_id = 1
    all_months = month_range(START_DATE, END_DATE)

    for _, cust in customers_df.iterrows():
        seg = SEGMENTS[cust["segment"]]
        signup = pd.Timestamp(cust["signup_date"])

        # Which months after signup is this customer "active" in?
        eligible_months = [m for m in all_months if m >= signup]
        if not eligible_months:
            continue
        n_active = min(len(eligible_months), random.randint(*seg["active_months"]))
        active_months = sorted(random.sample(eligible_months, n_active))

        for month in active_months:
            seasonal_mult = SEASONALITY[month.month]
            base_n = random.randint(*seg["orders_per_active_month"])
            n_orders_this_month = max(0, round(base_n * seasonal_mult))

            for _ in range(n_orders_this_month):
                day_offset = random.randint(0, 27)
                order_date = month + timedelta(days=day_offset,
                                                 hours=random.randint(8, 21))
                if order_date > END_DATE:
                    continue

                is_discounted = random.random() < seg["discount_rate"]
                status = random.choices(
                    ["completed", "abandoned_cart"], weights=[0.85, 0.15]
                )[0]

                orders.append({
                    "order_id": order_id,
                    "customer_id": cust["customer_id"],
                    "order_date": order_date,
                    "channel": random.choice(CHANNELS),
                    "status": status,
                    "discount_pct": random.choice([10, 15, 20]) if is_discounted else 0,
                })

                for _ in range(random.randint(1, 4)):
                    product = products_df.sample(1).iloc[0]
                    order_items.append({
                        "order_id": order_id,
                        "product_id": int(product["product_id"]),
                        "quantity": random.randint(1, 3),
                        "unit_price": float(product["price"]),
                    })
                order_id += 1

    return pd.DataFrame(orders), pd.DataFrame(order_items)


def make_returns(orders_df, order_items_df, rate=0.06):
    """A small fraction of completed order lines get returned."""
    completed = orders_df[orders_df["status"] == "completed"]
    items = order_items_df.merge(completed[["order_id", "order_date"]], on="order_id")
    n_returns = int(len(items) * rate)
    sample = items.sample(n=n_returns, random_state=SEED) if n_returns else items.iloc[0:0]

    rows = []
    reasons = ["damaged", "not_as_described", "changed_mind", "wrong_item"]
    for i, (_, row) in enumerate(sample.iterrows(), start=1):
        return_date = pd.Timestamp(row["order_date"]) + timedelta(days=random.randint(2, 21))
        rows.append({
            "return_id": i,
            "order_id": row["order_id"],
            "product_id": row["product_id"],
            "return_date": return_date,
            "reason": random.choice(reasons),
        })
    return pd.DataFrame(rows)


def main():
    products_df = make_products()
    customers_df = make_customers()
    orders_df, order_items_df = make_orders_and_items(customers_df, products_df)
    returns_df = make_returns(orders_df, order_items_df)

    products_df.to_csv("../data/products.csv", index=False)
    customers_df.to_csv("../data/customers.csv", index=False)
    orders_df.to_csv("../data/orders.csv", index=False)
    order_items_df.to_csv("../data/order_items.csv", index=False)
    returns_df.to_csv("../data/returns.csv", index=False)

    print(f"Generated: {len(products_df)} products, {len(customers_df)} customers, "
          f"{len(orders_df)} orders, {len(order_items_df)} order items, "
          f"{len(returns_df)} returns")
    print(orders_df.groupby(orders_df['order_date'].astype('datetime64[ns]').dt.to_period('M')).size())


if __name__ == "__main__":
    main()
