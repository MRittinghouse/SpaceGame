"""
Star system and station models.

Represents star systems, their coordinates, stations, and economic properties.
"""

from dataclasses import dataclass, field
from typing import List
import math


@dataclass
class Coordinates:
    """2D coordinates for star systems."""

    x: float
    y: float

    def distance_to(self, other: "Coordinates") -> float:
        """
        Calculate Euclidean distance to another coordinate.

        Args:
            other: Target coordinates

        Returns:
            Distance as a float
        """
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Station:
    """Trading station within a star system."""

    id: str
    name: str
    type: str  # major, minor
    description: str
    docking_fee: int
    market_variety: str  # full, industrial, agricultural, mining, high_tech, basic


@dataclass
class Economy:
    """Economic properties of a star system."""

    production_tags: List[str]
    consumption_tags: List[str]
    tariff_rate: float  # Percentage as decimal (e.g., 0.02 = 2%)


@dataclass
class StarSystem:
    """
    Represents a star system in the galaxy.

    Contains all properties needed for trading, navigation, and gameplay.
    """

    id: str
    name: str
    type: str  # trade_hub, agricultural, industrial, mining, research
    description: str
    coordinates: Coordinates
    danger_level: str  # safe, moderate, dangerous
    faction: str
    stations: List[Station]
    economy: Economy
    rest_cost: int  # Cost to rest/stay for one day

    def distance_to(self, other: "StarSystem") -> float:
        """
        Calculate distance to another star system.

        Args:
            other: Target star system

        Returns:
            Distance in coordinate units
        """
        return self.coordinates.distance_to(other.coordinates)

    def fuel_cost_to(self, other: "StarSystem", fuel_efficiency: int) -> int:
        """
        Calculate fuel cost to travel to another system.

        Args:
            other: Destination system
            fuel_efficiency: Ship's fuel consumption per unit distance

        Returns:
            Fuel units required
        """
        distance = self.distance_to(other)
        # Base fuel cost is fuel_efficiency * (distance / 30)
        # Reduced by 66% to allow more travel flexibility with starter ship
        # This makes ~90 distance units = ~30 fuel cost for shuttle (fuel_efficiency=10)
        return max(1, int(fuel_efficiency * (distance / 30)))

    def get_main_station(self) -> Station:
        """
        Get the primary/first station in this system.

        Returns:
            The main station
        """
        return self.stations[0] if self.stations else None

    def produces(self, commodity_tag: str) -> bool:
        """
        Check if this system produces goods with the given tag.

        Args:
            commodity_tag: Tag to check (e.g., "food", "machinery")

        Returns:
            True if system produces this type of commodity
        """
        return commodity_tag in self.economy.production_tags

    def consumes(self, commodity_tag: str) -> bool:
        """
        Check if this system consumes goods with the given tag.

        Args:
            commodity_tag: Tag to check

        Returns:
            True if system demands this type of commodity
        """
        return commodity_tag in self.economy.consumption_tags
