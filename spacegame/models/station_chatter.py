"""
Station chatter system.

Provides contextual ambient text lines for each station, filtered by system,
player reputation, active galaxy events, and dialogue flags. Tracks shown
lines per system to avoid repetition.

One-shot lines (progression-gated reactions) appear exactly once per save,
then retire permanently. This prevents the "arrow to the knee" problem where
NPCs endlessly reference the same player achievement.
"""

from __future__ import annotations

import random as _rng
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatterLine:
    """A single station chatter line."""

    id: str
    system_id: str
    text: str
    category: str  # "overheard", "notice", "announcement", "atmosphere"
    faction_id: str = ""
    min_reputation: int = -100
    max_reputation: int = 100
    requires_event_type: str = ""
    weight: int = 10
    required_flags: list[str] = field(default_factory=list)
    excluded_flags: list[str] = field(default_factory=list)
    one_shot: bool = False  # If True, appears at most once per save file


class StationChatterManager:
    """Manages station chatter lines with filtering and shown-line tracking.

    Filters lines by system, reputation range, active events, and player flags.
    Tracks previously shown lines per system to avoid repetition within a visit.
    One-shot lines are permanently retired after first display.
    """

    def __init__(self, lines: list[ChatterLine]) -> None:
        self._lines = lines
        self._shown: dict[str, set[str]] = {}  # system_id -> shown this visit
        self._retired: set[str] = set()  # Permanently retired one-shot line IDs

    def get_chatter(
        self,
        system_id: str,
        player_rep: int,
        active_event_types: list[str],
        count: int = 3,
        player_flags: dict[str, bool] | None = None,
    ) -> list[str]:
        """Get filtered chatter lines for a system.

        Args:
            system_id: Station system ID.
            player_rep: Player's reputation with the local faction.
            active_event_types: List of active galaxy event type strings.
            count: Maximum number of lines to return.
            player_flags: Player dialogue flags for progression-gated lines.

        Returns:
            List of chatter text strings, up to count.
        """
        flags = player_flags or {}
        shown = self._shown.get(system_id, set())

        candidates = []
        for line in self._lines:
            if line.system_id != system_id:
                continue
            if line.id in shown:
                continue
            if line.id in self._retired:
                continue
            if player_rep < line.min_reputation or player_rep > line.max_reputation:
                continue
            if line.requires_event_type and line.requires_event_type not in active_event_types:
                continue
            # Flag-based filtering
            if line.required_flags:
                if not all(flags.get(f, False) for f in line.required_flags):
                    continue
            if line.excluded_flags:
                if any(flags.get(f, False) for f in line.excluded_flags):
                    continue
            candidates.append(line)

        selected = _rng.sample(candidates, min(count, len(candidates)))

        # Track shown
        if system_id not in self._shown:
            self._shown[system_id] = set()
        for line in selected:
            self._shown[system_id].add(line.id)
            # Permanently retire one-shot lines
            if line.one_shot:
                self._retired.add(line.id)

        return [line.text for line in selected]

    def reset_shown(self, system_id: str) -> None:
        """Clear shown-line tracking for a system.

        Does NOT clear retired one-shot lines -- those are permanent.

        Args:
            system_id: System to reset.
        """
        self._shown.pop(system_id, None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for save system."""
        return {
            "shown": {sid: list(ids) for sid, ids in self._shown.items()},
            "retired": list(self._retired),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], lines: list[ChatterLine]) -> StationChatterManager:
        """Restore from serialized state.

        Args:
            data: Serialized dict from to_dict().
            lines: Full list of ChatterLine instances.

        Returns:
            Restored StationChatterManager.
        """
        manager = cls(lines)
        shown_data = data.get("shown", {})
        for sid, id_list in shown_data.items():
            manager._shown[sid] = set(id_list)
        manager._retired = set(data.get("retired", []))
        return manager
