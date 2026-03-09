"""Power/reset relay control via GPIO — stubbed until hardware is standardized."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hilbench.config import PowerConfig

logger = logging.getLogger(__name__)


class RelayController:
    """Controls power relay for target power cycling.

    Currently stubbed — raises NotImplementedError for real operations.
    Implement when relay hardware is standardized.
    """

    def __init__(self, config: PowerConfig) -> None:
        self.config = config

    def power_cycle(self, off_duration_s: float = 1.0) -> None:
        if self.config.type == "none":
            logger.warning("power control not configured (type=none)")
            return
        raise NotImplementedError(
            "relay power control not yet implemented — waiting for hardware standardization"
        )

    def power_off(self) -> None:
        if self.config.type == "none":
            logger.warning("power control not configured (type=none)")
            return
        raise NotImplementedError("relay power_off not yet implemented")

    def power_on(self) -> None:
        if self.config.type == "none":
            logger.warning("power control not configured (type=none)")
            return
        raise NotImplementedError("relay power_on not yet implemented")
