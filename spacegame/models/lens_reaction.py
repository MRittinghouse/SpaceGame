"""LensReaction dataclass -- a pool of NPC lines keyed by lens, context, and threshold.

A LensReaction record pairs one (lens_id, context, threshold) triple with an
authored tuple of interchangeable NPC lines. The companion ``LensReactor`` class
loads these records and picks one line per render call, seeded deterministically.

Separated from ``LensReactor`` for testability -- the data shape is independently
verifiable without constructing a reactor or needing a Player.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LensReaction:
    """One authored line pool for a given (lens_id, context, threshold) triple.

    Frozen to signal immutability -- the reactor reads these records, never
    mutates them. ``lines`` is a tuple (not a list) for the same reason.
    """

    lens_id: str
    context: str
    threshold: int
    lines: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LensReaction":
        """Build a LensReaction from a raw JSON record.

        Args:
            data: Dict with required keys ``lens_id``, ``context``,
                ``threshold``, and ``lines``.

        Returns:
            A populated LensReaction.

        Raises:
            ValueError: If any required field is missing, or ``lines`` is empty.
        """
        for key in ("lens_id", "context", "threshold", "lines"):
            if key not in data:
                raise ValueError(
                    f"LensReaction.from_dict: missing required field '{key}' in record {data!r}"
                )
        lines_raw = data["lines"]
        if not lines_raw:
            raise ValueError(
                f"LensReaction.from_dict: 'lines' must be non-empty "
                f"(lens_id={data['lens_id']!r}, context={data['context']!r})"
            )
        return cls(
            lens_id=str(data["lens_id"]),
            context=str(data["context"]),
            threshold=int(data["threshold"]),
            lines=tuple(str(s) for s in lines_raw),
        )
