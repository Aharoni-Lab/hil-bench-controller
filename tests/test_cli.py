"""Tests for CLI commands using Click's CliRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

from hilbench.cli.main import cli


class TestCli:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "benchctl" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_subcommands_present(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        for cmd in ["flash", "serial", "gpio", "health", "config", "publish"]:
            assert cmd in result.output

    def test_config_validate(self, sample_config_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(sample_config_path), "config", "validate"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_config_validate_missing(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(tmp_path / "nope.yaml"), "config", "validate"]
        )
        assert result.exit_code != 0

    def test_config_show(self, sample_config_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(sample_config_path), "config", "show"])
        assert result.exit_code == 0
        assert "test-bench-01" in result.output

    def test_flash_dry_run(self, sample_config_path: Path, tmp_path: Path) -> None:
        fw = tmp_path / "test.bin"
        fw.write_bytes(b"\x00" * 10)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(sample_config_path),
                "--dry-run",
                "flash",
                "--firmware",
                str(fw),
                "--target",
                "samd51",
            ],
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_gpio_set_dry_run(self, sample_config_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(sample_config_path),
                "--dry-run",
                "gpio",
                "set",
                "--pin",
                "reset",
                "--value",
                "high",
                "--target",
                "samd51",
            ],
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_serial_expect_dry_run(self, sample_config_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(sample_config_path),
                "--dry-run",
                "serial",
                "expect",
                "--pattern",
                "BOOT OK",
                "--target",
                "samd51",
            ],
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_health_no_config(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["health"])
        # Should fail — no config at default path
        assert result.exit_code != 0

    def test_health_check_config_only(self, sample_config_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(sample_config_path), "health", "--check", "config"]
        )
        assert result.exit_code == 0
        assert "config" in result.output

    def test_publish_config_no_env(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["publish", "config"])
        assert result.exit_code == 0
        assert "not configured" in result.output.lower()


class TestEspCli:
    def _invoke(self, cfg: Path, *args: str):  # type: ignore[no-untyped-def]
        return CliRunner().invoke(cli, ["--config", str(cfg), *args])

    def test_gpio_get_expect(self, sample_config_path: Path) -> None:
        from unittest.mock import patch

        with patch("hilbench.cli.gpio_cmd.GpiodController") as ctrl:
            ctrl.return_value.get_pin.return_value = True
            ok = self._invoke(
                sample_config_path, "gpio", "get", "--pin", "fault", "--expect", "high"
            )
            bad = self._invoke(
                sample_config_path, "gpio", "get", "--pin", "fault", "--expect", "low"
            )
        assert ok.exit_code == 0
        assert bad.exit_code == 1
        assert "FAIL" in bad.output

    def test_serial_wait_port_option_dry_run(self, sample_config_path: Path) -> None:
        r = CliRunner().invoke(
            cli,
            ["--config", str(sample_config_path), "--dry-run", "serial", "expect",
             "--pattern", "x", "--wait-port", "3"],
        )  # fmt: skip
        assert r.exit_code == 0

    def test_flash_waits_for_port_on_esptool(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        import yaml

        from hilbench.probe import FlashResult

        cfg = tmp_path / "c.yaml"
        cfg.write_text(
            yaml.dump(
                {
                    "bench_name": "b",
                    "targets": {
                        "e": {
                            "family": "esp32c6",
                            "probe": {"type": "esptool", "device_path": "/dev/ttyACM0"},
                            "serial": {"device_path": "/dev/ttyACM0"},
                        }
                    },
                    "paths": {"workspace": str(tmp_path), "log_dir": str(tmp_path)},
                }
            )
        )
        fw = tmp_path / "fw.bin"
        fw.write_bytes(b"\x00")
        with (
            patch("hilbench.probe.EsptoolProbe.flash", return_value=FlashResult(True, "ok")),
            patch("hilbench.cli.flash_cmd.wait_for_port", return_value=False) as wait,
        ):
            r = self._invoke(cfg, "flash", "--firmware", str(fw), "--wait-port", "2")
        wait.assert_called_once()
        assert r.exit_code != 0
        with (
            patch("hilbench.probe.EsptoolProbe.flash", return_value=FlashResult(True, "ok")),
            patch("hilbench.cli.flash_cmd.wait_for_port", return_value=True),
        ):
            r = self._invoke(cfg, "flash", "--firmware", str(fw))
        assert r.exit_code == 0, r.output
