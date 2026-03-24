"""Ship composite renderer — turns a ShipBuild into a polished sprite.

Applies the auto-detailing pipeline to raw pixel data, producing a
pygame Surface that renders the player's ship everywhere in the game.
Each step adds visual polish so that even a simple build looks good.

Pipeline:
1. Material Color Fill — base pixel colors
2. Panel Line Generation — darker lines between different materials
3. Edge Highlight — lighter border on top/left silhouette edges
4. Edge Outline — dark border around entire ship silhouette
5. Slot Indicators — subtle colored overlay on equipment slots
6. Material Texture — per-material micro-detail
7. Engine Glow — animated warm color at engine slot positions

Part of the Shipyard Overhaul — Phase C.
"""

from typing import Optional

import pygame

from spacegame.models.ship_build import (
    HullMaterial,
    PlacedPixel,
    ShipBuild,
    WEIGHT_CLASSES,
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
    ) -> None:
        self._build = build
        self._materials = materials
        self._clean_surface: Optional[pygame.Surface] = None  # Without engine glow
        self._base_surface: Optional[pygame.Surface] = None   # With current glow frame
        self._scaled_cache: dict[int, pygame.Surface] = {}
        self._engine_timer: float = 0.0
        self._engine_frame: int = 0  # 0 or 1
        self._dirty: bool = True

        # Pre-compute pixel lookup for fast neighbor queries
        self._pixel_map: dict[tuple[int, int], str] = {}
        for p in build.pixels:
            self._pixel_map[(p.x, p.y)] = p.material_id

    def invalidate(self) -> None:
        """Mark as needing rebuild (call when build changes)."""
        self._dirty = True
        self._scaled_cache.clear()
        # Rebuild pixel map
        self._pixel_map.clear()
        for p in self._build.pixels:
            self._pixel_map[(p.x, p.y)] = p.material_id

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
                    self._base_surface, (w, h),
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
        wc = WEIGHT_CLASSES.get(self._build.weight_class, WEIGHT_CLASSES["medium"])
        canvas_w = wc.get("canvas_w", wc.get("canvas", 32))
        canvas_h = wc.get("canvas_h", wc.get("canvas", 32))
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
        canvas = surf.get_width()
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

        for (x, y) in self._pixel_map:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in self._pixel_map:
                    if 0 <= nx < canvas_w and 0 <= ny < canvas_h:
                        outline_pixels.add((nx, ny))

        for x, y in outline_pixels:
            surf.set_at((x, y), outline_color)

    def _apply_slot_indicators(self, surf: pygame.Surface) -> None:
        """Step 5: Draw subtle colored overlays on equipment slot positions."""
        slot_colors = {
            "weapon": (200, 60, 60, 35),
            "defense": (60, 120, 200, 35),
            "engine": (200, 140, 40, 35),
            "utility": (60, 180, 80, 35),
            "core": (200, 180, 60, 40),
        }
        for slot in self._build.slots:
            color = slot_colors.get(slot.slot_type, (150, 150, 150, 30))
            size = slot.size
            for dy in range(size):
                for dx in range(size):
                    px, py = slot.x + dx, slot.y + dy
                    if (px, py) in self._pixel_map:
                        current = surf.get_at((px, py))
                        # Blend slot color over existing
                        alpha = color[3] / 255.0
                        blended = (
                            int(current.r * (1 - alpha) + color[0] * alpha),
                            int(current.g * (1 - alpha) + color[1] * alpha),
                            int(current.b * (1 - alpha) + color[2] * alpha),
                            255,
                        )
                        surf.set_at((px, py), blended)

    def _apply_engine_glow(self, surf: pygame.Surface) -> None:
        """Step 7: Animated engine glow at engine slot positions.

        Frame 0: Bright warm center
        Frame 1: Dimmer, slightly shifted
        """
        for slot in self._build.slots:
            if slot.slot_type != "engine":
                continue
            cx = slot.x + slot.size // 2
            cy = slot.y + slot.size // 2

            if self._engine_frame == 0:
                glow_color = self.ENGINE_COLOR_BRIGHT
                surround = self.ENGINE_SURROUND
            else:
                glow_color = self.ENGINE_COLOR_DIM
                surround = _darken(self.ENGINE_SURROUND, 0.7)

            # Center pixel
            sw, sh = surf.get_width(), surf.get_height()
            if 0 <= cx < sw and 0 <= cy < sh:
                surf.set_at((cx, cy), (*glow_color, 255))

            # Surround pixels (cross pattern)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < sw and 0 <= ny < sh and (nx, ny) in self._pixel_map:
                    surf.set_at((nx, ny), (*surround, 220))
