"""Per-enemy module-overlay provider (Combat §4.2 + §11.2 integration).

Mirrors :class:`EnemyCompositeProvider`'s per-instance caching model —
each enemy instance gets its own :class:`ShipModuleOverlay` so state
(focused subsystem, destroyed subsystems, hit flashes) is isolated from
other enemies of the same template.

**Region mapping strategy.** Enemy builds are procedurally generated
without ``placed_slots`` — so we can't read module footprints from the
build. Instead, we partition the build's canvas into canonical regions
based on subsystem tags (Combat §11.2's 6-tag palette). Ships point
right in the silhouette generator, so:

  - ``cockpit`` → front-top (rightmost, upper third)
  - ``weapon_array`` → front (rightmost, middle)
  - ``sensor_array`` → mid-top
  - ``shield_generator`` → center
  - ``reactor`` → back-center
  - ``engine`` → back (leftmost)

Regions are fixed-position approximations; a per-template override hook
could live here in the future for marquee bosses that want precise
placement. Today every enemy uses the canonical layout.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.2 + §11.2``.
"""

from __future__ import annotations

from typing import Optional

from spacegame.engine.ship_module_overlay import (
    ModuleOverlayState,
    ModuleRegion,
    ShipModuleOverlay,
)
from spacegame.models.enemy_subsystems import CANONICAL_TAGS
from spacegame.models.ship_build import ShipBuild

# Cache key: (template_id, instance_id). instance_id is id(enemy_ship).
# Matches Tier 3.A's EnemyCompositeProvider pattern.
_OverlayKey = tuple[str, Optional[int]]


def canonical_subsystem_regions(
    build: ShipBuild,
    subsystem_tags: list[str],
) -> list[ModuleRegion]:
    """Build :class:`ModuleRegion` objects for each tagged subsystem.

    Regions tile the build's canvas in a spatial layout that matches the
    ship-pointing-right orientation of the procedural silhouette
    generator. Overlapping regions are avoided by keeping each sub-rect
    in a distinct row or column.

    Args:
        build: The enemy's ShipBuild (provides canvas_w, canvas_h).
        subsystem_tags: The ``targetable_subsystems`` list (Combat §11.2).
            Tags not in the canonical 6-palette are silently skipped.

    Returns:
        One :class:`ModuleRegion` per recognized tag, positioned on the
        canvas grid. Empty list when the build has no canvas or tags.
    """
    canvas_w = max(1, build.canvas_w)
    canvas_h = max(1, build.canvas_h)

    # Column slices (front/mid/back). Front is right side because the
    # procedural generator points ships right.
    # Slot widths chosen so a 16x16 canvas still gives at least 2px wide
    # columns (1/4 = 4px).
    col_back_x = 0
    col_back_w = canvas_w // 4
    col_mid_x = canvas_w // 4
    col_mid_w = canvas_w // 2
    col_front_x = canvas_w - canvas_w // 4
    col_front_w = canvas_w - col_front_x

    # Row slices.
    row_top_y = 0
    row_top_h = canvas_h // 3
    row_mid_y = canvas_h // 3
    row_mid_h = canvas_h // 3
    row_bot_y = 2 * (canvas_h // 3)
    row_bot_h = canvas_h - row_bot_y

    # Tag → (x, y, w, h). Positions are visually plausible and non-
    # overlapping; adjustments can come from per-template overrides later.
    _LAYOUT: dict[str, tuple[int, int, int, int]] = {
        "cockpit": (col_front_x, row_top_y, col_front_w, row_top_h),
        "weapon_array": (col_front_x, row_mid_y, col_front_w, row_mid_h),
        "sensor_array": (col_mid_x, row_top_y, col_mid_w, row_top_h),
        "shield_generator": (col_mid_x, row_mid_y, col_mid_w, row_mid_h),
        "reactor": (col_back_x, row_mid_y, col_back_w, row_mid_h),
        "engine": (col_back_x, row_bot_y, col_back_w, row_bot_h),
    }

    canonical = set(CANONICAL_TAGS)
    regions: list[ModuleRegion] = []
    for tag in subsystem_tags:
        if tag not in canonical:
            continue
        layout = _LAYOUT.get(tag)
        if layout is None:
            continue
        x, y, w, h = layout
        regions.append(
            ModuleRegion(
                module_id=tag,  # Use the subsystem tag as the overlay's region ID
                x=x,
                y=y,
                w=max(1, w),
                h=max(1, h),
            )
        )
    return regions


class EnemyModuleOverlayProvider:
    """Per-enemy-instance :class:`ShipModuleOverlay` cache.

    Construct one per combat session. Overlay lifecycle is driven by
    combat view calls:

        overlay = provider.get_overlay(enemy.template.id, build, tags,
                                       instance_key=enemy)
        overlay.set_state("engine", ModuleOverlayState.DESTROYED)
        overlay.trigger_flash("weapon_array")
        overlay.update(dt)
        overlay.render(screen, ship_x, ship_y, cell_size)
    """

    def __init__(self) -> None:
        self._overlays: dict[_OverlayKey, ShipModuleOverlay] = {}

    def clear(self) -> None:
        self._overlays.clear()

    def prune_dead_instances(self, living_enemies: list) -> None:
        """Evict overlays whose enemy instance is no longer alive in combat.

        Mirrors ``EnemyCompositeProvider.prune_dead_instances``. Called
        at encounter start by combat view so stale overlays don't linger
        across fights.
        """
        living_ids = {id(e) for e in living_enemies}
        stale = [key for key in self._overlays if key[1] is not None and key[1] not in living_ids]
        for key in stale:
            del self._overlays[key]

    def cached_keys(self) -> tuple[_OverlayKey, ...]:
        return tuple(self._overlays.keys())

    def all_overlays(self) -> tuple[ShipModuleOverlay, ...]:
        """Return every cached overlay — for per-frame ``update(dt)`` ticks."""
        return tuple(self._overlays.values())

    def get_overlay(
        self,
        template_id: str,
        build: ShipBuild,
        subsystem_tags: list[str],
        instance_key: Optional[object] = None,
    ) -> ShipModuleOverlay:
        """Return the cached overlay for an enemy, building regions on first ask.

        The overlay is constructed once per (template_id, instance) and
        has its canonical subsystem regions pre-registered. Later calls
        reuse the instance — callers mutate state (set_state,
        trigger_flash) on the returned overlay.
        """
        cache_key: _OverlayKey = (
            template_id,
            id(instance_key) if instance_key is not None else None,
        )
        if cache_key in self._overlays:
            return self._overlays[cache_key]
        overlay = ShipModuleOverlay()
        for region in canonical_subsystem_regions(build, subsystem_tags):
            overlay.register_region(region)
        self._overlays[cache_key] = overlay
        return overlay

    def sync_state_from_enemy(
        self,
        overlay: ShipModuleOverlay,
        enemy,  # EnemyShip — untyped to avoid circular import
    ) -> None:
        """Sync overlay persistent state from the enemy's runtime fields.

        Translates the enemy's ``subsystems_destroyed`` set and
        ``focused_subsystem`` into overlay state transitions. Callers run
        this each frame BEFORE render to keep visuals in lockstep with
        combat state.

        State precedence (highest → lowest): DESTROYED > HIGHLIGHTED > NORMAL.
        """
        destroyed = getattr(enemy, "subsystems_destroyed", set()) or set()
        focused = getattr(enemy, "focused_subsystem", None)
        for region_id in overlay.module_ids():
            if region_id in destroyed:
                overlay.set_state(region_id, ModuleOverlayState.DESTROYED)
            elif region_id == focused:
                overlay.set_state(region_id, ModuleOverlayState.HIGHLIGHTED)
            else:
                # DESTROYED is terminal per overlay spec — set_state is
                # silently ignored if already DESTROYED, so this is safe
                # even if the enemy briefly un-destroyed something.
                overlay.set_state(region_id, ModuleOverlayState.NORMAL)
