"""Tests for publisher configuration loading."""

from __future__ import annotations

from pathlib import Path

from hilbench.publisher._config import load_publisher_config


class TestLoadPublisherConfig:
    def test_returns_none_when_not_configured(self, monkeypatch: object) -> None:
        """Returns None when SUPABASE_URL/KEY are missing."""
        # Clear any existing env vars
        for key in ("SUPABASE_URL", "SUPABASE_KEY", "BENCH_EMAIL", "BENCH_PASSWORD"):
            monkeypatch.delenv(key, raising=False)  # type: ignore[union-attr]
        result = load_publisher_config(env_path=Path("/nonexistent"))
        assert result is None

    def test_load_from_env_vars(self, monkeypatch: object) -> None:
        """Loads config from environment variables."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")  # type: ignore[union-attr]
        monkeypatch.setenv("SUPABASE_KEY", "test-key")  # type: ignore[union-attr]
        monkeypatch.setenv("BENCH_EMAIL", "bench@test.com")  # type: ignore[union-attr]
        monkeypatch.setenv("BENCH_PASSWORD", "pass123")  # type: ignore[union-attr]

        result = load_publisher_config(env_path=Path("/nonexistent"))
        assert result is not None
        assert result.supabase_url == "https://test.supabase.co"
        assert result.supabase_key == "test-key"
        assert result.bench_email == "bench@test.com"
        assert result.bench_password == "pass123"
        assert result.heartbeat_interval_s == 60
        assert result.publish_events is False
        assert result.enabled is True

    def test_load_from_file(self, tmp_path: Path, monkeypatch: object) -> None:
        """Loads config from env file."""
        for key in ("SUPABASE_URL", "SUPABASE_KEY", "BENCH_EMAIL", "BENCH_PASSWORD"):
            monkeypatch.delenv(key, raising=False)  # type: ignore[union-attr]

        env_file = tmp_path / "supabase.env"
        env_file.write_text(
            "SUPABASE_URL=https://file.supabase.co\n"
            "SUPABASE_KEY=file-key\n"
            "BENCH_EMAIL=file@test.com\n"
            "BENCH_PASSWORD=filepass\n"
        )
        result = load_publisher_config(env_path=env_file)
        assert result is not None
        assert result.supabase_url == "https://file.supabase.co"

    def test_env_vars_override_file(self, tmp_path: Path, monkeypatch: object) -> None:
        """Env vars take precedence over file values."""
        monkeypatch.setenv("SUPABASE_URL", "https://env.supabase.co")  # type: ignore[union-attr]
        monkeypatch.setenv("SUPABASE_KEY", "env-key")  # type: ignore[union-attr]
        monkeypatch.setenv("BENCH_EMAIL", "env@test.com")  # type: ignore[union-attr]
        monkeypatch.setenv("BENCH_PASSWORD", "envpass")  # type: ignore[union-attr]

        env_file = tmp_path / "supabase.env"
        env_file.write_text(
            "SUPABASE_URL=https://file.supabase.co\n"
            "SUPABASE_KEY=file-key\n"
            "BENCH_EMAIL=file@test.com\n"
            "BENCH_PASSWORD=filepass\n"
        )
        result = load_publisher_config(env_path=env_file)
        assert result is not None
        # setdefault in _load_env_file means env vars win
        assert result.supabase_url == "https://env.supabase.co"

    def test_defaults(self, monkeypatch: object) -> None:
        """Verify default values for optional fields."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")  # type: ignore[union-attr]
        monkeypatch.setenv("SUPABASE_KEY", "test-key")  # type: ignore[union-attr]
        monkeypatch.setenv("BENCH_EMAIL", "bench@test.com")  # type: ignore[union-attr]
        monkeypatch.setenv("BENCH_PASSWORD", "pass123")  # type: ignore[union-attr]

        result = load_publisher_config(env_path=Path("/nonexistent"))
        assert result is not None
        assert result.heartbeat_interval_s == 60
        assert result.publish_events is False
        assert result.enabled is True

    def test_returns_none_without_credentials(self, monkeypatch: object) -> None:
        """Returns None when email/password are missing."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")  # type: ignore[union-attr]
        monkeypatch.setenv("SUPABASE_KEY", "test-key")  # type: ignore[union-attr]
        monkeypatch.delenv("BENCH_EMAIL", raising=False)  # type: ignore[union-attr]
        monkeypatch.delenv("BENCH_PASSWORD", raising=False)  # type: ignore[union-attr]

        result = load_publisher_config(env_path=Path("/nonexistent"))
        assert result is None
