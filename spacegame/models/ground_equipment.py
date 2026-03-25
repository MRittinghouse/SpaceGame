"""Ground equipment and loot table models.

Equipment is ground-mission-exclusive gear that modifies exploration
and combat stats. Loot tables define container drops by difficulty.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EquipmentSlot(Enum):
    """Equipment slot categories."""

    UTILITY = "utility"
    DEFENSE = "defense"


# ===========================================================================
# Equipment effect keys (used by GroundCrewBonuses)
# ===========================================================================

# Exploration effects
EFFECT_VISION_BONUS = "vision_bonus"
EFFECT_NOISE_REDUCTION = "noise_reduction"
EFFECT_SILENT_DOORS = "silent_doors"

# Combat effects
EFFECT_HP_BONUS = "hp_bonus"
EFFECT_ABSORB_FIRST_HIT = "absorb_first_hit"

# Special effects
EFFECT_LOCKPICK = "lockpick"
EFFECT_EMP_DISABLE = "emp_disable_turns"


@dataclass
class GroundEquipment:
    """Equipment usable only during ground missions.

    Each piece occupies a slot (utility or defense) and provides
    one or more effects that are applied through GroundCrewBonuses.
    """

    id: str
    name: str
    description: str
    slot: EquipmentSlot
    effects: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "slot": self.slot.value,
            "effects": dict(self.effects),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundEquipment:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with equipment fields.

        Returns:
            GroundEquipment instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            slot=EquipmentSlot(data["slot"]),
            effects=data.get("effects", {}),
        )


# ===========================================================================
# GroundLootTable
# ===========================================================================


@dataclass
class GroundLootTable:
    """Defines possible loot for a ground mission container.

    Loot is rolled per-container. COM attribute bonus improves
    credit yields. Equipment drops are probability-gated.
    """

    credit_range: tuple[int, int]
    equipment_chance: float
    equipment_pool: list[str]
    commodity_drops: list[tuple[str, int]] = field(default_factory=list)

    def roll_container_loot(self, com_bonus: float, rng: random.Random) -> dict[str, Any]:
        """Generate loot for a single container.

        Args:
            com_bonus: COM attribute bonus as a fraction (e.g., 0.5 = +50%).
            rng: Seeded random instance for determinism.

        Returns:
            Dict with 'credits' (int), optional 'equipment' (str),
            optional 'commodities' (dict[str, int]).
        """
        result: dict[str, Any] = {}

        # Credits — roll within range, apply COM bonus
        base_credits = rng.randint(self.credit_range[0], self.credit_range[1])
        result["credits"] = int(base_credits * (1.0 + com_bonus))

        # Equipment drop
        if self.equipment_pool and rng.random() < self.equipment_chance:
            result["equipment"] = rng.choice(self.equipment_pool)

        # Commodity drops — each commodity rolls 1 to max_quantity
        if self.commodity_drops:
            commodities: dict[str, int] = {}
            for commodity_id, max_qty in self.commodity_drops:
                qty = rng.randint(1, max(1, max_qty))
                commodities[commodity_id] = qty
            if commodities:
                result["commodities"] = commodities

        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "credit_range": list(self.credit_range),
            "equipment_chance": self.equipment_chance,
            "equipment_pool": list(self.equipment_pool),
            "commodity_drops": [[cid, qty] for cid, qty in self.commodity_drops],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundLootTable:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with loot table fields.

        Returns:
            GroundLootTable instance.
        """
        cr = data.get("credit_range", [0, 0])
        return cls(
            credit_range=(cr[0], cr[1]),
            equipment_chance=data.get("equipment_chance", 0.0),
            equipment_pool=data.get("equipment_pool", []),
            commodity_drops=[(item[0], item[1]) for item in data.get("commodity_drops", [])],
        )
