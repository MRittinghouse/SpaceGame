"""SA-2 Deep Shafts memorial: pilgrimage state + rep / journal helpers.

Layered on top of :mod:`spacegame.models.player` (the runtime owner of
``DeepShaftsState``). All numeric constants live at module scope so a
future SA-X2 reputation rebalance can tune them in one place.

The view (:mod:`spacegame.views.deep_shafts_view`) calls
:func:`apply_visit` once per ``on_enter`` to advance state. The function
mutates the passed-in state in place AND returns ``(rep_grant,
journal_entry_id_or_None)`` so the view can dispatch the rep change and
journal-flag set without re-deriving the math.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Tunables (decisions locked in the SA-2 plan)
# ---------------------------------------------------------------------------

# First visit grants this many Miners' Union faction-rep points.
PILGRIMAGE_FIRST_GRANT: int = 5

# Each subsequent return after the cooldown grants this many points.
PILGRIMAGE_RECURRING_GRANT: int = 2

# Cumulative cap across the playthrough. Once ``blessing_total`` reaches
# the cap, visits still increment ``visit_count`` and may unlock journal
# entries, but no further rep grants fire.
PILGRIMAGE_BLESSING_CAP: int = 20

# Minimum days between recurring rep grants. A return on day
# ``last_pilgrimage_day + COOLDOWN_DAYS`` (inclusive) qualifies.
PILGRIMAGE_COOLDOWN_DAYS: int = 7

# Minimum game-day spacing between consecutive Sora Takahashi journal
# unlocks. Prevents a player rapid-cycling visits from burning the arc
# in one sitting.
PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS: int = 3

# Visit-count thresholds at which Sora journal entries unlock. Index 0
# corresponds to ``pilgrimage_journal_1``, index 1 to
# ``pilgrimage_journal_2``, and so on.
PILGRIMAGE_JOURNAL_THRESHOLDS: tuple[int, ...] = (1, 3, 5, 8, 12)


# ---------------------------------------------------------------------------
# Mutable runtime state
# ---------------------------------------------------------------------------


@dataclass
class DeepShaftsState:
    """Per-save Deep Shafts runtime state.

    Stored on :class:`spacegame.models.player.Player` as
    ``deep_shafts_state``. Faction-rep value lives separately on
    ``Player.faction_reputation["miners_union"]`` per the existing API.

    Attributes:
        visit_count: Total number of times the player has entered the
            venue. Increments on every ``DeepShaftsView.on_enter``.
        last_pilgrimage_day: Game day of the most recent rep-granting
            visit. Used by the cooldown gate for recurring grants.
        blessing_total: Cumulative Miners' Union rep granted via the
            pilgrimage mechanic across the playthrough. Caps at
            :data:`PILGRIMAGE_BLESSING_CAP`.
        scripted_scene_played: True once the first-visit scripted scene
            has fired. Subsequent visits skip the scene.
        last_journal_unlock_day: Game day of the most recent Sora
            journal unlock. Used by the spacing rule.
    """

    visit_count: int = 0
    last_pilgrimage_day: int = 0
    blessing_total: int = 0
    scripted_scene_played: bool = False
    last_journal_unlock_day: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "visit_count": self.visit_count,
            "last_pilgrimage_day": self.last_pilgrimage_day,
            "blessing_total": self.blessing_total,
            "scripted_scene_played": self.scripted_scene_played,
            "last_journal_unlock_day": self.last_journal_unlock_day,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeepShaftsState":
        """Restore a :class:`DeepShaftsState` from save data.

        Missing keys default to safe values so legacy saves and partial
        fixtures load without crashing.
        """
        return cls(
            visit_count=int(data.get("visit_count", 0)),
            last_pilgrimage_day=int(data.get("last_pilgrimage_day", 0)),
            blessing_total=int(data.get("blessing_total", 0)),
            scripted_scene_played=bool(data.get("scripted_scene_played", False)),
            last_journal_unlock_day=int(data.get("last_journal_unlock_day", 0)),
        )


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def apply_visit(state: DeepShaftsState, current_day: int) -> tuple[int, Optional[str]]:
    """Advance state for one venue visit and return the side-effect tuple.

    Mutates ``state`` in place: increments ``visit_count``, applies the
    rep grant (subject to cooldown + cap), updates
    ``last_pilgrimage_day`` if a grant fires, and unlocks the next Sora
    journal entry if the visit hits a threshold and the spacing rule is
    satisfied.

    Args:
        state: Player's :class:`DeepShaftsState`. Mutated.
        current_day: ``Player.game_day`` at the time of the visit.

    Returns:
        ``(rep_grant, journal_entry_id)``: ``rep_grant`` is the number
        of Miners' Union rep points to apply via
        :meth:`spacegame.models.player.Player.modify_reputation`.
        ``journal_entry_id`` is the ``pilgrimage_journal_<n>`` flag to
        set, or ``None`` if no entry unlocks on this visit.
    """
    state.visit_count += 1
    rep_grant = _resolve_rep_grant(state, current_day)
    journal_id = _resolve_journal_unlock(state, current_day)
    return rep_grant, journal_id


def _resolve_rep_grant(state: DeepShaftsState, current_day: int) -> int:
    """Compute the rep grant for the current visit and update state.

    Mutates ``state.blessing_total`` and ``state.last_pilgrimage_day``
    when a grant fires. Returns the int amount to forward to
    ``Player.modify_reputation``.
    """
    if state.blessing_total >= PILGRIMAGE_BLESSING_CAP:
        return 0
    is_first_grant = state.blessing_total == 0 and state.last_pilgrimage_day == 0
    if is_first_grant:
        intended = PILGRIMAGE_FIRST_GRANT
    else:
        days_since = current_day - state.last_pilgrimage_day
        if days_since < PILGRIMAGE_COOLDOWN_DAYS:
            return 0
        intended = PILGRIMAGE_RECURRING_GRANT
    headroom = PILGRIMAGE_BLESSING_CAP - state.blessing_total
    grant = min(intended, headroom)
    if grant <= 0:
        return 0
    state.blessing_total += grant
    state.last_pilgrimage_day = current_day
    return grant


def _resolve_journal_unlock(state: DeepShaftsState, current_day: int) -> Optional[str]:
    """Return the journal entry id to unlock on this visit, or None.

    A journal entry unlocks when:
      - ``state.visit_count`` matches one of
        :data:`PILGRIMAGE_JOURNAL_THRESHOLDS`,
      - the corresponding entry has not already been unlocked
        (``visit_count`` index implies the entry id), and
      - at least :data:`PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS` game days
        have elapsed since the previous unlock.

    Mutates ``state.last_journal_unlock_day`` when an unlock fires.
    """
    try:
        threshold_index = PILGRIMAGE_JOURNAL_THRESHOLDS.index(state.visit_count)
    except ValueError:
        return None
    if state.last_journal_unlock_day != 0:
        days_since = current_day - state.last_journal_unlock_day
        if days_since < PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS:
            return None
    state.last_journal_unlock_day = current_day
    return f"pilgrimage_journal_{threshold_index + 1}"
