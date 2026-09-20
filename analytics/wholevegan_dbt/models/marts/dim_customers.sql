select
    customer_id,
    customer_name,
    region,
    signup_date,
    segment,
    acquisition_channel
from {{ ref('stg_customers') }}