select
    customer_id,
    name as customer_name,
    region,
    signup_date::date as signup_date,
    segment,
    acquisition_channel
from {{ source('raw', 'customers') }}