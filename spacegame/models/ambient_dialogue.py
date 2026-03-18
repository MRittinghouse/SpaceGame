"""Ambient crew dialogue system.

Short contextual lines that crew members say in response to game events:
arriving at home systems, visiting faction territory, idle chatter, and
inter-crew banter. Fire-and-forget flavor text, not interactive conversations.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AmbientLine:
    """A single ambient dialogue line."""

    crew_id: str
    text: str
    context: str  # "home_system", "faction_territory", "idle", "inter_crew", "player_action"
    system_id: str = ""
    faction_id: str = ""
    required_crew: str = ""
    min_loyalty: int = 0
    action_type: str = ""  # Sub-type for player_action context (e.g. "sold_cargo", "combat_victory")


class AmbientDialogueManager:
    """Manages ambient dialogue selection and cooldowns."""

    def __init__(self, lines: list[AmbientLine]) -> None:
        self._lines = lines
        self._shown: set[int] = set()  # Indices of shown lines

    def get_line(
        self,
        context: str,
        crew_id: str,
        system_id: str = "",
        faction_id: str = "",
        recruited_ids: Optional[list[str]] = None,
        loyalty: int = 0,
        action_type: str = "",
    ) -> Optional[str]:
        """Get an ambient line matching the context.

        Args:
            context: Line context type.
            crew_id: Which crew member to get a line for.
            system_id: Current system ID (for home_system context).
            faction_id: Current system's faction (for faction_territory).
            recruited_ids: List of recruited crew IDs (for inter_crew).
            loyalty: Current loyalty of this crew member.
            action_type: Sub-type for player_action context.

        Returns:
            The line text, or None if no matching line available.
        """
        matching = self.get_all_matching(
            context, crew_id, system_id, faction_id, recruited_ids, loyalty,
            action_type,
        )
        available = [
            (i, line) for i, line in matching
            if i not in self._shown
        ]
        if not available:
            return None

        idx, line = random.choice(available)
        self._shown.add(idx)
        return line.text

    def get_all_matching(
        self,
        context: str,
        crew_id: str,
        system_id: str = "",
        faction_id: str = "",
        recruited_ids: Optional[list[str]] = None,
        loyalty: int = 0,
        action_type: str = "",
    ) -> list[tuple[int, AmbientLine]]:
        """Get all matching lines with their indices (for filtering).

        Args:
            context: Line context type.
            crew_id: Which crew member to get a line for.
            system_id: Current system ID (for home_system context).
            faction_id: Current system's faction (for faction_territory).
            recruited_ids: List of recruited crew IDs (for inter_crew).
            loyalty: Current loyalty of this crew member.
            action_type: Sub-type for player_action context.

        Returns:
            List of (index, AmbientLine) tuples.
        """
        results: list[tuple[int, AmbientLine]] = []
        for i, line in enumerate(self._lines):
            if line.crew_id != crew_id:
                continue
            if line.context != context:
                continue
            if line.min_loyalty > loyalty:
                continue
            if context == "home_system" and line.system_id != system_id:
                continue
            if context == "faction_territory" and line.faction_id != faction_id:
                continue
            if context == "inter_crew":
                if not recruited_ids or line.required_crew not in recruited_ids:
                    continue
            if context == "player_action" and line.action_type != action_type:
                continue
            results.append((i, line))
        return results

    def get_random_idle(
        self,
        recruited_ids: list[str],
        loyalty_map: dict[str, int],
    ) -> Optional[tuple[str, str]]:
        """Get a random idle line from any recruited crew member.

        Args:
            recruited_ids: Currently recruited crew IDs.
            loyalty_map: Map of crew_id -> loyalty value.

        Returns:
            Tuple of (crew_id, text), or None if nothing available.
        """
        all_available: list[tuple[str, int, AmbientLine]] = []
        for crew_id in recruited_ids:
            loyalty = loyalty_map.get(crew_id, 0)
            matching = self.get_all_matching(
                context="idle",
                crew_id=crew_id,
                loyalty=loyalty,
            )
            for idx, line in matching:
                if idx not in self._shown:
                    all_available.append((crew_id, idx, line))

        if not all_available:
            return None

        crew_id, idx, line = random.choice(all_available)
        self._shown.add(idx)
        return (crew_id, line.text)

    def get_player_action_line(
        self,
        action_type: str,
        recruited_ids: list[str],
        loyalty_map: dict[str, int],
    ) -> Optional[tuple[str, str]]:
        """Get a crew reaction line for a player action.

        Picks a random matching line from any recruited crew member.

        Args:
            action_type: The player action (e.g. "sold_cargo", "combat_victory").
            recruited_ids: Currently recruited crew IDs.
            loyalty_map: Map of crew_id -> loyalty value.

        Returns:
            Tuple of (crew_id, text), or None if no matching line available.
        """
        all_available: list[tuple[str, int, AmbientLine]] = []
        for crew_id in recruited_ids:
            loyalty = loyalty_map.get(crew_id, 0)
            matching = self.get_all_matching(
                context="player_action",
                crew_id=crew_id,
                loyalty=loyalty,
                action_type=action_type,
            )
            for idx, line in matching:
                if idx not in self._shown:
                    all_available.append((crew_id, idx, line))

        if not all_available:
            return None

        crew_id, idx, line = random.choice(all_available)
        self._shown.add(idx)
        return (crew_id, line.text)

    def to_dict(self) -> dict[str, Any]:
        """Serialize shown-line state for saving."""
        return {"shown_indices": list(self._shown)}

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore shown-line state from saved data."""
        self._shown = set(data.get("shown_indices", []))
