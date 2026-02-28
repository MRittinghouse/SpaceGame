"""
Tests for data loading system.
"""

import pytest
from spacegame.data_loader import DataLoader
from spacegame.models.system import StarSystem
from spacegame.models.commodity import Commodity, CommodityCategory
from spacegame.models.ship import ShipType


def test_data_loader_initialization() -> None:
    """Test that DataLoader can be initialized and loads data."""
    loader = DataLoader()
    loader.load_all()

    assert len(loader.systems) > 0, "Should load at least one system"
    assert len(loader.commodities) > 0, "Should load at least one commodity"
    assert len(loader.ship_types) > 0, "Should load at least one ship type"


def test_load_systems() -> None:
    """Test system loading and structure."""
    loader = DataLoader()
    systems = loader.load_systems()

    # Should have 10 systems (5 original + 5 expansion)
    assert len(systems) == 10, "Should load exactly 10 systems"

    # Check Nexus Prime system exists and has correct properties
    assert "nexus_prime" in systems, "Nexus Prime system should exist"
    nexus = systems["nexus_prime"]

    assert nexus.name == "Nexus Prime"
    assert nexus.type == "trade_hub"
    assert nexus.coordinates.x == 0
    assert nexus.coordinates.y == 0
    assert len(nexus.stations) > 0, "Nexus Prime should have at least one station"
    assert len(nexus.economy.production_tags) > 0


def test_load_commodities() -> None:
    """Test commodity loading and structure."""
    loader = DataLoader()
    commodities = loader.load_commodities()

    # Should have 19 commodities (12 original + 7 new ore/salvage types)
    assert len(commodities) == 19, "Should load exactly 19 commodities"

    # Check a basic commodity
    assert "food" in commodities
    food = commodities["food"]

    assert food.name == "Food & Water"
    assert food.category == CommodityCategory.BASIC
    assert food.base_price > 0
    assert food.volume_per_unit > 0


def test_load_ship_types() -> None:
    """Test ship type loading and structure."""
    loader = DataLoader()
    ship_types = loader.load_ship_types()

    # Should have 6 ship types
    assert len(ship_types) == 6, "Should load exactly 6 ship types"

    # Check starter ship
    assert "shuttle" in ship_types
    shuttle = ship_types["shuttle"]

    assert shuttle.name == "Shuttle"
    assert shuttle.cargo_capacity > 0
    assert shuttle.fuel_capacity > 0
    assert shuttle.purchase_price > 0


def test_system_distance_calculation() -> None:
    """Test Euclidean distance calculation between systems."""
    loader = DataLoader()
    loader.load_systems()

    nexus = loader.get_system("nexus_prime")
    verdant = loader.get_system("verdant")

    # Verdant is at (80, 40), Nexus Prime at (0, 0)
    # Distance = sqrt(80^2 + 40^2) = sqrt(8000) ≈ 89.4
    distance = nexus.distance_to(verdant)
    assert 89 < distance < 90, f"Distance should be ~89.4, got {distance}"


def test_commodity_price_range() -> None:
    """Test commodity price range calculation."""
    loader = DataLoader()
    loader.load_commodities()

    food = loader.get_commodity("food")
    min_price, max_price = food.get_price_range()

    assert min_price < food.base_price < max_price
    assert min_price > 0


def test_commodity_cargo_calculations() -> None:
    """Test cargo space calculations for commodities."""
    loader = DataLoader()
    loader.load_commodities()

    food = loader.get_commodity("food")

    # Test cargo space calculation
    space_for_10 = food.calculate_cargo_space(10)
    assert space_for_10 == 10 * food.volume_per_unit

    # Test max units calculation
    available_cargo = 100
    max_units = food.max_units_for_cargo(available_cargo)
    assert max_units == available_cargo // food.volume_per_unit
