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

    def test_publish_config_no_env(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["publish", "config"])
        assert result.exit_code == 0
        assert "not configured" in result.output.lower()
