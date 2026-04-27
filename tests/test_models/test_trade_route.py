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


# ============================================================================
# PriceMemory (Tier 3.F)
# ============================================================================


class TestPriceMemoryBasics:
    def test_fresh_memory_is_empty(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        assert mem.known_systems() == set()
        assert mem.has_memory("anywhere") is False
        assert mem.get_snapshot("anywhere") == {}
        assert mem.get_last_known("anywhere", "metals") is None

    def test_record_creates_snapshot(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("nexus_prime", {"metals": 120, "luxury_goods": 2500}, game_day=10)

        assert mem.has_memory("nexus_prime")
        assert mem.get_last_known("nexus_prime", "metals") == (120, 10)
        assert mem.get_last_known("nexus_prime", "luxury_goods") == (2500, 10)

    def test_record_overwrites_prior_snapshot(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("breakstone", {"metals": 100}, game_day=5)
        mem.record("breakstone", {"metals": 150, "water": 20}, game_day=10)

        assert mem.get_last_known("breakstone", "metals") == (150, 10)
        assert mem.get_last_known("breakstone", "water") == (20, 10)

    def test_record_zero_price_skipped(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("nexus_prime", {"metals": 100, "quest_item": 0}, game_day=1)
        assert mem.get_last_known("nexus_prime", "metals") == (100, 1)
        assert mem.get_last_known("nexus_prime", "quest_item") is None

    def test_record_empty_system_or_prices_is_noop(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("", {"metals": 100}, game_day=1)
        mem.record("nexus_prime", {}, game_day=1)
        assert mem.known_systems() == set()

    def test_known_systems_returns_all_recorded(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("a", {"metals": 100}, 1)
        mem.record("b", {"metals": 200}, 1)
        mem.record("c", {"metals": 300}, 1)
        assert mem.known_systems() == {"a", "b", "c"}

    def test_clear_wipes_all(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("a", {"metals": 100}, 1)
        mem.clear()
        assert mem.known_systems() == set()


class TestPriceMemorySerialization:
    def test_to_dict_shape_is_save_friendly(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("a", {"metals": 100}, game_day=5)
        data = mem.to_dict()

        assert "snapshots" in data
        entry = data["snapshots"]["a"]["metals"]
        assert isinstance(entry, list)
        assert entry == [100, 5]

    def test_roundtrip_preserves_snapshots(self) -> None:
        import json

        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory()
        mem.record("nexus_prime", {"metals": 120, "electronics": 800}, game_day=10)
        mem.record("breakstone", {"water": 30}, game_day=15)

        restored = PriceMemory.from_dict(json.loads(json.dumps(mem.to_dict())))

        assert restored.known_systems() == {"nexus_prime", "breakstone"}
        assert restored.get_last_known("nexus_prime", "metals") == (120, 10)
        assert restored.get_last_known("breakstone", "water") == (30, 15)

    def test_from_dict_tolerates_missing_snapshots_key(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        mem = PriceMemory.from_dict({})
        assert mem.known_systems() == set()

    def test_from_dict_tolerates_malformed_entry(self) -> None:
        from spacegame.models.trade_route import PriceMemory

        bad = {
            "snapshots": {
                "good_system": {"metals": [100, 5]},
                "bad_system": {"metals": "garbage"},
                "partial": {"metals": [42]},
            }
        }
        mem = PriceMemory.from_dict(bad)
        assert mem.get_last_known("good_system", "metals") == (100, 5)
        assert mem.get_last_known("bad_system", "metals") is None
        assert mem.get_last_known("partial", "metals") is None


class TestPriceMemoryIntegratesWithPlayer:
    def test_player_has_price_memory_by_default(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.models.trade_route import PriceMemory

        dl = get_data_loader()
        dl.load_all()
        ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=10)
        player = Player(name="Test", credits=100, current_system_id="nexus_prime", ship=ship)
        assert isinstance(player.price_memory, PriceMemory)
        assert player.price_memory.known_systems() == set()

    def test_player_to_dict_includes_price_memory(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.save_manager import SaveManager

        dl = get_data_loader()
        dl.load_all()
        ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=10)
        player = Player(name="Test", credits=100, current_system_id="nexus_prime", ship=ship)
        player.price_memory.record("nexus_prime", {"metals": 100}, game_day=1)

        mgr = SaveManager()
        data = mgr._serialize_player(player)
        assert "price_memory" in data
        assert "snapshots" in data["price_memory"]

    def test_player_round_trip_preserves_price_memory(self) -> None:
        import json

        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.save_manager import SaveManager

        dl = get_data_loader()
        dl.load_all()
        ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=10)
        player = Player(name="Test", credits=100, current_system_id="nexus_prime", ship=ship)
        player.price_memory.record("breakstone", {"metals": 120, "water": 20}, game_day=7)

        mgr = SaveManager()
        data = mgr._serialize_player(player)
        restored = mgr._deserialize_player(json.loads(json.dumps(data)))

        assert restored.price_memory.get_last_known("breakstone", "metals") == (120, 7)
        assert restored.price_memory.get_last_known("breakstone", "water") == (20, 7)
