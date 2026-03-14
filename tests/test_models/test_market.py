"""
Tests for market pricing system.
"""

import pytest
from spacegame.data_loader import DataLoader
from spacegame.models.market import Market, PriceHistory


def test_market_initialization() -> None:
    """Test market can be initialized for a system."""
    loader = DataLoader()
    loader.load_all()

    nexus = loader.get_system("nexus_prime")
    commodities = loader.get_all_commodities()

    market = Market(nexus, commodities, game_day=1)

    assert market.system == nexus
    assert len(market.commodities) == 27


def test_market_pricing() -> None:
    """Test that market generates prices for all commodities."""
    loader = DataLoader()
    loader.load_all()

    nexus = loader.get_system("nexus_prime")
    commodities = loader.get_all_commodities()
    market = Market(nexus, commodities, game_day=1)

    # All commodities should have prices
    prices = market.get_all_prices()
    assert len(prices) == 27

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


# ============================================================================
# PriceHistory tests
# ============================================================================


class TestPriceHistory:
    """Tests for PriceHistory tracking."""

    def test_record_and_retrieve(self) -> None:
        """Recording a price should be retrievable."""
        ph = PriceHistory()
        ph.record("nexus_prime", "metals", 1, 100)
        history = ph.get_history("nexus_prime", "metals")
        assert len(history) == 1
        assert history[0] == (1, 100)

    def test_max_days_limit(self) -> None:
        """History should be limited to max_days entries per system/commodity."""
        ph = PriceHistory(max_days=3)
        for day in range(1, 6):
            ph.record("sys_a", "metals", day, 100 + day)
        history = ph.get_history("sys_a", "metals")
        assert len(history) == 3
        # Should keep the 3 most recent
        assert history[0] == (3, 103)
        assert history[-1] == (5, 105)

    def test_trend_rising(self) -> None:
        """Trend should be 'rising' when prices are increasing."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 100)
        ph.record("sys_a", "metals", 2, 110)
        ph.record("sys_a", "metals", 3, 120)
        assert ph.get_trend("sys_a", "metals") == "rising"

    def test_trend_falling(self) -> None:
        """Trend should be 'falling' when prices are decreasing."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 120)
        ph.record("sys_a", "metals", 2, 110)
        ph.record("sys_a", "metals", 3, 100)
        assert ph.get_trend("sys_a", "metals") == "falling"

    def test_trend_stable(self) -> None:
        """Trend should be 'stable' when prices don't change much."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 100)
        ph.record("sys_a", "metals", 2, 101)
        ph.record("sys_a", "metals", 3, 100)
        assert ph.get_trend("sys_a", "metals") == "stable"

    def test_empty_returns_stable(self) -> None:
        """No history should return 'stable' trend."""
        ph = PriceHistory()
        assert ph.get_trend("sys_a", "metals") == "stable"
        assert ph.get_history("sys_a", "metals") == []

    def test_per_system_isolation(self) -> None:
        """History for one system should not affect another."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 100)
        ph.record("sys_b", "metals", 1, 200)
        assert ph.get_history("sys_a", "metals") == [(1, 100)]
        assert ph.get_history("sys_b", "metals") == [(1, 200)]

    def test_serialization_roundtrip(self) -> None:
        """to_dict/from_dict should preserve all data."""
        ph = PriceHistory(max_days=5)
        ph.record("sys_a", "metals", 1, 100)
        ph.record("sys_a", "metals", 2, 110)
        ph.record("sys_b", "fuel", 1, 50)

        data = ph.to_dict()
        restored = PriceHistory.from_dict(data)

        assert restored.max_days == 5
        assert restored.get_history("sys_a", "metals") == [(1, 100), (2, 110)]
        assert restored.get_history("sys_b", "fuel") == [(1, 50)]


class TestPriceHistoryTrendArrows:
    """Tests for trend arrow display logic used by trading view."""

    def test_trend_arrow_rising(self) -> None:
        """Rising trend should produce 'rising' which maps to a green up arrow."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 100)
        ph.record("sys_a", "metals", 2, 120)
        ph.record("sys_a", "metals", 3, 140)
        trend = ph.get_trend("sys_a", "metals")
        assert trend == "rising"

    def test_trend_arrow_falling(self) -> None:
        """Falling trend should produce 'falling' which maps to a red down arrow."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 140)
        ph.record("sys_a", "metals", 2, 120)
        ph.record("sys_a", "metals", 3, 100)
        trend = ph.get_trend("sys_a", "metals")
        assert trend == "falling"

    def test_single_entry_is_stable(self) -> None:
        """With only one data point, trend should be stable."""
        ph = PriceHistory()
        ph.record("sys_a", "metals", 1, 100)
        assert ph.get_trend("sys_a", "metals") == "stable"


# ============================================================================
# Dynamic supply/demand tests
# ============================================================================


class TestDynamicSupplyDemand:
    """Tests for player activity affecting market prices."""

    def _make_market(self) -> Market:
        loader = DataLoader()
        loader.load_all()
        nexus = loader.get_system("nexus_prime")
        commodities = loader.get_all_commodities()
        return Market(nexus, commodities, game_day=1)

    def test_buying_raises_price(self) -> None:
        """Player buying should raise the price of a commodity."""
        market = self._make_market()
        price_before = market.get_price("metals")
        market.record_buy("metals", 10)
        market._generate_prices()
        price_after = market.get_price("metals")
        assert price_after >= price_before, "Buying should not lower price"

    def test_selling_lowers_price(self) -> None:
        """Player selling should lower the price of a commodity."""
        market = self._make_market()
        price_before = market.get_price("metals")
        market.record_sell("metals", 10)
        market._generate_prices()
        price_after = market.get_price("metals")
        assert price_after <= price_before, "Selling should not raise price"

    def test_modifier_capped(self) -> None:
        """Supply/demand modifier should be capped at ±0.30."""
        market = self._make_market()
        # Buy massive quantity to hit cap
        market.record_buy("metals", 1000)
        assert market._player_supply_demand.get("metals", 0.0) <= 0.30

    def test_decay_per_day(self) -> None:
        """Supply/demand modifier should decay 30% per day."""
        market = self._make_market()
        market.record_buy("metals", 10)
        mod_before = market._player_supply_demand.get("metals", 0.0)
        assert mod_before > 0

        market.update_day(2)
        mod_after = market._player_supply_demand.get("metals", 0.0)
        # Should decay by 30%
        expected = mod_before * 0.7
        assert abs(mod_after - expected) < 0.001

    def test_defaults_zero(self) -> None:
        """Initially all supply/demand modifiers should be zero."""
        market = self._make_market()
        assert market._player_supply_demand == {}

    def test_serialization(self) -> None:
        """Player supply/demand data should survive to_dict/from_dict cycle."""
        market = self._make_market()
        market.record_buy("metals", 5)
        mod = market._player_supply_demand.get("metals", 0.0)
        assert mod > 0

        data = market.to_dict()
        assert "player_supply_demand" in data
        assert data["player_supply_demand"]["metals"] == mod

    def test_combined_with_base_modifiers(self) -> None:
        """Player modifier should stack with base supply/demand."""
        market = self._make_market()
        base_price = market.get_price("metals")
        # Buy a lot to push price up
        market.record_buy("metals", 10)
        market._generate_prices()
        new_price = market.get_price("metals")
        # Price should have changed (combined modifiers)
        assert new_price >= base_price

    def test_per_commodity_isolation(self) -> None:
        """Buying one commodity should not affect another."""
        market = self._make_market()
        market.record_buy("metals", 10)
        assert market._player_supply_demand.get("metals", 0.0) > 0
        assert market._player_supply_demand.get("fuel_cells", 0.0) == 0
