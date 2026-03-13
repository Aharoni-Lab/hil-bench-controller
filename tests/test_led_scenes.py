"""Tests for LED scene engine."""

from __future__ import annotations

import pytest

from hilbench.exceptions import LedError
from hilbench.led._scenes import (
    BootingScene,
    ErrorScene,
    FlashingScene,
    IdleScene,
    OffScene,
    ProgressScene,
    RainbowScene,
    SolidScene,
    SuccessScene,
    TestingScene,
    get_scene,
    list_scenes,
)
from hilbench.led._strip import StubStrip


class TestSceneRegistry:
    def test_list_scenes_returns_all(self) -> None:
        scenes = list_scenes()
        expected = [
            "booting",
            "error",
            "flashing",
            "idle",
            "off",
            "progress",
            "rainbow",
            "solid",
            "success",
            "testing",
        ]
        assert scenes == expected

    def test_get_scene_returns_instance(self) -> None:
        scene = get_scene("idle")
        assert scene.name == "idle"

    def test_get_unknown_scene_raises(self) -> None:
        with pytest.raises(LedError, match="unknown scene"):
            get_scene("nonexistent")


class TestIdleScene:
    def test_breathing(self) -> None:
        strip = StubStrip(8)
        scene = IdleScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        assert any(p != (0, 0, 0) for p in strip.pixels)
        scene.tick(strip, 500.0)
        scene.teardown(strip)

    def test_custom_color(self) -> None:
        strip = StubStrip(4)
        scene = IdleScene()
        scene.setup(strip, {"color": [255, 0, 0], "speed": 1.0})
        scene.tick(strip, 0.0)
        # All pixels should be the same (breathing applies uniformly)
        assert all(p == strip.pixels[0] for p in strip.pixels)


class TestFlashingScene:
    def test_knight_rider(self) -> None:
        strip = StubStrip(16)
        scene = FlashingScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        # At t=0, the bright spot should be near the start
        assert strip.pixels[0] != (0, 0, 0)
        scene.tick(strip, 250.0)  # Quarter of the way through
        scene.teardown(strip)

    def test_different_times_produce_different_frames(self) -> None:
        strip = StubStrip(16)
        scene = FlashingScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        frame1 = list(strip.pixels)
        scene.tick(strip, 100.0)
        frame2 = list(strip.pixels)
        assert frame1 != frame2


class TestTestingScene:
    def test_chase(self) -> None:
        strip = StubStrip(8)
        scene = TestingScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        scene.tick(strip, 333.0)
        scene.teardown(strip)


class TestErrorScene:
    def test_pulsing(self) -> None:
        strip = StubStrip(8)
        scene = ErrorScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        # Red channel should be non-zero (pulsing red)
        assert any(p[0] > 0 for p in strip.pixels)
        scene.tick(strip, 250.0)
        assert any(p[0] > 0 for p in strip.pixels)


class TestSuccessScene:
    def test_burst_and_revert(self) -> None:
        strip = StubStrip(8)
        scene = SuccessScene()
        scene.setup(strip, {"duration_ms": 100})
        scene.tick(strip, 0.0)
        assert not scene.should_revert
        assert any(p != (0, 0, 0) for p in strip.pixels)

        scene.tick(strip, 200.0)
        assert scene.should_revert
        assert scene.revert_scene == "idle"

    def test_custom_revert(self) -> None:
        strip = StubStrip(4)
        scene = SuccessScene()
        scene.setup(strip, {"revert_to": "rainbow", "duration_ms": 50})
        scene.tick(strip, 100.0)
        assert scene.revert_scene == "rainbow"


class TestBootingScene:
    def test_sequential_fill(self) -> None:
        strip = StubStrip(8)
        scene = BootingScene()
        scene.setup(strip, {"speed": 10.0})
        scene.tick(strip, 0.0)
        # At t=0 the fill may be partial
        scene.tick(strip, 500.0)
        scene.teardown(strip)


class TestOffScene:
    def test_all_off(self) -> None:
        strip = StubStrip(8)
        # Pre-fill with some color
        strip.set_all(255, 0, 0)
        scene = OffScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        assert all(p == (0, 0, 0) for p in strip.pixels)

    def test_teardown_clears(self) -> None:
        strip = StubStrip(4)
        strip.set_all(100, 100, 100)
        scene = OffScene()
        scene.setup(strip, {})
        scene.teardown(strip)
        assert all(p == (0, 0, 0) for p in strip.pixels)


class TestSolidScene:
    def test_solid_color(self) -> None:
        strip = StubStrip(8)
        scene = SolidScene()
        scene.setup(strip, {"color": [128, 64, 32]})
        scene.tick(strip, 0.0)
        assert all(p == (128, 64, 32) for p in strip.pixels)

    def test_sets_brightness(self) -> None:
        strip = StubStrip(4)
        scene = SolidScene()
        scene.setup(strip, {"brightness": 50})
        assert strip.brightness == 50


class TestRainbowScene:
    def test_different_pixels(self) -> None:
        strip = StubStrip(16)
        scene = RainbowScene()
        scene.setup(strip, {})
        scene.tick(strip, 0.0)
        # Rainbow should produce different colors across pixels
        unique = set(strip.pixels)
        assert len(unique) > 1


class TestProgressScene:
    def test_zero_percent(self) -> None:
        strip = StubStrip(8)
        scene = ProgressScene()
        scene.setup(strip, {"percent": 0})
        scene.tick(strip, 0.0)
        # All should be background color
        assert all(p == (10, 10, 10) for p in strip.pixels)

    def test_fifty_percent(self) -> None:
        strip = StubStrip(8)
        scene = ProgressScene()
        scene.setup(strip, {"percent": 50, "color": [0, 255, 0]})
        scene.tick(strip, 0.0)
        # First 4 should be green, last 4 should be background
        assert strip.pixels[0] == (0, 255, 0)
        assert strip.pixels[3] == (0, 255, 0)
        assert strip.pixels[4] == (10, 10, 10)

    def test_hundred_percent(self) -> None:
        strip = StubStrip(4)
        scene = ProgressScene()
        scene.setup(strip, {"percent": 100, "color": [0, 255, 0]})
        scene.tick(strip, 0.0)
        assert all(p == (0, 255, 0) for p in strip.pixels)

    def test_update_percent(self) -> None:
        strip = StubStrip(8)
        scene = ProgressScene()
        scene.setup(strip, {"percent": 0})
        scene.update_percent(75)
        scene.tick(strip, 0.0)
        # 6 of 8 should be filled
        filled = sum(1 for p in strip.pixels if p != (10, 10, 10))
        assert filled == 6


class TestStubStrip:
    def test_set_pixel(self) -> None:
        strip = StubStrip(4)
        strip.set_pixel(2, 100, 200, 50)
        assert strip.pixels[2] == (100, 200, 50)
        assert strip.pixels[0] == (0, 0, 0)

    def test_set_all(self) -> None:
        strip = StubStrip(4)
        strip.set_all(10, 20, 30)
        assert all(p == (10, 20, 30) for p in strip.pixels)

    def test_show_increments(self) -> None:
        strip = StubStrip(4)
        assert strip.show_count == 0
        strip.show()
        strip.show()
        assert strip.show_count == 2

    def test_num_pixels(self) -> None:
        strip = StubStrip(32)
        assert strip.num_pixels == 32
