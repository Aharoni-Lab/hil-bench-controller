"""Publisher configuration loaded from env file and environment variables."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_ENV_PATH = Path("/etc/hil-bench/supabase.env")


class PublisherConfig(BaseModel):
    """Supabase publisher configuration."""

    supabase_url: str
    supabase_key: str
    bench_email: str
    bench_password: str
    heartbeat_interval_s: int = 60
    publish_events: bool = False
    enabled: bool = True


def _load_env_file(path: Path) -> dict[str, str]:
    """Minimal .env loader — returns dict without mutating os.environ."""
    env_vars: dict[str, str] = {}
    if not path.is_file():
        return env_vars
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()
    return env_vars


def _get(key: str, file_vars: dict[str, str], default: str = "") -> str:
    """Get a value from env vars, falling back to file values."""
    return os.environ.get(key) or file_vars.get(key, default)


def load_publisher_config(env_path: Path | None = None) -> PublisherConfig | None:
    """Load publisher config from env file then env vars.

    Returns None if required variables (SUPABASE_URL, SUPABASE_KEY) are missing.
    Environment variables take precedence over file values.
    """
    path = env_path or DEFAULT_ENV_PATH
    file_vars = _load_env_file(path)

    url = _get("SUPABASE_URL", file_vars)
    key = _get("SUPABASE_KEY", file_vars)
    if not url or not key:
        logger.debug("Publisher not configured: SUPABASE_URL/SUPABASE_KEY missing")
        return None

    email = _get("BENCH_EMAIL", file_vars)
    password = _get("BENCH_PASSWORD", file_vars)
    if not email or not password:
        logger.debug("Publisher not configured: BENCH_EMAIL/BENCH_PASSWORD missing")
        return None

    return PublisherConfig(
        supabase_url=url,
        supabase_key=key,
        bench_email=email,
        bench_password=password,
        heartbeat_interval_s=int(_get("HEARTBEAT_INTERVAL_S", file_vars, "60")),
        publish_events=_get("PUBLISH_EVENTS", file_vars, "false").lower()
        in ("true", "1", "yes"),
        enabled=_get("PUBLISHER_ENABLED", file_vars, "true").lower() in ("true", "1", "yes"),
    )
