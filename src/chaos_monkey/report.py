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
    total = len(results)

    t = Table(title="Pipeline Resilience Report")
    t.add_column("Fault")
    t.add_column("Verdict")
    t.add_column("Fix (if silent)")
    for label, verdict, suggested in results:
        color = {"CAUGHT": "green", "SILENT": "red", "CRASHED": "yellow"}.get(
            verdict, "white"
        )
        fix = suggested if verdict == "SILENT" else "—"
        t.add_row(label, f"[{color}]{verdict}[/]", fix)
    console.print(t)

    console.print(f"\n[bold]Resilience: {caught}/{total} faults caught[/]")
    if silent:
        console.print(f"[red bold]⚠ {len(silent)} faults reach output SILENTLY:[/]")
        for label, _, suggested in silent:
            console.print(f"  • {label} → add {suggested}")
