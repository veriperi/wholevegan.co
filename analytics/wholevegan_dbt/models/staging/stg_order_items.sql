select
    order_id,
    product_id,
    quantity,
    unit_price::numeric(10,2) as unit_price,
    quantity * unit_price as line_total
from {{ source('raw', 'order_items') }}