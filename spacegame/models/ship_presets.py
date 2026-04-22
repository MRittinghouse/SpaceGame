"""Ship preset generation — converts legacy ShipTypes into ShipBuilds.

Algorithmically generates a ShipBuild from a ShipType's stats by
mapping hull → hull materials, shields → shield materials, evasion →
light materials, and placing pixels in a recognizable ship silhouette.

Part of Shipyard Overhaul Phase A3.
"""

from __future__ import annotations

import math
from typing import Optional

from spacegame.models.ship_build import (
    WEIGHT_CLASSES,
    HullMaterial,
    PlacedPixel,
    ShipBuild,
)

# Materials used for preset generation (these may not all be in the
# starter JSON — presets represent pre-built ships with full access)
_PRESET_MATERIALS: dict[str, HullMaterial] = {
    "standard_plate": HullMaterial(
        id="standard_plate",
        name="Standard Plate",
        description="Balanced",
        shade_band="steel",
        hull_per_pixel=2.5,
        weight_per_pixel=0.25,
        cost_per_pixel=15,
    ),
    "light_alloy": HullMaterial(
        id="light_alloy",
        name="Light Alloy",
        description="Light",
        shade_band="steel",
        hull_per_pixel=1.5,
        evasion_per_pixel=0.08,
        weight_per_pixel=0.15,
        cost_per_pixel=8,
    ),
    "shield_crystal": HullMaterial(
        id="shield_crystal",
        name="Shield Crystal",
        description="Shields",
        shade_band="collective_composite",
        emissive_role="cryo_fractal",
        hull_per_pixel=1.0,
        shield_per_pixel=0.6,
        shield_regen_per_pixel=0.03,
        weight_per_pixel=0.30,
        cost_per_pixel=22,
    ),
    "heavy_armor": HullMaterial(
        id="heavy_armor",
        name="Heavy Armor",
        description="Armor",
        shade_band="union_ceramic",
        category_offset=1,
        hull_per_pixel=3.0,
        armor_per_pixel=0.06,
        weight_per_pixel=0.55,
        cost_per_pixel=25,
    ),
    "salvage_scrap": HullMaterial(
        id="salvage_scrap",
        name="Salvage Scrap",
        description="Cheap",
        shade_band="frontier_canvas",
        hull_per_pixel=2.0,
        armor_per_pixel=0.02,
        weight_per_pixel=0.20,
        cost_per_pixel=5,
    ),
}


def _select_weight_class(ship_type: object) -> str:
    """Pick an appropriate weight class for a ship type based on its stats.

    Args:
        ship_type: ShipType with combat_hull, combat_shields, cargo_capacity.

    Returns:
        Weight class string.
    """
    total_hp = ship_type.combat_hull + ship_type.combat_shields
    cargo = ship_type.cargo_capacity

    if total_hp <= 100 and cargo <= 60:
        return "tiny"
    elif total_hp <= 180 and cargo <= 150:
        return "small"
    elif total_hp <= 300 and cargo <= 300:
        return "medium"
    elif total_hp <= 500:
        return "large"
    return "xlarge"


def _compute_pixel_counts(
    ship_type: object,
    weight_class: str,
) -> dict[str, int]:
    """Determine how many pixels of each material to place.

    Maps hull → standard_plate/heavy_armor, shields → shield_crystal,
    evasion → light_alloy. Balances pixel counts against the weight
    class's weight limit.

    Args:
        ship_type: ShipType with combat stats.
        weight_class: The chosen weight class.

    Returns:
        Dict of material_id → pixel count.
    """
    max_weight = WEIGHT_CLASSES[weight_class]["max_weight"]

    target_hull = ship_type.combat_hull
    target_shields = ship_type.combat_shields
    target_evasion = ship_type.combat_evasion
    identity = getattr(ship_type, "defensive_identity", "")

    # Calculate pixel counts to approximate target stats
    # Shield pixels (each gives 0.6 shields + 1.0 hull)
    shield_pixels = int(target_shields / 0.6) if target_shields > 0 else 0
    hull_from_shields = shield_pixels * 1.0

    # Evasion pixels (each gives 0.08 evasion + 1.5 hull)
    # Only use light_alloy if the ship has notable evasion
    evasion_pixels = 0
    if target_evasion > 15:
        # Scale evasion pixels conservatively — weight system provides bonus too
        evasion_pixels = min(
            int(target_evasion / 0.08 * 0.2),
            int(target_hull * 0.3 / 1.5),  # Cap at 30% of target hull contribution
        )
    hull_from_evasion = evasion_pixels * 1.5

    # Remaining hull from standard plate or heavy armor
    remaining_hull = max(0, target_hull - hull_from_shields - hull_from_evasion)

    if identity == "juggernaut":
        # Use heavy armor for hull ships
        armor_pixels = int(remaining_hull / 3.0)
        standard_pixels = max(5, int(remaining_hull * 0.1 / 2.5))  # Small amount of standard
        heavy_pixels = armor_pixels
    else:
        heavy_pixels = 0
        standard_pixels = int(remaining_hull / 2.5)

    # Check total weight and scale down if needed
    total_weight = (
        standard_pixels * 0.7 + shield_pixels * 0.6 + evasion_pixels * 0.4 + heavy_pixels * 1.2
    )

    if total_weight > max_weight * 0.95:
        scale = (max_weight * 0.90) / total_weight
        standard_pixels = int(standard_pixels * scale)
        shield_pixels = int(shield_pixels * scale)
        evasion_pixels = int(evasion_pixels * scale)
        heavy_pixels = int(heavy_pixels * scale)

    # Ensure at least some pixels
    if standard_pixels + shield_pixels + evasion_pixels + heavy_pixels < 10:
        standard_pixels = max(standard_pixels, 10)

    counts: dict[str, int] = {}
    if standard_pixels > 0:
        counts["standard_plate"] = standard_pixels
    if shield_pixels > 0:
        counts["shield_crystal"] = shield_pixels
    if evasion_pixels > 0:
        counts["light_alloy"] = evasion_pixels
    if heavy_pixels > 0:
        counts["heavy_armor"] = heavy_pixels
    return counts


def _place_pixels_in_silhouette(
    pixel_counts: dict[str, int],
    canvas_w: int,
    canvas_h: int = 0,
) -> list[PlacedPixel]:
    """Place pixels in a simple ship-like silhouette.

    Creates a diamond/dart shape centered on the canvas, filling
    from the center outward. Different materials are layered:
    hull materials at the core, shields around them, light alloy
    at the edges.

    Args:
        pixel_counts: Material → count mapping.
        canvas_w: Grid width.
        canvas_h: Grid height (defaults to canvas_w if 0).

    Returns:
        List of placed pixels forming the ship silhouette.
    """
    if canvas_h <= 0:
        canvas_h = canvas_w
    cx = canvas_w // 2
    cy = canvas_h // 2
    total = sum(pixel_counts.values())

    # Generate a ship-like shape: sorted positions by distance from center
    # within an elliptical boundary (wider than tall, like a ship)
    candidates: list[tuple[float, int, int]] = []
    for y in range(canvas_h):
        for x in range(canvas_w):
            dx = (x - cx) / (canvas_w * 0.4)  # Wider
            dy = (y - cy) / (canvas_h * 0.35)  # Taller aspect
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= 1.0:
                candidates.append((dist, x, y))

    # Sort by distance from center (fill from inside out)
    candidates.sort(key=lambda c: c[0])

    # Take only as many positions as we need
    positions = [(x, y) for _, x, y in candidates[:total]]

    # Assign materials: core materials first, edge materials last
    pixels: list[PlacedPixel] = []
    idx = 0

    # Core: heavy armor or standard plate
    for mat_id in ["heavy_armor", "standard_plate", "salvage_scrap"]:
        count = pixel_counts.get(mat_id, 0)
        for _ in range(count):
            if idx < len(positions):
                x, y = positions[idx]
                pixels.append(PlacedPixel(x, y, mat_id))
                idx += 1

    # Middle: shield crystal
    for _ in range(pixel_counts.get("shield_crystal", 0)):
        if idx < len(positions):
            x, y = positions[idx]
            pixels.append(PlacedPixel(x, y, "shield_crystal"))
            idx += 1

    # Edge: light alloy
    for _ in range(pixel_counts.get("light_alloy", 0)):
        if idx < len(positions):
            x, y = positions[idx]
            pixels.append(PlacedPixel(x, y, "light_alloy"))
            idx += 1

    return pixels


# Default slot definition IDs by (slot_type, size).
# Presets use these as the standard variant for each type/size combo.
_SLOT_DEF_IDS: dict[tuple[str, str], tuple[str, int, int]] = {
    # (slot_type, size) → (slot_def_id, footprint_w, footprint_h)
    ("cockpit", "small"): ("cockpit_scout_pod", 2, 2),
    ("cockpit", "medium"): ("cockpit_command_bridge", 3, 3),
    ("cockpit", "large"): ("cockpit_capital_bridge", 4, 4),
    ("engine", "small"): ("engine_small", 2, 3),
    ("engine", "medium"): ("engine_medium", 3, 4),
    ("engine", "large"): ("engine_large", 4, 5),
    ("reactor", "small"): ("reactor_small", 2, 2),
    ("reactor", "medium"): ("reactor_medium", 3, 3),
    ("reactor", "large"): ("reactor_large", 4, 4),
    ("fuel", "small"): ("fuel_small", 2, 2),
    ("fuel", "medium"): ("fuel_medium", 3, 3),
    ("fuel", "large"): ("fuel_large", 4, 4),
    ("weapon", "small"): ("weapon_small", 2, 2),
    ("weapon", "medium"): ("weapon_medium", 3, 3),
    ("weapon", "large"): ("weapon_large", 4, 4),
    ("defense", "small"): ("defense_small", 2, 2),
    ("defense", "medium"): ("defense_medium", 3, 3),
    ("defense", "large"): ("defense_large", 4, 4),
    ("utility", "small"): ("utility_small", 2, 2),
    ("utility", "medium"): ("utility_medium", 3, 3),
    ("utility", "large"): ("utility_large", 4, 4),
    ("cargo", "small"): ("cargo_small", 2, 3),
    ("cargo", "medium"): ("cargo_medium", 3, 4),
    ("cargo", "large"): ("cargo_large", 4, 6),
    ("crew_quarters", "small"): ("crew_quarters_small", 2, 2),
    ("crew_quarters", "medium"): ("crew_quarters_medium", 3, 3),
    ("crew_quarters", "large"): ("crew_quarters_large", 4, 4),
}


def _select_slot_def(slot_type: str, min_size: str, weight_class: str) -> tuple[str, int, int]:
    """Pick an appropriate slot definition for a preset build.

    Uses the frame's min_size requirement and the ship's weight class
    to select a sensible default slot variant.

    Args:
        slot_type: Slot category (e.g., "engine").
        min_size: Minimum required size from frame_requirements.
        weight_class: Ship's weight class.

    Returns:
        Tuple of (slot_def_id, footprint_w, footprint_h).
    """
    # Use min_size as the target — it's what the frame requires
    key = (slot_type, min_size)
    if key in _SLOT_DEF_IDS:
        return _SLOT_DEF_IDS[key]
    # Fall back to small if min_size variant not found
    key = (slot_type, "small")
    if key in _SLOT_DEF_IDS:
        return _SLOT_DEF_IDS[key]
    # Last resort
    return (f"{slot_type}_small", 2, 2)


def _generate_placed_slots(
    ship_type: object,
    pixels: list[PlacedPixel],
    canvas_w: int,
    canvas_h: int,
) -> list:
    """Generate PlacedSlot objects from a ShipType's frame_requirements.

    Uses frame_requirements to determine slot counts and sizes, falling
    back to legacy weapon_slots/defense_slots/utility_slots if no
    frame_requirements are defined.

    Args:
        ship_type: ShipType with frame_requirements (or legacy slot fields).
        pixels: Placed hull pixels (slots need filled area underneath).
        canvas_w: Grid width.
        canvas_h: Grid height.

    Returns:
        List of PlacedSlot objects.
    """
    from spacegame.models.ship_build import FrameRequirements, PlacedSlot

    placed: list = []
    occupied_rects: list[tuple[int, int, int, int]] = []  # (x, y, w, h)
    filled = {(p.x, p.y) for p in pixels}

    frame_reqs = getattr(ship_type, "frame_requirements", {})
    weight_class = _select_weight_class(ship_type)

    if frame_reqs:
        reqs = FrameRequirements(frame_reqs)
        # Build slot plan from frame_requirements
        # For presets: place min count for infrastructure, reasonable defaults for equipment
        slot_plan: list[tuple[str, int, int, int]] = []
        infra_types = ["cockpit", "engine", "fuel", "reactor", "crew_quarters"]
        equip_types = ["weapon", "defense", "utility", "cargo"]

        for slot_type in infra_types:
            mn = reqs.get_min(slot_type)
            if mn > 0:
                min_size = reqs.get_min_size(slot_type)
                def_id, fw, fh = _select_slot_def(slot_type, min_size, weight_class)
                slot_plan.append((def_id, fw, fh, mn))

        for slot_type in equip_types:
            mx = reqs.get_max(slot_type)
            if mx > 0:
                # Presets leave 1 slot free for player customization
                # when the max allows it. Minimum 1 placed for combat types.
                if slot_type in ("weapon", "defense"):
                    count = max(1, mx - 1)
                elif slot_type == "cargo":
                    count = max(1, mx // 2)
                else:
                    count = max(0, mx - 1)
                min_size = reqs.get_min_size(slot_type)
                def_id, fw, fh = _select_slot_def(slot_type, min_size, weight_class)
                slot_plan.append((def_id, fw, fh, count))
    else:
        # Legacy fallback: use hardcoded slot counts
        slot_plan = [
            ("cockpit_scout_pod", 2, 2, 1),
            ("engine_small", 2, 3, max(1, getattr(ship_type, "utility_slots", 2) // 3)),
            ("reactor_small", 2, 2, 1),
            ("fuel_small", 2, 2, 1),
            ("weapon_small", 2, 2, getattr(ship_type, "weapon_slots", 1)),
            ("defense_small", 2, 2, getattr(ship_type, "defense_slots", 1)),
            ("cargo_small", 2, 3, max(1, getattr(ship_type, "cargo_capacity", 50) // 80)),
            ("utility_small", 2, 2, max(0, getattr(ship_type, "utility_slots", 2) - 1)),
            ("crew_quarters_small", 2, 2, 1),
        ]

    def _find_position(fw: int, fh: int, prefer_rear: bool = False) -> Optional[tuple[int, int]]:
        cx, cy = canvas_w // 2, canvas_h // 2
        best = None
        best_dist = float("inf")

        y_range = range(canvas_h - fh, -1, -1) if prefer_rear else range(canvas_h - fh + 1)
        for y in y_range:
            for x in range(canvas_w - fw + 1):
                # Check footprint cells are filled
                if not all((x + dx, y + dy) in filled for dx in range(fw) for dy in range(fh)):
                    continue
                # No overlap with existing placed slots
                if any(
                    x < rx + rw and x + fw > rx and y < ry + rh and y + fh > ry
                    for rx, ry, rw, rh in occupied_rects
                ):
                    continue
                dist = abs(x + fw // 2 - cx) + abs(y + fh // 2 - cy)
                if prefer_rear:
                    dist = -(y)
                if dist < best_dist:
                    best_dist = dist
                    best = (x, y)
                    if prefer_rear:
                        return best
        return best

    for slot_def_id, fw, fh, count in slot_plan:
        prefer_rear = "engine" in slot_def_id
        for _ in range(count):
            pos = _find_position(fw, fh, prefer_rear=prefer_rear)
            if pos:
                placed.append(PlacedSlot(slot_def_id=slot_def_id, x=pos[0], y=pos[1]))
                occupied_rects.append((pos[0], pos[1], fw, fh))

    return placed


def generate_preset_from_ship_type(
    ship_type: object,
    materials: Optional[dict[str, HullMaterial]] = None,
) -> ShipBuild:
    """Generate a preset ShipBuild from a legacy ShipType.

    Creates a build that approximates the ShipType's combat stats
    using the available materials. The build uses an algorithmically
    generated ship silhouette with appropriate material distribution.
    Includes PlacedSlots for the Loadout tab.

    Args:
        ship_type: ShipType with all combat and slot fields.
        materials: Material catalog. Defaults to preset materials.

    Returns:
        A ShipBuild that approximates the ship's original stats.
    """
    if materials is None:
        materials = _PRESET_MATERIALS

    weight_class = _select_weight_class(ship_type)
    wc = WEIGHT_CLASSES[weight_class]
    canvas_w = wc.get("canvas_w", wc.get("canvas", 32))
    canvas_h = wc.get("canvas_h", wc.get("canvas", 32))

    pixel_counts = _compute_pixel_counts(ship_type, weight_class)
    pixels = _place_pixels_in_silhouette(pixel_counts, canvas_w, canvas_h)
    placed_slots = _generate_placed_slots(ship_type, pixels, canvas_w, canvas_h)

    return ShipBuild(
        weight_class=weight_class,
        pixels=pixels,
        preset_name=ship_type.name,
        placed_slots=placed_slots,
        ship_type_id=getattr(ship_type, "id", None),
    )


def get_preset_for_ship_type(
    ship_type_id: str,
    ship_types: Optional[dict] = None,
) -> Optional[ShipBuild]:
    """Get or generate a preset build for a legacy ship type.

    Args:
        ship_type_id: The ShipType ID to generate a preset for.
        ship_types: Ship type registry. If None, uses DataLoader.

    Returns:
        ShipBuild preset, or None if ship type not found.
    """
    if ship_types is None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        ship_types = dl.ship_types

    ship_type = ship_types.get(ship_type_id)
    if ship_type is None:
        return None

    return generate_preset_from_ship_type(ship_type)
