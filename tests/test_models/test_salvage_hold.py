"""Tests for SalvageHold and SalvageHoldManager."""

import pytest

from spacegame.models.salvage_hold import (
    SalvageHold,
    SalvageHoldManager,
    BASE_HOLD_CAPACITY,
)


class TestSalvageHold:
    """Tests for per-system salvage storage buffer."""

    def test_new_hold_is_empty(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        assert hold.get_total_stored() == 0

    def test_default_capacity(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        assert hold.capacity == BASE_HOLD_CAPACITY

    def test_custom_capacity(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=200)
        assert hold.capacity == 200

    def test_add_salvage(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        added = hold.add_salvage("scrap_metal", 10)
        assert added == 10
        assert hold.get_total_stored() == 10

    def test_add_multiple_types(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        hold.add_salvage("scrap_metal", 5)
        hold.add_salvage("salvaged_electronics", 3)
        assert hold.get_total_stored() == 8

    def test_add_capped_at_capacity(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=10)
        added = hold.add_salvage("scrap_metal", 15)
        assert added == 10
        assert hold.get_total_stored() == 10

    def test_partial_add_when_nearly_full(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=10)
        hold.add_salvage("scrap_metal", 7)
        added = hold.add_salvage("rare_parts", 5)
        assert added == 3
        assert hold.get_total_stored() == 10

    def test_add_zero_when_full(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=5)
        hold.add_salvage("scrap_metal", 5)
        added = hold.add_salvage("rare_parts", 3)
        assert added == 0

    def test_is_full(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=5)
        assert not hold.is_full()
        hold.add_salvage("scrap_metal", 5)
        assert hold.is_full()

    def test_available_space(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=20)
        hold.add_salvage("scrap_metal", 8)
        assert hold.get_available_space() == 12

    def test_remove_salvage(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        hold.add_salvage("scrap_metal", 10)
        removed = hold.remove_salvage("scrap_metal", 4)
        assert removed == 4
        assert hold.get_total_stored() == 6

    def test_remove_more_than_stored(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        hold.add_salvage("scrap_metal", 3)
        removed = hold.remove_salvage("scrap_metal", 10)
        assert removed == 3
        assert hold.get_total_stored() == 0

    def test_remove_not_present(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        removed = hold.remove_salvage("rare_parts", 5)
        assert removed == 0

    def test_remove_cleans_up_zero_entries(self) -> None:
        hold = SalvageHold(system_id="forgeworks")
        hold.add_salvage("scrap_metal", 5)
        hold.remove_salvage("scrap_metal", 5)
        assert "scrap_metal" not in hold.contents

    def test_serialization_round_trip(self) -> None:
        hold = SalvageHold(system_id="forgeworks", capacity=150)
        hold.add_salvage("scrap_metal", 20)
        hold.add_salvage("rare_parts", 5)
        data = hold.to_dict()
        restored = SalvageHold.from_dict(data)
        assert restored.system_id == "forgeworks"
        assert restored.capacity == 150
        assert restored.get_total_stored() == 25


class TestSalvageHoldManager:
    """Tests for cross-system salvage hold management."""

    def test_creates_hold_on_demand(self) -> None:
        mgr = SalvageHoldManager()
        hold = mgr.get_hold("forgeworks")
        assert hold.system_id == "forgeworks"
        assert hold.capacity == BASE_HOLD_CAPACITY

    def test_returns_same_hold(self) -> None:
        mgr = SalvageHoldManager()
        hold1 = mgr.get_hold("forgeworks")
        hold2 = mgr.get_hold("forgeworks")
        assert hold1 is hold2

    def test_different_systems_different_holds(self) -> None:
        mgr = SalvageHoldManager()
        h1 = mgr.get_hold("forgeworks")
        h2 = mgr.get_hold("the_fulcrum")
        assert h1 is not h2

    def test_upgrade_all_capacity(self) -> None:
        mgr = SalvageHoldManager()
        hold = mgr.get_hold("forgeworks")
        mgr.upgrade_all_capacity(50)
        assert hold.capacity == BASE_HOLD_CAPACITY + 50
        # New holds also get bonus
        new_hold = mgr.get_hold("breakstone")
        assert new_hold.capacity == BASE_HOLD_CAPACITY + 50

    def test_upgrade_stacks(self) -> None:
        mgr = SalvageHoldManager()
        hold = mgr.get_hold("forgeworks")
        mgr.upgrade_all_capacity(25)
        mgr.upgrade_all_capacity(25)
        assert hold.capacity == BASE_HOLD_CAPACITY + 50

    def test_serialization_round_trip(self) -> None:
        mgr = SalvageHoldManager()
        mgr.upgrade_all_capacity(50)
        hold = mgr.get_hold("forgeworks")
        hold.add_salvage("scrap_metal", 20)
        data = mgr.to_dict()
        restored = SalvageHoldManager.from_dict(data)
        assert restored.capacity_bonus == 50
        rhold = restored.get_hold("forgeworks")
        assert rhold.get_total_stored() == 20
