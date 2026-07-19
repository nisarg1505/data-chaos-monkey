
  
  create view "chaos_fixture"."main"."stg_charges__dbt_tmp" as (
    select
    charge_id,
    customer_id,
    amount,
    currency,
    status,
    created_at::timestamp as created_at
from "chaos_fixture"."main"."raw_charges"
  );
