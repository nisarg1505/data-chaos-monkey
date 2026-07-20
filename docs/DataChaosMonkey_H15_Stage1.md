# Horizon 1.5 — Real Messy Pipeline (Stage 1: Ingestion)

> Build a realistic ~30-50 model dbt project on GH Archive (real GitHub events — nested JSON, schema drift, genuine mess), all local on DuckDB, $0. Then run Chaos Monkey on it. This stage: ingest GH Archive → raw layer.

**Why GH Archive:** every public GitHub event (push, PR, issues, stars, forks…), hourly gzipped JSON, genuinely nested and messy, schema drifts across event types. DuckDB reads it straight from HTTP — no cloud, no cost.

---

## Structure

New dbt project alongside your fixture:
```
fixture/
├── dbt_project/          # your existing toy fixture (keep it)
└── gharchive/            # NEW — the realistic messy pipeline
    ├── dbt_project.yml
    ├── profiles.yml
    ├── models/
    │   ├── raw/
    │   ├── staging/
    │   └── marts/
    └── seeds/
```

---

## Step 1 · Scaffold

```bash
cd /Users/nisarg/data-chaos-monkey
mkdir -p fixture/gharchive/models/{raw,staging,marts}
cd fixture/gharchive
```

`dbt_project.yml`:
```yaml
name: 'gharchive'
version: '1.0.0'
profile: 'gharchive'
model-paths: ["models"]
target-path: "target"
models:
  gharchive:
    raw:
      +materialized: table
    staging:
      +materialized: view
    marts:
      +materialized: table
```

`profiles.yml`:
```yaml
gharchive:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: 'gharchive.duckdb'
      threads: 4
      extensions:
        - httpfs
        - json
    clone:
      type: duckdb
      path: '/tmp/gh_clone.duckdb'
      threads: 4
      extensions:
        - httpfs
        - json
```

---

## Step 2 · Ingest raw GH Archive (the messy source)

We'll load a few hours of real events. This is the raw layer — deliberately unclean, straight from the firehose.

`models/raw/raw_events.sql`:
```sql
-- Pull several hours of real GitHub events directly from HTTP.
-- This is genuinely messy: nested JSON, varying payloads per event type.
{{ config(materialized='table') }}

select *
from read_json_auto(
    [
        'https://data.gharchive.org/2024-01-15-12.json.gz',
        'https://data.gharchive.org/2024-01-15-13.json.gz',
        'https://data.gharchive.org/2024-01-15-14.json.gz'
    ],
    ignore_errors = true,
    maximum_object_size = 100000000
)
```

Build it (this downloads ~real data, takes a minute):
```bash
cd /Users/nisarg/data-chaos-monkey/fixture/gharchive
uv run dbt run --select raw_events --profiles-dir .
```

Check what landed:
```bash
uv run python -c "
import duckdb
con = duckdb.connect('gharchive.duckdb')
print('rows:', con.execute('SELECT count(*) FROM main.raw_events').fetchone()[0])
print('event types:')
for r in con.execute('SELECT type, count(*) n FROM main.raw_events GROUP BY type ORDER BY n DESC').fetchall():
    print(' ', r)
"
```

**✅ Stage 1 done when:** `raw_events` has tens of thousands of real GitHub events across many types (PushEvent, PullRequestEvent, IssuesEvent, WatchEvent, ForkEvent, etc.).

---

## What's next (staged, so it's not overwhelming)
- **Stage 2:** staging models — unnest the messy JSON into typed tables per event type (this is where the real mess lives: `payload` differs per event type).
- **Stage 3:** marts — `repo_activity`, `actor_stats`, `daily_metrics` (the outputs Chaos Monkey will test).
- **Stage 4:** a *realistic* test suite — some columns guarded, many not (like a real under-tested project).
- **Stage 5:** point Chaos Monkey at it — but first we need Horizon 1.1-1.3 (dynamic verdicts, auto-matrix) so the tool works on a project that isn't the fixture.

**Important:** the tool currently hardcodes `metric_revenue`. Before it can run on gharchive, you need **Horizon 1.1 (dynamic checksums)**. So the real order is:
1. Stage 1-4 here (build the messy pipeline)
2. Horizon 1.1-1.3 (make the tool work on any project)
3. Stage 5 (run Chaos Monkey on gharchive)

Get Stage 1 running (real events landing), then we do Stage 2.
