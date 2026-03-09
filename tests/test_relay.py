"""Tests for relay controller (stubbed)."""

from __future__ import annotations

import pytest

from hilbench.config import PowerConfig
from hilbench.relay import RelayController


class TestRelayController:
    def test_power_cycle_type_none(self) -> None:
        ctrl = RelayController(PowerConfig(type="none"))
        # Should not raise — just warns
        ctrl.power_cycle()

    def test_power_cycle_type_relay_not_implemented(self) -> None:
        ctrl = RelayController(PowerConfig(type="relay"))
        with pytest.raises(NotImplementedError):
            ctrl.power_cycle()

    def test_power_off_type_none(self) -> None:
        ctrl = RelayController(PowerConfig(type="none"))
        ctrl.power_off()

    def test_power_on_type_relay_not_implemented(self) -> None:
        ctrl = RelayController(PowerConfig(type="relay"))
        with pytest.raises(NotImplementedError):
            ctrl.power_on()
