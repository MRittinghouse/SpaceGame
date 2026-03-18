"""Tests for wiring dormant market systems: supply/demand, price history, trade routes."""

from spacegame.data_loader import DataLoader
from spacegame.models.market import Market, PriceHistory
from spacegame.models.trade_route import TradeRouteTracker


def _make_market(system_id: str = "nexus_prime", game_day: int = 1) -> Market:
    """Create a market for testing."""
    loader = DataLoader()
    loader.load_all()
    system = loader.get_system(system_id)
    commodities = loader.get_all_commodities()
    return Market(system, commodities, game_day=game_day)


class TestPlayerSupplyDemandWiring:
    """Tests that record_buy/record_sell affect pricing."""

    def test_buying_increases_price(self) -> None:
        """Buying large quantities should raise the commodity's price."""
        market = _make_market()
        commodity_id = "food"
        price_before = market.get_price(commodity_id)

        market.record_buy(commodity_id, 50)
        market._generate_prices()  # Recalculate with new modifier

        price_after = market.get_price(commodity_id)
        assert price_after > price_before, (
            f"Price should increase after buying 50 units: "
            f"before={price_before}, after={price_after}"
        )

    def test_selling_decreases_price(self) -> None:
        """Selling large quantities should lower the commodity's price."""
        market = _make_market()
        commodity_id = "food"
        price_before = market.get_price(commodity_id)

        market.record_sell(commodity_id, 50)
        market._generate_prices()

        price_after = market.get_price(commodity_id)
        assert price_after < price_before, (
            f"Price should decrease after selling 50 units: "
            f"before={price_before}, after={price_after}"
        )

    def test_small_trades_minimal_impact(self) -> None:
        """Buying 1-2 units should have minimal price impact."""
        market = _make_market()
        commodity_id = "food"
        price_before = market.get_price(commodity_id)

        market.record_buy(commodity_id, 1)
        market._generate_prices()

        price_after = market.get_price(commodity_id)
        # 1 unit * 0.02 per unit = 2% modifier — price may change by 0-1 due to rounding
        assert abs(price_after - price_before) <= 2, (
            f"Price change should be minimal for 1 unit: "
            f"before={price_before}, after={price_after}"
        )

    def test_modifier_decays_over_time(self) -> None:
        """Player modifier should decay when update_day is called."""
        market = _make_market()
        commodity_id = "food"

        market.record_buy(commodity_id, 50)
        market._generate_prices()
        price_day1 = market.get_price(commodity_id)

        # Advance several days — modifier decays by 30% each day
        for day in range(2, 6):
            market.update_day(day)

        price_day5 = market.get_price(commodity_id)
        original_price = _make_market().get_price(commodity_id)

        # After 4 days of decay (0.7^4 = 0.24), price should be closer to original
        assert abs(price_day5 - original_price) < abs(price_day1 - original_price), (
            f"Price should decay toward original over time: "
            f"day1={price_day1}, day5={price_day5}, original={original_price}"
        )

    def test_modifier_capped(self) -> None:
        """Player modifier should be capped at ±30%."""
        market = _make_market()
        commodity_id = "food"

        # Buy a huge amount — should hit the cap
        market.record_buy(commodity_id, 1000)
        assert market._player_supply_demand[commodity_id] <= 0.30

    def test_modifier_persists_in_save(self) -> None:
        """Player supply/demand should round-trip through to_dict/load."""
        market = _make_market()
        market.record_buy("food", 20)
        market.record_sell("ore", 15)

        data = market.to_dict()
        assert "player_supply_demand" in data
        assert data["player_supply_demand"]["food"] > 0
        assert data["player_supply_demand"]["ore"] < 0

        # Restore into a new market
        market2 = _make_market()
        market2.load_supply_demand(data)
        assert market2._player_supply_demand["food"] == market._player_supply_demand["food"]
        assert market2._player_supply_demand["ore"] == market._player_supply_demand["ore"]


class TestPriceHistoryWiring:
    """Tests for PriceHistory recording and trend detection."""

    def test_record_and_retrieve_price(self) -> None:
        """Recorded prices can be retrieved."""
        ph = PriceHistory()
        ph.record("nexus_prime", "food", 1, 100)
        ph.record("nexus_prime", "food", 2, 110)

        history = ph.get_history("nexus_prime", "food")
        assert len(history) == 2
        assert history[0] == (1, 100)
        assert history[1] == (2, 110)

    def test_get_trend_rising(self) -> None:
        """Rising prices should return 'rising' trend."""
        ph = PriceHistory()
        ph.record("nexus_prime", "food", 1, 100)
        ph.record("nexus_prime", "food", 2, 115)  # >5% increase

        assert ph.get_trend("nexus_prime", "food") == "rising"

    def test_get_trend_falling(self) -> None:
        """Falling prices should return 'falling' trend."""
        ph = PriceHistory()
        ph.record("nexus_prime", "food", 1, 100)
        ph.record("nexus_prime", "food", 2, 90)  # >5% decrease

        assert ph.get_trend("nexus_prime", "food") == "falling"

    def test_get_trend_stable(self) -> None:
        """Flat prices should return 'stable' trend."""
        ph = PriceHistory()
        ph.record("nexus_prime", "food", 1, 100)
        ph.record("nexus_prime", "food", 2, 102)  # <5% change

        assert ph.get_trend("nexus_prime", "food") == "stable"

    def test_trend_with_insufficient_data(self) -> None:
        """Fewer than 2 data points should return 'stable'."""
        ph = PriceHistory()
        ph.record("nexus_prime", "food", 1, 100)

        assert ph.get_trend("nexus_prime", "food") == "stable"

    def test_trend_no_data(self) -> None:
        """No data at all should return 'stable'."""
        ph = PriceHistory()
        assert ph.get_trend("nexus_prime", "food") == "stable"

    def test_price_history_serialization(self) -> None:
        """PriceHistory should round-trip through to_dict/from_dict."""
        ph = PriceHistory()
        ph.record("nexus_prime", "food", 1, 100)
        ph.record("nexus_prime", "food", 2, 110)
        ph.record("forgeworks", "ore", 1, 50)

        data = ph.to_dict()
        ph2 = PriceHistory.from_dict(data)

        assert ph2.get_history("nexus_prime", "food") == [(1, 100), (2, 110)]
        assert ph2.get_history("forgeworks", "ore") == [(1, 50)]
        assert ph2.max_days == ph.max_days

    def test_history_trims_to_max_days(self) -> None:
        """History should keep only the most recent max_days entries."""
        ph = PriceHistory(max_days=3)
        for day in range(1, 6):
            ph.record("nexus_prime", "food", day, 100 + day)

        history = ph.get_history("nexus_prime", "food")
        assert len(history) == 3
        assert history[0] == (3, 103)  # Oldest kept


class TestTradeRouteTrackerWiring:
    """Tests for TradeRouteTracker."""

    def test_record_trip_increments_count(self) -> None:
        """Recording a trip increases the route count."""
        tracker = TradeRouteTracker()
        tracker.record_trip("nexus_prime", "forgeworks")
        assert tracker.get_route_count("nexus_prime", "forgeworks") == 1

        tracker.record_trip("nexus_prime", "forgeworks")
        assert tracker.get_route_count("nexus_prime", "forgeworks") == 2

    def test_3_trips_gives_5_percent_bonus(self) -> None:
        """3 trips on a route should give 5% efficiency bonus."""
        tracker = TradeRouteTracker()
        for _ in range(3):
            tracker.record_trip("nexus_prime", "forgeworks")

        assert tracker.get_efficiency_bonus("nexus_prime", "forgeworks") == 0.05

    def test_5_trips_gives_10_percent_bonus(self) -> None:
        """5 trips should give 10% bonus."""
        tracker = TradeRouteTracker()
        for _ in range(5):
            tracker.record_trip("nexus_prime", "forgeworks")

        assert tracker.get_efficiency_bonus("nexus_prime", "forgeworks") == 0.10

    def test_10_trips_gives_15_percent_bonus(self) -> None:
        """10 trips should give 15% bonus."""
        tracker = TradeRouteTracker()
        for _ in range(10):
            tracker.record_trip("nexus_prime", "forgeworks")

        assert tracker.get_efficiency_bonus("nexus_prime", "forgeworks") == 0.15

    def test_bonus_applies_to_both_directions(self) -> None:
        """A->B and B->A should share the same route."""
        tracker = TradeRouteTracker()
        tracker.record_trip("nexus_prime", "forgeworks")
        tracker.record_trip("forgeworks", "nexus_prime")
        tracker.record_trip("nexus_prime", "forgeworks")

        assert tracker.get_route_count("nexus_prime", "forgeworks") == 3
        assert tracker.get_route_count("forgeworks", "nexus_prime") == 3
        assert tracker.get_efficiency_bonus("forgeworks", "nexus_prime") == 0.05

    def test_route_tracker_serialization(self) -> None:
        """TradeRouteTracker should round-trip through to_dict/from_dict."""
        tracker = TradeRouteTracker()
        for _ in range(5):
            tracker.record_trip("nexus_prime", "forgeworks")
        tracker.record_trip("verdant", "havens_rest")

        data = tracker.to_dict()
        tracker2 = TradeRouteTracker.from_dict(data)

        assert tracker2.get_route_count("nexus_prime", "forgeworks") == 5
        assert tracker2.get_route_count("verdant", "havens_rest") == 1
        assert tracker2.get_efficiency_bonus("nexus_prime", "forgeworks") == 0.10

    def test_no_trips_no_bonus(self) -> None:
        """Routes with 0-2 trips should have no bonus."""
        tracker = TradeRouteTracker()
        assert tracker.get_efficiency_bonus("nexus_prime", "forgeworks") == 0.0

        tracker.record_trip("nexus_prime", "forgeworks")
        tracker.record_trip("nexus_prime", "forgeworks")
        assert tracker.get_efficiency_bonus("nexus_prime", "forgeworks") == 0.0
