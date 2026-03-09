"""Serial port wrapper around pyserial."""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Protocol

import serial

from hilbench.exceptions import SerialError

if TYPE_CHECKING:
    from hilbench.config import SerialConfig

logger = logging.getLogger(__name__)


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

    def __init__(self, config: SerialConfig) -> None:
        self.config = config
        self._port: serial.Serial | None = None

    def open(self) -> None:
        if self._port is not None and self._port.is_open:
            return
        try:
            self._port = serial.Serial(
                port=str(self.config.device_path),
                baudrate=self.config.baud_rate,
                timeout=self.config.timeout,
            )
            logger.info(
                "opened serial port %s @ %d baud", self.config.device_path, self.config.baud_rate
            )
        except serial.SerialException as exc:
            raise SerialError(f"failed to open {self.config.device_path}: {exc}") from exc

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
