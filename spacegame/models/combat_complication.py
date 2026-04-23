"""Combat complication model — mid-fight events that change encounter shape.

CE-1 ships the model + save/load. CE-3 implements the actual trigger
logic (fire at turn N, spawn reinforcements, offer choice prompts, etc).

A complication attaches to a combat encounter and fires under a
well-defined trigger condition. When it fires, it has an effect
(spawn-reinforcement, environmental-modifier, narration-only, etc.) and
optional narration. Effects resolve through the existing combat engine
(CE-3 wires the specific effect handlers).

This file is pure model. Behavior lives in the combat engine hook CE-3
adds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CombatComplication:
    """A scripted mid-fight event.

    Attributes:
        id: Stable identifier (snake_case).
        name: Short display name.
        description: Player-facing summary (shown in UI / journal).
        trigger_type: One of ``"turn_counter"`` | ``"hp_threshold"``
            | ``"player_action"`` | ``"random"``. CE-3 maps to handlers.
        trigger_params: Shape depends on ``trigger_type``. Examples:
            ``{"turn": 3}`` for ``turn_counter``;
            ``{"hp_pct": 0.3}`` for ``hp_threshold``.
        effect_type: One of ``"spawn_reinforcement"`` | ``"environmental"``
            | ``"choice_prompt"`` | ``"iff_change"``. CE-3 maps to handlers.
        effect_params: Shape depends on ``effect_type``.
        narration: Line shown when the complication fires.
    """

    id: str
    name: str
    description: str
    trigger_type: str
    effect_type: str
    trigger_params: dict[str, Any] = field(default_factory=dict)
    effect_params: dict[str, Any] = field(default_factory=dict)
    narration: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CombatComplication":
        """Parse a complication from its JSON representation."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            trigger_type=data["trigger_type"],
            trigger_params=dict(data.get("trigger_params", {})),
            effect_type=data["effect_type"],
            effect_params=dict(data.get("effect_params", {})),
            narration=data.get("narration", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_params": dict(self.trigger_params),
            "effect_type": self.effect_type,
            "effect_params": dict(self.effect_params),
            "narration": self.narration,
        }


# Valid trigger / effect types — enforced by test_combat_complication_integrity
# to catch typos at data-load time. CE-3 expands these as it wires handlers.
VALID_TRIGGER_TYPES: frozenset[str] = frozenset(
    {"turn_counter", "hp_threshold", "player_action", "random"}
)

VALID_EFFECT_TYPES: frozenset[str] = frozenset(
    {
        "spawn_reinforcement",
        "environmental",
        "choice_prompt",
        "iff_change",
        # CE-3: narration-only complications that set a flag on CombatState
        # without altering combat mechanics. Useful for dramatic beats
        # (morale_shift, third_party_hail) that future UI can render.
        "narration",
    }
)
