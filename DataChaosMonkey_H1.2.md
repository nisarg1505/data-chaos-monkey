# Horizon 1.2 — Bounded Blast Radius (DAG Pruning)

> Right now, injecting one fault triggers `dbt build` on the *entire* DAG — O(N). On gharchive (9 models) it's fine; on a 1000-model DAG it's death. This milestone rebuilds only the models that actually depend on the corrupted column, using the lineage map you already added to loader.py.

**Where you are:** H1.1 done — dynamic checksum verdicts. Tool runs on any output table.

**Goal:** `runner.py` rebuilds only affected models via `dbt build --select`, not the whole DAG.

---

## The idea

When you corrupt `stg_events.actor_login`, only models *downstream* of it need rebuilding (`actor_stats`, maybe `repo_activity`) — not the unrelated ones. dbt's `--select` with the `+` operator does exactly this: `--select stg_events+` means "stg_events and everything downstream."

You already have `build_lineage_map` in loader.py. Now use it to scope the run.

---

## Step 1 · Update Runner to accept a select scope

Replace `src/chaos_monkey/runner.py`:

```python
"""M4 / H1.2: re-run the pipeline, scoped to only affected models."""
import json
import subprocess
from pathlib import Path


class Runner:
    def __init__(self, dbt_dir: str, target: str = "clone"):
        self.dbt_dir = dbt_dir
        self.target = target

    def run(self, select: str | None = None, exclude_seed: bool = True):
        """Rebuild models + tests on the clone.
        select: dbt --select expression (e.g. 'stg_events+') to prune the DAG.
                None = build everything (fallback).
        exclude_seed: skip seeds so injected corruption in source tables survives.
        """
        cmd = ["uv", "run", "dbt", "build",
               "--profiles-dir", ".", "--target", self.target]
        if select:
            cmd += ["--select", select]
        if exclude_seed:
            cmd += ["--exclude", "resource_type:seed"]
        subprocess.run(cmd, cwd=self.dbt_dir, capture_output=True, text=True)
        return self._parse_results()

    def _parse_results(self):
        path = Path(self.dbt_dir) / "target" / "run_results.json"
        with open(path) as f:
            results = json.load(f)["results"]
        return {
            "run_errors": [r for r in results if r["status"] == "error"],
            "test_failures": [
                r for r in results
                if r["status"] == "fail" and r["unique_id"].startswith("test.")
            ],
        }
```

Note: changed `--exclude raw_charges` to `--exclude resource_type:seed` — generic across projects (gharchive has no seed, fixture does; this handles both).

---

## Step 2 · Compute the select scope from the corrupted model

The corrupted column lives in some model. You want to rebuild that model + everything downstream. The scope is `{model}+`.

Add a helper in `src/chaos_monkey/loader.py` (or a small util). Given a corrupted table like `main.stg_events`, the dbt model name is `stg_events`:

```python
def model_from_table(table: str) -> str:
    """'main.stg_events' -> 'stg_events' (strip schema qualifier)."""
    return table.split(".")[-1]


def select_scope(table: str) -> str:
    """dbt --select expression: the model + all downstream."""
    return f"{model_from_table(table)}+"
```

---

## Step 3 · Wire scope into the CLI run command

Update the `run` command in `cli.py` to compute and pass the scope. But — there's a subtlety: you inject into the *source* (e.g. `main.raw_events` or a staging table), and want to rebuild downstream. So the select is based on the *corrupted table's model*.

In `cli.py`'s `run`:
```python
from chaos_monkey.loader import select_scope

# ... after inject, before Runner:
    scope = select_scope(table)          # e.g. 'stg_events+'
    run_result = Runner(DBT_DIR).run(select=scope)
```

**Catch:** if you corrupt `raw_events` (a table dbt built), rebuilding `raw_events+` would re-run raw_events itself — which re-downloads from HTTP (slow) OR rebuilds from existing data (fine). For gharchive, corrupt a *staging* table (e.g. `main.stg_events`) instead of raw, so the scope starts mid-DAG and doesn't touch the expensive raw ingestion.

For the fixture, corrupting `raw_charges` and selecting `raw_charges+` is fine (tiny).

---

## Step 4 · Verify pruning works

On the fixture — corrupt a column, confirm only downstream models rebuild:

```bash
cd /Users/nisarg/data-chaos-monkey
cd fixture/dbt_project && uv run dbt build --profiles-dir . && cd ../..

uv run chaos-monkey run --fault statistical_drift --column amount \
  --table main.stg_charges --output main.metric_revenue
```

Then check `run_results.json` — it should show only `stg_charges` + downstream (`fct_orders`, `metric_revenue`) ran, NOT a full rebuild.

```bash
uv run python -c "
import json
r = json.load(open('fixture/dbt_project/target/run_results.json'))
print('models/tests run:', len(r['results']))
for x in r['results']:
    print(' ', x['status'], x['unique_id'].split('.')[-1])
"
```

**✅ Done when:** the run rebuilds only the affected subgraph, not all 9 models. On the fixture that's ~5 nodes instead of 11; on gharchive corrupting `stg_events` rebuilds staging+marts but skips the 33-second raw ingestion.

---

## Step 5 · The payoff on gharchive

This is why 1.2 matters: gharchive's `raw_events` takes 33 seconds to build (HTTP download). Without pruning, every fault re-pays that 33s. With pruning — corrupt `stg_events`, select `stg_events+` — you skip raw entirely and each fault runs in ~1 second. That's the sub-linear execution the roadmap promised.

---

## Step 6 · Commit

```bash
uv run ruff format src/
git add src/
git commit -m "H1.2: DAG pruning via --select, skip unaffected models"
git push
```

---

## One honest limitation to note
`select_scope` uses the *table you inject into* as the DAG root. That assumes you inject into a model dbt manages (staging/marts), not the raw source. For gharchive, always inject into `main.stg_events` (or another staging table), never `main.raw_events` — otherwise you re-trigger the 33s download. Document this in the tool's help text.

## Next: H1.3 (auto-matrix)
Now that verdicts are dynamic (1.1) and runs are pruned (1.2), 1.3 makes `report` discover *what* to test automatically from the guard map — so it works on gharchive with zero hardcoded matrix. That's the last piece before pointing the tool at the real pipeline.
