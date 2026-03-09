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


def _load_env_file(path: Path) -> None:
    """Minimal .env loader — sets env vars that are not already set."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        os.environ.setdefault(key, value)


def load_publisher_config(env_path: Path | None = None) -> PublisherConfig | None:
    """Load publisher config from env file then env vars.

    Returns None if required variables (SUPABASE_URL, SUPABASE_KEY) are missing.
    """
    path = env_path or DEFAULT_ENV_PATH
    _load_env_file(path)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.debug("Publisher not configured: SUPABASE_URL/SUPABASE_KEY missing")
        return None

    email = os.environ.get("BENCH_EMAIL", "")
    password = os.environ.get("BENCH_PASSWORD", "")
    if not email or not password:
        logger.debug("Publisher not configured: BENCH_EMAIL/BENCH_PASSWORD missing")
        return None

    return PublisherConfig(
        supabase_url=url,
        supabase_key=key,
        bench_email=email,
        bench_password=password,
        heartbeat_interval_s=int(os.environ.get("HEARTBEAT_INTERVAL_S", "60")),
        publish_events=os.environ.get("PUBLISH_EVENTS", "false").lower() in ("true", "1", "yes"),
        enabled=os.environ.get("PUBLISHER_ENABLED", "true").lower() in ("true", "1", "yes"),
    )
