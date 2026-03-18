"""Tests for forge progression save/load round-trip."""

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.save_manager import SaveManager


def _make_player() -> Player:
    ship_type = ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="Basic", cargo_capacity=100, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=1, special_abilities=[], availability="all",
    )
    return Player(
        name="TestCaptain", credits=5000,
        current_system_id="forgeworks",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )


class TestForgeSaveLoad:
    """Tests for serializing and deserializing forge progression."""

    def test_forge_tokens_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_forge")
        player = _make_player()
        player.forge_tokens = 42
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.forge_tokens == 42

    def test_forge_upgrades_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_forge")
        player = _make_player()
        player.forge_upgrades._levels["speed_forge"] = 2
        player.forge_upgrades._levels["yield_boost"] = 1
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.forge_upgrades.get_level("speed_forge") == 2
        assert restored.forge_upgrades.get_level("yield_boost") == 1

    def test_forge_buffer_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_forge")
        player = _make_player()
        buf = player.forge_buffer_manager.get_buffer("forgeworks")
        buf.add_output("alloy_plate", 20)
        player.forge_buffer_manager.upgrade_all_capacity(25)
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.forge_buffer_manager.capacity_bonus == 25
        rbuf = restored.forge_buffer_manager.get_buffer("forgeworks")
        assert rbuf.get_total_stored() == 20

    def test_recipe_mastery_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_forge")
        player = _make_player()
        player.recipe_mastery.record_craft("alloy_plate")
        player.recipe_mastery.record_craft("alloy_plate")
        player.recipe_mastery.record_craft("alloy_plate")  # hits level 1
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        entry = restored.recipe_mastery.get_mastery("alloy_plate")
        assert entry.times_crafted == 3
        assert entry.mastery_level == 1

    def test_backward_compat_no_forge_data(self) -> None:
        """Old saves without forge fields should load with defaults."""
        sm = SaveManager(save_directory="/tmp/test_saves_forge")
        player = _make_player()
        data = sm._serialize_player(player)
        # Strip forge fields to simulate old save
        for key in ["forge_tokens", "forge_upgrades",
                     "forge_buffer_manager", "recipe_mastery"]:
            data.pop(key, None)
        restored = sm._deserialize_player(data)
        assert restored.forge_tokens == 0
        assert restored.forge_upgrades.get_level("anything") == 0
        assert restored.forge_buffer_manager.capacity_bonus == 0
        assert restored.recipe_mastery.get_mastery("x").times_crafted == 0
