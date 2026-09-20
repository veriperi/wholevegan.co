select
    oi.order_id,
    oi.product_id,
    p.product_name,
    p.category,
    o.order_date,
    o.status,
    oi.quantity,
    oi.unit_price,
    oi.line_total
from {{ ref('stg_order_items') }} oi
join {{ ref('stg_products') }} p on oi.product_id = p.product_id
join {{ ref('stg_orders') }} o on oi.order_id = o.order_id