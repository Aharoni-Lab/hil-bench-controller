"""Tests for publisher hook functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hilbench.config import BenchConfig
from hilbench.health import CheckResult
from hilbench.publisher import _hooks
from tests.conftest import SAMPLE_CONFIG


@pytest.fixture()
def bench_config() -> BenchConfig:
    return BenchConfig.model_validate(SAMPLE_CONFIG)


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset the module-level publisher singleton between tests."""
    _hooks._publisher = None


class TestOnFlashStart:
    def test_publishes_flashing_state(self, bench_config: BenchConfig) -> None:
        mock_pub = MagicMock()
        with patch.object(_hooks, "_get_publisher", return_value=mock_pub):
            _hooks.on_flash_start(bench_config, "samd51", "/path/to/fw.bin")
        mock_pub.publish_status.assert_called_once()
        args = mock_pub.publish_status.call_args
        assert args[1]["state"] == "flashing"

    def test_noop_when_not_configured(self, bench_config: BenchConfig) -> None:
        with patch.object(_hooks, "_get_publisher", return_value=None):
            # Should not raise
            _hooks.on_flash_start(bench_config, "samd51", "/path/to/fw.bin")


class TestOnFlashEnd:
    def test_success_publishes_idle(self, bench_config: BenchConfig) -> None:
        mock_pub = MagicMock()
        with patch.object(_hooks, "_get_publisher", return_value=mock_pub):
            _hooks.on_flash_end(bench_config, "samd51", True, 5.2)
        args = mock_pub.publish_status.call_args
        assert args[1]["state"] == "idle"

    def test_failure_publishes_error(self, bench_config: BenchConfig) -> None:
        mock_pub = MagicMock()
        with patch.object(_hooks, "_get_publisher", return_value=mock_pub):
            _hooks.on_flash_end(bench_config, "samd51", False, 0.0)
        args = mock_pub.publish_status.call_args
        assert args[1]["state"] == "error"


class TestOnHealthComplete:
    def test_all_passed(self, bench_config: BenchConfig) -> None:
        mock_pub = MagicMock()
        results = [CheckResult(name="config", passed=True, detail="ok")]
        with patch.object(_hooks, "_get_publisher", return_value=mock_pub):
            _hooks.on_health_complete(bench_config, results)
        args = mock_pub.publish_status.call_args
        assert args[1]["state"] == "idle"
        assert args[1]["healthy"] is True

    def test_some_failed(self, bench_config: BenchConfig) -> None:
        mock_pub = MagicMock()
        results = [
            CheckResult(name="config", passed=True, detail="ok"),
            CheckResult(name="probe", passed=False, detail="not found"),
        ]
        with patch.object(_hooks, "_get_publisher", return_value=mock_pub):
            _hooks.on_health_complete(bench_config, results)
        args = mock_pub.publish_status.call_args
        assert args[1]["state"] == "error"
        assert args[1]["healthy"] is False
