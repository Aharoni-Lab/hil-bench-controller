"""Flash probe abstraction for edbg and OpenOCD."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from hilbench.exceptions import FlashError, ProbeError

if TYPE_CHECKING:
    from pathlib import Path

    from hilbench.config import ProbeConfig

logger = logging.getLogger(__name__)

_FLASH_TIMEOUT = 120


@dataclass
class FlashResult:
    success: bool
    message: str
    duration_s: float = 0.0
    command: list[str] = field(default_factory=list)


class Probe(Protocol):
    """Interface for flash probes."""

    def flash(self, firmware: Path, *, verify: bool = True) -> FlashResult: ...

    def is_connected(self) -> bool: ...

    def describe_command(self, firmware: Path, *, verify: bool = True) -> list[str]: ...


def _subprocess_ok(cmd: list[str], timeout: int = 5) -> bool:
    """Return True if *cmd* exits with returncode 0 within *timeout*."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _run_flash(
    cmd: list[str], tool_name: str, *, output_field: str = "stdout"
) -> FlashResult:
    """Run a flash subprocess and return a ``FlashResult``.

    *output_field* selects which stream (``"stdout"`` or ``"stderr"``)
    contains the tool's primary output message.
    """
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_FLASH_TIMEOUT
        )
        elapsed = time.monotonic() - start
    except subprocess.TimeoutExpired as exc:
        raise FlashError(f"{tool_name} flash timed out after {_FLASH_TIMEOUT}s") from exc
    except FileNotFoundError as exc:
        raise FlashError(f"{tool_name} not found — is it installed?") from exc

    if result.returncode != 0:
        raise FlashError(
            f"{tool_name} failed (rc={result.returncode}): {result.stderr.strip()}"
        )

    msg = getattr(result, output_field).strip() or "flash complete"
    return FlashResult(success=True, message=msg, duration_s=elapsed, command=cmd)


class EdbgProbe:
    """Atmel-ICE probe via the ``edbg`` command-line tool."""

    def __init__(self, config: ProbeConfig) -> None:
        self.config = config

    def _base_args(self) -> list[str]:
        args = ["edbg", "-t", "samd51"]
        if self.config.serial_number:
            args += ["-s", self.config.serial_number]
        return args

    def is_connected(self) -> bool:
        return _subprocess_ok(self._base_args() + ["-l"])

    def describe_command(self, firmware: Path, *, verify: bool = True) -> list[str]:
        cmd = self._base_args()
        cmd += ["-pv"] if verify else ["-p"]
        cmd += ["-f", str(firmware)]
        return cmd

    def flash(self, firmware: Path, *, verify: bool = True) -> FlashResult:
        cmd = self.describe_command(firmware, verify=verify)
        logger.info("flashing: %s", " ".join(cmd))
        return _run_flash(cmd, "edbg", output_field="stdout")


class OpenOCDProbe:
    """Flash probe via OpenOCD."""

    def __init__(self, config: ProbeConfig) -> None:
        self.config = config

    def is_connected(self) -> bool:
        return _subprocess_ok(["openocd", "--version"])

    def describe_command(self, firmware: Path, *, verify: bool = True) -> list[str]:
        program_arg = (
            f"program {firmware} verify reset exit"
            if verify
            else f"program {firmware} reset exit"
        )
        return [
            "openocd",
            "-f", "interface/cmsis-dap.cfg",
            "-f", "target/atsame5x.cfg",
            "-c", program_arg,
        ]

    def flash(self, firmware: Path, *, verify: bool = True) -> FlashResult:
        cmd = self.describe_command(firmware, verify=verify)
        logger.info("flashing via openocd: %s", " ".join(cmd))
        return _run_flash(cmd, "openocd", output_field="stderr")


def probe_factory(config: ProbeConfig) -> Probe:
    """Create the appropriate probe from config."""
    match config.type:
        case "edbg":
            return EdbgProbe(config)
        case "openocd":
            return OpenOCDProbe(config)
        case _:
            raise ProbeError(f"unknown probe type: {config.type!r}")
