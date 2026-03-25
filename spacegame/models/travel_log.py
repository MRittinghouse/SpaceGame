"""
Travel log generator.

Produces JournalEntry instances for first visits, major trades, encounters,
and galaxy events. Uses templates from data/journal/travel_log_templates.json.
"""

from __future__ import annotations

import random as _rng
from typing import Any, Optional

from spacegame.models.journal import JournalEntry


class TravelLogGenerator:
    """Generates travel log journal entries from templates.

    Templates are data-driven JSON loaded by DataLoader. The generator
    selects random templates and fills in placeholders.
    """

    def __init__(self, templates: dict[str, Any]) -> None:
        self._first_visit: dict[str, str] = templates.get("first_visit", {})
        self._major_trade: list[str] = templates.get("major_trade", [])
        self._encounter: list[str] = templates.get("encounter_survived", [])
        self._galaxy_event: list[str] = templates.get("galaxy_event_witnessed", [])
        self._counter: int = 0

    def _next_id(self, prefix: str) -> str:
        """Generate a unique entry ID."""
        self._counter += 1
        return f"travel_{prefix}_{self._counter}"

    def on_first_visit(self, system_id: str, game_day: int) -> Optional[JournalEntry]:
        """Generate a journal entry for first visit to a system.

        Args:
            system_id: System being visited for the first time.
            game_day: Current game day.

        Returns:
            JournalEntry if template exists for this system, None otherwise.
        """
        text = self._first_visit.get(system_id)
        if not text:
            return None
        return JournalEntry(
            entry_id=self._next_id("visit"),
            text=text,
            game_day=game_day,
            system_id=system_id,
            source="auto",
            tag="travel",
        )

    def on_major_trade(
        self, commodity: str, profit: int, system_id: str, game_day: int
    ) -> Optional[JournalEntry]:
        """Generate a journal entry for a major trade.

        Args:
            commodity: Commodity name traded.
            profit: Profit earned in CR.
            system_id: System where trade occurred.
            game_day: Current game day.

        Returns:
            JournalEntry if templates exist, None otherwise.
        """
        if not self._major_trade:
            return None
        template = _rng.choice(self._major_trade)
        text = template.format(commodity=commodity, profit=profit, system=system_id)
        return JournalEntry(
            entry_id=self._next_id("trade"),
            text=text,
            game_day=game_day,
            system_id=system_id,
            source="auto",
            tag="travel",
        )

    def on_encounter_survived(self, system_id: str, game_day: int) -> Optional[JournalEntry]:
        """Generate a journal entry for surviving an encounter.

        Args:
            system_id: System near which the encounter occurred.
            game_day: Current game day.

        Returns:
            JournalEntry if templates exist, None otherwise.
        """
        if not self._encounter:
            return None
        template = _rng.choice(self._encounter)
        text = template.format(system=system_id)
        return JournalEntry(
            entry_id=self._next_id("encounter"),
            text=text,
            game_day=game_day,
            system_id=system_id,
            source="auto",
            tag="travel",
        )

    def on_galaxy_event_witnessed(
        self,
        event_type: str,
        description: str,
        system_id: str,
        game_day: int,
    ) -> Optional[JournalEntry]:
        """Generate a journal entry for witnessing a galaxy event.

        Args:
            event_type: Type of event (e.g. "embargo", "festival").
            description: Event description text.
            system_id: System where event is happening.
            game_day: Current game day.

        Returns:
            JournalEntry if templates exist, None otherwise.
        """
        if not self._galaxy_event:
            return None
        template = _rng.choice(self._galaxy_event)
        text = template.format(event_type=event_type, description=description, system=system_id)
        return JournalEntry(
            entry_id=self._next_id("event"),
            text=text,
            game_day=game_day,
            system_id=system_id,
            source="auto",
            tag="travel",
        )
