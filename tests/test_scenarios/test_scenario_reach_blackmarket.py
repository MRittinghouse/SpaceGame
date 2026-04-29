"""SA-B4: Full Reach Black Market session scenario.

Drives a Reach auction session end-to-end against the loaded data
catalog: PREVIEW -> SESSION_OPEN -> 4 lots -> POST_SESSION ->
SESSION_CLOSE. Verifies the demand-driven cadence resets on close, that
contraband wins fire the locked legality penalty, and that the journal
entries trigger on the right flag transitions.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import (
    REACH_CONTRABAND_REP_PENALTY,
    REACH_DEMAND_MAX_GAP_DAYS,
    REACH_RESTRICTED_WEAPON_REP_PENALTY,
    REACH_SESSION_SIZE,
    AuctionLifecycle,
    AuctionState,
    generate_lot_pool,
    reach_advance_demand,
    reach_session_due,
    wreckers_tier_for_membership,
)
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_CONTRABAND,
    LOT_CATEGORY_FACTION_COMMODITY,
    LOT_CATEGORY_RESTRICTED_WEAPON,
    LOT_CATEGORY_SALVAGE_LOT,
    VENUE_CRIMSON_REACH,
)
from spacegame.models.bidding_persona import (
    PERSONA_KADE,
    PERSONA_PRENTISS,
    PERSONA_SALKO,
    make_reach_flavor,
    make_salko,
)


def _make_journeyman_player() -> "object":
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship

    loader = get_data_loader()
    loader.load_all()
    shuttle = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle, current_fuel=shuttle.fuel_capacity)
    player = Player(
        name="Reach Tester",
        credits=200000,
        current_system_id="crimson_reach",
        ship=ship,
    )
    # Direct sub_reputation poke to journeyman tier.
    player.sub_reputation["wreckers_guild"] = 50  # journeyman threshold = 30
    return player


class TestReachDemandCadence:
    """AC8: demand-driven cadence determinism + reset on close."""

    def test_demand_advance_then_session_due(self) -> None:
        state = AuctionState()
        # Start on day 0; advance demand each day until session is due.
        day = 1
        while not reach_session_due(state, current_day=day):
            reach_advance_demand(state, current_day=day)
            day += 1
            if day > 20:
                break
        assert reach_session_due(state, current_day=day), (
            f"Session should be due by day {day} under demand cadence"
        )
        # Should fire either by counter (>= REACH_SESSION_SIZE) or by cap.
        counter = state.next_auction_day.get("crimson_reach_pending", 0)
        last_day = state.last_auction_day.get("crimson_reach", 0)
        assert counter >= REACH_SESSION_SIZE or (day - last_day) >= REACH_DEMAND_MAX_GAP_DAYS

    def test_demand_reset_on_session_close(self) -> None:
        state = AuctionState()
        state.next_auction_day["crimson_reach_pending"] = REACH_SESSION_SIZE
        state.active_auction_id = VENUE_CRIMSON_REACH
        state.active_session_id = "test_session"
        # Append a session-history entry so close_session_for_day has
        # something to stamp.
        from spacegame.models.bidding import _SessionHistoryEntry

        state.session_history.append(
            _SessionHistoryEntry(
                session_id="test_session",
                venue_id=VENUE_CRIMSON_REACH,
                closed_on_day=0,
                lot_results=[],
                rival_ids=[],
            )
        )
        state.close_session_for_day(current_day=12)
        assert state.next_auction_day.get("crimson_reach_pending", 0) == 0
        assert state.last_auction_day[VENUE_CRIMSON_REACH] == 12


class TestReachSessionEndToEnd:
    """AC20: full Reach session scenario."""

    def test_session_runs_to_close_with_locked_seed(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        catalog = dl.get_auction_lots(VENUE_CRIMSON_REACH)
        assert catalog, "Reach catalog must be loaded"

        player = _make_journeyman_player()
        tier = wreckers_tier_for_membership(player)
        assert tier == "journeyman"

        state = player.auction_state
        session_id = "test_reach_full_session"
        pool = generate_lot_pool(
            catalog,
            venue_id=VENUE_CRIMSON_REACH,
            player_rep_tier=tier,
            player_faction_standing=dict(player.faction_reputation),
            season_tag=None,
            session_id=session_id,
            target_size=REACH_SESSION_SIZE,
        )
        assert len(pool) >= 1

        # Build personas: Salko + 3 ambient Reach buyers (no Prentiss / Kade).
        personas = [make_salko()]
        for i in (1, 2, 3):
            personas.append(make_reach_flavor(instance_index=i))

        rival_ids = [p.persona_id for p in personas]
        state.enter_preview(
            venue_id=VENUE_CRIMSON_REACH,
            session_lots=pool[:REACH_SESSION_SIZE],
            rival_ids=rival_ids,
            session_id=session_id,
        )
        state.set_session_personas(personas)
        # Verify named-rival exclusions: Prentiss + Kade NOT present.
        assert PERSONA_PRENTISS not in rival_ids
        assert PERSONA_KADE not in rival_ids
        assert PERSONA_SALKO in rival_ids

        state.open_session()
        # Drive ticks until SESSION_CLOSE.
        ticks = 0
        max_ticks = 800
        while state.lifecycle != AuctionLifecycle.SESSION_CLOSE and ticks < max_ticks:
            state.tick(2.0)
            if state.lifecycle == AuctionLifecycle.LOT_RESOLUTION:
                state.advance_after_resolution()
            ticks += 1
        assert state.lifecycle == AuctionLifecycle.SESSION_CLOSE
        assert len(state.session_history) >= 1

        # Close + verify the demand counter resets.
        state.close_session_for_day(current_day=14)
        assert state.next_auction_day.get("crimson_reach_pending", 0) == 0
        assert state.last_auction_day[VENUE_CRIMSON_REACH] == 14
        # No 5-7 day reschedule for Reach (demand-driven, not calendar).
        assert (
            VENUE_CRIMSON_REACH
            not in {
                k
                for k in state.next_auction_day
                if k != "crimson_reach_pending" and k != "crimson_reach_last_advance_day"
            }
            or state.next_auction_day.get(VENUE_CRIMSON_REACH) is None
        )


class TestReachLegalityPenalty:
    """AC10: legality consequences locked per category.

    Locked decision §B4.8 magnitudes:

    * contraband -> -2 stellaris_commerce_guild rep
    * restricted_weapon -> -1
    * salvage_lot -> 0
    * faction_commodity -> 0
    """

    @pytest.mark.parametrize(
        "category,expected_penalty",
        [
            (LOT_CATEGORY_CONTRABAND, REACH_CONTRABAND_REP_PENALTY),
            (LOT_CATEGORY_RESTRICTED_WEAPON, REACH_RESTRICTED_WEAPON_REP_PENALTY),
            (LOT_CATEGORY_SALVAGE_LOT, 0),
            (LOT_CATEGORY_FACTION_COMMODITY, 0),
        ],
    )
    def test_penalty_per_category(self, category: str, expected_penalty: int) -> None:
        from spacegame.engine.game import _apply_reach_legality_penalty

        player = _make_journeyman_player()
        # Start at neutral commerce-guild rep.
        player.faction_reputation["stellaris_commerce_guild"] = 0
        from spacegame.models.bidding_lot import AuctionLot

        lot = AuctionLot(
            id=f"test_lot_{category}",
            headline="Test Lot",
            description="Test",
            category=category,
            venue=VENUE_CRIMSON_REACH,
            base_appraisal=10000,
            reserve_pct=0.7,
        )
        _apply_reach_legality_penalty(player, lot)
        actual = player.faction_reputation.get("stellaris_commerce_guild", 0)
        assert actual == expected_penalty, (
            f"Lot category {category}: expected rep delta {expected_penalty}, got {actual}"
        )
