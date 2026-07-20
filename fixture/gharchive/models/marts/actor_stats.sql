select
    e.actor_login,
    count(*)                                              as total_events,
    count(distinct e.repo_name)                           as repos_touched,
    count(*) filter (where e.event_type = 'PushEvent')      as pushes,
    count(*) filter (where e.event_type = 'PullRequestEvent') as prs,
    sum(coalesce(p.commit_count, 0))                      as total_commits
from {{ ref('stg_events') }} e
left join {{ ref('stg_push_events') }} p using (event_id)
where e.actor_login is not null
group by e.actor_login