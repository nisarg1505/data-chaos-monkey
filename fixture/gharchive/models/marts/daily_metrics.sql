select
    date_trunc('hour', created_at)                        as activity_hour,
    count(*)                                              as total_events,
    count(distinct actor_login)                           as active_users,
    count(distinct repo_name)                             as active_repos,
    count(*) filter (where event_type = 'PullRequestEvent') as pr_events,
    count(*) filter (where event_type = 'IssuesEvent')      as issue_events
from {{ ref('stg_events') }}
group by 1
order by 1