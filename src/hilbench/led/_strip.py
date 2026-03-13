"""LED strip hardware abstraction."""

from __future__ import annotations

from typing import Protocol


class LedStrip(Protocol):
    """Interface for addressable LED strip control."""

    @property
    def num_pixels(self) -> int: ...

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None: ...

    def set_all(self, r: int, g: int, b: int) -> None: ...

    def show(self) -> None: ...

    def set_brightness(self, brightness: int) -> None: ...


class Ws281xStrip:
    """Real WS2812B strip using rpi_ws281x."""

    def __init__(
        self,
        led_count: int,
        gpio_pin: int = 18,
        brightness: int = 128,
    ) -> None:
        from rpi_ws281x import PixelStrip  # type: ignore[import-untyped]

        self._strip = PixelStrip(led_count, gpio_pin, brightness=brightness)
        self._strip.begin()
        self._led_count = led_count

    @property
    def num_pixels(self) -> int:
        return self._led_count

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        from rpi_ws281x import Color  # type: ignore[import-untyped]

        self._strip.setPixelColor(index, Color(r, g, b))

    def set_all(self, r: int, g: int, b: int) -> None:
        for i in range(self._led_count):
            self.set_pixel(i, r, g, b)

    def show(self) -> None:
        self._strip.show()

    def set_brightness(self, brightness: int) -> None:
        self._strip.setBrightness(brightness)


class StubStrip:
    """In-memory LED strip for testing."""

    def __init__(self, led_count: int = 16) -> None:
        self._led_count = led_count
        self.pixels: list[tuple[int, int, int]] = [(0, 0, 0)] * led_count
        self.brightness: int = 128
        self.show_count: int = 0

    @property
    def num_pixels(self) -> int:
        return self._led_count

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        self.pixels[index] = (r, g, b)

    def set_all(self, r: int, g: int, b: int) -> None:
        self.pixels = [(r, g, b)] * self._led_count

    def show(self) -> None:
        self.show_count += 1

    def set_brightness(self, brightness: int) -> None:
        self.brightness = brightness
