"""Publisher hook functions called from CLI commands."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hilbench.config import BenchConfig
    from hilbench.health import CheckResult
    from hilbench.publisher._client import SupabasePublisher

logger = logging.getLogger(__name__)

_publisher: SupabasePublisher | None = None


def _get_publisher(bench_config: BenchConfig) -> SupabasePublisher | None:
    """Return (and lazily create) the module-level publisher singleton."""
    global _publisher  # noqa: PLW0603
    if _publisher is not None:
        return _publisher

    from hilbench.publisher._config import load_publisher_config

    pub_config = load_publisher_config()
    if pub_config is None or not pub_config.enabled:
        return None

    from hilbench.publisher._client import SupabasePublisher

    _publisher = SupabasePublisher(pub_config, bench_config)
    return _publisher


def on_flash_start(bench_config: BenchConfig, target_name: str, firmware: str) -> None:
    """Called before flashing begins."""
    pub = _get_publisher(bench_config)
    if pub is None:
        return
    pub.publish_status(state="flashing", healthy=True, detail=f"target={target_name}")
    pub.publish_event("flash_start", {"target": target_name, "firmware": firmware})


def on_flash_end(
    bench_config: BenchConfig, target_name: str, success: bool, duration_s: float
) -> None:
    """Called after flashing completes (success or failure)."""
    pub = _get_publisher(bench_config)
    if pub is None:
        return
    state = "idle" if success else "error"
    detail = f"target={target_name} duration={duration_s:.1f}s"
    pub.publish_status(state=state, healthy=success, detail=detail)
    pub.publish_event(
        "flash_end",
        {"target": target_name, "success": success, "duration_s": duration_s},
    )


def on_health_complete(bench_config: BenchConfig, results: list[CheckResult]) -> None:
    """Called after health checks complete."""
    pub = _get_publisher(bench_config)
    if pub is None:
        return
    from hilbench.health import results_to_dicts

    all_passed = all(r.passed for r in results)
    checks = results_to_dicts(results)
    state = "idle" if all_passed else "error"
    pub.publish_status(state=state, healthy=all_passed, checks=checks)
    pub.publish_event("health_check", {"healthy": all_passed, "checks": checks})
