# Horizon 1.3 — Auto-Matrix Generation (kill the hardcoded suite)

> `report.py` hardcodes a 4-row MATRIX and the fixture's revenue query. This milestone makes it *discover* what to test from the project itself — every column that flows to an output, paired with applicable faults — so `report` works on gharchive (or any project) with zero config.

**Where you are:** H1.1 (dynamic verdicts) + H1.2 (DAG pruning) done. `chaos-monkey run` works on any project. `report` still hardcoded.

**Goal:** `chaos-monkey report --project <path>` auto-discovers targets and prints a resilience report for any dbt project.

---

## The idea

The loader already gives you the guard map (every column + its tests) and lineage. To auto-generate the test matrix:
1. Find the **output tables** (models nothing else depends on — the leaves of the DAG).
2. Find **columns that flow to those outputs** (via lineage).
3. Pair each with **applicable faults** (enum_drift for strings, statistical_drift for any).
4. Run each, checksum the output, collect verdicts.

---

## Step 1 · Discover output (terminal) models

Add to `src/chaos_monkey/loader.py`:

```python
def find_output_models(manifest: dict) -> list[str]:
    """Terminal models: those no other model depends on (DAG leaves)."""
    all_models = {
        node["name"]
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model"
    }
    depended_on = set()
    for node in manifest["nodes"].values():
        for dep in node.get("depends_on", {}).get("nodes", []):
            if dep in manifest["nodes"] and manifest["nodes"][dep]["resource_type"] == "model":
                depended_on.add(manifest["nodes"][dep]["name"])
    # outputs = models nobody depends on
    return sorted(all_models - depended_on)
```

---

## Step 2 · Pick a fault per column type

Add to `src/chaos_monkey/faults/__init__.py`:

```python
def applicable_faults(column_type: str = "any"):
    """Which faults make sense for a column. v1: type-agnostic defaults."""
    # For now, try both; the verdict's NO-OP filter handles bad fits.
    return ["statistical_drift", "enum_drift"]
```

---

## Step 3 · Rewrite report.py to be project-driven

Replace `src/chaos_monkey/report.py`:

```python
"""H1.3: auto-discover targets, sweep faults, score any project's resilience."""
import duckdb
from rich.console import Console
from rich.table import Table

from chaos_monkey.faults import get_fault, applicable_faults
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.loader import load_project, find_output_models, load_manifest, select_scope
from chaos_monkey.verdict import get_checksum, classify

console = Console()


def build_report(db_path, dbt_dir, manifest_path, output_table, target_columns):
    """
    db_path: the built duckdb file to clone
    dbt_dir: dbt project dir
    manifest_path: target/manifest.json
    output_table: e.g. 'main.daily_metrics' — the table we checksum
    target_columns: list of (table, column) to attack
    """
    results = []
    for table, column in target_columns:
        for fault_name in applicable_faults():
            inj = Injector(db_path)
            inj.clone()
            before = get_checksum(inj.clone_path, output_table)
            fault = get_fault(fault_name)
            try:
                inj.inject(fault, table, column, 0.3)
            except Exception:
                continue  # fault doesn't apply to this column type
            scope = select_scope(table)
            run_result = Runner(dbt_dir).run(select=scope)
            verdict, _ = classify(run_result, inj.clone_path, before, output_table)
            if verdict == "NO-OP":
                continue  # this fault didn't affect this output; skip noise
            results.append((f"{column} ({fault_name})", verdict,
                            fault.suggested_test(column)))
    return results


def print_report(results):
    caught = sum(1 for _, v, _ in results if v == "CAUGHT")
    silent = [r for r in results if r[1] == "SILENT"]
    total = len(results)

    t = Table(title="Pipeline Resilience Report")
    t.add_column("Fault")
    t.add_column("Verdict")
    t.add_column("Fix (if silent)")
    for label, verdict, suggested in results:
        color = {"CAUGHT": "green", "SILENT": "red", "CRASHED": "yellow"}.get(verdict, "white")
        fix = suggested if verdict == "SILENT" else "—"
        t.add_row(label, f"[{color}]{verdict}[/]", fix)
    console.print(t)

    console.print(f"\n[bold]Resilience: {caught}/{total} faults caught[/]")
    if silent:
        console.print(f"[red bold]⚠ {len(silent)} reach output SILENTLY:[/]")
        for label, _, suggested in silent:
            console.print(f"  • {label} → add {suggested}")
```

---

## Step 4 · Wire the report command with project params

Update `report` in `cli.py`:

```python
from chaos_monkey.loader import load_project, load_manifest, find_output_models


@cli.command("report")
@click.option("--db", required=True, help="built duckdb file, e.g. fixture/gharchive/gharchive.duckdb")
@click.option("--dbt-dir", required=True, help="e.g. fixture/gharchive")
@click.option("--manifest", required=True, help="e.g. fixture/gharchive/target/manifest.json")
@click.option("--output", required=True, help="output table to checksum, e.g. main.daily_metrics")
@click.option("--inject-into", required=True, help="staging table to corrupt, e.g. main.stg_events")
def report(db, dbt_dir, manifest, output, inject_into):
    """Auto-sweep faults across a project's columns; score resilience."""
    m = load_manifest(manifest)
    project = load_project(manifest)

    # target columns: all columns of the inject_into model (from guard map)
    model_name = inject_into.split(".")[-1]
    target_columns = [
        (inject_into, col.name)
        for key, col in project.columns.items()
        if col.table == model_name
    ]

    from chaos_monkey.report import build_report, print_report
    results = build_report(db, dbt_dir, manifest, output, target_columns)
    print_report(results)
```

---

## Step 5 · Run on the fixture (sanity check)

```bash
cd fixture/dbt_project && uv run dbt build --profiles-dir . && cd ../..

uv run chaos-monkey report \
  --db fixture/dbt_project/chaos_fixture.duckdb \
  --dbt-dir fixture/dbt_project \
  --manifest fixture/dbt_project/target/manifest.json \
  --output main.metric_revenue \
  --inject-into main.stg_charges
```

Should sweep stg_charges' columns and reproduce your known verdicts (amount→CAUGHT, status→SILENT, etc.).

---

## Step 6 · The money shot — run on gharchive

```bash
# make sure gharchive is built + has a manifest
cd fixture/gharchive && uv run dbt build --profiles-dir . && cd ../..

uv run chaos-monkey report \
  --db fixture/gharchive/gharchive.duckdb \
  --dbt-dir fixture/gharchive \
  --manifest fixture/gharchive/target/manifest.json \
  --output main.daily_metrics \
  --inject-into main.stg_events
```

**✅ Done when:** it sweeps `stg_events`' columns (actor_login, repo_name, created_at, event_type…), injects faults, and reports which reach `daily_metrics` silently — on a REAL 827k-event pipeline, with zero hardcoded matrix.

**This is the result you post about:** "I ran my chaos tool on a real 827k-event GitHub pipeline and found N silent gaps its tests miss."

---

## Step 7 · Commit

```bash
uv run ruff format src/
git add src/
git commit -m "H1.3: auto-matrix, report runs on any project incl gharchive"
git push
```

---

## Expected reality check
On gharchive, expect several SILENT verdicts — the realistic test suite deliberately left metric columns unguarded. `event_id`/`event_type` (guarded) → CAUGHT; `actor_login`/`repo_name`/`created_at` (unguarded, flow to daily_metrics) → likely SILENT. Cross-check against your COVERAGE_NOTES.md.

Some faults will be NO-OP (e.g. corrupting a column daily_metrics doesn't use) — those are filtered out automatically. That's correct: only report faults that actually reach the output.

## Next
After 1.3 the tool is *real* — runs on any dbt project, auto-discovers, prunes the DAG, checksums outputs. That's the substance. Then: more faults (type_coercion, unit_shift), then M7/M8 (demo + ship) on the gharchive result.
