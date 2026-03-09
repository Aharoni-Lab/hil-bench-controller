"""Serial communication subcommands: listen, send, expect."""

from __future__ import annotations

import click
from rich.console import Console

from hilbench.serial_io import PySerialPort


@click.group()
def serial() -> None:
    """Serial port communication with targets."""


@serial.command()
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.option("--duration", "-d", type=float, default=10.0, help="Listen duration in seconds.")
@click.pass_obj
def listen(ctx: object, target_name: str | None, duration: float) -> None:
    """Listen to serial output from a target."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)

    if ctx.dry_run:
        console.print(
            f"[yellow]dry-run:[/yellow] would listen on {target.serial.device_path} "
            f"@ {target.serial.baud_rate} baud for {duration}s"
        )
        return

    port = PySerialPort(target.serial)
    console.print(
        f"Listening on [bold]{target.serial.device_path}[/bold] "
        f"@ {target.serial.baud_rate} baud ({duration}s)..."
    )
    with port:
        lines = port.listen(duration=duration, callback=lambda line: console.print(line))
    console.print(f"\n[dim]{len(lines)} lines received[/dim]")


@serial.command()
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.argument("data")
@click.pass_obj
def send(ctx: object, target_name: str | None, data: str) -> None:
    """Send data to target serial port."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)

    if ctx.dry_run:
        console.print(
            f"[yellow]dry-run:[/yellow] would send {data!r} to {target.serial.device_path}"
        )
        return

    port = PySerialPort(target.serial)
    with port:
        port.send(data + "\n")
    console.print(f"Sent to {name}: {data!r}")


@serial.command()
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.option("--pattern", "-p", required=True, help="Regex pattern to match.")
@click.option("--timeout", type=float, default=10.0, help="Timeout in seconds.")
@click.pass_obj
def expect(ctx: object, target_name: str | None, pattern: str, timeout: float) -> None:
    """Wait for a serial line matching a regex pattern."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)

    if ctx.dry_run:
        console.print(
            f"[yellow]dry-run:[/yellow] would wait for {pattern!r} on "
            f"{target.serial.device_path} (timeout={timeout}s)"
        )
        return

    port = PySerialPort(target.serial)
    console.print(f"Waiting for [bold]{pattern}[/bold] on {name} (timeout={timeout}s)...")
    with port:
        matched = port.expect(pattern, timeout=timeout)
    console.print(f"[green]Matched:[/green] {matched}")
