"""Serial port wrapper around pyserial."""

from __future__ import annotations

import glob
import logging
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import serial

from hilbench.exceptions import SerialError

if TYPE_CHECKING:
    from hilbench.config import SerialConfig

logger = logging.getLogger(__name__)

_GLOB_CHARS = frozenset("*?[")


def resolve_device_path(path: Path | str) -> Path:
    """Resolve a device path that may contain a glob (e.g. ``/dev/serial/by-id/usb-*-if00``).

    Returns the first sorted match, or the path unchanged when it has no glob
    characters or nothing matches (so callers can report the original path).
    """
    text = str(path)
    if not _GLOB_CHARS.intersection(text):
        return Path(text)
    matches = sorted(glob.glob(text))
    return Path(matches[0]) if matches else Path(text)


def device_present(path: Path | str) -> bool:
    """Return True if the (possibly globbed) device path currently exists."""
    return resolve_device_path(path).exists()


def wait_for_port(path: Path | str, timeout: float = 10.0, poll_interval: float = 0.25) -> bool:
    """Wait up to *timeout* seconds for a device path to (re)appear.

    Used after flashing a chip whose USB Serial/JTAG port re-enumerates on
    reset. Returns True if the path exists before the deadline.
    """
    deadline = time.monotonic() + timeout
    while True:
        if device_present(path):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)


class SerialPort(Protocol):
    """Interface for serial communication."""

    def open(self) -> None: ...

    def close(self) -> None: ...

    def send(self, data: str) -> None: ...

    def read_line(self, timeout: float | None = None) -> str | None: ...

    def expect(self, pattern: str, timeout: float = 10.0) -> str: ...

    def listen(self, duration: float = 0.0, callback: object = None) -> list[str]: ...


class PySerialPort:
    """Real serial port using pyserial."""

    def __init__(self, config: SerialConfig, wait_port: float = 0.0) -> None:
        self.config = config
        self.wait_port = wait_port
        self._port: serial.Serial | None = None

    def open(self) -> None:
        """Open the port, retrying for up to ``wait_port`` seconds if it is not there yet."""
        if self._port is not None and self._port.is_open:
            return
        deadline = time.monotonic() + self.wait_port
        while True:
            device = resolve_device_path(self.config.device_path)
            try:
                self._port = serial.Serial(
                    port=str(device),
                    baudrate=self.config.baud_rate,
                    timeout=self.config.timeout,
                )
                logger.info("opened serial port %s @ %d baud", device, self.config.baud_rate)
                return
            except (serial.SerialException, OSError) as exc:
                if time.monotonic() >= deadline:
                    raise SerialError(f"failed to open {self.config.device_path}: {exc}") from exc
                logger.debug("port %s not ready (%s); retrying", device, exc)
                time.sleep(0.25)

    def close(self) -> None:
        if self._port is not None and self._port.is_open:
            self._port.close()
            logger.debug("closed serial port")

    def send(self, data: str) -> None:
        if self._port is None or not self._port.is_open:
            raise SerialError("serial port not open")
        self._port.write(data.encode())
        self._port.flush()
        logger.debug("sent: %r", data)

    def read_line(self, timeout: float | None = None) -> str | None:
        if self._port is None or not self._port.is_open:
            raise SerialError("serial port not open")
        old_timeout = self._port.timeout
        if timeout is not None:
            self._port.timeout = timeout
        try:
            raw = self._port.readline()
            if raw:
                return raw.decode(errors="replace").rstrip("\r\n")
            return None
        finally:
            self._port.timeout = old_timeout

    def expect(self, pattern: str, timeout: float = 10.0) -> str:
        """Read lines until one matches ``pattern`` (regex) or timeout expires."""
        regex = re.compile(pattern)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            line = self.read_line(timeout=min(remaining, 0.5))
            if line is not None:
                logger.debug("rx: %s", line)
                if regex.search(line):
                    return line
        raise SerialError(f"pattern {pattern!r} not seen within {timeout}s")

    def listen(self, duration: float = 0.0, callback: object = None) -> list[str]:
        """Read lines for ``duration`` seconds (0 = one read cycle). Return collected lines."""
        lines: list[str] = []
        deadline = time.monotonic() + duration if duration > 0 else 0.0
        while True:
            line = self.read_line(timeout=0.5)
            if line is not None:
                lines.append(line)
                if callable(callback):
                    callback(line)
            if duration <= 0:
                break
            if time.monotonic() >= deadline:
                break
        return lines

    def __enter__(self) -> PySerialPort:
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
