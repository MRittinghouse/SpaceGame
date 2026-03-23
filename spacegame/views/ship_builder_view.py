"""Ship builder view — the pixel ship designer.

The player builds their ship on a grid by stamping geometric shapes
with chosen materials. The grid IS the ship sprite. Real-time stat
updates show the effect of every placement. Part of the Shipyard
Overhaul — Phase B1.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState, scale_x, scale_y,
)
from spacegame.views.base_view import BaseView
from spacegame.models.player import Player
from spacegame.models.ship_build import (
    HullShape, HullMaterial, PlacedPixel, DesignatedSlot,
    ShipBuild, ShipGridManager, ShipStatsComputer,
    ComputedShipStats, WEIGHT_CLASSES, SLOT_POOLS,
)
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel, draw_bar
from spacegame.engine.fonts import FontCache, FONT_BODY, FONT_LG, FONT_MD, FONT_SM, FONT_TITLE, FONT_XL, FONT_XS
from spacegame.utils.logger import logger


# Layout constants
GRID_AREA_X = scale_x(200)
GRID_AREA_Y = scale_y(50)
GRID_AREA_W = scale_x(500)
GRID_AREA_H = scale_y(500)

SHAPE_PANEL_X = scale_x(10)
SHAPE_PANEL_Y = scale_y(50)
SHAPE_PANEL_W = scale_x(180)
SHAPE_PANEL_H = scale_y(500)

MATERIAL_PANEL_X = WINDOW_WIDTH - scale_x(190)
MATERIAL_PANEL_Y = scale_y(50)
MATERIAL_PANEL_W = scale_x(180)
MATERIAL_PANEL_H = scale_y(260)

STATS_PANEL_Y = WINDOW_HEIGHT - scale_y(170)
STATS_PANEL_H = scale_y(160)

BAR_H = scale_y(14)


class ShipBuilderView(BaseView):
    """Interactive pixel ship builder.

    The player selects shapes from the palette, picks a material,
    and stamps them onto the grid. Stats update in real-time. The
    build is confirmed to become the player's active ship.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        data_loader: object,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.data_loader = data_loader
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = FontCache.get(FONT_TITLE)
        self.header_font = FontCache.get(FONT_XL)
        self.body_font = FontCache.get(FONT_BODY)
        self.small_font = FontCache.get(FONT_MD)
        self.tiny_font = FontCache.get(FONT_SM)
        self.label_font = FontCache.get(FONT_XS)

        # Background
        self.background = AnimatedBackground(
            "industrial", WINDOW_WIDTH, WINDOW_HEIGHT, seed=90,
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(160)

        # Build state
        self.build: ShipBuild = ShipBuild(
            weight_class=self._get_initial_weight_class(),
        )
        self.grid_manager = ShipGridManager(self.build.weight_class)
        self._computed_stats: Optional[ComputedShipStats] = None
        self._modified = False

        # Tool state
        self._selected_shape: Optional[HullShape] = None
        self._selected_material_id: str = "standard_plate"
        self._shape_rotation: int = 0  # 0-3 (90° increments)
        self._shape_flipped: bool = False

        # Shape palette scroll
        self._shape_scroll_offset: int = 0
        self._shape_category_filter: str = "all"
        self._shape_categories = ["all", "basic", "intermediate", "advanced", "exotic", "faction"]

        # Material list scroll
        self._material_scroll_offset: int = 0

        # UI elements
        self.confirm_button: Optional[pygame_gui.elements.UIButton] = None
        self.clear_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

    def _get_initial_weight_class(self) -> str:
        """Get the best weight class the player has unlocked."""
        order = ["xlarge", "large", "medium", "small", "tiny"]
        for wc in order:
            if wc in self.player.unlocked_weight_classes:
                return wc
        return "tiny"

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered Ship Builder")

        # Load or create build from player's ship
        if self.player.ship.build:
            self.build = ShipBuild.from_dict(self.player.ship.build.to_dict())
        else:
            # Generate a preset from the current ship type
            from spacegame.models.ship_presets import generate_preset_from_ship_type
            self.build = generate_preset_from_ship_type(self.player.ship.ship_type)

        self.grid_manager = ShipGridManager(self.build.weight_class)
        self._modified = False
        self._recompute_stats()
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        self._destroy_ui()
        btn_w = scale_x(130)
        btn_h = scale_y(36)
        btn_y = WINDOW_HEIGHT - scale_y(45)

        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - btn_w - scale_x(20), btn_y, btn_w, btn_h,
            ),
            text="CONFIRM BUILD",
            manager=self.ui_manager,
        )
        self.clear_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - btn_w * 2 - scale_x(30), btn_y, btn_w, btn_h,
            ),
            text="CLEAR ALL",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(20), btn_y, btn_w, btn_h,
            ),
            text="BACK",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for btn in [self.confirm_button, self.clear_button, self.back_button]:
            if btn:
                btn.kill()
        self.confirm_button = None
        self.clear_button = None
        self.back_button = None

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.SHIPYARD
                return
            if event.ui_element == self.confirm_button:
                self._confirm_build()
                return
            if event.ui_element == self.clear_button:
                self.build.pixels.clear()
                self.build.slots.clear()
                self._modified = True
                self._recompute_stats()
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._shape_rotation = (self._shape_rotation + 1) % 4
            elif event.key == pygame.K_q:
                self._shape_flipped = not self._shape_flipped
            elif event.key == pygame.K_ESCAPE:
                self.next_state = GameState.SHIPYARD

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                self._handle_left_click(event.pos)
            elif event.button == 3:  # Right click — erase
                self._handle_right_click(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if mx < GRID_AREA_X:
                # Shape palette scroll
                self._shape_scroll_offset = max(
                    0, self._shape_scroll_offset - event.y * 30,
                )
            elif mx > MATERIAL_PANEL_X:
                # Material panel scroll
                self._material_scroll_offset = max(
                    0, self._material_scroll_offset - event.y * 30,
                )

    def _handle_left_click(self, pos: tuple[int, int]) -> None:
        mx, my = pos

        # Click on shape palette
        if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W:
            self._handle_shape_palette_click(mx, my)
            return

        # Click on material panel
        if MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W:
            self._handle_material_panel_click(mx, my)
            return

        # Click on grid — place shape
        grid_pos = self._screen_to_grid(mx, my)
        if grid_pos and self._selected_shape:
            self._place_shape_at(*grid_pos)

    def _handle_right_click(self, pos: tuple[int, int]) -> None:
        """Erase pixel at clicked grid position."""
        grid_pos = self._screen_to_grid(pos[0], pos[1])
        if grid_pos:
            gx, gy = grid_pos
            self.build.pixels = [
                p for p in self.build.pixels
                if not (p.x == gx and p.y == gy)
            ]
            self._modified = True
            self._recompute_stats()

    def _handle_shape_palette_click(self, mx: int, my: int) -> None:
        """Select a shape from the palette or switch category filter."""
        # Category tabs at top
        tab_y = SHAPE_PANEL_Y + 5
        tab_h = scale_y(20)
        for i, cat in enumerate(self._shape_categories):
            tab_x = SHAPE_PANEL_X + 5 + i * scale_x(28)
            if tab_x <= mx < tab_x + scale_x(26) and tab_y <= my < tab_y + tab_h:
                self._shape_category_filter = cat
                self._shape_scroll_offset = 0
                return

        # Shape items below tabs
        shapes = self._get_filtered_shapes()
        item_h = scale_y(36)
        start_y = SHAPE_PANEL_Y + scale_y(30) - self._shape_scroll_offset
        for i, shape in enumerate(shapes):
            iy = start_y + i * item_h
            if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W and iy <= my < iy + item_h:
                self._selected_shape = shape
                self._shape_rotation = 0
                self._shape_flipped = False
                return

    def _handle_material_panel_click(self, mx: int, my: int) -> None:
        """Select a material from the panel."""
        materials = self._get_available_materials()
        item_h = scale_y(30)
        start_y = MATERIAL_PANEL_Y + scale_y(25) - self._material_scroll_offset
        for i, mat in enumerate(materials):
            iy = start_y + i * item_h
            if MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W and iy <= my < iy + item_h:
                self._selected_material_id = mat.id
                return

    def _place_shape_at(self, gx: int, gy: int) -> None:
        """Place the selected shape at the given grid position."""
        if not self._selected_shape:
            return
        shape = self._get_transformed_shape()
        material = self._get_selected_material()
        if material is None:
            return

        ok, msg = self.grid_manager.can_place_shape(
            shape, gx, gy, material, self.build.pixels,
        )
        if not ok:
            return

        # Stamp pixels
        for row_idx, row in enumerate(shape.pixel_mask):
            for col_idx, filled in enumerate(row):
                if filled:
                    px, py = gx + col_idx, gy + row_idx
                    self.build.pixels.append(
                        PlacedPixel(px, py, self._selected_material_id)
                    )
        self._modified = True
        self._recompute_stats()

    def _confirm_build(self) -> None:
        """Apply the current build to the player's ship."""
        self.player.ship.set_build(self.build)
        # Update hull/shields to match new build stats
        if self._computed_stats:
            self.player.ship.current_hull = self._computed_stats.hull
            self.player.ship.current_shields = self._computed_stats.shields
        self._modified = False
        logger.info("Ship build confirmed")
        self.next_state = GameState.SHIPYARD

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def _recompute_stats(self) -> None:
        materials = getattr(self.data_loader, "hull_materials", {})
        equipment = getattr(self.data_loader, "upgrades", {})
        self._computed_stats = ShipStatsComputer.compute(
            self.build, materials, equipment,
        )

    def _get_filtered_shapes(self) -> list[HullShape]:
        shapes = list(getattr(self.data_loader, "hull_shapes", {}).values())
        unlocked = self.player.unlocked_shapes
        shapes = [s for s in shapes if s.id in unlocked]
        if self._shape_category_filter != "all":
            shapes = [s for s in shapes if s.category == self._shape_category_filter]
        return shapes

    def _get_available_materials(self) -> list[HullMaterial]:
        materials = list(getattr(self.data_loader, "hull_materials", {}).values())
        unlocked = self.player.unlocked_materials
        return [m for m in materials if m.id in unlocked]

    def _get_selected_material(self) -> Optional[HullMaterial]:
        materials = getattr(self.data_loader, "hull_materials", {})
        return materials.get(self._selected_material_id)

    def _get_transformed_shape(self) -> HullShape:
        """Get the selected shape with current rotation/flip applied."""
        shape = self._selected_shape
        if shape is None:
            return HullShape(id="", name="", description="", pixel_mask=[[]])
        if self._shape_flipped:
            shape = shape.flipped()
        if self._shape_rotation > 0:
            shape = shape.rotated(self._shape_rotation)
        return shape

    # ------------------------------------------------------------------
    # Grid coordinate conversion
    # ------------------------------------------------------------------

    def _get_cell_size(self) -> int:
        canvas = self.build.canvas_size
        return min(GRID_AREA_W, GRID_AREA_H) // canvas

    def _get_grid_origin(self) -> tuple[int, int]:
        canvas = self.build.canvas_size
        cell = self._get_cell_size()
        ox = GRID_AREA_X + (GRID_AREA_W - canvas * cell) // 2
        oy = GRID_AREA_Y + (GRID_AREA_H - canvas * cell) // 2
        return ox, oy

    def _screen_to_grid(self, sx: int, sy: int) -> Optional[tuple[int, int]]:
        ox, oy = self._get_grid_origin()
        cell = self._get_cell_size()
        gx = (sx - ox) // cell
        gy = (sy - oy) // cell
        canvas = self.build.canvas_size
        if 0 <= gx < canvas and 0 <= gy < canvas:
            return gx, gy
        return None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.background.update(dt)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Header
        title = self.title_font.render(
            f"DRYDOCK — {self.build.weight_class.upper()} ({self.build.canvas_size}×{self.build.canvas_size})",
            True, Colors.TEXT_HIGHLIGHT,
        )
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 10))

        # Main panels
        self._render_grid(screen)
        self._render_shape_palette(screen)
        self._render_material_panel(screen)
        self._render_stats_panel(screen)

    def _render_grid(self, screen: pygame.Surface) -> None:
        """Render the ship building grid with placed pixels."""
        canvas = self.build.canvas_size
        cell = self._get_cell_size()
        ox, oy = self._get_grid_origin()

        # Grid background
        grid_w = canvas * cell
        grid_h = canvas * cell
        pygame.draw.rect(screen, (8, 10, 20), (ox, oy, grid_w, grid_h))

        # Grid lines (subtle)
        for i in range(canvas + 1):
            alpha_line = 30
            # Every 8 cells slightly brighter
            if i % 8 == 0:
                alpha_line = 50
            lx = ox + i * cell
            ly = oy + i * cell
            line_surf = pygame.Surface((1, grid_h), pygame.SRCALPHA)
            line_surf.fill((100, 120, 160, alpha_line))
            screen.blit(line_surf, (lx, oy))
            line_surf2 = pygame.Surface((grid_w, 1), pygame.SRCALPHA)
            line_surf2.fill((100, 120, 160, alpha_line))
            screen.blit(line_surf2, (ox, ly))

        # Filled pixels (material colors)
        materials = getattr(self.data_loader, "hull_materials", {})
        for pixel in self.build.pixels:
            mat = materials.get(pixel.material_id)
            color = mat.color_primary if mat else (128, 128, 128)
            px = ox + pixel.x * cell
            py = oy + pixel.y * cell
            pygame.draw.rect(screen, color, (px + 1, py + 1, cell - 1, cell - 1))

        # Slot indicators
        slot_colors = {
            "weapon": (200, 60, 60), "defense": (60, 120, 200),
            "engine": (200, 140, 40), "utility": (60, 180, 80),
            "core": (200, 180, 60),
        }
        for slot in self.build.slots:
            color = slot_colors.get(slot.slot_type, (150, 150, 150))
            sx = ox + slot.x * cell
            sy = oy + slot.y * cell
            size = slot.size * cell
            slot_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            slot_surf.fill((*color, 60))
            screen.blit(slot_surf, (sx, sy))
            pygame.draw.rect(screen, color, (sx, sy, size, size), 1)

        # Ghost preview (selected shape at mouse position)
        mouse_pos = pygame.mouse.get_pos()
        grid_pos = self._screen_to_grid(mouse_pos[0], mouse_pos[1])
        if grid_pos and self._selected_shape:
            shape = self._get_transformed_shape()
            mat = self._get_selected_material()
            ghost_color = mat.color_primary if mat else (100, 200, 100)

            # Check if placement is valid
            valid = True
            if mat:
                ok, _ = self.grid_manager.can_place_shape(
                    shape, grid_pos[0], grid_pos[1], mat, self.build.pixels,
                )
                valid = ok

            for row_idx, row in enumerate(shape.pixel_mask):
                for col_idx, filled in enumerate(row):
                    if filled:
                        gx = grid_pos[0] + col_idx
                        gy = grid_pos[1] + row_idx
                        if 0 <= gx < canvas and 0 <= gy < canvas:
                            px = ox + gx * cell
                            py = oy + gy * cell
                            preview_color = ghost_color if valid else (200, 60, 60)
                            ghost_surf = pygame.Surface((cell - 1, cell - 1), pygame.SRCALPHA)
                            ghost_surf.fill((*preview_color, 100))
                            screen.blit(ghost_surf, (px + 1, py + 1))

        # Grid border
        pygame.draw.rect(screen, Colors.UI_BORDER, (ox - 1, oy - 1, grid_w + 2, grid_h + 2), 1)

    def _render_shape_palette(self, screen: pygame.Surface) -> None:
        """Render the shape selection panel on the left."""
        draw_panel(screen, (SHAPE_PANEL_X, SHAPE_PANEL_Y, SHAPE_PANEL_W, SHAPE_PANEL_H), alpha=200)

        # Title
        title = self.small_font.render("SHAPES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (SHAPE_PANEL_X + 8, SHAPE_PANEL_Y + 6))

        # Category tabs
        tab_y = SHAPE_PANEL_Y + 5
        tab_labels = {"all": "All", "basic": "B", "intermediate": "I", "advanced": "A", "exotic": "X", "faction": "F"}
        for i, cat in enumerate(self._shape_categories):
            tx = SHAPE_PANEL_X + 5 + (i % 6) * scale_x(28)
            ty = tab_y + scale_y(18)
            is_active = cat == self._shape_category_filter
            color = Colors.TEXT_HIGHLIGHT if is_active else Colors.TEXT_SECONDARY
            label = self.label_font.render(tab_labels.get(cat, cat[0].upper()), True, color)
            screen.blit(label, (tx, ty))

        # Shape list
        shapes = self._get_filtered_shapes()
        item_h = scale_y(36)
        start_y = SHAPE_PANEL_Y + scale_y(42) - self._shape_scroll_offset
        clip_rect = pygame.Rect(SHAPE_PANEL_X, SHAPE_PANEL_Y + scale_y(38), SHAPE_PANEL_W, SHAPE_PANEL_H - scale_y(42))
        screen.set_clip(clip_rect)

        for i, shape in enumerate(shapes):
            iy = start_y + i * item_h
            if iy + item_h < clip_rect.top or iy > clip_rect.bottom:
                continue

            is_selected = (self._selected_shape and self._selected_shape.id == shape.id)
            bg_color = (40, 50, 80) if is_selected else (20, 25, 40)
            pygame.draw.rect(screen, bg_color,
                             (SHAPE_PANEL_X + 4, iy, SHAPE_PANEL_W - 8, item_h - 2))
            if is_selected:
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT,
                                 (SHAPE_PANEL_X + 4, iy, SHAPE_PANEL_W - 8, item_h - 2), 1)

            # Shape name
            name = self.tiny_font.render(shape.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name, (SHAPE_PANEL_X + 8, iy + 2))

            # Pixel count
            info = self.label_font.render(
                f"{shape.pixel_count}px {shape.width}×{shape.height}",
                True, Colors.TEXT_SECONDARY,
            )
            screen.blit(info, (SHAPE_PANEL_X + 8, iy + 18))

            # Mini preview (tiny grid of the shape)
            preview_x = SHAPE_PANEL_X + SHAPE_PANEL_W - scale_x(40)
            preview_cell = min(3, max(1, scale_x(30) // max(shape.width, shape.height)))
            for ry, row in enumerate(shape.pixel_mask):
                for cx, filled in enumerate(row):
                    if filled:
                        pygame.draw.rect(
                            screen, Colors.TEXT_SECONDARY,
                            (preview_x + cx * preview_cell, iy + 4 + ry * preview_cell,
                             preview_cell, preview_cell),
                        )

        screen.set_clip(None)

    def _render_material_panel(self, screen: pygame.Surface) -> None:
        """Render the material selection panel on the right."""
        draw_panel(screen, (MATERIAL_PANEL_X, MATERIAL_PANEL_Y, MATERIAL_PANEL_W, MATERIAL_PANEL_H), alpha=200)

        title = self.small_font.render("MATERIALS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (MATERIAL_PANEL_X + 8, MATERIAL_PANEL_Y + 6))

        materials = self._get_available_materials()
        item_h = scale_y(30)
        start_y = MATERIAL_PANEL_Y + scale_y(25) - self._material_scroll_offset

        for i, mat in enumerate(materials):
            iy = start_y + i * item_h
            if iy + item_h < MATERIAL_PANEL_Y or iy > MATERIAL_PANEL_Y + MATERIAL_PANEL_H:
                continue

            is_selected = mat.id == self._selected_material_id
            bg_color = (40, 50, 80) if is_selected else (20, 25, 40)
            pygame.draw.rect(screen, bg_color,
                             (MATERIAL_PANEL_X + 4, iy, MATERIAL_PANEL_W - 8, item_h - 2))
            if is_selected:
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT,
                                 (MATERIAL_PANEL_X + 4, iy, MATERIAL_PANEL_W - 8, item_h - 2), 1)

            # Color swatch
            pygame.draw.rect(screen, mat.color_primary,
                             (MATERIAL_PANEL_X + 8, iy + 4, scale_x(14), item_h - 10))

            # Name
            name = self.tiny_font.render(mat.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name, (MATERIAL_PANEL_X + scale_x(26), iy + 2))

            # Cost
            cost = self.label_font.render(f"{mat.cost_per_pixel}/px", True, Colors.TEXT_SECONDARY)
            screen.blit(cost, (MATERIAL_PANEL_X + scale_x(26), iy + 15))

    def _render_stats_panel(self, screen: pygame.Surface) -> None:
        """Render the ship stats and weight/power bars at the bottom."""
        draw_panel(screen, (0, STATS_PANEL_Y, WINDOW_WIDTH, STATS_PANEL_H), alpha=210)

        stats = self._computed_stats
        if stats is None:
            return

        y = STATS_PANEL_Y + 8
        x_start = scale_x(20)
        col_w = scale_x(150)

        # Row 1: Combat stats
        stat_items = [
            ("Hull", str(stats.hull), Colors.GREEN),
            ("Shields", str(stats.shields), (80, 180, 255)),
            ("Armor", str(stats.armor), (200, 150, 50)),
            ("Evasion", str(stats.evasion), (160, 100, 200)),
            ("Speed", str(stats.speed), Colors.TEXT_PRIMARY),
        ]
        for i, (label, value, color) in enumerate(stat_items):
            lx = x_start + i * col_w
            lbl = self.tiny_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            val = self.tiny_font.render(value, True, color)
            screen.blit(lbl, (lx, y))
            screen.blit(val, (lx + lbl.get_width() + 4, y))

        y += scale_y(22)

        # Row 2: Economy stats
        eco_items = [
            ("Cargo", str(stats.cargo_capacity), Colors.TEXT_PRIMARY),
            ("Fuel", str(stats.fuel_capacity), Colors.TEXT_PRIMARY),
            ("Crew", str(stats.crew_slots), Colors.TEXT_PRIMARY),
            ("Cost", f"{stats.total_cost:,} CR", Colors.GOLD if hasattr(Colors, "GOLD") else (200, 180, 80)),
            ("Pixels", str(len(self.build.pixels)), Colors.TEXT_SECONDARY),
        ]
        for i, (label, value, color) in enumerate(eco_items):
            lx = x_start + i * col_w
            lbl = self.tiny_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            val = self.tiny_font.render(value, True, color)
            screen.blit(lbl, (lx, y))
            screen.blit(val, (lx + lbl.get_width() + 4, y))

        y += scale_y(24)

        # Weight bar
        bar_w = scale_x(300)
        weight_color = (80, 200, 80)  # Green
        if stats.weight_ratio > 0.80:
            weight_color = (220, 140, 40)  # Orange
        if stats.weight_ratio > 0.95:
            weight_color = (220, 60, 40)  # Red
        draw_bar(
            screen, x_start, y, bar_w, BAR_H,
            stats.weight_current, stats.weight_max,
            weight_color, label="Weight", font=self.label_font,
        )
        # Weight label
        wt_label = self.label_font.render(
            f"{stats.weight_label} ({stats.weight_ratio:.0%})",
            True, weight_color,
        )
        screen.blit(wt_label, (x_start + bar_w + 10, y))

        y += BAR_H + 8

        # Identity indicator
        if stats.defensive_identity:
            id_colors = {
                "juggernaut": (200, 150, 50),
                "sentinel": (80, 180, 255),
                "ghost": (160, 100, 200),
            }
            id_color = id_colors.get(stats.defensive_identity, Colors.TEXT_SECONDARY)
            id_text = self.tiny_font.render(
                f"Identity: {stats.defensive_identity.upper()}",
                True, id_color,
            )
            screen.blit(id_text, (x_start, y))

        # Rotation/flip indicator (right side)
        if self._selected_shape:
            rot_text = self.label_font.render(
                f"[R] Rotate ({self._shape_rotation * 90}°)  [Q] Flip {'ON' if self._shape_flipped else 'OFF'}",
                True, Colors.TEXT_SECONDARY,
            )
            screen.blit(rot_text, (WINDOW_WIDTH - rot_text.get_width() - scale_x(20), STATS_PANEL_Y + 8))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
