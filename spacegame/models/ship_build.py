"""Ship builder data models and computation engine.

Pure data structures for the pixel ship designer. No pygame imports.
Handles shape definitions, material stats, grid placement validation,
stat derivation, weight modifiers, and defensive identity detection.

Part of the Shipyard Overhaul — Phase A1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

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

# Minimum hull-pixel count for a player-built ship to qualify for any
# defensive identity. Below this, the ship is too small to carry an
# archetype's thematic and mechanical weight — it's a scrap build, not a
# classified frame. A 16x16 tutorial shuttle usually lands below this
# cap even at high material-family ratios.
MIN_IDENTITY_PIXELS = 50

# Juggernaut additionally requires absolute mass. A juggernaut is a bulk
# ship — dominant, imposing, hard to dodge. A tiny 30-pixel build can't
# feel like one regardless of material composition. Sentinel (shield-
# centric) and Ghost (stealth) can scale to smaller ships, so they only
# need the general MIN_IDENTITY_PIXELS gate.
MIN_JUGGERNAUT_PIXELS = 100

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
    """A material type that determines per-pixel stats and visual appearance.

    Materials are the primary way players express defensive identity.
    Each pixel filled with a material contributes its stats to the ship.

    Visual appearance is driven by ``shade_band`` naming a canonical palette
    band (see ``engine/material_palette.py``). Render parameters tune the
    ShipComposite pipeline: rivets, wear, gloss, optional emissive overlay.
    """

    id: str
    name: str
    description: str
    shade_band: str
    category_offset: int = 0
    noise_intensity: float = 0.15
    rivet_density: float = 40.0
    wear_intensity: float = 0.10
    gloss: float = 0.30
    emissive_role: Optional[str] = None
    signature_stripe_role: Optional[str] = None
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

    @property
    def color_primary(self) -> tuple[int, int, int]:
        """Representative base color derived from the material's shade band.

        Returns the band midpoint. Prefer direct ``get_band`` access in new
        rendering code; this property exists for consumers that only need
        a single representative RGB (UI swatches, minimap pixels, etc.).
        """
        band = self._resolved_band()
        return band[len(band) // 2]

    @property
    def color_accent(self) -> tuple[int, int, int]:
        """Darker variant of the base color (one band stop below midpoint)."""
        band = self._resolved_band()
        return band[max(0, len(band) // 2 - 1)]

    @property
    def color_highlight(self) -> tuple[int, int, int]:
        """Brighter variant of the base color (one band stop above midpoint)."""
        band = self._resolved_band()
        return band[min(len(band) - 1, len(band) // 2 + 1)]

    def _resolved_band(self) -> tuple[tuple[int, int, int], ...]:
        from spacegame.engine.material_palette import apply_category_offset, get_band, is_valid_band

        if not is_valid_band(self.shade_band):
            return ((90, 90, 100), (128, 128, 140), (160, 160, 180))
        band = get_band(self.shade_band)
        if self.category_offset:
            band = apply_category_offset(band, self.category_offset)
        return band

    def to_dict(self) -> dict:
        """Serialize material to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "shade_band": self.shade_band,
            "category_offset": self.category_offset,
            "noise_intensity": self.noise_intensity,
            "rivet_density": self.rivet_density,
            "wear_intensity": self.wear_intensity,
            "gloss": self.gloss,
            "emissive_role": self.emissive_role,
            "signature_stripe_role": self.signature_stripe_role,
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
            shade_band=data["shade_band"],
            category_offset=data.get("category_offset", 0),
            noise_intensity=data.get("noise_intensity", 0.15),
            rivet_density=data.get("rivet_density", 40.0),
            wear_intensity=data.get("wear_intensity", 0.10),
            gloss=data.get("gloss", 0.30),
            emissive_role=data.get("emissive_role"),
            signature_stripe_role=data.get("signature_stripe_role"),
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
class PlacedSlot:
    """A slot placed on the ship's pixel grid.

    Represents a typed/sized slot at a specific grid position. The slot
    is a placeholder — the actual equipment is referenced by equipped_part_id
    and managed through the Loadout tab.

    Attributes:
        slot_def_id: References a SlotDefinition.id (e.g., "weapon_small").
        x: Grid column of the top-left corner.
        y: Grid row of the top-left corner.
        rotation: Placement rotation (0, 90, 180, 270).
        equipped_part_id: ID of the ShipPart installed, or None if empty.
    """

    slot_def_id: str
    x: int
    y: int
    rotation: int = 0
    equipped_part_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        d: dict = {
            "slot_def_id": self.slot_def_id,
            "x": self.x,
            "y": self.y,
        }
        if self.rotation != 0:
            d["rotation"] = self.rotation
        if self.equipped_part_id:
            d["equipped_part_id"] = self.equipped_part_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PlacedSlot":
        """Deserialize from a dict."""
        return cls(
            slot_def_id=data["slot_def_id"],
            x=data["x"],
            y=data["y"],
            rotation=data.get("rotation", 0),
            equipped_part_id=data.get("equipped_part_id"),
        )


# DEPRECATED: Per-weight-class slot limits. Superseded by per-frame
# FrameRequirements (loaded from ship_types.json frame_requirements).
# Kept as fallback for builds without ship_type_id (legacy saves).
FRAME_SLOT_LIMITS: dict[str, dict[str, int]] = {
    "tiny": {
        "cockpit": 1,
        "weapon": 1,
        "defense": 1,
        "engine": 1,
        "utility": 2,
        "fuel": 1,
        "cargo": 2,
        "crew_quarters": 1,
        "reactor": 1,
    },
    "small": {
        "cockpit": 1,
        "weapon": 2,
        "defense": 1,
        "engine": 1,
        "utility": 2,
        "fuel": 1,
        "cargo": 3,
        "crew_quarters": 1,
        "reactor": 1,
    },
    "medium": {
        "cockpit": 1,
        "weapon": 3,
        "defense": 2,
        "engine": 2,
        "utility": 3,
        "fuel": 2,
        "cargo": 4,
        "crew_quarters": 2,
        "reactor": 1,
    },
    "large": {
        "cockpit": 1,
        "weapon": 4,
        "defense": 3,
        "engine": 2,
        "utility": 4,
        "fuel": 2,
        "cargo": 5,
        "crew_quarters": 3,
        "reactor": 2,
    },
    "xlarge": {
        "cockpit": 1,
        "weapon": 5,
        "defense": 3,
        "engine": 3,
        "utility": 4,
        "fuel": 3,
        "cargo": 6,
        "crew_quarters": 3,
        "reactor": 2,
    },
}

# Ship class → weight class mapping (used by FrameRequirements.from_ship_type)
_CLASS_TO_WEIGHT: dict[str, str] = {
    "starter": "tiny",
    "early_game": "small",
    "mid_game": "medium",
    "late_game": "large",
    "faction": "large",
}

# Infrastructure minimum defaults by weight class (for fallback generation)
_INFRA_MINS: dict[str, dict[str, dict[str, int | str]]] = {
    "tiny": {
        "cockpit": {"min": 1, "min_size": "small"},
        "engine": {"min": 1, "min_size": "small"},
        "fuel": {"min": 1, "min_size": "small"},
        "reactor": {"min": 1, "min_size": "small"},
        "crew_quarters": {"min": 0, "min_size": "small"},
    },
    "small": {
        "cockpit": {"min": 1, "min_size": "small"},
        "engine": {"min": 1, "min_size": "small"},
        "fuel": {"min": 1, "min_size": "small"},
        "reactor": {"min": 1, "min_size": "small"},
        "crew_quarters": {"min": 0, "min_size": "small"},
    },
    "medium": {
        "cockpit": {"min": 1, "min_size": "small"},
        "engine": {"min": 1, "min_size": "medium"},
        "fuel": {"min": 1, "min_size": "small"},
        "reactor": {"min": 1, "min_size": "small"},
        "crew_quarters": {"min": 1, "min_size": "small"},
    },
    "large": {
        "cockpit": {"min": 1, "min_size": "medium"},
        "engine": {"min": 2, "min_size": "medium"},
        "fuel": {"min": 1, "min_size": "medium"},
        "reactor": {"min": 1, "min_size": "small"},
        "crew_quarters": {"min": 1, "min_size": "small"},
    },
    "xlarge": {
        "cockpit": {"min": 1, "min_size": "medium"},
        "engine": {"min": 2, "min_size": "large"},
        "fuel": {"min": 2, "min_size": "medium"},
        "reactor": {"min": 2, "min_size": "small"},
        "crew_quarters": {"min": 2, "min_size": "small"},
    },
}

_SIZE_ORDER: dict[str, int] = {"small": 0, "medium": 1, "large": 2}


@dataclass
class FrameRequirements:
    """Per-frame slot requirements with min/max/min_size per slot type.

    Each slot type entry is a dict with keys:
        min: int — minimum slots required for flight readiness
        max: int — maximum slots the frame supports
        min_size: str — smallest acceptable slot size ("small"/"medium"/"large")
    """

    requirements: dict[str, dict[str, int | str]]

    def get_min(self, slot_type: str) -> int:
        """Return minimum required count for a slot type."""
        spec = self.requirements.get(slot_type)
        if spec is None:
            return 0
        return int(spec.get("min", 0))

    def get_max(self, slot_type: str) -> int:
        """Return maximum allowed count for a slot type."""
        spec = self.requirements.get(slot_type)
        if spec is None:
            return 0
        return int(spec.get("max", 0))

    def get_min_size(self, slot_type: str) -> str:
        """Return minimum acceptable slot size for a slot type."""
        spec = self.requirements.get(slot_type)
        if spec is None:
            return "small"
        return str(spec.get("min_size", "small"))

    def is_slot_size_valid(self, slot_type: str, slot_size: str) -> bool:
        """Check if a slot size meets the minimum size requirement.

        Args:
            slot_type: The slot category (e.g., "engine").
            slot_size: The slot's size ("small", "medium", "large").

        Returns:
            True if slot_size >= min_size for this slot type.
        """
        min_size = self.get_min_size(slot_type)
        return _SIZE_ORDER.get(slot_size, 0) >= _SIZE_ORDER.get(min_size, 0)

    def check_flight_ready(
        self,
        slot_counts: dict[str, int],
        slot_sizes: dict[str, list[str]],
    ) -> tuple[bool, list[str]]:
        """Check if a build meets all minimum requirements for flight.

        Args:
            slot_counts: Count of placed slots per type (e.g., {"engine": 2}).
            slot_sizes: List of sizes per type (e.g., {"engine": ["medium", "large"]}).

        Returns:
            Tuple of (is_ready, list_of_failure_reasons).
        """
        reasons: list[str] = []
        for slot_type, spec in self.requirements.items():
            min_count = int(spec.get("min", 0))
            if min_count == 0:
                continue
            actual = slot_counts.get(slot_type, 0)
            if actual < min_count:
                reasons.append(f"{slot_type}: need {min_count}, have {actual}")
                continue
            # Check size constraint on placed slots
            min_size = str(spec.get("min_size", "small"))
            sizes = slot_sizes.get(slot_type, [])
            valid_count = sum(
                1 for s in sizes if _SIZE_ORDER.get(s, 0) >= _SIZE_ORDER.get(min_size, 0)
            )
            if valid_count < min_count:
                reasons.append(
                    f"{slot_type}: need {min_count} at size {min_size}+, only {valid_count} qualify"
                )
        return (len(reasons) == 0, reasons)

    @classmethod
    def from_ship_type(cls, ship_type: object) -> FrameRequirements:
        """Create FrameRequirements from a ShipType instance.

        Falls back to weight-class defaults if the ShipType has no
        frame_requirements field or it's empty.

        Args:
            ship_type: ShipType with optional frame_requirements dict.

        Returns:
            FrameRequirements instance.
        """
        reqs = getattr(ship_type, "frame_requirements", {})
        if reqs:
            return cls(reqs)
        # Fallback: derive from weight class
        ship_class = getattr(ship_type, "ship_class", "")
        weight_class = _CLASS_TO_WEIGHT.get(ship_class, "small")
        return cls.fallback_from_weight_class(weight_class)

    @classmethod
    def fallback_from_weight_class(cls, weight_class: str) -> FrameRequirements:
        """Generate FrameRequirements from FRAME_SLOT_LIMITS for legacy builds.

        Uses the weight-class slot limits as maximums and infrastructure
        defaults as minimums.

        Args:
            weight_class: Weight class string (tiny/small/medium/large/xlarge).

        Returns:
            FrameRequirements with reasonable defaults.
        """
        limits = FRAME_SLOT_LIMITS.get(weight_class, {})
        infra = _INFRA_MINS.get(weight_class, _INFRA_MINS.get("small", {}))
        reqs: dict[str, dict[str, int | str]] = {}
        for slot_type, max_val in limits.items():
            infra_spec = infra.get(slot_type, {})
            reqs[slot_type] = {
                "min": infra_spec.get("min", 0),
                "max": max_val,
                "min_size": infra_spec.get("min_size", "small"),
            }
        return cls(reqs)


@dataclass
class ShipBuild:
    """Complete ship configuration -- the central data structure.

    A ShipBuild defines everything about a player's ship: the weight
    class (canvas size), every filled pixel with its material, and
    every placed slot with optional equipped parts.
    """

    weight_class: str
    pixels: list[PlacedPixel] = field(default_factory=list)
    preset_name: Optional[str] = None
    frame_variant: Optional[str] = None
    placed_slots: list[PlacedSlot] = field(default_factory=list)
    ship_type_id: Optional[str] = None

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
        """Serialize build to dict."""
        result: dict = {
            "weight_class": self.weight_class,
            "pixels": [p.to_dict() for p in self.pixels],
            "preset_name": self.preset_name,
        }
        if self.placed_slots:
            result["placed_slots"] = [ps.to_dict() for ps in self.placed_slots]
        if self.frame_variant:
            result["frame_variant"] = self.frame_variant
        if self.ship_type_id:
            result["ship_type_id"] = self.ship_type_id
        return result

    @classmethod
    def from_dict(cls, data: dict) -> ShipBuild:
        """Restore build from dict."""
        placed_slots = [PlacedSlot.from_dict(ps) for ps in data.get("placed_slots", [])]
        return cls(
            weight_class=data["weight_class"],
            pixels=[PlacedPixel.from_dict(p) for p in data.get("pixels", [])],
            preset_name=data.get("preset_name"),
            frame_variant=data.get("frame_variant"),
            placed_slots=placed_slots,
            ship_type_id=data.get("ship_type_id"),
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
        slot_definitions: Optional[dict] = None,
        parts_catalog: Optional[dict] = None,
        ship_type: Optional[object] = None,
    ) -> ComputedShipStats:
        """Compute all ship stats from the build configuration.

        Supports both the new slot+part model (placed_slots) and the
        legacy module model (modules). If placed_slots is populated,
        stats come from slot definitions + equipped parts. Otherwise
        falls back to the module path.

        When ship_type is provided, the frame's base stats (cargo, fuel,
        hull, shields, speed, evasion) are included as a foundation.
        Parts add on top of these base values.

        Args:
            build: The ship build to compute stats for.
            materials: Material definitions keyed by ID.
            equipment: Equipment/upgrade definitions keyed by ID (optional).
            module_catalog: Ship module blueprints keyed by ID (optional).
            slot_definitions: SlotDefinition catalog keyed by ID (optional).
            parts_catalog: ShipPart catalog keyed by ID (optional).
            ship_type: ShipType for frame base stats (optional).

        Returns:
            ComputedShipStats with all derived values.
        """
        if equipment is None:
            equipment = {}
        if module_catalog is None:
            module_catalog = {}
        if slot_definitions is None:
            slot_definitions = {}
        if parts_catalog is None:
            parts_catalog = {}

        stats = ComputedShipStats()
        wc = WEIGHT_CLASSES.get(build.weight_class, WEIGHT_CLASSES["medium"])
        stats.weight_max = wc["max_weight"]

        # --- Frame base stats (from ShipType) ---
        # The frame provides baseline capabilities; parts enhance them.
        if ship_type is not None:
            stats.cargo_capacity += getattr(ship_type, "cargo_capacity", 0)
            stats.fuel_capacity += getattr(ship_type, "fuel_capacity", 0)
            stats.hull += getattr(ship_type, "combat_hull", 0)
            stats.shields += getattr(ship_type, "combat_shields", 0)
            stats.speed += getattr(ship_type, "combat_speed", 0)
            stats.evasion += getattr(ship_type, "combat_evasion", 0)
            stats.energy_pool += getattr(ship_type, "combat_energy", 0)
            stats.energy_regen += getattr(ship_type, "combat_energy_regen", 0)
            stats.accuracy += getattr(ship_type, "combat_accuracy", 0)

        # --- NEW: Slot + Part stat contributions ---
        if build.placed_slots:
            for placed_slot in build.placed_slots:
                # Slot itself contributes weight and cost
                slot_def = slot_definitions.get(placed_slot.slot_def_id)
                if slot_def:
                    stats.weight_current += slot_def.weight
                    stats.total_cost += slot_def.placement_cost

                # Equipped part contributes stats
                if placed_slot.equipped_part_id:
                    part = parts_catalog.get(placed_slot.equipped_part_id)
                    if part:
                        provides = part.provides
                        stats.shields += provides.get("shield_hp", 0)
                        stats.shield_regen += provides.get("shield_regen", 0)
                        stats.cargo_capacity += provides.get("cargo_capacity", 0)
                        stats.crew_slots += provides.get("crew_capacity", 0)
                        stats.speed += provides.get("thrust", 0)
                        stats.armor += provides.get("armor_bonus", 0)
                        stats.fuel_capacity += provides.get("fuel_capacity", 0)
                        stats.power_max += provides.get("power_output", 0)
                        stats.energy_pool += provides.get("power_output", 0)
                        stats.energy_regen += provides.get("energy_regen", 0)
                        stats.evasion += provides.get("evasion_bonus", 0)
                        stats.accuracy += provides.get("accuracy_bonus", 0)
                        stats.hull += provides.get("hull_hp", 0)
                        stats.weight_current += part.weight
                        stats.total_cost += part.base_cost

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
        if module_catalog and build.pixels:
            try:
                from spacegame.models.ship_physics import compute_physics_modifiers

                physics = compute_physics_modifiers(build, materials, module_catalog)
                physics_evasion_mult = physics.get("evasion_mult", 1.0)
                if physics_evasion_mult != 1.0:
                    stats.evasion = int(stats.evasion * physics_evasion_mult)
            except Exception:
                pass  # Physics computation failed gracefully (import, data, etc.)

        # Defensive identity detection (hull pixels only).
        # Gated by MIN_IDENTITY_PIXELS: a tiny scrap build does not
        # inherit an archetype label, because at that scale the identity
        # framing (and the mechanical bonuses downstream in combat_engine)
        # is thematically wrong. Juggernaut carries an extra size gate via
        # MIN_JUGGERNAUT_PIXELS since "juggernaut" implies bulk.
        total_pixels = len(build.pixels)
        if total_pixels >= MIN_IDENTITY_PIXELS:
            juggernaut_count = sum(material_counts.get(mid, 0) for mid in JUGGERNAUT_MATERIALS)
            sentinel_count = sum(material_counts.get(mid, 0) for mid in SENTINEL_MATERIALS)
            ghost_count = sum(material_counts.get(mid, 0) for mid in GHOST_MATERIALS)

            juggernaut_ratio = juggernaut_count / total_pixels
            sentinel_ratio = sentinel_count / total_pixels
            ghost_ratio = ghost_count / total_pixels

            best_ratio = max(juggernaut_ratio, sentinel_ratio, ghost_ratio)
            if best_ratio >= IDENTITY_THRESHOLD:
                if juggernaut_ratio == best_ratio:
                    # Extra bulk gate for juggernaut: tiny ships don't
                    # qualify even at high armor-material ratios.
                    if juggernaut_count >= MIN_JUGGERNAUT_PIXELS:
                        stats.defensive_identity = "juggernaut"
                elif sentinel_ratio == best_ratio:
                    stats.defensive_identity = "sentinel"
                else:
                    stats.defensive_identity = "ghost"

        return stats
