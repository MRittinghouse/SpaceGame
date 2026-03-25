"""News ticker model.

Generates and displays scrolling headlines that reflect current game state —
galaxy events, market shifts, political dispatches, and player milestones.
Falls back to flavor text when nothing dramatic is happening.
"""

from __future__ import annotations

import random as _rng
from collections import deque
from dataclasses import dataclass
from typing import Any

# ============================================================================
# Data Model
# ============================================================================


@dataclass
class HeadlineTemplate:
    """A template for a single news headline.

    Placeholders in `template` are filled from event context dicts using
    standard str.format_map(); unknown keys are silently left as-is.
    """

    id: str
    template: str  # e.g. "{faction} imposes embargo on {commodity} at {system}."
    trigger: str  # "galaxy_event_embargo", "galaxy_event_festival", "market_event",
    #              "political_event", "player_milestone", "flavor"
    priority: int = 5
    faction_id: str = ""  # optional faction filter; "" means any faction


# ============================================================================
# Safe formatter (leaves unknown keys untouched)
# ============================================================================


class _SafeDict(dict):  # type: ignore[type-arg]
    """dict subclass that returns the key placeholder for missing keys."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _fill(template: str, ctx: dict[str, str]) -> str:
    """Fill template placeholders from ctx, leaving unknown keys intact."""
    return template.format_map(_SafeDict(ctx))


# ============================================================================
# NewsTicker
# ============================================================================

_SAVE_VERSION = 1


class NewsTicker:
    """Generates and manages a rolling buffer of news headlines.

    Headlines are produced from game-state context (galaxy events, market
    events, political events, player milestones) and topped up with flavor
    text when nothing dramatic is occurring. The buffer drops the oldest entry
    once it reaches `buffer_size`.
    """

    def __init__(self, templates: list[HeadlineTemplate], buffer_size: int = 8) -> None:
        self._templates = templates
        self._buffer_size = buffer_size
        # deque left=oldest, right=newest
        self._buffer: deque[str] = deque(maxlen=buffer_size)
        # Tracks flavor IDs already used in the current cycle to avoid repeats
        self._used_flavor_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_headline(self, text: str, priority: int = 5) -> None:
        """Manually add a headline to the buffer.

        Args:
            text: Headline string to add.
            priority: Reserved for future ordering use; currently unused.
        """
        self._buffer.append(text)

    def get_headlines(self, count: int = 5) -> list[str]:
        """Get the most recent headlines, newest first.

        Args:
            count: Maximum number of headlines to return.

        Returns:
            List of headline strings, newest first, at most `count` long.
        """
        if count <= 0:
            return []
        # Buffer stores oldest→newest; reverse for newest-first output
        items = list(self._buffer)
        items.reverse()
        return items[:count]

    def generate_headlines(self, context: dict[str, Any]) -> None:
        """Generate headlines from game state context and add them to the buffer.

        Processes each context category in turn (galaxy events, market events,
        political events, player milestones).  After all event-driven headlines
        are generated, flavor templates fill any remaining capacity.

        Args:
            context: Dict with optional keys:
                - "galaxy_events": list[dict] — keys: event_type, system_id,
                  faction_id, description, commodity
                - "market_events": list[dict] — keys: event_type, commodity,
                  system_id, description
                - "political_events": list[dict] — keys: description
                - "player_milestones": list[str] — pre-formatted strings
        """
        generated: list[str] = []

        # --- galaxy_events ---
        for event in context.get("galaxy_events", []):
            trigger = f"galaxy_event_{event.get('event_type', '')}"
            ctx = {
                "system": event.get("system_id", ""),
                "faction": event.get("faction_id", ""),
                "commodity": event.get("commodity", ""),
                "description": event.get("description", ""),
            }
            headline = self._pick_headline(trigger, ctx)
            if headline:
                generated.append(headline)

        # --- market_events ---
        for event in context.get("market_events", []):
            ctx = {
                "system": event.get("system_id", ""),
                "commodity": event.get("commodity", ""),
                "description": event.get("description", ""),
                "event_type": event.get("event_type", ""),
            }
            headline = self._pick_headline("market_event", ctx)
            if headline:
                generated.append(headline)

        # --- political_events ---
        for event in context.get("political_events", []):
            ctx = {
                "description": event.get("description", ""),
            }
            headline = self._pick_headline("political_event", ctx)
            if headline:
                generated.append(headline)

        # --- player_milestones ---
        for milestone in context.get("player_milestones", []):
            ctx = {"milestone": milestone}
            headline = self._pick_headline("player_milestone", ctx)
            if headline:
                generated.append(headline)

        # --- player_actions (trade, mining, salvage, combat achievements) ---
        for action in context.get("player_actions", []):
            ctx = {
                "player": action.get("player_name", ""),
                "ship": action.get("ship_name", ""),
                "system": action.get("system", ""),
                "amount": action.get("amount", ""),
                "commodity": action.get("commodity", ""),
                "detail": action.get("detail", ""),
            }
            headline = self._pick_headline("player_action", ctx)
            if headline:
                generated.append(headline)

        # --- flavor fallback: fill buffer if no event headlines were generated ---
        if not generated:
            flavor_headline = self._pick_flavor()
            if flavor_headline:
                generated.append(flavor_headline)

        for h in generated:
            self._buffer.append(h)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize buffer state for the save system.

        Returns:
            Dict containing version, buffer contents, and buffer_size.
        """
        return {
            "version": _SAVE_VERSION,
            "buffer": list(self._buffer),
            "buffer_size": self._buffer_size,
            "used_flavor_ids": list(self._used_flavor_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], templates: list[HeadlineTemplate]) -> NewsTicker:
        """Restore a NewsTicker from serialized data.

        Args:
            data: Serialized dict from to_dict().
            templates: Full list of HeadlineTemplate instances.

        Returns:
            Restored NewsTicker with buffer contents intact.
        """
        buffer_size = data.get("buffer_size", 8)
        ticker = cls(templates=templates, buffer_size=buffer_size)
        for headline in data.get("buffer", []):
            ticker._buffer.append(headline)
        ticker._used_flavor_ids = set(data.get("used_flavor_ids", []))
        return ticker

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pick_headline(self, trigger: str, ctx: dict[str, str]) -> str:
        """Return a filled headline for the given trigger, or empty string if none match.

        Args:
            trigger: Trigger string to match against template triggers.
            ctx: Placeholder values to substitute into the template.

        Returns:
            Filled headline string, or "" if no matching template exists.
        """
        candidates = [t for t in self._templates if t.trigger == trigger]
        if not candidates:
            return ""
        template = _rng.choice(candidates)
        return _fill(template.template, ctx)

    def _pick_flavor(self) -> str:
        """Return a flavor headline, cycling through the pool without repeating.

        Resets the used-flavor set when the entire pool has been consumed.

        Returns:
            A flavor headline string, or "" if no flavor templates exist.
        """
        flavor_pool = [t for t in self._templates if t.trigger == "flavor"]
        if not flavor_pool:
            return ""

        available = [t for t in flavor_pool if t.id not in self._used_flavor_ids]
        if not available:
            # Pool exhausted — reset and start over
            self._used_flavor_ids.clear()
            available = flavor_pool

        chosen = _rng.choice(available)
        self._used_flavor_ids.add(chosen.id)
        return _fill(chosen.template, {})
