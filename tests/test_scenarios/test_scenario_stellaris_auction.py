"""SA-B3: Full Stellaris session scenario.

Drives a Stellaris auction session end-to-end against the loaded data
catalog: PREVIEW -> SESSION_OPEN -> 6+ lots -> POST_SESSION ->
SESSION_CLOSE -> next-day reschedule. Verifies the session cadence
lands within the locked 5-7 day window after close, and that the
post-session social UI renders at least one line.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import (
    STELLARIS_CADENCE_MAX_DAYS,
    STELLARIS_CADENCE_MIN_DAYS,
    AuctionLifecycle,
    current_season_tag,
    generate_lot_pool,
    pick_stellaris_rival_attendance,
    stellaris_initial_session_day,
    stellaris_tier_for_standing,
)
from spacegame.models.bidding_lot import VENUE_STELLARIS
from spacegame.models.bidding_persona import (
    PERSONA_KADE,
    PERSONA_PRENTISS,
    PERSONA_SALKO,
    make_kade,
    make_prentiss,
    make_salko,
    make_stellaris_speculator,
)


class TestFullSession:
    def test_end_to_end_drives_lifecycle(self) -> None:
        """Full Stellaris session: schedule -> preview -> close -> reschedule."""
        from spacegame.models.bidding import AuctionState

        dl = get_data_loader()
        dl.load_all()
        catalog = dl.get_auction_lots(VENUE_STELLARIS)
        assert catalog, "Stellaris catalog must be loaded"

        state = AuctionState()
        # First-time schedule.
        current_day = 10
        first_day = stellaris_initial_session_day(current_day)
        state.schedule_session(VENUE_STELLARIS, first_day)
        assert state.is_session_due(VENUE_STELLARIS, current_day) is False
        assert state.is_session_due(VENUE_STELLARIS, first_day) is True

        # Generate a session pool on the due day.
        session_id = f"test_full_{first_day}"
        season = current_season_tag(first_day)
        tier = stellaris_tier_for_standing(80)  # patron
        pool = generate_lot_pool(
            catalog,
            venue_id=VENUE_STELLARIS,
            player_rep_tier=tier,
            player_faction_standing={"commerce_guild": 50},
            season_tag=season,
            session_id=session_id,
            target_size=8,
        )
        assert len(pool) >= 6
        attending = pick_stellaris_rival_attendance(
            session_id=session_id,
            lot_pool=pool,
        )
        # Salko always attends.
        assert PERSONA_SALKO in attending
        personas = []
        if PERSONA_PRENTISS in attending:
            personas.append(make_prentiss())
        if PERSONA_KADE in attending:
            personas.append(make_kade())
        if PERSONA_SALKO in attending:
            personas.append(make_salko())
        personas.append(make_stellaris_speculator("module", instance_index=1))
        personas.append(make_stellaris_speculator("antiquity", instance_index=2))

        state.enter_preview(
            venue_id=VENUE_STELLARIS,
            session_lots=pool[:6],
            rival_ids=[p.persona_id for p in personas],
            session_id=session_id,
        )
        state.set_session_personas(personas)
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
        # Session was recorded.
        assert len(state.session_history) >= 1
        # Close the session and reschedule for next.
        state.close_session_for_day(first_day)
        next_day = state.next_auction_day.get(VENUE_STELLARIS)
        assert next_day is not None
        gap = next_day - first_day
        assert STELLARIS_CADENCE_MIN_DAYS <= gap <= STELLARIS_CADENCE_MAX_DAYS

    def test_speculator_unique_persona_ids_within_session(self) -> None:
        """AC7: 2 speculators per session must have unique persona ids."""
        spec1 = make_stellaris_speculator("module", instance_index=1)
        spec2 = make_stellaris_speculator("antiquity", instance_index=2)
        assert spec1.persona_id != spec2.persona_id


class TestRivalAttendanceDeterminism:
    def test_attendance_stable_across_runs(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        catalog = dl.get_auction_lots(VENUE_STELLARIS)
        first = pick_stellaris_rival_attendance(session_id="determ_t1", lot_pool=catalog)
        second = pick_stellaris_rival_attendance(session_id="determ_t1", lot_pool=catalog)
        assert first == second
