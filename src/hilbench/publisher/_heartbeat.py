"""Heartbeat loop for continuous status publishing."""

from __future__ import annotations

import logging
import signal
import time
from typing import TYPE_CHECKING, Any

from hilbench.health import results_to_dicts, run_all_checks

if TYPE_CHECKING:
    from hilbench.config import BenchConfig
    from hilbench.publisher._client import SupabasePublisher

logger = logging.getLogger(__name__)


def run_heartbeat_loop(
    publisher: SupabasePublisher,
    bench_config: BenchConfig,
    interval_s: int = 60,
) -> None:
    """Run health checks and publish status on a loop until signalled to stop."""
    shutdown = False

    def _handle_signal(signum: int, frame: Any) -> None:
        nonlocal shutdown
        logger.info("Received signal %s, shutting down heartbeat", signum)
        shutdown = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Starting heartbeat loop (interval=%ds)", interval_s)

    while not shutdown:
        try:
            results = run_all_checks(bench_config)
            all_passed = all(r.passed for r in results)
            checks = results_to_dicts(results)
            state = "idle" if all_passed else "error"
            publisher.publish_status(state=state, healthy=all_passed, checks=checks)
            publisher.publish_event("heartbeat", {"healthy": all_passed, "checks": checks})
        except Exception:
            logger.warning("Heartbeat iteration failed", exc_info=True)

        # Sleep in 1s increments for signal responsiveness
        for _ in range(interval_s):
            if shutdown:
                break
            time.sleep(1)

    logger.info("Heartbeat loop stopped")
    publisher.close()
