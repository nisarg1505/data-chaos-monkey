# Horizon 1.5 — Stage 3: Marts + Realistic Test Suite

> Build the output models (the "dashboard numbers") that Chaos Monkey will test, then add a *realistically incomplete* test suite — some columns guarded, many not, like a real under-tested project. These marts are what faults will silently corrupt.

**Where you are:** Stage 2 done — 5 staging models built (827k events unnested).

**Goal:** 3 mart models + a realistic (deliberately patchy) test suite.

---

## Step 1 · Marts (the outputs)

`models/marts/repo_activity.sql` — events per repo:
```sql
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
```

`models/marts/actor_stats.sql` — contributions per user:
```sql
select
    actor_login,
    count(*)                                              as total_events,
    count(distinct repo_name)                             as repos_touched,
    count(*) filter (where event_type = 'PushEvent')      as pushes,
    count(*) filter (where event_type = 'PullRequestEvent') as prs,
    sum(coalesce(p.commit_count, 0))                      as total_commits
from {{ ref('stg_events') }} e
left join {{ ref('stg_push_events') }} p using (event_id)
where actor_login is not null
group by actor_login
```

`models/marts/daily_metrics.sql` — activity over time (the headline dashboard number):
```sql
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
```

---

## Step 2 · Build

```bash
cd /Users/nisarg/data-chaos-monkey/fixture/gharchive
uv run dbt run --profiles-dir .
```

Verify:
```bash
uv run python -c "
import duckdb
con = duckdb.connect('gharchive.duckdb')
for t in ['repo_activity','actor_stats','daily_metrics']:
    n = con.execute(f'SELECT count(*) FROM main.{t}').fetchone()[0]
    print(f'{t}: {n}')
"
```

**✅ marts built when:** all 3 populate (repo_activity ~tens of thousands of repos, daily_metrics = 3 hours × distinct hours).

---

## Step 3 · The REALISTIC test suite (the key part)

This is what makes it a believable target: **patchy coverage, like a real project.** Some obvious columns guarded, many not — including columns that flow to important outputs. Create `models/schema.yml`:

```yaml
version: 2

models:
  # staging — lightly tested (realistic: teams test the "important" base tables)
  - name: stg_events
    columns:
      - name: event_id
        tests: [not_null, unique]        # GUARDED
      - name: event_type
        tests: [not_null]                # GUARDED
      - name: actor_login                # UNGUARDED (silent target)
      - name: repo_name                  # UNGUARDED (silent target)
      - name: created_at                 # UNGUARDED (silent target)

  - name: stg_push_events
    columns:
      - name: event_id
        tests: [not_null]                # GUARDED
      - name: commit_count               # UNGUARDED — flows to actor_stats.total_commits
      - name: branch_ref                 # UNGUARDED

  - name: stg_pr_events
    columns:
      - name: event_id                   # UNGUARDED (realistic gap — no test at all)
      - name: is_merged                  # UNGUARDED
      - name: pr_number                  # UNGUARDED

  # marts — barely tested (realistic: output tables often lack column tests)
  - name: repo_activity
    columns:
      - name: repo_name
        tests: [not_null, unique]        # GUARDED
      - name: total_events               # UNGUARDED
      - name: unique_contributors        # UNGUARDED

  - name: actor_stats
    columns:
      - name: actor_login
        tests: [unique]                  # GUARDED (but NOT not_null — subtle gap)
      - name: total_commits              # UNGUARDED — the silent-corruption jackpot

  - name: daily_metrics
    columns:
      - name: activity_hour
        tests: [not_null]                # GUARDED
      - name: total_events               # UNGUARDED
      - name: active_users               # UNGUARDED
```

The realism: `event_id`, `repo_name`, `activity_hour` are guarded (the "obvious" keys). But `commit_count`, `total_commits`, `actor_login` nulls, `total_events` — all the things that actually matter for correctness — are unguarded. That's exactly how real projects under-test, and it's where Chaos Monkey will find silent gaps.

---

## Step 4 · Build + test green on clean data

```bash
uv run dbt build --profiles-dir .
```

**✅ Stage 3 done when:** everything builds and all tests pass on clean data (faults break it later, not the clean pipeline).

---

## Step 5 · Write the ground-truth (lighter than fixture)

Unlike the toy fixture, you won't hand-verify every column here. Instead, note the *pattern*: guarded = the keys (event_id, repo_name, activity_hour); unguarded = the metrics (commit_count, total_commits, total_events, actor_login). When Chaos Monkey runs, silent faults should land on the metric columns. Jot this in `fixture/gharchive/COVERAGE_NOTES.md` — a few lines, just enough to sanity-check the tool's verdicts.

---

## Next: Horizon 1.1-1.3 (make the tool work on THIS project)
The pipeline is now real. But Chaos Monkey still hardcodes `metric_revenue` from the toy fixture. Before it can run on gharchive, you need:
- **1.1** dynamic verdicts (checksum any output table, not just revenue)
- **1.2** DAG pruning (you've partly done this in loader.py)
- **1.3** auto-matrix (discover targets from the project)

Then Stage 4 = point Chaos Monkey at gharchive and watch it find real silent gaps in the metric columns. That's the money shot on real data.
