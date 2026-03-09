"""Tests for probe flash abstraction (mocked subprocess)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from hilbench.config import ProbeConfig
from hilbench.exceptions import FlashError
from hilbench.probe import EdbgProbe, OpenOCDProbe, probe_factory


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
