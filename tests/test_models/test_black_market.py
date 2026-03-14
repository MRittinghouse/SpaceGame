"""Tests for black market access and smuggling contract system (Phase C).

Covers black market access conditions, pricing adjustments, smuggling
contract generation, tracking, completion, and failure flows.
"""

import pytest

from spacegame.models.smuggling import (
    BlackMarketAccess,
    SmugglingContract,
    SmugglingContractManager,
    check_black_market_access,
)


# ============================================================================
# Black Market Access Conditions
# ============================================================================


class TestBlackMarketAccess:
    """Black market access depends on system, reputation, and NPC contacts."""

    def test_crimson_reach_always_accessible(self) -> None:
        """Crimson Reach black market is always available."""
        access = check_black_market_access(
            system_id="crimson_reach",
            faction_reputation={},
            dialogue_flags={},
            crew_member_ids=[],
        )
        assert access.available is True
        assert access.market_name == "Wrecker's Market"

    def test_alliance_station_with_malia_contact(self) -> None:
        """Frontier Alliance station accessible with 30+ rep AND Malia contact."""
        access = check_black_market_access(
            system_id="havens_rest",
            faction_reputation={"frontier_alliance": 35},
            dialogue_flags={"met_malia_torres": True},
            crew_member_ids=[],
        )
        assert access.available is True

    def test_alliance_station_without_malia_denied(self) -> None:
        """Alliance station denied without Malia Torres contact."""
        access = check_black_market_access(
            system_id="havens_rest",
            faction_reputation={"frontier_alliance": 50},
            dialogue_flags={},
            crew_member_ids=[],
        )
        assert access.available is False

    def test_alliance_station_low_rep_denied(self) -> None:
        """Alliance station denied with rep below 30 even with Malia contact."""
        access = check_black_market_access(
            system_id="havens_rest",
            faction_reputation={"frontier_alliance": 15},
            dialogue_flags={"met_malia_torres": True},
            crew_member_ids=[],
        )
        assert access.available is False

    def test_nexus_prime_with_dex_and_heat(self) -> None:
        """Nexus Prime accessible with 40+ heat AND Dex Halloran contact."""
        access = check_black_market_access(
            system_id="nexus_prime",
            faction_reputation={},
            dialogue_flags={"met_dex_halloran": True},
            crew_member_ids=[],
            criminal_heat=45,
        )
        assert access.available is True
        assert access.market_name == "The Back Room"

    def test_nexus_prime_low_heat_denied(self) -> None:
        """Nexus Prime denied with heat below 40."""
        access = check_black_market_access(
            system_id="nexus_prime",
            faction_reputation={},
            dialogue_flags={"met_dex_halloran": True},
            crew_member_ids=[],
            criminal_heat=20,
        )
        assert access.available is False

    def test_breakstone_with_marcus_crew(self) -> None:
        """Breakstone accessible with 20+ Union rep AND Marcus crew."""
        access = check_black_market_access(
            system_id="breakstone",
            faction_reputation={"miners_union": 25},
            dialogue_flags={},
            crew_member_ids=["marcus_jin"],
        )
        assert access.available is True

    def test_breakstone_without_marcus_denied(self) -> None:
        """Breakstone denied without Marcus Jin aboard."""
        access = check_black_market_access(
            system_id="breakstone",
            faction_reputation={"miners_union": 50},
            dialogue_flags={},
            crew_member_ids=[],
        )
        assert access.available is False

    def test_unknown_system_denied(self) -> None:
        """Systems with no black market rules are denied."""
        access = check_black_market_access(
            system_id="axiom_labs",
            faction_reputation={},
            dialogue_flags={},
            crew_member_ids=[],
        )
        assert access.available is False

    def test_access_includes_reason_when_denied(self) -> None:
        """Denied access includes a reason string."""
        access = check_black_market_access(
            system_id="havens_rest",
            faction_reputation={"frontier_alliance": 10},
            dialogue_flags={},
            crew_member_ids=[],
        )
        assert access.available is False
        assert access.reason != ""


# ============================================================================
# Black Market Pricing
# ============================================================================


class TestBlackMarketPricing:
    """Black market uses modified pricing: no tariff, premium on legal goods."""

    def test_access_result_has_market_name(self) -> None:
        """Accessible markets have a display name."""
        access = check_black_market_access(
            system_id="crimson_reach",
            faction_reputation={},
            dialogue_flags={},
            crew_member_ids=[],
        )
        assert access.market_name != ""

    def test_legal_goods_premium(self) -> None:
        """Legal goods cost 15% more at black markets."""
        from spacegame.models.smuggling import get_black_market_price_modifier
        from spacegame.models.commodity import Legality

        modifier = get_black_market_price_modifier(Legality.LEGAL)
        assert modifier == pytest.approx(0.15, abs=0.01)

    def test_illegal_goods_discount(self) -> None:
        """Illegal goods cost 10% less at black markets."""
        from spacegame.models.smuggling import get_black_market_price_modifier
        from spacegame.models.commodity import Legality

        modifier = get_black_market_price_modifier(Legality.ILLEGAL)
        assert modifier == pytest.approx(-0.10, abs=0.01)

    def test_restricted_goods_no_modifier(self) -> None:
        """Restricted goods have no price modifier at black markets."""
        from spacegame.models.smuggling import get_black_market_price_modifier
        from spacegame.models.commodity import Legality

        modifier = get_black_market_price_modifier(Legality.RESTRICTED)
        assert modifier == pytest.approx(0.0, abs=0.01)


# ============================================================================
# Smuggling Contract Manager
# ============================================================================


class TestSmugglingContractManager:
    """SmugglingContractManager generates and tracks smuggling contracts."""

    def test_generate_contracts_returns_1_to_3(self) -> None:
        """Generates 1-3 contracts per call."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts(
            system_id="crimson_reach",
            game_day=10,
            player_level=3,
        )
        assert 1 <= len(contracts) <= 3

    def test_generation_is_deterministic(self) -> None:
        """Same inputs produce same contracts."""
        mgr1 = SmugglingContractManager()
        mgr2 = SmugglingContractManager()
        c1 = mgr1.generate_contracts("crimson_reach", 10, 3)
        c2 = mgr2.generate_contracts("crimson_reach", 10, 3)
        assert len(c1) == len(c2)
        for a, b in zip(c1, c2):
            assert a.id == b.id
            assert a.commodity_id == b.commodity_id
            assert a.payment == b.payment

    def test_different_day_different_contracts(self) -> None:
        """Different game days produce different contracts."""
        mgr = SmugglingContractManager()
        c1 = mgr.generate_contracts("crimson_reach", 10, 3)
        mgr2 = SmugglingContractManager()
        c2 = mgr2.generate_contracts("crimson_reach", 13, 3)
        # Contracts should differ (IDs at minimum)
        ids1 = {c.id for c in c1}
        ids2 = {c.id for c in c2}
        assert ids1 != ids2

    def test_contracts_have_required_fields(self) -> None:
        """Generated contracts have all required fields populated."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        for c in contracts:
            assert c.id != ""
            assert c.client_name != ""
            assert c.commodity_id != ""
            assert c.quantity > 0
            assert c.source_system != ""
            assert c.destination_system != ""
            assert c.payment > 0
            assert c.deadline_days > 0
            assert c.difficulty in ("low", "medium", "high")

    def test_difficulty_scales_with_level(self) -> None:
        """Higher player level unlocks harder contracts."""
        mgr_low = SmugglingContractManager()
        low_contracts = []
        for day in range(1, 50):
            mgr_t = SmugglingContractManager()
            low_contracts.extend(mgr_t.generate_contracts("crimson_reach", day, 1))

        mgr_high = SmugglingContractManager()
        high_contracts = []
        for day in range(1, 50):
            mgr_t = SmugglingContractManager()
            high_contracts.extend(mgr_t.generate_contracts("crimson_reach", day, 8))

        low_diffs = {c.difficulty for c in low_contracts}
        high_diffs = {c.difficulty for c in high_contracts}
        # Low level should mostly see "low" difficulty
        assert "low" in low_diffs
        # High level should see "high" difficulty
        assert "high" in high_diffs

    def test_accept_contract(self) -> None:
        """Accepting a contract adds it to active tracking."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]

        success, msg = mgr.accept_contract(contract.id, accepted_day=10)
        assert success is True
        assert contract.id in [c.id for c in mgr.get_active_contracts()]

    def test_accept_already_accepted_fails(self) -> None:
        """Cannot accept the same contract twice."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]

        mgr.accept_contract(contract.id, accepted_day=10)
        success, msg = mgr.accept_contract(contract.id, accepted_day=10)
        assert success is False

    def test_complete_contract(self) -> None:
        """Completing a contract returns payment and heat info."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        result = mgr.complete_contract(
            contract.id,
            current_system=contract.destination_system,
            current_day=12,
        )
        assert result.success is True
        assert result.payment == contract.payment
        assert result.heat_gain == contract.heat_on_completion

    def test_complete_wrong_system_fails(self) -> None:
        """Cannot complete at the wrong system."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        result = mgr.complete_contract(
            contract.id,
            current_system="wrong_system",
            current_day=12,
        )
        assert result.success is False

    def test_complete_expired_contract_fails(self) -> None:
        """Cannot complete an expired contract."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        result = mgr.complete_contract(
            contract.id,
            current_system=contract.destination_system,
            current_day=10 + contract.deadline_days + 5,
        )
        assert result.success is False
        assert result.penalty > 0

    def test_get_expired_contracts(self) -> None:
        """Can retrieve contracts that have expired."""
        mgr = SmugglingContractManager()
        contracts = mgr.generate_contracts("crimson_reach", 10, 3)
        contract = contracts[0]
        mgr.accept_contract(contract.id, accepted_day=10)

        expired = mgr.get_expired_contracts(current_day=10 + contract.deadline_days + 5)
        assert len(expired) >= 1

    def test_serialization_round_trip(self) -> None:
        """Manager serializes and deserializes correctly."""
        mgr = SmugglingContractManager()
        mgr.generate_contracts("crimson_reach", 10, 3)
        contracts = mgr.get_available_contracts("crimson_reach")
        if contracts:
            mgr.accept_contract(contracts[0].id, accepted_day=10)

        data = mgr.to_dict()
        restored = SmugglingContractManager.from_dict(data)

        assert len(restored.get_available_contracts("crimson_reach")) == len(
            mgr.get_available_contracts("crimson_reach")
        )
        assert len(restored.get_active_contracts()) == len(mgr.get_active_contracts())

    def test_max_active_contracts(self) -> None:
        """Player can have at most 3 active smuggling contracts."""
        mgr = SmugglingContractManager()
        # Generate multiple batches to get enough contracts
        for day in range(10, 30):
            mgr.generate_contracts("crimson_reach", day, 5)

        available = mgr.get_available_contracts("crimson_reach")
        accepted = 0
        for c in available:
            success, _ = mgr.accept_contract(c.id, accepted_day=15)
            if success:
                accepted += 1
            if accepted >= 4:
                break

        active = mgr.get_active_contracts()
        assert len(active) <= 3


# ============================================================================
# Black Market Access Permits (Phase E)
# ============================================================================


class TestBlackMarketAccessPermits:
    """Player.black_market_access: permit-based access system."""

    def _make_player(self) -> "Player":
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="shuttle",
            name="Shuttle",
            ship_class="light",
            description="Basic ship",
            cargo_capacity=50,
            fuel_capacity=100,
            fuel_efficiency=1.0,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=1,
            special_abilities=[],
            availability="all",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        return Player(
            name="Test",
            credits=5000,
            current_system_id="nexus_prime",
            ship=ship,
        )

    def test_black_market_access_default_empty(self) -> None:
        """black_market_access should default to empty set."""
        player = self._make_player()
        assert player.black_market_access == set()
        assert isinstance(player.black_market_access, set)

    def test_grant_black_market_access(self) -> None:
        """grant_black_market_access adds system to set."""
        player = self._make_player()
        player.grant_black_market_access("crimson_reach")
        assert "crimson_reach" in player.black_market_access

    def test_has_black_market_access(self) -> None:
        """has_black_market_access returns True when granted."""
        player = self._make_player()
        assert player.has_black_market_access("crimson_reach") is False
        player.grant_black_market_access("crimson_reach")
        assert player.has_black_market_access("crimson_reach") is True

    def test_grant_idempotent(self) -> None:
        """Granting the same system twice does not duplicate."""
        player = self._make_player()
        player.grant_black_market_access("crimson_reach")
        player.grant_black_market_access("crimson_reach")
        assert len(player.black_market_access) == 1

    def test_multiple_systems(self) -> None:
        """Can grant access to multiple systems."""
        player = self._make_player()
        player.grant_black_market_access("crimson_reach")
        player.grant_black_market_access("havens_rest")
        player.grant_black_market_access("breakstone")
        assert len(player.black_market_access) == 3
        assert player.has_black_market_access("havens_rest") is True

    def test_black_market_access_serialization_roundtrip(self) -> None:
        """black_market_access survives save/load cycle."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = self._make_player()
        player.grant_black_market_access("crimson_reach")
        player.grant_black_market_access("havens_rest")

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.has_black_market_access("crimson_reach") is True
            assert p2.has_black_market_access("havens_rest") is True
            assert p2.has_black_market_access("breakstone") is False

    def test_backward_compat_old_save(self) -> None:
        """Old saves without black_market_access load with empty set."""
        from spacegame.save_manager import SaveManager
        from spacegame.data_loader import get_data_loader
        import tempfile
        from pathlib import Path

        dl = get_data_loader()
        dl.load_all()

        player = self._make_player()
        # Don't grant any access — simulates old save

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.black_market_access == set()


# ============================================================================
# Black Market Helper Functions (Phase E)
# ============================================================================


class TestBlackMarketHelpers:
    """get_black_market_name and get_black_market_systems helpers."""

    def test_get_black_market_name_valid(self) -> None:
        """Returns market name for a system with a black market."""
        from spacegame.models.smuggling import get_black_market_name

        assert get_black_market_name("crimson_reach") == "Wrecker's Market"
        assert get_black_market_name("nexus_prime") == "The Back Room"
        assert get_black_market_name("breakstone") == "The Undershaft"

    def test_get_black_market_name_invalid(self) -> None:
        """Returns None for a system with no black market."""
        from spacegame.models.smuggling import get_black_market_name

        assert get_black_market_name("axiom_labs") is None
        assert get_black_market_name("nonexistent") is None

    def test_get_black_market_systems(self) -> None:
        """Returns all system IDs that have black markets."""
        from spacegame.models.smuggling import get_black_market_systems

        systems = get_black_market_systems()
        assert "crimson_reach" in systems
        assert "havens_rest" in systems
        assert "nexus_prime" in systems
        assert "breakstone" in systems
        assert len(systems) == 6  # matches _BLACK_MARKET_RULES
