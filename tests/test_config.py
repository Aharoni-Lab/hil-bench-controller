"""Tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hilbench.config import BenchConfig, load_config
from hilbench.exceptions import ConfigError


class TestBenchConfig:
    def test_valid_config(self, sample_config_path: Path) -> None:
        cfg = load_config(sample_config_path)
        assert cfg.bench_name == "test-bench-01"
        assert "samd51" in cfg.targets

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("{{{{not yaml")
        with pytest.raises(ConfigError, match="invalid YAML"):
            load_config(bad)

    def test_missing_required_field(self, tmp_path: Path) -> None:
        cfg = tmp_path / "incomplete.yaml"
        cfg.write_text(yaml.dump({"hostname": "x"}))
        with pytest.raises(ConfigError, match="validation failed"):
            load_config(cfg)

    def test_invalid_probe_type(self, tmp_path: Path) -> None:
        data = {
            "bench_name": "b",
            "targets": {
                "t": {
                    "family": "samd51",
                    "probe": {"type": "invalid", "device_path": "/dev/null"},
                    "serial": {"device_path": "/dev/null"},
                }
            },
        }
        cfg = tmp_path / "bad_probe.yaml"
        cfg.write_text(yaml.dump(data))
        with pytest.raises(ConfigError, match="validation failed"):
            load_config(cfg)

    def test_get_target_single(self, sample_config: BenchConfig) -> None:
        name, target = sample_config.get_target()
        assert name == "samd51"
        assert target.family == "samd51"

    def test_get_target_by_name(self, sample_config: BenchConfig) -> None:
        name, target = sample_config.get_target("samd51")
        assert name == "samd51"

    def test_get_target_not_found(self, sample_config: BenchConfig) -> None:
        with pytest.raises(ConfigError, match="not found"):
            sample_config.get_target("nonexistent")

    def test_get_target_ambiguous(self, tmp_path: Path) -> None:
        data = {
            "bench_name": "multi",
            "targets": {
                "a": {
                    "family": "samd51",
                    "probe": {"type": "edbg", "device_path": "/dev/null"},
                    "serial": {"device_path": "/dev/null"},
                },
                "b": {
                    "family": "samd51",
                    "probe": {"type": "edbg", "device_path": "/dev/null"},
                    "serial": {"device_path": "/dev/null"},
                },
            },
        }
        cfg = BenchConfig.model_validate(data)
        with pytest.raises(ConfigError, match="multiple targets"):
            cfg.get_target()

    def test_default_paths(self, sample_config: BenchConfig) -> None:
        assert sample_config.paths.workspace == Path("/tmp/hil-test-workspace")

    def test_serial_config_defaults(self, sample_config: BenchConfig) -> None:
        _, target = sample_config.get_target()
        assert target.serial.baud_rate == 115200
        assert target.serial.timeout == 1.0
