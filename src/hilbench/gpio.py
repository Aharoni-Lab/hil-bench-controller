"""GPIO wrapper using libgpiod (gpiod) — Pi 5 compatible."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Protocol

import gpiod
from gpiod.line import Direction, Value

from hilbench.exceptions import GpioError

if TYPE_CHECKING:
    from hilbench.config import GpioPin

logger = logging.getLogger(__name__)

DEFAULT_CHIP = "/dev/gpiochip4"  # Pi 5 main GPIO chip


class GpioController(Protocol):
    """Interface for GPIO operations."""

    def set_pin(self, line: int, high: bool) -> None: ...

    def get_pin(self, line: int) -> bool: ...

    def pulse_pin(self, line: int, duration_ms: int = 100) -> None: ...


class GpiodController:
    """Real GPIO controller using libgpiod."""

    def __init__(self, chip_path: str = DEFAULT_CHIP, consumer: str = "hilbench") -> None:
        self.chip_path = chip_path
        self.consumer = consumer

    def set_pin(self, line: int, high: bool) -> None:
        value = Value.ACTIVE if high else Value.INACTIVE
        try:
            request = gpiod.request_lines(
                self.chip_path,
                consumer=self.consumer,
                config={line: gpiod.LineSettings(direction=Direction.OUTPUT)},
            )
            with request:
                request.set_value(line, value)
            logger.info("GPIO %d → %s", line, "HIGH" if high else "LOW")
        except OSError as exc:
            raise GpioError(f"failed to set GPIO {line}: {exc}") from exc

    def get_pin(self, line: int) -> bool:
        try:
            request = gpiod.request_lines(
                self.chip_path,
                consumer=self.consumer,
                config={line: gpiod.LineSettings(direction=Direction.INPUT)},
            )
            with request:
                val = request.get_value(line)
            result = val == Value.ACTIVE
            logger.debug("GPIO %d = %s", line, "HIGH" if result else "LOW")
            return result
        except OSError as exc:
            raise GpioError(f"failed to read GPIO {line}: {exc}") from exc

    def pulse_pin(self, line: int, duration_ms: int = 100) -> None:
        try:
            request = gpiod.request_lines(
                self.chip_path,
                consumer=self.consumer,
                config={line: gpiod.LineSettings(direction=Direction.OUTPUT)},
            )
            with request:
                request.set_value(line, Value.ACTIVE)
                time.sleep(duration_ms / 1000.0)
                request.set_value(line, Value.INACTIVE)
            logger.info("GPIO %d pulsed for %d ms", line, duration_ms)
        except OSError as exc:
            raise GpioError(f"failed to pulse GPIO {line}: {exc}") from exc


def resolve_pin(name_or_num: str, gpio_map: dict[str, GpioPin]) -> int:
    """Resolve a pin name (from config) or raw number to a GPIO line number."""
    if name_or_num in gpio_map:
        return gpio_map[name_or_num].line
    try:
        return int(name_or_num)
    except ValueError:
        available = list(gpio_map.keys())
        raise GpioError(f"unknown pin {name_or_num!r}; available names: {available}") from None
