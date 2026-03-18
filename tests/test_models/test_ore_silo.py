"""Tests for OreSilo model — per-system ore storage buffer."""

import pytest

from spacegame.models.ore_silo import OreSilo, OreSiloManager


class TestOreSilo:
    """Tests for individual ore silo operations."""

    def test_new_silo_is_empty(self) -> None:
        silo = OreSilo(system_id="breakstone")
        assert silo.get_total_stored() == 0
        assert silo.contents == {}

    def test_default_capacity(self) -> None:
        silo = OreSilo(system_id="breakstone")
        assert silo.capacity == 100

    def test_custom_capacity(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=200)
        assert silo.capacity == 200

    def test_add_ore(self) -> None:
        silo = OreSilo(system_id="breakstone")
        added = silo.add_ore("iron_ore", 10)
        assert added == 10
        assert silo.contents["iron_ore"] == 10
        assert silo.get_total_stored() == 10

    def test_add_ore_multiple_types(self) -> None:
        silo = OreSilo(system_id="breakstone")
        silo.add_ore("iron_ore", 10)
        silo.add_ore("crystal_ore", 5)
        assert silo.get_total_stored() == 15

    def test_add_ore_capped_at_capacity(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=20)
        added = silo.add_ore("iron_ore", 25)
        assert added == 20
        assert silo.get_total_stored() == 20

    def test_add_ore_partial_when_nearly_full(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=20)
        silo.add_ore("iron_ore", 15)
        added = silo.add_ore("crystal_ore", 10)
        assert added == 5
        assert silo.get_total_stored() == 20

    def test_add_ore_zero_when_full(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=10)
        silo.add_ore("iron_ore", 10)
        added = silo.add_ore("crystal_ore", 5)
        assert added == 0

    def test_remove_ore(self) -> None:
        silo = OreSilo(system_id="breakstone")
        silo.add_ore("iron_ore", 20)
        removed = silo.remove_ore("iron_ore", 10)
        assert removed == 10
        assert silo.contents["iron_ore"] == 10

    def test_remove_ore_more_than_stored(self) -> None:
        silo = OreSilo(system_id="breakstone")
        silo.add_ore("iron_ore", 5)
        removed = silo.remove_ore("iron_ore", 10)
        assert removed == 5
        assert silo.get_total_stored() == 0

    def test_remove_ore_not_present(self) -> None:
        silo = OreSilo(system_id="breakstone")
        removed = silo.remove_ore("iron_ore", 5)
        assert removed == 0

    def test_remove_ore_cleans_up_zero_entries(self) -> None:
        silo = OreSilo(system_id="breakstone")
        silo.add_ore("iron_ore", 5)
        silo.remove_ore("iron_ore", 5)
        assert "iron_ore" not in silo.contents

    def test_get_available_space(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=100)
        silo.add_ore("iron_ore", 30)
        assert silo.get_available_space() == 70

    def test_is_full(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=10)
        assert not silo.is_full()
        silo.add_ore("iron_ore", 10)
        assert silo.is_full()

    def test_to_dict_round_trip(self) -> None:
        silo = OreSilo(system_id="breakstone", capacity=150)
        silo.add_ore("iron_ore", 20)
        silo.add_ore("crystal_ore", 10)
        data = silo.to_dict()
        restored = OreSilo.from_dict(data)
        assert restored.system_id == "breakstone"
        assert restored.capacity == 150
        assert restored.contents == {"iron_ore": 20, "crystal_ore": 10}


class TestOreSiloManager:
    """Tests for managing silos across multiple systems."""

    def test_get_silo_creates_new(self) -> None:
        mgr = OreSiloManager()
        silo = mgr.get_silo("breakstone")
        assert silo.system_id == "breakstone"
        assert silo.capacity == 100

    def test_get_silo_returns_same_instance(self) -> None:
        mgr = OreSiloManager()
        silo1 = mgr.get_silo("breakstone")
        silo1.add_ore("iron_ore", 10)
        silo2 = mgr.get_silo("breakstone")
        assert silo2.contents["iron_ore"] == 10

    def test_multiple_systems(self) -> None:
        mgr = OreSiloManager()
        mgr.get_silo("breakstone").add_ore("iron_ore", 10)
        mgr.get_silo("iron_depths").add_ore("crystal_ore", 5)
        assert mgr.get_silo("breakstone").get_total_stored() == 10
        assert mgr.get_silo("iron_depths").get_total_stored() == 5

    def test_upgrade_silo_capacity(self) -> None:
        mgr = OreSiloManager()
        silo = mgr.get_silo("breakstone")
        assert silo.capacity == 100
        mgr.upgrade_all_capacity(50)
        assert silo.capacity == 150
        # New silos also get the upgraded capacity
        silo2 = mgr.get_silo("iron_depths")
        assert silo2.capacity == 150

    def test_to_dict_round_trip(self) -> None:
        mgr = OreSiloManager()
        mgr.get_silo("breakstone").add_ore("iron_ore", 20)
        mgr.get_silo("iron_depths").add_ore("crystal_ore", 5)
        mgr.upgrade_all_capacity(50)
        data = mgr.to_dict()
        restored = OreSiloManager.from_dict(data)
        assert restored.get_silo("breakstone").contents["iron_ore"] == 20
        assert restored.get_silo("iron_depths").contents["crystal_ore"] == 5
        assert restored.capacity_bonus == 50

    def test_empty_manager_to_dict(self) -> None:
        mgr = OreSiloManager()
        data = mgr.to_dict()
        restored = OreSiloManager.from_dict(data)
        assert len(restored._silos) == 0
