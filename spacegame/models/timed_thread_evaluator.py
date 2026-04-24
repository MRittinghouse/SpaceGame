"""TW-2: timed thread evaluator.

Evaluates all active threads against the player's current state. Emits
``DriftEvent`` for every newly-entered drift state so the caller
(game.py) can wire the effects into concrete systems (journal entries,
news ticker, dialogue flags).

The evaluator mutates ``player.timed_thread_state`` in place but is
pure relative to external systems — it returns events rather than
reaching into the journal or news directly. The caller wires them.

Called by game.py after game_day advances. Idempotent within a single
tick: each (thread_id, state_id) fires at most once per save.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from spacegame.models.timed_thread import (
    DriftEvent,
    TimedThread,
    initial_state_for_thread,
)

if TYPE_CHECKING:
    from spacegame.models.player import Player


def evaluate_threads(
    player: "Player",
    threads: dict[str, TimedThread],
) -> list[DriftEvent]:
    """Evaluate every thread against the player's state.

    Returns a list of DriftEvent — one per newly-entered drift state
    across all threads. Multiple drift states on one thread CAN fire
    in the same call if enough time has passed (e.g., 100 days of
    inactivity past thresholds at 30 / 60 / 90).

    Args:
        player: Player whose state is being evaluated. Mutated.
        threads: All loaded TimedThread definitions, keyed by id.

    Returns:
        List of DriftEvent for newly-entered states. Empty when
        nothing has drifted on this call.
    """
    events: list[DriftEvent] = []
    game_day = player.game_day

    for thread in threads.values():
        events.extend(_evaluate_one(player, thread, game_day))

    return events


def _evaluate_one(
    player: "Player",
    thread: TimedThread,
    game_day: int,
) -> list[DriftEvent]:
    """Evaluate one thread. Handles touch detection + drift transitions.

    Touch model (QA-F-1 fix): the thread consults
    ``player.last_interaction_day`` — a dict populated via
    ``Player.record_interaction()`` at action points — to find the
    most recent day any watched interaction key fired. If that day is
    newer than ``state.last_touched_day``, the clock resets. This works
    for both one-time events (dialogue accept) AND recurring events
    (repeated NPC talks) because each record records the CURRENT game
    day, not just whether the event happened.

    Inactive threads (``last_touched_day is None``) are skipped — drift
    only evaluates once an interaction has kicked the thread off. This
    prevents all threads from drifting on day 30 of any playthrough,
    which was the DOA bug prior to this fix.
    """
    state = player.timed_thread_state.get(thread.id)
    if state is None:
        state = initial_state_for_thread(thread)
        player.timed_thread_state[thread.id] = state

    # Phase 1: touch detection via the interaction map. Any watched key
    # with a more-recent record than our last_touched_day rewinds the
    # drift clock. Handles recurring touches (each new record is a
    # fresh touch) AND one-time events (single record, single touch).
    for key in thread.touch_triggers:
        last_day = player.last_interaction_day.get(key)
        if last_day is None:
            continue
        if state.last_touched_day is None or last_day > state.last_touched_day:
            state.last_touched_day = last_day

    # Phase 2: skip inactive threads (never touched). Without this, any
    # never-touched thread would drift immediately on day
    # threshold_days, regardless of whether the relevant arc was ever
    # engaged by the player.
    if state.last_touched_day is None:
        return []

    # Phase 3: drift transitions. Iterate in threshold-ascending order
    # (enforced by TimedThread.from_dict). Multiple states can fire in
    # one evaluation if enough time has passed.
    days_untouched = game_day - state.last_touched_day
    events: list[DriftEvent] = []

    for drift in thread.drift_states:
        if state.has_entered(drift.id):
            continue
        if days_untouched < drift.threshold_days:
            break

        state.mark_entered(drift.id)

        if drift.flag_to_set_on_enter:
            player.dialogue_flags[drift.flag_to_set_on_enter] = True

        events.append(
            DriftEvent(
                thread_id=thread.id,
                state_id=drift.id,
                journal_entry=drift.journal_entry_on_enter,
                flag_to_set=drift.flag_to_set_on_enter,
                narration=drift.narration,
                game_day=game_day,
            )
        )

    return events
