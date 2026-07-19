select
    charge_id,
    customer_id,
    amount,
    currency,
    status,
    created_at::timestamp as created_at
from "chaos_clone"."main"."raw_charges"