"""Wreck upgrade system — salvage-specific persistent progression."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional


def calculate_intel_earned(
    deck: int,
    extraction_ratio: float = 0.0,
    prestige_level: int = 0,
) -> int:
    """Calculate salvage intel earned on deck advance.

    Args:
        deck: The deck number just cleared.
        extraction_ratio: Fraction of items extracted on this deck (0.0-1.0).
        prestige_level: Player's current salvage prestige level.

    Returns:
        Total salvage intel earned.
    """
    base = math.floor(deck * 1.2)
    bonus = math.floor(deck * 0.8) if extraction_ratio >= 0.80 else 0
    subtotal = base + bonus
    multiplier = 1.0 + (0.1 * prestige_level)
    return int(subtotal * multiplier)


@dataclass
class WreckUpgrade:
    """Definition of a single wreck salvage upgrade.

    Loaded from data/economy/salvage_upgrades.json.
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
            Cost in salvage intel, or None if beyond max level.
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


class WreckUpgradeState:
    """Tracks which wreck upgrades the player has purchased and at what level."""

    def __init__(self) -> None:
        self._levels: dict[str, int] = {}

    def get_level(self, upgrade_id: str) -> int:
        """Get current level of an upgrade."""
        return self._levels.get(upgrade_id, 0)

    def purchase(
        self,
        upgrade_id: str,
        upgrades: dict[str, WreckUpgrade],
        intel_available: int,
    ) -> tuple[bool, str, int]:
        """Attempt to purchase the next level of an upgrade.

        Args:
            upgrade_id: ID of the upgrade to purchase.
            upgrades: All upgrade definitions.
            intel_available: Player's current salvage intel balance.

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

        if intel_available < cost:
            return (
                False,
                f"Need {cost} Salvage Intel, have {intel_available}",
                0,
            )

        self._levels[upgrade_id] = next_level
        return (True, f"{definition.name} upgraded to level {next_level}!", cost)

    def get_effect(self, upgrade_id: str, upgrades: dict[str, WreckUpgrade]) -> float:
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

    def get_total_invested(self, upgrades: dict[str, WreckUpgrade]) -> int:
        """Get total salvage intel invested across all upgrades."""
        total = 0
        for uid, level in self._levels.items():
            if uid in upgrades:
                for lvl in range(1, level + 1):
                    cost = upgrades[uid].get_cost(lvl)
                    if cost is not None:
                        total += cost
        return total

    def reset(self) -> None:
        """Reset all upgrade levels to 0 (used by prestige)."""
        self._levels.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {"levels": dict(self._levels)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WreckUpgradeState:
        """Deserialize from dictionary."""
        state = cls()
        state._levels = dict(data.get("levels", {}))
        return state
