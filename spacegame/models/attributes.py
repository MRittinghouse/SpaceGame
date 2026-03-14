"""Character attribute system.

Defines the 5 sci-fi themed attributes (Commerce, Acuity, Resolve, Ingenuity,
Synergy) and the AttributeSheet that tracks values, allocation, milestones,
and passive bonuses for both protagonist and crew.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================================
# Constants
# ============================================================================


class AttributeId(Enum):
    """The five character attributes."""

    COM = "com"  # Commerce — governs Trading tree
    ACU = "acu"  # Acuity — governs Gathering tree
    RES = "res"  # Resolve — governs Mining tree
    ING = "ing"  # Ingenuity — governs Leadership tree
    SYN = "syn"  # Synergy — governs Social tree


ATTRIBUTE_DEFINITIONS: dict[str, dict[str, str]] = {
    "com": {
        "name": "Commerce",
        "description": "Business acumen and market instincts. Governs Trading skills.",
    },
    "acu": {
        "name": "Acuity",
        "description": "Perception and analytical precision. Governs Gathering skills.",
    },
    "res": {
        "name": "Resolve",
        "description": "Willpower and physical determination. Governs Mining skills.",
    },
    "ing": {
        "name": "Ingenuity",
        "description": "Technical creativity and problem-solving. Governs Leadership skills.",
    },
    "syn": {
        "name": "Synergy",
        "description": "Social awareness and interpersonal influence. Governs Social skills.",
    },
}

ATTRIBUTE_MAX: int = 10
ATTRIBUTE_MIN: int = 1

# Bonus rates per modifier point (value - 1)
_BONUS_RATES: dict[str, tuple[str, float]] = {
    # bonus_type -> (attribute_id, rate_per_modifier_point)
    "buy_price_attr_reduction": ("com", 0.005),  # -0.5% per point above 1
    "sell_price_attr_bonus": ("com", 0.005),  # +0.5% per point above 1
    "scan_efficiency_attr": ("acu", 0.05),  # +5% per point above 1
    "mining_power_attr": ("res", 0.05),  # +5% per point above 1
    "crew_efficiency_attr": ("ing", 0.05),  # +5% per point above 1
}

# Gameplay milestones that award +1 attribute point each
MILESTONE_DEFINITIONS: dict[str, str] = {
    "first_trade": "Complete your first trade",
    "explorer_5": "Visit 5 star systems",
    "miner_50": "Mine 50 ore",
    "first_mission": "Complete your first mission",
}


# ============================================================================
# AttributeSheet
# ============================================================================


@dataclass
class AttributeSheet:
    """Tracks attribute values, unspent points, and awarded milestones.

    Used by both the protagonist (via Player.attribute_state) and crew members
    (via crew state dicts).
    """

    values: dict[str, int] = field(default_factory=dict)
    unspent_points: int = 0
    _awarded_milestones: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Ensure all attributes have at least the minimum value."""
        for attr in AttributeId:
            if attr.value not in self.values:
                self.values[attr.value] = ATTRIBUTE_MIN

    def get_value(self, attr_id: str) -> int:
        """Get the current value of an attribute.

        Args:
            attr_id: Attribute ID (e.g., "com").

        Returns:
            Attribute value, or 0 if unknown.
        """
        return self.values.get(attr_id, 0)

    def get_all_values(self) -> dict[str, int]:
        """Get a copy of all attribute values."""
        return dict(self.values)

    def get_modifier(self, attr_id: str) -> int:
        """Get the modifier for an attribute (value - 1).

        Args:
            attr_id: Attribute ID.

        Returns:
            Modifier value (0 at base, increases with investment).
        """
        return max(0, self.get_value(attr_id) - 1)

    def get_synergy_social_bonus(self) -> int:
        """Get the social effective level bonus from Synergy.

        Returns:
            Bonus to social skill effective level (SYN value // 2).
        """
        return self.get_value("syn") // 2

    def allocate_point(self, attr_id: str) -> tuple[bool, str]:
        """Allocate one unspent point to an attribute.

        Args:
            attr_id: Attribute to increase.

        Returns:
            Tuple of (success, message).
        """
        if attr_id not in self.values:
            return (False, f"Unknown attribute: {attr_id}")
        if self.unspent_points <= 0:
            return (False, "No attribute points available")
        if self.values[attr_id] >= ATTRIBUTE_MAX:
            name = ATTRIBUTE_DEFINITIONS.get(attr_id, {}).get("name", attr_id)
            return (False, f"{name} is already at maximum")

        self.values[attr_id] += 1
        self.unspent_points -= 1
        name = ATTRIBUTE_DEFINITIONS.get(attr_id, {}).get("name", attr_id)
        return (True, f"{name} increased to {self.values[attr_id]}")

    def deallocate_point(self, attr_id: str) -> tuple[bool, str]:
        """Remove one point from an attribute, returning it to unspent.

        Args:
            attr_id: Attribute to decrease.

        Returns:
            Tuple of (success, message).
        """
        if attr_id not in self.values:
            return (False, f"Unknown attribute: {attr_id}")
        if self.values[attr_id] <= ATTRIBUTE_MIN:
            name = ATTRIBUTE_DEFINITIONS.get(attr_id, {}).get("name", attr_id)
            return (False, f"{name} is already at minimum")

        self.values[attr_id] -= 1
        self.unspent_points += 1
        name = ATTRIBUTE_DEFINITIONS.get(attr_id, {}).get("name", attr_id)
        return (True, f"{name} decreased to {self.values[attr_id]}")

    def add_points(self, amount: int) -> None:
        """Grant unspent attribute points.

        Args:
            amount: Number of points to add.
        """
        self.unspent_points += amount

    def award_milestone(self, milestone_id: str) -> tuple[bool, str]:
        """Award a milestone bonus (+1 attribute point) if not already awarded.

        Args:
            milestone_id: Milestone identifier.

        Returns:
            Tuple of (success, message).
        """
        if milestone_id not in MILESTONE_DEFINITIONS:
            return (False, f"Unknown milestone: {milestone_id}")
        if milestone_id in self._awarded_milestones:
            return (False, "Milestone already awarded")

        self._awarded_milestones.add(milestone_id)
        self.unspent_points += 1
        desc = MILESTONE_DEFINITIONS[milestone_id]
        return (True, f"Milestone: {desc} — +1 attribute point!")

    def has_milestone(self, milestone_id: str) -> bool:
        """Check if a milestone has been awarded.

        Args:
            milestone_id: Milestone identifier.

        Returns:
            True if the milestone has been awarded.
        """
        return milestone_id in self._awarded_milestones

    def get_bonus(self, bonus_type: str) -> float:
        """Get passive bonus for a given bonus type based on attribute values.

        Args:
            bonus_type: The bonus key (e.g., "buy_price_attr_reduction").

        Returns:
            Bonus value (0.0 if unknown type or base attribute).
        """
        if bonus_type not in _BONUS_RATES:
            return 0.0
        attr_id, rate = _BONUS_RATES[bonus_type]
        modifier = self.get_modifier(attr_id)
        return modifier * rate

    def to_dict(self) -> dict[str, Any]:
        """Serialize attribute state for saving."""
        return {
            "values": dict(self.values),
            "unspent_points": self.unspent_points,
            "awarded_milestones": sorted(self._awarded_milestones),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttributeSheet":
        """Restore attribute state from saved data.

        Args:
            data: Dict from to_dict(). Empty dict gives fresh defaults.

        Returns:
            Restored AttributeSheet.
        """
        if not data:
            return cls()

        values = dict(data.get("values", {}))
        unspent = data.get("unspent_points", 0)
        milestones = set(data.get("awarded_milestones", []))

        sheet = cls(values=values, unspent_points=unspent)
        sheet._awarded_milestones = milestones
        return sheet
