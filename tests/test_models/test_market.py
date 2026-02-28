"""
Tests for market pricing system.
"""

import pytest
from spacegame.data_loader import DataLoader
from spacegame.models.market import Market


def test_market_initialization() -> None:
    """Test market can be initialized for a system."""
    loader = DataLoader()
    loader.load_all()

    nexus = loader.get_system("nexus_prime")
    commodities = loader.get_all_commodities()

    market = Market(nexus, commodities, game_day=1)

    assert market.system == nexus
    assert len(market.commodities) == 19


def test_market_pricing() -> None:
    """Test that market generates prices for all commodities."""
    loader = DataLoader()
    loader.load_all()

    nexus = loader.get_system("nexus_prime")
    commodities = loader.get_all_commodities()
    market = Market(nexus, commodities, game_day=1)

    # All commodities should have prices
    prices = market.get_all_prices()
    assert len(prices) == 19

    # All prices should be positive
    for commodity_id, price in prices.items():
        assert price > 0, f"{commodity_id} should have positive price"


def test_supply_demand_pricing() -> None:
    """Test that supply/demand affects prices correctly."""
    loader = DataLoader()
    loader.load_all()

    # Verdant produces food (should be cheap)
    verdant = loader.get_system("verdant")
    # Forgeworks consumes food (should be expensive)
    forgeworks = loader.get_system("forgeworks")

    commodities = loader.get_all_commodities()

    verdant_market = Market(verdant, commodities, game_day=1)
    forgeworks_market = Market(forgeworks, commodities, game_day=1)

    verdant_food_price = verdant_market.get_price("food")
    forgeworks_food_price = forgeworks_market.get_price("food")

    # Food should be cheaper in Verdant (producer)
    # than in Forgeworks (consumer)
    assert verdant_food_price < forgeworks_food_price, (
        f"Food should be cheaper in Verdant ({verdant_food_price}) "
        f"than Forgeworks ({forgeworks_food_price})"
    )


def test_market_report() -> None:
    """Test market report generation."""
    loader = DataLoader()
    loader.load_all()

    nexus = loader.get_system("nexus_prime")
    commodities = loader.get_all_commodities()
    market = Market(nexus, commodities, game_day=1)

    report = market.get_market_report("food")

    assert report["commodity_id"] == "food"
    assert report["commodity_name"] == "Food & Water"
    assert "current_price" in report
    assert "trend" in report
    assert "analysis" in report


def test_market_day_update() -> None:
    """Test that market prices change when day updates."""
    loader = DataLoader()
    loader.load_all()

    nexus = loader.get_system("nexus_prime")
    commodities = loader.get_all_commodities()
    market = Market(nexus, commodities, game_day=1)

    day1_prices = market.get_all_prices().copy()

    # Update to day 2
    market.update_day(2)
    day2_prices = market.get_all_prices()

    # At least some prices should change due to random variance
    # (though supply/demand modifiers stay the same)
    price_changes = sum(1 for cid in day1_prices if day1_prices[cid] != day2_prices[cid])

    # Most prices should change slightly
    assert (
        price_changes >= len(day1_prices) * 0.5
    ), "At least 50% of prices should change between days"
