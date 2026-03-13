"""Pydantic v2 configuration models and YAML loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, Field, field_validator

DEFAULT_CONFIG_PATH = Path("/etc/hil-bench/config.yaml")
ENV_CONFIG_VAR = "HIL_BENCH_CONFIG"


# ── Sub-models ──────────────────────────────────────────────────────────────


class RunnerConfig(BaseModel):
    labels: list[str] = Field(default_factory=lambda: ["self-hosted", "linux", "ARM64", "hil"])


class GpioPin(BaseModel):
    line: int = Field(ge=0)


class ProbeConfig(BaseModel):
    type: str = Field(description="Probe type: edbg or openocd")
    device_path: Path = Path("/dev/atmel-ice-0")
    serial_number: str | None = None

    @field_validator("type")
    @classmethod
    def validate_probe_type(cls, v: str) -> str:
        allowed = {"edbg", "openocd"}
        if v not in allowed:
            msg = f"probe type must be one of {allowed}, got {v!r}"
            raise ValueError(msg)
        return v


class SerialConfig(BaseModel):
    device_path: Path
    baud_rate: Annotated[int, Field(gt=0)] = 115200
    timeout: Annotated[float, Field(gt=0)] = 1.0


class PowerConfig(BaseModel):
    type: str = "none"
    relay_pin: GpioPin | None = None

    @field_validator("type")
    @classmethod
    def validate_power_type(cls, v: str) -> str:
        allowed = {"none", "relay"}
        if v not in allowed:
            msg = f"power type must be one of {allowed}, got {v!r}"
            raise ValueError(msg)
        return v


class TargetConfig(BaseModel):
    family: str
    probe: ProbeConfig
    serial: SerialConfig
    gpio: dict[str, GpioPin] = Field(default_factory=dict)
    power: PowerConfig = PowerConfig()


class PathsConfig(BaseModel):
    workspace: Path = Path("/opt/hil-bench")
    log_dir: Path = Path("/var/log/hil-bench")


class WikiConfig(BaseModel):
    canonical_url: str | None = None


class LedConfig(BaseModel):
    enabled: bool = False
    led_count: int = Field(default=16, ge=1, le=1000)
    gpio_pin: int = Field(default=18, ge=0)
    brightness: int = Field(default=128, ge=0, le=255)
    fps: int = Field(default=30, ge=1, le=120)
    socket_path: Path = Path("/run/hil-bench/led.sock")


# ── Root model ──────────────────────────────────────────────────────────────


class BenchConfig(BaseModel):
    bench_name: str
    hostname: str | None = None
    runner: RunnerConfig = RunnerConfig()
    targets: dict[str, TargetConfig]
    paths: PathsConfig = PathsConfig()
    wiki: WikiConfig = WikiConfig()
    led: LedConfig = LedConfig()

    def get_target(self, name: str | None = None) -> tuple[str, TargetConfig]:
        """Return (name, config) for the named target, or the only target if name is None."""
        if name is not None:
            if name not in self.targets:
                from hilbench.exceptions import ConfigError

                msg = f"target {name!r} not found; available: {list(self.targets)}"
                raise ConfigError(msg)
            return name, self.targets[name]
        if len(self.targets) == 1:
            name = next(iter(self.targets))
            return name, self.targets[name]
        from hilbench.exceptions import ConfigError

        msg = f"multiple targets configured; use --target to choose: {list(self.targets)}"
        raise ConfigError(msg)


# ── Loader ──────────────────────────────────────────────────────────────────


def resolve_config_path(cli_path: str | Path | None = None) -> Path:
    """Resolve config path from CLI flag → env var → default."""
    if cli_path is not None:
        return Path(cli_path)
    env = os.environ.get(ENV_CONFIG_VAR)
    if env:
        return Path(env)
    return DEFAULT_CONFIG_PATH


def load_config(path: str | Path | None = None) -> BenchConfig:
    """Load and validate config from YAML file."""
    from hilbench.exceptions import ConfigError

    resolved = resolve_config_path(path)
    if not resolved.exists():
        msg = f"config file not found: {resolved}"
        raise ConfigError(msg)
    try:
        raw = yaml.safe_load(resolved.read_text())
    except yaml.YAMLError as exc:
        msg = f"invalid YAML in {resolved}: {exc}"
        raise ConfigError(msg) from exc
    if not isinstance(raw, dict):
        msg = f"config must be a YAML mapping, got {type(raw).__name__}"
        raise ConfigError(msg)
    try:
        return BenchConfig.model_validate(raw)
    except Exception as exc:
        msg = f"config validation failed: {exc}"
        raise ConfigError(msg) from exc
