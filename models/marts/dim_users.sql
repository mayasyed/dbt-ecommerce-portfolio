with stg_users as (
    select * from {{ ref('stg_users') }}
)

select
    user_id,
    first_name,
    last_name,
    age,
    gender,
    city,
    state,
    country,
    traffic_source,
    user_created_at

from stg_users