"""Pydantic models for Supabase table payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BenchRegistration(BaseModel):
    """Payload for upserting into the benches table."""

    bench_name: str
    hostname: str | None = None
    labels: list[str] = []
    targets: dict[str, Any] = {}
    wiki_url: str | None = None


class StatusUpsert(BaseModel):
    """Payload for upserting into bench_status_current."""

    bench_id: str
    state: str
    healthy: bool
    checks: list[dict[str, Any]] = []
    last_heartbeat: str  # ISO 8601 timestamp
    detail: str | None = None


class BenchEvent(BaseModel):
    """Payload for inserting into bench_events."""

    bench_id: str
    event_type: str
    payload: dict[str, Any] = {}
