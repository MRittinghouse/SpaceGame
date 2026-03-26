"""Slot definition model for the slot-based ship builder.

Defines the types and sizes of slots that can be placed on a ship's
pixel grid. Each slot type+size combination has a fixed grid footprint,
weight cost, and placement cost.
"""

from dataclasses import dataclass, field

# Valid slot types — each maps to a category of equippable parts
SLOT_TYPES: frozenset[str] = frozenset(
    {
        "cockpit",
        "weapon",
        "defense",
        "engine",
        "utility",
        "fuel",
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
    "fuel": "Fuel Tank",
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
    pixel_mask: list[str] = field(default_factory=list)  # Row strings: "XX.." = filled/empty
    variant_group: str = ""  # Group ID for variant cycling (e.g., "weapon_medium")
    variant_name: str = ""  # Short variant label (e.g., "Standard", "Angular")

    @property
    def grid_area(self) -> int:
        """Total filled cells (from pixel_mask if present, else w*h)."""
        if self.pixel_mask:
            return sum(row.count("X") for row in self.pixel_mask)
        return self.footprint_w * self.footprint_h

    def get_rotated(self, rotation: int) -> tuple[int, int, list[str]]:
        """Get footprint dimensions and mask after rotation.

        Args:
            rotation: 0-3 (number of 90° clockwise rotations).

        Returns:
            (width, height, rotated_pixel_mask) tuple.
        """
        r = rotation % 4
        w, h = self.footprint_w, self.footprint_h
        mask = self.pixel_mask

        if r == 0:
            return w, h, mask

        # Build a full grid, rotate, extract
        if not mask:
            # Pure rectangle — just swap dimensions
            if r in (1, 3):
                return h, w, []
            return w, h, []

        # Rotate the mask grid
        grid = []
        for row_str in mask:
            grid.append(list(row_str))

        for _ in range(r):
            # 90° clockwise: new[x][old_h - 1 - y] = old[y][x]
            old_h = len(grid)
            old_w = len(grid[0]) if grid else 0
            new_grid = [["." for _ in range(old_h)] for _ in range(old_w)]
            for y in range(old_h):
                for x in range(old_w):
                    new_grid[x][old_h - 1 - y] = grid[y][x]
            grid = new_grid

        new_h = len(grid)
        new_w = len(grid[0]) if grid else 0
        new_mask = ["".join(row) for row in grid]
        return new_w, new_h, new_mask

    def is_filled(self, local_x: int, local_y: int) -> bool:
        """Check if a local grid cell is filled in this slot's shape.

        Args:
            local_x: Column within the footprint (0 to footprint_w-1).
            local_y: Row within the footprint (0 to footprint_h-1).

        Returns:
            True if the cell is filled (part of the slot shape).
        """
        if not self.pixel_mask:
            return 0 <= local_x < self.footprint_w and 0 <= local_y < self.footprint_h
        if 0 <= local_y < len(self.pixel_mask):
            row = self.pixel_mask[local_y]
            if 0 <= local_x < len(row):
                return row[local_x] == "X"
        return False

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
        if self.pixel_mask:
            d["pixel_mask"] = self.pixel_mask
        if self.variant_group:
            d["variant_group"] = self.variant_group
        if self.variant_name:
            d["variant_name"] = self.variant_name
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
            pixel_mask=data.get("pixel_mask", []),
            variant_group=data.get("variant_group", ""),
            variant_name=data.get("variant_name", ""),
        )
