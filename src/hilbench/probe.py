"""Flash probe abstraction for edbg and OpenOCD."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from hilbench.exceptions import FlashError, ProbeError

if TYPE_CHECKING:
    from pathlib import Path

    from hilbench.config import ProbeConfig

logger = logging.getLogger(__name__)


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
        try:
            result = subprocess.run(
                self._base_args() + ["-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def flash(self, firmware: Path, *, verify: bool = True) -> FlashResult:
        if not firmware.exists():
            raise FlashError(f"firmware file not found: {firmware}")

        cmd = self._base_args()
        if verify:
            cmd += ["-pv"]
        else:
            cmd += ["-p"]
        cmd += ["-f", str(firmware)]

        logger.info("flashing: %s", " ".join(cmd))

        import time

        start = time.monotonic()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            elapsed = time.monotonic() - start
        except subprocess.TimeoutExpired as exc:
            raise FlashError("flash timed out after 120s") from exc
        except FileNotFoundError as exc:
            raise FlashError("edbg not found — is it installed?") from exc

        if result.returncode != 0:
            raise FlashError(f"edbg failed (rc={result.returncode}): {result.stderr.strip()}")

        return FlashResult(
            success=True,
            message=result.stdout.strip() or "flash complete",
            duration_s=elapsed,
            command=cmd,
        )


class OpenOCDProbe:
    """Flash probe via OpenOCD."""

    def __init__(self, config: ProbeConfig) -> None:
        self.config = config

    def is_connected(self) -> bool:
        try:
            result = subprocess.run(
                ["openocd", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def flash(self, firmware: Path, *, verify: bool = True) -> FlashResult:
        if not firmware.exists():
            raise FlashError(f"firmware file not found: {firmware}")

        cmd = [
            "openocd",
            "-f",
            "interface/cmsis-dap.cfg",
            "-f",
            "target/atsame5x.cfg",
            "-c",
            f"program {firmware} verify reset exit"
            if verify
            else f"program {firmware} reset exit",
        ]

        logger.info("flashing via openocd: %s", " ".join(cmd))

        import time

        start = time.monotonic()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            elapsed = time.monotonic() - start
        except subprocess.TimeoutExpired as exc:
            raise FlashError("openocd flash timed out after 120s") from exc
        except FileNotFoundError as exc:
            raise FlashError("openocd not found — is it installed?") from exc

        if result.returncode != 0:
            raise FlashError(f"openocd failed (rc={result.returncode}): {result.stderr.strip()}")

        return FlashResult(
            success=True,
            message=result.stderr.strip() or "flash complete",
            duration_s=elapsed,
            command=cmd,
        )


def probe_factory(config: ProbeConfig) -> Probe:
    """Create the appropriate probe from config."""
    match config.type:
        case "edbg":
            return EdbgProbe(config)  # type: ignore[return-value]
        case "openocd":
            return OpenOCDProbe(config)  # type: ignore[return-value]
        case _:
            raise ProbeError(f"unknown probe type: {config.type!r}")
