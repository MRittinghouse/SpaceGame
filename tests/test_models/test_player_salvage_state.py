"""Tests for player salvage progression fields."""

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.wreck_upgrade import WreckUpgradeState
from spacegame.models.salvage_hold import SalvageHoldManager


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


class TestPlayerSalvageFields:
    """Tests for salvage-related Player fields."""

    def test_default_salvage_intel(self) -> None:
        player = _make_player()
        assert player.salvage_intel == 0

    def test_default_salvage_prestige(self) -> None:
        player = _make_player()
        assert player.salvage_prestige_level == 0

    def test_default_wreck_upgrades(self) -> None:
        player = _make_player()
        assert isinstance(player.wreck_upgrades, WreckUpgradeState)
        assert player.wreck_upgrades.get_level("signal_amplifier") == 0

    def test_default_salvage_hold_manager(self) -> None:
        player = _make_player()
        assert isinstance(player.salvage_hold_manager, SalvageHoldManager)

    def test_default_max_salvage_deck(self) -> None:
        player = _make_player()
        assert player.max_salvage_deck == 0

    def test_add_salvage_intel(self) -> None:
        player = _make_player()
        player.add_salvage_intel(25)
        assert player.salvage_intel == 25
        player.add_salvage_intel(10)
        assert player.salvage_intel == 35

    def test_spend_salvage_intel_success(self) -> None:
        player = _make_player()
        player.salvage_intel = 50
        assert player.spend_salvage_intel(20)
        assert player.salvage_intel == 30

    def test_spend_salvage_intel_insufficient(self) -> None:
        player = _make_player()
        player.salvage_intel = 5
        assert not player.spend_salvage_intel(10)
        assert player.salvage_intel == 5
