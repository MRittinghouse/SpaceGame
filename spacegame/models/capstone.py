"""Capstone data model and hook-contract predicate for Act II.

A capstone is punctuation, not a terminus. Firing a capstone MUST NOT end the
session; the engine (A2-20) transitions to GameState.CAPSTONE to render the
moment, then pops back to the prior state so play continues. The player earns a
capstone when cumulative investment in a single lens crosses a threshold, and the
dilemma engine has not closed that lens. Each lens supports exactly one capstone.

Hook contract (enforced by A2-20):
- On every action that raises lens investment, A2-20 calls ``should_fire()`` for
  the matching capstone (if one exists in the registry).
- When ``should_fire()`` returns True, the engine transitions to
  ``GameState.CAPSTONE``, renders the capstone moment, then pops back to the
  caller state. It also adds ``capstone_id`` to ``player.capstones_reached``.
- ``cutscene_ref`` being None means A2-20 renders a generated template narration.
  When non-null it points at a cutscene id for future authored cutscenes.
- This module imports nothing from ``spacegame.engine.*`` or ``spacegame.views.*``.
  That zero coupling is the structural enforcement of the "must not end the session"
  invariant: the Capstone model cannot trigger state transitions by itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_REQUIRED_FIELDS = ("capstone_id", "lens_id", "capstone_threshold")


@dataclass(frozen=True)
class Capstone:
    """A punctuation moment that fires when lens investment crosses a threshold.

    Attributes:
        capstone_id: Stable snake_case identifier.
        lens_id: The single lens this capstone punctuates (snake_case).
        capstone_threshold: Investment value at or above which the capstone
            becomes eligible to fire. Must be non-negative.
        cutscene_ref: Optional reference to a cutscene or narration asset.
            None means A2-20 renders a template narration. Non-null points at
            a future authored cutscene id.
    """

    capstone_id: str
    lens_id: str
    capstone_threshold: int
    cutscene_ref: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize this capstone to a JSON-compatible dict.

        Returns:
            Dict with all four fields. ``cutscene_ref`` is emitted explicitly
            as ``None`` (JSON null) when absent, preserving round-trip fidelity.
        """
        return {
            "capstone_id": self.capstone_id,
            "lens_id": self.lens_id,
            "capstone_threshold": self.capstone_threshold,
            "cutscene_ref": self.cutscene_ref,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Capstone":
        """Construct a Capstone from a dict, validating all required fields.

        Args:
            data: Raw dict, typically from JSON.

        Returns:
            Validated, frozen Capstone instance.

        Raises:
            ValueError: If any required field is missing, ids are not
                snake_case, threshold is negative, or cutscene_ref has a
                bad type.
        """
        _validate_capstone_dict(data)
        return cls(
            capstone_id=data["capstone_id"],
            lens_id=data["lens_id"],
            capstone_threshold=data["capstone_threshold"],
            cutscene_ref=data.get("cutscene_ref", None),
        )


def _validate_capstone_dict(data: dict) -> None:
    """Raise ValueError if the capstone dict violates the schema.

    Args:
        data: Raw dict to validate.

    Raises:
        ValueError: On any schema violation.
    """
    capstone_id = data.get("capstone_id", "<unknown>")

    for field in _REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            raise ValueError(f"Capstone '{capstone_id}' is missing required field '{field}'.")

    if not isinstance(capstone_id, str) or not _SNAKE_CASE_RE.match(capstone_id):
        raise ValueError(
            f"capstone_id {capstone_id!r} is not valid snake_case (must match ^[a-z][a-z0-9_]*$)."
        )

    lens_id = data["lens_id"]
    if not isinstance(lens_id, str):
        raise ValueError(
            f"Capstone '{capstone_id}' field 'lens_id' must be a string, "
            f"got {type(lens_id).__name__!r}."
        )
    if not _SNAKE_CASE_RE.match(lens_id):
        raise ValueError(
            f"Capstone '{capstone_id}' lens_id {lens_id!r} is not valid snake_case "
            f"(must match ^[a-z][a-z0-9_]*$)."
        )

    threshold = data["capstone_threshold"]
    if not isinstance(threshold, int) or isinstance(threshold, bool):
        raise ValueError(
            f"Capstone '{capstone_id}' field 'capstone_threshold' must be an int, "
            f"got {type(threshold).__name__!r}."
        )
    if threshold < 0:
        raise ValueError(
            f"Capstone '{capstone_id}' capstone_threshold must be non-negative, got {threshold}."
        )

    cutscene_ref = data.get("cutscene_ref", None)
    if cutscene_ref is not None and not isinstance(cutscene_ref, str):
        raise ValueError(
            f"Capstone '{capstone_id}' field 'cutscene_ref' must be a string or null, "
            f"got {type(cutscene_ref).__name__!r}."
        )


def should_fire(
    capstone: Capstone,
    current_investment: int,
    closed_lenses: set[str],
    capstones_reached: set[str],
) -> bool:
    """Return True iff the capstone is eligible to fire right now.

    A capstone fires when:
    - ``current_investment >= capstone.capstone_threshold``
    - ``capstone.lens_id`` is NOT in ``closed_lenses``
    - ``capstone.capstone_id`` is NOT in ``capstones_reached``

    This is a pure predicate with no side effects. A2-20 calls it on every
    action that raises lens investment and drives the resulting state transition.

    Args:
        capstone: The capstone record from the registry.
        current_investment: The player's current investment in ``capstone.lens_id``.
        closed_lenses: Set of lens_ids the dilemma engine has closed.
        capstones_reached: Set of capstone_ids the player has already triggered.

    Returns:
        True if all three conditions are satisfied, False otherwise.
    """
    return (
        current_investment >= capstone.capstone_threshold
        and capstone.lens_id not in closed_lenses
        and capstone.capstone_id not in capstones_reached
    )
