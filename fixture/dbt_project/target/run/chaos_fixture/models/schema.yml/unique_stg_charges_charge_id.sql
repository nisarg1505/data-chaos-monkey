
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    charge_id as unique_field,
    count(*) as n_records

from "chaos_fixture"."main"."stg_charges"
where charge_id is not null
group by charge_id
having count(*) > 1



  
  
      
    ) dbt_internal_test