"""Tests for save/load of deep core mining state."""

import pytest

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.save_manager import SaveManager


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player() -> Player:
    return Player(
        name="TestCaptain",
        credits=5000,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


class TestMiningStateSerialization:
    """Tests for round-trip serialization of mining persistent state."""

    def test_strata_tokens_serialize(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_mining")
        player = _make_player()
        player.strata_tokens = 42
        data = sm._serialize_player(player)
        assert data["strata_tokens"] == 42

    def test_strata_tokens_deserialize(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_mining")
        player = _make_player()
        player.strata_tokens = 42
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.strata_tokens == 42

    def test_prestige_level_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_mining")
        player = _make_player()
        player.mining_prestige_level = 3
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.mining_prestige_level == 3

    def test_deep_core_upgrades_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_mining")
        player = _make_player()
        player.deep_core_upgrades._levels["core_resonance"] = 3
        player.deep_core_upgrades._levels["energy_conduit"] = 1
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.deep_core_upgrades.get_level("core_resonance") == 3
        assert restored.deep_core_upgrades.get_level("energy_conduit") == 1

    def test_ore_silo_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_mining")
        player = _make_player()
        player.ore_silo_manager.get_silo("breakstone").add_ore("iron_ore", 30)
        player.ore_silo_manager.get_silo("iron_depths").add_ore("crystal_ore", 10)
        player.ore_silo_manager.upgrade_all_capacity(100)
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.ore_silo_manager.get_silo("breakstone").contents["iron_ore"] == 30
        assert restored.ore_silo_manager.get_silo("iron_depths").contents["crystal_ore"] == 10
        assert restored.ore_silo_manager.capacity_bonus == 100

    def test_backward_compat_no_mining_state(self) -> None:
        """Old saves without mining state should get defaults."""
        sm = SaveManager(save_directory="/tmp/test_saves_mining")
        player = _make_player()
        data = sm._serialize_player(player)
        # Remove mining keys to simulate old save
        del data["strata_tokens"]
        del data["mining_prestige_level"]
        del data["deep_core_upgrades"]
        del data["ore_silo_manager"]
        restored = sm._deserialize_player(data)
        assert restored.strata_tokens == 0
        assert restored.mining_prestige_level == 0
        assert restored.deep_core_upgrades.get_level("core_resonance") == 0
        assert restored.ore_silo_manager.capacity_bonus == 0
