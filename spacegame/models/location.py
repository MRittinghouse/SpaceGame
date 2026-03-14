"""Station location models for planet infrastructure.

Represents visitable locations within star systems — markets, repair bays,
cantinas, and unique points of interest.
"""

from dataclasses import dataclass


@dataclass
class Location:
    """A visitable location within a star system.

    Attributes:
        id: Unique identifier for this location.
        name: Display name.
        location_type: Category — market, repair_bay, cantina, mining,
            salvaging, refining, shipyard, or unique.
        description: One-line gameplay description.
        flavor_text: Faction-flavored ambient text for atmosphere.
        system_id: ID of the star system this location belongs to.
        repair_cost_per_hp: Credits per hull point for repair_bay type.
            Zero for non-repair locations.
    """

    id: str
    name: str
    location_type: str
    description: str
    flavor_text: str
    system_id: str
    repair_cost_per_hp: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dict representation of this location.
        """
        return {
            "id": self.id,
            "name": self.name,
            "location_type": self.location_type,
            "description": self.description,
            "flavor_text": self.flavor_text,
            "system_id": self.system_id,
            "repair_cost_per_hp": self.repair_cost_per_hp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        """Deserialize from dictionary.

        Args:
            data: Dict with location fields.

        Returns:
            Location instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            location_type=data["location_type"],
            description=data["description"],
            flavor_text=data.get("flavor_text", ""),
            system_id=data.get("system_id", ""),
            repair_cost_per_hp=data.get("repair_cost_per_hp", 0),
        )
