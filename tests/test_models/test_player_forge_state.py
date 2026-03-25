"""Tests for player forge progression fields."""

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.forge_upgrade import ForgeUpgradeState
from spacegame.models.forge_buffer import ForgeBufferManager
from spacegame.models.recipe_mastery import RecipeMasteryTracker


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


class TestPlayerForgeFields:
    """Tests for forge-related Player fields."""

    def test_default_forge_tokens(self) -> None:
        player = _make_player()
        assert player.forge_tokens == 0

    def test_default_forge_upgrades(self) -> None:
        player = _make_player()
        assert isinstance(player.forge_upgrades, ForgeUpgradeState)
        assert player.forge_upgrades.get_level("any_upgrade") == 0

    def test_default_forge_buffer_manager(self) -> None:
        player = _make_player()
        assert isinstance(player.forge_buffer_manager, ForgeBufferManager)

    def test_default_recipe_mastery(self) -> None:
        player = _make_player()
        assert isinstance(player.recipe_mastery, RecipeMasteryTracker)

    def test_add_forge_tokens(self) -> None:
        player = _make_player()
        player.add_forge_tokens(25)
        assert player.forge_tokens == 25
        player.add_forge_tokens(10)
        assert player.forge_tokens == 35

    def test_spend_forge_tokens_success(self) -> None:
        player = _make_player()
        player.forge_tokens = 50
        assert player.spend_forge_tokens(20)
        assert player.forge_tokens == 30

    def test_spend_forge_tokens_insufficient(self) -> None:
        player = _make_player()
        player.forge_tokens = 5
        assert not player.spend_forge_tokens(10)
        assert player.forge_tokens == 5
