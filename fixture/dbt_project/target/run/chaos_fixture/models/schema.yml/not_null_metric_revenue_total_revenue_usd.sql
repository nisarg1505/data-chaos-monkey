
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_revenue_usd
from "chaos_clone"."main"."metric_revenue"
where total_revenue_usd is null



  
  
      
    ) dbt_internal_test