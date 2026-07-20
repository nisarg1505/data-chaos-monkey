{{ config(materialized='table') }}
select
    id::bigint              as event_id,
    type                    as event_type,
    actor.id::bigint        as actor_id,
    actor.login             as actor_login,
    repo.id::bigint         as repo_id,
    repo.name               as repo_name,
    created_at::timestamp   as created_at,
    public                  as is_public,
    payload                 as payload   -- keep raw for typed extraction below
from {{ ref('raw_events') }}
where id is not null