"""State + transition coverage tracker for the play-harness crawler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from spacegame.config import GameState


@dataclass
class CoverageTracker:
    """Track which ``GameState`` values were reached and which transitions fired.

    Attributes:
        states_reached: Map of state name → bool for every ``GameState``.
            All 41 members are always present; True once reached.
        transitions: Ordered list of ``(from_name, to_name)`` tuples.
    """

    states_reached: dict[str, bool] = field(default_factory=dict)
    transitions: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize the states_reached dict with all 41 GameState members."""
        if not self.states_reached:
            self.states_reached = {state.name: False for state in GameState}

    def record_visit(self, state: GameState | str) -> None:
        """Mark a state as visited.

        Args:
            state: A ``GameState`` value or its name.
        """
        name = state.name if isinstance(state, GameState) else str(state)
        if name in self.states_reached:
            self.states_reached[name] = True

    def record_transition(
        self, from_state: Optional[GameState | str], to_state: GameState | str
    ) -> None:
        """Record a state transition (from → to).

        Args:
            from_state: Previous state, or None on initial entry.
            to_state: New state entered.
        """
        from_name = ""
        if from_state is not None:
            from_name = from_state.name if isinstance(from_state, GameState) else str(from_state)
        to_name = to_state.name if isinstance(to_state, GameState) else str(to_state)
        self.transitions.append((from_name, to_name))
        self.record_visit(to_state)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict.

        Returns:
            Dict of ``{"states_reached": ..., "transitions": ...}``.
        """
        return {
            "states_reached": dict(self.states_reached),
            "transitions": [list(t) for t in self.transitions],
        }

    def summary_text(self) -> str:
        """Human-readable one-block summary.

        Returns:
            Multi-line string listing reached/unreached states and count.
        """
        total = len(self.states_reached)
        reached = sum(1 for v in self.states_reached.values() if v)
        lines = [
            f"State coverage: {reached}/{total} states reached",
            f"Transitions fired: {len(self.transitions)}",
            "",
            "Reached states:",
        ]
        for name, was_reached in sorted(self.states_reached.items()):
            marker = "  [X]" if was_reached else "  [ ]"
            lines.append(f"{marker} {name}")
        return "\n".join(lines)
