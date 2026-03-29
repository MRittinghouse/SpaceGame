"""Ship composite renderer — turns a ShipBuild into a polished sprite.

Applies the auto-detailing pipeline to raw pixel data, producing a
pygame Surface that renders the player's ship everywhere in the game.
Each step adds visual polish so that even a simple build looks good.

Pipeline:
1. Material Color Fill — base pixel colors
2. Panel Line Generation — darker lines between different materials
3. Edge Highlight — lighter border on top/left silhouette edges
4. Material Texture — per-material micro-detail (hull + module materials)
5. Edge Outline — dark border around entire ship silhouette
6. Slot Indicators — subtle colored overlay on equipment slots
7. Engine Glow — animated warm color at engine slots and exhaust_port pixels

Supports both legacy pixel-only builds and module-based builds.
Module pixels are resolved into the pixel map alongside hull pixels.

Part of the Shipyard Overhaul — Phases C + 3.
"""

from typing import Optional

import pygame

from spacegame.models.ship_build import (
    HullMaterial,
    ShipBuild,
)


def _darken(color: tuple[int, int, int], factor: float = 0.7) -> tuple[int, int, int]:
    """Darken a color by a factor (0.0 = black, 1.0 = unchanged)."""
    return (
        max(0, int(color[0] * factor)),
        max(0, int(color[1] * factor)),
        max(0, int(color[2] * factor)),
    )


def _lighten(color: tuple[int, int, int], amount: int = 30) -> tuple[int, int, int]:
    """Lighten a color by adding a flat amount to each channel."""
    return (
        min(255, color[0] + amount),
        min(255, color[1] + amount),
        min(255, color[2] + amount),
    )


class ShipComposite:
    """Cached rendered surface for a player's ship build.

    Generates a pixel-art sprite from the build's pixel grid by
    applying an auto-detailing pipeline. The result is cached and
    scaled on demand for different display contexts (combat, map, HUD).
    """

    # Engine glow animation
    ENGINE_GLOW_PERIOD = 0.6  # Seconds per full cycle
    ENGINE_COLOR_BRIGHT = (255, 180, 60)
    ENGINE_COLOR_DIM = (200, 120, 40)
    ENGINE_SURROUND = (255, 220, 120)

    def __init__(
        self,
        build: ShipBuild,
        materials: dict[str, HullMaterial],
        module_catalog: Optional[dict] = None,
    ) -> None:
        self._build = build
        self._materials = materials
        self._module_catalog = module_catalog or {}
        self._clean_surface: Optional[pygame.Surface] = None  # Without engine glow
        self._base_surface: Optional[pygame.Surface] = None  # With current glow frame
        self._scaled_cache: dict[int, pygame.Surface] = {}
        self._engine_timer: float = 0.0
        self._engine_frame: int = 0  # 0 or 1
        self._dirty: bool = True

        # Pre-compute pixel lookup for fast neighbor queries
        self._pixel_map: dict[tuple[int, int], str] = {}
        self._build_pixel_map()

    def _build_pixel_map(self) -> None:
        """Build the (x, y) -> material_id lookup from modules + hull pixels."""
        self._pixel_map.clear()
        for p in self._build.pixels:
            self._pixel_map[(p.x, p.y)] = p.material_id

    def invalidate(self) -> None:
        """Mark as needing rebuild (call when build changes)."""
        self._dirty = True
        self._scaled_cache.clear()
        self._build_pixel_map()

    def get_surface(self, scale: int = 1) -> pygame.Surface:
        """Get the rendered ship at the given scale.

        Args:
            scale: Integer scale factor (1 = native, 2 = double, etc.)

        Returns:
            Rendered pygame Surface at the requested scale.
        """
        if self._dirty:
            self._rebuild()

        if scale not in self._scaled_cache:
            if self._base_surface is None:
                self._rebuild()
            w = self._base_surface.get_width() * scale
            h = self._base_surface.get_height() * scale
            if scale == 1:
                self._scaled_cache[scale] = self._base_surface.copy()
            else:
                self._scaled_cache[scale] = pygame.transform.scale(
                    self._base_surface,
                    (w, h),
                )
        return self._scaled_cache[scale]

    def update(self, dt: float) -> None:
        """Advance engine glow animation.

        Args:
            dt: Delta time in seconds.
        """
        self._engine_timer += dt
        new_frame = int(self._engine_timer / (self.ENGINE_GLOW_PERIOD / 2)) % 2
        if new_frame != self._engine_frame:
            self._engine_frame = new_frame
            # Rebuild base from clean + fresh glow (no accumulation)
            self._scaled_cache.clear()
            if self._clean_surface is not None:
                self._base_surface = self._clean_surface.copy()
                self._apply_engine_glow(self._base_surface)

    def _rebuild(self) -> None:
        """Execute the full rendering pipeline."""
        canvas_w = self._build.canvas_w
        canvas_h = self._build.canvas_h
        surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)

        # Step 1: Material color fill
        self._fill_materials(surf)

        # Step 2: Panel lines (between different materials)
        self._apply_panel_lines(surf)

        # Step 3: Edge highlight (top/left silhouette edges)
        self._apply_edge_highlight(surf)

        # Step 4: Material texture (per-material detail)
        self._apply_material_texture(surf)

        # Step 5: Edge outline (dark border around silhouette)
        self._apply_outline(surf)

        # Step 6: Slot indicators (subtle overlay)
        self._apply_slot_indicators(surf)

        # Step 7: Engine glow (animated)
        self._apply_engine_glow(surf)

        self._clean_surface = surf.convert_alpha()
        self._base_surface = self._clean_surface.copy()
        self._dirty = False
        self._scaled_cache.clear()

    # === Pipeline Steps ===

    def _fill_materials(self, surf: pygame.Surface) -> None:
        """Step 1: Fill each pixel with its material's primary color."""
        for (x, y), mat_id in self._pixel_map.items():
            mat = self._materials.get(mat_id)
            if mat:
                surf.set_at((x, y), (*mat.color_primary, 255))

    def _apply_panel_lines(self, surf: pygame.Surface) -> None:
        """Step 2: Darken pixels adjacent to different materials.

        Where two different materials meet, the shared edge pixel is
        tinted slightly darker, creating a natural panel-line effect.
        """
        for (x, y), mat_id in self._pixel_map.items():
            # Check right and bottom neighbors
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                neighbor_mat = self._pixel_map.get((nx, ny))
                if neighbor_mat and neighbor_mat != mat_id:
                    # Darken the current pixel slightly
                    current = surf.get_at((x, y))
                    darkened = _darken((current.r, current.g, current.b), 0.75)
                    surf.set_at((x, y), (*darkened, 255))
                    break  # Only darken once per pixel

    def _apply_edge_highlight(self, surf: pygame.Surface) -> None:
        """Step 3: Lighten pixels on the top/left edge of the silhouette.

        Simulates top-left lighting — standard in pixel art. Pixels
        with no filled neighbor above or to the left get a highlight.
        """
        for (x, y), mat_id in self._pixel_map.items():
            has_above = (x, y - 1) in self._pixel_map
            has_left = (x - 1, y) in self._pixel_map

            if not has_above or not has_left:
                mat = self._materials.get(mat_id)
                if mat:
                    highlight = mat.color_highlight
                    if highlight != (0, 0, 0):
                        # Blend highlight with current color
                        current = surf.get_at((x, y))
                        blended = (
                            min(255, (current.r + highlight[0]) // 2),
                            min(255, (current.g + highlight[1]) // 2),
                            min(255, (current.b + highlight[2]) // 2),
                        )
                        surf.set_at((x, y), (*blended, 255))

    def _apply_material_texture(self, surf: pygame.Surface) -> None:
        """Step 6: Apply per-material micro-detail.

        Each material type has a subtle texture pattern that adds
        visual richness without overwhelming the silhouette:
        - Heavy Armor: rivet pattern (every 3rd pixel darker)
        - Shield Crystal: center-bright gradient
        - Stealth Composite: flat matte (no change)
        - Salvage Scrap: patchy worn look (random darker pixels)
        """
        import random as _rng

        scrap_rng = _rng.Random(42)  # Deterministic for consistency

        for (x, y), mat_id in self._pixel_map.items():
            current = surf.get_at((x, y))

            if mat_id == "heavy_armor" or mat_id == "reinforced_plate":
                # Rivet pattern: every 3rd pixel slightly darker
                if (x + y) % 3 == 0:
                    darkened = _darken((current.r, current.g, current.b), 0.88)
                    surf.set_at((x, y), (*darkened, 255))

            elif mat_id == "salvage_scrap":
                # Patchy: 15% of pixels get a random tint shift
                if scrap_rng.random() < 0.15:
                    shift = scrap_rng.randint(-15, 15)
                    shifted = (
                        max(0, min(255, current.r + shift)),
                        max(0, min(255, current.g + shift - 5)),
                        max(0, min(255, current.b + shift - 10)),
                    )
                    surf.set_at((x, y), (*shifted, 255))

            elif mat_id == "shield_crystal" or mat_id == "quantum_lattice":
                # Subtle shimmer: alternate rows are slightly brighter
                if y % 2 == 0:
                    bright = _lighten((current.r, current.g, current.b), 10)
                    surf.set_at((x, y), (*bright, 255))

            elif mat_id == "bio_hull":
                # Organic veins: pixels adjacent to empty space are lighter
                has_empty_neighbor = any(
                    (x + dx, y + dy) not in self._pixel_map
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                )
                if has_empty_neighbor:
                    veined = _lighten((current.r, current.g, current.b), 15)
                    surf.set_at((x, y), (*veined, 255))

            elif mat_id == "crimson_steel":
                # Subtle red pulse pattern
                if (x * 7 + y * 13) % 5 == 0:
                    pulse = _lighten((current.r, current.g, current.b), 8)
                    surf.set_at((x, y), (*pulse, 255))

            # --- Module-specific material textures ---

            elif mat_id == "cockpit_glass":
                # Reflection band: top edge of glass gets a bright highlight
                if (x, y - 1) not in self._pixel_map or self._pixel_map.get(
                    (x, y - 1)
                ) != "cockpit_glass":
                    bright = _lighten((current.r, current.g, current.b), 18)
                    surf.set_at((x, y), (*bright, 255))

            elif mat_id == "console_panel":
                # Instrument dots: alternating pixels get a green/amber glow
                if (x + y) % 2 == 0:
                    dotted = (
                        min(255, current.r + 3),
                        min(255, current.g + 12),
                        min(255, current.b + 2),
                    )
                    surf.set_at((x, y), (*dotted, 255))

            elif mat_id == "exhaust_port":
                # Warm inner glow tint (main glow is animated in step 7)
                warm = (
                    min(255, current.r + 10),
                    min(255, current.g + 5),
                    current.b,
                )
                surf.set_at((x, y), (*warm, 255))

            elif mat_id == "weapon_barrel":
                # Machined groove: alternate rows slightly lighter
                if y % 2 == 0:
                    groove = _lighten((current.r, current.g, current.b), 6)
                    surf.set_at((x, y), (*groove, 255))

            elif mat_id == "shield_emitter":
                # Cyan shimmer: same pattern as shield_crystal
                if y % 2 == 0:
                    bright = _lighten((current.r, current.g, current.b), 10)
                    surf.set_at((x, y), (*bright, 255))

            elif mat_id == "sensor_dish":
                # Interior pixels brighter (dish center effect)
                all_neighbors_filled = all(
                    (x + dx, y + dy) in self._pixel_map
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                )
                if all_neighbors_filled:
                    bright = _lighten((current.r, current.g, current.b), 14)
                    surf.set_at((x, y), (*bright, 255))

            elif mat_id == "cargo_interior":
                # Crate grid: every 3rd pixel darker
                if (x + y) % 3 == 0:
                    crate = _darken((current.r, current.g, current.b), 0.90)
                    surf.set_at((x, y), (*crate, 255))

            elif mat_id == "reactor_core":
                # Energy pulse: diagonal wave
                if (x * 5 + y * 11) % 4 == 0:
                    pulse = _lighten((current.r, current.g, current.b), 12)
                    surf.set_at((x, y), (*pulse, 255))

            elif mat_id == "crew_quarters_interior":
                # Warm interior rows (window/lighting effect)
                if y % 2 == 0:
                    warm = _lighten((current.r, current.g, current.b), 6)
                    surf.set_at((x, y), (*warm, 255))

            # --- Manufacturer hull textures ---

            elif mat_id == "module_hull_foundry":
                # Industrial rivets (same pattern as heavy_armor)
                if (x + y) % 3 == 0:
                    rivet = _darken((current.r, current.g, current.b), 0.90)
                    surf.set_at((x, y), (*rivet, 255))

            elif mat_id == "module_hull_talon":
                # Sharp angular highlights
                if (x + y) % 4 == 0:
                    edge = _lighten((current.r, current.g, current.b), 7)
                    surf.set_at((x, y), (*edge, 255))

            elif mat_id == "module_hull_meridian":
                # Luxury shimmer
                if x % 2 == 0:
                    shimmer = _lighten((current.r, current.g, current.b), 5)
                    surf.set_at((x, y), (*shimmer, 255))

            elif mat_id == "module_hull_salvage":
                # Patchy worn (reuse salvage scrap pattern)
                if scrap_rng.random() < 0.15:
                    shift = scrap_rng.randint(-12, 12)
                    shifted = (
                        max(0, min(255, current.r + shift)),
                        max(0, min(255, current.g + shift - 3)),
                        max(0, min(255, current.b + shift - 6)),
                    )
                    surf.set_at((x, y), (*shifted, 255))

            # --- Legendary material textures ---

            elif mat_id == "legendary_hull":
                # Golden shimmer: alternating bright/dim in a wave
                if (x + y) % 2 == 0:
                    shimmer = _lighten((current.r, current.g, current.b), 12)
                    surf.set_at((x, y), (*shimmer, 255))

            elif mat_id == "legendary_core":
                # Purple energy pulse: strong diagonal wave
                if (x * 3 + y * 7) % 4 == 0:
                    pulse = _lighten((current.r, current.g, current.b), 18)
                    surf.set_at((x, y), (*pulse, 255))

            elif mat_id == "void_material":
                # Void absorption: very subtle dark ripple, almost imperceptible
                if (x * 5 + y * 3) % 6 == 0:
                    void_dark = _darken((current.r, current.g, current.b), 0.7)
                    surf.set_at((x, y), (*void_dark, 255))

            elif mat_id == "phantom_material":
                # Phase flicker: some pixels slightly transparent-looking
                if (x + y * 2) % 3 == 0:
                    phase = _lighten((current.r, current.g, current.b), 20)
                    surf.set_at((x, y), (*phase, 255))

    def _apply_outline(self, surf: pygame.Surface) -> None:
        """Step 4: Draw a 1px dark outline around the entire silhouette.

        For each empty pixel adjacent (4-directional) to a filled
        pixel, draw a dark outline pixel. This makes the ship read
        clearly against any background.
        """
        canvas_w = surf.get_width()
        canvas_h = surf.get_height()
        outline_color = (15, 18, 30, 200)
        outline_pixels: set[tuple[int, int]] = set()

        for x, y in self._pixel_map:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in self._pixel_map:
                    if 0 <= nx < canvas_w and 0 <= ny < canvas_h:
                        outline_pixels.add((nx, ny))

        for x, y in outline_pixels:
            surf.set_at((x, y), outline_color)

    def _apply_slot_indicators(self, surf: pygame.Surface) -> None:
        """Step 5: Draw subtle colored overlays on equipment slot positions.

        Uses placed_slots with SlotDefinition lookups for slot type/footprint.
        """
        if not self._build.placed_slots:
            return
        try:
            from spacegame.data_loader import get_data_loader

            slot_defs = getattr(get_data_loader(), "slot_definitions", {})
        except Exception:
            return
        if not slot_defs:
            return
        for ps in self._build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            color = sdef.color  # (r, g, b) from slot definition
            alpha = 40 / 255.0  # Subtle overlay
            fw, fh, mask = sdef.get_rotated(ps.rotation)
            for dy in range(fh):
                for dx in range(fw):
                    if mask and dy < len(mask) and dx < len(mask[dy]) and not mask[dy][dx]:
                        continue
                    px, py = ps.x + dx, ps.y + dy
                    if 0 <= px < surf.get_width() and 0 <= py < surf.get_height():
                        current = surf.get_at((px, py))
                        if current.a == 0:
                            continue  # Skip transparent pixels
                        blended = (
                            int(current.r * (1 - alpha) + color[0] * alpha),
                            int(current.g * (1 - alpha) + color[1] * alpha),
                            int(current.b * (1 - alpha) + color[2] * alpha),
                            current.a,
                        )
                        surf.set_at((px, py), blended)

    def _apply_engine_glow(self, surf: pygame.Surface) -> None:
        """Step 7: Animated engine glow at engine slots and exhaust_port pixels.

        Frame 0: Bright warm center
        Frame 1: Dimmer, slightly shifted

        For legacy builds: glow at engine slot centers.
        For module builds: glow on exhaust_port material pixels.
        """
        if self._engine_frame == 0:
            glow_color = self.ENGINE_COLOR_BRIGHT
        else:
            glow_color = self.ENGINE_COLOR_DIM

        sw, sh = surf.get_width(), surf.get_height()

        # Glow on exhaust_port pixels directly
        for (x, y), mat_id in self._pixel_map.items():
            if mat_id == "exhaust_port":
                if 0 <= x < sw and 0 <= y < sh:
                    surf.set_at((x, y), (*glow_color, 255))
