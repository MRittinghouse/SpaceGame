"""Ship module data models for the module-based builder system.

Defines ShipModule (a functional ship component blueprint) and PlacedModule
(a module positioned on the ship grid). Modules are the primary building
unit — pre-designed, multi-pixel parts with fixed stats, named identity,
and manufacturer affiliation.

Also provides build-level functions: resolve_all_pixels, can_place_module.

Part of the Shipbuilder Upgrade — Phases 1-2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from spacegame.models.ship_build import PlacedPixel

# ============================================================================
# Constants
# ============================================================================

MODULE_CATEGORIES: set[str] = {
    "cockpit",
    "engine",
    "weapon",
    "shield",
    "cargo",
    "crew",
    "reactor",
    "utility",
    "structural",
}

MANUFACTURERS: set[str] = {
    "reyes_kowalski",
    "foundry",
    "talon",
    "sable",
    "meridian",
    "salvage_rat",
}

MANUFACTURER_COST_MULTIPLIERS: dict[str, float] = {
    "salvage_rat": 0.6,
    "reyes_kowalski": 1.0,
    "foundry": 1.1,
    "talon": 1.2,
    "sable": 1.3,
    "meridian": 1.5,
}


# ============================================================================
# ShipModule
# ============================================================================


@dataclass
class ShipModule:
    """A ship module blueprint — a functional component with pixel art and stats.

    Modules are pre-designed, multi-pixel building blocks. Each module has a
    2D pixel grid where characters map to visual materials via material_map.
    The '.' character represents empty space.

    Modules provide fixed stats (not per-pixel accumulation) and carry
    equipment slots implicitly based on their category.
    """

    id: str
    name: str
    description: str
    category: str
    manufacturer: str
    pixel_grid: list[list[str]]
    material_map: dict[str, str]
    provides: dict = field(default_factory=dict)
    weight: float = 0.0
    base_cost: int = 0
    unlock_method: str = "free"
    unlock_cost: int = 0
    unlock_source: str = ""
    discovery_flavor: str = ""

    @property
    def width(self) -> int:
        """Width of the module bounding box (columns)."""
        if not self.pixel_grid:
            return 0
        return len(self.pixel_grid[0]) if self.pixel_grid[0] else 0

    @property
    def height(self) -> int:
        """Height of the module bounding box (rows)."""
        return len(self.pixel_grid)

    @property
    def pixel_count(self) -> int:
        """Number of filled (non-empty) pixels in the module."""
        return sum(1 for row in self.pixel_grid for cell in row if cell != ".")

    @property
    def instantiation_cost(self) -> int:
        """Credit cost to place this module, with manufacturer multiplier."""
        mult = MANUFACTURER_COST_MULTIPLIERS.get(self.manufacturer, 1.0)
        return int(self.base_cost * mult)

    def filled_pixels(self) -> list[tuple[int, int, str]]:
        """Return filled pixel positions with their material characters.

        Returns:
            List of (local_x, local_y, material_char) for non-empty cells.
        """
        result: list[tuple[int, int, str]] = []
        for row_idx, row in enumerate(self.pixel_grid):
            for col_idx, cell in enumerate(row):
                if cell != ".":
                    result.append((col_idx, row_idx, cell))
        return result

    def resolved_pixels(self) -> list[tuple[int, int, str]]:
        """Return filled pixel positions with resolved material IDs.

        Uses material_map to convert grid characters to actual material IDs.

        Returns:
            List of (local_x, local_y, material_id) for non-empty cells.
        """
        result: list[tuple[int, int, str]] = []
        for col_idx, row_idx, char in self.filled_pixels():
            material_id = self.material_map.get(char, char)
            result.append((col_idx, row_idx, material_id))
        return result

    def rotated(self, times: int = 1) -> ShipModule:
        """Return a new module rotated 90 degrees clockwise.

        Args:
            times: Number of 90-degree clockwise rotations (0-3).

        Returns:
            New ShipModule with rotated pixel grid.
        """
        grid = [row[:] for row in self.pixel_grid]
        for _ in range(times % 4):
            rows = len(grid)
            cols = len(grid[0]) if grid else 0
            new_grid: list[list[str]] = []
            for c in range(cols):
                new_row = [grid[rows - 1 - r][c] for r in range(rows)]
                new_grid.append(new_row)
            grid = new_grid
        return ShipModule(
            id=self.id,
            name=self.name,
            description=self.description,
            category=self.category,
            manufacturer=self.manufacturer,
            pixel_grid=grid,
            material_map=dict(self.material_map),
            provides=dict(self.provides),
            weight=self.weight,
            base_cost=self.base_cost,
            unlock_method=self.unlock_method,
            unlock_cost=self.unlock_cost,
            unlock_source=self.unlock_source,
            discovery_flavor=self.discovery_flavor,
        )

    def flipped(self) -> ShipModule:
        """Return a new module flipped horizontally.

        Returns:
            New ShipModule with horizontally mirrored pixel grid.
        """
        grid = [row[::-1] for row in self.pixel_grid]
        return ShipModule(
            id=self.id,
            name=self.name,
            description=self.description,
            category=self.category,
            manufacturer=self.manufacturer,
            pixel_grid=grid,
            material_map=dict(self.material_map),
            provides=dict(self.provides),
            weight=self.weight,
            base_cost=self.base_cost,
            unlock_method=self.unlock_method,
            unlock_cost=self.unlock_cost,
            unlock_source=self.unlock_source,
            discovery_flavor=self.discovery_flavor,
        )

    def to_dict(self) -> dict:
        """Serialize module to dict (compact mask format)."""
        compact = ["".join(row) for row in self.pixel_grid]
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "manufacturer": self.manufacturer,
            "pixel_mask_compact": compact,
            "material_map": dict(self.material_map),
            "provides": dict(self.provides),
            "weight": self.weight,
            "base_cost": self.base_cost,
            "unlock_method": self.unlock_method,
            "unlock_cost": self.unlock_cost,
            "unlock_source": self.unlock_source,
            "discovery_flavor": self.discovery_flavor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ShipModule:
        """Restore module from dict.

        Args:
            data: Dict with module fields. pixel_mask_compact is a list
                of strings where each character is a material key or '.'.

        Returns:
            New ShipModule instance.
        """
        compact = data.get("pixel_mask_compact", [])
        grid = [list(row) for row in compact]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "structural"),
            manufacturer=data.get("manufacturer", "reyes_kowalski"),
            pixel_grid=grid,
            material_map=data.get("material_map", {}),
            provides=data.get("provides", {}),
            weight=data.get("weight", 0.0),
            base_cost=data.get("base_cost", 0),
            unlock_method=data.get("unlock_method", "free"),
            unlock_cost=data.get("unlock_cost", 0),
            unlock_source=data.get("unlock_source", ""),
            discovery_flavor=data.get("discovery_flavor", ""),
        )


# ============================================================================
# PlacedModule
# ============================================================================


@dataclass
class PlacedModule:
    """A module placed on the ship grid at a specific position and orientation.

    Stores a reference to the module blueprint (by ID) plus placement
    coordinates, rotation, and flip state. Color overrides allow per-pixel
    recoloring of hull pixels without changing module shape or stats.
    """

    module_id: str
    x: int
    y: int
    rotation: int = 0
    flipped: bool = False
    color_overrides: dict[tuple[int, int], str] = field(default_factory=dict)
    # Equipment installed in this module's slot (Systems Unification)
    installed_upgrade_id: Optional[str] = None
    upgrade_mark: int = 1
    upgrade_tuning: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result: dict = {
            "module_id": self.module_id,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "flipped": self.flipped,
        }
        if self.color_overrides:
            result["color_overrides"] = {
                f"{k[0]},{k[1]}": v for k, v in self.color_overrides.items()
            }
        if self.installed_upgrade_id is not None:
            result["installed_upgrade_id"] = self.installed_upgrade_id
            result["upgrade_mark"] = self.upgrade_mark
            result["upgrade_tuning"] = self.upgrade_tuning
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PlacedModule:
        """Restore from dict. Backward-compatible with old saves."""
        overrides: dict[tuple[int, int], str] = {}
        raw_overrides = data.get("color_overrides", {})
        for key_str, mat_id in raw_overrides.items():
            parts = key_str.split(",")
            if len(parts) == 2:
                try:
                    overrides[(int(parts[0]), int(parts[1]))] = mat_id
                except ValueError:
                    pass
        return cls(
            module_id=data["module_id"],
            x=data["x"],
            y=data["y"],
            rotation=data.get("rotation", 0),
            flipped=data.get("flipped", False),
            color_overrides=overrides,
            installed_upgrade_id=data.get("installed_upgrade_id"),
            upgrade_mark=data.get("upgrade_mark", 1),
            upgrade_tuning=data.get("upgrade_tuning"),
        )


# Materials that can be recolored (hull-frame pixels only)
RECOLORABLE_MATERIAL_PREFIXES = ("module_hull_", "legendary_hull")

# Functional materials that are locked (cannot be recolored)
LOCKED_MATERIALS = frozenset(
    {
        "cockpit_glass",
        "console_panel",
        "exhaust_port",
        "weapon_barrel",
        "shield_emitter",
        "sensor_dish",
        "cargo_interior",
        "reactor_core",
        "crew_quarters_interior",
        "legendary_core",
        "void_material",
        "phantom_material",
    }
)


def is_pixel_recolorable(module: ShipModule, local_x: int, local_y: int) -> bool:
    """Check if a pixel within a module can be recolored.

    Only hull-frame pixels (mapped to manufacturer hull materials) are
    recolorable. Functional material pixels (glass, exhaust, barrels,
    emitters, etc.) are locked to preserve module visual identity.

    Args:
        module: The module blueprint.
        local_x: X coordinate within the module grid.
        local_y: Y coordinate within the module grid.

    Returns:
        True if the pixel can be recolored, False if locked or empty.
    """
    if local_y < 0 or local_y >= module.height or local_x < 0 or local_x >= module.width:
        return False

    char = module.pixel_grid[local_y][local_x]
    if char == ".":
        return False

    material_id = module.material_map.get(char, "")
    if material_id in LOCKED_MATERIALS:
        return False

    # Check if it's a hull material (recolorable)
    for prefix in RECOLORABLE_MATERIAL_PREFIXES:
        if material_id.startswith(prefix):
            return True

    return False


# ============================================================================
# Resolution
# ============================================================================


def resolve_placed_module(
    placed: PlacedModule,
    module_catalog: dict[str, ShipModule],
) -> list[PlacedPixel]:
    """Resolve a placed module into world-space PlacedPixels.

    Applies the module's flip and rotation, then offsets all pixels
    by the placement position.

    Args:
        placed: The placed module with position and orientation.
        module_catalog: Dict of all module blueprints keyed by ID.

    Returns:
        List of PlacedPixel at world coordinates with resolved material IDs.
    """
    module = module_catalog[placed.module_id]

    # Apply orientation: flip first, then rotate
    oriented = module
    if placed.flipped:
        oriented = oriented.flipped()
    if placed.rotation:
        oriented = oriented.rotated(placed.rotation)

    # Convert to world coordinates, applying color overrides
    pixels: list[PlacedPixel] = []
    overrides = placed.color_overrides
    for local_x, local_y, material_id in oriented.resolved_pixels():
        # Apply color override if one exists for this local pixel
        if overrides and (local_x, local_y) in overrides:
            material_id = overrides[(local_x, local_y)]
        pixels.append(
            PlacedPixel(
                x=placed.x + local_x,
                y=placed.y + local_y,
                material_id=material_id,
            )
        )
    return pixels


def _get_oriented_module(
    placed: PlacedModule,
    module_catalog: dict[str, ShipModule],
) -> ShipModule:
    """Get a module with flip and rotation applied."""
    module = module_catalog[placed.module_id]
    oriented = module
    if placed.flipped:
        oriented = oriented.flipped()
    if placed.rotation:
        oriented = oriented.rotated(placed.rotation)
    return oriented


# ============================================================================
# Build-Level Functions
# ============================================================================


def resolve_all_pixels(
    build: "ShipBuild",
    module_catalog: dict[str, ShipModule],
) -> list[PlacedPixel]:
    """Return all hull pixels from the build.

    Legacy modules are no longer supported; this returns only hull pixels.
    The module_catalog parameter is kept for API compatibility.

    Args:
        build: The ship build with hull pixels.
        module_catalog: Module blueprints (unused, kept for compatibility).

    Returns:
        List of PlacedPixel from the build's hull pixels.
    """
    return list(build.pixels)


def can_place_module(
    build: "ShipBuild",
    placed: PlacedModule,
    module_catalog: dict[str, ShipModule],
    materials_catalog: dict[str, "HullMaterial"],
) -> tuple[bool, str]:
    """Check if a module can be placed on the build grid.

    Validates bounds, overlap with existing modules/hull pixels, and
    weight budget.

    Args:
        build: Current ship build state.
        placed: The module placement to validate.
        module_catalog: Dict of all module blueprints keyed by ID.
        materials_catalog: Dict of all materials keyed by ID.

    Returns:
        (success, message) tuple.
    """
    if placed.module_id not in module_catalog:
        return False, f"Unknown module: {placed.module_id}"

    oriented = _get_oriented_module(placed, module_catalog)
    module = module_catalog[placed.module_id]

    # Bounds check
    if placed.x < 0 or placed.y < 0:
        return False, "Position out of bounds"
    if placed.x + oriented.width > build.canvas_w:
        return False, "Module extends beyond canvas (right)"
    if placed.y + oriented.height > build.canvas_h:
        return False, "Module extends beyond canvas (bottom)"

    # Build set of occupied coordinates (hull pixels)
    occupied: set[tuple[int, int]] = set()
    for p in build.pixels:
        occupied.add((p.x, p.y))

    # Check overlap
    for local_x, local_y, _ in oriented.filled_pixels():
        wx, wy = placed.x + local_x, placed.y + local_y
        if (wx, wy) in occupied:
            return False, f"Overlap at ({wx}, {wy})"

    # Weight check
    current_weight = 0.0
    for p in build.pixels:
        mat = materials_catalog.get(p.material_id)
        if mat:
            current_weight += mat.weight_per_pixel

    new_weight = current_weight + module.weight
    if new_weight > build.max_weight:
        return False, (f"Exceeds weight limit ({new_weight:.1f}/{build.max_weight})")

    return True, "OK"


