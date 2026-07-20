-- Pull several hours of real GitHub events directly from HTTP.
-- This is genuinely messy: nested JSON, varying payloads per event type.
{{ config(materialized='table') }}

select *
from read_json_auto(
    [
        'https://data.gharchive.org/2024-01-15-12.json.gz',
        'https://data.gharchive.org/2024-01-15-13.json.gz',
        'https://data.gharchive.org/2024-01-15-14.json.gz'
    ],
    ignore_errors = true,
    maximum_object_size = 100000000
)