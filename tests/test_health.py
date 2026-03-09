"""Tests for health check logic."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from hilbench.health import (
    check_config,
    check_gpio_chip,
    check_runner_service,
    run_all_checks,
)

if TYPE_CHECKING:
    from hilbench.config import BenchConfig


class TestHealthChecks:
    def test_check_config(self, sample_config: BenchConfig) -> None:
        result = check_config(sample_config)
        assert result.passed
        assert "test-bench-01" in result.detail

    def test_check_gpio_chip_missing(self) -> None:
        result = check_gpio_chip("/dev/nonexistent-chip")
        assert not result.passed

    def test_check_runner_service_not_running(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"stdout": "inactive"})()
            result = check_runner_service()
            assert not result.passed

    def test_run_all_checks(self, sample_config: BenchConfig) -> None:
        with patch("hilbench.health.probe_factory") as mock_pf:
            mock_probe = type("P", (), {"is_connected": lambda self: False})()
            mock_pf.return_value = mock_probe
            results = run_all_checks(sample_config)

        assert len(results) >= 4
        names = [r.name for r in results]
        assert "config" in names
