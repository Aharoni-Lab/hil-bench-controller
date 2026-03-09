"""Health check logic for bench components."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from hilbench.probe import probe_factory

if TYPE_CHECKING:
    from hilbench.config import BenchConfig

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_config(config: BenchConfig) -> CheckResult:
    """Verify config is loaded and valid."""
    return CheckResult(name="config", passed=True, detail=f"bench={config.bench_name}")


def check_probe(config: BenchConfig) -> list[CheckResult]:
    """Check probe connectivity for each target."""
    results = []
    for name, target in config.targets.items():
        probe = probe_factory(target.probe)
        connected = probe.is_connected()
        results.append(
            CheckResult(
                name=f"probe:{name}",
                passed=connected,
                detail="connected" if connected else "not detected",
            )
        )
    return results


def check_serial(config: BenchConfig) -> list[CheckResult]:
    """Check serial device presence for each target."""
    results = []
    for name, target in config.targets.items():
        exists = Path(target.serial.device_path).exists()
        results.append(
            CheckResult(
                name=f"serial:{name}",
                passed=exists,
                detail=str(target.serial.device_path),
            )
        )
    return results


def check_gpio_chip(chip_path: str = "/dev/gpiochip4") -> CheckResult:
    """Check that the GPIO chip device exists."""
    exists = Path(chip_path).exists()
    return CheckResult(
        name="gpio_chip",
        passed=exists,
        detail=chip_path if exists else f"{chip_path} not found",
    )


def check_runner_service() -> CheckResult:
    """Check if the GitHub Actions runner service is active."""
    try:
        # Use shell=True so the glob expands to the actual service name
        # (e.g. actions.runner.MyOrg.my-bench.service).
        result = subprocess.run(
            "systemctl is-active actions.runner.*.service",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        active = result.stdout.strip() == "active"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        active = False
    return CheckResult(
        name="runner_service",
        passed=active,
        detail="active" if active else "inactive or not found",
    )


def run_all_checks(config: BenchConfig) -> list[CheckResult]:
    """Run all health checks and return results."""
    results: list[CheckResult] = []
    results.append(check_config(config))
    results.extend(check_probe(config))
    results.extend(check_serial(config))
    results.append(check_gpio_chip())
    results.append(check_runner_service())
    return results
