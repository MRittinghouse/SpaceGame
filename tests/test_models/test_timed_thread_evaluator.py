"""TW-2: evaluator tests — QA-F-1 revised model.

Touches are recorded via Player.record_interaction() at action points,
NOT sniffed from dialogue_flags. Inactive threads (never touched)
never drift — drift only evaluates from the first touch day forward.
"""

from __future__ import annotations

from spacegame.models.timed_thread import (
    DriftState,
    TimedThread,
)
from spacegame.models.timed_thread_evaluator import evaluate_threads


def _make_player(game_day: int = 0):
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="x", cargo_capacity=10, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=2, special_abilities=[],
        availability="all",
    )
    player = Player(
        name="T", credits=500, current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )
    player.game_day = game_day
    return player


def _marcus_thread() -> TimedThread:
    return TimedThread(
        id="marcus_lead_cold",
        touch_triggers=["talked_to_marcus_jin"],
        drift_states=[
            DriftState(
                id="cold",
                threshold_days=30,
                journal_entry_on_enter="Marcus's lead went cold.",
                flag_to_set_on_enter="marcus_cold",
            ),
            DriftState(
                id="gone",
                threshold_days=60,
                journal_entry_on_enter="Marcus has stopped responding.",
                flag_to_set_on_enter="marcus_gone",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Inactive threads (DOA bug fix)
# ---------------------------------------------------------------------------


class TestInactiveThreadsStaySilent:
    """Threads that have never been touched via record_interaction should
    NEVER drift, regardless of how many game days pass. This is the
    QA-F-1 fix — prior to it, every thread drifted on day 30 of every
    playthrough."""

    def test_untouched_thread_never_drifts_even_after_100_days(self) -> None:
        player = _make_player(game_day=100)
        threads = {"marcus_lead_cold": _marcus_thread()}
        events = evaluate_threads(player, threads)
        assert events == []

    def test_untouched_thread_stays_silent_on_repeat_ticks(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        for day in (10, 30, 60, 100, 200):
            player.game_day = day
            assert evaluate_threads(player, threads) == []


# ---------------------------------------------------------------------------
# Touch via record_interaction
# ---------------------------------------------------------------------------


class TestTouchViaInteraction:
    def test_first_interaction_sets_last_touched_day(self) -> None:
        player = _make_player(game_day=10)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        events = evaluate_threads(player, threads)
        state = player.timed_thread_state["marcus_lead_cold"]
        assert state.last_touched_day == 10
        assert events == []  # No drift yet

    def test_recurring_interactions_update_clock(self) -> None:
        """Elena-unspoken semantics: player talks to Elena on day 5 and
        day 40. Drift fires 45 days after day 40, not day 5."""
        thread = TimedThread(
            id="elena_unspoken",
            touch_triggers=["talked_to_elena_reeves"],
            drift_states=[
                DriftState(id="acknowledged", threshold_days=45),
            ],
        )
        player = _make_player(game_day=5)
        threads = {"elena_unspoken": thread}

        # Day 5: first interaction
        player.record_interaction("talked_to_elena_reeves")
        evaluate_threads(player, threads)

        # Day 40: another interaction — clock should reset
        player.game_day = 40
        player.record_interaction("talked_to_elena_reeves")
        evaluate_threads(player, threads)
        assert (
            player.timed_thread_state["elena_unspoken"].last_touched_day == 40
        )

        # Day 84 (44 after touch): still no drift
        player.game_day = 84
        assert evaluate_threads(player, threads) == []

        # Day 85 (45 after touch): drift fires
        player.game_day = 85
        events = evaluate_threads(player, threads)
        assert len(events) == 1
        assert events[0].state_id == "acknowledged"


# ---------------------------------------------------------------------------
# Drift transitions (once thread is active)
# ---------------------------------------------------------------------------


class TestDriftTransitions:
    def test_drift_fires_when_threshold_crossed(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)

        player.game_day = 30
        events = evaluate_threads(player, threads)
        assert len(events) == 1
        assert events[0].state_id == "cold"
        assert events[0].journal_entry == "Marcus's lead went cold."

    def test_drift_does_not_fire_before_threshold(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)
        player.game_day = 29
        assert evaluate_threads(player, threads) == []

    def test_multiple_states_fire_when_very_late(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)
        player.game_day = 100
        events = evaluate_threads(player, threads)
        state_ids = {e.state_id for e in events}
        assert state_ids == {"cold", "gone"}

    def test_drift_sets_flag_on_player(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)
        player.game_day = 30
        evaluate_threads(player, threads)
        assert player.dialogue_flags.get("marcus_cold") is True


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_same_state_does_not_refire_on_repeat_evaluation(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)
        player.game_day = 30
        first = evaluate_threads(player, threads)
        second = evaluate_threads(player, threads)
        assert len(first) == 1
        assert second == []

    def test_later_drift_fires_after_earlier_already_entered(self) -> None:
        player = _make_player(game_day=0)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)
        player.game_day = 30
        evaluate_threads(player, threads)
        player.game_day = 60
        events = evaluate_threads(player, threads)
        assert len(events) == 1
        assert events[0].state_id == "gone"


# ---------------------------------------------------------------------------
# Multiple threads
# ---------------------------------------------------------------------------


class TestMultipleThreads:
    def test_evaluator_processes_all_active_threads(self) -> None:
        thread_a = TimedThread(
            id="a",
            touch_triggers=["key_a"],
            drift_states=[DriftState(id="a1", threshold_days=10,
                journal_entry_on_enter="A drift")],
        )
        thread_b = TimedThread(
            id="b",
            touch_triggers=["key_b"],
            drift_states=[DriftState(id="b1", threshold_days=20,
                journal_entry_on_enter="B drift")],
        )
        player = _make_player(game_day=0)
        player.record_interaction("key_a")
        player.record_interaction("key_b")
        player.game_day = 25
        events = evaluate_threads(player, {"a": thread_a, "b": thread_b})
        thread_ids = {e.thread_id for e in events}
        assert thread_ids == {"a", "b"}

    def test_inactive_thread_silent_while_other_drifts(self) -> None:
        thread_a = TimedThread(
            id="a",
            touch_triggers=["key_a"],
            drift_states=[DriftState(id="a1", threshold_days=10)],
        )
        thread_b = TimedThread(
            id="b",
            touch_triggers=["key_b"],  # never recorded
            drift_states=[DriftState(id="b1", threshold_days=10)],
        )
        player = _make_player(game_day=0)
        player.record_interaction("key_a")
        player.game_day = 30
        events = evaluate_threads(player, {"a": thread_a, "b": thread_b})
        thread_ids = {e.thread_id for e in events}
        assert thread_ids == {"a"}


# ---------------------------------------------------------------------------
# Touch prevents drift
# ---------------------------------------------------------------------------


class TestTouchPreventsDrift:
    def test_touch_before_threshold_prevents_drift(self) -> None:
        player = _make_player(game_day=10)
        threads = {"marcus_lead_cold": _marcus_thread()}
        player.record_interaction("talked_to_marcus_jin")
        evaluate_threads(player, threads)
        player.game_day = 35
        # 35 - 10 = 25 < 30 threshold
        assert evaluate_threads(player, threads) == []
