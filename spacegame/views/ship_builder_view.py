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
from spacegame.engine.particles import ParticlePool, FORGE_FLAME, SPARK_BURST
from spacegame.engine.audio_manager import get_audio_manager
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
        self.particles = ParticlePool(100)

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
        self._active_tool: str = "stamp"  # "stamp", "pencil", "brush", "fill", "eraser"

        # Advanced tools (Phase B2)
        self._mirror_mode: bool = False
        self._undo_stack: list[list[dict]] = []  # Pixel snapshots

        # Slot designator (Phase B3)
        self._slot_type_to_place: Optional[str] = None
        self._equipment_modal_open: bool = False
        self._equipment_modal_slot: Optional[DesignatedSlot] = None
        self._equipment_list: list = []
        self._equipment_scroll: int = 0

        # Polish (Phase E)
        self._confirm_anim_timer: float = 0.0  # Confirmation animation
        self._confirm_anim_surface: Optional[pygame.Surface] = None
        self._hovered_shape: Optional[HullShape] = None  # Shape under cursor in palette
        self._particle_timer: float = 0.0  # Ambient sparks
        self._validation_warnings: list[str] = []  # Build issues
        self._redo_stack: list[list[dict]] = []
        self._max_undo: int = 20

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
        # Quick Start / Help buttons (Phase F — always visible)
        self.load_preset_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(160), btn_y, btn_w, btn_h,
            ),
            text="LOAD PRESET",
            manager=self.ui_manager,
        )
        self.help_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(300), btn_y, scale_x(40), btn_h,
            ),
            text="?",
            manager=self.ui_manager,
        )
        self._help_overlay_open = False

    def _destroy_ui(self) -> None:
        for btn in [self.confirm_button, self.clear_button, self.back_button,
                    getattr(self, "load_preset_button", None),
                    getattr(self, "help_button", None)]:
            if btn:
                btn.kill()
        self.confirm_button = None
        self.clear_button = None
        self.back_button = None

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        # Block input during confirmation animation
        if self._confirm_anim_timer > 0:
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.SHIPYARD
                return
            if event.ui_element == self.confirm_button:
                self._confirm_build()
                return
            if event.ui_element == self.clear_button:
                self._push_undo()
                self.build.pixels.clear()
                self.build.slots.clear()
                self._modified = True
                self._recompute_stats()
                return
            if hasattr(self, "load_preset_button") and event.ui_element == self.load_preset_button:
                self._load_preset()
                return
            if hasattr(self, "help_button") and event.ui_element == self.help_button:
                self._help_overlay_open = not self._help_overlay_open
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._shape_rotation = (self._shape_rotation + 1) % 4
            elif event.key == pygame.K_q:
                self._shape_flipped = not self._shape_flipped
            elif event.key == pygame.K_ESCAPE:
                self.next_state = GameState.SHIPYARD
            # Tool switching (Phase B2)
            elif event.key == pygame.K_s:
                self._active_tool = "stamp"
            elif event.key == pygame.K_p:
                self._active_tool = "pencil"
            elif event.key == pygame.K_m:
                self._active_tool = "brush"
            elif event.key == pygame.K_f:
                self._active_tool = "fill"
            elif event.key == pygame.K_e:
                self._active_tool = "eraser"
            elif event.key == pygame.K_x:
                self._mirror_mode = not self._mirror_mode
            elif event.key == pygame.K_d:
                self._active_tool = "slot"
                self._slot_type_to_place = None
            # Undo/Redo (Phase B2)
            elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._undo()
            elif event.key == pygame.K_y and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._redo()

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Close help overlay on any click
            if getattr(self, "_help_overlay_open", False):
                self._help_overlay_open = False
                return
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

        # Equipment modal takes priority if open
        if self._equipment_modal_open:
            self._handle_equipment_modal_click(mx, my)
            return

        # Click on shape palette
        if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W:
            self._handle_shape_palette_click(mx, my)
            return

        # Click on material panel
        if MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W:
            self._handle_material_panel_click(mx, my)
            return

        # Slot type selector (shown when in slot mode, below material panel)
        if self._active_tool == "slot":
            if self._handle_slot_type_click(mx, my):
                return

        # Click on grid — route through active tool
        grid_pos = self._screen_to_grid(mx, my)
        if grid_pos:
            if self._active_tool == "slot":
                if self._slot_type_to_place:
                    self._push_undo()
                    self._place_slot(*grid_pos)
                else:
                    # Click on existing slot to open equipment modal
                    self._try_open_equipment_modal(*grid_pos)
            elif self._active_tool == "stamp" and self._selected_shape:
                self._push_undo()
                self._place_shape_at(*grid_pos)
            elif self._active_tool == "pencil":
                self._push_undo()
                self._place_pencil(*grid_pos)
            elif self._active_tool == "brush":
                self._push_undo()
                self._paint_material(*grid_pos)
            elif self._active_tool == "fill":
                self._push_undo()
                self._flood_fill(*grid_pos)
            elif self._active_tool == "eraser":
                self._push_undo()
                self._erase_pixel(*grid_pos)

    def _handle_right_click(self, pos: tuple[int, int]) -> None:
        """Erase pixel or remove slot at clicked grid position."""
        if self._equipment_modal_open:
            self._equipment_modal_open = False
            return
        grid_pos = self._screen_to_grid(pos[0], pos[1])
        if grid_pos:
            if self._active_tool == "slot":
                self._remove_slot_at(*grid_pos)
            else:
                self._push_undo()
                self._erase_pixel(*grid_pos)

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
            materials_catalog=getattr(self.data_loader, "hull_materials", None),
        )
        if not ok:
            return

        # Stamp pixels (with mirror mode support)
        canvas = self.build.canvas_size
        occupied = {(p.x, p.y) for p in self.build.pixels}
        for row_idx, row in enumerate(shape.pixel_mask):
            for col_idx, filled in enumerate(row):
                if filled:
                    px, py = gx + col_idx, gy + row_idx
                    if (px, py) not in occupied:
                        self.build.pixels.append(
                            PlacedPixel(px, py, self._selected_material_id)
                        )
                        occupied.add((px, py))
                    # Mirror mode: place mirrored pixel
                    if self._mirror_mode:
                        mx = canvas - 1 - px
                        if (mx, py) not in occupied:
                            self.build.pixels.append(
                                PlacedPixel(mx, py, self._selected_material_id)
                            )
                            occupied.add((mx, py))
        self._modified = True
        self._recompute_stats()

    # ------------------------------------------------------------------
    # Advanced Tools (Phase B2)
    # ------------------------------------------------------------------

    def _place_pencil(self, gx: int, gy: int) -> None:
        """Place a single pixel at the grid position."""
        canvas = self.build.canvas_size
        if gx < 0 or gy < 0 or gx >= canvas or gy >= canvas:
            return
        occupied = {(p.x, p.y) for p in self.build.pixels}
        if (gx, gy) in occupied:
            return
        self.build.pixels.append(PlacedPixel(gx, gy, self._selected_material_id))
        if self._mirror_mode:
            mx = canvas - 1 - gx
            if (mx, gy) not in occupied:
                self.build.pixels.append(PlacedPixel(mx, gy, self._selected_material_id))
        self._modified = True
        self._recompute_stats()

    def _paint_material(self, gx: int, gy: int) -> None:
        """Change the material of an existing pixel (Material Brush)."""
        for pixel in self.build.pixels:
            if pixel.x == gx and pixel.y == gy:
                pixel.material_id = self._selected_material_id
                if self._mirror_mode:
                    mx = self.build.canvas_size - 1 - gx
                    for mp in self.build.pixels:
                        if mp.x == mx and mp.y == gy:
                            mp.material_id = self._selected_material_id
                            break
                self._modified = True
                self._recompute_stats()
                return

    def _flood_fill(self, gx: int, gy: int) -> None:
        """Flood-fill empty cells from the clicked position.

        Uses 4-connected fill bounded by canvas edges and existing
        pixels. Fills with the currently selected material.
        """
        canvas = self.build.canvas_size
        if gx < 0 or gy < 0 or gx >= canvas or gy >= canvas:
            return
        occupied = {(p.x, p.y) for p in self.build.pixels}
        if (gx, gy) in occupied:
            return  # Can't fill a filled cell

        # BFS flood fill
        to_fill: list[tuple[int, int]] = []
        visited: set[tuple[int, int]] = set()
        queue = [(gx, gy)]
        max_fill = 500  # Safety limit

        while queue and len(to_fill) < max_fill:
            x, y = queue.pop(0)
            if (x, y) in visited or (x, y) in occupied:
                continue
            if x < 0 or y < 0 or x >= canvas or y >= canvas:
                continue
            visited.add((x, y))
            to_fill.append((x, y))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                queue.append((x + dx, y + dy))

        for x, y in to_fill:
            self.build.pixels.append(PlacedPixel(x, y, self._selected_material_id))
            if self._mirror_mode:
                mx = canvas - 1 - x
                if (mx, y) not in occupied and (mx, y) not in {(fx, fy) for fx, fy in to_fill}:
                    self.build.pixels.append(PlacedPixel(mx, y, self._selected_material_id))

        if to_fill:
            self._modified = True
            self._recompute_stats()
            if len(to_fill) >= max_fill:
                self._validation_warnings.append("Fill capped at 500 pixels (safety limit).")

    def _erase_pixel(self, gx: int, gy: int) -> None:
        """Remove the pixel at the given grid position."""
        canvas = self.build.canvas_size
        before = len(self.build.pixels)
        self.build.pixels = [
            p for p in self.build.pixels
            if not (p.x == gx and p.y == gy)
        ]
        if self._mirror_mode:
            mx = canvas - 1 - gx
            self.build.pixels = [
                p for p in self.build.pixels
                if not (p.x == mx and p.y == gy)
            ]
        if len(self.build.pixels) < before:
            self._modified = True
            self._recompute_stats()

    # ------------------------------------------------------------------
    # Undo/Redo (Phase B2)
    # ------------------------------------------------------------------

    def _push_undo(self) -> None:
        """Save current pixel state to undo stack."""
        snapshot = [p.to_dict() for p in self.build.pixels]
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self) -> None:
        """Restore previous pixel state."""
        if not self._undo_stack:
            return
        # Save current state to redo
        self._redo_stack.append([p.to_dict() for p in self.build.pixels])
        # Restore previous state
        snapshot = self._undo_stack.pop()
        self.build.pixels = [PlacedPixel.from_dict(d) for d in snapshot]
        self._modified = True
        self._recompute_stats()

    def _redo(self) -> None:
        """Restore next pixel state (after undo)."""
        if not self._redo_stack:
            return
        # Save current to undo
        self._undo_stack.append([p.to_dict() for p in self.build.pixels])
        # Restore redo state
        snapshot = self._redo_stack.pop()
        self.build.pixels = [PlacedPixel.from_dict(d) for d in snapshot]
        self._modified = True
        self._recompute_stats()

    # ------------------------------------------------------------------
    # Slot Designator & Equipment (Phase B3)
    # ------------------------------------------------------------------

    SLOT_COSTS: dict[str, int] = {
        "weapon": 3000, "defense": 2500, "engine": 2000,
        "utility": 1500, "core": 0,
    }
    SLOT_TYPES_ORDER: list[str] = ["weapon", "defense", "engine", "utility", "core"]

    def _handle_slot_type_click(self, mx: int, my: int) -> bool:
        """Handle clicks on the slot type selector panel."""
        panel_x = MATERIAL_PANEL_X
        panel_y = MATERIAL_PANEL_Y + MATERIAL_PANEL_H + scale_y(10)
        item_h = scale_y(24)

        for i, slot_type in enumerate(self.SLOT_TYPES_ORDER):
            iy = panel_y + scale_y(20) + i * item_h
            if panel_x <= mx < panel_x + MATERIAL_PANEL_W and iy <= my < iy + item_h:
                self._slot_type_to_place = slot_type
                return True
        return False

    def _place_slot(self, gx: int, gy: int) -> None:
        """Place a slot at the given grid position."""
        if not self._slot_type_to_place:
            return
        ok, msg = self.grid_manager.can_place_slot(
            self._slot_type_to_place, gx, gy,
            self.build.pixels, self.build.slots,
        )
        if not ok:
            return

        slot = DesignatedSlot(slot_type=self._slot_type_to_place, x=gx, y=gy)
        self.build.slots.append(slot)
        self._modified = True
        self._recompute_stats()

    def _remove_slot_at(self, gx: int, gy: int) -> None:
        """Remove a slot that contains the given grid position."""
        for slot in self.build.slots:
            if (slot.x <= gx < slot.x + slot.size
                    and slot.y <= gy < slot.y + slot.size):
                self.build.slots.remove(slot)
                self._modified = True
                self._recompute_stats()
                return

    def _try_open_equipment_modal(self, gx: int, gy: int) -> None:
        """Open equipment browser if clicking on an existing slot."""
        for slot in self.build.slots:
            if (slot.x <= gx < slot.x + slot.size
                    and slot.y <= gy < slot.y + slot.size):
                self._open_equipment_modal(slot)
                return

    def _open_equipment_modal(self, slot: DesignatedSlot) -> None:
        """Open the equipment browser for the given slot."""
        self._equipment_modal_open = True
        self._equipment_modal_slot = slot
        self._equipment_scroll = 0

        # Build available equipment list for this slot type
        all_upgrades = getattr(self.data_loader, "upgrades", {})
        slot_type = slot.slot_type

        # Map builder slot types to upgrade slot_types
        type_map = {
            "weapon": ["weapon"],
            "defense": ["defense"],
            "engine": ["engine"],
            "utility": ["cargo", "fuel", "mining", "scanner", "smuggling", "utility"],
            "core": [],  # Core provides energy, no equipment
        }
        valid_types = type_map.get(slot_type, [])
        self._equipment_list = [
            u for u in all_upgrades.values()
            if u.slot_type in valid_types
        ]
        # Sort by tier then price
        self._equipment_list.sort(key=lambda u: (u.tier, u.price))

    def _handle_equipment_modal_click(self, mx: int, my: int) -> None:
        """Handle clicks within the equipment modal."""
        modal_x = GRID_AREA_X + scale_x(50)
        modal_y = GRID_AREA_Y + scale_y(30)
        modal_w = GRID_AREA_W - scale_x(100)
        modal_h = GRID_AREA_H - scale_y(60)

        # Close button (top right of modal)
        close_x = modal_x + modal_w - scale_x(30)
        close_y = modal_y + 5
        if close_x <= mx < close_x + scale_x(25) and close_y <= my < close_y + scale_y(20):
            self._equipment_modal_open = False
            return

        # Equipment items
        item_h = scale_y(40)
        start_y = modal_y + scale_y(35) - self._equipment_scroll
        for i, upgrade in enumerate(self._equipment_list):
            iy = start_y + i * item_h
            if modal_x <= mx < modal_x + modal_w and iy <= my < iy + item_h:
                # Install this equipment (check credits)
                if self._equipment_modal_slot:
                    if self.player.credits >= upgrade.price:
                        self.player.credits -= upgrade.price
                        self._equipment_modal_slot.equipment_id = upgrade.id
                        self._modified = True
                        self._recompute_stats()
                        get_audio_manager().play_sfx("trade_buy")
                self._equipment_modal_open = False
                return

    def _get_slot_pool_remaining(self) -> dict[str, tuple[int, int]]:
        """Get remaining slot counts by type (used, max)."""
        pool = SLOT_POOLS.get(self.build.weight_class, {})
        result: dict[str, tuple[int, int]] = {}
        for slot_type in self.SLOT_TYPES_ORDER:
            if slot_type == "core":
                # Core: max 1
                used = sum(1 for s in self.build.slots if s.slot_type == "core")
                result["core"] = (used, 1)
            else:
                max_count = pool.get(slot_type, 0)
                used = sum(1 for s in self.build.slots if s.slot_type == slot_type)
                result[slot_type] = (used, max_count)
        return result

    def _confirm_build(self) -> None:
        """Apply the current build to the player's ship."""
        self.player.ship.set_build(self.build)
        # Update hull/shields to match new build stats
        if self._computed_stats:
            self.player.ship.current_hull = self._computed_stats.hull
            self.player.ship.current_shields = self._computed_stats.shields
        self._modified = False
        logger.info("Ship build confirmed")

        # Confirmation animation (Phase E)
        self._confirm_anim_timer = 1.2
        # Cache the composite sprite for the animation
        composite = self.player.ship.composite
        if composite and hasattr(composite, "get_surface"):
            from spacegame.engine.sprites import res_scale
            self._confirm_anim_surface = composite.get_surface(scale=res_scale(3))
        # Spark burst at grid center
        cx = GRID_AREA_X + GRID_AREA_W // 2
        cy = GRID_AREA_Y + GRID_AREA_H // 2
        for _ in range(3):
            self.particles.emit(cx, cy, SPARK_BURST)
        get_audio_manager().play_sfx("ui_confirm")

        # Delay transition until animation completes (handled in update)

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def _update_validation_warnings(self) -> None:
        """Check build for issues and update warning list."""
        warnings: list[str] = []
        stats = self._computed_stats
        if stats:
            if stats.weight_ratio > 1.0:
                warnings.append("OVERWEIGHT! Remove pixels or use lighter materials.")
            elif stats.weight_ratio > 0.95:
                warnings.append("Near weight limit.")

        has_core = any(s.slot_type == "core" for s in self.build.slots)
        if not has_core and len(self.build.pixels) > 0:
            warnings.append("No Core slot — ship has no energy system.")

        has_weapon_or_engine = any(
            s.slot_type in ("weapon", "engine") for s in self.build.slots
        )
        if not has_weapon_or_engine and len(self.build.pixels) > 0:
            warnings.append("No weapons or engines — ship can't fight or flee.")

        if len(self.build.pixels) == 0:
            warnings.append("Empty build. Place shapes to design your ship.")

        self._validation_warnings = warnings

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
        self.particles.update(dt)

        # Ambient welding sparks (Phase E)
        self._particle_timer += dt
        if self._particle_timer > 0.3:
            self._particle_timer = 0.0
            import random
            spark_x = GRID_AREA_X + random.randint(0, GRID_AREA_W)
            spark_y = GRID_AREA_Y + random.randint(0, GRID_AREA_H)
            self.particles.emit(spark_x, spark_y, FORGE_FLAME)

        # Confirmation animation countdown → transition when done
        if self._confirm_anim_timer > 0:
            self._confirm_anim_timer = max(0, self._confirm_anim_timer - dt)
            if self._confirm_anim_timer <= 0 and not self._modified:
                self.next_state = GameState.SHIPYARD

        # Update validation warnings
        self._update_validation_warnings()

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

        # Credits display (top right)
        credits_text = self.small_font.render(
            f"Credits: {self.player.credits:,} CR", True, Colors.TEXT_PRIMARY,
        )
        screen.blit(credits_text, (WINDOW_WIDTH - credits_text.get_width() - scale_x(20), 14))

        # Main panels
        self._render_grid(screen)
        self._render_shape_palette(screen)
        self._render_material_panel(screen)
        if self._active_tool == "slot":
            self._render_slot_type_panel(screen)
        self._render_stats_panel(screen)

        # Ambient particles
        self.particles.render(screen)

        # Validation warnings (above stats panel)
        if self._validation_warnings:
            warn_y = STATS_PANEL_Y - scale_y(20) * len(self._validation_warnings)
            for warning in self._validation_warnings:
                warn_surf = self.label_font.render(warning, True, Colors.YELLOW)
                screen.blit(warn_surf, (scale_x(20), warn_y))
                warn_y += scale_y(18)

        # Stat comparison preview (when hovering shape in palette)
        self._render_stat_preview(screen)

        # Equipment modal (overlay)
        if self._equipment_modal_open:
            self._render_equipment_modal(screen)

        # Confirmation animation (overlay)
        if self._confirm_anim_timer > 0:
            self._render_confirm_animation(screen)

        # Help overlay (on top of everything)
        if getattr(self, "_help_overlay_open", False):
            self._render_help_overlay(screen)

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

        # Engine rear zone highlight (Phase B3 — when placing engine slots)
        if self._active_tool == "slot" and self._slot_type_to_place == "engine":
            rear_y = int(canvas * 0.75)
            zone_h = (canvas - rear_y) * cell
            zone_surf = pygame.Surface((grid_w, zone_h), pygame.SRCALPHA)
            zone_surf.fill((200, 140, 40, 25))
            screen.blit(zone_surf, (ox, oy + rear_y * cell))

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

        # Tool bar (right side of stats panel)
        tool_x = WINDOW_WIDTH - scale_x(280)
        tool_y = STATS_PANEL_Y + 8

        # Active tool indicator
        tool_labels = {
            "stamp": "[S] Stamp", "pencil": "[P] Pencil", "brush": "[M] Brush",
            "fill": "[F] Fill", "eraser": "[E] Eraser", "slot": "[D] Slot",
        }
        for i, (tool_id, label) in enumerate(tool_labels.items()):
            is_active = self._active_tool == tool_id
            color = Colors.TEXT_HIGHLIGHT if is_active else Colors.TEXT_SECONDARY
            t = self.label_font.render(label, True, color)
            screen.blit(t, (tool_x + i * scale_x(55), tool_y))

        tool_y += scale_y(16)

        # Mirror mode and rotation
        mirror_text = f"[X] Mirror {'ON' if self._mirror_mode else 'OFF'}"
        mirror_color = Colors.TEXT_HIGHLIGHT if self._mirror_mode else Colors.TEXT_SECONDARY
        mt = self.label_font.render(mirror_text, True, mirror_color)
        screen.blit(mt, (tool_x, tool_y))

        if self._selected_shape:
            rot_text = self.label_font.render(
                f"  [R] {self._shape_rotation * 90}°  [Q] Flip {'Y' if self._shape_flipped else 'N'}",
                True, Colors.TEXT_SECONDARY,
            )
            screen.blit(rot_text, (tool_x + mt.get_width(), tool_y))

        tool_y += scale_y(16)

        # Undo/redo indicator
        undo_text = self.label_font.render(
            f"Undo: {len(self._undo_stack)}  Redo: {len(self._redo_stack)}  [Ctrl+Z/Y]",
            True, Colors.TEXT_SECONDARY,
        )
        screen.blit(undo_text, (tool_x, tool_y))

    def _render_slot_type_panel(self, screen: pygame.Surface) -> None:
        """Render the slot type selector panel (shown in slot mode)."""
        panel_x = MATERIAL_PANEL_X
        panel_y = MATERIAL_PANEL_Y + MATERIAL_PANEL_H + scale_y(10)
        panel_w = MATERIAL_PANEL_W
        panel_h = scale_y(170)

        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=210)

        title = self.small_font.render("SLOT TYPE", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + 8, panel_y + 5))

        slot_colors = {
            "weapon": (200, 60, 60), "defense": (60, 120, 200),
            "engine": (200, 140, 40), "utility": (60, 180, 80),
            "core": (200, 180, 60),
        }
        pool = self._get_slot_pool_remaining()
        item_h = scale_y(24)

        for i, slot_type in enumerate(self.SLOT_TYPES_ORDER):
            iy = panel_y + scale_y(24) + i * item_h
            used, max_count = pool.get(slot_type, (0, 0))
            is_selected = self._slot_type_to_place == slot_type
            is_full = used >= max_count

            # Background
            if is_selected:
                bg = (*slot_colors.get(slot_type, (100, 100, 100)), 80)
                bg_surf = pygame.Surface((panel_w - 8, item_h - 2), pygame.SRCALPHA)
                bg_surf.fill(bg)
                screen.blit(bg_surf, (panel_x + 4, iy))

            # Label
            color = slot_colors.get(slot_type, (150, 150, 150))
            if is_full:
                color = Colors.TEXT_SECONDARY
            label = self.tiny_font.render(
                f"{slot_type.title()}: {used}/{max_count}",
                True, color,
            )
            screen.blit(label, (panel_x + 10, iy + 2))

            # Cost
            cost = self.SLOT_COSTS.get(slot_type, 0)
            if cost > 0:
                cost_text = self.label_font.render(f"{cost:,} CR", True, Colors.TEXT_SECONDARY)
                screen.blit(cost_text, (panel_x + panel_w - cost_text.get_width() - 10, iy + 4))

        # Engine zone hint
        if self._slot_type_to_place == "engine":
            hint = self.label_font.render("Engine: rear 25% only", True, (200, 140, 40))
            screen.blit(hint, (panel_x + 8, panel_y + panel_h - scale_y(18)))

    def _render_equipment_modal(self, screen: pygame.Surface) -> None:
        """Render the equipment browser overlay."""
        # Darken background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        modal_x = GRID_AREA_X + scale_x(30)
        modal_y = GRID_AREA_Y + scale_y(20)
        modal_w = GRID_AREA_W - scale_x(60)
        modal_h = GRID_AREA_H - scale_y(40)

        draw_panel(screen, (modal_x, modal_y, modal_w, modal_h), alpha=240)

        # Title
        slot = self._equipment_modal_slot
        slot_name = slot.slot_type.title() if slot else "Unknown"
        title = self.header_font.render(f"Install: {slot_name}", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (modal_x + 10, modal_y + 8))

        # Close button
        close_text = self.small_font.render("[X] Close", True, Colors.RED)
        screen.blit(close_text, (modal_x + modal_w - close_text.get_width() - 10, modal_y + 10))

        # Equipment list
        item_h = scale_y(40)
        start_y = modal_y + scale_y(40) - self._equipment_scroll
        clip = pygame.Rect(modal_x, modal_y + scale_y(36), modal_w, modal_h - scale_y(40))
        screen.set_clip(clip)

        for i, upgrade in enumerate(self._equipment_list):
            iy = start_y + i * item_h
            if iy + item_h < clip.top or iy > clip.bottom:
                continue

            # Card background
            is_installed = (slot and slot.equipment_id == upgrade.id)
            bg_color = (40, 60, 50) if is_installed else (22, 28, 40)
            pygame.draw.rect(screen, bg_color,
                             (modal_x + 8, iy, modal_w - 16, item_h - 2))
            if is_installed:
                pygame.draw.rect(screen, Colors.GREEN,
                                 (modal_x + 8, iy, modal_w - 16, item_h - 2), 1)

            # Name and tier
            tier_colors = {1: Colors.TEXT_SECONDARY, 2: (100, 180, 255), 3: (255, 200, 80)}
            name_surf = self.tiny_font.render(
                f"T{upgrade.tier} {upgrade.name}",
                True, tier_colors.get(upgrade.tier, Colors.TEXT_PRIMARY),
            )
            screen.blit(name_surf, (modal_x + 14, iy + 2))

            # Price and description
            desc_text = upgrade.description[:50] + ("..." if len(upgrade.description) > 50 else "")
            desc_surf = self.label_font.render(desc_text, True, Colors.TEXT_SECONDARY)
            screen.blit(desc_surf, (modal_x + 14, iy + 18))

            price_surf = self.tiny_font.render(f"{upgrade.price:,} CR", True, Colors.TEXT_PRIMARY)
            screen.blit(price_surf, (modal_x + modal_w - price_surf.get_width() - 14, iy + 8))

        screen.set_clip(None)

        # Hint
        hint = self.label_font.render("Click to install. Right-click to close.", True, Colors.TEXT_SECONDARY)
        screen.blit(hint, (modal_x + 10, modal_y + modal_h - scale_y(16)))

    def _load_preset(self) -> None:
        """Load the current ship type's preset into the builder."""
        from spacegame.models.ship_presets import generate_preset_from_ship_type
        self._push_undo()
        self.build = generate_preset_from_ship_type(self.player.ship.ship_type)
        self.grid_manager = ShipGridManager(self.build.weight_class)
        self._modified = True
        self._recompute_stats()
        logger.info(f"Loaded preset for {self.player.ship.ship_type.name}")

    def _render_help_overlay(self, screen: pygame.Surface) -> None:
        """Render the in-builder help panel (Phase F)."""
        # Darken background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        screen.blit(dim, (0, 0))

        pw = scale_x(600)
        ph = scale_y(450)
        px = (WINDOW_WIDTH - pw) // 2
        py = (WINDOW_HEIGHT - ph) // 2

        draw_panel(screen, (px, py, pw, ph), alpha=240)

        # Title
        title = self.header_font.render("Ship Builder — Controls", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (px + scale_x(20), py + scale_y(10)))

        y = py + scale_y(45)
        line_h = scale_y(20)

        help_lines = [
            ("BUILDING", Colors.TEXT_HIGHLIGHT),
            ("  Left-click: Place shape / Use tool", Colors.TEXT_PRIMARY),
            ("  Right-click: Erase pixel / Remove slot", Colors.TEXT_PRIMARY),
            ("  [R] Rotate shape 90°    [Q] Flip horizontally", Colors.TEXT_PRIMARY),
            ("  [X] Toggle Mirror Mode (symmetrical building)", Colors.TEXT_PRIMARY),
            ("  Ctrl+Z: Undo    Ctrl+Y: Redo", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("TOOLS", Colors.TEXT_HIGHLIGHT),
            ("  [S] Stamp    [P] Pencil    [M] Material Brush", Colors.TEXT_PRIMARY),
            ("  [F] Flood Fill    [E] Eraser    [D] Slot Designator", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("SLOTS & EQUIPMENT", Colors.TEXT_HIGHLIGHT),
            ("  Press [D], select a slot type, click grid to place", Colors.TEXT_PRIMARY),
            ("  Click an existing slot to install equipment", Colors.TEXT_PRIMARY),
            ("  Weapons (red), Defense (blue), Engine (orange), Utility (green)", Colors.TEXT_PRIMARY),
            ("  Core (gold) — required for energy. 1 per ship.", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("WEIGHT & IDENTITY", Colors.TEXT_HIGHLIGHT),
            ("  Hull materials are heavy → Juggernaut (armor, durability)", Colors.TEXT_PRIMARY),
            ("  Shield materials are medium → Sentinel (regen, sustain)", Colors.TEXT_PRIMARY),
            ("  Light materials are fast → Ghost (evasion, speed)", Colors.TEXT_PRIMARY),
            ("  Your ship's identity activates when 35%+ of pixels are one type", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("Press [?] or click anywhere to close", Colors.TEXT_SECONDARY),
        ]

        for text, color in help_lines:
            if text:
                surf = self.label_font.render(text, True, color)
                screen.blit(surf, (px + scale_x(20), y))
            y += line_h

    def _render_stat_preview(self, screen: pygame.Surface) -> None:
        """Show stat delta when hovering a shape in the palette (Phase E)."""
        # Detect hovered shape from mouse position
        mx, my = pygame.mouse.get_pos()
        hovered_shape = None
        if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W:
            shapes = self._get_filtered_shapes()
            item_h = scale_y(36)
            start_y = SHAPE_PANEL_Y + scale_y(42) - self._shape_scroll_offset
            for i, shape in enumerate(shapes):
                iy = start_y + i * item_h
                if iy <= my < iy + item_h:
                    hovered_shape = shape
                    break

        if not hovered_shape:
            return

        mat = self._get_selected_material()
        if not mat:
            return

        # Calculate what placing this shape would add
        pixel_count = hovered_shape.pixel_count
        hull_delta = int(pixel_count * mat.hull_per_pixel)
        shield_delta = int(pixel_count * mat.shield_per_pixel)
        weight_delta = pixel_count * mat.weight_per_pixel
        cost_delta = pixel_count * mat.cost_per_pixel
        armor_delta = pixel_count * mat.armor_per_pixel
        evasion_delta = pixel_count * mat.evasion_per_pixel

        # Render preview box near the shape palette
        preview_x = SHAPE_PANEL_X + SHAPE_PANEL_W + scale_x(5)
        preview_y = my - scale_y(20)
        pw = scale_x(140)
        ph = scale_y(80)

        draw_panel(screen, (preview_x, preview_y, pw, ph), alpha=230)

        y = preview_y + 4
        deltas = [
            (f"+{hull_delta} Hull", Colors.GREEN if hull_delta > 0 else Colors.TEXT_SECONDARY),
            (f"+{shield_delta} Shield", (80, 180, 255) if shield_delta > 0 else Colors.TEXT_SECONDARY),
            (f"+{weight_delta:.1f} Weight", Colors.YELLOW),
            (f"+{cost_delta} CR", Colors.TEXT_SECONDARY),
        ]
        if armor_delta > 0:
            deltas.insert(1, (f"+{armor_delta:.2f} Armor", (200, 150, 50)))
        if evasion_delta > 0:
            deltas.insert(2, (f"+{evasion_delta:.2f} Evasion", (160, 100, 200)))

        for text, color in deltas:
            surf = self.label_font.render(text, True, color)
            screen.blit(surf, (preview_x + 6, y))
            y += scale_y(12)

    def _render_confirm_animation(self, screen: pygame.Surface) -> None:
        """Render the build confirmation celebration (Phase E)."""
        t = self._confirm_anim_timer / 1.2  # 0→1 as animation plays
        alpha = int(255 * min(1.0, t * 3))  # Fade in fast, hold, then we transition

        # Flash overlay
        if t > 0.8:
            flash_alpha = int(200 * ((t - 0.8) / 0.2))
            flash = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            screen.blit(flash, (0, 0))

        # Ship sprite centered large
        if self._confirm_anim_surface:
            sprite = self._confirm_anim_surface
            sprite_alpha = min(255, alpha)
            sprite.set_alpha(sprite_alpha)
            rect = sprite.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            screen.blit(sprite, rect)

            # "BUILD CONFIRMED" text
            text = self.header_font.render("BUILD CONFIRMED", True, (255, 220, 100))
            text.set_alpha(sprite_alpha)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + sprite.get_height() // 2 + scale_y(30)))
            screen.blit(text, text_rect)

        # Darken edges
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(120 * (1.0 - t))))
        screen.blit(dim, (0, 0))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
