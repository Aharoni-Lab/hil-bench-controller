"""Tests for serial I/O wrapper (mocked pyserial)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hilbench.config import SerialConfig
from hilbench.exceptions import SerialError
from hilbench.serial_io import PySerialPort


@pytest.fixture()
def serial_config() -> SerialConfig:
    return SerialConfig(device_path=Path("/dev/ttyUSB0"), baud_rate=115200, timeout=1.0)


class TestPySerialPort:
    def test_open_close(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        with patch("serial.Serial") as mock_serial:
            mock_instance = MagicMock()
            mock_instance.is_open = True
            mock_serial.return_value = mock_instance

            port.open()
            assert port._port is not None
            port.close()
            mock_instance.close.assert_called_once()

    def test_send(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        mock_port = MagicMock()
        mock_port.is_open = True
        port._port = mock_port

        port.send("hello")
        mock_port.write.assert_called_once_with(b"hello")

    def test_send_not_open(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        with pytest.raises(SerialError, match="not open"):
            port.send("hello")

    def test_read_line(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_port.readline.return_value = b"BOOT OK\r\n"
        mock_port.timeout = 1.0
        port._port = mock_port

        line = port.read_line()
        assert line == "BOOT OK"

    def test_read_line_empty(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_port.readline.return_value = b""
        mock_port.timeout = 1.0
        port._port = mock_port

        line = port.read_line()
        assert line is None

    def test_expect_match(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_port.timeout = 1.0
        # Return lines: first doesn't match, second matches
        mock_port.readline.side_effect = [b"loading...\r\n", b"BOOT OK\r\n"]
        port._port = mock_port

        result = port.expect("BOOT OK", timeout=5.0)
        assert result == "BOOT OK"

    def test_expect_timeout(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_port.timeout = 1.0
        mock_port.readline.return_value = b""
        port._port = mock_port

        with pytest.raises(SerialError, match="not seen within"):
            port.expect("NEVER", timeout=0.5)

    def test_context_manager(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        with patch("serial.Serial") as mock_serial:
            mock_instance = MagicMock()
            mock_instance.is_open = True
            mock_serial.return_value = mock_instance

            with port:
                pass
            mock_instance.close.assert_called_once()

    def test_listen_collects_lines(self, serial_config: SerialConfig) -> None:
        port = PySerialPort(serial_config)
        mock_port = MagicMock()
        mock_port.is_open = True
        mock_port.timeout = 1.0
        mock_port.readline.side_effect = [b"line1\n", b"line2\n", b""]
        port._port = mock_port

        lines = port.listen(duration=0)
        assert lines == ["line1"]
