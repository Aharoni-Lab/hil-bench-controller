"""LED subcommands: set-scene, off, list-scenes, status, daemon."""

from __future__ import annotations

import click
from rich.console import Console


@click.group()
def led() -> None:
    """Addressable RGB LED strip control."""


@led.command("set-scene")
@click.argument("name")
@click.option("--color", "-c", default=None, help="RGB color as R,G,B (e.g. 255,0,0).")
@click.option("--speed", "-s", type=float, default=None, help="Animation speed multiplier.")
@click.option("--brightness", "-b", type=int, default=None, help="Strip brightness (0-255).")
@click.option("--percent", "-p", type=float, default=None, help="Progress percent (0-100).")
@click.pass_obj
def set_scene(
    ctx: object,
    name: str,
    color: str | None,
    speed: float | None,
    brightness: int | None,
    percent: float | None,
) -> None:
    """Set the active LED scene."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()

    params: dict[str, object] = {}
    if color is not None:
        parts = color.split(",")
        if len(parts) == 3:
            params["color"] = [int(p.strip()) for p in parts]
    if speed is not None:
        params["speed"] = speed
    if brightness is not None:
        params["brightness"] = brightness
    if percent is not None:
        params["percent"] = percent

    if ctx.dry_run:
        console.print(f"[yellow]dry-run:[/yellow] would set LED scene to {name!r} params={params}")
        return

    from hilbench.led import LedClient

    client = LedClient(ctx.config.led.socket_path)
    resp = client.set_scene(name, params)
    if resp.ok:
        console.print(f"LED scene → [bold]{resp.current_scene}[/bold]")
    else:
        console.print(f"[red]Error:[/red] {resp.error}")
        raise SystemExit(1)


@led.command()
@click.pass_obj
def off(ctx: object) -> None:
    """Turn off all LEDs."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()

    if ctx.dry_run:
        console.print("[yellow]dry-run:[/yellow] would turn off LEDs")
        return

    from hilbench.led import LedClient

    client = LedClient(ctx.config.led.socket_path)
    resp = client.off()
    if resp.ok:
        console.print("LEDs off")
    else:
        console.print(f"[red]Error:[/red] {resp.error}")
        raise SystemExit(1)


@led.command("list-scenes")
def list_scenes_cmd() -> None:
    """List available LED scenes."""
    from hilbench.led._scenes import list_scenes

    console = Console()
    scenes = list_scenes()
    for s in scenes:
        console.print(f"  {s}")


@led.command()
@click.pass_obj
def status(ctx: object) -> None:
    """Show LED daemon status."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()

    from hilbench.led import LedClient

    client = LedClient(ctx.config.led.socket_path)
    if not client.is_daemon_running():
        console.print("[yellow]LED daemon is not running[/yellow]")
        return

    st = client.status()
    console.print(f"Running:  {st.running}")
    console.print(f"Scene:    {st.current_scene}")
    console.print(f"LEDs:     {st.led_count}")
    console.print(f"Uptime:   {st.uptime_s:.0f}s")


@led.command()
@click.option("--stub", is_flag=True, help="Use stub strip (no hardware).")
@click.pass_obj
def daemon(ctx: object, stub: bool) -> None:
    """Start the LED animation daemon (for systemd ExecStart)."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config.led

    if ctx.dry_run:
        console.print("[yellow]dry-run:[/yellow] would start LED daemon")
        return

    from hilbench.led._daemon import LedDaemon

    d = LedDaemon(
        led_count=cfg.led_count,
        gpio_pin=cfg.gpio_pin,
        brightness=cfg.brightness,
        fps=cfg.fps,
        socket_path=str(cfg.socket_path),
        use_stub=stub,
    )
    d.run()
