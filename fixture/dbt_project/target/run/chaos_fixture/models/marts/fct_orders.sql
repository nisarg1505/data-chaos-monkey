
  
    
    

    create  table
      "chaos_fixture"."main"."fct_orders__dbt_tmp"
  
    as (
      select
    charge_id as order_id,
    customer_id,
    amount,
    currency,
    -- naive conversion; the point is this depends on `currency` being valid
    case currency
        when 'USD' then amount
        when 'EUR' then amount * 1.08
        when 'GBP' then amount * 1.27
    end as amount_usd,
    status,
    created_at
from "chaos_fixture"."main"."stg_charges"
where status = 'completed'
    );
  
  