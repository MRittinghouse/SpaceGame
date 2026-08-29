"""Per-lens investment tracking for Act II ambition arcs (A2-4).

The store answers one question for downstream systems: "how far has the
player invested in this reading of the world?" It intentionally does not
answer "should the world react?" — that is the sibling sprint A2-4A's job
(oblique NPC-address / offered-work reactor) and A2-8's job (dilemma-engine
threshold telegraph). Keeping the reactor and the numeric substrate apart
is what lets Spec F's telegraph invariant hold: raw investment numbers are
never rendered.

Design decisions (locked in A2-4 planning; see ROADMAP.md sprint A2-4
Risks / open questions for full rationale):

- **Uncapped integers**: Spec F speaks of a "threshold" but names no unit or
  ceiling. A2-8 owns concrete thresholds; A2-4 stores raw `int`, floored
  at 0. Adding an arbitrary cap here would force A2-8 to work around it.
- **Monotonic rise**: ``add_investment`` rejects negative amounts with
  ``ValueError``. The one modelled state transition that reduces investment
  is closure (a full clear on dilemma resolution) — A2-10's scope, not a
  per-action decrement.
- **Registry as parameter**: ``record_action`` accepts the ``lenses`` dict
  as a parameter rather than importing ``data_loader``. This keeps the
  model testable with hand-built lens fixtures and preserves the layer
  discipline (models never reach into the data loader).
- **Opaque ``source`` parameter**: retained on ``add_investment`` so future
  telemetry consumers don't need a signature-breaking change; A2-4 does not
  wire a sink.

Structural invariant (enforced by
``tests/test_compliance/test_lens_investment_never_rendered.py``): no file
under ``spacegame/views/`` or ``spacegame/engine/`` may import
``LensInvestment`` or read ``player.lens_investment``. Consumers live in
the model layer and expose behavioural readouts, never numeric ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from spacegame.utils.logger import logger

if TYPE_CHECKING:
    from spacegame.models.lens import Lens


@dataclass
class LensInvestment:
    """Per-lens accrual store keyed by ``lens_id``.

    The underscore-prefixed ``_values`` field signals that callers must use
    the methods, never the raw dict — the compliance test in AC4 keys off
    this rule to make "no raw number in UI" a structural invariant.
    """

    _values: dict[str, int] = field(default_factory=dict)

    def add_investment(self, lens_id: str, amount: int, source: str) -> None:
        """Add ``amount`` to the investment counter for ``lens_id``.

        Args:
            lens_id: The lens whose counter to raise. Any string is
                accepted; validation against the registry is A2-1's job.
            amount: The integer to add. Must be non-negative — investment
                monotonically rises then closes at a resolved dilemma
                (Spec F "Permanent closure"), it never leaks backward.
            source: Free-form action or system tag. Ignored in A2-4; the
                parameter exists so a future telemetry consumer sprint
                does not require a signature-breaking change.

        Raises:
            ValueError: If ``amount`` is negative.
        """
        if amount < 0:
            raise ValueError(
                f"LensInvestment.add_investment received negative amount "
                f"{amount} for lens '{lens_id}' (source={source!r}); "
                f"investment monotonically rises."
            )
        # ``source`` is intentionally unused in A2-4; see module docstring.
        del source
        self._values[lens_id] = self._values.get(lens_id, 0) + amount

    def get_investment(self, lens_id: str) -> int:
        """Return the current investment counter for ``lens_id``, or 0."""
        return self._values.get(lens_id, 0)

    def is_at_or_above(self, lens_id: str, threshold: int) -> bool:
        """True when the lens's current value >= ``threshold``.

        A never-touched lens reads as 0, so any positive threshold returns
        False, and a threshold of 0 returns True.
        """
        return self._values.get(lens_id, 0) >= threshold

    def record_action(
        self,
        action_tag: str,
        amount: int,
        lenses: "dict[str, Lens]",
    ) -> list[str]:
        """Walk the passed lens registry and increment every matching lens.

        A lens matches when ``action_tag`` appears in its
        ``investment_from`` tuple (exact match, no substring matching).
        Passing the registry in explicitly keeps this model layer clean of
        any dependency on ``data_loader``.

        Args:
            action_tag: The qualified action identifier (e.g.
                ``"combat_victory_named_target"``). Must appear verbatim
                in a lens's ``investment_from`` to match.
            amount: Non-negative integer to add to each matching lens.
            lenses: Registry snapshot keyed by ``lens_id``. Tests pass
                small hand-built fixtures; production callers pass
                ``data_loader.get_data_loader().lenses``.

        Returns:
            The list of ``lens_id``s that were incremented, in registry
            iteration order (deterministic given Python 3.7+'s dict
            ordering guarantee).

        Raises:
            ValueError: If ``amount`` is negative (propagated from
                ``add_investment``).
        """
        incremented: list[str] = []
        for lens_id, lens in lenses.items():
            if action_tag in lens.investment_from:
                self.add_investment(lens_id, amount, source=action_tag)
                incremented.append(lens_id)
        return incremented

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe wrapped dict.

        The wrapper is deliberate: it leaves room for a future
        ``metadata`` sibling (schema version, last-updated day) without
        forcing a save migration.
        """
        return {"values": dict(self._values)}

    @classmethod
    def from_dict(cls, data: Any) -> "LensInvestment":
        """Restore a LensInvestment from save data.

        Accepts either the wrapped form ``{"values": {...}}`` (the shape
        ``to_dict`` emits) or a bare ``dict[str, int]`` (defensive against
        a hypothetical malformed save from a partial rollout). Non-int
        values and negative values are dropped rather than raised so
        legacy or corrupted save data does not crash the load path — see
        CLAUDE.md Save Migration rules.

        Args:
            data: Raw payload from a save file.

        Returns:
            A new LensInvestment. Empty when ``data`` is missing, malformed,
            or a non-dict.
        """
        if not isinstance(data, dict):
            return cls()

        if "values" in data and isinstance(data["values"], dict):
            raw = data["values"]
        else:
            raw = data

        cleaned: dict[str, int] = {}
        for lens_id, value in raw.items():
            if not isinstance(lens_id, str):
                logger.warning(f"LensInvestment.from_dict: dropping non-string key {lens_id!r}")
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                logger.warning(
                    f"LensInvestment.from_dict: dropping non-int value for "
                    f"lens '{lens_id}': {value!r}"
                )
                continue
            if value < 0:
                logger.warning(
                    f"LensInvestment.from_dict: dropping negative value for "
                    f"lens '{lens_id}': {value}"
                )
                continue
            cleaned[lens_id] = value
        return cls(_values=cleaned)
