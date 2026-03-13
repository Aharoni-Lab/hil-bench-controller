"""Tests for LED CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from hilbench.cli.main import cli
from hilbench.led._models import DaemonStatus, SceneResponse


class TestLedListScenes:
    def test_list_scenes(self, sample_config_path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["led", "list-scenes"])
        assert result.exit_code == 0
        assert "idle" in result.output
        assert "rainbow" in result.output
        assert "off" in result.output


class TestLedSetScene:
    def test_dry_run(self, sample_config_path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(sample_config_path), "--dry-run", "led", "set-scene", "idle"]
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_set_scene_success(self, sample_config_path) -> None:
        mock_client = MagicMock()
        mock_client.set_scene.return_value = SceneResponse(ok=True, current_scene="rainbow")

        runner = CliRunner()
        with patch("hilbench.led.LedClient", return_value=mock_client):
            result = runner.invoke(
                cli,
                [
                    "--config",
                    str(sample_config_path),
                    "led",
                    "set-scene",
                    "rainbow",
                    "--speed",
                    "2.0",
                ],
            )
        assert result.exit_code == 0
        assert "rainbow" in result.output

    def test_set_scene_with_color(self, sample_config_path) -> None:
        mock_client = MagicMock()
        mock_client.set_scene.return_value = SceneResponse(ok=True, current_scene="solid")

        runner = CliRunner()
        with patch("hilbench.led.LedClient", return_value=mock_client):
            result = runner.invoke(
                cli,
                [
                    "--config",
                    str(sample_config_path),
                    "led",
                    "set-scene",
                    "solid",
                    "--color",
                    "255,0,0",
                ],
            )
        assert result.exit_code == 0
        mock_client.set_scene.assert_called_once()
        call_params = mock_client.set_scene.call_args[0][1]
        assert call_params["color"] == [255, 0, 0]

    def test_set_scene_error(self, sample_config_path) -> None:
        mock_client = MagicMock()
        mock_client.set_scene.return_value = SceneResponse(ok=False, error="daemon down")

        runner = CliRunner()
        with patch("hilbench.led.LedClient", return_value=mock_client):
            result = runner.invoke(
                cli,
                ["--config", str(sample_config_path), "led", "set-scene", "idle"],
            )
        assert result.exit_code == 1


class TestLedOff:
    def test_dry_run(self, sample_config_path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(sample_config_path), "--dry-run", "led", "off"]
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_off_success(self, sample_config_path) -> None:
        mock_client = MagicMock()
        mock_client.off.return_value = SceneResponse(ok=True, current_scene="off")

        runner = CliRunner()
        with patch("hilbench.led.LedClient", return_value=mock_client):
            result = runner.invoke(cli, ["--config", str(sample_config_path), "led", "off"])
        assert result.exit_code == 0


class TestLedStatus:
    def test_daemon_not_running(self, sample_config_path) -> None:
        mock_client = MagicMock()
        mock_client.is_daemon_running.return_value = False

        runner = CliRunner()
        with patch("hilbench.led.LedClient", return_value=mock_client):
            result = runner.invoke(cli, ["--config", str(sample_config_path), "led", "status"])
        assert result.exit_code == 0
        assert "not running" in result.output

    def test_daemon_running(self, sample_config_path) -> None:
        mock_client = MagicMock()
        mock_client.is_daemon_running.return_value = True
        mock_client.status.return_value = DaemonStatus(
            running=True, current_scene="idle", led_count=16, uptime_s=42.0
        )

        runner = CliRunner()
        with patch("hilbench.led.LedClient", return_value=mock_client):
            result = runner.invoke(cli, ["--config", str(sample_config_path), "led", "status"])
        assert result.exit_code == 0
        assert "idle" in result.output
        assert "16" in result.output


class TestLedDaemonCmd:
    def test_dry_run(self, sample_config_path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(sample_config_path), "--dry-run", "led", "daemon"]
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output
