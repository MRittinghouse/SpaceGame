"""RC-1: per-captain memory state.

Tracks the player's history with each named ``EnemyCaptain`` so recurring
encounters can serve return-meeting hails, and so rivalries can resolve
into one of several end states based on player choice.

Resolution semantics (v1)
-------------------------
Each meaningful combat outcome resolves the rivalry immediately:

- ``VICTORY`` (player won combat)   -> ``defeated`` (captain removed)
- ``NEGOTIATED``                     -> ``truce`` (captain stands down)
- ``BRIBED``                         -> ``bribed_off`` (transactional)
- ``DEFEAT`` (player lost combat)    -> no resolution; counts toward cap
- ``FLED`` (player ran)              -> no resolution; counts toward cap

After ``RESOLUTION_THRESHOLD`` total encounters with no resolution
trigger, the captain auto-retires to ``wanderer`` (they've made their
point or moved on). This prevents an infinite-flee loop where the same
captain harasses the player forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Status constants — captain's current standing relative to the player.
STATUS_ACTIVE = "active"  # Still in the recurring rotation.
STATUS_DEFEATED = "defeated"  # Player won the rivalry in combat.
STATUS_TRUCE = "truce"  # Negotiated peace.
STATUS_BRIBED_OFF = "bribed_off"  # Player paid them off.
STATUS_WANDERER = "wanderer"  # Auto-retired after threshold.

VALID_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_ACTIVE,
        STATUS_DEFEATED,
        STATUS_TRUCE,
        STATUS_BRIBED_OFF,
        STATUS_WANDERER,
    }
)

# Outcome strings recorded on ``last_outcome``. Mirror combat result names
# (lowercased) so callers can pass them straight through from CombatResult.
OUTCOME_VICTORY = "victory"
OUTCOME_DEFEAT = "defeat"
OUTCOME_NEGOTIATED = "negotiated"
OUTCOME_BRIBED = "bribed"
OUTCOME_FLED = "fled"
# SA-B2: auction loss (rival outbids player on a contested lot). Behaves like
# DEFEAT/FLED in the resolution logic — accumulates toward RESOLUTION_THRESHOLD,
# never triggers a one-step status transition.
OUTCOME_OUTBID = "outbid"

# Encounters before an unresolved rivalry auto-retires.
RESOLUTION_THRESHOLD = 3


@dataclass
class CaptainMemory:
    """The player's accumulated memory of one named captain.

    Attributes:
        captain_id: The captain's id (links back to ``EnemyCaptain``).
        encounter_count: Total meetings (any outcome).
        last_outcome: Most recent combat outcome string (see OUTCOME_*).
            Empty until first encounter resolves.
        status: One of ``VALID_STATUSES``. ``active`` means the captain
            is still in the encounter rotation; everything else is a
            terminal state.
        first_seen_day: Game day of the first encounter. 0 = never met.
        last_seen_day: Game day of the most recent encounter. 0 = never.
    """

    captain_id: str
    encounter_count: int = 0
    last_outcome: str = ""
    status: str = STATUS_ACTIVE
    first_seen_day: int = 0
    last_seen_day: int = 0

    @property
    def is_resolved(self) -> bool:
        """True when the captain's rivalry has reached a terminal state."""
        return self.status != STATUS_ACTIVE

    @property
    def is_first_meeting(self) -> bool:
        """True before any encounter has been recorded for this captain."""
        return self.encounter_count == 0

    def record_encounter(self, outcome: str, game_day: int) -> None:
        """Record a meeting + apply resolution rules in one call.

        Increments ``encounter_count``, updates day stamps, sets
        ``last_outcome``, and transitions ``status`` if the outcome is
        a resolution trigger or if the threshold has been reached.

        Idempotent in the sense that calling on a resolved captain still
        updates the stamps but never reverses status. Resolution is
        permanent once set.
        """
        if self.encounter_count == 0:
            self.first_seen_day = game_day
        self.encounter_count += 1
        self.last_seen_day = game_day
        self.last_outcome = outcome

        # Already resolved — nothing further to do.
        if self.status != STATUS_ACTIVE:
            return

        # Single-action resolutions.
        if outcome == OUTCOME_VICTORY:
            self.status = STATUS_DEFEATED
            return
        if outcome == OUTCOME_NEGOTIATED:
            self.status = STATUS_TRUCE
            return
        if outcome == OUTCOME_BRIBED:
            self.status = STATUS_BRIBED_OFF
            return

        # Threshold-based auto-retire (defeat / fled accumulate).
        if self.encounter_count >= RESOLUTION_THRESHOLD:
            self.status = STATUS_WANDERER

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "captain_id": self.captain_id,
            "encounter_count": self.encounter_count,
            "last_outcome": self.last_outcome,
            "status": self.status,
            "first_seen_day": self.first_seen_day,
            "last_seen_day": self.last_seen_day,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptainMemory":
        status = data.get("status", STATUS_ACTIVE)
        if status not in VALID_STATUSES:
            status = STATUS_ACTIVE
        return cls(
            captain_id=data["captain_id"],
            encounter_count=int(data.get("encounter_count", 0)),
            last_outcome=data.get("last_outcome", ""),
            status=status,
            first_seen_day=int(data.get("first_seen_day", 0)),
            last_seen_day=int(data.get("last_seen_day", 0)),
        )
