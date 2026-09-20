select
    order_id,
    customer_id,
    order_date::timestamp as order_date,
    channel,
    status,
    coalesce(discount_pct, 0) as discount_pct
from {{ source('raw', 'orders') }}