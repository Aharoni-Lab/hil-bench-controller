"""Tests for probe flash abstraction (mocked subprocess)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from hilbench.config import ProbeConfig
from hilbench.exceptions import FlashError
from hilbench.probe import EdbgProbe, EsptoolProbe, OpenOCDProbe, probe_factory


@pytest.fixture()
def edbg_config() -> ProbeConfig:
    return ProbeConfig(type="edbg", device_path=Path("/dev/atmel-ice-0"))


@pytest.fixture()
def openocd_config() -> ProbeConfig:
    return ProbeConfig(type="openocd", device_path=Path("/dev/null"))


class TestEdbgProbe:
    def test_flash_success(self, edbg_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "test.bin"
        fw.write_bytes(b"\x00" * 100)
        probe = EdbgProbe(edbg_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="Done.", stderr=""
            )
            result = probe.flash(fw)

        assert result.success
        assert result.duration_s >= 0

    def test_flash_failure(self, edbg_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "test.bin"
        fw.write_bytes(b"\x00")
        probe = EdbgProbe(edbg_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="No target found"
            )
            with pytest.raises(FlashError, match="edbg failed"):
                probe.flash(fw)

    def test_flash_timeout(self, edbg_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "test.bin"
        fw.write_bytes(b"\x00")
        probe = EdbgProbe(edbg_config)

        with (
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("edbg", 120)),
            pytest.raises(FlashError, match="timed out"),
        ):
            probe.flash(fw)

    def test_flash_missing_firmware(self, edbg_config: ProbeConfig) -> None:
        probe = EdbgProbe(edbg_config)
        with pytest.raises(FlashError, match="not found"):
            probe.flash(Path("/nonexistent/firmware.bin"))

    def test_flash_edbg_not_installed(self, edbg_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "test.bin"
        fw.write_bytes(b"\x00")
        probe = EdbgProbe(edbg_config)

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(FlashError, match="not found"),
        ):
            probe.flash(fw)

    def test_is_connected(self, edbg_config: ProbeConfig) -> None:
        probe = EdbgProbe(edbg_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            assert probe.is_connected()

    def test_is_not_connected(self, edbg_config: ProbeConfig) -> None:
        probe = EdbgProbe(edbg_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr=""
            )
            assert not probe.is_connected()

    def test_serial_number_in_args(self) -> None:
        config = ProbeConfig(
            type="edbg", device_path=Path("/dev/null"), serial_number="J41800000000"
        )
        probe = EdbgProbe(config)
        args = probe._base_args()
        assert "-s" in args
        assert "J41800000000" in args


class TestOpenOCDProbe:
    def test_flash_success(self, openocd_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "test.bin"
        fw.write_bytes(b"\x00")
        probe = OpenOCDProbe(openocd_config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="verified"
            )
            result = probe.flash(fw)

        assert result.success


class TestProbeFactory:
    def test_edbg(self, edbg_config: ProbeConfig) -> None:
        probe = probe_factory(edbg_config)
        assert isinstance(probe, EdbgProbe)

    def test_openocd(self, openocd_config: ProbeConfig) -> None:
        probe = probe_factory(openocd_config)
        assert isinstance(probe, OpenOCDProbe)

    def test_unknown_type(self) -> None:
        from hilbench.exceptions import ProbeError

        config = ProbeConfig(type="edbg", device_path=Path("/dev/null"))
        # Manually override to test factory validation
        object.__setattr__(config, "type", "jtag-magic")
        with pytest.raises(ProbeError, match="unknown probe type"):
            probe_factory(config)


class TestEsptoolProbe:
    @pytest.fixture()
    def esp_config(self) -> ProbeConfig:
        return ProbeConfig(type="esptool", device_path=Path("/dev/ttyACM0"))

    def test_describe_command_defaults(self, esp_config: ProbeConfig) -> None:
        cmd = EsptoolProbe(esp_config).describe_command(Path("fw.bin"))
        assert cmd == [
            "esptool",
            "--chip",
            "esp32c6",
            "--port",
            "/dev/ttyACM0",
            "--baud",
            "460800",
            "--before",
            "usb-reset",
            "--after",
            "hard-reset",
            "write-flash",
            "0x0",
            "fw.bin",
        ]

    def test_describe_command_custom_fields(self) -> None:
        cfg = ProbeConfig(
            type="esptool",
            device_path=Path("/dev/ttyACM1"),
            chip="esp32s3",
            baud=921600,
            flash_offset="0x1000",
        )
        cmd = EsptoolProbe(cfg).describe_command(Path("a.bin"))
        assert cmd[cmd.index("--chip") + 1] == "esp32s3"
        assert cmd[cmd.index("--baud") + 1] == "921600"
        assert cmd[cmd.index("write-flash") + 1] == "0x1000"

    def test_verify_flag_is_noop(self, esp_config: ProbeConfig) -> None:
        probe = EsptoolProbe(esp_config)
        fw = Path("fw.bin")
        assert probe.describe_command(fw, verify=True) == probe.describe_command(fw, verify=False)

    def test_describe_command_resolves_glob(self, tmp_path: Path) -> None:
        port = tmp_path / "usb-Espressif_X_AA-if00"
        port.touch()
        cfg = ProbeConfig(type="esptool", device_path=tmp_path / "usb-Espressif_*-if00")
        cmd = EsptoolProbe(cfg).describe_command(Path("fw.bin"))
        assert cmd[cmd.index("--port") + 1] == str(port)

    def test_is_connected_does_not_run_subprocess(self, tmp_path: Path) -> None:
        port = tmp_path / "ttyACM0"
        port.touch()
        probe = EsptoolProbe(ProbeConfig(type="esptool", device_path=port))
        with patch("subprocess.run") as mock_run:
            assert probe.is_connected()
            port.unlink()
            assert not probe.is_connected()
        mock_run.assert_not_called()

    def test_flash_success(self, esp_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "fw.bin"
        fw.write_bytes(b"\x00")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="Hash of data verified.", stderr=""
            )
            result = EsptoolProbe(esp_config).flash(fw)
        assert result.success
        assert result.command[0] == "esptool"

    def test_flash_failure(self, esp_config: ProbeConfig, tmp_path: Path) -> None:
        fw = tmp_path / "fw.bin"
        fw.write_bytes(b"\x00")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=2, stdout="", stderr="Failed to connect"
            )
            with pytest.raises(FlashError, match="esptool failed"):
                EsptoolProbe(esp_config).flash(fw)

    def test_factory(self, esp_config: ProbeConfig) -> None:
        assert isinstance(probe_factory(esp_config), EsptoolProbe)
