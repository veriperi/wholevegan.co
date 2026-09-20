with order_items_agg as (
    select
        order_id,
        sum(line_total) as gross_revenue,
        count(*) as line_item_count
    from {{ ref('stg_order_items') }}
    group by order_id
),

returns_agg as (
    select
        order_id,
        count(*) as return_count
    from {{ ref('stg_returns') }}
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    o.order_date,
    o.channel,
    o.status,
    o.discount_pct,
    oi.gross_revenue,
    round(oi.gross_revenue * (1 - o.discount_pct / 100.0), 2) as net_revenue,
    oi.line_item_count,
    coalesce(r.return_count, 0) as return_count
from {{ ref('stg_orders') }} o
left join order_items_agg oi on o.order_id = oi.order_id
left join returns_agg r on o.order_id = r.order_id