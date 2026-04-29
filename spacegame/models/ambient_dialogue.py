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
    context: str  # "home_system", "faction_territory", "idle", "inter_crew",
    #               "player_action", "combat_after", "flag_triggered"
    system_id: str = ""
    faction_id: str = ""
    required_crew: str = ""
    min_loyalty: int = 0
    action_type: str = (
        ""  # Sub-type for player_action context (e.g. "sold_cargo", "combat_victory")
    )
    required_flags: list[str] = field(default_factory=list)
    excluded_flags: list[str] = field(default_factory=list)


class AmbientDialogueManager:
    """Manages ambient dialogue selection and cooldowns."""

    def __init__(self, lines: list[AmbientLine]) -> None:
        self._lines = lines
        self._shown: set[int] = set()  # Indices of shown lines
        self.last_combat_day: Optional[int] = None

    def get_line(
        self,
        context: str,
        crew_id: str,
        system_id: str = "",
        faction_id: str = "",
        recruited_ids: Optional[list[str]] = None,
        loyalty: int = 0,
        action_type: str = "",
        player_flags: Optional[dict[str, bool]] = None,
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
            player_flags: Player's dialogue flags for flag-conditional filtering.

        Returns:
            The line text, or None if no matching line available.
        """
        matching = self.get_all_matching(
            context,
            crew_id,
            system_id,
            faction_id,
            recruited_ids,
            loyalty,
            action_type,
            player_flags,
        )
        available = [(i, line) for i, line in matching if i not in self._shown]
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
        player_flags: Optional[dict[str, bool]] = None,
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
            player_flags: Player's dialogue flags; when provided, required_flags
                and excluded_flags on each line are evaluated. When None, the
                flag filter is skipped (backward compatibility for callers that
                predate CB-2).

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
            # Flag filter — only active when player_flags is explicitly provided
            if player_flags is not None:
                if line.required_flags and not all(
                    player_flags.get(f) for f in line.required_flags
                ):
                    continue
                if line.excluded_flags and any(player_flags.get(f) for f in line.excluded_flags):
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

    def mark_combat(self, game_day: int) -> None:
        """Record that combat occurred on game_day.

        Args:
            game_day: The current game day when combat resolved.
        """
        self.last_combat_day = game_day

    def get_combat_after_line(
        self,
        recruited_ids: list[str],
        loyalty_map: dict[str, int],
        current_day: int,
        recent_window_days: int = 3,
    ) -> Optional[tuple[str, str]]:
        """Get a post-combat ambient line if within the recency window.

        Only fires when combat was marked within ``recent_window_days`` of
        ``current_day``. Mirrors get_player_action_line but operates on the
        combat_after context and gates on recency rather than action type.

        Args:
            recruited_ids: Currently recruited crew IDs.
            loyalty_map: Map of crew_id -> loyalty value.
            current_day: The current game day.
            recent_window_days: Days after combat during which lines are eligible.

        Returns:
            Tuple of (crew_id, text), or None if outside window or nothing available.
        """
        if self.last_combat_day is None:
            return None
        if (current_day - self.last_combat_day) > recent_window_days:
            return None

        all_available: list[tuple[str, int, AmbientLine]] = []
        for crew_id in recruited_ids:
            loyalty = loyalty_map.get(crew_id, 0)
            matching = self.get_all_matching(
                context="combat_after",
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

    def check_flag_lines(
        self,
        player_flags: dict[str, bool],
        recruited_ids: list[str],
        loyalty_map: dict[str, int],
    ) -> Optional[tuple[str, str]]:
        """Return the first eligible flag-triggered line for any recruited crew member.

        Iterates over recruited crew members and gathers flag_triggered lines
        that pass the flag filter and have not been shown. Returns a random
        pick from eligible lines, or None if none are available.

        Args:
            player_flags: Player's current dialogue flags.
            recruited_ids: Currently recruited crew IDs.
            loyalty_map: Map of crew_id -> loyalty value.

        Returns:
            Tuple of (crew_id, text), or None if no eligible line exists.
        """
        all_available: list[tuple[str, int, AmbientLine]] = []
        for crew_id in recruited_ids:
            loyalty = loyalty_map.get(crew_id, 0)
            matching = self.get_all_matching(
                context="flag_triggered",
                crew_id=crew_id,
                loyalty=loyalty,
                player_flags=player_flags,
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
        return {
            "shown_indices": list(self._shown),
            "last_combat_day": self.last_combat_day,
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore shown-line state from saved data."""
        self._shown = set(data.get("shown_indices", []))
        self.last_combat_day = data.get("last_combat_day", None)
