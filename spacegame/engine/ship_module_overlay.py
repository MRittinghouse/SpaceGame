"""Ship module targeting + damage overlay (Combat overhaul §4.2).

Renders the visual feedback layer above a ship's composite surface:

  - **Highlighted** outline when a module is the player's pre-fire target
    (``hud_warning`` 2-pixel inset).
  - **Committed** outline when the target is locked (``hud_critical``).
  - **Flash** — transient bright pulse at the moment of impact, using the
    targeted material's band specular entry for 100ms.
  - **Damaged** — persistent scorch tint once a module drops below ~50%
    module-HP (``rivet`` role overlay).
  - **Destroyed** — permanent marker once the module is gone: fill in
    ``steel`` band's shadow_deep entry with a ``seam`` outline.

The overlay is intentionally decoupled from :class:`ShipComposite` — it
consumes regions in *grid coordinates* and renders to screen coordinates
given an origin and cell size, so it composes cleanly over any ship
surface (player or enemy). Callers construct regions from their own data
source (``PlacedSlot`` footprints today, enemy template placements once
Combat C4 §4.1 lands).

All colors route through :mod:`engine.material_palette` so the overlay
participates in colorblind remap.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.2``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pygame

from spacegame.engine.material_palette import get_band, get_role, is_valid_band

# ---------------------------------------------------------------------------
# State enum + region dataclass
# ---------------------------------------------------------------------------


class ModuleOverlayState(Enum):
    """Persistent per-module overlay state.

    ``FLASH`` is explicitly not a persistent state — see
    :meth:`ShipModuleOverlay.trigger_flash` for the transient pulse.
    """

    NORMAL = "normal"
    HIGHLIGHTED = "highlighted"
    COMMITTED = "committed"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"


@dataclass
class ModuleRegion:
    """One module's footprint in ship-grid coordinates.

    ``x``, ``y``, ``w``, ``h`` are grid cells (not pixels). The overlay
    multiplies by ``cell_size`` during render to get screen pixels.
    """

    module_id: str
    x: int
    y: int
    w: int
    h: int
    state: ModuleOverlayState = ModuleOverlayState.NORMAL


# ---------------------------------------------------------------------------
# Palette mapping + constants
# ---------------------------------------------------------------------------

# Per spec §4.2 state-color discipline.
_HIGHLIGHT_ROLE = "hud_warning"
_COMMITTED_ROLE = "hud_critical"
_DAMAGED_TINT_ROLE = "rivet"
_DESTROYED_OUTLINE_ROLE = "seam"

# Outline thickness in screen pixels (spec §4.2: "2-pixel inset outline").
OUTLINE_PX = 2

# Flash defaults per spec §4.2: "100ms" specular flash using the
# targeted material's band. Callers override the band name per hit.
FLASH_DURATION = 0.1
_FLASH_DEFAULT_BAND = "solari_chrome"

# Tint alphas — tuned for overlay over dark ship pixels while keeping
# the underlying material legible.
_HIGHLIGHT_BG_ALPHA = 48
_COMMITTED_BG_ALPHA = 72
_DAMAGED_TINT_ALPHA = 96
_DESTROYED_FILL_ALPHA = 210
_FLASH_ALPHA_PEAK = 200


# ---------------------------------------------------------------------------
# Overlay
# ---------------------------------------------------------------------------


@dataclass
class _FlashState:
    """Transient flash overlay on top of whatever persistent state is set."""

    elapsed: float
    duration: float
    color: tuple[int, int, int]


class ShipModuleOverlay:
    """Module-targeting + damage overlay (spec §4.2).

    Lifecycle:
      1. Construct once per ship (player or enemy).
      2. Register every targetable region via :meth:`register_region`.
      3. Call :meth:`set_state` when persistent state changes (targeting,
         damage thresholds, destruction).
      4. Call :meth:`trigger_flash` on impact frames.
      5. Call :meth:`update(dt)` every frame.
      6. Call :meth:`render` every frame *after* the ship composite.
    """

    def __init__(self) -> None:
        self._regions: dict[str, ModuleRegion] = {}
        self._flashes: dict[str, _FlashState] = {}

    # ---- registration ------------------------------------------------------

    def register_region(self, region: ModuleRegion) -> None:
        """Register a module region. Overwrites any prior entry with the same id."""
        self._regions[region.module_id] = region

    def get_region(self, module_id: str) -> Optional[ModuleRegion]:
        return self._regions.get(module_id)

    def module_ids(self) -> tuple[str, ...]:
        return tuple(self._regions.keys())

    def clear(self) -> None:
        self._regions.clear()
        self._flashes.clear()

    # ---- state + flash -----------------------------------------------------

    def set_state(self, module_id: str, state: ModuleOverlayState) -> bool:
        """Update persistent state. Returns True when the state changed.

        Destroyed is terminal — once a module is marked destroyed, further
        ``set_state`` calls are ignored (the region stays destroyed for
        the remainder of combat per spec §4.2).
        """
        region = self._regions.get(module_id)
        if region is None:
            return False
        if region.state == ModuleOverlayState.DESTROYED:
            return False
        if region.state == state:
            return False
        region.state = state
        return True

    def trigger_flash(
        self,
        module_id: str,
        band_name: str = _FLASH_DEFAULT_BAND,
        duration: float = FLASH_DURATION,
    ) -> bool:
        """Start a 100ms specular flash on the given module.

        ``band_name`` is the targeted material's shade band — the overlay
        uses that band's brightest entry (index ``-1``) as the flash color.
        Unknown or malformed band names fall back to solari_chrome so the
        flash still fires visibly (it just won't be palette-exact for that
        material).

        Destroyed modules no longer flash.
        """
        region = self._regions.get(module_id)
        if region is None or region.state == ModuleOverlayState.DESTROYED:
            return False
        resolved_band = band_name if is_valid_band(band_name) else _FLASH_DEFAULT_BAND
        band = get_band(resolved_band)
        self._flashes[module_id] = _FlashState(
            elapsed=0.0,
            duration=max(1e-6, duration),
            color=band[-1],  # specular — brightest stop
        )
        return True

    def has_active_flash(self, module_id: str) -> bool:
        return module_id in self._flashes

    # ---- lifecycle ---------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance flash timers and prune expired ones."""
        if dt <= 0 or not self._flashes:
            return
        expired: list[str] = []
        for mid, flash in self._flashes.items():
            flash.elapsed += dt
            if flash.elapsed >= flash.duration:
                expired.append(mid)
        for mid in expired:
            del self._flashes[mid]

    # ---- hit detection -----------------------------------------------------

    def module_at_pixel(
        self,
        local_px: int,
        local_py: int,
        cell_size: int,
    ) -> Optional[str]:
        """Return the module_id whose region contains the given ship-local pixel.

        ``local_px`` / ``local_py`` are measured from the top-left of the
        ship composite surface. Returns ``None`` if no region contains
        the pixel. When regions overlap the first registered match wins —
        callers should avoid registering overlapping regions.
        """
        if cell_size <= 0:
            return None
        for region in self._regions.values():
            left = region.x * cell_size
            top = region.y * cell_size
            right = left + region.w * cell_size
            bottom = top + region.h * cell_size
            if left <= local_px < right and top <= local_py < bottom:
                return region.module_id
        return None

    # ---- rendering ---------------------------------------------------------

    def render(
        self,
        surface: pygame.Surface,
        origin_x: int,
        origin_y: int,
        cell_size: int,
    ) -> None:
        """Paint every region's overlay onto ``surface``.

        ``origin_x`` / ``origin_y`` locate the ship composite's top-left
        on ``surface``; ``cell_size`` is the pixel size of one grid cell.
        Call AFTER painting the ship composite (spec §4.2: overlay
        renders between composite and VFX).
        """
        if cell_size <= 0:
            return
        for region in self._regions.values():
            rect = pygame.Rect(
                origin_x + region.x * cell_size,
                origin_y + region.y * cell_size,
                region.w * cell_size,
                region.h * cell_size,
            )
            self._render_state(surface, rect, region.state)
        # Flashes render above persistent state.
        for module_id, flash in self._flashes.items():
            flash_region = self._regions.get(module_id)
            if flash_region is None:
                continue
            rect = pygame.Rect(
                origin_x + flash_region.x * cell_size,
                origin_y + flash_region.y * cell_size,
                flash_region.w * cell_size,
                flash_region.h * cell_size,
            )
            self._render_flash(surface, rect, flash)

    # ---- internals ---------------------------------------------------------

    @staticmethod
    def _render_state(
        surface: pygame.Surface,
        rect: pygame.Rect,
        state: ModuleOverlayState,
    ) -> None:
        if state == ModuleOverlayState.NORMAL:
            return
        if state == ModuleOverlayState.HIGHLIGHTED:
            ShipModuleOverlay._paint_tint(surface, rect, _HIGHLIGHT_ROLE, _HIGHLIGHT_BG_ALPHA)
            ShipModuleOverlay._paint_inset_outline(surface, rect, _HIGHLIGHT_ROLE)
            return
        if state == ModuleOverlayState.COMMITTED:
            ShipModuleOverlay._paint_tint(surface, rect, _COMMITTED_ROLE, _COMMITTED_BG_ALPHA)
            ShipModuleOverlay._paint_inset_outline(surface, rect, _COMMITTED_ROLE)
            return
        if state == ModuleOverlayState.DAMAGED:
            ShipModuleOverlay._paint_tint(surface, rect, _DAMAGED_TINT_ROLE, _DAMAGED_TINT_ALPHA)
            return
        if state == ModuleOverlayState.DESTROYED:
            # Spec §4.2: steel band shadow_deep fill + seam outline.
            steel_deep = get_band("steel")[0]
            fill = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            fill.fill((*steel_deep, _DESTROYED_FILL_ALPHA))
            surface.blit(fill, rect.topleft)
            seam = get_role(_DESTROYED_OUTLINE_ROLE)
            pygame.draw.rect(surface, seam, rect, width=1)
            return

    @staticmethod
    def _render_flash(
        surface: pygame.Surface,
        rect: pygame.Rect,
        flash: _FlashState,
    ) -> None:
        # Ease out: full alpha at start, decays linearly over duration.
        progress = min(1.0, flash.elapsed / flash.duration)
        alpha = max(0, int(_FLASH_ALPHA_PEAK * (1.0 - progress)))
        if alpha == 0:
            return
        fill = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        fill.fill((*flash.color, alpha))
        surface.blit(fill, rect.topleft)

    @staticmethod
    def _paint_tint(
        surface: pygame.Surface,
        rect: pygame.Rect,
        role: str,
        alpha: int,
    ) -> None:
        color = get_role(role)
        tint = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        tint.fill((*color, alpha))
        surface.blit(tint, rect.topleft)

    @staticmethod
    def _paint_inset_outline(
        surface: pygame.Surface,
        rect: pygame.Rect,
        role: str,
    ) -> None:
        """Draw a 2px outline inset one pixel from the region edge.

        The 1-pixel inset keeps the outline visible when adjacent regions
        share an edge — without it, two touching modules' outlines would
        overlap and read as a single thicker line.
        """
        if rect.width <= 2 or rect.height <= 2:
            return
        color = get_role(role)
        inset = rect.inflate(-2, -2)
        pygame.draw.rect(surface, color, inset, width=OUTLINE_PX)
