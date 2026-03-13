"""Scene system for LED animations."""

from __future__ import annotations

import colorsys
import math
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from hilbench.led._strip import LedStrip


class Scene(Protocol):
    """Interface for LED animation scenes."""

    @property
    def name(self) -> str: ...

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None: ...

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None: ...

    def teardown(self, strip: LedStrip) -> None: ...


# ── Registry ────────────────────────────────────────────────────────────────

_SCENE_REGISTRY: dict[str, type[Scene]] = {}


def register_scene(cls: type[Scene]) -> type[Scene]:
    """Decorator to register a scene class."""
    instance = cls()
    _SCENE_REGISTRY[instance.name] = cls
    return cls


def get_scene(name: str) -> Scene:
    """Create a scene instance by name."""
    if name not in _SCENE_REGISTRY:
        from hilbench.exceptions import LedError

        msg = f"unknown scene {name!r}; available: {list_scenes()}"
        raise LedError(msg)
    return _SCENE_REGISTRY[name]()


def list_scenes() -> list[str]:
    """Return sorted list of registered scene names."""
    return sorted(_SCENE_REGISTRY.keys())


# ── Helpers ─────────────────────────────────────────────────────────────────


def _parse_color(params: dict[str, Any], default: tuple[int, int, int]) -> tuple[int, int, int]:
    """Extract (r,g,b) from params['color'] which may be a list or dict."""
    raw = params.get("color")
    if raw is None:
        return default
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        return (int(raw[0]), int(raw[1]), int(raw[2]))
    if isinstance(raw, dict):
        return (int(raw.get("r", 0)), int(raw.get("g", 0)), int(raw.get("b", 0)))
    return default


def _clamp(value: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, value))


# ── Built-in scenes ────────────────────────────────────────────────────────


@register_scene
class IdleScene:
    """Slow sine-wave breathing, dim to bright."""

    @property
    def name(self) -> str:
        return "idle"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (0, 80, 200))
        self._speed = float(params.get("speed", 0.5))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        t = elapsed_ms / 1000.0
        brightness = 0.15 + 0.85 * ((math.sin(2 * math.pi * self._speed * t) + 1) / 2)
        r = _clamp(int(self._color[0] * brightness))
        g = _clamp(int(self._color[1] * brightness))
        b = _clamp(int(self._color[2] * brightness))
        strip.set_all(r, g, b)

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class FlashingScene:
    """Knight-rider sweep back and forth."""

    @property
    def name(self) -> str:
        return "flashing"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (255, 165, 0))
        self._speed = float(params.get("speed", 2.0))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        n = strip.num_pixels
        t = elapsed_ms / 1000.0
        cycle = (t * self._speed) % 2.0
        pos = cycle if cycle < 1.0 else 2.0 - cycle
        center = pos * (n - 1)

        for i in range(n):
            dist = abs(i - center)
            intensity = max(0.0, 1.0 - dist / 3.0)
            r = _clamp(int(self._color[0] * intensity))
            g = _clamp(int(self._color[1] * intensity))
            b = _clamp(int(self._color[2] * intensity))
            strip.set_pixel(i, r, g, b)

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class TestingScene:
    """Chase pattern — segments moving along strip."""

    @property
    def name(self) -> str:
        return "testing"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (0, 200, 255))
        self._speed = float(params.get("speed", 3.0))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        n = strip.num_pixels
        t = elapsed_ms / 1000.0
        offset = t * self._speed

        for i in range(n):
            phase = ((i + offset) % 4) / 4.0
            intensity = max(0.0, 1.0 - phase * 2)
            r = _clamp(int(self._color[0] * intensity))
            g = _clamp(int(self._color[1] * intensity))
            b = _clamp(int(self._color[2] * intensity))
            strip.set_pixel(i, r, g, b)

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class ErrorScene:
    """Red pulsing/flashing alert."""

    @property
    def name(self) -> str:
        return "error"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (255, 0, 0))
        self._speed = float(params.get("speed", 2.0))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        t = elapsed_ms / 1000.0
        pulse = (math.sin(2 * math.pi * self._speed * t) + 1) / 2
        intensity = 0.3 + 0.7 * pulse
        r = _clamp(int(self._color[0] * intensity))
        g = _clamp(int(self._color[1] * intensity))
        b = _clamp(int(self._color[2] * intensity))
        strip.set_all(r, g, b)

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class SuccessScene:
    """Green burst, auto-reverts to idle."""

    @property
    def name(self) -> str:
        return "success"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (0, 255, 0))
        self._duration_ms = float(params.get("duration_ms", 3000))
        self._revert_to = str(params.get("revert_to", "idle"))
        self._reverted = False

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        if elapsed_ms >= self._duration_ms:
            if not self._reverted:
                self._reverted = True
            return
        progress = elapsed_ms / self._duration_ms
        intensity = max(0.0, 1.0 - progress * 0.5)
        r = _clamp(int(self._color[0] * intensity))
        g = _clamp(int(self._color[1] * intensity))
        b = _clamp(int(self._color[2] * intensity))
        strip.set_all(r, g, b)

    @property
    def should_revert(self) -> bool:
        return self._reverted

    @property
    def revert_scene(self) -> str:
        return self._revert_to

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class BootingScene:
    """Sequential fill from one end."""

    @property
    def name(self) -> str:
        return "booting"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (0, 100, 255))
        self._speed = float(params.get("speed", 1.0))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        n = strip.num_pixels
        t = elapsed_ms / 1000.0
        filled = int((t * self._speed * n) % (n + 1))
        filled = min(filled, n)

        for i in range(n):
            if i < filled:
                strip.set_pixel(i, *self._color)
            else:
                strip.set_pixel(i, 0, 0, 0)

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class OffScene:
    """All pixels off."""

    @property
    def name(self) -> str:
        return "off"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        pass

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        strip.set_all(0, 0, 0)

    def teardown(self, strip: LedStrip) -> None:
        strip.set_all(0, 0, 0)


@register_scene
class SolidScene:
    """Static single color."""

    @property
    def name(self) -> str:
        return "solid"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (255, 255, 255))
        if "brightness" in params:
            strip.set_brightness(int(params["brightness"]))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        strip.set_all(*self._color)

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class RainbowScene:
    """HSV rainbow cycling across strip."""

    @property
    def name(self) -> str:
        return "rainbow"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._speed = float(params.get("speed", 0.5))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        n = strip.num_pixels
        t = elapsed_ms / 1000.0

        for i in range(n):
            hue = (i / n + t * self._speed) % 1.0
            r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            strip.set_pixel(i, int(r_f * 255), int(g_f * 255), int(b_f * 255))

    def teardown(self, strip: LedStrip) -> None:
        pass


@register_scene
class ProgressScene:
    """LED bar graph proportional to percent."""

    @property
    def name(self) -> str:
        return "progress"

    def setup(self, strip: LedStrip, params: dict[str, Any]) -> None:
        self._color = _parse_color(params, (0, 255, 0))
        self._bg_color = _parse_color(
            {"color": params.get("bg_color")}, (10, 10, 10)
        )
        self._percent = float(params.get("percent", 0))

    def tick(self, strip: LedStrip, elapsed_ms: float) -> None:
        n = strip.num_pixels
        filled = int(n * self._percent / 100.0)
        filled = max(0, min(n, filled))

        for i in range(n):
            if i < filled:
                strip.set_pixel(i, *self._color)
            else:
                strip.set_pixel(i, *self._bg_color)

    def update_percent(self, percent: float) -> None:
        self._percent = max(0.0, min(100.0, percent))

    def teardown(self, strip: LedStrip) -> None:
        pass
