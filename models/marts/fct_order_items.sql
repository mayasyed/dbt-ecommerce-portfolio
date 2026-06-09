with stg_order_items as (
    select * from {{ ref('stg_order_items') }}
),

stg_orders as (
    select * from {{ ref('stg_orders') }}
)

select
    oi.order_item_id,
    oi.order_id,
    oi.user_id,
    oi.product_id,
    oi.status,
    oi.created_at,
    oi.shipped_at,
    oi.delivered_at,
    oi.returned_at,
    oi.sale_price,
    o.num_of_item

from stg_order_items oi
left join stg_orders o
    on oi.order_id = o.order_id