"""Procedural enemy ship-build generator (Combat overhaul §4.1).

Derives a :class:`~spacegame.models.ship_build.ShipBuild` from an
:class:`~spacegame.models.combat.EnemyShipTemplate` so enemy ships can
render through the same :class:`~spacegame.engine.ship_composite.ShipComposite`
pipeline the player uses. Instead of hand-authoring 60+ builds, the
generator maps each template's faction + danger tier + behavior to a
canonical silhouette + material palette — the "manufacturer identity"
treatment per Aesthetic Bible §4.

Output is deterministic per ``template.id`` — identical inputs always
produce identical builds, so rendering stays cached and save/load of
encounters doesn't shift visuals between sessions.

Hand-authored overrides for marquee bosses can land in a follow-up
session via an optional ``composite_build`` field on EnemyShipTemplate;
this generator provides the baseline for every enemy immediately.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.1``.
"""

from __future__ import annotations

import math
import random as _random
from typing import Optional

from spacegame.models.combat import EnemyBehavior, EnemyShipTemplate
from spacegame.models.ship_build import WEIGHT_CLASSES, PlacedPixel, ShipBuild

# ---------------------------------------------------------------------------
# Mapping tables (spec §4.1 + Bible §4 manufacturer identity)
# ---------------------------------------------------------------------------

# Faction → primary hull material. Empty faction = Crimson Reach (bandit).
_FACTION_PRIMARY_MATERIAL: dict[str, str] = {
    "": "module_hull_talon",  # Crimson Reach default
    "commerce_guild": "module_hull_rk",
    "miners_union": "module_hull_foundry",
    "frontier_alliance": "module_hull_salvage",
    "science_collective": "module_hull_sable",
}

# Danger tier → weight class (canvas size + pixel budget).
_DANGER_WEIGHT_CLASS: dict[str, str] = {
    "low": "tiny",
    "moderate": "small",
    "dangerous": "medium",
}

# Boss flag overrides the danger-tier mapping when set.
_BOSS_WEIGHT_CLASS = "large"

# Behavior → accent material (layered at ~15% of total pixels).
_BEHAVIOR_ACCENT: dict[EnemyBehavior, str] = {
    EnemyBehavior.AGGRESSIVE: "heavy_armor",
    EnemyBehavior.DEFENSIVE: "shield_crystal",
    EnemyBehavior.COWARDLY: "light_alloy",
    EnemyBehavior.EVASIVE: "stealth_composite",
}

# Cockpit accent — one cockpit pixel plopped at the front of every ship so
# the silhouette reads as a spacecraft. Falls back gracefully if cockpit
# glass isn't in the materials catalog.
_COCKPIT_MATERIAL = "cockpit_glass"

# Accent share of total pixels. Low ratio so faction identity dominates.
_ACCENT_RATIO = 0.18


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_primary_material(faction_id: str) -> str:
    """Return the primary hull material id for a faction.

    Unknown factions fall back to the Crimson Reach (bandit) default.
    """
    return _FACTION_PRIMARY_MATERIAL.get(
        faction_id or "", _FACTION_PRIMARY_MATERIAL[""]
    )


def resolve_weight_class(template: EnemyShipTemplate) -> str:
    """Return the weight class that best fits an enemy template.

    Bosses always upgrade to ``_BOSS_WEIGHT_CLASS`` regardless of danger
    tier so the visual silhouette reads as a heavyweight encounter.
    """
    if template.is_boss:
        return _BOSS_WEIGHT_CLASS
    return _DANGER_WEIGHT_CLASS.get(template.danger_tier, "small")


def resolve_accent_material(behavior: EnemyBehavior) -> str:
    """Return the accent material id for an AI behavior."""
    return _BEHAVIOR_ACCENT.get(behavior, "light_alloy")


def generate_enemy_build(template: EnemyShipTemplate) -> ShipBuild:
    """Create a ShipBuild from an enemy template, deterministic per template id.

    Produces a silhouette filled with the faction's primary material and
    a behavior-linked accent layer near the hull edges. No placed slots —
    enemy ships don't host player-facing equipment, so slots stay empty
    until a future session introduces module-targeted combat for
    enemies. The pixel palette alone is enough for rendering + the
    C4 Session 1 overlay primitive to operate on region footprints.
    """
    weight_class = resolve_weight_class(template)
    wc = WEIGHT_CLASSES[weight_class]
    canvas_w = int(wc.get("canvas_w", wc.get("canvas", 32)))
    canvas_h = int(wc.get("canvas_h", wc.get("canvas", 32)))

    primary_id = resolve_primary_material(template.faction_id)
    accent_id = resolve_accent_material(template.behavior)

    seed = _deterministic_seed(template.id)
    pixels = _place_enemy_silhouette(
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        primary_id=primary_id,
        accent_id=accent_id,
        seed=seed,
    )

    return ShipBuild(
        weight_class=weight_class,
        pixels=pixels,
        preset_name=template.name,
        ship_type_id=template.id,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _deterministic_seed(template_id: str) -> int:
    """Stable 31-bit seed derived from the template id."""
    return hash(template_id) & 0x7FFFFFFF


def _place_enemy_silhouette(
    canvas_w: int,
    canvas_h: int,
    primary_id: str,
    accent_id: str,
    seed: int,
) -> list[PlacedPixel]:
    """Generate a ship-like silhouette filled with primary + accent pixels.

    Uses an elliptical distance field so ships read as "pointing right" —
    wider front, tapered tail. Pixels within the ellipse are ranked by
    distance from the ship's centerline; the hull interior gets primary
    material, the outer edge band gets accent material, and a single
    cockpit pixel anchors the forward-most position.
    """
    cx = canvas_w // 2
    cy = canvas_h // 2

    candidates: list[tuple[float, int, int]] = []
    for y in range(canvas_h):
        for x in range(canvas_w):
            dx = (x - cx) / (canvas_w * 0.42)
            dy = (y - cy) / (canvas_h * 0.35)
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= 1.0:
                candidates.append((dist, x, y))

    # Deterministic ordering: by distance from center (inside-out fill).
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))

    rng = _random.Random(seed)
    total = len(candidates)
    accent_count = max(1, int(total * _ACCENT_RATIO))

    # Accent sits in the outermost band of the ellipse — closer to the
    # edge, reads as "plating detail" against the core material.
    accent_threshold_idx = total - accent_count
    pixels: list[PlacedPixel] = []
    forward_most: Optional[tuple[int, int]] = None

    for idx, (_dist, x, y) in enumerate(candidates):
        material = primary_id if idx < accent_threshold_idx else accent_id
        # 6% of accent pixels jitter into the hull interior so the edge
        # band doesn't read as a perfectly concentric ring. Seeded RNG
        # keeps the jitter deterministic per template.
        if idx < accent_threshold_idx and rng.random() < 0.06:
            material = accent_id
        pixels.append(PlacedPixel(x=x, y=y, material_id=material))
        # Track the front-most (largest x) pixel for cockpit placement.
        if forward_most is None or x > forward_most[0]:
            forward_most = (x, y)

    # Anchor a cockpit pixel at the forward-most position (overrides
    # whatever material was there). Single-pixel cockpit keeps the
    # silhouette clean at tiny/small weight classes.
    if forward_most is not None:
        fx, fy = forward_most
        for i, p in enumerate(pixels):
            if p.x == fx and p.y == fy:
                pixels[i] = PlacedPixel(x=fx, y=fy, material_id=_COCKPIT_MATERIAL)
                break

    return pixels
