select
    event_id,
    actor_login,
    repo_name,
    created_at,
    (payload->>'size')::int         as commit_count,
    (payload->>'ref')               as branch_ref,
    (payload->>'push_id')::bigint   as push_id
from {{ ref('stg_events') }}
where event_type = 'PushEvent'