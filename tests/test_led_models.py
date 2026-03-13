"""Tests for LED models and config."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hilbench.config import BenchConfig, LedConfig
from hilbench.led._models import DaemonStatus, LedColor, SceneRequest, SceneResponse
from tests.conftest import SAMPLE_CONFIG


class TestLedColor:
    def test_factory_red(self) -> None:
        c = LedColor.red()
        assert c.r == 255 and c.g == 0 and c.b == 0

    def test_factory_green(self) -> None:
        c = LedColor.green()
        assert c.r == 0 and c.g == 255 and c.b == 0

    def test_factory_blue(self) -> None:
        c = LedColor.blue()
        assert c.r == 0 and c.g == 0 and c.b == 255

    def test_factory_off(self) -> None:
        c = LedColor.off()
        assert c.r == 0 and c.g == 0 and c.b == 0

    def test_factory_white(self) -> None:
        c = LedColor.white()
        assert c.r == 255 and c.g == 255 and c.b == 255

    def test_factory_yellow(self) -> None:
        c = LedColor.yellow()
        assert c.r == 255 and c.g == 255 and c.b == 0

    def test_factory_cyan(self) -> None:
        c = LedColor.cyan()
        assert c.r == 0 and c.g == 255 and c.b == 255

    def test_to_grb_int(self) -> None:
        c = LedColor(r=255, g=0, b=0)
        # GRB: g=0 << 16, r=255 << 8, b=0
        assert c.to_grb_int() == 0x00FF00

    def test_to_rgb_tuple(self) -> None:
        c = LedColor(r=10, g=20, b=30)
        assert c.to_rgb_tuple() == (10, 20, 30)

    def test_out_of_range_rejects(self) -> None:
        with pytest.raises(ValidationError):
            LedColor(r=256, g=0, b=0)
        with pytest.raises(ValidationError):
            LedColor(r=0, g=-1, b=0)


class TestSceneRequest:
    def test_minimal(self) -> None:
        req = SceneRequest(command="set_scene", scene="idle")
        assert req.command == "set_scene"
        assert req.params == {}

    def test_with_params(self) -> None:
        req = SceneRequest(command="set_scene", scene="solid", params={"color": [255, 0, 0]})
        assert req.params["color"] == [255, 0, 0]

    def test_json_round_trip(self) -> None:
        req = SceneRequest(command="set_scene", scene="rainbow", params={"speed": 2.0})
        raw = req.model_dump_json()
        restored = SceneRequest.model_validate_json(raw)
        assert restored.scene == "rainbow"
        assert restored.params["speed"] == 2.0


class TestSceneResponse:
    def test_ok(self) -> None:
        resp = SceneResponse(ok=True, current_scene="idle")
        assert resp.ok
        assert resp.error == ""

    def test_error(self) -> None:
        resp = SceneResponse(ok=False, error="unknown scene")
        assert not resp.ok


class TestDaemonStatus:
    def test_fields(self) -> None:
        status = DaemonStatus(running=True, current_scene="idle", led_count=16, uptime_s=42.5)
        assert status.running
        assert status.led_count == 16


class TestLedConfig:
    def test_defaults(self) -> None:
        cfg = LedConfig()
        assert cfg.enabled is False
        assert cfg.led_count == 16
        assert cfg.gpio_pin == 18
        assert cfg.brightness == 128
        assert cfg.fps == 30

    def test_validation_led_count(self) -> None:
        with pytest.raises(ValidationError):
            LedConfig(led_count=0)
        with pytest.raises(ValidationError):
            LedConfig(led_count=1001)

    def test_validation_brightness(self) -> None:
        with pytest.raises(ValidationError):
            LedConfig(brightness=-1)
        with pytest.raises(ValidationError):
            LedConfig(brightness=256)

    def test_bench_config_has_led(self) -> None:
        cfg = BenchConfig.model_validate(SAMPLE_CONFIG)
        assert cfg.led.enabled is False
        assert cfg.led.led_count == 16

    def test_bench_config_with_led_override(self) -> None:
        data = {**SAMPLE_CONFIG, "led": {"enabled": True, "led_count": 30}}
        cfg = BenchConfig.model_validate(data)
        assert cfg.led.enabled is True
        assert cfg.led.led_count == 30
