"""Supabase publisher client — all methods swallow exceptions to avoid disrupting bench ops."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from hilbench.publisher._models import BenchEvent, BenchRegistration, StatusUpsert

if TYPE_CHECKING:
    from hilbench.config import BenchConfig
    from hilbench.publisher._config import PublisherConfig

logger = logging.getLogger(__name__)


class SupabasePublisher:
    """Publishes bench status and events to Supabase.

    All public methods swallow exceptions and log warnings so the bench
    continues operating even if Supabase is unreachable.
    """

    def __init__(self, pub_config: PublisherConfig, bench_config: BenchConfig) -> None:
        self._pub_config = pub_config
        self._bench_config = bench_config
        self._client: Any = None
        self._bench_id: str | None = None

    def _ensure_client(self) -> bool:
        """Create Supabase client and sign in. Returns True on success."""
        if self._client is not None:
            return True
        try:
            from supabase import create_client

            self._client = create_client(
                self._pub_config.supabase_url, self._pub_config.supabase_key
            )
            self._client.auth.sign_in_with_password(
                {
                    "email": self._pub_config.bench_email,
                    "password": self._pub_config.bench_password,
                }
            )
            logger.info("Supabase publisher authenticated")
            return True
        except Exception:
            logger.warning("Failed to connect to Supabase", exc_info=True)
            self._client = None
            return False

    def _ensure_bench_registered(self) -> str | None:
        """Upsert bench registration and return bench_id."""
        if self._bench_id is not None:
            return self._bench_id
        if not self._ensure_client():
            return None
        try:
            cfg = self._bench_config
            reg = BenchRegistration(
                bench_name=cfg.bench_name,
                hostname=cfg.hostname,
                labels=cfg.runner.labels,
                targets={
                    name: {"family": t.family, "probe_type": t.probe.type}
                    for name, t in cfg.targets.items()
                },
                wiki_url=cfg.wiki.canonical_url,
            )
            result = (
                self._client.table("benches")
                .upsert(reg.model_dump(), on_conflict="bench_name")
                .execute()
            )
            self._bench_id = result.data[0]["id"]
            logger.info("Bench registered: %s (id=%s)", cfg.bench_name, self._bench_id)
            return self._bench_id
        except Exception:
            logger.warning("Failed to register bench", exc_info=True)
            return None

    def publish_status(
        self,
        state: str,
        healthy: bool,
        checks: list[dict[str, Any]] | None = None,
        detail: str | None = None,
    ) -> None:
        """Upsert bench status. Non-blocking on failure."""
        bench_id = self._ensure_bench_registered()
        if bench_id is None:
            return
        try:
            upsert = StatusUpsert(
                bench_id=bench_id,
                state=state,
                healthy=healthy,
                checks=checks or [],
                last_heartbeat=datetime.now(UTC).isoformat(),
                detail=detail,
            )
            self._client.table("bench_status_current").upsert(
                upsert.model_dump(), on_conflict="bench_id"
            ).execute()
            logger.debug("Published status: state=%s healthy=%s", state, healthy)
        except Exception:
            logger.warning("Failed to publish status", exc_info=True)

    def publish_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """Insert a bench event. Gated by publish_events config flag."""
        if not self._pub_config.publish_events:
            return
        bench_id = self._ensure_bench_registered()
        if bench_id is None:
            return
        try:
            event = BenchEvent(
                bench_id=bench_id,
                event_type=event_type,
                payload=payload or {},
            )
            self._client.table("bench_events").insert(event.model_dump()).execute()
            logger.debug("Published event: %s", event_type)
        except Exception:
            logger.warning("Failed to publish event", exc_info=True)

    def close(self) -> None:
        """Sign out from Supabase."""
        if self._client is not None:
            try:
                self._client.auth.sign_out()
            except Exception:
                logger.warning("Failed to sign out", exc_info=True)
            self._client = None
            self._bench_id = None
