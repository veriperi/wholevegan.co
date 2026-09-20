select
    product_id,
    product_name,
    category,
    price::numeric(10,2) as price
from {{ source('raw', 'products') }}