"""Root CLI group and global options for benchctl."""

from __future__ import annotations

from typing import Any

import click

from hilbench import __version__
from hilbench.config import load_config
from hilbench.log import setup_logging


class Context:
    """Shared CLI context passed via ``ctx.obj``."""

    def __init__(
        self,
        config_path: str | None,
        verbose: bool,
        dry_run: bool,
    ) -> None:
        self.config_path = config_path
        self.verbose = verbose
        self.dry_run = dry_run
        self.logger = setup_logging(verbose=verbose)
        self._config: Any = None

    @property
    def config(self) -> Any:
        if self._config is None:
            self._config = load_config(self.config_path)
        return self._config


@click.group()
@click.version_option(version=__version__, prog_name="benchctl")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    envvar="HIL_BENCH_CONFIG",
    help="Path to bench config YAML.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing.")
@click.pass_context
def cli(ctx: click.Context, config_path: str | None, verbose: bool, dry_run: bool) -> None:
    """benchctl — HIL bench controller for automated MCU firmware testing."""
    ctx.ensure_object(dict)
    ctx.obj = Context(config_path=config_path, verbose=verbose, dry_run=dry_run)


# ── Register subcommands ────────────────────────────────────────────────────

from hilbench.cli.config_cmd import config_cmd  # noqa: E402
from hilbench.cli.flash_cmd import flash  # noqa: E402
from hilbench.cli.gpio_cmd import gpio  # noqa: E402
from hilbench.cli.health_cmd import health  # noqa: E402
from hilbench.cli.publish_cmd import publish  # noqa: E402
from hilbench.cli.serial_cmd import serial  # noqa: E402

cli.add_command(config_cmd, "config")
cli.add_command(flash)
cli.add_command(serial)
cli.add_command(gpio)
cli.add_command(health)
cli.add_command(publish)
