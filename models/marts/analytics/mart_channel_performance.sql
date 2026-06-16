-- Business question: which acquisition channel brings the most valuable and
-- the stickiest customers? Spend follows the channel that wins on revenue per
-- customer and repeat rate, not just raw sign-up volume.
--
-- Grain: one row per traffic_source (acquisition channel).
--
-- Orders, revenue, and the repeat flag are all derived from fct_order_items
-- filtered on the SAME item-level status, so every metric in a row excludes the
-- same rows. (A customer's order is counted when it has at least one
-- non-cancelled item.)

with users as (
    select
        user_id,
        traffic_source
    from {{ ref('dim_users') }}
),

order_items as (
    select
        user_id,
        order_id,
        sale_price
    from {{ ref('fct_order_items') }}
    where status != 'Cancelled'
),

per_user as (
    select
        user_id,
        count(distinct order_id) as lifetime_orders,
        sum(sale_price)          as lifetime_revenue
    from order_items
    group by user_id
),

user_level as (
    select
        u.user_id,
        u.traffic_source,
        coalesce(p.lifetime_orders, 0)   as lifetime_orders,
        coalesce(p.lifetime_revenue, 0)  as lifetime_revenue,
        case when p.lifetime_orders >= 2 then 1 else 0 end as is_repeat_customer
    from users u
    left join per_user p on u.user_id = p.user_id
)

select
    traffic_source,
    count(*)                                                  as customers,
    sum(lifetime_orders)                                      as total_orders,
    round(sum(lifetime_revenue), 2)                           as total_revenue,
    round(safe_divide(sum(lifetime_revenue), count(*)), 2)    as revenue_per_customer,
    round(safe_divide(sum(lifetime_orders), count(*)), 2)     as orders_per_customer,
    round(safe_divide(sum(is_repeat_customer), count(*)), 4)  as repeat_purchase_rate
from user_level
group by traffic_source
order by total_revenue desc
