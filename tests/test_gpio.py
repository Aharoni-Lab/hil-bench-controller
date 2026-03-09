"""Tests for GPIO wrapper (no hardware required)."""

from __future__ import annotations

import pytest

from hilbench.config import GpioPin
from hilbench.exceptions import GpioError
from hilbench.gpio import resolve_pin


class TestResolvePin:
    def test_resolve_by_name(self) -> None:
        gpio_map = {"reset": GpioPin(line=17), "ready": GpioPin(line=27)}
        assert resolve_pin("reset", gpio_map) == 17

    def test_resolve_by_number(self) -> None:
        gpio_map = {"reset": GpioPin(line=17)}
        assert resolve_pin("22", gpio_map) == 22

    def test_resolve_unknown(self) -> None:
        gpio_map = {"reset": GpioPin(line=17)}
        with pytest.raises(GpioError, match="unknown pin"):
            resolve_pin("nonexistent", gpio_map)

    def test_resolve_empty_map(self) -> None:
        assert resolve_pin("5", {}) == 5
