"""ShipComposite — unified-object ship renderer.

Implements the 7-phase pipeline validated in Spike 02 (replacing the
legacy tile-stitch algorithm):

  1. Silhouette — union of module shapes (with rotation)
  2. Per-module base fill — material band midpoint
  3. Global lighting — upper-right 45°; lerp within material band
  4. Connection detail — typed seams between adjacent modules
  5. Decoration — rivets, wear, stripes, faction insignia
  6. Emissive — animated overlay (engine cores, cockpit windows, plasma)
  7. Palette snap — material-band-constrained

All seven phases implemented. See requirements/overhaul/94_ship_composite_api.md
for the full specification, and SPIKE_02_FINDINGS.md for the prototype
evidence that validated this approach.
"""

from __future__ import annotations

import math
import random as _random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

import numpy as np
import pygame

if TYPE_CHECKING:
    from spacegame.models.ship_build import HullMaterial, ShipBuild


# ---------------------------------------------------------------------------
# Material resolution
# ---------------------------------------------------------------------------
#
# Phase 2 needs a color-per-pixel lookup. Production materials come from the
# data loader; in test environments or during implementation gaps, we fall
# back to a neutral placeholder so rendering never crashes on an unknown ID.
#
# When band-structured palette infrastructure lands (per Bible §2), this
# resolver swaps from HullMaterial.color_primary to band[midpoint_index].
# The API signature stays the same.


def _get_placeholder_material() -> "HullMaterial":
    """Neutral grey placeholder for unknown material IDs.

    Deferred import to avoid circular dependency at module-load time.
    """
    from spacegame.models.ship_build import HullMaterial

    return HullMaterial(
        id="_placeholder",
        name="Placeholder",
        description="Fallback for unknown material IDs.",
        shade_band="steel",
    )


def _resolve_material(material_id: str) -> "HullMaterial":
    """Look up a HullMaterial by ID with graceful fallback.

    Production path: data_loader.hull_materials[material_id].
    Fallback: placeholder material (neutral grey).
    """
    try:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        materials = getattr(dl, "hull_materials", None)
        if materials and material_id in materials:
            return materials[material_id]
    except Exception:
        # Data loader may not be initialized in test environments.
        pass
    return _get_placeholder_material()


# ---------------------------------------------------------------------------
# Material bands — canonical palette lookup
# ---------------------------------------------------------------------------
#
# A material band is a monotonic color sequence from darkest to brightest.
# Canonical bands (5 stops for most, 4 for glass_viewport) live in
# engine/material_palette.py per Bible §2.2. ShipComposite fetches them
# directly and applies per-material category_offset when non-zero.
#
# Phase 3 lighting uses bands as interpolation anchors; Phase 7 palette
# snap uses the same bands as snap targets. The band's darkest stop
# (band[0]) doubles as the ambient floor per Framework §5.2.


def _darken(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Scale each channel by factor (0.0 = black, 1.0 = unchanged)."""
    return (
        max(0, min(255, int(color[0] * factor))),
        max(0, min(255, int(color[1] * factor))),
        max(0, min(255, int(color[2] * factor))),
    )


def _mix(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linear interpolation between two colors at t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _derive_material_band(material: "HullMaterial") -> tuple[tuple[int, int, int], ...]:
    """Return the canonical band for a material, with category offset applied.

    Thin delegate to material_palette. Unknown bands fall back to "steel"
    so callers never see a KeyError from malformed content.
    """
    from spacegame.engine.material_palette import (
        apply_category_offset,
        get_band,
        is_valid_band,
    )

    band_name = material.shade_band if is_valid_band(material.shade_band) else "steel"
    band = get_band(band_name)
    if material.category_offset:
        band = apply_category_offset(band, material.category_offset)
    return band


def _band_midpoint(band: tuple[tuple[int, int, int], ...]) -> tuple[int, int, int]:
    """Return the representative 'base' entry of a band.

    Defined as index ``len(band) // 2`` — index 2 for 5-stop canonical
    bands, index 2 for 4-stop glass_viewport (the brighter central stop).
    """
    return band[len(band) // 2]


def _lerp_band_color(
    band: tuple[tuple[int, int, int], ...],
    factor: float,
) -> tuple[int, int, int]:
    """Interpolate a color from a band based on a 0..1 lighting factor.

    Factor 0.0 returns band[0]; factor 1.0 returns band[-1]; intermediate
    values interpolate linearly between adjacent stops.
    """
    if len(band) == 0:
        return (0, 0, 0)
    if len(band) == 1:
        return band[0]
    # Clamp factor to [0, 1]
    f = max(0.0, min(1.0, factor))
    # Map factor to band index space: f=0 → 0, f=1 → len-1
    scaled = f * (len(band) - 1)
    lo = int(scaled)
    hi = min(lo + 1, len(band) - 1)
    blend = scaled - lo
    return _mix(band[lo], band[hi], blend)


# ---------------------------------------------------------------------------
# Rivet density + emissive color — material-field reads
# ---------------------------------------------------------------------------
#
# Per Bible §3.2 material library, rivet_density and emissive_role are
# declarative HullMaterial fields. ShipComposite reads them directly —
# no substring heuristics.


def _rivet_density_for(material: "HullMaterial") -> float:
    """Rivets per 1000 px² for the given material."""
    return material.rivet_density


def _emissive_color_for(material: "HullMaterial") -> Optional[tuple[int, int, int]]:
    """Base emissive RGB for a material, or None if it has no emissive role.

    Resolves ``material.emissive_role`` through the canonical PALETTE_ROLES
    table. Unknown role names fall through to None rather than raising —
    matches the tolerance the substring-match API used to offer.
    """
    from spacegame.engine.material_palette import get_role, is_valid_role

    role = material.emissive_role
    if not role or not is_valid_role(role):
        return None
    return get_role(role)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RenderAngle(Enum):
    """Canonical orthographic angles. Three supported in v1."""

    FRONT = "front"
    PROFILE = "profile"
    THREE_QUARTER = "three_quarter"


class ModuleState(Enum):
    """Per-module visual state override.

    Applied via ShipComposite.set_module_state; module_id identifies a
    PlacedSlot instance (production data model reconciliation per
    94_ship_composite_api.md §1.4).
    """

    NORMAL = "normal"
    HIGHLIGHTED = "highlighted"
    DAMAGED = "damaged"
    CRITICAL = "critical"
    DISABLED = "disabled"
    DESTROYED = "destroyed"
    RECOVERED = "recovered"
    CORRUPTED = "corrupted"


class InvalidationScope(Enum):
    """Granularity of cache invalidation.

    ALL         — full rebuild (build geometry changed)
    STATE_ONLY  — module states changed; base silhouette preserved
    WEAR_ONLY   — wear level changed; base + states preserved
    SCALE_CACHE — only the per-scale cache discarded
    """

    ALL = "all"
    STATE_ONLY = "state_only"
    WEAR_ONLY = "wear_only"
    SCALE_CACHE = "scale_cache"


# ---------------------------------------------------------------------------
# Request / config types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModuleRenderRequest:
    """Standalone render request for a single module.

    Used by:
      - Ship builder catalog preview pane
      - Placement ghost during drag
      - Salvage module recovery cinematic
    """

    module_id: str
    category: str
    manufacturer: str
    material_override: Optional[str] = None
    faction_overlay: Optional[str] = None
    state: ModuleState = ModuleState.NORMAL
    wear: float = 0.0
    rotation: int = 0
    flipped: bool = False
    seed: int = 0
    scale: int = 1


@dataclass(frozen=True)
class ShipCompositeConfig:
    """Configuration tunables for ShipComposite rendering.

    Defaults produce the canonical Aurelia look; overrides support
    specific scene contexts.
    """

    angles_to_cache: tuple[RenderAngle, ...] = (RenderAngle.THREE_QUARTER,)
    emissive_pulse_hz: float = 0.83      # ~1.2s period; matches material §3.5 discipline
    enable_engine_glow: bool = True
    enable_wear_overlay: bool = True
    enable_rivets: bool = True
    enable_connection_detail: bool = True
    enable_palette_snap: bool = True
    faction_overlay: Optional[str] = None
    max_scale: int = 8


# ---------------------------------------------------------------------------
# ShipComposite — per-build renderer
# ---------------------------------------------------------------------------


class ShipComposite:
    """Per-build renderer with caching, state overrides, and angle support.

    Consumer pattern:
        composite = ShipComposite(ship.build)
        composite.set_module_state("cockpit@5,3", ModuleState.DAMAGED)
        composite.update(dt)  # advances emissive pulse
        surface = composite.get_surface(angle=RenderAngle.THREE_QUARTER, scale=2)

    See requirements/overhaul/94_ship_composite_api.md for full spec.
    """

    def __init__(
        self,
        build: "ShipBuild",
        config: Optional[ShipCompositeConfig] = None,
    ) -> None:
        self._build = build
        self._config = config or ShipCompositeConfig()

        # State overrides: module_id -> ModuleState (absent = NORMAL default)
        self._module_states: dict[str, ModuleState] = {}

        # Ship-wide parameters
        self._wear: float = 0.0
        self._faction_overlay: Optional[str] = self._config.faction_overlay
        # Destruction progression (Combat §11.4). Real-valued [0, 1] input is
        # quantized to 5 buckets (0, 0.25, 0.5, 0.75, 1.0); rebuild triggers
        # on bucket change only.
        self._destruction_bucket: float = 0.0

        # Cache state
        # - _base_cache holds pre-emissive native-scale surfaces (Phases 1-5+7)
        # - _scale_cache holds final scaled surfaces; populated only when no
        #   emissive pixels exist (because Phase 6 is per-frame animation).
        self._phase_cache: dict[object, pygame.Surface] = {}
        self._base_cache: dict[object, pygame.Surface] = {}
        self._final_cache: dict[object, pygame.Surface] = {}
        self._scale_cache: dict[object, pygame.Surface] = {}
        self._cached_angles: set[RenderAngle] = set()

        # Emissive pixel list — (x, y, base_color). Computed lazily during
        # rebuild; invalidated with ALL scope. Drives Phase 6 per-frame work.
        self._emissive_pixels: Optional[list[tuple[int, int, tuple[int, int, int]]]] = None

        # Emissive pulse phase (0..1, advanced by update(dt))
        self._emissive_phase: float = 0.0

        # Dirty flag drives lazy rebuild
        self._dirty: bool = True

    # -----------------------------------------------------------------
    # State management
    # -----------------------------------------------------------------

    def set_module_state(self, module_id: str, state: ModuleState) -> None:
        """Override a single module's visual state. Triggers STATE_ONLY
        invalidation so only the affected module region rebuilds."""
        if self._module_states.get(module_id) == state:
            return  # No-op
        self._module_states[module_id] = state
        self.invalidate(InvalidationScope.STATE_ONLY, module_id=module_id)

    def get_module_state(self, module_id: str) -> ModuleState:
        """Current state override for a module, or NORMAL if unset."""
        return self._module_states.get(module_id, ModuleState.NORMAL)

    def set_wear(self, wear: float) -> None:
        """Set ship-wide wear level (0.0-1.0). Clamps to range."""
        new_wear = max(0.0, min(1.0, wear))
        if new_wear == self._wear:
            return
        self._wear = new_wear
        self.invalidate(InvalidationScope.WEAR_ONLY)

    def set_faction_overlay(self, faction_id: Optional[str]) -> None:
        """Apply or clear a faction color overlay. Triggers ALL invalidation."""
        if faction_id == self._faction_overlay:
            return
        self._faction_overlay = faction_id
        self.invalidate(InvalidationScope.ALL)

    def set_destruction_progress(self, progress: float) -> None:
        """Set destruction progression ``[0, 1]``; quantized to 5 buckets.

        Rebuild fires only when the bucket changes — intermediate progress
        values between bucket edges are free. See Combat §11.4.
        """
        clamped = max(0.0, min(1.0, progress))
        # Quantize to {0.0, 0.25, 0.5, 0.75, 1.0} via round-to-nearest-quarter.
        bucket = round(clamped * 4) / 4.0
        if bucket == self._destruction_bucket:
            return
        self._destruction_bucket = bucket
        self.invalidate(InvalidationScope.ALL)

    @property
    def destruction_bucket(self) -> float:
        """Current destruction bucket in {0.0, 0.25, 0.5, 0.75, 1.0}."""
        return self._destruction_bucket

    def invalidate(
        self,
        scope: InvalidationScope = InvalidationScope.ALL,
        module_id: Optional[str] = None,
    ) -> None:
        """Cache invalidation. Pass module_id with STATE_ONLY to target
        a single module; otherwise the full state-overlay is rebuilt.
        """
        if scope == InvalidationScope.ALL:
            self._phase_cache.clear()
            self._base_cache.clear()
            self._final_cache.clear()
            self._scale_cache.clear()
            self._cached_angles.clear()
            self._emissive_pixels = None  # Recompute on next rebuild
            self._dirty = True
        elif scope == InvalidationScope.STATE_ONLY:
            # State-only preserves phases 1-4; invalidates final + scale caches.
            self._base_cache.clear()
            self._final_cache.clear()
            self._scale_cache.clear()
            self._dirty = True
        elif scope == InvalidationScope.WEAR_ONLY:
            # Wear-only: phases 1-4 preserved; phase 5 decoration invalidated.
            self._base_cache.clear()
            self._final_cache.clear()
            self._scale_cache.clear()
            self._dirty = True
        elif scope == InvalidationScope.SCALE_CACHE:
            self._scale_cache.clear()

    # -----------------------------------------------------------------
    # Per-frame update
    # -----------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance emissive pulse phase by dt seconds.

        Does not rebuild cached surfaces; emissive animation is applied
        at render time as a cheap overlay pass.
        """
        self._emissive_phase = (self._emissive_phase + dt * self._config.emissive_pulse_hz) % 1.0

    # -----------------------------------------------------------------
    # Render access
    # -----------------------------------------------------------------

    def get_surface(
        self,
        angle: RenderAngle = RenderAngle.THREE_QUARTER,
        scale: int = 1,
    ) -> pygame.Surface:
        """Return the composited ship surface for the requested angle + scale.

        Cache behavior depends on whether the build has emissive pixels:
          - No emissive pixels (or Phase 6 disabled) — full cache; identical
            object on repeat calls.
          - Emissive pixels with Phase 6 active — base cache (Phases 1-5+7)
            hits; Phase 6 overlay applied to a fresh copy each call so pulse
            animation progresses between frames.

        All pipeline phases implemented:
          - Phase 1 (Silhouette), 2 (Base fill), 3 (Lighting),
          - Phase 4 (Connection), 5 (Decoration), 7 (Palette snap) — cached
          - Phase 6 (Emissive) — per-call animated overlay
        """
        base_key = (angle, self._wear, self._faction_overlay,
                    frozenset(self._module_states.items()))
        scale_key = (base_key, scale)

        # Check for fully-cached scaled surface (only possible when no
        # Phase 6 animation is active).
        has_emissive_animation = self._has_active_emissive()
        if not has_emissive_animation and scale_key in self._scale_cache:
            return self._scale_cache[scale_key]

        # Build or retrieve the pre-Phase-6 native-scale base.
        if base_key not in self._base_cache:
            self._base_cache[base_key] = self._rebuild_base(angle)
        base = self._base_cache[base_key]

        # Apply Phase 6 emissive overlay to a copy when animation is active.
        # When no emissive pixels exist, the base IS the final render.
        if has_emissive_animation:
            working = base.copy()
            self._phase6_emissive(working)
        else:
            working = base

        # Apply scale.
        if scale == 1:
            final = working.copy() if not has_emissive_animation else working
        else:
            w = working.get_width() * scale
            h = working.get_height() * scale
            final = pygame.transform.scale(working, (w, h))

        # Cache only when no per-frame animation: Phase 6 pixels would
        # otherwise render stale on next frame.
        if not has_emissive_animation:
            self._scale_cache[scale_key] = final

        self._cached_angles.add(angle)
        self._dirty = False
        return final

    def _has_active_emissive(self) -> bool:
        """True if the build has emissive pixels AND Phase 6 is enabled."""
        if not self._config.enable_engine_glow:
            return False
        if self._emissive_pixels is None:
            # Lazy populate — happens naturally via _rebuild_base, but we
            # may check before first render.
            self._emissive_pixels = self._collect_emissive_pixels()
        return bool(self._emissive_pixels)

    def _collect_emissive_pixels(self) -> list[tuple[int, int, tuple[int, int, int]]]:
        """Gather (x, y, emissive_color) tuples for all emissive pixels."""
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        result: list[tuple[int, int, tuple[int, int, int]]] = []
        emissive_cache: dict[str, Optional[tuple[int, int, int]]] = {}
        for p in self._build.pixels:
            if not (0 <= p.x < canvas_w and 0 <= p.y < canvas_h):
                continue
            if p.material_id not in emissive_cache:
                emissive_cache[p.material_id] = _emissive_color_for(
                    _resolve_material(p.material_id)
                )
            color = emissive_cache[p.material_id]
            if color is not None:
                result.append((p.x, p.y, color))
        return result

    # -----------------------------------------------------------------
    # Pipeline phases — internal
    # -----------------------------------------------------------------

    def _rebuild_base(self, angle: RenderAngle) -> pygame.Surface:
        """Run the composition pipeline at native (1x) scale.

        All seven phases implemented. Phases 1-5+7 are baked into the
        returned surface; Phase 6 emissive overlay is applied per-call in
        get_surface (not baked so pulse animation progresses).
        """
        silhouette_mask = self._phase1_silhouette()
        emissive_mask = self._compute_emissive_mask()

        # Populate emissive-pixel cache for Phase 6 use.
        self._emissive_pixels = self._collect_emissive_pixels()

        lighting_factors = self._compute_lighting_factors(silhouette_mask)
        surface = self._phase3_lighting(silhouette_mask, lighting_factors)
        if self._config.enable_connection_detail:
            self._phase4_connection_detail(surface, silhouette_mask)
        if self._config.enable_rivets or self._config.enable_wear_overlay:
            self._phase5_decoration(surface, silhouette_mask)
        if self._config.enable_palette_snap:
            self._phase7_palette_snap(surface, silhouette_mask, emissive_mask)
        # Destruction overlay (Combat §11.4) — bucket-driven darkening + pixel
        # dropout; applied after palette snap so scorch reads as damage, not
        # as a darker variant of the base material.
        if self._destruction_bucket > 0.0:
            self._phase_destruction_damage(surface, silhouette_mask, emissive_mask)
        # Phase 6 (emissive overlay) applied per-frame in get_surface.
        return surface

    def _build_seed(self) -> int:
        """Derive a deterministic seed from the build's pixel geometry.

        Different builds produce different rivet / wear patterns; the same
        build always produces the same pattern — BOTH within a run AND
        across pytest-xdist worker processes. Python's built-in ``hash()``
        is randomized per-process via PYTHONHASHSEED, which makes parallel
        test runs flaky (same build, different seeds across workers).
        Using hashlib's md5 gives us a stable hash independent of the
        interpreter's PYTHONHASHSEED.
        """
        import hashlib

        positions = ";".join(
            f"{p.x},{p.y},{p.material_id}" for p in self._build.pixels
        )
        digest = hashlib.md5(positions.encode("utf-8")).digest()
        # Take first 4 bytes as a positive 31-bit int for numpy compat.
        return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF

    def _phase1_silhouette(self) -> np.ndarray:
        """Phase 1 — compute the ship silhouette as a boolean mask.

        Returns:
            np.ndarray with shape (canvas_h, canvas_w), dtype=bool.
            Indexed as mask[y, x]. True where a ship pixel is present.
        """
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        mask = np.zeros((canvas_h, canvas_w), dtype=bool)
        for p in self._build.pixels:
            if 0 <= p.x < canvas_w and 0 <= p.y < canvas_h:
                mask[p.y, p.x] = True
        return mask

    def _phase2_base_fill(self, silhouette_mask: np.ndarray) -> pygame.Surface:
        """Phase 2 — fill each ship pixel with its material's base color.

        The silhouette_mask constrains the fill; pixels outside the
        silhouette remain transparent.

        Kept as an isolated step for testing and alternative pipelines;
        the production path runs Phase 3 (lit fill) instead.

        Args:
            silhouette_mask: Output of Phase 1. Indexed as mask[y, x].

        Returns:
            pygame.Surface with SRCALPHA, filled at the midpoint of each
            material's canonical shade band (with category_offset applied).
        """
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)

        # Cache resolved band midpoint per unique material_id seen in this
        # build. Avoids redundant data-loader lookups for repeat materials.
        midpoint_cache: dict[str, tuple[int, int, int]] = {}

        for p in self._build.pixels:
            if not (0 <= p.x < canvas_w and 0 <= p.y < canvas_h):
                continue
            if not silhouette_mask[p.y, p.x]:
                continue
            if p.material_id not in midpoint_cache:
                material = _resolve_material(p.material_id)
                midpoint_cache[p.material_id] = _band_midpoint(_derive_material_band(material))
            color = midpoint_cache[p.material_id]
            surf.set_at((p.x, p.y), (*color, 255))

        return surf

    def _compute_lighting_factors(self, silhouette_mask: np.ndarray) -> np.ndarray:
        """Compute per-pixel lighting factors across the silhouette.

        Bbox-gradient approach validated by Spike 02: factor=0 at the
        lower-left corner of the silhouette bbox, factor=1 at the
        upper-right. Linear blend between. Pygame y-axis increases
        downward, so "upper" = low y.

        Pixels outside the silhouette get factor=0 (irrelevant; Phase 3
        masks them out).

        Args:
            silhouette_mask: Output of Phase 1. Indexed as mask[y, x].

        Returns:
            np.ndarray[float32] with same shape as silhouette_mask.
            Values in [0.0, 1.0] for ship pixels; 0.0 elsewhere.
        """
        factors = np.zeros_like(silhouette_mask, dtype=np.float32)
        ys, xs = np.where(silhouette_mask)
        if len(xs) == 0:
            return factors
        min_x = int(xs.min())
        max_x = int(xs.max())
        min_y = int(ys.min())
        max_y = int(ys.max())

        span_x = max_x - min_x
        span_y = max_y - min_y

        if span_x == 0 and span_y == 0:
            # Single-pixel ship — no gradient possible; treat as fully lit.
            factors[ys, xs] = 1.0
            return factors

        # Normalize each ship pixel position within the bbox.
        rel_x = (xs - min_x) / max(1, span_x)  # 0 at left, 1 at right
        rel_y = (ys - min_y) / max(1, span_y)  # 0 at top, 1 at bottom

        # Upper-right brightest: factor = (right-ness + up-ness) / 2
        factor_values = (rel_x + (1.0 - rel_y)) / 2.0
        factors[ys, xs] = factor_values.astype(np.float32)
        return factors

    def _phase3_lighting(
        self,
        silhouette_mask: np.ndarray,
        lighting_factors: np.ndarray,
    ) -> pygame.Surface:
        """Phase 3 — apply global directional lighting per material band.

        For each ship pixel, look up its material's band, then interpolate
        within the band based on the pixel's lighting factor. The result
        has continuous RGB values (Phase 7 snap runs later to collapse
        back onto palette band stops).

        Args:
            silhouette_mask: Output of Phase 1. Indexed as mask[y, x].
            lighting_factors: Output of _compute_lighting_factors.
                Same shape as silhouette_mask; values in [0, 1].

        Returns:
            pygame.Surface with SRCALPHA, lit base ready for subsequent
            phases (connection detail, decoration, emissive, snap).
        """
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)

        # Cache resolved bands per material_id (one data-loader lookup +
        # one band derivation per unique material in the build).
        band_cache: dict[str, tuple[tuple[int, int, int], ...]] = {}

        for p in self._build.pixels:
            if not (0 <= p.x < canvas_w and 0 <= p.y < canvas_h):
                continue
            if not silhouette_mask[p.y, p.x]:
                continue

            # Resolve + derive band once per material_id.
            if p.material_id not in band_cache:
                material = _resolve_material(p.material_id)
                band_cache[p.material_id] = _derive_material_band(material)
            band = band_cache[p.material_id]

            factor = float(lighting_factors[p.y, p.x])
            color = _lerp_band_color(band, factor)
            surf.set_at((p.x, p.y), (*color, 255))

        return surf

    def _phase4_connection_detail(
        self,
        surface: pygame.Surface,
        silhouette_mask: np.ndarray,
    ) -> None:
        """Phase 4 — darken pixels at material boundaries to produce seams.

        Mutates the input surface in place. Operates on material-adjacency:
        a pixel that has a neighbor of a different material gets darkened,
        producing a visible panel-line seam.

        Data-model note: production uses PlacedPixel.material_id as the
        connection proxy. When typed ConnectionKind metadata lands per
        Framework §15.3, this phase extends to select seam treatment by
        connection type (structural / mount / power / data / coolant)
        rather than just darkening uniformly. The extension is additive —
        no refactoring required.

        Algorithm:
          - For each ship pixel, check its right + down neighbors.
          - If any neighbor has a different material_id, darken the current
            pixel to factor 0.65 of its Phase 3 color.
          - Right+down pattern prevents double-darkening shared edges.
          - Break on first hit to produce one-sided seams (aesthetic choice).

        Args:
            surface: Phase 3 lit surface; mutated in place.
            silhouette_mask: Phase 1 output; bounds-checks writes.
        """
        # Build pixel_map: (x, y) -> material_id for O(1) neighbor lookup.
        pixel_map: dict[tuple[int, int], str] = {
            (p.x, p.y): p.material_id for p in self._build.pixels
        }

        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h

        for (x, y), mat_id in pixel_map.items():
            if not (0 <= x < canvas_w and 0 <= y < canvas_h):
                continue
            if not silhouette_mask[y, x]:
                continue
            # Right + down neighbor check. Break on first different-material hit.
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                neighbor_mat = pixel_map.get((nx, ny))
                if neighbor_mat is not None and neighbor_mat != mat_id:
                    current = surface.get_at((x, y))
                    darker = _darken((current.r, current.g, current.b), 0.65)
                    surface.set_at((x, y), (*darker, current.a))
                    break

    def _phase5_decoration(
        self,
        surface: pygame.Surface,
        silhouette_mask: np.ndarray,
    ) -> None:
        """Phase 5 — add rivets and wear overlay.

        Mutates the surface in place. Two sub-passes, each seeded from
        the build geometry so the same build always decorates the same way.

        Scope for Session 4 — per Bible §3 material library:
          - Rivets: seeded Poisson-like placement at material-specific density
          - Wear overlay: seeded uniform noise darkening

        Deferred to future work (per 94_ship_composite_api.md):
          - Signature stripes (requires manufacturer metadata)
          - Faction insignia (requires faction_overlay system + hand-
            authored sprites)

        Args:
            surface: Phase 3+4 surface; mutated in place.
            silhouette_mask: Phase 1 output; bounds-checks writes.
        """
        seed = self._build_seed()

        if self._config.enable_rivets:
            self._decorate_rivets(surface, silhouette_mask, seed)

        if self._config.enable_wear_overlay:
            # Use a distinct sub-seed so rivets and wear don't correlate
            # (placing rivets and then wearing them would be redundant).
            self._decorate_wear(surface, silhouette_mask, seed ^ 0xA5A5A5A5)

    def _decorate_rivets(
        self,
        surface: pygame.Surface,
        silhouette_mask: np.ndarray,
        seed: int,
    ) -> None:
        """Place rivets on the silhouette via seeded Poisson-like sampling.

        Rivet density is per-material (looked up by material_id). The
        sampler respects a minimum Manhattan spacing so rivets don't
        cluster. Rivets render as dark single-pixel dots (band-0 style).

        Algorithm:
          1. Compute per-material target rivet count from density × area / 1000.
          2. Shuffle candidate positions via seeded RNG.
          3. Accept each candidate if it's at least min_spacing away from
             all previously placed rivets on the same material.
          4. Darken accepted pixels to factor 0.45 of their current color.
        """
        # Group pixels by material so density lookup is per-group.
        pixels_by_material: dict[str, list[tuple[int, int]]] = {}
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        for p in self._build.pixels:
            if not (0 <= p.x < canvas_w and 0 <= p.y < canvas_h):
                continue
            if not silhouette_mask[p.y, p.x]:
                continue
            pixels_by_material.setdefault(p.material_id, []).append((p.x, p.y))

        rng = np.random.default_rng(seed)
        min_spacing = 3  # Manhattan distance between rivets

        for material_id, positions in pixels_by_material.items():
            density = _rivet_density_for(_resolve_material(material_id))
            if density <= 0 or not positions:
                continue
            area = len(positions)
            target_count = max(1, int(area * density / 1000.0))
            if target_count == 0:
                continue

            # Seeded shuffle of candidate positions for this material.
            indices = rng.permutation(len(positions))
            placed: list[tuple[int, int]] = []
            for idx in indices:
                if len(placed) >= target_count:
                    break
                x, y = positions[int(idx)]
                # Minimum-spacing rejection (Manhattan distance).
                too_close = any(
                    abs(x - px) + abs(y - py) < min_spacing
                    for px, py in placed
                )
                if not too_close:
                    placed.append((x, y))

            # Darken accepted pixels to produce rivet cores.
            for x, y in placed:
                current = surface.get_at((x, y))
                dark = _darken((current.r, current.g, current.b), 0.45)
                surface.set_at((x, y), (*dark, current.a))

    def _decorate_wear(
        self,
        surface: pygame.Surface,
        silhouette_mask: np.ndarray,
        seed: int,
    ) -> None:
        """Apply wear overlay: seeded noise darkens some pixels.

        Algorithm:
          - Generate per-pixel noise in [0, 1] via seeded RNG.
          - Threshold controlled by wear level: higher wear → lower
            threshold → more darkened pixels.
          - Affected pixels darken to factor 0.72 (subtle scorching).

        Wear = 0.15 baseline (every ship looks lived-in) + per-instance
        wear level up to 1.0 (battle-wrecked).
        """
        # Effective wear: baseline 0.15 + per-instance, capped at 1.0.
        effective_wear = min(1.0, 0.15 + self._wear)

        # Threshold: at wear=1.0, threshold=0.7 (30% of pixels darken).
        #            at wear=0.15 (baseline), threshold=0.95 (~5% darken).
        threshold = 1.0 - effective_wear * 0.3

        rng = np.random.default_rng(seed)
        noise = rng.random(silhouette_mask.shape)

        # Find pixels where noise exceeds threshold AND is on the silhouette.
        wear_mask = silhouette_mask & (noise > threshold)
        ys, xs = np.where(wear_mask)

        for y, x in zip(ys, xs, strict=True):
            current = surface.get_at((int(x), int(y)))
            dark = _darken((current.r, current.g, current.b), 0.72)
            surface.set_at((int(x), int(y)), (*dark, current.a))

    def _compute_emissive_mask(self) -> np.ndarray:
        """Compute a boolean mask marking emissive pixels.

        A pixel is emissive if its resolved material has a populated
        ``emissive_role`` field pointing at a canonical PALETTE_ROLES entry.
        Emissive pixels:
          - Bypass Phase 7 palette snap (continuous color preserved)
          - Receive Phase 6 animated overlay at render time

        Returns:
            np.ndarray[bool] shaped (canvas_h, canvas_w). Indexed [y, x].
        """
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        mask = np.zeros((canvas_h, canvas_w), dtype=bool)
        emissive_cache: dict[str, bool] = {}
        for p in self._build.pixels:
            if not (0 <= p.x < canvas_w and 0 <= p.y < canvas_h):
                continue
            if p.material_id not in emissive_cache:
                emissive_cache[p.material_id] = (
                    _emissive_color_for(_resolve_material(p.material_id)) is not None
                )
            if emissive_cache[p.material_id]:
                mask[p.y, p.x] = True
        return mask

    def _phase7_palette_snap(
        self,
        surface: pygame.Surface,
        silhouette_mask: np.ndarray,
        emissive_mask: np.ndarray,
    ) -> None:
        """Phase 7 — snap each non-emissive pixel to the nearest entry in
        its material's shade band.

        Mutates the surface in place. Produces the discrete banded appearance
        per Bible §1.3 ("chunky, material-honest lighting"). Band-constrained:
        each pixel snaps only within ITS OWN material's band, never crossing
        into another material's palette (per Bible §2 material-band discipline
        and Spike 02 Finding 3).

        Emissive pixels bypass snap entirely (Bible §3.5) — their continuous
        color is preserved for Phase 6 to overlay.

        Algorithm:
          - For each ship pixel, look up its material and derive band.
          - Find the band entry with minimum sum-of-squared-RGB-differences.
          - Replace the pixel with that band entry.

        Args:
            surface: Phase 5 surface; mutated in place.
            silhouette_mask: Phase 1 output; bounds writes to ship pixels.
            emissive_mask: Phase-1-era emissive mask; skip-list for snap.
        """
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h

        # Cache derived bands per material_id.
        band_cache: dict[str, tuple[tuple[int, int, int], ...]] = {}

        for p in self._build.pixels:
            x, y = p.x, p.y
            if not (0 <= x < canvas_w and 0 <= y < canvas_h):
                continue
            if not silhouette_mask[y, x]:
                continue
            if emissive_mask[y, x]:
                continue  # Emissive bypasses snap

            # Resolve band once per material_id.
            if p.material_id not in band_cache:
                material = _resolve_material(p.material_id)
                band_cache[p.material_id] = _derive_material_band(material)
            band = band_cache[p.material_id]

            # Snap to nearest band entry by sum-of-squared-RGB distance.
            current = surface.get_at((x, y))
            cr, cg, cb = current.r, current.g, current.b
            best_entry = band[0]
            best_dist = float("inf")
            for entry in band:
                er, eg, eb = entry
                dist = (cr - er) ** 2 + (cg - eg) ** 2 + (cb - eb) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_entry = entry

            surface.set_at((x, y), (*best_entry, current.a))

    def _phase_destruction_damage(
        self,
        surface: pygame.Surface,
        silhouette_mask: np.ndarray,
        emissive_mask: np.ndarray,
    ) -> None:
        """Apply bucket-driven destruction damage (Combat §11.4).

        Reads ``self._destruction_bucket`` (one of {0.25, 0.5, 0.75, 1.0})
        and mutates ``surface`` in place:
          - Progressive darkening: RGB multiplied by ``1 - bucket * 0.55``
          - Pixel dropout (silhouette breaks) at ≥0.50, scaled with bucket
          - Emissive pixels bypass both (they overlay later in Phase 6)

        Pattern is seeded by build geometry so the same ship destroys
        identically — important for reproducible replays and tests.
        """
        bucket = self._destruction_bucket
        if bucket <= 0.0:
            return

        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        dim = 1.0 - bucket * 0.55
        rng = _random.Random(self._build_seed() ^ int(bucket * 1000))

        # Dropout fraction per bucket — chosen so bucket 1.0 wreck reads as
        # "skeletal but still a silhouette", not absent.
        drop_by_bucket = {0.25: 0.0, 0.5: 0.10, 0.75: 0.28, 1.0: 0.48}
        drop_fraction = drop_by_bucket.get(bucket, 0.0)

        for p in self._build.pixels:
            x, y = p.x, p.y
            if not (0 <= x < canvas_w and 0 <= y < canvas_h):
                continue
            if not silhouette_mask[y, x]:
                continue
            if emissive_mask[y, x]:
                continue  # Emissive bypasses damage so engine glow etc. stay readable

            # Dropout — replace with transparent (silhouette break).
            if drop_fraction > 0.0 and rng.random() < drop_fraction:
                surface.set_at((x, y), (0, 0, 0, 0))
                continue

            # Progressive darkening.
            current = surface.get_at((x, y))
            surface.set_at(
                (x, y),
                (
                    int(current.r * dim),
                    int(current.g * dim),
                    int(current.b * dim),
                    current.a,
                ),
            )

    def _phase6_emissive(self, surface: pygame.Surface) -> None:
        """Phase 6 — apply pulse-modulated additive overlay to emissive pixels.

        Per-frame animated overlay. Uses self._emissive_phase (advanced by
        update(dt)) to modulate brightness. Amplitude is 15% of peak per
        Bible §3.5 — emissive pulses between 85% and 100% of base intensity.

        Additive blend: emissive color scaled by pulse intensity is added to
        the existing surface color, clamped at 255. Produces a glow effect
        without replacing the underlying Phase 3 lit base.

        Emissive pixels were already excluded from Phase 7 snap, so their
        Phase 3 colors are continuous (not band-aligned). This is correct —
        emissive pixels represent glowing sources that shouldn't be
        constrained to the material's non-emissive band.

        Args:
            surface: Post-Phase-7 surface; mutated in place with additive overlay.
        """
        # Ensure we have the emissive pixel list (lazy compute).
        if self._emissive_pixels is None:
            self._emissive_pixels = self._collect_emissive_pixels()
        if not self._emissive_pixels:
            return

        # Pulse: sin wave over phase, scaled to [0.85, 1.0] (15% amplitude).
        pulse_sin = math.sin(2.0 * math.pi * self._emissive_phase)
        intensity = 0.925 + 0.075 * pulse_sin  # Midpoint 0.925, amplitude 0.075

        for x, y, (er, eg, eb) in self._emissive_pixels:
            scaled_r = int(er * intensity)
            scaled_g = int(eg * intensity)
            scaled_b = int(eb * intensity)

            current = surface.get_at((x, y))
            new_r = min(255, current.r + scaled_r)
            new_g = min(255, current.g + scaled_g)
            new_b = min(255, current.b + scaled_b)
            surface.set_at((x, y), (new_r, new_g, new_b, current.a))

    def get_module_surface(self, module_id: str) -> pygame.Surface:
        """Return the surface for a single module in isolation.

        Used by Salvage S5 for module recovery cinematic. Uses the
        7-phase pipeline minus the silhouette-union step.

        Skeleton: returns a placeholder until pipeline phases implement.
        """
        # Placeholder — replaced by pipeline implementation.
        return pygame.Surface((16, 16), pygame.SRCALPHA)

    def get_module_rect(
        self,
        module_id: str,
        angle: RenderAngle = RenderAngle.THREE_QUARTER,
    ) -> pygame.Rect:
        """Return the bounding rect of a module within the ship composite.

        Used by Combat C4 module-targeting overlay for highlight / hit
        flash / damage tint / destruction marker positioning.

        Skeleton: returns a placeholder rect until slot-to-module
        mapping lands with Phase 1.
        """
        return pygame.Rect(0, 0, 16, 16)

    # -----------------------------------------------------------------
    # Batch / precompute operations
    # -----------------------------------------------------------------

    def preload_angles(self) -> None:
        """Pre-render all angles configured in config.angles_to_cache."""
        for angle in self._config.angles_to_cache:
            self.get_surface(angle=angle)

    def preload_scales(self, scales: tuple[int, ...]) -> None:
        """Pre-render at the given integer scales."""
        for scale in scales:
            self.get_surface(scale=scale)

    # -----------------------------------------------------------------
    # State queries
    # -----------------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        """True if any pending invalidation has not yet been resolved."""
        return self._dirty

    @property
    def wear(self) -> float:
        """Current ship-wide wear level."""
        return self._wear

    @property
    def cached_angles(self) -> tuple[RenderAngle, ...]:
        """Angles currently present in cache."""
        return tuple(self._cached_angles)


# ---------------------------------------------------------------------------
# Standalone module rendering (free function)
# ---------------------------------------------------------------------------


# Internal cache for compose_standalone_module; keyed on frozen request.
_standalone_cache: dict[ModuleRenderRequest, pygame.Surface] = {}


def compose_standalone_module(request: ModuleRenderRequest) -> pygame.Surface:
    """Render a single module in isolation, outside any ShipComposite.

    Used by:
      - Builder catalog preview (hovering a module in the shop)
      - Placement ghost (drag preview before commit)
      - Salvage cell preview (showing a recoverable module in the grid)

    Does not persistently cache across requests with different parameters;
    callers should cache the result if rendering the same module repeatedly.

    Skeleton: returns a placeholder surface at the requested scale.
    Pipeline implementation lands incrementally per 94_ship_composite_api.md.
    """
    if request in _standalone_cache:
        return _standalone_cache[request]

    # Placeholder — replaced by pipeline implementation.
    base_size = 32
    w = base_size * request.scale
    h = base_size * request.scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    _standalone_cache[request] = surf
    return surf
