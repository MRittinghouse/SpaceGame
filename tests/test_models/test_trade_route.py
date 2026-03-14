"""Tests for trade route tracking."""

from spacegame.models.trade_route import TradeRouteTracker


class TestTradeRouteTracker:
    """Tests for TradeRouteTracker."""

    def test_record_trip(self) -> None:
        """Recording a trip should increment the route count."""
        tracker = TradeRouteTracker()
        tracker.record_trip("nexus_prime", "breakstone")
        assert tracker.get_route_count("nexus_prime", "breakstone") == 1

    def test_increment_count(self) -> None:
        """Multiple trips on same route should accumulate."""
        tracker = TradeRouteTracker()
        tracker.record_trip("nexus_prime", "breakstone")
        tracker.record_trip("nexus_prime", "breakstone")
        tracker.record_trip("nexus_prime", "breakstone")
        assert tracker.get_route_count("nexus_prime", "breakstone") == 3

    def test_sorted_key_symmetry(self) -> None:
        """Route A->B should be the same as B->A."""
        tracker = TradeRouteTracker()
        tracker.record_trip("breakstone", "nexus_prime")
        assert tracker.get_route_count("nexus_prime", "breakstone") == 1

    def test_bonus_tier_zero(self) -> None:
        """Under 3 trips: 0% efficiency bonus."""
        tracker = TradeRouteTracker()
        tracker.record_trip("a", "b")
        tracker.record_trip("a", "b")
        assert tracker.get_efficiency_bonus("a", "b") == 0.0

    def test_bonus_tier_5_percent(self) -> None:
        """3+ trips: 5% efficiency bonus."""
        tracker = TradeRouteTracker()
        for _ in range(3):
            tracker.record_trip("a", "b")
        assert tracker.get_efficiency_bonus("a", "b") == 0.05

    def test_bonus_tier_10_percent(self) -> None:
        """5+ trips: 10% efficiency bonus."""
        tracker = TradeRouteTracker()
        for _ in range(5):
            tracker.record_trip("a", "b")
        assert tracker.get_efficiency_bonus("a", "b") == 0.10

    def test_bonus_tier_15_percent(self) -> None:
        """10+ trips: 15% efficiency bonus."""
        tracker = TradeRouteTracker()
        for _ in range(10):
            tracker.record_trip("a", "b")
        assert tracker.get_efficiency_bonus("a", "b") == 0.15

    def test_active_routes_list(self) -> None:
        """get_active_routes should return all routes with counts."""
        tracker = TradeRouteTracker()
        tracker.record_trip("a", "b")
        tracker.record_trip("c", "d")
        tracker.record_trip("c", "d")
        routes = tracker.get_active_routes()
        assert len(routes) == 2
        # Check both routes present (as sorted tuples)
        route_set = {(r[0], r[1]) for r in routes}
        assert ("a", "b") in route_set
        assert ("c", "d") in route_set

    def test_serialization_roundtrip(self) -> None:
        """to_dict/from_dict should preserve route data."""
        tracker = TradeRouteTracker()
        tracker.record_trip("a", "b")
        tracker.record_trip("a", "b")
        tracker.record_trip("c", "d")

        data = tracker.to_dict()
        restored = TradeRouteTracker.from_dict(data)

        assert restored.get_route_count("a", "b") == 2
        assert restored.get_route_count("c", "d") == 1
