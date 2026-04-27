"""TW-1: optional time-sensitive reward tiers on missions.

A mission with a ``SoftDeadline`` pays full reward if completed within
``full_reward_day_count`` days of acceptance, a partial reward up to
``partial_reward_day_count`` days, and a floor reward past that. Nothing
LOCKS past the deadline — the roadmap constraint ("drift, not fail")
applies here too: late completion still pays, just less.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Floor multiplier applied past the partial deadline. 0.5 keeps the
# reward meaningful while signaling the urgency was missed.
DEFAULT_LATE_MULTIPLIER = 0.5


@dataclass
class SoftDeadline:
    """Time-sensitive reward tier for a mission.

    Attributes:
        full_reward_day_count: Days from accept at which full reward
            (1.0x multiplier) still applies.
        partial_reward_day_count: Days from accept at which partial
            reward still applies (between full and partial => linear
            or stepped, see ``resolve_multiplier``).
        partial_reward_multiplier: Multiplier applied in the
            full..partial window (e.g., 0.75).
        late_multiplier: Multiplier applied past the partial deadline.
            Never zero — nothing locks.
    """

    full_reward_day_count: int
    partial_reward_day_count: int
    partial_reward_multiplier: float = 0.75
    late_multiplier: float = DEFAULT_LATE_MULTIPLIER

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SoftDeadline":
        return cls(
            full_reward_day_count=int(data["full_reward_day_count"]),
            partial_reward_day_count=int(data["partial_reward_day_count"]),
            partial_reward_multiplier=float(data.get("partial_reward_multiplier", 0.75)),
            late_multiplier=float(data.get("late_multiplier", DEFAULT_LATE_MULTIPLIER)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_reward_day_count": self.full_reward_day_count,
            "partial_reward_day_count": self.partial_reward_day_count,
            "partial_reward_multiplier": self.partial_reward_multiplier,
            "late_multiplier": self.late_multiplier,
        }

    def resolve_multiplier(self, days_elapsed: int) -> float:
        """Resolve the reward multiplier given days since acceptance.

        Tiers (stepped, not linear — clearer to the player):
        - ``days_elapsed <= full``: 1.0 (full reward)
        - ``full < days_elapsed <= partial``: ``partial_reward_multiplier``
        - ``days_elapsed > partial``: ``late_multiplier`` (never 0)
        """
        if days_elapsed <= self.full_reward_day_count:
            return 1.0
        if days_elapsed <= self.partial_reward_day_count:
            return self.partial_reward_multiplier
        return self.late_multiplier

    def resolve_tier(self, days_elapsed: int) -> str:
        """Return the tier name for the given elapsed days.

        Mirrors ``resolve_multiplier``'s thresholds but returns a
        narrative-friendly string used for dialogue lookup:
        - ``"timely"``: within the full-reward window
        - ``"late"``: past full, within partial
        - ``"very_late"``: past partial
        """
        if days_elapsed <= self.full_reward_day_count:
            return "timely"
        if days_elapsed <= self.partial_reward_day_count:
            return "late"
        return "very_late"
