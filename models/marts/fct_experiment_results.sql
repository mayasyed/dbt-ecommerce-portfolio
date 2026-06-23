{{
    config(
        materialized = 'table'
    )
}}

/*
    Experiment results fact table for the checkout free-shipping banner A/B test.

    Each row represents one order placed during the test window. Joins simulated
    variant assignments to order data from thelook_ecommerce.

    Test window: 2024-01-01 to 2024-01-28 (4 weeks, simulated).
    Adjust the date filters below if a different window is needed.

    Primary metric:   order_value  (used to calculate average order value per variant)
    Guardrail metric: is_returned  (used to calculate return rate per variant)
*/

with assignments as (

    select
        user_id,
        variant
    from {{ ref('stg_experiment_assignments') }}

),

orders as (

    select
        id         as order_id,
        user_id,
        status     as order_status,
        created_at as order_created_at
    from {{ source('thelook_ecommerce', 'orders') }}
    where
        -- Test window: hardcoded for the portfolio simulation.
        -- In production this would use dbt variables so the window is configurable:
        --   dbt run --vars "{'experiment_start': '2024-01-01', 'experiment_end': '2024-01-28'}"
        -- and the filter would read: date(created_at) between '{{ var("experiment_start") }}' and '{{ var("experiment_end") }}'
        date(created_at) between '2024-01-01' and '2024-01-28'
        -- Only include orders that have a final status
        and status in ('Complete', 'Returned')

),

order_values as (

    -- Sum sale_price at the order level across all line items.
    -- No status filter here as we want the full basket value regardless
    -- of individual item status.
    select
        order_id,
        sum(sale_price) as order_value,
        count(*)        as item_count
    from {{ source('thelook_ecommerce', 'order_items') }}
    group by order_id

),

joined as (

    select
        o.order_id,
        o.user_id,
        a.variant,
        o.order_status,
        o.order_created_at,
        ov.order_value,
        ov.item_count,

        -- Metric flags used directly in the Python analysis
        case when o.order_status = 'Complete' then 1 else 0 end as is_completed,
        case when o.order_status = 'Returned' then 1 else 0 end as is_returned

    from orders             o
    inner join assignments  a  on o.user_id  = a.user_id
    inner join order_values ov on o.order_id = ov.order_id

)

select * from joined
