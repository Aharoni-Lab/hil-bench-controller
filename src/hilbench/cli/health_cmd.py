"""Health check subcommand."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from hilbench.health import CHECK_CATEGORIES, results_to_dicts, run_checks


@click.command()
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--check",
    "-c",
    "checks",
    multiple=True,
    type=click.Choice(CHECK_CATEGORIES, case_sensitive=False),
    help="Run only specific checks (repeatable). Default: all.",
)
@click.pass_obj
def health(ctx: object, as_json: bool, checks: tuple[str, ...]) -> None:
    """Run health checks on the bench."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    categories = list(checks) if checks else None
    results = run_checks(cfg, categories=categories)

    try:
        from hilbench.publisher import on_health_complete

        on_health_complete(cfg, results)
    except ImportError:
        pass

    all_passed = all(r.passed for r in results)

    if as_json:
        data = {"healthy": all_passed, "checks": results_to_dicts(results)}
        click.echo(json.dumps(data, indent=2))
    else:
        table = Table(title=f"Health: {cfg.bench_name}")
        table.add_column("Check", style="bold")
        table.add_column("Status")
        table.add_column("Detail")
        for r in results:
            status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            table.add_row(r.name, status, r.detail)
        console.print(table)

    if not all_passed:
        raise SystemExit(1)
