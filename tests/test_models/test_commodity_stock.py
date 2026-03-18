"""Tests for commodity stock limits system."""

from spacegame.data_loader import DataLoader
from spacegame.models.market import Market


def _make_market(system_id: str = "nexus_prime", game_day: int = 1) -> Market:
    """Create a market for testing with stock initialized."""
    loader = DataLoader()
    loader.load_all()
    system = loader.get_system(system_id)
    commodities = loader.get_all_commodities()
    market = Market(system, commodities, game_day=game_day)
    market.initialize_stock(system, commodities)
    return market


class TestStockInitialization:
    """Tests for initial stock levels."""

    def test_produced_commodities_have_high_stock(self) -> None:
        """Systems that produce a commodity should have high base stock."""
        # Verdant produces food
        market = _make_market("verdant")
        stock = market.get_stock("food")
        assert stock >= 80, f"Producer should have high stock, got {stock}"

    def test_consumed_commodities_have_lower_stock(self) -> None:
        """Systems that consume a commodity should have lower stock."""
        # Forgeworks consumes food
        market = _make_market("forgeworks")
        food_stock = market.get_stock("food")
        # Stock should be moderate (consumed means imported, some available)
        assert 0 < food_stock <= 60, (
            f"Consumer should have moderate stock, got {food_stock}"
        )

    def test_unavailable_commodity_has_zero_stock(self) -> None:
        """Commodities not available at a system should have 0 stock."""
        market = _make_market("verdant")
        # Check a commodity that Verdant doesn't stock
        # Get a commodity that's NOT in the market's available list
        unavailable = [
            cid for cid in market._all_commodities
            if cid not in market.commodities
        ]
        if unavailable:
            assert market.get_stock(unavailable[0]) == 0

    def test_all_available_commodities_have_stock(self) -> None:
        """Every available commodity should have some initial stock."""
        market = _make_market("nexus_prime")
        for commodity_id in market.commodities:
            commodity = market.commodities[commodity_id]
            if commodity.base_price > 0:  # Skip quest items
                stock = market.get_stock(commodity_id)
                assert stock > 0, (
                    f"Available commodity {commodity_id} should have stock > 0"
                )


class TestStockDepletion:
    """Tests for stock depletion when buying."""

    def test_buying_depletes_stock(self) -> None:
        """Buying should reduce available stock."""
        market = _make_market()
        commodity_id = "food"
        initial = market.get_stock(commodity_id)

        success, msg = market.deplete_stock(commodity_id, 10)

        assert success, f"Depletion should succeed: {msg}"
        assert market.get_stock(commodity_id) == initial - 10

    def test_cannot_buy_more_than_stock(self) -> None:
        """Attempting to buy more than available stock should fail."""
        market = _make_market()
        commodity_id = "food"
        stock = market.get_stock(commodity_id)

        success, msg = market.deplete_stock(commodity_id, stock + 10)

        assert not success, "Should not deplete more than available"
        # Stock should remain unchanged
        assert market.get_stock(commodity_id) == stock

    def test_stock_zero_blocks_purchase(self) -> None:
        """Cannot buy when stock is 0."""
        market = _make_market()
        commodity_id = "food"
        stock = market.get_stock(commodity_id)

        # Deplete all stock
        market.deplete_stock(commodity_id, stock)
        assert market.get_stock(commodity_id) == 0

        # Try to buy more
        success, msg = market.deplete_stock(commodity_id, 1)
        assert not success

    def test_selling_does_not_affect_stock(self) -> None:
        """Selling cargo should not change the market's stock levels."""
        market = _make_market()
        commodity_id = "food"
        initial = market.get_stock(commodity_id)

        # record_sell doesn't affect stock — stock only tracks supply for buying
        market.record_sell(commodity_id, 50)

        assert market.get_stock(commodity_id) == initial


class TestStockRegeneration:
    """Tests for daily stock regeneration."""

    def test_stock_regenerates_daily(self) -> None:
        """Stock should regenerate when regenerate_stock is called."""
        market = _make_market()
        commodity_id = "food"
        base = market.get_base_stock(commodity_id)
        initial = market.get_stock(commodity_id)

        # Deplete half the stock
        market.deplete_stock(commodity_id, initial // 2)
        depleted = market.get_stock(commodity_id)

        # Regenerate
        market.regenerate_stock()

        regenerated = market.get_stock(commodity_id)
        assert regenerated > depleted, (
            f"Stock should regenerate: depleted={depleted}, after={regenerated}"
        )

    def test_regeneration_caps_at_base(self) -> None:
        """Stock should never exceed base stock after regeneration."""
        market = _make_market()
        commodity_id = "food"
        base = market.get_base_stock(commodity_id)

        # Multiple regenerations shouldn't exceed base
        for _ in range(10):
            market.regenerate_stock()

        assert market.get_stock(commodity_id) <= base, (
            f"Stock should cap at base: stock={market.get_stock(commodity_id)}, base={base}"
        )

    def test_regeneration_rate_is_30_percent(self) -> None:
        """Regeneration should restore approximately 30% of base stock per day."""
        market = _make_market()
        commodity_id = "food"
        base = market.get_base_stock(commodity_id)

        # Fully deplete
        market.deplete_stock(commodity_id, market.get_stock(commodity_id))
        assert market.get_stock(commodity_id) == 0

        # One regeneration
        market.regenerate_stock()
        stock_after = market.get_stock(commodity_id)

        expected = int(base * 0.30)
        # Allow rounding tolerance
        assert abs(stock_after - expected) <= 1, (
            f"Expected ~{expected} after 30% regen, got {stock_after}"
        )


class TestStockSerialization:
    """Tests for stock data persistence."""

    def test_stock_persists_in_to_dict(self) -> None:
        """Stock data should be included in market serialization."""
        market = _make_market()
        market.deplete_stock("food", 10)

        data = market.to_dict()

        assert "stock" in data
        assert "base_stock" in data

    def test_stock_round_trips(self) -> None:
        """Stock should survive to_dict -> load_supply_demand round-trip."""
        market = _make_market()
        initial_food = market.get_stock("food")
        market.deplete_stock("food", 10)

        data = market.to_dict()

        market2 = _make_market()
        market2.load_supply_demand(data)

        assert market2.get_stock("food") == initial_food - 10
