# Horizon 1.1 — Dynamic Verdicts (kill the hardcoded metric_revenue)

> The tool currently hardcodes `SELECT sum(total_revenue_usd) FROM metric_revenue`. It can only test the toy fixture. This milestone makes verdicts work on *any* output table via checksums — so it can run on the gharchive pipeline (or any project).

**Where you are:** Engine works on toy fixture. Real gharchive pipeline built (9 models). Tool can't touch gharchive yet because verdicts are hardcoded.

**Goal:** replace the single hardcoded query with a checksum of *whatever output table* you point it at.

---

## The idea

Instead of "did revenue change," ask "did this output table's *contents* change" — via a structural checksum. Works on any table, any project.

Checksum = a single number summarizing every value in a table. If any cell changes, the checksum changes.

---

## Step 1 · Add checksum logic to verdict.py

Replace `src/chaos_monkey/verdict.py`:

```python
"""M5 / H1.1: classify a fault's outcome using dynamic table checksums.
Never confidently wrong."""
import duckdb


def checksum(con, table: str) -> int:
    """Structural checksum of an entire table. Any cell change -> different number.
    O(1) memory: DuckDB aggregates server-side."""
    # hash every row's full content, sum the hashes. Order-independent.
    row = con.execute(
        f"SELECT COALESCE(SUM(hash(CAST(t AS VARCHAR))), 0) FROM {table} t"
    ).fetchone()
    return row[0]


def get_checksum(clone_path: str, table: str) -> int:
    con = duckdb.connect(clone_path)
    try:
        return checksum(con, table)
    finally:
        con.close()


def classify(run_result, clone_path, before_checksum, output_table):
    """
    run_result: dict from Runner (run_errors, test_failures)
    before_checksum: checksum of output_table BEFORE injection
    output_table: the table whose corruption we measure (e.g. 'main.daily_metrics')
    Returns (verdict, after_checksum).
    """
    after = get_checksum(clone_path, output_table)

    if run_result["run_errors"]:
        return "CRASHED", after
    if run_result["test_failures"]:
        return "CAUGHT", after
    if after != before_checksum:
        return "SILENT", after   # ran green but output changed
    return "NO-OP", after         # fault didn't actually change output
```

The `after != before` guard is the "never confidently wrong" rule: SILENT only if the output *actually* changed.

---

## Step 2 · Update cli.py to use checksums + take the output table as a param

Update the `run` command in `src/chaos_monkey/cli.py`:

```python
from chaos_monkey.verdict import get_checksum, classify


@cli.command("run")
@click.option("--fault", required=True)
@click.option("--table", default="main.raw_charges", help="source table to corrupt")
@click.option("--column", required=True)
@click.option("--output", required=True, help="output table to check, e.g. main.daily_metrics")
@click.option("--severity", default=0.3, type=float)
def run(fault, table, column, output, severity):
    """Inject one fault on a clone, re-run, print the verdict."""
    inj = Injector(SRC)
    inj.clone()

    before = get_checksum(inj.clone_path, output)

    f = get_fault(fault)
    result = inj.inject(f, table, column, severity)
    console.print(f"injected: {result.description}")

    run_result = Runner(DBT_DIR).run()
    verdict, after = classify(run_result, inj.clone_path, before, output)

    console.print(f"checksum: {before} -> {after}")
    console.print(f"[bold]VERDICT: {verdict}[/]")
    console.print(f"source untouched: {inj.verify_source_untouched()}")
```

Note: `SRC` and `DBT_DIR` are still fixture-specific constants at the top of cli.py. For now, keep them — you'll parameterize project path in a later step. This milestone is just about *dynamic output tables*.

---

## Step 3 · Verify it still works on the fixture

The fixture's output is `metric_revenue`. Test both verdicts with the new `--output` flag:

```bash
cd /Users/nisarg/data-chaos-monkey
# rebuild fixture first (needs a clean db)
cd fixture/dbt_project && uv run dbt build --profiles-dir . && cd ../..

# CAUGHT (guarded column)
uv run chaos-monkey run --fault statistical_drift --column amount --output main.metric_revenue

# SILENT (unguarded, flows to output)
uv run chaos-monkey run --fault enum_drift --column status --output main.metric_revenue
```

**✅ Done when:**
- `amount` → CAUGHT
- `status` → SILENT, with `checksum: X -> Y` (different numbers)
- Both work using the *generic checksum*, not the hardcoded revenue query.

This proves the verdict engine no longer depends on knowing about "revenue" — it works on any table's checksum. Next milestone points it at gharchive.

---

## Step 4 · Commit

```bash
uv run ruff format src/
git add src/
git commit -m "H1.1: dynamic checksum verdicts, kill hardcoded revenue query"
git push
```

---

## Note on report.py
`report.py` still uses the old hardcoded `REVENUE_Q`. It'll break until you update it too — but that's part of **H1.3 (auto-matrix)**, which rewrites report.py to discover targets and outputs automatically. For now, `chaos-monkey run` (single fault) works dynamically; `report` (the sweep) gets fixed in 1.3. Don't run `report` until then.

## Next: H1.2 (DAG pruning) + H1.3 (auto-matrix)
- 1.2: use the lineage map (already in your loader.py) to rebuild only affected models — `dbt build --select`.
- 1.3: auto-discover which columns to test and which output tables to check, per project — so `report` works on gharchive with zero hardcoding.
