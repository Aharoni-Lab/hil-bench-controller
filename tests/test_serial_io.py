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


class TestPortWaiting:
    def test_resolve_glob(self, tmp_path: Path) -> None:
        from hilbench.serial_io import resolve_device_path

        (tmp_path / "usb-A-if00").touch()
        assert resolve_device_path(tmp_path / "usb-*-if00") == tmp_path / "usb-A-if00"
        assert resolve_device_path(tmp_path / "none-*") == tmp_path / "none-*"
        assert resolve_device_path("/dev/ttyACM0") == Path("/dev/ttyACM0")

    def test_wait_for_port_already_present(self) -> None:
        from hilbench.serial_io import wait_for_port

        with patch("pathlib.Path.exists", return_value=True):
            assert wait_for_port("/dev/ttyACM0", timeout=1.0)

    def test_wait_for_port_appears_later(self) -> None:
        from hilbench.serial_io import wait_for_port

        with (
            patch("pathlib.Path.exists", side_effect=[False, False, True]),
            patch("time.sleep") as sleep,
        ):
            assert wait_for_port("/dev/ttyACM0", timeout=10.0)
        assert sleep.call_count == 2

    def test_wait_for_port_times_out(self) -> None:
        from hilbench.serial_io import wait_for_port

        clock = iter([0.0, 1.0, 2.0, 3.0, 11.0, 12.0])
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("time.sleep"),
            patch("time.monotonic", side_effect=lambda: next(clock)),
        ):
            assert not wait_for_port("/dev/ttyACM0", timeout=10.0)

    def test_open_retries_until_port_appears(self, serial_config: SerialConfig) -> None:
        import serial as pyserial

        port = PySerialPort(serial_config, wait_port=5.0)
        good = MagicMock()
        good.is_open = True
        with (
            patch("serial.Serial", side_effect=[pyserial.SerialException("gone"), good]) as ctor,
            patch("time.sleep"),
        ):
            port.open()
        assert ctor.call_count == 2
        assert port._port is good

    def test_open_gives_up_after_wait(self, serial_config: SerialConfig) -> None:
        import serial as pyserial

        port = PySerialPort(serial_config, wait_port=2.0)
        clock = iter([0.0, 1.0, 3.0, 4.0])
        with (
            patch("serial.Serial", side_effect=pyserial.SerialException("gone")),
            patch("time.sleep"),
            patch("time.monotonic", side_effect=lambda: next(clock)),
            pytest.raises(SerialError, match="failed to open"),
        ):
            port.open()

    def test_open_no_wait_fails_immediately(self, serial_config: SerialConfig) -> None:
        import serial as pyserial

        port = PySerialPort(serial_config)
        with (
            patch("serial.Serial", side_effect=pyserial.SerialException("gone")) as ctor,
            pytest.raises(SerialError),
        ):
            port.open()
        assert ctor.call_count == 1
