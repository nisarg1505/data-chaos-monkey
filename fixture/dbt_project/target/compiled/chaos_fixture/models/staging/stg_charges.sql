select
    charge_id,
    customer_id,
    amount,
    currency,
    status,
    created_at::timestamp as created_at
from "chaos_fixture"."main"."raw_charges"