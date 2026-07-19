
  
    
    

    create  table
      "chaos_clone"."main"."metric_revenue__dbt_tmp"
  
    as (
      select
    date_trunc('day', created_at) as day,
    count(*) as order_count,
    sum(amount_usd) as total_revenue_usd
from "chaos_clone"."main"."fct_orders"
group by 1
    );
  
  