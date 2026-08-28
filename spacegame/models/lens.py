"""Lens data model for Act II ambition tracking.

A lens is a *reading* of the shared world, not a questline. Each lens record
answers the same structured questions so that one authored location can be
filtered through sixteen different motivational frames without sixteen separate
questlines. The registry is loaded by DataLoader and keyed by lens_id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_REQUIRED_FIELDS = (
    "lens_id",
    "name",
    "core_fantasy",
    "question",
    "sees",
    "wants",
    "trades",
    "investment_from",
    "minigame_shape",
    "voice",
    "tier_unlocks",
)


@dataclass(frozen=True)
class Lens:
    """A motivational reading of the shared Aurelia world.

    Attributes:
        lens_id: Stable snake_case identifier (e.g. ``"vengeance"``).
        name: Player-facing display name.
        core_fantasy: One-line statement of what this ambition gives the player.
        question: What the arc asks the player to answer through play.
        sees: What someone with this lens notices in a place, wreck, rumour, or person.
        wants: What a character embodying this lens is trying to obtain.
        trades: What they will give up to get it.
        investment_from: Action tags that raise this lens's investment meter.
        minigame_shape: The mechanical form that reinforces the ambition's feel.
        voice: How a character embodying this lens speaks.
        tier_unlocks: What deepens when a dilemma resolves in this lens's favour.
    """

    lens_id: str
    name: str
    core_fantasy: str
    question: str
    sees: str
    wants: str
    trades: str
    investment_from: tuple[str, ...]
    minigame_shape: str
    voice: str
    tier_unlocks: tuple[str, ...]

    def to_dict(self) -> dict:
        """Serialize this lens to a JSON-compatible dict.

        Returns:
            Dict with all 11 fields; tuple fields are serialized as lists.
        """
        return {
            "lens_id": self.lens_id,
            "name": self.name,
            "core_fantasy": self.core_fantasy,
            "question": self.question,
            "sees": self.sees,
            "wants": self.wants,
            "trades": self.trades,
            "investment_from": list(self.investment_from),
            "minigame_shape": self.minigame_shape,
            "voice": self.voice,
            "tier_unlocks": list(self.tier_unlocks),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Lens":
        """Construct a Lens from a dict, validating all required fields.

        Args:
            data: Raw dict, typically from JSON. ``investment_from`` and
                ``tier_unlocks`` may be lists (JSON round-trip) or tuples.

        Returns:
            Validated, frozen Lens instance.

        Raises:
            ValueError: If any required field is missing, ``lens_id`` is not
                snake_case, or a collection field has an unexpected type.
        """
        _validate_lens_dict(data)
        return cls(
            lens_id=data["lens_id"],
            name=data["name"],
            core_fantasy=data["core_fantasy"],
            question=data["question"],
            sees=data["sees"],
            wants=data["wants"],
            trades=data["trades"],
            investment_from=tuple(data["investment_from"]),
            minigame_shape=data["minigame_shape"],
            voice=data["voice"],
            tier_unlocks=tuple(data["tier_unlocks"]),
        )


def _validate_lens_dict(data: dict) -> None:
    """Raise ValueError if the lens dict violates the schema.

    Args:
        data: Raw dict to validate.

    Raises:
        ValueError: On any schema violation.
    """
    lens_id = data.get("lens_id", "<unknown>")

    for field in _REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            raise ValueError(f"Lens '{lens_id}' is missing required field '{field}'.")

    if not _SNAKE_CASE_RE.match(lens_id):
        raise ValueError(
            f"lens_id '{lens_id}' is not valid snake_case (must match ^[a-z][a-z0-9_]*$)."
        )

    for collection_field in ("investment_from", "tier_unlocks"):
        value = data[collection_field]
        if not isinstance(value, (list, tuple)):
            raise ValueError(
                f"Lens '{lens_id}' field '{collection_field}' must be a list or "
                f"tuple, got {type(value).__name__!r}."
            )
