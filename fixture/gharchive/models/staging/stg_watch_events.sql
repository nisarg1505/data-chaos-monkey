select
    event_id,
    actor_login,
    repo_name,
    created_at
from {{ ref('stg_events') }}
where event_type = 'WatchEvent'