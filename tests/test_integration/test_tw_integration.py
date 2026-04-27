"""TW-5: end-to-end integration tests + content integrity.

QA-F-1 revised: verifies the interaction-day touch model, catches the
"inactive thread never drifts" DOA-fix invariant, and exercises full
mission-accept-triggered-interaction flow end-to-end.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.timed_thread_evaluator import evaluate_threads


def _make_player(game_day: int = 0):
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="x",
        cargo_capacity=10,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=2,
        special_abilities=[],
        availability="all",
    )
    player = Player(
        name="T",
        credits=500,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )
    player.game_day = game_day
    return player


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


# ---------------------------------------------------------------------------
# Authored threads: content integrity
# ---------------------------------------------------------------------------


class TestAuthoredThreadContent:
    def test_minimum_thread_count(self, dl) -> None:
        # QA-F-1 dropped summit_restless; now 4 threads
        assert len(dl.timed_threads) >= 4, (
            f"TW ships at least 4 threads; got {len(dl.timed_threads)}"
        )

    def test_all_threads_have_at_least_one_drift_state(self, dl) -> None:
        for tid, t in dl.timed_threads.items():
            assert t.drift_states, f"Thread '{tid}' has no drift states"

    def test_all_threads_have_touch_triggers(self, dl) -> None:
        """Post QA-F-1 every thread must watch at least one interaction
        key — a thread with no triggers stays inactive forever and the
        content is dead."""
        for tid, t in dl.timed_threads.items():
            assert t.touch_triggers, f"Thread '{tid}' has no touch_triggers — would never drift"

    def test_drift_text_follows_writing_bible(self, dl) -> None:
        EM_DASHES = ("\u2014", "\u2013", " -- ")
        BANNED = ("couldn't help but", "a testament to")
        offenders = []
        for tid, t in dl.timed_threads.items():
            for state in t.drift_states:
                for field_name in ("journal_entry_on_enter", "narration"):
                    text = getattr(state, field_name, "")
                    for dash in EM_DASHES:
                        if dash in text:
                            offenders.append(f"{tid}/{state.id}.{field_name}: em-dash")
                            break
                    lowered = text.lower()
                    for phrase in BANNED:
                        if phrase in lowered:
                            offenders.append(f"{tid}/{state.id}.{field_name}: {phrase!r}")
        assert not offenders, "\n  " + "\n  ".join(offenders)

    def test_thresholds_ascending_per_thread(self, dl) -> None:
        for tid, t in dl.timed_threads.items():
            thresholds = [s.threshold_days for s in t.drift_states]
            assert thresholds == sorted(thresholds), (
                f"Thread '{tid}' has non-ascending thresholds: {thresholds}"
            )

    def test_thresholds_are_positive(self, dl) -> None:
        for tid, t in dl.timed_threads.items():
            for state in t.drift_states:
                assert state.threshold_days > 0, (
                    f"Thread '{tid}/{state.id}' threshold must be positive"
                )


# ---------------------------------------------------------------------------
# QA-F-1 invariant: inactive threads never drift
# ---------------------------------------------------------------------------


class TestInactiveThreadsNeverDrift:
    """The DOA bug was: threads with untouched=0 drifted on day 30 of every
    playthrough. Post-fix, threads stay inactive until record_interaction
    fires."""

    def test_fresh_player_gets_no_drift_over_long_time(self, dl) -> None:
        """A brand-new player who engages zero content should see zero
        drift events even after 200 game days."""
        player = _make_player(game_day=0)
        # Simulate many day-advances without any interactions
        for day in range(1, 201):
            player.game_day = day
            events = evaluate_threads(player, dl.timed_threads)
            assert events == [], (
                f"Fresh player drifted on day {day}: {[e.thread_id for e in events]}"
            )


# ---------------------------------------------------------------------------
# Soft deadlines: content integrity (unchanged by QA-F-1)
# ---------------------------------------------------------------------------


class TestAuthoredSoftDeadlines:
    REQUIRED_MISSIONS = {
        "bill_of_landing",
        "iron_delivery",
        "the_scholars_errand",
        "the_ledger",
    }

    def test_target_missions_have_soft_deadlines(self, dl) -> None:
        missions_by_id = {m.id: m for m in dl.missions}
        missing = []
        for mid in self.REQUIRED_MISSIONS:
            m = missions_by_id.get(mid)
            if m is None:
                missing.append(f"{mid} (mission not found)")
                continue
            if m.soft_deadline is None:
                missing.append(f"{mid} (no soft_deadline)")
        assert not missing, "Missing soft deadlines:\n  " + "\n  ".join(missing)

    def test_soft_deadline_tiers_are_sensible(self, dl) -> None:
        for m in dl.missions:
            if m.soft_deadline is None:
                continue
            sd = m.soft_deadline
            assert sd.full_reward_day_count > 0
            assert sd.partial_reward_day_count > sd.full_reward_day_count
            assert sd.late_multiplier > 0

    def test_mission_multiplier_helper_works_end_to_end(self, dl) -> None:
        missions_by_id = {m.id: m for m in dl.missions}
        iron = missions_by_id["iron_delivery"]
        assert iron.get_reward_multiplier(0) == 1.0
        assert iron.get_reward_multiplier(14) == 1.0
        assert iron.get_reward_multiplier(16) == 0.75
        assert iron.get_reward_multiplier(50) == 0.5


# ---------------------------------------------------------------------------
# End-to-end: interaction -> thread activation -> drift
# ---------------------------------------------------------------------------


class TestEndToEndAuthoredThreads:
    def test_marcus_talk_activates_thread_then_drifts_at_30_days(self, dl) -> None:
        player = _make_player(game_day=5)
        # Simulate first Marcus conversation
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, dl.timed_threads)
        state = player.timed_thread_state["marcus_lead_cold"]
        assert state.last_touched_day == 5

        # 30 days pass, no further touches
        player.game_day = 35
        events = evaluate_threads(player, dl.timed_threads)
        cold = [e for e in events if e.state_id == "cold"]
        assert len(cold) == 1
        assert player.dialogue_flags.get("marcus_lead_cold") is True

    def test_repeated_marcus_talks_reset_clock(self, dl) -> None:
        """Recurring touch semantics: player talks to Marcus at day 5 and
        day 20. Drift fires 30 days after the LATEST talk, not the first."""
        player = _make_player(game_day=5)
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, dl.timed_threads)

        player.game_day = 20
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, dl.timed_threads)
        assert player.timed_thread_state["marcus_lead_cold"].last_touched_day == 20

        # Day 49: 29 days past the last touch — no drift yet
        player.game_day = 49
        assert evaluate_threads(player, dl.timed_threads) == []

        # Day 50: 30 days past, drift fires
        player.game_day = 50
        events = evaluate_threads(player, dl.timed_threads)
        assert any(e.state_id == "cold" for e in events)

    def test_any_mission_accepted_touches_tomas_thread(self, dl) -> None:
        """tomas_restless watches 'any_mission_accepted'. Verify the
        interaction resets its drift clock."""
        player = _make_player(game_day=10)
        player.record_interaction("any_mission_accepted")
        evaluate_threads(player, dl.timed_threads)
        state = player.timed_thread_state.get("tomas_restless")
        assert state is not None
        assert state.last_touched_day == 10


# ---------------------------------------------------------------------------
# "Moderate" invariant: no content locks
# ---------------------------------------------------------------------------


class TestModerateInvariant:
    def test_no_drift_state_negates_rewards(self, dl) -> None:
        BLOCKING_PREFIXES = ("block_", "lock_", "disable_", "deny_")
        offenders = []
        for tid, t in dl.timed_threads.items():
            for state in t.drift_states:
                flag = state.flag_to_set_on_enter
                if not flag:
                    continue
                for prefix in BLOCKING_PREFIXES:
                    if flag.startswith(prefix):
                        offenders.append(
                            f"{tid}/{state.id}: flag '{flag}' looks like a content lock"
                        )
        assert not offenders, "Potentially-locking drift flags:\n  " + "\n  ".join(offenders)

    def test_every_soft_deadline_late_multiplier_nonzero(self, dl) -> None:
        for m in dl.missions:
            if m.soft_deadline is None:
                continue
            assert m.get_reward_multiplier(99999) > 0


# ---------------------------------------------------------------------------
# Save/load round-trip with RC + TW state coexisting
# ---------------------------------------------------------------------------


class TestTWSaveLoadWithOtherState:
    def test_timed_thread_state_coexists_with_captain_memory(self, dl, tmp_path) -> None:
        from spacegame.models.captain_memory import OUTCOME_VICTORY
        from spacegame.save_manager import SaveManager

        player = _make_player(game_day=5)
        # RC state
        player.record_captain_encounter("vela_wolfs_ear", OUTCOME_VICTORY)
        # TW state via the QA-F-1 interaction API
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, dl.timed_threads)
        player.game_day = 35
        evaluate_threads(player, dl.timed_threads)

        assert "marcus_lead_cold" in player.timed_thread_state
        assert player.captain_memory["vela_wolfs_ear"].status == "defeated"

        sm = SaveManager(save_directory=tmp_path)
        sm.save_game(
            slot=0,
            player=player,
            markets={},
            active_events={},
            playtime_seconds=0,
        )
        loaded = sm.load_game(slot=0)
        lp = loaded["player"]
        # Both systems' state preserved
        assert lp.captain_memory["vela_wolfs_ear"].status == "defeated"
        assert "marcus_lead_cold" in lp.timed_thread_state
        assert "cold" in lp.timed_thread_state["marcus_lead_cold"].entered_states
        # Interaction records preserved too
        assert lp.last_interaction_day["talked_to_marcus_jin"] == 5
