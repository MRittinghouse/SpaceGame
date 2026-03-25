"""Ship builder data models and computation engine.

Pure data structures for the pixel ship designer. No pygame imports.
Handles shape definitions, material stats, grid placement validation,
stat derivation, weight modifiers, and defensive identity detection.

Part of the Shipyard Overhaul — Phase A1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.ship_module import PlacedModule


# ============================================================================
# Weight Classes
# ============================================================================

WEIGHT_CLASSES: dict[str, dict] = {
    "tiny": {"canvas_w": 16, "canvas_h": 16, "max_weight": 55, "max_slots": 4, "unlock_cost": 0},
    "small": {
        "canvas_w": 32,
        "canvas_h": 20,
        "max_weight": 110,
        "max_slots": 7,
        "unlock_cost": 15000,
    },
    "medium": {
        "canvas_w": 40,
        "canvas_h": 28,
        "max_weight": 190,
        "max_slots": 10,
        "unlock_cost": 60000,
    },
    "large": {
        "canvas_w": 56,
        "canvas_h": 40,
        "max_weight": 330,
        "max_slots": 14,
        "unlock_cost": 200000,
    },
    "xlarge": {
        "canvas_w": 72,
        "canvas_h": 52,
        "max_weight": 550,
        "max_slots": 18,
        "unlock_cost": 500000,
    },
}

# LEGACY: Old slot pool system, kept only for backward compatibility
# with saves created before the module-based builder. New builds use
# MODULE_CAPS instead. Do not reference in new code.
SLOT_POOLS: dict[str, dict[str, int]] = {
    "tiny": {"weapon": 1, "defense": 1, "utility": 1, "engine": 1},
    "small": {"weapon": 2, "defense": 1, "utility": 2, "engine": 2},
    "medium": {"weapon": 3, "defense": 2, "utility": 3, "engine": 2},
    "large": {"weapon": 4, "defense": 3, "utility": 4, "engine": 3},
    "xlarge": {"weapon": 6, "defense": 4, "utility": 5, "engine": 3},
}

# Maximum modules per category per weight class.
# These are soft caps — more generous than SLOT_POOLS since modules
# now serve as both structure and equipment slots. Prevents degenerate
# builds (20-weapon turret arrays) while preserving creative freedom.
MODULE_CAPS: dict[str, dict[str, int]] = {
    "tiny": {
        "cockpit": 1,
        "engine": 2,
        "weapon": 2,
        "shield": 2,
        "cargo": 2,
        "crew": 1,
        "reactor": 1,
        "utility": 3,
        "structural": 50,
    },
    "small": {
        "cockpit": 1,
        "engine": 3,
        "weapon": 3,
        "shield": 3,
        "cargo": 3,
        "crew": 2,
        "reactor": 1,
        "utility": 4,
        "structural": 50,
    },
    "medium": {
        "cockpit": 1,
        "engine": 4,
        "weapon": 5,
        "shield": 4,
        "cargo": 4,
        "crew": 3,
        "reactor": 2,
        "utility": 6,
        "structural": 50,
    },
    "large": {
        "cockpit": 1,
        "engine": 5,
        "weapon": 7,
        "shield": 5,
        "cargo": 5,
        "crew": 4,
        "reactor": 3,
        "utility": 8,
        "structural": 50,
    },
    "xlarge": {
        "cockpit": 1,
        "engine": 6,
        "weapon": 9,
        "shield": 7,
        "cargo": 6,
        "crew": 5,
        "reactor": 4,
        "utility": 10,
        "structural": 50,
    },
}

# Weight ratio → stat modifier thresholds
WEIGHT_MODIFIERS: list[tuple[float, float, str, float, float]] = [
    # (max_ratio, min_ratio, label, evasion_mult, speed_mult)
    (0.40, 0.00, "ULTRALIGHT", 1.15, 1.10),
    (0.60, 0.40, "LIGHT", 1.05, 1.05),
    (0.80, 0.60, "BALANCED", 1.00, 1.00),
    (0.95, 0.80, "HEAVY", 0.90, 0.95),
    (1.00, 0.95, "OVERLOADED", 0.80, 0.90),
]

# Frame variants: (width, height) for non-default canvas aspect ratios.
# Tiny and small have no variants. Variants preserve roughly the same
# total pixel area as the default canvas for each weight class.
FRAME_VARIANTS: dict[str, dict[str, tuple[int, int]]] = {
    "medium": {
        "wide": (48, 24),
        "tall": (28, 40),
    },
    "large": {
        "wide": (68, 32),
        "tall": (40, 56),
    },
    "xlarge": {
        "wide": (84, 44),
        "tall": (52, 72),
    },
}

# Identity detection: material pixel ratio threshold
IDENTITY_THRESHOLD = 0.35

# Materials that count toward each identity
JUGGERNAUT_MATERIALS = {
    "heavy_armor",
    "reinforced_plate",
    "ablative_plating",
    "nano_fiber",
    "crimson_steel",
}
SENTINEL_MATERIALS = {
    "shield_crystal",
    "barrier_lattice",
    "quantum_lattice",
}
GHOST_MATERIALS = {
    "stealth_composite",
    "phase_alloy",
    "void_glass",
    "light_alloy",
}


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class HullShape:
    """A geometric building block template for ship construction.

    Shapes are stamped onto the pixel grid. Each shape has a 2D boolean
    mask defining which pixels it fills. Shapes can be rotated 90° and
    flipped horizontally.
    """

    id: str
    name: str
    description: str
    pixel_mask: list[list[bool]]
    category: str = "basic"
    unlock_method: str = "free"
    unlock_cost: int = 0
    unlock_source: str = ""
    discovery_flavor: str = ""

    @property
    def width(self) -> int:
        """Width of the shape bounding box."""
        if not self.pixel_mask:
            return 0
        return len(self.pixel_mask[0]) if self.pixel_mask else 0

    @property
    def height(self) -> int:
        """Height of the shape bounding box."""
        return len(self.pixel_mask)

    @property
    def pixel_count(self) -> int:
        """Number of filled pixels in the shape."""
        return sum(1 for row in self.pixel_mask for cell in row if cell)

    def rotated(self, times: int = 1) -> HullShape:
        """Return a new shape rotated 90° clockwise the given number of times.

        Args:
            times: Number of 90° clockwise rotations (1-3).

        Returns:
            New HullShape with rotated pixel mask.
        """
        mask = [row[:] for row in self.pixel_mask]
        for _ in range(times % 4):
            # Rotate 90° clockwise: transpose then reverse each row
            rows = len(mask)
            cols = len(mask[0]) if mask else 0
            new_mask = []
            for c in range(cols):
                new_row = [mask[rows - 1 - r][c] for r in range(rows)]
                new_mask.append(new_row)
            mask = new_mask
        return HullShape(
            id=self.id,
            name=self.name,
            description=self.description,
            pixel_mask=mask,
            category=self.category,
            unlock_method=self.unlock_method,
            unlock_cost=self.unlock_cost,
            unlock_source=self.unlock_source,
            discovery_flavor=self.discovery_flavor,
        )

    def flipped(self) -> HullShape:
        """Return a new shape flipped horizontally.

        Returns:
            New HullShape with horizontally mirrored pixel mask.
        """
        mask = [row[::-1] for row in self.pixel_mask]
        return HullShape(
            id=self.id,
            name=self.name,
            description=self.description,
            pixel_mask=mask,
            category=self.category,
            unlock_method=self.unlock_method,
            unlock_cost=self.unlock_cost,
            unlock_source=self.unlock_source,
            discovery_flavor=self.discovery_flavor,
        )

    def to_dict(self) -> dict:
        """Serialize shape to dict."""
        compact = ["".join("#" if c else "." for c in row) for row in self.pixel_mask]
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pixel_mask_compact": compact,
            "category": self.category,
            "unlock_method": self.unlock_method,
            "unlock_cost": self.unlock_cost,
            "unlock_source": self.unlock_source,
            "discovery_flavor": self.discovery_flavor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HullShape:
        """Restore shape from dict."""
        if "pixel_mask_compact" in data:
            mask = [[c == "#" for c in row] for row in data["pixel_mask_compact"]]
        elif "pixel_mask" in data:
            mask = data["pixel_mask"]
        else:
            mask = []
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            pixel_mask=mask,
            category=data.get("category", "basic"),
            unlock_method=data.get("unlock_method", "free"),
            unlock_cost=data.get("unlock_cost", 0),
            unlock_source=data.get("unlock_source", ""),
            discovery_flavor=data.get("discovery_flavor", ""),
        )


@dataclass
class HullMaterial:
    """A material type that determines per-pixel stats and visual color.

    Materials are the primary way players express defensive identity.
    Each pixel filled with a material contributes its stats to the ship.
    """

    id: str
    name: str
    description: str
    color_primary: tuple[int, int, int]
    color_accent: tuple[int, int, int] = (0, 0, 0)
    color_highlight: tuple[int, int, int] = (0, 0, 0)
    hull_per_pixel: float = 0.0
    armor_per_pixel: float = 0.0
    shield_per_pixel: float = 0.0
    shield_regen_per_pixel: float = 0.0
    evasion_per_pixel: float = 0.0
    weight_per_pixel: float = 0.0
    cost_per_pixel: int = 0
    special_property: Optional[str] = None
    unlock_method: str = "free"
    unlock_cost: int = 0
    unlock_source: str = ""

    def to_dict(self) -> dict:
        """Serialize material to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color_primary": list(self.color_primary),
            "color_accent": list(self.color_accent),
            "color_highlight": list(self.color_highlight),
            "hull_per_pixel": self.hull_per_pixel,
            "armor_per_pixel": self.armor_per_pixel,
            "shield_per_pixel": self.shield_per_pixel,
            "shield_regen_per_pixel": self.shield_regen_per_pixel,
            "evasion_per_pixel": self.evasion_per_pixel,
            "weight_per_pixel": self.weight_per_pixel,
            "cost_per_pixel": self.cost_per_pixel,
            "special_property": self.special_property,
            "unlock_method": self.unlock_method,
            "unlock_cost": self.unlock_cost,
            "unlock_source": self.unlock_source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> HullMaterial:
        """Restore material from dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            color_primary=tuple(data.get("color_primary", [128, 128, 128])),
            color_accent=tuple(data.get("color_accent", [0, 0, 0])),
            color_highlight=tuple(data.get("color_highlight", [0, 0, 0])),
            hull_per_pixel=data.get("hull_per_pixel", 0.0),
            armor_per_pixel=data.get("armor_per_pixel", 0.0),
            shield_per_pixel=data.get("shield_per_pixel", 0.0),
            shield_regen_per_pixel=data.get("shield_regen_per_pixel", 0.0),
            evasion_per_pixel=data.get("evasion_per_pixel", 0.0),
            weight_per_pixel=data.get("weight_per_pixel", 0.0),
            cost_per_pixel=data.get("cost_per_pixel", 0),
            special_property=data.get("special_property"),
            unlock_method=data.get("unlock_method", "free"),
            unlock_cost=data.get("unlock_cost", 0),
            unlock_source=data.get("unlock_source", ""),
        )


@dataclass
class PlacedPixel:
    """A single filled pixel on the ship grid."""

    x: int
    y: int
    material_id: str

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "material_id": self.material_id}

    @classmethod
    def from_dict(cls, data: dict) -> PlacedPixel:
        return cls(x=data["x"], y=data["y"], material_id=data["material_id"])


@dataclass
class DesignatedSlot:
    """LEGACY: Equipment slot from the old pixel-based builder.

    Kept for backward compatibility with saves created before the
    module-based system. New builds use PlacedModule.installed_upgrade_id
    instead. Do not use in new code.

    Originally: An equipment slot placed on the ship grid.

    Each slot occupies a 2×2 area (3×3 for core) of filled pixels.
    Equipment modules are installed into slots to provide combat moves
    and stat bonuses.
    """

    slot_type: str  # "weapon", "defense", "engine", "utility", "core"
    x: int
    y: int
    equipment_id: Optional[str] = None
    mark: int = 1
    tuning: Optional[str] = None

    @property
    def size(self) -> int:
        """Grid footprint: 3 for core slots, 2 for all others."""
        return 3 if self.slot_type == "core" else 2

    def to_dict(self) -> dict:
        return {
            "slot_type": self.slot_type,
            "x": self.x,
            "y": self.y,
            "equipment_id": self.equipment_id,
            "mark": self.mark,
            "tuning": self.tuning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DesignatedSlot:
        return cls(
            slot_type=data["slot_type"],
            x=data["x"],
            y=data["y"],
            equipment_id=data.get("equipment_id"),
            mark=data.get("mark", 1),
            tuning=data.get("tuning"),
        )


@dataclass
class ShipBuild:
    """Complete ship configuration — the central data structure.

    A ShipBuild defines everything about a player's ship: the weight
    class (canvas size), every filled pixel with its material, and
    every designated equipment slot with installed modules.
    """

    weight_class: str
    pixels: list[PlacedPixel] = field(default_factory=list)
    slots: list[DesignatedSlot] = field(default_factory=list)
    preset_name: Optional[str] = None
    modules: list[PlacedModule] = field(default_factory=list)
    frame_variant: Optional[str] = None

    @property
    def canvas_size(self) -> int:
        """Largest grid dimension for backward compat (max of w, h)."""
        return max(self.canvas_w, self.canvas_h)

    @property
    def canvas_w(self) -> int:
        """Grid width, accounting for frame variant."""
        if self.frame_variant and self.weight_class in FRAME_VARIANTS:
            variants = FRAME_VARIANTS[self.weight_class]
            if self.frame_variant in variants:
                return variants[self.frame_variant][0]
        return WEIGHT_CLASSES.get(self.weight_class, {}).get("canvas_w", 32)

    @property
    def canvas_h(self) -> int:
        """Grid height, accounting for frame variant."""
        if self.frame_variant and self.weight_class in FRAME_VARIANTS:
            variants = FRAME_VARIANTS[self.weight_class]
            if self.frame_variant in variants:
                return variants[self.frame_variant][1]
        return WEIGHT_CLASSES.get(self.weight_class, {}).get("canvas_h", 32)

    @property
    def max_weight(self) -> int:
        """Maximum weight budget for this weight class."""
        return WEIGHT_CLASSES.get(self.weight_class, {}).get("max_weight", 140)

    def to_dict(self) -> dict:
        """Serialize build to dict, including modules and frame variant."""
        result: dict = {
            "weight_class": self.weight_class,
            "pixels": [p.to_dict() for p in self.pixels],
            "slots": [s.to_dict() for s in self.slots],
            "preset_name": self.preset_name,
        }
        if self.modules:
            result["modules"] = [m.to_dict() for m in self.modules]
        if self.frame_variant:
            result["frame_variant"] = self.frame_variant
        return result

    @classmethod
    def from_dict(cls, data: dict) -> ShipBuild:
        """Restore build from dict. Backward-compatible with old saves."""
        # Local import to avoid circular dependency
        from spacegame.models.ship_module import PlacedModule as PM

        modules = [PM.from_dict(m) for m in data.get("modules", [])]
        return cls(
            weight_class=data["weight_class"],
            pixels=[PlacedPixel.from_dict(p) for p in data.get("pixels", [])],
            slots=[DesignatedSlot.from_dict(s) for s in data.get("slots", [])],
            preset_name=data.get("preset_name"),
            modules=modules,
            frame_variant=data.get("frame_variant"),
        )


@dataclass
class ComputedShipStats:
    """All derived stats for a ship build.

    Computed from the sum of material stats across all pixels, modified
    by weight ratio and identity passives. This replaces ShipType combat
    stats when a ShipBuild is active.
    """

    hull: int = 0
    armor: int = 0
    shields: int = 0
    shield_regen: int = 0
    evasion: int = 0
    speed: int = 0
    accuracy: int = 0
    energy_pool: int = 0
    energy_regen: int = 0
    cargo_capacity: int = 0
    fuel_capacity: int = 0
    crew_slots: int = 0
    weight_current: float = 0.0
    weight_max: int = 0
    weight_ratio: float = 0.0
    weight_label: str = "BALANCED"
    power_current: int = 0
    power_max: int = 0
    defensive_identity: Optional[str] = None
    combat_moves: list = field(default_factory=list)
    flee_bonus: int = 0
    special_abilities: list[str] = field(default_factory=list)
    total_cost: int = 0


# ============================================================================
# Grid Manager
# ============================================================================


class ShipGridManager:
    """Handles placement validation and grid state queries.

    All operations are stateless — they take the current build state
    as parameters and return results without side effects.
    """

    def __init__(self, weight_class: str) -> None:
        wc = WEIGHT_CLASSES.get(weight_class, WEIGHT_CLASSES["medium"])
        self._canvas_w = wc.get("canvas_w", wc.get("canvas", 32))
        self._canvas_h = wc.get("canvas_h", wc.get("canvas", 32))
        self._max_weight = wc["max_weight"]
        self._weight_class = weight_class

    def get_canvas_size(self) -> int:
        """Return the largest grid dimension (backward compat)."""
        return max(self._canvas_w, self._canvas_h)

    def get_canvas_w(self) -> int:
        return self._canvas_w

    def get_canvas_h(self) -> int:
        return self._canvas_h

    def can_place_shape(
        self,
        shape: HullShape,
        x: int,
        y: int,
        material: HullMaterial,
        existing_pixels: list[PlacedPixel],
        materials_catalog: Optional[dict[str, "HullMaterial"]] = None,
    ) -> tuple[bool, str]:
        """Check if a shape can be placed at the given position.

        Args:
            shape: The shape to place.
            x: Left column of placement.
            y: Top row of placement.
            material: Material for the new pixels.
            existing_pixels: Currently placed pixels.
            materials_catalog: Optional dict of all materials (for accurate
                weight calculation). If None, uses new material's weight
                as approximation.

        Returns:
            (success, message) tuple.
        """
        # Bounds check
        if x < 0 or y < 0:
            return False, "Position out of bounds"
        if x + shape.width > self._canvas_w or y + shape.height > self._canvas_h:
            return False, "Shape extends beyond canvas"

        # Build occupied set for fast overlap check
        occupied = {(p.x, p.y) for p in existing_pixels}

        # Check each filled pixel in the shape
        new_pixel_count = 0
        for row_idx, row in enumerate(shape.pixel_mask):
            for col_idx, filled in enumerate(row):
                if filled:
                    px, py = x + col_idx, y + row_idx
                    if (px, py) in occupied:
                        return False, f"Overlap at ({px}, {py})"
                    new_pixel_count += 1

        # Weight check — use actual material weights per pixel
        current_weight = 0.0
        for p in existing_pixels:
            if materials_catalog and p.material_id in materials_catalog:
                current_weight += materials_catalog[p.material_id].weight_per_pixel
            else:
                current_weight += material.weight_per_pixel  # Fallback approximation
        new_weight = new_pixel_count * material.weight_per_pixel
        if current_weight + new_weight > self._max_weight:
            return (
                False,
                f"Exceeds weight limit ({current_weight + new_weight:.1f}/{self._max_weight})",
            )

        return True, "OK"

    def is_area_filled(
        self,
        x: int,
        y: int,
        size: int,
        pixels: list[PlacedPixel],
    ) -> bool:
        """Check if every cell in a size×size area is filled with pixels."""
        occupied = {(p.x, p.y) for p in pixels}
        for dy in range(size):
            for dx in range(size):
                if (x + dx, y + dy) not in occupied:
                    return False
        return True

    def get_pixels_at(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        pixels: list[PlacedPixel],
    ) -> list[PlacedPixel]:
        """Get all pixels within a rectangular region."""
        return [p for p in pixels if x <= p.x < x + width and y <= p.y < y + height]

    # _get_pixel_weight removed — weight now calculated with actual material catalog


# ============================================================================
# Stats Computer
# ============================================================================


class ShipStatsComputer:
    """Derives all ship stats from a ShipBuild + material/equipment data."""

    @staticmethod
    def compute(
        build: ShipBuild,
        materials: dict[str, HullMaterial],
        equipment: Optional[dict] = None,
        module_catalog: Optional[dict] = None,
    ) -> ComputedShipStats:
        """Compute all ship stats from the build configuration.

        Args:
            build: The ship build to compute stats for.
            materials: Material definitions keyed by ID.
            equipment: Equipment/upgrade definitions keyed by ID (optional).
            module_catalog: Ship module blueprints keyed by ID (optional).

        Returns:
            ComputedShipStats with all derived values.
        """
        if equipment is None:
            equipment = {}
        if module_catalog is None:
            module_catalog = {}

        stats = ComputedShipStats()
        wc = WEIGHT_CLASSES.get(build.weight_class, WEIGHT_CLASSES["medium"])
        stats.weight_max = wc["max_weight"]

        # --- Module stat contributions (fixed stats from provides dict) ---
        for placed_mod in build.modules:
            module = module_catalog.get(placed_mod.module_id)
            if module is None:
                continue
            provides = module.provides
            stats.shields += provides.get("shield_hp", 0)
            stats.shield_regen += provides.get("shield_regen", 0)
            stats.cargo_capacity += provides.get("cargo_capacity", 0)
            stats.crew_slots += provides.get("crew_capacity", 0)
            stats.speed += provides.get("thrust", 0)
            stats.armor += provides.get("armor_bonus", 0)
            stats.fuel_capacity += provides.get("fuel_capacity", 0)
            stats.power_max += provides.get("power_output", 0)
            stats.evasion += provides.get("evasion_bonus", 0)
            stats.accuracy += provides.get("accuracy_bonus", 0)
            stats.hull += provides.get("hull_hp", 0)
            # Module weight and cost
            stats.weight_current += module.weight
            stats.total_cost += module.instantiation_cost

        # --- Hull pixel stat contributions (per-pixel material accumulation) ---
        material_counts: dict[str, int] = {}
        for pixel in build.pixels:
            mat = materials.get(pixel.material_id)
            if mat is None:
                continue
            material_counts[pixel.material_id] = material_counts.get(pixel.material_id, 0) + 1
            stats.hull += mat.hull_per_pixel
            stats.armor += mat.armor_per_pixel
            stats.shields += mat.shield_per_pixel
            stats.shield_regen += mat.shield_regen_per_pixel
            stats.evasion += mat.evasion_per_pixel
            stats.weight_current += mat.weight_per_pixel
            stats.total_cost += mat.cost_per_pixel

        # Round accumulated fractional stats
        stats.hull = int(stats.hull)
        stats.armor = int(stats.armor)
        stats.shields = int(stats.shields)
        stats.shield_regen = int(stats.shield_regen)
        stats.evasion = int(stats.evasion)

        # Weight ratio and modifiers
        if stats.weight_max > 0:
            stats.weight_ratio = stats.weight_current / stats.weight_max
        else:
            stats.weight_ratio = 0.0

        evasion_mult = 1.0
        speed_mult = 1.0
        stats.weight_label = "BALANCED"
        for max_r, min_r, label, ev_mult, sp_mult in WEIGHT_MODIFIERS:
            if min_r <= stats.weight_ratio <= max_r:
                evasion_mult = ev_mult
                speed_mult = sp_mult
                stats.weight_label = label
                break

        stats.evasion = int(stats.evasion * evasion_mult)
        stats.speed = int(stats.speed * speed_mult) if stats.speed > 0 else 0

        # Physics-based modifiers (CoM balance, frontal profile)
        if module_catalog and (build.modules or build.pixels):
            try:
                from spacegame.models.ship_physics import compute_physics_modifiers

                physics = compute_physics_modifiers(build, materials, module_catalog)
                physics_evasion_mult = physics.get("evasion_mult", 1.0)
                if physics_evasion_mult != 1.0:
                    stats.evasion = int(stats.evasion * physics_evasion_mult)
            except Exception:
                pass  # Physics computation failed gracefully (import, data, etc.)

        # Equipment contributions (from slots with installed equipment)
        for slot in build.slots:
            if slot.equipment_id and slot.equipment_id in equipment:
                upgrade = equipment[slot.equipment_id]
                if hasattr(upgrade, "combat_move") and upgrade.combat_move:
                    stats.combat_moves.append(upgrade.combat_move)

        # Slot cost
        slot_costs = {"weapon": 3000, "defense": 2500, "engine": 2000, "utility": 1500, "core": 0}
        for slot in build.slots:
            stats.total_cost += slot_costs.get(slot.slot_type, 0)

        # Defensive identity detection (hull pixels only)
        total_pixels = len(build.pixels)
        if total_pixels > 0:
            juggernaut_count = sum(material_counts.get(mid, 0) for mid in JUGGERNAUT_MATERIALS)
            sentinel_count = sum(material_counts.get(mid, 0) for mid in SENTINEL_MATERIALS)
            ghost_count = sum(material_counts.get(mid, 0) for mid in GHOST_MATERIALS)

            juggernaut_ratio = juggernaut_count / total_pixels
            sentinel_ratio = sentinel_count / total_pixels
            ghost_ratio = ghost_count / total_pixels

            best_ratio = max(juggernaut_ratio, sentinel_ratio, ghost_ratio)
            if best_ratio >= IDENTITY_THRESHOLD:
                if juggernaut_ratio == best_ratio:
                    stats.defensive_identity = "juggernaut"
                elif sentinel_ratio == best_ratio:
                    stats.defensive_identity = "sentinel"
                else:
                    stats.defensive_identity = "ghost"

        return stats
