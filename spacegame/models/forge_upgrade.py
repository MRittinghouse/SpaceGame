"""Forge upgrade system — refining-specific persistent progression."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional


def calculate_forge_tokens(
    recipe_time: float,
    num_inputs: int,
    mastery_level: int = 0,
    token_earn_bonus: float = 0.0,
) -> int:
    """Calculate forge tokens earned on job completion.

    Args:
        recipe_time: Duration of the recipe in seconds.
        num_inputs: Number of distinct input commodities.
        mastery_level: Player's mastery level for this recipe.
        token_earn_bonus: Fractional bonus to token earning (e.g. 0.30 = +30%).

    Returns:
        Total forge tokens earned.
    """
    base = max(1, math.floor(recipe_time / 5.0))
    complexity_bonus = max(0, num_inputs - 1)
    mastery_bonus = 1 if mastery_level >= 3 else 0
    total = math.floor((base + complexity_bonus + mastery_bonus) * (1.0 + token_earn_bonus))
    return total


@dataclass
class ForgeUpgrade:
    """Definition of a single forge upgrade.

    Loaded from data/economy/forge_upgrades.json.
    """

    id: str
    name: str
    description: str
    max_level: int
    costs: list[int]  # Cost per level (length must equal max_level)
    effect_type: str  # Key used to apply the effect
    effect_per_level: float  # Effect value per level

    def __post_init__(self) -> None:
        if len(self.costs) != self.max_level:
            raise ValueError(
                f"Upgrade '{self.id}': costs length ({len(self.costs)}) "
                f"must match max_level ({self.max_level})"
            )

    def get_cost(self, level: int) -> Optional[int]:
        """Get cost to purchase a specific level (1-indexed).

        Args:
            level: Level to purchase (1 = first level).

        Returns:
            Cost in forge tokens, or None if beyond max level.
        """
        if level < 1 or level > self.max_level:
            return None
        return self.costs[level - 1]

    def get_effect(self, current_level: int) -> float:
        """Get total effect at a given level.

        Args:
            current_level: Current upgrade level (0 = not purchased).

        Returns:
            Total effect value.
        """
        return self.effect_per_level * current_level


class ForgeUpgradeState:
    """Tracks which forge upgrades the player has purchased and at what level."""

    def __init__(self) -> None:
        self._levels: dict[str, int] = {}

    def get_level(self, upgrade_id: str) -> int:
        """Get current level of an upgrade."""
        return self._levels.get(upgrade_id, 0)

    def purchase(
        self,
        upgrade_id: str,
        upgrades: dict[str, ForgeUpgrade],
        forge_tokens_available: int,
    ) -> tuple[bool, str, int]:
        """Attempt to purchase the next level of an upgrade.

        Args:
            upgrade_id: ID of the upgrade to purchase.
            upgrades: All upgrade definitions.
            forge_tokens_available: Player's current forge token balance.

        Returns:
            Tuple of (success, message, cost_paid).
        """
        if upgrade_id not in upgrades:
            return (False, f"Unknown upgrade: {upgrade_id}", 0)

        definition = upgrades[upgrade_id]
        current = self.get_level(upgrade_id)
        next_level = current + 1

        cost = definition.get_cost(next_level)
        if cost is None:
            return (False, f"{definition.name} is already at max level", 0)

        if forge_tokens_available < cost:
            return (
                False,
                f"Need {cost} Forge Tokens, have {forge_tokens_available}",
                0,
            )

        self._levels[upgrade_id] = next_level
        return (True, f"{definition.name} upgraded to level {next_level}!", cost)

    def get_effect(self, upgrade_id: str, upgrades: dict[str, ForgeUpgrade]) -> float:
        """Get current effect value for an upgrade.

        Args:
            upgrade_id: ID of the upgrade.
            upgrades: All upgrade definitions.

        Returns:
            Effect value (0.0 if not purchased or unknown).
        """
        if upgrade_id not in upgrades:
            return 0.0
        return upgrades[upgrade_id].get_effect(self.get_level(upgrade_id))

    def get_total_invested(self, upgrades: dict[str, ForgeUpgrade]) -> int:
        """Get total forge tokens invested across all upgrades."""
        total = 0
        for uid, level in self._levels.items():
            if uid in upgrades:
                for lvl in range(1, level + 1):
                    cost = upgrades[uid].get_cost(lvl)
                    if cost is not None:
                        total += cost
        return total

    def reset(self) -> None:
        """Reset all upgrade levels to 0."""
        self._levels.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {"levels": dict(self._levels)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForgeUpgradeState:
        """Deserialize from dictionary."""
        state = cls()
        state._levels = dict(data.get("levels", {}))
        return state
