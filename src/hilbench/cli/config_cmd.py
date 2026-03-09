"""Config subcommands: show, validate, generate."""

from __future__ import annotations

import json
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.syntax import Syntax

from hilbench.config import load_config, resolve_config_path


@click.group("config")
def config_cmd() -> None:
    """View and validate bench configuration."""


@config_cmd.command()
@click.pass_obj
def show(ctx: object) -> None:
    """Display the active configuration."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    rendered = yaml.dump(
        json.loads(cfg.model_dump_json()),
        default_flow_style=False,
        sort_keys=False,
    )
    console.print(Syntax(rendered, "yaml", theme="monokai"))


@config_cmd.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.pass_obj
def validate(ctx: object, config_path: str | None) -> None:
    """Validate a config file and report errors."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    path = config_path or ctx.config_path
    try:
        cfg = load_config(path)
        console.print(f"[green]Config valid:[/green] {resolve_config_path(path)}")
        console.print(f"  bench_name: {cfg.bench_name}")
        console.print(f"  targets:    {list(cfg.targets)}")
    except Exception as exc:
        console.print(f"[red]Config invalid:[/red] {exc}")
        raise SystemExit(1) from exc


@config_cmd.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output path (default: stdout).",
)
def generate(output: str | None) -> None:
    """Generate a config template."""
    template = Path(__file__).resolve().parents[3] / "configs" / "config.template.yaml"
    if not template.exists():
        click.echo("Template not found — install from repo root.", err=True)
        raise SystemExit(1)
    content = template.read_text()
    if output:
        Path(output).write_text(content)
        click.echo(f"Written to {output}")
    else:
        click.echo(content)
