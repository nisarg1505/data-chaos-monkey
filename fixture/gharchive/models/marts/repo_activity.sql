select
    repo_name,
    count(*)                                          as total_events,
    count(*) filter (where event_type = 'PushEvent')  as pushes,
    count(*) filter (where event_type = 'WatchEvent') as stars,
    count(*) filter (where event_type = 'ForkEvent')  as forks,
    count(distinct actor_login)                       as unique_contributors,
    min(created_at)                                   as first_seen,
    max(created_at)                                   as last_seen
from {{ ref('stg_events') }}
where repo_name is not null
group by repo_name