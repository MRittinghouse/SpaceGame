"""Ship part model for equippable items that go into ship slots.

Parts are inventory items the player buys and assigns to slots on their
ship. Each part has a slot type (what kind of slot it fits) and a minimum
size requirement (a medium part fits medium or large slots, not small).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ShipPart:
    """An equippable ship part that installs into a slot.

    Attributes:
        id: Unique identifier.
        name: Display name.
        description: Flavor/info text.
        slot_type: What slot type this part fits ("weapon", "defense", etc.).
        min_size: Minimum slot size required ("small", "medium", "large").
        manufacturer: Manufacturer ID for faction/flavor variety.
        provides: Stat contributions when equipped (same keys as module provides).
        base_cost: Purchase price in credits.
        mark: Quality tier (1=Mk1, 2=Mk2, 3=Mk3).
        weight: Additional weight when equipped (on top of slot weight).
        legendary: Whether this is a legendary boss-drop part.
        combat_move: Combat action when equipped (weapons/defense).
    """

    id: str
    name: str
    description: str
    slot_type: str
    min_size: str
    manufacturer: str
    provides: dict = field(default_factory=dict)
    base_cost: int = 0
    mark: int = 1
    weight: float = 0.0
    legendary: bool = False
    combat_move: Optional[dict] = None

    def fits_in_slot_size(self, slot_size: str) -> bool:
        """Check if this part fits in a slot of the given size.

        Strict matching: Small fits Small, Medium fits Medium, Large fits Large.
        """
        return self.min_size == slot_size

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "slot_type": self.slot_type,
            "min_size": self.min_size,
            "manufacturer": self.manufacturer,
            "provides": dict(self.provides),
            "base_cost": self.base_cost,
            "mark": self.mark,
            "weight": self.weight,
            "legendary": self.legendary,
            "combat_move": dict(self.combat_move) if self.combat_move else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipPart":
        """Deserialize from a dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            slot_type=data["slot_type"],
            min_size=data.get("min_size", "small"),
            manufacturer=data.get("manufacturer", ""),
            provides=data.get("provides", {}),
            base_cost=data.get("base_cost", 0),
            mark=data.get("mark", 1),
            weight=data.get("weight", 0.0),
            legendary=data.get("legendary", False),
            combat_move=data.get("combat_move"),
        )
