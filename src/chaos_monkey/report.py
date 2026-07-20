"""H1.3: auto-discover targets, sweep faults, score any project's resilience."""

import duckdb

from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from chaos_monkey.faults import get_fault, applicable_faults
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.verdict import get_checksum, classify

console = Console()

_NUMERIC = {"BIGINT", "INTEGER", "DOUBLE", "DECIMAL", "FLOAT", "HUGEINT"}


def _column_type(db_path, table, column):
    schema, tbl = table.split(".") if "." in table else ("main", table)
    con = duckdb.connect(db_path)
    try:
        row = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? AND column_name = ?",
            [schema, tbl, column],
        ).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def _type_family(col_type: str) -> str:
    base = col_type.split("(")[0].strip()
    if base in _NUMERIC:
        return "numeric"
    if base == "VARCHAR":
        return "string"
    if base.startswith("TIMESTAMP") or base == "DATE":
        return "timestamp"
    return "other"


def build_report(db_path, dbt_dir, manifest_path, output_table, target_columns):
    results = []
    faults = applicable_faults()
    total_tasks = len(target_columns) * len(faults)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Initializing...", total=total_tasks)

        for table, column in target_columns:
            # Per-column: resolve type once, filter faults by family.
            col_type = _column_type(db_path, table, column)
            if col_type is None:
                progress.console.print(
                    f"[yellow]Skipping {table}.{column}: column not found[/]"
                )
                progress.advance(task_id, advance=len(faults))
                continue
            allowed = set(applicable_faults(_type_family(col_type)))

            for fault_name in faults:
                progress.update(
                    task_id, description=f"[cyan]Testing {column} ({fault_name})"
                )
                if fault_name not in allowed:
                    progress.advance(task_id)
                    continue

                inj = Injector(db_path)
                inj.clone()
                before = get_checksum(inj.clone_path, output_table)
                fault = get_fault(fault_name)

                try:
                    inj.inject(fault, table, column, 1.0)
                except Exception as e:
                    progress.console.print(
                        f"[yellow]Skipping {column} ({fault_name}): {e}[/]"
                    )
                    progress.advance(task_id)
                    continue

                # Strip 'main.' prefix so dbt can find the model in the DAG;
                # exclude the mutated model so dbt doesn't overwrite our chaos.
                dbt_model_name = table.split(".")[-1]
                run_result = Runner(dbt_dir).run(
                    select=f"{dbt_model_name}+", exclude=dbt_model_name
                )

                verdict, _ = classify(run_result, inj.clone_path, before, output_table)

                if verdict != "NO-OP":
                    results.append(
                        (
                            f"{column} ({fault_name})",
                            verdict,
                            fault.suggested_test(column),
                        )
                    )
                progress.advance(task_id)

    return results


def print_report(results):
    caught = sum(1 for _, v, _ in results if v == "CAUGHT")
    silent = [r for r in results if r[1] == "SILENT"]
    total = len(results)

    if total == 0:
        console.print(
            "[yellow]0 faults registered. Everything was skipped or evaluated to NO-OP.[/]"
        )
        return

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
