{{ config(materialized='table') }}

select *
from read_json(
    [
        'https://data.gharchive.org/2024-01-15-12.json.gz'
    ],
    format = 'newline_delimited',
    records = true,
    ignore_errors = true,
    maximum_object_size = 100000000
)