select
    return_id,
    order_id,
    product_id,
    return_date::timestamp as return_date,
    reason
from {{ source('raw', 'returns') }}
