"""Slot definition model for the slot-based ship builder.

Defines the types and sizes of slots that can be placed on a ship's
pixel grid. Each slot type+size combination has a fixed grid footprint,
weight cost, and placement cost.
"""

from dataclasses import dataclass

# Valid slot types — each maps to a category of equippable parts
SLOT_TYPES: frozenset[str] = frozenset(
    {
        "cockpit",
        "weapon",
        "defense",
        "engine",
        "utility",
        "cargo",
        "crew_quarters",
        "reactor",
    }
)

# Valid slot sizes
SLOT_SIZES: frozenset[str] = frozenset({"small", "medium", "large"})

# Numeric ordering for size compatibility checks
SIZE_ORDER: dict[str, int] = {"small": 0, "medium": 1, "large": 2}

# Display-friendly type names
_TYPE_DISPLAY: dict[str, str] = {
    "cockpit": "Cockpit",
    "weapon": "Weapon",
    "defense": "Defense",
    "engine": "Engine",
    "utility": "Utility",
    "cargo": "Cargo",
    "crew_quarters": "Crew Quarters",
    "reactor": "Reactor",
}

_SIZE_DISPLAY: dict[str, str] = {
    "small": "S",
    "medium": "M",
    "large": "L",
}


@dataclass
class SlotDefinition:
    """Definition of a slot type+size that can be placed on a ship grid.

    Each slot occupies a rectangular footprint on the pixel grid and has
    a weight and credit cost for fabrication/placement. The slot itself
    is an empty placeholder — actual equipment (parts) are assigned in
    the Loadout tab.

    Attributes:
        id: Unique identifier (e.g., "weapon_small", "cargo_large").
        slot_type: Category of parts this slot accepts.
        size: Physical size class affecting grid footprint and part compatibility.
        footprint_w: Grid width in pixels.
        footprint_h: Grid height in pixels.
        weight: Weight cost when placed on the ship.
        placement_cost: Credit cost to fabricate/install this slot.
        color: RGB tuple for rendering the slot type on the grid.
    """

    id: str
    slot_type: str
    size: str
    footprint_w: int
    footprint_h: int
    weight: float
    placement_cost: int
    color: tuple[int, int, int]
    custom_name: str = ""  # Override display name (e.g., "Scout Pod")
    unlock_faction: str = ""  # Faction ID required (empty = always available)
    unlock_rep_tier: str = ""  # Min reputation tier ("friendly", "allied")

    @property
    def grid_area(self) -> int:
        """Total pixel grid cells this slot occupies."""
        return self.footprint_w * self.footprint_h

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        if self.custom_name:
            return self.custom_name
        type_name = _TYPE_DISPLAY.get(self.slot_type, self.slot_type.title())
        size_label = _SIZE_DISPLAY.get(self.size, self.size[0].upper())
        return f"{type_name} ({size_label})"

    @staticmethod
    def part_fits_slot(part_size: str, slot_size: str) -> bool:
        """Check if a part of the given size fits in a slot of the given size.

        A small part fits any slot. A medium part fits medium or large.
        A large part only fits large.

        Args:
            part_size: The part's minimum size requirement.
            slot_size: The slot's size.

        Returns:
            True if the part fits in the slot.
        """
        return SIZE_ORDER.get(part_size, 0) <= SIZE_ORDER.get(slot_size, 0)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        d = {
            "id": self.id,
            "slot_type": self.slot_type,
            "size": self.size,
            "footprint_w": self.footprint_w,
            "footprint_h": self.footprint_h,
            "weight": self.weight,
            "placement_cost": self.placement_cost,
            "color": list(self.color),
        }
        if self.custom_name:
            d["custom_name"] = self.custom_name
        if self.unlock_faction:
            d["unlock_faction"] = self.unlock_faction
            d["unlock_rep_tier"] = self.unlock_rep_tier
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SlotDefinition":
        """Deserialize from a dict."""
        color = data.get("color", [150, 150, 150])
        return cls(
            id=data["id"],
            slot_type=data["slot_type"],
            size=data["size"],
            footprint_w=data["footprint_w"],
            footprint_h=data["footprint_h"],
            weight=data.get("weight", 1.0),
            placement_cost=data.get("placement_cost", 100),
            color=tuple(color),
            custom_name=data.get("custom_name", ""),
            unlock_faction=data.get("unlock_faction", ""),
            unlock_rep_tier=data.get("unlock_rep_tier", ""),
        )
