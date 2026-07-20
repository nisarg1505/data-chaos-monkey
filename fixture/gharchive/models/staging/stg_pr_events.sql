select
    event_id,
    actor_login,
    repo_name,
    created_at,
    (payload->>'action')                              as action,
    (payload->'pull_request'->>'merged')::boolean     as is_merged,
    (payload->'pull_request'->>'number')::int         as pr_number,
    (payload->'pull_request'->>'additions')::int      as additions,
    (payload->'pull_request'->>'deletions')::int      as deletions
from {{ ref('stg_events') }}
where event_type = 'PullRequestEvent'