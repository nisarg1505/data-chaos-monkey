# M6 — Resilience Report (the money shot)

> Loop over every column × applicable fault, collect verdicts, and print the resilience score + the list of SILENT faults (the ones that reach output undetected). This is where M1's guard map pays off — and it's the output you'll screenshot for the demo.

**Where you are:** M0–M5 done. Single-fault `chaos-monkey run` works, both CAUGHT and SILENT proven.

**Goal:** `chaos-monkey report` — sweeps the whole pipeline, validates against ground truth, prints the score.

---

## 1 · What to sweep

For v1, keep the sweep targeted (not every column × every fault — many combos are NO-OP noise). Define the meaningful test matrix. Put this in `src/chaos_monkey/report.py`:

```python
"""M6: sweep faults across columns, score the pipeline's resilience."""
import duckdb
from rich.console import Console
from rich.table import Table

from chaos_monkey.faults import get_fault
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.verdict import classify

console = Console()

SRC = "fixture/dbt_project/chaos_fixture.duckdb"
DBT_DIR = "fixture/dbt_project"
REVENUE_Q = "SELECT sum(total_revenue_usd) FROM main.metric_revenue"

# The test matrix: (fault, source_column, human_label)
# Chosen to hit columns that actually flow to output, mixing guarded + unguarded.
MATRIX = [
    ("statistical_drift", "amount", "amount nulls"),
    ("statistical_drift", "charge_id", "charge_id nulls"),
    ("enum_drift", "status", "status enum drift"),
    ("enum_drift", "currency", "currency enum drift"),
]


def run_one(fault_name, column, severity=0.3):
    inj = Injector(SRC)
    inj.clone()
    con = duckdb.connect(inj.clone_path)
    before = con.execute(REVENUE_Q).fetchone()[0]
    con.close()

    fault = get_fault(fault_name)
    inj.inject(fault, "main.raw_charges", column, severity)
    run_result = Runner(DBT_DIR).run()
    verdict, _ = classify(run_result, inj.clone_path, before, REVENUE_Q)
    return verdict, fault.suggested_test(column)


def build_report():
    results = []
    for fault_name, column, label in MATRIX:
        verdict, suggested = run_one(fault_name, column)
        results.append((label, verdict, suggested))
    return results


def print_report(results):
    caught = sum(1 for _, v, _ in results if v == "CAUGHT")
    silent = [r for r in results if r[1] == "SILENT"]
    crashed = sum(1 for _, v, _ in results if v == "CRASHED")
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
        console.print(f"[red bold]⚠ {len(silent)} faults reach output SILENTLY:[/]")
        for label, _, suggested in silent:
            console.print(f"  • {label} → add {suggested}")
```

---

## 2 · Wire into CLI

Add to `src/chaos_monkey/cli.py`:

```python
from chaos_monkey.report import build_report, print_report


@cli.command("report")
def report():
    """Sweep all faults, score the pipeline's data resilience."""
    results = build_report()
    print_report(results)
```

---

## 3 · Run it

```bash
uv run chaos-monkey report
```

**Expect** (validate against your GROUND_TRUTH.md):
- `amount nulls` → CAUGHT (guarded by not_null)
- `charge_id nulls` → CAUGHT (guarded)
- `status enum drift` → SILENT (unguarded, drops revenue)
- `currency enum drift` → CAUGHT (guarded by accepted_values)

So: **3/4 caught, 1 silent** (status), with a suggested fix. That's the resilience score.

---

## 4 · Validate the sweep against ground truth

Every verdict in the report should match a row in your `fixture/GROUND_TRUTH.md`. If any disagrees:
- verdict wrong → tool bug (good, you caught it)
- ground truth wrong → fix the table, note why

This is the whole design paying off: M1 told you what *should* be guarded, M6 proves what *actually is*, and they're validated against each other.

---

## 5 · Commit

```bash
uv run ruff format src/
git add src/
git commit -m "M6 resilience report and score"
git push
```

---

## ✅ Done when
- [ ] `chaos-monkey report` prints the full table + score
- [ ] verdicts match GROUND_TRUTH.md
- [ ] SILENT faults show a suggested fix
- [ ] committed + pushed

---

## Note on speed
Each matrix row clones + re-runs dbt (~1–2s each on your fixture). 4 rows = a few seconds, fine. When you add more faults/columns later, this sweep grows — that's when caching baselines (M4's optimization) matters. Not needed yet.

## Next: M7 (the demo money-shot)
M6 gives you the terminal report. M7 captures the *reveal* — a green test suite, then the report showing hidden SILENT holes — as a GIF/recording. That's the first postable artifact. After M7 comes M8 (the live interactive page = "the website").
