"""TW-1: time-sensitive narrative threads that drift when ignored.

Threads give the player a sense that time moves in the galaxy — if a
story thread goes untouched for long enough, its state changes. The
arc continues (drift, not fail), just with different content.

Design constraints (from roadmap §TW):
- **Drift, not fail.** State transitions change what's ahead; they
  never lock content.
- **Soft.** A drifted thread can still be engaged; it just reads
  differently.
- **Touch semantics.** v1 uses one-time touches: the first time a
  trigger flag flips from unset -> set, ``last_touched_day`` resets.
  This prevents the "flag stays True forever -> thread never drifts"
  degenerate case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DriftState:
    """One discrete state a thread can drift into.

    Attributes:
        id: State identifier (unique within a thread).
        threshold_days: Days of untouched-ness to reach this state.
            Evaluated as ``game_day - last_touched_day >= threshold_days``.
            Threads process drift states in order; each can fire at most
            once per thread lifetime.
        journal_entry_on_enter: Optional journal text to auto-add when
            entering this state. Empty string = no entry.
        flag_to_set_on_enter: Optional dialogue_flag to set True.
        narration: Optional short line (news ticker / environmental).
    """

    id: str
    threshold_days: int
    journal_entry_on_enter: str = ""
    flag_to_set_on_enter: str = ""
    narration: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DriftState":
        return cls(
            id=data["id"],
            threshold_days=int(data["threshold_days"]),
            journal_entry_on_enter=data.get("journal_entry_on_enter", ""),
            flag_to_set_on_enter=data.get("flag_to_set_on_enter", ""),
            narration=data.get("narration", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "threshold_days": self.threshold_days,
            "journal_entry_on_enter": self.journal_entry_on_enter,
            "flag_to_set_on_enter": self.flag_to_set_on_enter,
            "narration": self.narration,
        }


@dataclass
class TimedThread:
    """A narrative thread that drifts when unattended.

    Attributes:
        id: Thread identifier (unique across all threads).
        touch_triggers: Dialogue flag ids. When any of these flips from
            unset to set, the thread is "touched" — ``last_touched_day``
            resets to current game day.
        drift_states: Drift states in threshold order (ascending).
        initial_day: Day the thread starts its clock from. Usually 0 for
            ambient threads; can be later for threads that only start
            counting after a specific flag is set.
    """

    id: str
    touch_triggers: list[str] = field(default_factory=list)
    drift_states: list[DriftState] = field(default_factory=list)
    initial_day: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimedThread":
        drift = [DriftState.from_dict(d) for d in data.get("drift_states", [])]
        # Enforce threshold-ascending order so evaluation can short-circuit.
        drift.sort(key=lambda s: s.threshold_days)
        return cls(
            id=data["id"],
            touch_triggers=list(data.get("touch_triggers", [])),
            drift_states=drift,
            initial_day=int(data.get("initial_day", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "touch_triggers": list(self.touch_triggers),
            "drift_states": [s.to_dict() for s in self.drift_states],
            "initial_day": self.initial_day,
        }


@dataclass
class TimedThreadState:
    """Per-player runtime state for one TimedThread.

    Lives inside ``Player.timed_thread_state`` keyed by thread_id.

    Attributes:
        last_touched_day: Day of the most recent touch. ``None`` when
            the thread has never been touched (no interaction has kicked
            it off). The evaluator skips threads in this state, so
            inactive threads never drift.
        entered_states: Drift state ids that have already fired.
            Prevents re-entering the same state.
    """

    last_touched_day: Optional[int] = None
    entered_states: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimedThreadState":
        raw = data.get("last_touched_day")
        if raw is None:
            ltd: Optional[int] = None
        else:
            ltd = int(raw)
            # Pre-QA-F-1 saves used 0 as the "never touched" default.
            # Treat that as None on load so old saves don't drift
            # spuriously; genuine touches were always > 0.
            if ltd == 0:
                ltd = None
        return cls(
            last_touched_day=ltd,
            entered_states=list(data.get("entered_states", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_touched_day": self.last_touched_day,
            "entered_states": list(self.entered_states),
        }

    def has_entered(self, state_id: str) -> bool:
        return state_id in self.entered_states

    def mark_entered(self, state_id: str) -> None:
        if state_id not in self.entered_states:
            self.entered_states.append(state_id)


@dataclass
class DriftEvent:
    """Emitted when a thread enters a drift state.

    Returned by the evaluator so callers (game.py) can surface journal
    entries / narration / news without the model knowing about those
    concrete systems.
    """

    thread_id: str
    state_id: str
    journal_entry: str
    flag_to_set: str
    narration: str
    game_day: int


def initial_state_for_thread(thread: TimedThread) -> TimedThreadState:
    """Build a fresh state for a thread. ``last_touched_day=None`` means
    the thread is inactive until an interaction kicks it off."""
    return TimedThreadState()
