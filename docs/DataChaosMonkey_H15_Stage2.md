# Horizon 1.5 — Stage 2: Staging Models (unnest the mess)

> Turn the raw 827k-event blob into typed staging models. This is where the real mess lives: every event type has a *different* `payload` shape, so unnesting is genuinely fiddly — exactly like a real pipeline.

**Where you are:** Stage 1 done — `raw_events` has 827k real events, 15 types.

**Goal:** staging views that extract clean, typed fields from the nested JSON — a base events view + per-type views for the messy payloads.

---

## The mess you're dealing with

Every GH Archive event has common fields (`id`, `type`, `actor`, `repo`, `created_at`) but a `payload` that differs entirely by type:
- PushEvent → `payload.commits`, `payload.size`
- PullRequestEvent → `payload.action`, `payload.pull_request.merged`
- IssuesEvent → `payload.action`, `payload.issue.number`
- WatchEvent → `payload.action` (just "started")

So staging = one clean base view + typed extractions per event type.

---

## Step 1 · Base staging view (common fields)

`models/staging/stg_events.sql`:
```sql
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
```

## Step 2 · Push events

`models/staging/stg_push_events.sql`:
```sql
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
```

## Step 3 · Pull request events

`models/staging/stg_pr_events.sql`:
```sql
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
```

## Step 4 · Issue events

`models/staging/stg_issue_events.sql`:
```sql
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
```

## Step 5 · Watch (star) events

`models/staging/stg_watch_events.sql`:
```sql
select
    event_id,
    actor_login,
    repo_name,
    created_at
from {{ ref('stg_events') }}
where event_type = 'WatchEvent'
```

---

## Step 6 · Build and verify

```bash
cd /Users/nisarg/data-chaos-monkey/fixture/gharchive
uv run dbt run --profiles-dir .
```

Check the staging models populated:
```bash
uv run python -c "
import duckdb
con = duckdb.connect('gharchive.duckdb')
for t in ['stg_events','stg_push_events','stg_pr_events','stg_issue_events','stg_watch_events']:
    n = con.execute(f'SELECT count(*) FROM main.{t}').fetchone()[0]
    print(f'{t}: {n}')
"
```

**✅ Stage 2 done when:** all staging views build, and counts roughly match the raw event-type distribution (push ~543k, PR ~52k, issues ~12k, watch ~28k).

---

## Watch for real mess (this is the point)
DuckDB's JSON access (`payload->>'field'`) may return NULLs where the payload shape varies or a field is missing — that's *real* and it's fine. Some events genuinely lack fields. Don't "fix" those NULLs — they're the realistic mess your Chaos Monkey will later probe. If a model errors on a type cast, that's a real schema-drift issue worth noting (loosen the cast, don't force it).

---

## Next: Stage 3 (marts)
Marts are the outputs Chaos Monkey will test: `repo_activity` (events per repo), `actor_stats` (contributions per user), `daily_metrics` (activity over time). These aggregate the staging models into the "dashboard numbers" that faults will silently corrupt.
