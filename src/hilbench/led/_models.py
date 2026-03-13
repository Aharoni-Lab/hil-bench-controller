"""Pydantic IPC models for LED daemon communication."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LedColor(BaseModel):
    """RGB color value."""

    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)

    @classmethod
    def red(cls) -> LedColor:
        return cls(r=255, g=0, b=0)

    @classmethod
    def green(cls) -> LedColor:
        return cls(r=0, g=255, b=0)

    @classmethod
    def blue(cls) -> LedColor:
        return cls(r=0, g=0, b=255)

    @classmethod
    def white(cls) -> LedColor:
        return cls(r=255, g=255, b=255)

    @classmethod
    def off(cls) -> LedColor:
        return cls(r=0, g=0, b=0)

    @classmethod
    def yellow(cls) -> LedColor:
        return cls(r=255, g=255, b=0)

    @classmethod
    def cyan(cls) -> LedColor:
        return cls(r=0, g=255, b=255)

    def to_grb_int(self) -> int:
        """Convert to 24-bit GRB integer (rpi_ws281x format)."""
        return (self.g << 16) | (self.r << 8) | self.b

    def to_rgb_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)


class SceneRequest(BaseModel):
    """Client → daemon command."""

    command: str
    scene: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class SceneResponse(BaseModel):
    """Daemon → client response."""

    ok: bool
    current_scene: str = ""
    error: str = ""


class DaemonStatus(BaseModel):
    """Daemon status info."""

    running: bool
    current_scene: str = ""
    led_count: int = 0
    uptime_s: float = 0.0
