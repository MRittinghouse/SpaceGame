"""RC-3: per-meeting-state captain dialogue variants.

A ``CaptainVariant`` is a partial override of an ``EnemyCaptain``'s
dialogue, scoped to a specific player relationship state with that
captain. The combat view consults the player's ``CaptainMemory`` to pick
the appropriate variant; any field the variant leaves empty falls back
to the base captain's value.

Meeting states
--------------
- ``first_meeting`` — never met. Base captain dialogue (default).
- ``return``        — met before, no resolution yet (status ACTIVE, count >= 1).
- ``post_truce``    — player negotiated peace previously.
- ``post_bribed_off`` — player bribed them off previously.
- ``post_defeated`` — player won in combat previously (rare; resolved
  captains usually leave the pool).
- ``post_wanderer`` — auto-retired after threshold (rare; same).

Author content for ``return`` first; the post-resolved states are mostly
for scripted re-encounters that future content (TW or RC-5) may add.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from spacegame.models.captain_memory import (
    STATUS_ACTIVE,
    STATUS_BRIBED_OFF,
    STATUS_DEFEATED,
    STATUS_TRUCE,
    STATUS_WANDERER,
)

if TYPE_CHECKING:
    from spacegame.models.captain_memory import CaptainMemory
    from spacegame.models.enemy_captain import EnemyCaptain


# Meeting state constants — keys for variant lookup.
MEETING_STATE_FIRST = "first_meeting"
MEETING_STATE_RETURN = "return"
MEETING_STATE_POST_TRUCE = "post_truce"
MEETING_STATE_POST_BRIBED_OFF = "post_bribed_off"
MEETING_STATE_POST_DEFEATED = "post_defeated"
MEETING_STATE_POST_WANDERER = "post_wanderer"

VALID_MEETING_STATES: frozenset[str] = frozenset(
    {
        MEETING_STATE_FIRST,
        MEETING_STATE_RETURN,
        MEETING_STATE_POST_TRUCE,
        MEETING_STATE_POST_BRIBED_OFF,
        MEETING_STATE_POST_DEFEATED,
        MEETING_STATE_POST_WANDERER,
    }
)

# Map captain status -> "post_<status>" meeting state. ACTIVE is handled
# separately because it splits between first_meeting and return based on
# encounter_count.
_STATUS_TO_MEETING_STATE = {
    STATUS_TRUCE: MEETING_STATE_POST_TRUCE,
    STATUS_BRIBED_OFF: MEETING_STATE_POST_BRIBED_OFF,
    STATUS_DEFEATED: MEETING_STATE_POST_DEFEATED,
    STATUS_WANDERER: MEETING_STATE_POST_WANDERER,
}


@dataclass
class CaptainVariant:
    """A partial override of captain dialogue for one meeting state.

    Empty string in any field means "fall back to the base captain's
    value at resolution time" — variants are sparse overlays, not full
    definitions.
    """

    captain_id: str
    meeting_state: str
    pre_combat_hail: str = ""
    surrender_line: str = ""
    retreat_line: str = ""
    victory_line: str = ""
    defeat_line: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptainVariant":
        return cls(
            captain_id=data["captain_id"],
            meeting_state=data["meeting_state"],
            pre_combat_hail=data.get("pre_combat_hail", ""),
            surrender_line=data.get("surrender_line", ""),
            retreat_line=data.get("retreat_line", ""),
            victory_line=data.get("victory_line", ""),
            defeat_line=data.get("defeat_line", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "captain_id": self.captain_id,
            "meeting_state": self.meeting_state,
            "pre_combat_hail": self.pre_combat_hail,
            "surrender_line": self.surrender_line,
            "retreat_line": self.retreat_line,
            "victory_line": self.victory_line,
            "defeat_line": self.defeat_line,
        }


@dataclass
class EffectiveCaptainDialogue:
    """The resolved dialogue for a captain after variant overlay.

    Fields contain whichever value won — the variant's value if set,
    otherwise the base captain's value. Always populated, never empty
    (assuming the base captain had content).
    """

    captain_id: str
    display_name: str
    pre_combat_hail: str
    surrender_line: str
    retreat_line: str
    victory_line: str
    defeat_line: str
    meeting_state: str  # Tracks which state was resolved (for diagnostics)


def meeting_state_for_memory(memory: Optional["CaptainMemory"]) -> str:
    """Pick the meeting state given the player's memory of the captain.

    None or unmet (encounter_count == 0) => ``first_meeting``.
    Active + met before => ``return``.
    Resolved => ``post_<status>``.
    """
    if memory is None or memory.encounter_count == 0:
        return MEETING_STATE_FIRST
    if memory.status == STATUS_ACTIVE:
        return MEETING_STATE_RETURN
    return _STATUS_TO_MEETING_STATE.get(memory.status, MEETING_STATE_FIRST)


def _override(base: str, variant: str) -> str:
    """Variant's value wins if set, otherwise fall back to base."""
    return variant if variant else base


def get_effective_captain_dialogue(
    captain: "EnemyCaptain",
    memory: Optional["CaptainMemory"],
    variants_by_key: dict[tuple[str, str], CaptainVariant],
) -> EffectiveCaptainDialogue:
    """Resolve a captain's effective dialogue for the current meeting.

    Args:
        captain: The base captain definition.
        memory: The player's memory of this captain (None = never met).
        variants_by_key: Lookup keyed by (captain_id, meeting_state).

    Returns:
        EffectiveCaptainDialogue with overlaid fields.
    """
    state = meeting_state_for_memory(memory)
    variant = variants_by_key.get((captain.id, state))
    if variant is None:
        return EffectiveCaptainDialogue(
            captain_id=captain.id,
            display_name=captain.display_name,
            pre_combat_hail=captain.pre_combat_hail,
            surrender_line=captain.surrender_line,
            retreat_line=captain.retreat_line,
            victory_line=captain.victory_line,
            defeat_line=captain.defeat_line,
            meeting_state=state,
        )
    return EffectiveCaptainDialogue(
        captain_id=captain.id,
        display_name=captain.display_name,
        pre_combat_hail=_override(captain.pre_combat_hail, variant.pre_combat_hail),
        surrender_line=_override(captain.surrender_line, variant.surrender_line),
        retreat_line=_override(captain.retreat_line, variant.retreat_line),
        victory_line=_override(captain.victory_line, variant.victory_line),
        defeat_line=_override(captain.defeat_line, variant.defeat_line),
        meeting_state=state,
    )
