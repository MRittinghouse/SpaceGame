"""
Commodity and trading good models.

Defines tradeable commodities with their economic properties.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class CommodityCategory(Enum):
    """Category classification for commodities."""

    BASIC = "basic"
    INDUSTRIAL = "industrial"
    LUXURY = "luxury"
    QUEST = "quest"
    COMPONENT = "component"


class Legality(Enum):
    """Legal status of commodities."""

    LEGAL = "legal"
    RESTRICTED = "restricted"
    ILLEGAL = "illegal"


@dataclass
class Commodity:
    """
    Represents a tradeable commodity in the game.

    Commodities have base prices that fluctuate based on supply/demand,
    system economy, and random variance.
    """

    id: str
    name: str
    category: CommodityCategory
    description: str
    base_price: int
    variance_min: float  # Negative percentage (e.g., -0.20 = -20%)
    variance_max: float  # Positive percentage (e.g., 0.30 = +30%)
    volume_per_unit: int  # Cargo space consumed per unit
    legality: Legality
    production_tags: List[str]
    consumption_tags: List[str]

    def get_price_range(self) -> tuple[int, int]:
        """
        Calculate the absolute min/max price range for this commodity.

        Returns:
            Tuple of (min_price, max_price)
        """
        min_price = int(self.base_price * (1 + self.variance_min))
        max_price = int(self.base_price * (1 + self.variance_max))
        return (min_price, max_price)

    def calculate_cargo_space(self, quantity: int) -> int:
        """
        Calculate total cargo space required for a quantity.

        Args:
            quantity: Number of units

        Returns:
            Total cargo space required
        """
        return quantity * self.volume_per_unit

    def max_units_for_cargo(self, available_cargo: int) -> int:
        """
        Calculate maximum units that fit in available cargo space.

        Args:
            available_cargo: Available cargo capacity

        Returns:
            Maximum number of units that fit
        """
        return available_cargo // self.volume_per_unit

    def is_produced_by(self, system_tags: List[str]) -> bool:
        """
        Check if this commodity is produced by systems with given tags.

        Args:
            system_tags: List of system production tags

        Returns:
            True if any production tag matches
        """
        return any(tag in system_tags for tag in self.production_tags)

    def is_consumed_by(self, system_tags: List[str]) -> bool:
        """
        Check if this commodity is consumed by systems with given tags.

        Args:
            system_tags: List of system consumption tags

        Returns:
            True if any consumption tag matches
        """
        return any(tag in system_tags for tag in self.consumption_tags)
