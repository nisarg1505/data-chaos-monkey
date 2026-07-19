import click
from rich.console import Console
from rich.table import Table
from chaos_monkey.loader import load_project

console = Console()


@click.group()
def cli():
    """Data Chaos Monkey."""


@cli.command("inspect")
@click.option("--manifest", default="fixture/dbt_project/target/manifest.json")
def inspect(manifest):
    """Dry-run: print the guard map (what's guarded vs unguarded)."""
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


if __name__ == "__main__":
    cli()
