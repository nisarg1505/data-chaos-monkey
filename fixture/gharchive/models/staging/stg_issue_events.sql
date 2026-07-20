select
    event_id,
    actor_login,
    repo_name,
    created_at,
    (payload->>'action')                        as action,
    (payload->'issue'->>'number')::int          as issue_number,
    (payload->'issue'->>'state')                as issue_state
from {{ ref('stg_events') }}
where event_type = 'IssuesEvent'