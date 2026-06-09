with stg_orders as (
    select * from {{ ref('stg_orders') }}
)

select
    order_id,
    user_id,
    status,
    gender,
    created_at      as order_created_at,
    returned_at,
    shipped_at,
    delivered_at,
    num_of_item

from stg_orders