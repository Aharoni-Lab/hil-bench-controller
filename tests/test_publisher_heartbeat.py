"""Tests for publisher heartbeat loop."""

from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

import pytest

from hilbench.config import BenchConfig
from hilbench.health import CheckResult
from hilbench.publisher._heartbeat import run_heartbeat_loop
from tests.conftest import SAMPLE_CONFIG


@pytest.fixture()
def bench_config() -> BenchConfig:
    return BenchConfig.model_validate(SAMPLE_CONFIG)


class TestHeartbeatLoop:
    def test_runs_and_stops_on_signal(self, bench_config: BenchConfig) -> None:
        """Heartbeat loop runs one iteration then stops when signalled."""
        mock_publisher = MagicMock()
        iteration_count = 0

        def mock_run_all_checks(cfg: object) -> list[CheckResult]:
            nonlocal iteration_count
            iteration_count += 1
            # After first iteration, simulate SIGTERM
            if iteration_count >= 1:
                signal.raise_signal(signal.SIGTERM)
            return [CheckResult(name="config", passed=True, detail="ok")]

        with (
            patch("hilbench.health.run_all_checks", side_effect=mock_run_all_checks),
            patch("hilbench.publisher._heartbeat.time.sleep"),
        ):
            run_heartbeat_loop(mock_publisher, bench_config, interval_s=1)

        assert iteration_count >= 1
        mock_publisher.publish_status.assert_called()
        mock_publisher.close.assert_called_once()

    def test_continues_on_exception(self, bench_config: BenchConfig) -> None:
        """Heartbeat loop continues even if an iteration fails."""
        mock_publisher = MagicMock()
        call_count = 0

        def mock_run_all_checks(cfg: object) -> list[CheckResult]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient error")
            signal.raise_signal(signal.SIGTERM)
            return [CheckResult(name="config", passed=True, detail="ok")]

        with (
            patch("hilbench.health.run_all_checks", side_effect=mock_run_all_checks),
            patch("hilbench.publisher._heartbeat.time.sleep"),
        ):
            run_heartbeat_loop(mock_publisher, bench_config, interval_s=1)

        assert call_count >= 2
        mock_publisher.close.assert_called_once()
