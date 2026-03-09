"""GPIO subcommands: set, get, pulse."""

from __future__ import annotations

import click
from rich.console import Console

from hilbench.gpio import GpiodController, resolve_pin


@click.group()
def gpio() -> None:
    """GPIO pin control."""


@gpio.command("set")
@click.option("--pin", "-p", required=True, help="Pin name (from config) or GPIO line number.")
@click.option(
    "--value", "-v", required=True, type=click.Choice(["high", "low"]), help="Pin value."
)
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.pass_obj
def set_pin(ctx: object, pin: str, value: str, target_name: str | None) -> None:
    """Set a GPIO pin high or low."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)
    line = resolve_pin(pin, target.gpio)
    high = value == "high"

    if ctx.dry_run:
        console.print(f"[yellow]dry-run:[/yellow] would set GPIO {line} (pin={pin}) → {value}")
        return

    ctrl = GpiodController()
    ctrl.set_pin(line, high)
    console.print(f"GPIO {line} ({pin}) → [bold]{value}[/bold]")


@gpio.command("get")
@click.option("--pin", "-p", required=True, help="Pin name or GPIO line number.")
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.pass_obj
def get_pin(ctx: object, pin: str, target_name: str | None) -> None:
    """Read a GPIO pin value."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)
    line = resolve_pin(pin, target.gpio)

    if ctx.dry_run:
        console.print(f"[yellow]dry-run:[/yellow] would read GPIO {line} (pin={pin})")
        return

    ctrl = GpiodController()
    val = ctrl.get_pin(line)
    label = "HIGH" if val else "LOW"
    console.print(f"GPIO {line} ({pin}) = [bold]{label}[/bold]")


@gpio.command()
@click.option("--pin", "-p", required=True, help="Pin name or GPIO line number.")
@click.option("--duration", "-d", type=int, default=100, help="Pulse duration in ms.")
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.pass_obj
def pulse(ctx: object, pin: str, duration: int, target_name: str | None) -> None:
    """Pulse a GPIO pin high for a duration."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)
    line = resolve_pin(pin, target.gpio)

    if ctx.dry_run:
        console.print(
            f"[yellow]dry-run:[/yellow] would pulse GPIO {line} (pin={pin}) for {duration}ms"
        )
        return

    ctrl = GpiodController()
    ctrl.pulse_pin(line, duration_ms=duration)
    console.print(f"GPIO {line} ({pin}) pulsed for {duration}ms")
