with stg_products as (
    select * from {{ ref('stg_products') }}
)

select
    product_id,
    product_name,
    brand,
    category,
    department,
    cost,
    retail_price

from stg_products