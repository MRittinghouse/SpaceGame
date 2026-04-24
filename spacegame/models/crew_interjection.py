"""CE-5: Crew combat interjections.

Companions speak short situational lines during combat: opening greeting,
concern when the player drops below 30% hull, confidence when an enemy
falls below 20%, recognition of a nemesis-tier enemy, and a closing
beat on victory or defeat.

The model is purely view-layer cosmetic. The combat engine doesn't need
to know about it. ``CombatView`` owns a ``CrewInterjectionResolver`` per
fight and asks it to evaluate at well-defined hook points (round start
and combat end).

Trigger types
-------------
- ``first_turn`` — fires once on round 1 for each crew aboard.
- ``player_low_hp`` — fires once when player ``hull / max_hull <= threshold``.
- ``enemy_low_hp`` — fires once when any surviving enemy crosses below
  ``threshold``.
- ``enemy_type_match`` — fires once when an enemy with a matching template
  id appears in the fight (nemesis recognition).
- ``combat_outcome`` — fires once at fight end. The line set is partitioned
  by ``conditions.outcome`` ("victory" | "defeat").

Throttling: callers (the view) decide how often to call ``evaluate`` and
how many events to surface per round. The resolver itself only enforces
once-per-(crew_id, trigger) firing within a single fight.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from spacegame.models.combat import CombatState


VALID_INTERJECTION_TRIGGERS: frozenset[str] = frozenset(
    {
        "first_turn",
        "player_low_hp",
        "enemy_low_hp",
        "enemy_type_match",
        "combat_outcome",
    }
)


# Default thresholds match the roadmap spec; an interjection's
# ``conditions`` dict can override per entry.
DEFAULT_PLAYER_LOW_HP_PCT = 0.30
DEFAULT_ENEMY_LOW_HP_PCT = 0.20


@dataclass
class CrewInterjection:
    """A bank of crew lines tied to one (crew_id, trigger) pair.

    Attributes:
        crew_id: Crew template id (e.g. ``elena_reeves``).
        trigger: One of ``VALID_INTERJECTION_TRIGGERS``.
        lines: Set of interchangeable lines the resolver picks from. The
            resolver picks deterministically from the seeded RNG so the
            same fight on the same seed always picks the same line.
        conditions: Per-trigger qualifiers:
            - ``threshold`` (float, 0-1) for hp_threshold variants
            - ``enemy_template_id`` (str) for ``enemy_type_match``
            - ``outcome`` ("victory" | "defeat") for ``combat_outcome``
    """

    crew_id: str
    trigger: str
    lines: list[str]
    conditions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrewInterjection":
        return cls(
            crew_id=data["crew_id"],
            trigger=data["trigger"],
            lines=list(data.get("lines", [])),
            conditions=dict(data.get("conditions", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "crew_id": self.crew_id,
            "trigger": self.trigger,
            "lines": list(self.lines),
            "conditions": dict(self.conditions),
        }


@dataclass
class InterjectionEvent:
    """A crew line that should be surfaced this tick."""

    crew_id: str
    crew_name: str
    trigger: str
    line: str


class CrewInterjectionResolver:
    """Evaluates crew interjections per round during combat.

    Held by the combat view (purely cosmetic — the engine does not call
    this). The resolver tracks (crew_id, trigger) pairs that have fired
    so once-shot lines don't repeat within a single fight.
    """

    def __init__(
        self,
        interjections: list[CrewInterjection],
        crew_aboard: list[tuple[str, str]],
        seed: int = 0,
    ) -> None:
        """Build a resolver scoped to a single combat encounter.

        Args:
            interjections: The full bank of crew interjections (typically
                ``DataLoader.crew_interjections``). The resolver filters
                to entries whose crew_id is in ``crew_aboard`` lazily on
                each evaluate call.
            crew_aboard: List of (crew_id, display_name) for crew on
                the current ship. Display names are used in surface text
                without re-looking-up the crew template each tick.
            seed: Deterministic seed for line-from-bank selection. Same
                seed + same trigger order = same lines, helpful for tests.
        """
        self._interjections = list(interjections)
        self._crew_aboard = dict(crew_aboard)
        self._fired: set[tuple[str, str]] = set()
        self._rng = random.Random(seed)

    @property
    def fired(self) -> set[tuple[str, str]]:
        """Read-only snapshot of (crew_id, trigger) pairs that have fired."""
        return set(self._fired)

    def evaluate_round(
        self, state: "CombatState"
    ) -> list[InterjectionEvent]:
        """Return eligible non-outcome interjections without committing.

        Builds a candidate event for every interjection whose trigger is
        currently satisfied and that hasn't already fired. Caller picks
        which to surface and calls ``commit`` on it; uncommitted events
        remain eligible for future ticks.
        """
        events: list[InterjectionEvent] = []
        for entry in self._interjections:
            if entry.crew_id not in self._crew_aboard:
                continue
            key = (entry.crew_id, entry.trigger)
            if key in self._fired:
                continue
            if not self._round_trigger_satisfied(entry, state):
                continue
            event = self._build_event(entry)
            if event is not None:
                events.append(event)
        return events

    def evaluate_outcome(
        self, state: "CombatState", outcome: str
    ) -> list[InterjectionEvent]:
        """Return eligible ``combat_outcome`` events without committing.

        ``outcome`` is "victory" or "defeat" — matched against the entry's
        ``conditions.outcome`` field. An entry without a configured outcome
        fires for both. Caller commits via ``commit``.
        """
        events: list[InterjectionEvent] = []
        for entry in self._interjections:
            if entry.crew_id not in self._crew_aboard:
                continue
            if entry.trigger != "combat_outcome":
                continue
            key = (entry.crew_id, entry.trigger)
            if key in self._fired:
                continue
            entry_outcome = entry.conditions.get("outcome", "")
            if entry_outcome and entry_outcome != outcome:
                continue
            event = self._build_event(entry)
            if event is not None:
                events.append(event)
        return events

    def commit(self, event: InterjectionEvent) -> None:
        """Mark an event's (crew_id, trigger) pair as fired.

        Idempotent — committing the same event twice is harmless. Callers
        commit only the events they actually surface; the rest stay live
        for the next evaluate call.
        """
        self._fired.add((event.crew_id, event.trigger))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _round_trigger_satisfied(
        self, entry: CrewInterjection, state: "CombatState"
    ) -> bool:
        """Per-round triggers (everything except ``combat_outcome``)."""
        t = entry.trigger
        if t == "first_turn":
            return state.round_number == 1

        if t == "player_low_hp":
            threshold = float(
                entry.conditions.get("threshold", DEFAULT_PLAYER_LOW_HP_PCT)
            )
            max_hp = max(1, state.player.max_hull)
            return state.player.hull / max_hp <= threshold

        if t == "enemy_low_hp":
            threshold = float(
                entry.conditions.get("threshold", DEFAULT_ENEMY_LOW_HP_PCT)
            )
            for enemy in state.surviving_enemies:
                max_hp = max(1, enemy.max_hull)
                if enemy.current_hull / max_hp <= threshold:
                    return True
            return False

        if t == "enemy_type_match":
            target_id = entry.conditions.get("enemy_template_id", "")
            if not target_id:
                return False
            for enemy in state.enemies:
                if enemy.template.id == target_id:
                    return True
            return False

        # combat_outcome handled in evaluate_outcome, never here
        return False

    def _build_event(
        self, entry: CrewInterjection
    ) -> Optional[InterjectionEvent]:
        """Pick a line and build the candidate event (no commit)."""
        if not entry.lines:
            return None
        line = self._rng.choice(entry.lines)
        return InterjectionEvent(
            crew_id=entry.crew_id,
            crew_name=self._crew_aboard.get(entry.crew_id, entry.crew_id),
            trigger=entry.trigger,
            line=line,
        )
