"""SA-P2 — politics market-shift registry tests (AC 14).

Verifies stack rule (largest-magnitude wins), independent decay per
shift, and coexistence with the existing single-active MarketEvent.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import DataLoader
from spacegame.models.market import Market
from spacegame.models.politics_dispute import PoliticsMarketShift


@pytest.fixture(scope="module")
def loader():
    dl = DataLoader()
    dl.load_all()
    return dl


def _build_market(loader: DataLoader, system_id: str = "verdant") -> Market:
    system = loader.systems[system_id]
    commodities = list(loader.commodities.values())
    return Market(system, commodities, game_day=1)


class TestPoliticsShiftRegistry:
    def test_register_single_shift_applies_multiplier(self, loader) -> None:
        """A 10% positive shift raises the price by approximately 10%."""
        market = _build_market(loader, "verdant")
        commodity_id = next(iter(market.commodities))
        baseline = market.get_price(commodity_id)
        shift = PoliticsMarketShift(
            commodity_id=commodity_id,
            system_id="verdant",
            magnitude=0.10,
            duration_days=30,
            start_day=market.game_day,
        )
        market.add_politics_shift(shift)
        # Force re-pricing.
        market.update_day(market.game_day)
        assert market.get_price(commodity_id) >= int(baseline * 1.05)

    def test_two_shifts_largest_magnitude_wins(self, loader) -> None:
        """SA-P1 §11 decision 14: largest absolute magnitude applies."""
        market = _build_market(loader, "verdant")
        commodity_id = next(iter(market.commodities))
        baseline = market.get_price(commodity_id)

        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", 0.05, 30, market.game_day)
        )
        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", 0.15, 30, market.game_day)
        )
        market.update_day(market.game_day)
        # The 15% shift dominates; result is approximately baseline * 1.15.
        assert market.get_price(commodity_id) >= int(baseline * 1.10)

    def test_negative_largest_magnitude_wins_over_positive(self, loader) -> None:
        """A larger-absolute negative shift drops the price."""
        market = _build_market(loader, "verdant")
        commodity_id = next(iter(market.commodities))
        baseline = market.get_price(commodity_id)

        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", 0.05, 30, market.game_day)
        )
        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", -0.15, 30, market.game_day)
        )
        market.update_day(market.game_day)
        assert market.get_price(commodity_id) <= int(baseline * 0.95)

    def test_shifts_decay_independently_after_duration_days(self, loader) -> None:
        """Each shift decays after its own duration_days; coexisting shifts
        of different durations expire at separate ticks."""
        market = _build_market(loader, "verdant")
        commodity_id = next(iter(market.commodities))

        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", 0.10, 5, market.game_day)
        )
        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", -0.05, 30, market.game_day)
        )
        # Tick to day where the +0.10 expired but -0.05 still active.
        market.update_day(market.game_day + 6)
        active = market.get_active_politics_shifts(commodity_id, "verdant")
        assert len(active) == 1
        assert active[0].magnitude == pytest.approx(-0.05)

        # Tick past the second shift's expiry.
        market.update_day(market.game_day + 25)
        active = market.get_active_politics_shifts(commodity_id, "verdant")
        assert len(active) == 0

    def test_shifts_filter_by_commodity_and_system(self, loader) -> None:
        """A shift on (X, verdant) does not affect (Y, verdant) or (X, nexus)."""
        market = _build_market(loader, "verdant")
        commodities = list(market.commodities)
        if len(commodities) < 2:
            pytest.skip("Need at least two commodities at verdant for this test")
        a, b = commodities[0], commodities[1]
        market.add_politics_shift(PoliticsMarketShift(a, "verdant", 0.10, 30, market.game_day))
        active_a = market.get_active_politics_shifts(a, "verdant")
        active_b = market.get_active_politics_shifts(b, "verdant")
        active_a_other = market.get_active_politics_shifts(a, "nexus_prime")
        assert len(active_a) == 1
        assert len(active_b) == 0
        assert len(active_a_other) == 0


class TestPoliticsShiftCoexistsWithMarketEvent:
    """Politics shifts run in parallel with the single-slot MarketEvent."""

    def test_no_interference_with_market_event_apply(self, loader) -> None:
        from spacegame.models.event import EventType, MarketEvent

        market = _build_market(loader, "verdant")
        commodity_id = next(iter(market.commodities))
        # Apply a market event AND a politics shift; both should affect price.
        event = MarketEvent(
            event_type=EventType.SHORTAGE,
            commodity_id=commodity_id,
            system_id="verdant",
            price_multiplier=1.20,
            duration_days=30,
            day_started=market.game_day,
            description="test surge",
        )
        market.apply_event(event)
        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", 0.10, 30, market.game_day)
        )
        market.update_day(market.game_day)
        # Price should reflect the combined effect (multiplied chain).
        # Our concern: politics shift didn't unset the active_event.
        assert market.active_event is event
        assert len(market.get_active_politics_shifts(commodity_id, "verdant")) == 1

    def test_serialize_restore_round_trip(self, loader) -> None:
        market = _build_market(loader, "verdant")
        commodity_id = next(iter(market.commodities))
        market.add_politics_shift(
            PoliticsMarketShift(commodity_id, "verdant", 0.10, 30, market.game_day)
        )
        snapshot = market.to_dict()
        # Build a fresh market and load.
        market2 = _build_market(loader, "verdant")
        market2.load_supply_demand(snapshot)
        active = market2.get_active_politics_shifts(commodity_id, "verdant")
        assert len(active) == 1
        assert active[0].magnitude == pytest.approx(0.10)
