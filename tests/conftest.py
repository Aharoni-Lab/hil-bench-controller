"""Shared test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_CONFIG = {
    "bench_name": "test-bench-01",
    "hostname": "test-bench-01",
    "runner": {"org": "test-org", "labels": ["self-hosted", "linux", "ARM64", "hil"]},
    "targets": {
        "samd51": {
            "family": "samd51",
            "probe": {
                "type": "edbg",
                "device_path": "/dev/atmel-ice-0",
            },
            "serial": {
                "device_path": "/dev/ttyUSB0",
                "baud_rate": 115200,
                "timeout": 1.0,
            },
            "gpio": {
                "reset": {"line": 17},
                "ready": {"line": 27},
                "fault": {"line": 22},
            },
            "power": {"type": "none"},
        }
    },
    "paths": {
        "workspace": "/tmp/hil-test-workspace",
        "log_dir": "/tmp/hil-test-logs",
    },
}


@pytest.fixture()
def sample_config_path(tmp_path: Path) -> Path:
    """Write sample config to a temp file and return its path."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(SAMPLE_CONFIG))
    return config_file


@pytest.fixture()
def sample_config():
    """Return a validated BenchConfig from sample data."""
    from hilbench.config import BenchConfig

    return BenchConfig.model_validate(SAMPLE_CONFIG)


@pytest.fixture()
def publisher_env(monkeypatch):
    """Set publisher env vars for testing."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-anon-key")
    monkeypatch.setenv("BENCH_EMAIL", "bench@test.com")
    monkeypatch.setenv("BENCH_PASSWORD", "test-password")
