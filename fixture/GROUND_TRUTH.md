# Fixture Ground Truth

For each (column, fault) the tool's verdict is validated against this table.
CAUGHT = a test should fire. SILENT = no test guards it, corruption reaches output.
CRASHED = the fault breaks schema/SQL so dbt run errors.

| Table       | Column         | Guarded by            | Fault injected            | Expected verdict |
|-------------|----------------|-----------------------|---------------------------|------------------|
| stg_charges | charge_id      | not_null, unique      | statistical_drift (nulls) | CAUGHT           |
| stg_charges | amount         | not_null              | statistical_drift (nulls) | CAUGHT           |
| stg_charges | currency       | accepted_values       | enum_drift ('BTC')        | CAUGHT           |
| stg_charges | status         | — (none)              | enum_drift ('processing') | SILENT           |
| stg_charges | customer_id    | — (none)              | statistical_drift (nulls) | SILENT           |
| fct_orders  | order_id       | not_null, unique      | statistical_drift (nulls) | CAUGHT           |
| fct_orders  | amount_usd     | — (none)              | type_coercion (round)     | SILENT           |
| fct_orders  | status         | — (none)              | enum_drift ('processing') | SILENT           |
| metric_revenue | total_revenue_usd | not_null       | statistical_drift (nulls) | CAUGHT           |