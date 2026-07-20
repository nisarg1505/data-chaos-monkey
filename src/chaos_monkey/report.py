"""H1.3: auto-discover targets, sweep faults, score any project's resilience."""

from rich.console import Console
from rich.table import Table

from chaos_monkey.faults import get_fault, applicable_faults
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.loader import (
    select_scope,
)
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
            results.append(
                (f"{column} ({fault_name})", verdict, fault.suggested_test(column))
            )
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
        console.print(f"[red bold]⚠ {len(silent)} reach output SILENTLY:[/]")
        for label, _, suggested in silent:
            console.print(f"  • {label} → add {suggested}")
