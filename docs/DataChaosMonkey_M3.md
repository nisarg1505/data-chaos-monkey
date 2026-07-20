# M3 — Injector + Runner (real modules)

> Turn your working scratch logic into two clean modules: `injector.py` (clone + inject) and `runner.py` (re-run pipeline on the clone). This is the plumbing that M5 (verdict) and the CLI sit on top of. You've already proven the logic works end-to-end (CAUGHT + SILENT verdicts) — this just makes it real code, not a scratch script.

**Where you are:** M0, M1, M2 done. Both faults (`statistical_drift`, `enum_drift`) proven via `scratch_prove.py`.

**Goal:** replace the scratch script with proper modules + a fault registry, so any fault can be injected and judged through one clean path.

---

## 1 · Fault registry

So the tool can look up a fault by name. Put this in `src/chaos_monkey/faults/__init__.py`:

```python
from chaos_monkey.faults.statistical_drift import StatisticalDrift
from chaos_monkey.faults.enum_drift import EnumDrift

REGISTRY = {
    f.name: f
    for f in [StatisticalDrift(), EnumDrift()]
}


def get_fault(name):
    if name not in REGISTRY:
        raise ValueError(f"unknown fault: {name}. Available: {list(REGISTRY)}")
    return REGISTRY[name]
```

---

## 2 · Injector module

Put this in `src/chaos_monkey/injector.py`:

```python
"""M3: safely clone the pipeline db and inject a fault into the SOURCE table."""
import shutil
from pathlib import Path
import duckdb


class Injector:
    def __init__(self, source_db: str, clone_path: str = "/tmp/chaos_clone.duckdb"):
        self.source_db = source_db
        self.clone_path = clone_path
        self._source_size = Path(source_db).stat().st_size

    def clone(self):
        """Zero-effort clone: copy the db file. Source is never touched."""
        shutil.copy(self.source_db, self.clone_path)
        return self.clone_path

    def inject(self, fault, table, column, severity):
        """Apply a fault to the clone. Returns the FaultResult."""
        con = duckdb.connect(self.clone_path)
        try:
            result = fault.apply(con, table, column, severity)
        finally:
            con.close()  # release so dbt can open it
        return result

    def verify_source_untouched(self) -> bool:
        """Safety guarantee: the source file must be byte-identical after a run."""
        return Path(self.source_db).stat().st_size == self._source_size
```

---

## 3 · Runner module

Put this in `src/chaos_monkey/runner.py`:

```python
"""M4: re-run the dbt pipeline against the corrupted clone, capture results."""
import json
import subprocess
from pathlib import Path


class Runner:
    def __init__(self, dbt_dir: str, target: str = "clone"):
        self.dbt_dir = dbt_dir
        self.target = target

    def run(self):
        """Rebuild models + tests on the clone. --exclude the seed so the
        injected corruption in the source table survives (dbt build re-seeds
        from the clean CSV otherwise)."""
        subprocess.run(
            ["uv", "run", "dbt", "build",
             "--profiles-dir", ".",
             "--target", self.target,
             "--exclude", "raw_charges"],
            cwd=self.dbt_dir, capture_output=True, text=True,
        )
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

---

## 4 · Verdict module (M5 — the payoff)

Put this in `src/chaos_monkey/verdict.py`:

```python
"""M5: classify a fault's outcome. Never confidently wrong."""
import duckdb


def classify(run_result, clone_path, before_value, after_query):
    """
    run_result: dict from Runner (run_errors, test_failures)
    before_value: the output metric BEFORE injection
    after_query: SQL to measure the same metric on the clone AFTER
    Returns one of: CRASHED / CAUGHT / SILENT / NO-OP
    """
    con = duckdb.connect(clone_path)
    try:
        after = con.execute(after_query).fetchone()[0]
    finally:
        con.close()

    if run_result["run_errors"]:
        return "CRASHED", after
    if run_result["test_failures"]:
        return "CAUGHT", after
    if after != before_value:
        return "SILENT", after   # ran green but output changed
    return "NO-OP", after         # fault didn't actually change anything
```

The `after != before` guard is the "never confidently wrong" rule: a fault is only SILENT if it *actually* changed the output. No change = NO-OP, not a false silent flag.

---

## 5 · Wire it into the CLI

Add a `run` command to `src/chaos_monkey/cli.py`. This replaces `scratch_prove.py` with a real command:

```python
from chaos_monkey.faults import get_fault
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.verdict import classify

SRC = "fixture/dbt_project/chaos_fixture.duckdb"
DBT_DIR = "fixture/dbt_project"
REVENUE_Q = "SELECT sum(total_revenue_usd) FROM main.metric_revenue"


@cli.command("run")
@click.option("--fault", required=True, help="fault name (statistical_drift/enum_drift)")
@click.option("--table", default="main.raw_charges")
@click.option("--column", required=True)
@click.option("--severity", default=0.3, type=float)
def run(fault, table, column, severity):
    """Inject one fault on a clone, re-run the pipeline, print the verdict."""
    import duckdb
    inj = Injector(SRC)
    inj.clone()

    con = duckdb.connect(inj.clone_path)
    before = con.execute(REVENUE_Q).fetchone()[0]
    con.close()

    f = get_fault(fault)
    result = inj.inject(f, table, column, severity)
    console.print(f"injected: {result.description}")

    run_result = Runner(DBT_DIR).run()
    verdict, after = classify(run_result, inj.clone_path, before, REVENUE_Q)

    safe = inj.verify_source_untouched()
    console.print(f"revenue: {before} -> {after}")
    console.print(f"[bold]VERDICT: {verdict}[/]")
    console.print(f"source untouched: {safe}")
```

---

## 6 · Test both verdicts through the real CLI

```bash
uv sync

# CAUGHT (guarded column):
uv run chaos-monkey run --fault statistical_drift --column amount

# SILENT (unguarded column that flows to revenue):
uv run chaos-monkey run --fault enum_drift --column status
```

**Expect:**
- `amount` → `VERDICT: CAUGHT` + `source untouched: True`
- `status` → `VERDICT: SILENT` + revenue dropped + `source untouched: True`

If both match, M3+M4+M5 are real modules, not scratch. Delete `scratch_prove.py` (it's served its purpose).

---

## 7 · Commit

```bash
git add src/
git status          # review before committing — no -A
git commit -m "M3/M4/M5: injector + runner + verdict modules, CLI run command"
git push
```

---

## ✅ Done when
- [ ] `chaos-monkey run --fault statistical_drift --column amount` → CAUGHT
- [ ] `chaos-monkey run --fault enum_drift --column status` → SILENT
- [ ] `source untouched: True` on both (the safety guarantee holds)
- [ ] scratch_prove.py deleted, real modules committed

---

## Git discipline (so the earlier mess doesn't repeat)
1. **Never `git add -A`.** Use explicit paths: `git add src/`.
2. **Always `git status` before committing** — read what's staged.
3. If pre-commit reformats files, just `git add src/` again and re-commit. Don't `--no-verify` unless it's a throwaday file.
4. `.gitignore` now covers `.pyc`, `__pycache__`, `scratch_prove.py`, `*.duckdb`, and `target/` — so junk won't get staged.

---

## Next: M6 (Resilience Report)
Once `run` works for a single fault, M6 loops over ALL columns × applicable faults, collects verdicts, and prints the resilience score + the SILENT list. That's where the guard map from M1 pays off — it tells you which faults *should* be CAUGHT vs SILENT, so you can validate the whole sweep against ground truth at once.
