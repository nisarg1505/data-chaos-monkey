import click
from rich.console import Console
from rich.table import Table
from chaos_monkey.loader import load_project
from chaos_monkey.faults import get_fault
from chaos_monkey.injector import Injector
from chaos_monkey.runner import Runner
from chaos_monkey.verdict import classify
from chaos_monkey.report import build_report, print_report
from chaos_monkey.verdict import get_checksum

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

    run_result = Runner(DBT_DIR).run()
    verdict, after = classify(run_result, inj.clone_path, before, output)

    console.print(f"checksum: {before} -> {after}")
    console.print(f"[bold]VERDICT: {verdict}[/]")
    console.print(f"source untouched: {inj.verify_source_untouched()}")


if __name__ == "__main__":
    cli()


@cli.command("report")
def report():
    """Sweep all faults, score the pipeline's data resilience."""
    results = build_report()
    print_report(results)
