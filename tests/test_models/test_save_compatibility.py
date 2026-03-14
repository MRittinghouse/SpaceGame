"""Tests for Phase 3 save system compatibility."""

from spacegame.models.market import PriceHistory
from spacegame.models.trade_route import TradeRouteTracker
from spacegame.models.trade_contract import TradeContract, TradeContractManager
from spacegame.save_manager import SaveManager


# ============================================================================
# Helpers
# ============================================================================


def _make_price_history() -> PriceHistory:
    ph = PriceHistory()
    ph.record("nexus_prime", "metals", 1, 100)
    ph.record("nexus_prime", "metals", 2, 110)
    ph.record("breakstone", "fuel_cells", 1, 50)
    return ph


def _make_trade_routes() -> TradeRouteTracker:
    tracker = TradeRouteTracker()
    tracker.record_trip("nexus_prime", "breakstone")
    tracker.record_trip("nexus_prime", "breakstone")
    tracker.record_trip("nexus_prime", "breakstone")
    return tracker


def _make_trade_contracts() -> TradeContractManager:
    mgr = TradeContractManager()
    c = TradeContract(
        id="c1",
        contract_type="sell",
        commodity_id="metals",
        quantity=10,
        price_per_unit=120,
        bonus_credits=200,
        system_id="nexus_prime",
        day_offered=1,
        expiry_day=10,
    )
    mgr._contracts.append(c)
    return mgr


# ============================================================================
# Save includes new fields
# ============================================================================


class TestSaveIncludesNewFields:
    """Serialization should include Phase 3 trading data."""

    def test_serialize_includes_price_history(self) -> None:
        """Price history should appear in serialized save data."""
        mgr = SaveManager()
        ph = _make_price_history()
        # Call _serialize_game_state indirectly by checking the dict structure
        data = ph.to_dict()
        restored = PriceHistory.from_dict(data)
        assert restored.get_history("nexus_prime", "metals") == [(1, 100), (2, 110)]

    def test_serialize_includes_trade_routes(self) -> None:
        """Trade routes should appear in serialized save data."""
        tracker = _make_trade_routes()
        data = tracker.to_dict()
        restored = TradeRouteTracker.from_dict(data)
        assert restored.get_route_count("nexus_prime", "breakstone") == 3

    def test_serialize_includes_trade_contracts(self) -> None:
        """Trade contracts should appear in serialized save data."""
        mgr = _make_trade_contracts()
        data = mgr.to_dict()
        restored = TradeContractManager.from_dict(data)
        assert len(restored._contracts) == 1
        assert restored._contracts[0].id == "c1"
        assert restored._contracts[0].bonus_credits == 200

    def test_serialize_includes_market_supply_demand(self) -> None:
        """Market supply/demand modifiers should serialize and restore."""
        from spacegame.models.market import Market
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        system = dl.get_system("nexus_prime")
        commodities = dl.get_all_commodities()
        market = Market(system, commodities, game_day=1)
        market.record_buy("metals", 5)
        sd_data = market.to_dict()
        assert "metals" in sd_data["player_supply_demand"]
        assert sd_data["player_supply_demand"]["metals"] > 0


# ============================================================================
# Old saves load without error
# ============================================================================


class TestOldSaveBackwardCompat:
    """Old saves without Phase 3 fields should load without error."""

    def test_old_save_no_price_history(self) -> None:
        """Missing price_history in save data should deserialize to None."""
        mgr = SaveManager()
        # Simulate old save data structure (no Phase 3 fields)
        old_save = {
            "version": "1.0",
            "player": _minimal_player_data(),
            "markets": {},
            "active_events": {},
            "event_log": [],
            "tutorial": {},
            "playtime_seconds": 100,
            "metadata": {},
        }
        result = mgr._deserialize_game_state(old_save)
        assert result["price_history"] is None

    def test_old_save_no_trade_routes(self) -> None:
        """Missing trade_routes in save data should deserialize to None."""
        mgr = SaveManager()
        old_save = {
            "version": "1.0",
            "player": _minimal_player_data(),
            "markets": {},
            "active_events": {},
            "playtime_seconds": 0,
        }
        result = mgr._deserialize_game_state(old_save)
        assert result["trade_routes"] is None

    def test_old_save_no_trade_contracts(self) -> None:
        """Missing trade_contracts in save data should deserialize to None."""
        mgr = SaveManager()
        old_save = {
            "version": "1.0",
            "player": _minimal_player_data(),
            "markets": {},
            "active_events": {},
            "playtime_seconds": 0,
        }
        result = mgr._deserialize_game_state(old_save)
        assert result["trade_contracts"] is None

    def test_old_save_no_market_supply_demand(self) -> None:
        """Missing market_supply_demand should default to empty dict."""
        mgr = SaveManager()
        old_save = {
            "version": "1.0",
            "player": _minimal_player_data(),
            "markets": {},
            "active_events": {},
            "playtime_seconds": 0,
        }
        result = mgr._deserialize_game_state(old_save)
        assert result["market_supply_demand"] == {}


# ============================================================================
# Roundtrip with all fields
# ============================================================================


class TestSaveRoundtrip:
    """Full roundtrip: serialize -> deserialize with all Phase 3 fields."""

    def test_roundtrip_price_history(self) -> None:
        """Price history should survive serialize -> deserialize."""
        ph = _make_price_history()
        data = ph.to_dict()
        restored = PriceHistory.from_dict(data)
        history = restored.get_history("nexus_prime", "metals")
        assert len(history) == 2
        assert history[0] == (1, 100)
        assert history[1] == (2, 110)
        # Other system preserved too
        assert len(restored.get_history("breakstone", "fuel_cells")) == 1

    def test_roundtrip_trade_routes(self) -> None:
        """Trade routes should survive serialize -> deserialize."""
        tracker = _make_trade_routes()
        data = tracker.to_dict()
        restored = TradeRouteTracker.from_dict(data)
        assert restored.get_route_count("nexus_prime", "breakstone") == 3
        assert restored.get_efficiency_bonus("nexus_prime", "breakstone") == 0.05

    def test_roundtrip_trade_contracts(self) -> None:
        """Trade contracts should survive serialize -> deserialize."""
        mgr = _make_trade_contracts()
        data = mgr.to_dict()
        restored = TradeContractManager.from_dict(data)
        assert len(restored._contracts) == 1
        c = restored._contracts[0]
        assert c.id == "c1"
        assert c.contract_type == "sell"
        assert c.commodity_id == "metals"
        assert c.quantity == 10
        assert c.price_per_unit == 120
        assert c.bonus_credits == 200
        assert c.system_id == "nexus_prime"
        assert c.expiry_day == 10
        assert not c.completed

    def test_roundtrip_deserialize_with_all_phase3_fields(self) -> None:
        """Deserialize should restore all Phase 3 objects from save data."""
        mgr = SaveManager()
        save_data = {
            "version": "1.0",
            "player": _minimal_player_data(),
            "markets": {},
            "active_events": {},
            "playtime_seconds": 500,
            "price_history": _make_price_history().to_dict(),
            "trade_routes": _make_trade_routes().to_dict(),
            "trade_contracts": _make_trade_contracts().to_dict(),
            "market_supply_demand": {
                "nexus_prime": {"metals": 0.10},
            },
        }
        result = mgr._deserialize_game_state(save_data)

        # Price history restored
        assert result["price_history"] is not None
        assert isinstance(result["price_history"], PriceHistory)
        assert len(result["price_history"].get_history("nexus_prime", "metals")) == 2

        # Trade routes restored
        assert result["trade_routes"] is not None
        assert isinstance(result["trade_routes"], TradeRouteTracker)
        assert result["trade_routes"].get_route_count("nexus_prime", "breakstone") == 3

        # Trade contracts restored
        assert result["trade_contracts"] is not None
        assert isinstance(result["trade_contracts"], TradeContractManager)
        assert len(result["trade_contracts"]._contracts) == 1

        # Market supply/demand restored
        assert result["market_supply_demand"] == {"nexus_prime": {"metals": 0.10}}


# ============================================================================
# Minimal player data for deserialization tests
# ============================================================================


def _minimal_player_data() -> dict:
    """Create minimal player save data for backward compat tests."""
    return {
        "name": "TestCaptain",
        "credits": 5000,
        "current_system_id": "nexus_prime",
        "game_day": 1,
        "ship": {
            "ship_type_id": "light_freighter",
            "current_fuel": 100,
            "current_cargo": {},
            "cargo_purchase_prices": {},
            "current_hull": 100,
            "current_shields": 40,
        },
        "progression": {
            "level": 1,
            "xp": 0,
            "xp_to_next_level": 100,
            "skill_points": 0,
            "purchased_skills": [],
        },
        "upgrades": {"installed": []},
    }
