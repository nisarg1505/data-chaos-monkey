select
    date_trunc('day', created_at) as day,
    count(*) as order_count,
    sum(amount_usd) as total_revenue_usd
from {{ ref('fct_orders') }}
group by 1