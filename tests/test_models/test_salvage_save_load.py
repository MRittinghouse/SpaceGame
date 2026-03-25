"""Tests for salvage progression save/load round-trip."""

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.save_manager import SaveManager


def _make_player() -> Player:
    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic",
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
    return Player(
        name="TestCaptain",
        credits=5000,
        current_system_id="forgeworks",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )


class TestSalvageSaveLoad:
    """Tests for serializing and deserializing salvage progression."""

    def test_salvage_intel_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_salvage")
        player = _make_player()
        player.salvage_intel = 42
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.salvage_intel == 42

    def test_salvage_prestige_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_salvage")
        player = _make_player()
        player.salvage_prestige_level = 3
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.salvage_prestige_level == 3

    def test_max_salvage_deck_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_salvage")
        player = _make_player()
        player.max_salvage_deck = 7
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.max_salvage_deck == 7

    def test_wreck_upgrades_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_salvage")
        player = _make_player()
        player.wreck_upgrades._levels["signal_amplifier"] = 3
        player.wreck_upgrades._levels["quick_extract"] = 1
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.wreck_upgrades.get_level("signal_amplifier") == 3
        assert restored.wreck_upgrades.get_level("quick_extract") == 1

    def test_salvage_hold_round_trip(self) -> None:
        sm = SaveManager(save_directory="/tmp/test_saves_salvage")
        player = _make_player()
        hold = player.salvage_hold_manager.get_hold("forgeworks")
        hold.add_salvage("scrap_metal", 30)
        player.salvage_hold_manager.upgrade_all_capacity(50)
        data = sm._serialize_player(player)
        restored = sm._deserialize_player(data)
        assert restored.salvage_hold_manager.capacity_bonus == 50
        rhold = restored.salvage_hold_manager.get_hold("forgeworks")
        assert rhold.get_total_stored() == 30

    def test_backward_compat_no_salvage_data(self) -> None:
        """Old saves without salvage fields should load with defaults."""
        sm = SaveManager(save_directory="/tmp/test_saves_salvage")
        player = _make_player()
        data = sm._serialize_player(player)
        # Strip salvage fields to simulate old save
        for key in [
            "salvage_intel",
            "salvage_prestige_level",
            "wreck_upgrades",
            "salvage_hold_manager",
            "max_salvage_deck",
        ]:
            data.pop(key, None)
        restored = sm._deserialize_player(data)
        assert restored.salvage_intel == 0
        assert restored.salvage_prestige_level == 0
        assert restored.max_salvage_deck == 0
        assert restored.wreck_upgrades.get_level("anything") == 0
