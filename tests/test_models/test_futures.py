"""SA-F2 unit tests for the futures sub-system.

Covers:
- ``FuturesContract`` field defaults and to/from dict round-trip.
- ``FuturesState`` empty + populated round-trip, sequence persistence.
- ``PricingEngine`` Section 3.4 example integers (A/B/C).
- Direction / duration / quantity guards.
- Speculator reduction cap.
- Accept lifecycle (credit debit, flag idempotence, journal fire).
- Settlement math (LONG/SHORT × profit/loss, running totals, zero-price
  deferral).
- Side-effect gates (headliner news threshold, Commerce Guild rep delta).
- Save-migration: pre-SA-F2 dict + malformed payload load cleanly.

The Section 3.4 example tests use synthetic ``StarSystem`` instances so
the hop distance resolves to the illustrative values (3/2/1) named in
the design doc. The bucket-table calibration itself is validated
separately against the shipped galaxy JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from spacegame.constants.flags import (
    futures_first_contract_accepted,
    futures_first_loss,
    futures_first_win,
)
from spacegame.models.commodity import Commodity, CommodityCategory, Legality
from spacegame.models.futures import (
    BASE_BROKER_SPREAD,
    COMMERCE_GUILD_FACTION_ID,
    COMMERCE_GUILD_PROFIT_THRESHOLD,
    DURATION_SPREAD,
    HEADLINER_NOTIONAL_THRESHOLD,
    HOP_PENALTY,
    MAX_SPECULATOR_REDUCTION,
    MIN_QUANTITY,
    TREND_PREMIUM,
    VALID_DURATIONS,
    FuturesContract,
    FuturesState,
    PricingEngine,
)
from spacegame.models.system import Coordinates, Economy, StarSystem

# ---------------------------------------------------------------------------
# Shared test doubles
# ---------------------------------------------------------------------------


class _StubMarket:
    """Just enough Market surface for the futures tests."""

    def __init__(self, prices: dict[str, int], commodities: Optional[list[Commodity]] = None):
        self._prices = dict(prices)
        self._all_commodities = {c.id: c for c in (commodities or [])}

    def get_price(self, commodity_id: str) -> int:
        return self._prices.get(commodity_id, 0)


class _StubPriceHistory:
    """Returns a fixed trend for any (system, commodity) pair."""

    def __init__(self, trend: str = "stable"):
        self.trend = trend

    def get_trend(self, system_id: str, commodity_id: str) -> str:
        return self.trend


class _StubBonusSource:
    """Object satisfying the .get_bonus(name) shape used by PricingEngine."""

    def __init__(self, bonuses: Optional[dict[str, float]] = None):
        self._bonuses = dict(bonuses or {})

    def get_bonus(self, bonus_type: str) -> float:
        return self._bonuses.get(bonus_type, 0.0)


@dataclass
class _FakePlayer:
    """Minimal Player stand-in — enough for FuturesState.accept/advance_day."""

    credits: int = 10_000
    dialogue_flags: dict[str, bool] = field(default_factory=dict)
    max_credits_held: int = 10_000

    def add_credits(self, amount: int) -> None:
        self.credits += amount
        if self.credits > self.max_credits_held:
            self.max_credits_held = self.credits

    def deduct_credits(self, amount: int) -> bool:
        if amount > self.credits:
            return False
        self.credits -= amount
        return True


class _FakeJournal:
    """Captures programmatic auto-entries added by the model."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def add_auto_entry(
        self,
        entry_id: str,
        text: str,
        game_day: int,
        system_id: str = "",
        tag: str = "",
        mission_id: str = "",
    ) -> None:
        self.entries.append(
            {
                "entry_id": entry_id,
                "text": text,
                "game_day": game_day,
                "system_id": system_id,
                "tag": tag,
                "mission_id": mission_id,
            }
        )


class _FakeNewsTicker:
    """Provides a mutable ``pending_events`` list for the queue path."""

    def __init__(self) -> None:
        self.pending_events: list[dict[str, Any]] = []


class _FakeReputationManager:
    """Records apply_reputation_with_spillover calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def apply_reputation_with_spillover(
        self, player: Any, faction_id: str, amount: int
    ) -> list[tuple[str, int]]:
        self.calls.append((faction_id, amount))
        return [(faction_id, amount)]


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_commodity(
    commodity_id: str,
    *,
    base_price: int = 60,
    production_tags: Optional[list[str]] = None,
    consumption_tags: Optional[list[str]] = None,
) -> Commodity:
    return Commodity(
        id=commodity_id,
        name=commodity_id.replace("_", " ").title(),
        category=CommodityCategory.BASIC,
        description="test commodity",
        base_price=base_price,
        variance_min=-0.15,
        variance_max=0.15,
        volume_per_unit=1,
        legality=Legality.LEGAL,
        production_tags=production_tags or [commodity_id],
        consumption_tags=consumption_tags or [],
    )


def _make_system(
    system_id: str,
    *,
    x: float,
    y: float,
    production_tags: Optional[list[str]] = None,
) -> StarSystem:
    return StarSystem(
        id=system_id,
        name=system_id.replace("_", " ").title(),
        type="mining",
        description="test system",
        coordinates=Coordinates(x=x, y=y),
        danger_level="safe",
        faction="test",
        stations=[],
        economy=Economy(
            production_tags=production_tags or [],
            consumption_tags=[],
            tariff_rate=0.0,
        ),
        rest_cost=0,
    )


def _make_contract(**overrides: Any) -> FuturesContract:
    defaults: dict[str, Any] = {
        "contract_id": "futures_1_common_metals_001",
        "commodity_id": "common_metals",
        "direction": "LONG",
        "strike_price": 67,
        "quantity": 80,
        "duration_days": 7,
        "entry_cost": 214,
        "accept_day": 1,
        "maturity_day": 8,
    }
    defaults.update(overrides)
    return FuturesContract(**defaults)


# ---------------------------------------------------------------------------
# FuturesContract dataclass + round-trip
# ---------------------------------------------------------------------------


class TestFuturesContract:
    def test_defaults_leave_settlement_fields_unset(self) -> None:
        contract = _make_contract()
        assert contract.settled is False
        assert contract.payoff is None
        assert contract.settlement_day is None
        assert contract.settlement_price is None

    def test_to_from_dict_round_trip_preserves_all_fields(self) -> None:
        contract = _make_contract(
            settled=True,
            payoff=560,
            settlement_day=8,
            settlement_price=74,
        )
        restored = FuturesContract.from_dict(contract.to_dict())
        assert restored == contract

    def test_from_dict_tolerates_missing_optional_fields(self) -> None:
        raw = {
            "contract_id": "x",
            "commodity_id": "common_metals",
            "direction": "SHORT",
            "strike_price": 100,
            "quantity": 20,
            "duration_days": 7,
            "entry_cost": 50,
            "accept_day": 1,
            "maturity_day": 8,
        }
        restored = FuturesContract.from_dict(raw)
        assert restored.settled is False
        assert restored.payoff is None


# ---------------------------------------------------------------------------
# FuturesState round-trip + sequence
# ---------------------------------------------------------------------------


class TestFuturesStateRoundTrip:
    def test_empty_state_round_trip_is_identity(self) -> None:
        state = FuturesState()
        restored = FuturesState.from_dict(state.to_dict())
        assert restored.active_contracts == []
        assert restored.settled_contracts == []
        assert restored.total_credits_won == 0
        assert restored.total_credits_lost == 0

    def test_populated_state_round_trip_preserves_lists_and_totals(self) -> None:
        state = FuturesState()
        state.active_contracts.append(_make_contract())
        state.settled_contracts.append(
            _make_contract(
                contract_id="futures_1_medical_002",
                commodity_id="medical",
                settled=True,
                payoff=-360,
                settlement_day=15,
                settlement_price=461,
            )
        )
        state.total_credits_won = 560
        state.total_credits_lost = 360
        state.next_sequence()  # advance seq to 1
        state.next_sequence()  # advance seq to 2

        restored = FuturesState.from_dict(state.to_dict())
        assert restored.active_contracts == state.active_contracts
        assert restored.settled_contracts == state.settled_contracts
        assert restored.total_credits_won == 560
        assert restored.total_credits_lost == 360
        # Sequence continues past the persisted value.
        assert restored.next_sequence() == 3

    def test_from_dict_none_returns_empty_state(self) -> None:
        state = FuturesState.from_dict(None)
        assert state.active_contracts == []
        assert state._contract_seq == 0

    def test_from_dict_bad_payload_returns_empty_state(self) -> None:
        state = FuturesState.from_dict({"active_contracts": "not-a-list"})
        assert state.active_contracts == []

    def test_pre_sa_f2_save_dict_loads_cleanly(self) -> None:
        """A save with no futures_state key loads to an empty FuturesState."""
        pre_sa_f2_data = {"credits": 5_000, "game_day": 1}
        state = FuturesState.from_dict(pre_sa_f2_data.get("futures_state"))
        assert state.active_contracts == []
        assert state._contract_seq == 0


# ---------------------------------------------------------------------------
# PricingEngine: Section 3.4 worked examples
# ---------------------------------------------------------------------------


class TestPricingEngineExamples:
    """Verify Section 3.4 examples produce the exact strike/entry-cost integers."""

    def _engine_and_context(
        self,
        *,
        commodity_id: str,
        current_price: int,
        trend: str,
        producer_distance: float,
        production_tags: Optional[list[str]] = None,
    ) -> tuple[
        PricingEngine,
        Commodity,
        _StubMarket,
        _StubPriceHistory,
        list[StarSystem],
        StarSystem,
    ]:
        commodity = _make_commodity(
            commodity_id, base_price=current_price, production_tags=production_tags
        )
        market = _StubMarket({commodity_id: current_price}, commodities=[commodity])
        history = _StubPriceHistory(trend=trend)
        nexus_prime = _make_system("nexus_prime", x=0.0, y=0.0)
        producer = _make_system(
            "test_producer",
            x=producer_distance,
            y=0.0,
            production_tags=production_tags or [commodity_id],
        )
        return PricingEngine(), commodity, market, history, [nexus_prime, producer], nexus_prime

    def test_example_a_common_metals_long_7d_no_bonuses(self) -> None:
        """Section 3.4 Example A: strike=67, entry_cost=214."""
        engine, commodity, market, history, systems, nexus = self._engine_and_context(
            commodity_id="common_metals",
            current_price=62,
            trend="rising",
            producer_distance=85.0,  # bucket 3 (60-90)
            production_tags=["common_metals", "raw_materials", "mining"],
        )

        contract = engine.generate_offer(
            commodity=commodity,
            direction="LONG",
            duration_days=7,
            quantity=80,
            current_day=1,
            market=market,
            progression=None,
            crew_roster=None,
            all_systems=systems,
            nexus_prime=nexus,
            sequence=1,
            price_history=history,
        )
        assert isinstance(contract, FuturesContract)
        assert contract.strike_price == 67
        assert contract.entry_cost == 214
        assert contract.direction == "LONG"
        assert contract.quantity == 80
        assert contract.duration_days == 7
        assert contract.accept_day == 1
        assert contract.maturity_day == 8

    def test_example_b_medical_long_14d_brix_tano_only(self) -> None:
        """Section 3.4 Example B: strike=479, entry_cost=344.

        The design doc labels the entry_cost as 345 ("floor(345.12)"),
        but 479 * 20 * 0.036 = 344.88, not 345.12. Faithfully applying
        the Section 3.2 formula produces 344; the doc's stated integer
        is off by one due to an arithmetic error in the worked-example
        commentary (see the SA-F2 implementation phase report).
        """
        engine, commodity, market, history, systems, nexus = self._engine_and_context(
            commodity_id="medical",
            current_price=444,
            trend="stable",
            producer_distance=45.0,  # bucket 2 (30-60)
            production_tags=["medical", "research", "high_tech"],
        )
        crew_roster = _StubBonusSource({"speculator_premium_reduction": 0.10})

        contract = engine.generate_offer(
            commodity=commodity,
            direction="LONG",
            duration_days=14,
            quantity=20,
            current_day=1,
            market=market,
            progression=None,
            crew_roster=crew_roster,
            all_systems=systems,
            nexus_prime=nexus,
            sequence=2,
            price_history=history,
        )
        assert isinstance(contract, FuturesContract)
        assert contract.strike_price == 479
        assert contract.entry_cost == 344

    def test_example_c_manufactured_goods_short_21d_max_bonuses(self) -> None:
        """Section 3.4 Example C: strike=167, entry_cost=267."""
        engine, commodity, market, history, systems, nexus = self._engine_and_context(
            commodity_id="manufactured_goods",
            current_price=152,
            trend="falling",
            producer_distance=15.0,  # bucket 1 (0-30)
            production_tags=["manufactured_goods", "industrial"],
        )
        progression = _StubBonusSource({"speculator_premium_reduction": 0.10})  # L2
        crew_roster = _StubBonusSource({"speculator_premium_reduction": 0.10})  # Brix

        contract = engine.generate_offer(
            commodity=commodity,
            direction="SHORT",
            duration_days=21,
            quantity=50,
            current_day=1,
            market=market,
            progression=progression,
            crew_roster=crew_roster,
            all_systems=systems,
            nexus_prime=nexus,
            sequence=3,
            price_history=history,
        )
        assert isinstance(contract, FuturesContract)
        assert contract.strike_price == 167
        assert contract.entry_cost == 267


# ---------------------------------------------------------------------------
# PricingEngine: guard rails
# ---------------------------------------------------------------------------


class TestPricingEngineGuards:
    def _context(self) -> tuple[PricingEngine, Commodity, _StubMarket, StarSystem]:
        commodity = _make_commodity("common_metals", base_price=60)
        market = _StubMarket({"common_metals": 60}, commodities=[commodity])
        nexus = _make_system("nexus_prime", x=0.0, y=0.0)
        return PricingEngine(), commodity, market, nexus

    def test_quantity_below_minimum_rejected(self) -> None:
        engine, commodity, market, nexus = self._context()
        result = engine.generate_offer(
            commodity=commodity,
            direction="LONG",
            duration_days=7,
            quantity=MIN_QUANTITY - 1,
            current_day=1,
            market=market,
            progression=None,
            crew_roster=None,
            all_systems=[nexus],
            nexus_prime=nexus,
            sequence=1,
            price_history=_StubPriceHistory(),
        )
        assert isinstance(result, tuple)
        ok, reason = result
        assert ok is False
        assert str(MIN_QUANTITY) in reason

    def test_duration_outside_whitelist_rejected(self) -> None:
        engine, commodity, market, nexus = self._context()
        for bad_duration in (0, 3, 10, 30):
            assert bad_duration not in VALID_DURATIONS
            result = engine.generate_offer(
                commodity=commodity,
                direction="LONG",
                duration_days=bad_duration,
                quantity=20,
                current_day=1,
                market=market,
                progression=None,
                crew_roster=None,
                all_systems=[nexus],
                nexus_prime=nexus,
                sequence=1,
                price_history=_StubPriceHistory(),
            )
            assert isinstance(result, tuple)
            ok, _ = result
            assert ok is False, f"duration={bad_duration} should be rejected"

    def test_invalid_direction_rejected(self) -> None:
        engine, commodity, market, nexus = self._context()
        result = engine.generate_offer(
            commodity=commodity,
            direction="STRADDLE",
            duration_days=7,
            quantity=20,
            current_day=1,
            market=market,
            progression=None,
            crew_roster=None,
            all_systems=[nexus],
            nexus_prime=nexus,
            sequence=1,
            price_history=_StubPriceHistory(),
        )
        assert isinstance(result, tuple)
        ok, reason = result
        assert ok is False
        assert "STRADDLE" in reason

    def test_zero_market_price_rejected(self) -> None:
        engine, commodity, _, nexus = self._context()
        embargo_market = _StubMarket({"common_metals": 0}, commodities=[commodity])
        result = engine.generate_offer(
            commodity=commodity,
            direction="LONG",
            duration_days=7,
            quantity=20,
            current_day=1,
            market=embargo_market,
            progression=None,
            crew_roster=None,
            all_systems=[nexus],
            nexus_prime=nexus,
            sequence=1,
            price_history=_StubPriceHistory(),
        )
        assert isinstance(result, tuple)
        ok, _ = result
        assert ok is False

    def test_speculator_reduction_capped_at_max(self) -> None:
        """Combined skill + crew stack of 0.30 caps at 0.25."""
        engine = PricingEngine()
        progression = _StubBonusSource({"speculator_premium_reduction": 0.20})
        crew_roster = _StubBonusSource({"speculator_premium_reduction": 0.10})
        reduction = engine.speculator_reduction(progression, crew_roster)
        assert reduction == pytest.approx(MAX_SPECULATOR_REDUCTION)

        # Verify the cap flows into entry_cost. With 0.25 the broker rate
        # is 0.04 * 0.75 = 0.03 — well below the uncapped 0.028.
        commodity = _make_commodity("test", base_price=100)
        market = _StubMarket({"test": 100}, commodities=[commodity])
        nexus = _make_system("nexus_prime", x=0.0, y=0.0)
        contract = engine.generate_offer(
            commodity=commodity,
            direction="LONG",
            duration_days=7,
            quantity=100,
            current_day=1,
            market=market,
            progression=progression,
            crew_roster=crew_roster,
            all_systems=[nexus],
            nexus_prime=nexus,
            sequence=1,
            price_history=_StubPriceHistory(trend="stable"),
            hop_distance_override=1,
        )
        assert isinstance(contract, FuturesContract)
        # strike = int(100 * (1 + 0.01 + 0.01 + 0.02)) = int(104) = 104
        # entry = int(104 * 100 * 0.04 * 0.75) = int(312) = 312
        assert contract.strike_price == 104
        assert contract.entry_cost == 312

    def test_hop_distance_defaults_to_max_without_producers(self) -> None:
        engine = PricingEngine()
        commodity = _make_commodity("uncommon", production_tags=["never_produced"])
        nexus = _make_system("nexus_prime", x=0.0, y=0.0)
        # No system tagged "never_produced".
        other = _make_system("other", x=10.0, y=0.0, production_tags=["something_else"])
        assert engine.hop_distance(commodity, [nexus, other], nexus) == 5


# ---------------------------------------------------------------------------
# Contract ID uniqueness
# ---------------------------------------------------------------------------


class TestContractIdScheme:
    def test_contract_id_is_deterministic_and_unique(self) -> None:
        engine = PricingEngine()
        commodity = _make_commodity("common_metals", base_price=60)
        market = _StubMarket({"common_metals": 60}, commodities=[commodity])
        nexus = _make_system("nexus_prime", x=0.0, y=0.0)
        producer = _make_system("producer", x=50.0, y=0.0, production_tags=["common_metals"])

        state = FuturesState()
        contracts = []
        for _ in range(3):
            seq = state.next_sequence()
            contract = engine.generate_offer(
                commodity=commodity,
                direction="LONG",
                duration_days=7,
                quantity=20,
                current_day=5,
                market=market,
                progression=None,
                crew_roster=None,
                all_systems=[nexus, producer],
                nexus_prime=nexus,
                sequence=seq,
                price_history=_StubPriceHistory(),
            )
            assert isinstance(contract, FuturesContract)
            contracts.append(contract)

        ids = [c.contract_id for c in contracts]
        assert ids == [
            "futures_5_common_metals_001",
            "futures_5_common_metals_002",
            "futures_5_common_metals_003",
        ]
        assert len(set(ids)) == 3


# ---------------------------------------------------------------------------
# FuturesState.accept
# ---------------------------------------------------------------------------


class TestFuturesStateAccept:
    def test_accept_debits_credits_and_registers_contract(self) -> None:
        state = FuturesState()
        player = _FakePlayer(credits=1000)
        contract = _make_contract(entry_cost=214)
        ok, msg = state.accept(contract, player)
        assert ok is True, msg
        assert player.credits == 786
        assert state.active_contracts == [contract]

    def test_accept_with_insufficient_credits_leaves_state_unchanged(self) -> None:
        state = FuturesState()
        player = _FakePlayer(credits=50)
        contract = _make_contract(entry_cost=214)
        ok, reason = state.accept(contract, player)
        assert ok is False
        assert "Insufficient" in reason
        assert player.credits == 50
        assert state.active_contracts == []

    def test_accept_sets_first_contract_accepted_flag_once(self) -> None:
        state = FuturesState()
        player = _FakePlayer(credits=10_000)
        state.accept(_make_contract(contract_id="c1"), player)
        assert player.dialogue_flags.get(futures_first_contract_accepted()) is True

        # Second accept must not clobber the flag (which is what
        # idempotent-set-once means here — the value remains True).
        player.dialogue_flags[futures_first_contract_accepted()] = True
        state.accept(_make_contract(contract_id="c2", entry_cost=100), player)
        # No new setter fires; asserted by verifying that the flag stays
        # True whether or not the second call touches it.
        assert player.dialogue_flags[futures_first_contract_accepted()] is True

    def test_accept_fires_position_open_journal_entry(self) -> None:
        state = FuturesState()
        player = _FakePlayer(credits=10_000)
        journal = _FakeJournal()
        contract = _make_contract()

        state.accept(contract, player, journal=journal)
        assert len(journal.entries) == 1
        entry = journal.entries[0]
        assert entry["entry_id"].startswith("futures_position_open_")
        assert "Position Open" in entry["text"]
        assert "LONG" in entry["text"]


# ---------------------------------------------------------------------------
# FuturesState.advance_day — settlement math
# ---------------------------------------------------------------------------


class TestFuturesStateAdvanceDay:
    def _seeded_state(self, contract: FuturesContract) -> FuturesState:
        state = FuturesState()
        state.active_contracts.append(contract)
        return state

    def test_long_profit_settles_correctly(self) -> None:
        contract = _make_contract(direction="LONG", strike_price=67, quantity=80)
        state = self._seeded_state(contract)
        player = _FakePlayer(credits=1000)
        commodity = _make_commodity("common_metals", base_price=60)
        market = _StubMarket({"common_metals": 74}, commodities=[commodity])

        notifications = state.advance_day(current_day=8, nexus_market=market, player=player)
        assert len(notifications) == 1
        # Payoff = (74 - 67) * 80 = 560
        settled = state.settled_contracts[0]
        assert settled.payoff == 560
        assert settled.settlement_price == 74
        assert settled.settlement_day == 8
        assert player.credits == 1560
        assert state.total_credits_won == 560
        assert state.total_credits_lost == 0

    def test_long_loss_settles_correctly(self) -> None:
        contract = _make_contract(
            contract_id="c_medical",
            commodity_id="medical",
            direction="LONG",
            strike_price=479,
            quantity=20,
            entry_cost=345,
            duration_days=14,
            maturity_day=15,
        )
        state = self._seeded_state(contract)
        player = _FakePlayer(credits=1000)
        commodity = _make_commodity("medical", base_price=350)
        market = _StubMarket({"medical": 461}, commodities=[commodity])

        state.advance_day(current_day=15, nexus_market=market, player=player)
        settled = state.settled_contracts[0]
        # Payoff = (461 - 479) * 20 = -360
        assert settled.payoff == -360
        # credits decrement by 360 (obligation semantics allow < starting)
        assert player.credits == 640
        assert state.total_credits_lost == 360
        assert state.total_credits_won == 0

    def test_short_profit_settles_correctly(self) -> None:
        contract = _make_contract(
            contract_id="c_mfg",
            commodity_id="manufactured_goods",
            direction="SHORT",
            strike_price=167,
            quantity=50,
            entry_cost=267,
            duration_days=21,
            maturity_day=22,
        )
        state = self._seeded_state(contract)
        player = _FakePlayer(credits=500)
        commodity = _make_commodity("manufactured_goods", base_price=120)
        market = _StubMarket({"manufactured_goods": 139}, commodities=[commodity])

        state.advance_day(current_day=22, nexus_market=market, player=player)
        settled = state.settled_contracts[0]
        # Payoff = (167 - 139) * 50 = 1400
        assert settled.payoff == 1400
        assert player.credits == 1900
        assert state.total_credits_won == 1400

    def test_short_loss_settles_correctly(self) -> None:
        contract = _make_contract(
            contract_id="c_short_loss",
            commodity_id="fuel",
            direction="SHORT",
            strike_price=100,
            quantity=30,
            entry_cost=40,
            duration_days=7,
            maturity_day=8,
        )
        state = self._seeded_state(contract)
        player = _FakePlayer(credits=1000)
        commodity = _make_commodity("fuel", base_price=90)
        market = _StubMarket({"fuel": 120}, commodities=[commodity])

        state.advance_day(current_day=8, nexus_market=market, player=player)
        settled = state.settled_contracts[0]
        # Payoff = (100 - 120) * 30 = -600
        assert settled.payoff == -600
        assert player.credits == 400
        assert state.total_credits_lost == 600

    def test_unmatured_contract_stays_active(self) -> None:
        contract = _make_contract(maturity_day=10)
        state = self._seeded_state(contract)
        player = _FakePlayer(credits=1000)
        market = _StubMarket({"common_metals": 100})

        state.advance_day(current_day=5, nexus_market=market, player=player)
        assert state.active_contracts == [contract]
        assert state.settled_contracts == []
        assert player.credits == 1000

    def test_zero_price_defers_settlement(self) -> None:
        contract = _make_contract(maturity_day=8)
        state = self._seeded_state(contract)
        player = _FakePlayer(credits=1000)
        commodity = _make_commodity("common_metals", base_price=60)
        embargo_market = _StubMarket({"common_metals": 0}, commodities=[commodity])

        notifications = state.advance_day(current_day=8, nexus_market=embargo_market, player=player)
        assert state.active_contracts == [contract]
        assert state.settled_contracts == []
        assert len(notifications) == 1
        assert "deferred" in notifications[0].lower()

        # Retry the next day with a live price: settlement completes.
        live_market = _StubMarket({"common_metals": 100}, commodities=[commodity])
        state.advance_day(current_day=9, nexus_market=live_market, player=player)
        assert state.settled_contracts and state.settled_contracts[0].settled is True

    def test_first_win_and_first_loss_flags_fire_once_each(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("common_metals", base_price=60)
        market_win = _StubMarket({"common_metals": 100}, commodities=[commodity])
        market_loss = _StubMarket({"common_metals": 50}, commodities=[commodity])
        player = _FakePlayer(credits=1000)

        # Win first.
        state.active_contracts.append(
            _make_contract(contract_id="a", strike_price=60, quantity=20, maturity_day=1)
        )
        state.advance_day(current_day=1, nexus_market=market_win, player=player)
        assert player.dialogue_flags.get(futures_first_win()) is True
        assert player.dialogue_flags.get(futures_first_loss()) is not True

        # Loss second.
        state.active_contracts.append(
            _make_contract(contract_id="b", strike_price=60, quantity=20, maturity_day=2)
        )
        state.advance_day(current_day=2, nexus_market=market_loss, player=player)
        assert player.dialogue_flags.get(futures_first_loss()) is True

    def test_journal_entries_fire_at_settle(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("common_metals", base_price=60)
        market = _StubMarket({"common_metals": 74}, commodities=[commodity])
        journal = _FakeJournal()
        player = _FakePlayer(credits=1000)

        state.active_contracts.append(
            _make_contract(contract_id="p1", strike_price=67, quantity=80, maturity_day=8)
        )
        state.advance_day(current_day=8, nexus_market=market, player=player, journal=journal)
        assert any(e["entry_id"].startswith("futures_closed_profit_") for e in journal.entries)
        # No loss entry on a profitable settlement.
        assert not any(e["entry_id"].startswith("futures_closed_loss_") for e in journal.entries)

    def test_headliner_news_gated_by_notional_threshold(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("medical", base_price=350)
        market = _StubMarket({"medical": 500}, commodities=[commodity])
        player = _FakePlayer(credits=5000)
        news_ticker = _FakeNewsTicker()

        # Notional = 300 * 40 = 12,000 → headliner.
        state.active_contracts.append(
            _make_contract(
                contract_id="head",
                commodity_id="medical",
                direction="LONG",
                strike_price=300,
                quantity=40,
                maturity_day=1,
            )
        )
        state.advance_day(
            current_day=1,
            nexus_market=market,
            player=player,
            news_ticker=news_ticker,
        )
        assert len(news_ticker.pending_events) == 1
        event = news_ticker.pending_events[0]
        assert event["trigger"] == "futures_headliner_settled"
        assert event["commodity_id"] == "medical"
        assert event["direction"] == "LONG"

    def test_non_headliner_settlement_skips_news(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("fuel", base_price=10)
        market = _StubMarket({"fuel": 15}, commodities=[commodity])
        player = _FakePlayer(credits=1000)
        news_ticker = _FakeNewsTicker()

        # Notional = 10 * 20 = 200 → non-headliner.
        state.active_contracts.append(
            _make_contract(
                contract_id="tiny",
                commodity_id="fuel",
                strike_price=10,
                quantity=20,
                maturity_day=1,
            )
        )
        assert HEADLINER_NOTIONAL_THRESHOLD > 200
        state.advance_day(
            current_day=1,
            nexus_market=market,
            player=player,
            news_ticker=news_ticker,
        )
        assert news_ticker.pending_events == []

    def test_commerce_guild_rep_delta_fires_above_profit_threshold(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("medical", base_price=350)
        # Payoff = (500 - 300) * 40 = 8000 → above 5000 threshold.
        market = _StubMarket({"medical": 500}, commodities=[commodity])
        player = _FakePlayer(credits=5000)
        rep = _FakeReputationManager()

        state.active_contracts.append(
            _make_contract(
                contract_id="win",
                commodity_id="medical",
                strike_price=300,
                quantity=40,
                maturity_day=1,
            )
        )
        state.advance_day(current_day=1, nexus_market=market, player=player, reputation_manager=rep)
        assert rep.calls == [(COMMERCE_GUILD_FACTION_ID, 2)]

    def test_commerce_guild_rep_delta_does_not_fire_under_threshold(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("common_metals", base_price=60)
        # Payoff = (74 - 67) * 80 = 560 → below 5000 threshold.
        market = _StubMarket({"common_metals": 74}, commodities=[commodity])
        player = _FakePlayer(credits=1000)
        rep = _FakeReputationManager()

        state.active_contracts.append(_make_contract(strike_price=67, quantity=80, maturity_day=8))
        state.advance_day(current_day=8, nexus_market=market, player=player, reputation_manager=rep)
        assert rep.calls == []
        assert COMMERCE_GUILD_PROFIT_THRESHOLD > 560

    def test_advance_day_with_no_active_contracts_returns_empty_list(self) -> None:
        state = FuturesState()
        market = _StubMarket({"common_metals": 60})
        player = _FakePlayer(credits=1000)
        assert state.advance_day(current_day=1, nexus_market=market, player=player) == []

    def test_settlement_side_effects_skipped_when_no_reputation_manager(self) -> None:
        state = FuturesState()
        commodity = _make_commodity("medical", base_price=350)
        market = _StubMarket({"medical": 500}, commodities=[commodity])
        player = _FakePlayer(credits=5000)

        state.active_contracts.append(
            _make_contract(
                commodity_id="medical",
                strike_price=300,
                quantity=40,
                maturity_day=1,
            )
        )
        # No reputation_manager provided — should not raise.
        state.advance_day(current_day=1, nexus_market=market, player=player)
        assert len(state.settled_contracts) == 1


# ---------------------------------------------------------------------------
# Constants presence + module contract
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_trend_premium_locked_values(self) -> None:
        assert TREND_PREMIUM == {"rising": 0.04, "stable": 0.01, "falling": 0.00}

    def test_hop_penalty_locked(self) -> None:
        assert HOP_PENALTY == 0.01

    def test_duration_spread_locked(self) -> None:
        assert DURATION_SPREAD == {7: 0.02, 14: 0.05, 21: 0.09}

    def test_base_broker_spread_locked(self) -> None:
        assert BASE_BROKER_SPREAD == 0.04

    def test_min_quantity_locked(self) -> None:
        assert MIN_QUANTITY == 20

    def test_duration_whitelist_locked(self) -> None:
        assert VALID_DURATIONS == frozenset({7, 14, 21})

    def test_speculator_cap_locked(self) -> None:
        assert MAX_SPECULATOR_REDUCTION == 0.25

    def test_headliner_threshold_locked(self) -> None:
        assert HEADLINER_NOTIONAL_THRESHOLD == 10_000


# ---------------------------------------------------------------------------
# Hop-distance calibration against the real galaxy
# ---------------------------------------------------------------------------


class TestHopDistanceAgainstShippedGalaxy:
    """Documentation test: current galaxy places all three Section 3.4
    commodities' nearest producers between ~80-110 units from Nexus Prime.
    The bucket table therefore maps them all to hop 3. The Section 3.4
    example tests use synthetic systems, so this mapping is informational
    rather than load-bearing — but we lock it here so a future coordinate
    move is a visible test change instead of a silent formula drift.
    """

    def test_shipped_galaxy_puts_commodities_in_hop_3(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        engine = PricingEngine()
        all_systems = dl.get_all_systems()
        nexus = dl.get_system("nexus_prime")
        assert nexus is not None

        for commodity_id in ("common_metals", "medical", "manufactured_goods"):
            commodity = dl.get_commodity(commodity_id)
            assert commodity is not None
            hops = engine.hop_distance(commodity, all_systems, nexus)
            assert hops == 3, (
                f"{commodity_id} bucketed to {hops}; regenerate the "
                "calibration if the galaxy JSON was moved."
            )
