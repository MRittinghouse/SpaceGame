"""Recipe mastery tracking -- repeated crafting improves outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

MASTERY_THRESHOLDS: list[int] = [3, 8, 15]  # crafts needed for levels 1, 2, 3


@dataclass
class RecipeMasteryEntry:
    """Tracks mastery progress for a single recipe."""

    recipe_id: str
    times_crafted: int = 0
    mastery_level: int = 0  # 0=none, 1=familiar, 2=practiced, 3=mastered


class RecipeMasteryTracker:
    """Tracks mastery across all recipes the player has crafted."""

    def __init__(self) -> None:
        self._entries: dict[str, RecipeMasteryEntry] = {}

    def get_mastery(self, recipe_id: str) -> RecipeMasteryEntry:
        """Get or create mastery entry for a recipe."""
        if recipe_id not in self._entries:
            self._entries[recipe_id] = RecipeMasteryEntry(recipe_id=recipe_id)
        return self._entries[recipe_id]

    def record_craft(self, recipe_id: str) -> Optional[int]:
        """Record a craft. Returns new mastery level if threshold crossed, else None."""
        entry = self.get_mastery(recipe_id)
        entry.times_crafted += 1
        for level, threshold in enumerate(MASTERY_THRESHOLDS, start=1):
            if entry.times_crafted == threshold and entry.mastery_level < level:
                entry.mastery_level = level
                return level
        return None

    def get_speed_bonus(self, recipe_id: str) -> float:
        """Level 1+: -10% processing time (return 0.10)."""
        entry = self.get_mastery(recipe_id)
        if entry.mastery_level >= 1:
            return 0.10
        return 0.0

    def get_yield_bonus(self, recipe_id: str) -> int:
        """Level 2+: +1 bonus output unit."""
        entry = self.get_mastery(recipe_id)
        if entry.mastery_level >= 2:
            return 1
        return 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize all mastery entries."""
        return {
            "entries": {
                recipe_id: {
                    "times_crafted": entry.times_crafted,
                    "mastery_level": entry.mastery_level,
                }
                for recipe_id, entry in self._entries.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeMasteryTracker:
        """Deserialize from saved data."""
        tracker = cls()
        for recipe_id, entry_data in data.get("entries", {}).items():
            tracker._entries[recipe_id] = RecipeMasteryEntry(
                recipe_id=recipe_id,
                times_crafted=entry_data["times_crafted"],
                mastery_level=entry_data["mastery_level"],
            )
        return tracker
