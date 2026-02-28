"""
Tests for player and ship models.
"""

import pytest
from spacegame.data_loader import DataLoader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.faction import ReputationTier


def test_player_initialization() -> None:
    """Test player can be created with starting ship."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)

    player = Player(name="Test Pilot", credits=2000, current_system_id="nexus_prime", ship=ship)

    assert player.name == "Test Pilot"
    assert player.credits == 2000
    assert player.current_system_id == "nexus_prime"
    assert player.game_day == 1
    assert "nexus_prime" in player.systems_visited


def test_player_buying_commodity() -> None:
    """Test player can buy commodities."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)
    player = Player("Test", 2000, "nexus_prime", ship)

    commodity_volumes = loader.get_commodity_volumes()

    # Buy 10 units of food at 50 credits each
    success, msg = player.buy_commodity("food", 10, 50, commodity_volumes)

    assert success, f"Purchase should succeed: {msg}"
    assert player.credits == 1500  # 2000 - 500
    assert player.ship.get_cargo_quantity("food") == 10
    assert player.trades_completed == 1


def test_player_insufficient_funds() -> None:
    """Test player cannot buy without enough credits."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)
    player = Player("Test", 100, "nexus_prime", ship)  # Only 100 credits

    commodity_volumes = loader.get_commodity_volumes()

    # Try to buy 10 units at 50 each (500 total)
    success, msg = player.buy_commodity("food", 10, 50, commodity_volumes)

    assert not success
    assert "Insufficient funds" in msg
    assert player.credits == 100  # Credits unchanged


def test_player_selling_commodity() -> None:
    """Test player can sell commodities."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)
    ship.add_cargo("food", 20)  # Start with 20 food

    player = Player("Test", 1000, "nexus_prime", ship)

    # Sell 10 units at 60 credits each
    success, msg = player.sell_commodity("food", 10, 60)

    assert success
    assert player.credits == 1600  # 1000 + 600
    assert player.ship.get_cargo_quantity("food") == 10
    assert player.trades_completed == 1


def test_player_travel() -> None:
    """Test player can travel between systems."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=100)

    player = Player("Test", 2000, "nexus_prime", ship)

    # Travel with 20 fuel cost
    success, msg = player.travel_to_system("verdant", 20)

    assert success
    assert player.current_system_id == "verdant"
    assert player.ship.current_fuel == 80  # 100 - 20
    assert player.game_day == 2  # Turn advanced
    assert "verdant" in player.systems_visited


def test_ship_cargo_management() -> None:
    """Test ship cargo operations."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=100)

    commodity_volumes = loader.get_commodity_volumes()

    # Add cargo
    ship.add_cargo("food", 10)
    assert ship.get_cargo_quantity("food") == 10

    # Check cargo space
    used = ship.get_used_cargo(commodity_volumes)
    assert used == 20  # 10 units * 2 volume each

    available = ship.get_available_cargo(commodity_volumes)
    assert available == ship.max_cargo - 20

    # Remove cargo
    success = ship.remove_cargo("food", 5)
    assert success
    assert ship.get_cargo_quantity("food") == 5


def test_ship_fuel_management() -> None:
    """Test ship fuel operations."""
    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=50)

    # Check fuel
    assert ship.has_fuel_for_jump(30)
    assert not ship.has_fuel_for_jump(100)

    # Consume fuel
    success = ship.consume_fuel(20)
    assert success
    assert ship.current_fuel == 30

    # Refuel
    added = ship.refuel(50)
    assert ship.current_fuel == 80  # 30 + 50

    # Refuel beyond capacity
    added = ship.refuel(100)
    assert ship.current_fuel == 100  # Max capacity
    assert added == 20  # Only 20 could be added


# ============================================================================
# Faction Reputation Tests
# ============================================================================


class TestPlayerReputation:
    """Tests for player faction reputation methods."""

    def _make_player(self) -> Player:
        loader = DataLoader()
        loader.load_all()
        shuttle_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=shuttle_type, current_fuel=100)
        player = Player("Test", 2000, "nexus_prime", ship)
        player.faction_reputation = {
            "commerce_guild": 0,
            "miners_union": 0,
            "science_collective": 0,
            "frontier_alliance": 0,
        }
        player.faction_assignments = {
            "nexus_prime": "commerce_guild",
            "verdant": "frontier_alliance",
        }
        return player

    def test_modify_reputation_positive(self) -> None:
        player = self._make_player()
        success, msg = player.modify_reputation("commerce_guild", 5)
        assert success
        assert player.faction_reputation["commerce_guild"] == 5

    def test_modify_reputation_negative(self) -> None:
        player = self._make_player()
        success, msg = player.modify_reputation("miners_union", -10)
        assert success
        assert player.faction_reputation["miners_union"] == -10

    def test_reputation_clamped_at_max(self) -> None:
        player = self._make_player()
        player.faction_reputation["commerce_guild"] = 95
        player.modify_reputation("commerce_guild", 20)
        assert player.faction_reputation["commerce_guild"] == 100

    def test_reputation_clamped_at_min(self) -> None:
        player = self._make_player()
        player.faction_reputation["miners_union"] = -90
        player.modify_reputation("miners_union", -20)
        assert player.faction_reputation["miners_union"] == -100

    def test_get_reputation_default_zero(self) -> None:
        player = self._make_player()
        assert player.get_reputation("unknown_faction") == 0

    def test_get_reputation_returns_value(self) -> None:
        player = self._make_player()
        player.faction_reputation["commerce_guild"] = 42
        assert player.get_reputation("commerce_guild") == 42

    def test_get_reputation_tier(self) -> None:
        player = self._make_player()
        player.faction_reputation["commerce_guild"] = 55
        assert player.get_reputation_tier("commerce_guild") == ReputationTier.ALLIED

    def test_get_reputation_tier_neutral_default(self) -> None:
        player = self._make_player()
        assert player.get_reputation_tier("commerce_guild") == ReputationTier.NEUTRAL

    def test_get_faction_for_system(self) -> None:
        player = self._make_player()
        assert player.get_faction_for_system("nexus_prime") == "commerce_guild"
        assert player.get_faction_for_system("verdant") == "frontier_alliance"

    def test_get_faction_for_unknown_system(self) -> None:
        player = self._make_player()
        assert player.get_faction_for_system("unknown_system") is None

    def test_modify_reputation_unknown_faction(self) -> None:
        player = self._make_player()
        success, msg = player.modify_reputation("nonexistent", 5)
        assert success
        assert player.faction_reputation["nonexistent"] == 5
