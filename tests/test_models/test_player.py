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


# ============================================================================
# Total Profit Tracking Tests
# ============================================================================


class TestTotalProfitTracking:
    """Tests for total_profit tracking actual profit, not revenue."""

    def test_total_profit_tracks_actual_profit(self) -> None:
        """total_profit should track price_per_unit - avg_cost, not revenue."""
        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        volumes = {c.id: c.volume_per_unit for c in loader.get_all_commodities()}

        player = Player("Test", 5000, "nexus_prime", ship)
        # Buy 10 food at 50 CR (avg cost = 50)
        player.buy_commodity("food", 10, 50, volumes)
        # Sell 10 food at 80 CR (profit = (80-50)*10 = 300)
        player.sell_commodity("food", 10, 80)

        assert player.total_profit == 300, f"Expected 300, got {player.total_profit}"

    def test_total_profit_negative_trade(self) -> None:
        """Selling below purchase price should decrease total_profit."""
        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        volumes = {c.id: c.volume_per_unit for c in loader.get_all_commodities()}

        player = Player("Test", 5000, "nexus_prime", ship)
        player.buy_commodity("food", 10, 80, volumes)
        player.sell_commodity("food", 10, 50)

        assert player.total_profit == -300, f"Expected -300, got {player.total_profit}"

    def test_total_profit_accumulates(self) -> None:
        """Multiple trades should accumulate correctly."""
        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        volumes = {c.id: c.volume_per_unit for c in loader.get_all_commodities()}

        player = Player("Test", 10000, "nexus_prime", ship)
        # Trade 1: buy at 50, sell at 80 = +300
        player.buy_commodity("food", 10, 50, volumes)
        player.sell_commodity("food", 10, 80)
        # Trade 2: buy at 100, sell at 90 = -100
        player.buy_commodity("food", 10, 100, volumes)
        player.sell_commodity("food", 10, 90)

        assert player.total_profit == 200, f"Expected 200, got {player.total_profit}"


class TestPlayerRepairAtStation:
    """Tests for hull repair at station service."""

    def _make_player(self, credits: int = 5000) -> Player:
        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        # Set hull to half max
        ship.current_hull = ship_type.combat_hull
        return Player("Test", credits, "nexus_prime", ship)

    def test_repair_at_station_success(self) -> None:
        player = self._make_player(credits=5000)
        player.ship.current_hull = 30  # max is 60 for shuttle
        success, msg = player.repair_at_station(cost_per_hp=10)
        assert success
        assert player.ship.current_hull == player.ship.ship_type.combat_hull
        # Cost: (60 - 30) * 10 = 300
        assert player.credits == 4700

    def test_repair_at_station_hull_already_full(self) -> None:
        player = self._make_player()
        player.ship.current_hull = player.ship.ship_type.combat_hull
        success, msg = player.repair_at_station(cost_per_hp=10)
        assert not success
        assert "full" in msg.lower() or "no" in msg.lower()

    def test_repair_at_station_insufficient_credits(self) -> None:
        player = self._make_player(credits=100)
        player.ship.current_hull = 10  # needs (60-10)*10 = 500 CR
        success, msg = player.repair_at_station(cost_per_hp=10)
        assert not success
        assert "credits" in msg.lower() or "afford" in msg.lower()

    def test_repair_at_station_deducts_exact_cost(self) -> None:
        player = self._make_player(credits=1000)
        player.ship.current_hull = 55  # 5 HP to repair
        success, msg = player.repair_at_station(cost_per_hp=12)
        assert success
        # Cost: (60 - 55) * 12 = 60
        assert player.credits == 940

    def test_repair_at_station_zero_cost_per_hp(self) -> None:
        """Free repair should still work."""
        player = self._make_player(credits=0)
        player.ship.current_hull = 30
        success, msg = player.repair_at_station(cost_per_hp=0)
        assert success
        assert player.ship.current_hull == player.ship.ship_type.combat_hull
        assert player.credits == 0

    def test_repair_at_station_returns_amount_repaired_in_message(self) -> None:
        player = self._make_player(credits=5000)
        player.ship.current_hull = 40  # 20 HP to repair
        success, msg = player.repair_at_station(cost_per_hp=10)
        assert success
        assert "20" in msg  # Should mention amount repaired
