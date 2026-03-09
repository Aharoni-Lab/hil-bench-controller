"""Flash firmware to a target MCU."""

from __future__ import annotations

import click
from rich.console import Console

from hilbench.artifacts import resolve_firmware_path
from hilbench.probe import probe_factory
from hilbench.relay import RelayController


@click.command()
@click.option("--firmware", "-f", required=True, type=click.Path(), help="Firmware file path.")
@click.option("--target", "-t", "target_name", default=None, help="Target name from config.")
@click.option("--verify/--no-verify", default=True, help="Verify after flash.")
@click.option("--power-cycle", is_flag=True, help="Power-cycle target before flash.")
@click.pass_obj
def flash(
    ctx: object, firmware: str, target_name: str | None, verify: bool, power_cycle: bool
) -> None:
    """Flash firmware to a target MCU via probe."""
    from hilbench.cli.main import Context

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config
    name, target = cfg.get_target(target_name)

    # Resolve firmware path
    fw_path = resolve_firmware_path(firmware, workspace=cfg.paths.workspace)
    console.print(f"Target:   [bold]{name}[/bold] ({target.family})")
    console.print(f"Firmware: {fw_path}")
    console.print(f"Probe:    {target.probe.type}")

    if ctx.dry_run:
        probe = probe_factory(target.probe)
        cmd = probe.describe_command(fw_path, verify=verify)
        console.print(f"[yellow]dry-run:[/yellow] would execute: {' '.join(cmd)}")
        return

    # Optional power cycle
    if power_cycle:
        relay = RelayController(target.power)
        console.print("Power cycling target...")
        try:
            relay.power_cycle()
        except NotImplementedError:
            console.print("[yellow]warning:[/yellow] power cycle not implemented, skipping")

    # Flash
    probe = probe_factory(target.probe)
    console.print("Flashing...")

    try:
        from hilbench.publisher import on_flash_start

        on_flash_start(cfg, name, str(fw_path))
    except ImportError:
        pass

    try:
        result = probe.flash(fw_path, verify=verify)
    except Exception:
        try:
            from hilbench.publisher import on_flash_end

            on_flash_end(cfg, name, False, 0.0)
        except ImportError:
            pass
        raise

    try:
        from hilbench.publisher import on_flash_end

        on_flash_end(cfg, name, True, result.duration_s)
    except ImportError:
        pass

    console.print(f"[green]Success:[/green] {result.message} ({result.duration_s:.1f}s)")
