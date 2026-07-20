import click
import duckdb
from rich.console import Console
from rich.table import Table
from chaos_monkey.loader import load_project
from chaos_monkey.faults import get_fault
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.verdict import classify
from chaos_monkey.report import build_report, print_report
from chaos_monkey.verdict import get_checksum
from chaos_monkey.loader import select_scope

console = Console()

SRC = "fixture/dbt_project/chaos_fixture.duckdb"
DBT_DIR = "fixture/dbt_project"
REVENUE_Q = "SELECT sum(total_revenue_usd) FROM main.metric_revenue"


@click.group()
def cli():
    """Data Chaos Monkey."""


@cli.command("inspect")
@click.option("--manifest", default="fixture/dbt_project/target/manifest.json")
def inspect(manifest):
    """Print the guard map."""
    project = load_project(manifest)
    t = Table(title="Guard Map")
    t.add_column("Column")
    t.add_column("Guarded by")
    t.add_column("Status")
    for key, col in sorted(project.columns.items()):
        guards = ", ".join(col.guarding_tests) or "—"
        status = "[green]GUARDED[/]" if col.is_guarded else "[red]UNGUARDED[/]"
        t.add_row(key, guards, status)
    console.print(t)


@cli.command("run")
@click.option("--fault", required=True)
@click.option("--table", default="main.raw_charges", help="source table to corrupt")
@click.option("--column", required=True)
@click.option(
    "--output", required=True, help="output table to check, e.g. main.daily_metrics"
)
@click.option("--severity", default=0.3, type=float)
def run(fault, table, column, output, severity):
    """Inject one fault on a clone, re-run, print the verdict."""
    inj = Injector(SRC)
    inj.clone()

    before = get_checksum(inj.clone_path, output)

    f = get_fault(fault)
    result = inj.inject(f, table, column, severity)
    console.print(f"injected: {result.description}")

    scope = select_scope(table)  # e.g. 'stg_events+'
    run_result = Runner(DBT_DIR).run(select=scope)

    verdict, after = classify(run_result, inj.clone_path, before, output)

    console.print(f"checksum: {before} -> {after}")
    console.print(f"[bold]VERDICT: {verdict}[/]")
    console.print(f"source untouched: {inj.verify_source_untouched()}")


if __name__ == "__main__":
    cli()


@cli.command("report")
@click.option(
    "--db",
    required=True,
    help="built duckdb file, e.g. fixture/gharchive/gharchive.duckdb",
)
@click.option("--dbt-dir", required=True, help="e.g. fixture/gharchive")
@click.option(
    "--manifest", required=True, help="e.g. fixture/gharchive/target/manifest.json"
)
@click.option(
    "--output", required=True, help="output table to checksum, e.g. main.daily_metrics"
)
@click.option(
    "--inject-into",
    required=True,
    help="staging table to corrupt, e.g. main.stg_events",
)
def report(db, dbt_dir, manifest, output, inject_into):
    """Auto-sweep faults across a project's columns; score resilience."""

    # target columns: all columns of the inject_into model (from guard map)
    schema, tbl = (
        inject_into.split(".") if "." in inject_into else ("main", inject_into)
    )
    con = duckdb.connect(db)
    cols = [
        r[0]
        for r in con.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{tbl}' AND table_schema = '{schema}'"
        ).fetchall()
    ]
    con.close()
    target_columns = [(inject_into, c) for c in cols]

    results = build_report(db, dbt_dir, manifest, output, target_columns)
    print_report(results)
