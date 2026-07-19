
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select charge_id
from "chaos_fixture"."main"."stg_charges"
where charge_id is null



  
  
      
    ) dbt_internal_test