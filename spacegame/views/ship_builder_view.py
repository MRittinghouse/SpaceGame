"""Ship builder view — the unified ship designer.

Three-mode builder: MODULES (place ship parts), HULL (paint structural
pixels), and EQUIP (install weapons/shields into module slots). The grid
IS the ship sprite. Real-time stat updates show the effect of every
placement.

File structure (3300+ lines):
  - Lines ~1-200: Imports, layout constants, __init__, lifecycle
  - Lines ~200-600: Event handling (clicks, keys, mode routing)
  - Lines ~600-850: Module interaction methods (catalog, place, remove, recolor)
  - Lines ~850-1050: Equip mode interaction (slot selection, install, uninstall)
  - Lines ~1050-1350: Build actions (save draft, share, import, confirm with delta cost)
  - Lines ~1350-1650: Update loop, render dispatch, grid rendering
  - Lines ~1650-2050: Module catalog rendering, requirements checklist, mode toggle
  - Lines ~2050-2350: Physics overlays, module tooltip, stats panel
  - Lines ~2350-2650: Equip mode rendering (slot list, equipment panel)
  - Lines ~2650-2800: Recolor panel, help overlay, confirmation animation
  - Lines ~2800+: Equipment modal, stat preview, preset loading

Candidate for extraction: EQUIP mode (~300 lines) and RECOLOR mode (~150 lines)
could be extracted into helper modules when file grows further.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar, draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_MD,
    FONT_SM,
    FONT_TITLE,
    FONT_XL,
    FONT_XS,
    get_font,
)
from spacegame.engine.particles import FORGE_FLAME, SPARK_BURST, ParticlePool
from spacegame.models.player import Player
from spacegame.models.ship_build import (
    FRAME_SLOT_LIMITS,
    ComputedShipStats,
    DesignatedSlot,
    HullMaterial,
    HullShape,
    PlacedPixel,
    PlacedSlot,
    ShipBuild,
    ShipGridManager,
    ShipStatsComputer,
)
from spacegame.models.ship_module import (
    PlacedModule,
    ShipModule,
    can_place_module,
    is_pixel_recolorable,
    resolve_all_pixels,
    resolve_placed_module,
    validate_connectivity,
    validate_requirements,
)
from spacegame.models.slot_definition import _SIZE_DISPLAY, _TYPE_DISPLAY, SlotDefinition
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# Hull-only materials for the simplified hull pixel palette
HULL_PIXEL_MATERIALS = ("light_alloy", "standard_plate", "heavy_armor", "stealth_composite")

# Single-letter labels for slot types rendered on grid cells
_SLOT_TYPE_SHORT: dict[str, str] = {
    "weapon": "W",
    "defense": "D",
    "engine": "E",
    "utility": "U",
    "cargo": "C",
    "crew_quarters": "Q",
    "reactor": "R",
}

# Ordered slot types for palette grouping
_SLOT_TYPE_ORDER: list[str] = [
    "weapon",
    "defense",
    "engine",
    "utility",
    "cargo",
    "crew_quarters",
    "reactor",
]

# Layout constants — widened panels, centered grid
SHAPE_PANEL_X = scale_x(8)
SHAPE_PANEL_Y = scale_y(58)
SHAPE_PANEL_W = scale_x(240)
SHAPE_PANEL_H = scale_y(490)

MATERIAL_PANEL_X = WINDOW_WIDTH - scale_x(220)
MATERIAL_PANEL_Y = scale_y(58)
MATERIAL_PANEL_W = scale_x(210)
MATERIAL_PANEL_H = scale_y(280)

GRID_AREA_X = SHAPE_PANEL_X + SHAPE_PANEL_W + scale_x(8)
GRID_AREA_Y = scale_y(58)
GRID_AREA_W = MATERIAL_PANEL_X - GRID_AREA_X - scale_x(8)
GRID_AREA_H = scale_y(490)

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

        # Fonts — role-based
        self.title_font = get_font("header", FONT_TITLE)  # "DRYDOCK — LARGE"
        self.header_font = get_font("header", FONT_XL)  # Section headers
        self.body_font = get_font("dialogue", FONT_BODY)  # Module names
        self.small_font = get_font("stats", FONT_MD)  # Stats, costs
        self.tiny_font = get_font("dialogue", FONT_SM)  # Detail text
        self.label_font = get_font("label", FONT_XS)  # Category tabs, badges

        # Background
        self.background = AnimatedBackground(
            "industrial",
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            seed=90,
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

        # Zoom/Pan for Large/XL canvases (QA Fix #6)
        self._zoom_level: float = 1.0
        self._pan_offset_x: float = 0.0
        self._pan_offset_y: float = 0.0
        self._panning: bool = False
        self._pan_start: tuple[int, int] = (0, 0)

        # (Legacy slot designator removed — equipment via EQUIP mode)

        # Polish (Phase E)
        self._confirm_anim_timer: float = 0.0  # Confirmation animation
        self._confirm_anim_surface: Optional[pygame.Surface] = None
        self._hovered_shape: Optional[HullShape] = None  # Shape under cursor in palette
        self._particle_timer: float = 0.0  # Ambient sparks
        self._validation_warnings: list[str] = []  # Build issues (blocking)
        self._advisory_warnings: list[str] = []  # Build advisories (non-blocking)
        self._can_confirm: bool = False
        self._pending_hint: Optional[str] = None  # Hint ID for game.py to show
        self._redo_stack: list[list[dict]] = []
        self._max_undo: int = 30

        # Shape palette scroll
        self._shape_scroll_offset: int = 0
        self._shape_category_filter: str = "all"
        self._shape_categories = ["all", "basic", "intermediate", "advanced", "exotic", "faction"]

        # Material list scroll
        self._material_scroll_offset: int = 0

        # Module mode (Phase 4 — Shipbuilder Upgrade)
        self._builder_mode: str = "slot"  # "slot" or "hull"
        self._selected_module_id: Optional[str] = None
        self._module_rotation: int = 0  # 0-3 (90° increments)
        self._module_flipped: bool = False
        self._module_catalog_scroll: int = 0
        self._module_category_filter: str = "all"
        self._module_categories = [
            "all",
            "cockpit",
            "engine",
            "weapon",
            "shield",
            "cargo",
            "utility",
            "structural",
        ]
        self._selected_placed_module_idx: Optional[int] = None  # For removal
        self._recolor_mode: bool = False
        self._recolor_material_id: str = "standard_plate"
        # Slot palette (S2.2 — new slot-based builder)
        self._selected_slot_def_id: Optional[str] = None
        self._slot_palette_scroll: int = 0

        # EQUIP mode moved to Loadout tab (Phase S4)
        self._equip_selected_module_idx: Optional[int] = None  # Legacy, kept for compat

        # Visual feedback (Phase 10)
        self._placement_flash_timer: float = 0.0
        self._placement_flash_pos: tuple[int, int] = (0, 0)
        self._feedback_messages: list[dict] = []

        # Physics overlay toggles (Phase 6)
        self._show_integrity_overlay: bool = False
        self._show_com_overlay: bool = False
        self._cached_integrity: Optional[dict] = None

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
        # Track the build cost at entry to charge only the delta on confirm
        self._entry_cost = self._computed_stats.total_cost if self._computed_stats else 0
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
                WINDOW_WIDTH - btn_w - scale_x(20),
                btn_y,
                btn_w,
                btn_h,
            ),
            text="CONFIRM BUILD",
            manager=self.ui_manager,
        )
        self.clear_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH - btn_w * 2 - scale_x(30),
                btn_y,
                btn_w,
                btn_h,
            ),
            text="CLEAR ALL",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(20),
                btn_y,
                btn_w,
                btn_h,
            ),
            text="BACK",
            manager=self.ui_manager,
        )
        # Quick Start / Help buttons (Phase F — always visible)
        self.load_preset_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(160),
                btn_y,
                btn_w,
                btn_h,
            ),
            text="LOAD PRESET",
            manager=self.ui_manager,
        )
        self.help_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(300),
                btn_y,
                scale_x(40),
                btn_h,
            ),
            text="?",
            manager=self.ui_manager,
        )
        self.save_draft_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(350),
                btn_y,
                btn_w,
                btn_h,
            ),
            text="SAVE DRAFT",
            manager=self.ui_manager,
        )
        self.share_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(490),
                btn_y,
                scale_x(110),
                btn_h,
            ),
            text="SHARE BUILD",
            manager=self.ui_manager,
        )
        self.import_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(610),
                btn_y,
                scale_x(90),
                btn_h,
            ),
            text="IMPORT",
            manager=self.ui_manager,
        )
        self._help_overlay_open = False
        self._import_modal_open = False
        self._import_text = ""
        self._import_error = ""
        self._import_missing_blueprints: list[dict] = []

    def _destroy_ui(self) -> None:
        for btn in [
            self.confirm_button,
            self.clear_button,
            self.back_button,
            getattr(self, "load_preset_button", None),
            getattr(self, "help_button", None),
            getattr(self, "save_draft_button", None),
            getattr(self, "share_button", None),
            getattr(self, "import_button", None),
        ]:
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
                self.build.modules.clear()
                self.build.placed_slots.clear()
                self._selected_placed_module_idx = None
                self._selected_slot_def_id = None
                self._modified = True
                self._recompute_stats()
                return
            if hasattr(self, "load_preset_button") and event.ui_element == self.load_preset_button:
                logger.info("Load Preset button clicked")
                self._load_preset()
                return
            if hasattr(self, "help_button") and event.ui_element == self.help_button:
                self._help_overlay_open = not self._help_overlay_open
                return
            if hasattr(self, "save_draft_button") and event.ui_element == self.save_draft_button:
                self._save_draft()
                return
            if hasattr(self, "share_button") and event.ui_element == self.share_button:
                self._share_build()
                return
            if hasattr(self, "import_button") and event.ui_element == self.import_button:
                self._import_modal_open = not self._import_modal_open
                self._import_text = ""
                self._import_error = ""
                self._import_missing_blueprints = []
                return

        if event.type == pygame.KEYDOWN:
            # Import modal text input
            if getattr(self, "_import_modal_open", False):
                if event.key == pygame.K_ESCAPE:
                    self._import_modal_open = False
                    return
                elif event.key == pygame.K_RETURN:
                    self._try_import_build()
                    return
                elif event.key == pygame.K_BACKSPACE:
                    self._import_text = self._import_text[:-1]
                    return
                elif event.key == pygame.K_v and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    # Paste from clipboard
                    try:
                        if not pygame.scrap.get_init():
                            pygame.scrap.init()
                        clipboard = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if clipboard:
                            text = clipboard.decode("utf-8").rstrip("\x00").strip()
                            self._import_text = text
                    except Exception:
                        pass
                    return
                elif event.unicode and len(event.unicode) == 1 and event.unicode.isprintable():
                    self._import_text += event.unicode
                    return
                return  # Block all other keys when modal is open

            if event.key == pygame.K_TAB:
                # Cycle through module → hull → equip
                cycle = {"slot": "hull", "hull": "slot"}
                self._builder_mode = cycle.get(self._builder_mode, "slot")
                self._equip_selected_module_idx = None
                try:
                    get_audio_manager().play_sfx("ui_click")
                except Exception:
                    pass
            elif event.key == pygame.K_r:
                if self._builder_mode == "slot":
                    self._module_rotation = (self._module_rotation + 1) % 4
                else:
                    self._shape_rotation = (self._shape_rotation + 1) % 4
            elif event.key == pygame.K_q:
                if self._builder_mode == "slot":
                    self._module_flipped = not self._module_flipped
                else:
                    self._shape_flipped = not self._shape_flipped
            elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                if self._builder_mode == "slot" and self._selected_placed_module_idx is not None:
                    self._push_undo()
                    idx = self._selected_placed_module_idx
                    if 0 <= idx < len(self.build.modules):
                        self.build.modules.pop(idx)
                    self._selected_placed_module_idx = None
                    self._modified = True
                    self._recompute_stats()
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
            elif event.key == pygame.K_c:
                if self._builder_mode == "slot":
                    self._recolor_mode = not getattr(self, "_recolor_mode", False)
                    self._recolor_material_id = "standard_plate"
            elif event.key == pygame.K_x:
                self._mirror_mode = not self._mirror_mode
            # [D] key retired — equipment now installed via EQUIP mode
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
            elif event.button == 2:  # Middle click — start pan
                self._panning = True
                self._pan_start = event.pos
            elif event.button == 3:  # Right click — erase
                self._handle_right_click(event.pos)

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                self._panning = False

        if event.type == pygame.MOUSEMOTION:
            if self._panning:
                dx = event.pos[0] - self._pan_start[0]
                dy = event.pos[1] - self._pan_start[1]
                self._pan_offset_x += dx
                self._pan_offset_y += dy
                self._pan_start = event.pos

        if event.type == pygame.MOUSEWHEEL:
            mx, _my = pygame.mouse.get_pos()
            if mx < GRID_AREA_X:
                if self._builder_mode == "slot":
                    # Slot palette scroll
                    self._slot_palette_scroll = max(
                        0,
                        self._slot_palette_scroll - event.y * 30,
                    )
                else:
                    # Shape palette scroll
                    self._shape_scroll_offset = max(
                        0,
                        self._shape_scroll_offset - event.y * 30,
                    )
            elif mx > MATERIAL_PANEL_X:
                # Material panel scroll
                self._material_scroll_offset = max(
                    0,
                    self._material_scroll_offset - event.y * 30,
                )
            else:
                # Grid zoom — works from anywhere not on side panels
                self._zoom_level = max(0.5, min(4.0, self._zoom_level + event.y * 0.25))

    def _handle_left_click(self, pos: tuple[int, int]) -> None:
        mx, my = pos

        # --- Mode toggle click (header area) ---
        toggle_y = scale_y(30)
        toggle_h = scale_y(20)
        center_x = WINDOW_WIDTH // 2
        btn_w = scale_x(70)
        gap = 4
        total_w = btn_w * 2 + gap
        start_x = center_x - total_w // 2
        modes = ["slot", "hull"]
        if toggle_y <= my < toggle_y + toggle_h:
            for i, mode_id in enumerate(modes):
                bx = start_x + i * (btn_w + gap)
                if bx <= mx < bx + btn_w:
                    self._builder_mode = mode_id
                    self._equip_selected_module_idx = None
                    return

        # --- Frame variant click (header area, Medium+ only) ---
        if hasattr(self, "_frame_variant_rects"):
            for variant_key, rect in self._frame_variant_rects.items():
                if rect.collidepoint(mx, my):
                    new_variant = None if variant_key == "default" else variant_key
                    if new_variant != self.build.frame_variant:
                        self._push_undo()
                        self.build.frame_variant = new_variant
                        self._modified = True
                        self._recompute_stats()
                        try:
                            get_audio_manager().play_sfx("ui_click")
                        except Exception:
                            pass
                    return

        # --- Overlay toggle clicks (right panel, slot mode) ---
        if self._builder_mode == "slot":
            if hasattr(self, "_integrity_toggle_rect") and self._integrity_toggle_rect.collidepoint(
                mx, my
            ):
                self._show_integrity_overlay = not self._show_integrity_overlay
                self._cached_integrity = None  # Force recompute
                return
            if hasattr(self, "_com_toggle_rect") and self._com_toggle_rect.collidepoint(mx, my):
                self._show_com_overlay = not self._show_com_overlay
                return

        # --- Slot mode routing ---
        if self._builder_mode == "slot":
            # Click on slot palette (left panel)
            if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W:
                self._handle_slot_palette_click(mx, my)
                return

            # Click on grid — slot placement or selection
            grid_pos = self._screen_to_grid(mx, my)
            if grid_pos:
                if self._selected_slot_def_id:
                    self._place_slot_at(*grid_pos)
                else:
                    self._select_slot_at(*grid_pos)
            return

        # --- EQUIP mode routing (disabled — moves to Loadout tab) ---
        # if self._builder_mode == "equip":
        #     if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W:
        #         self._handle_equip_slot_list_click(mx, my)
        #         return
        #     if MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W:
        #         self._handle_equip_panel_click(mx, my)
        #         return
        #     grid_pos = self._screen_to_grid(mx, my)
        #     if grid_pos:
        #         self._select_equip_module_at(*grid_pos)
        #     return

        # --- Hull mode routing (existing behavior) ---
        # Click on shape palette
        if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W:
            self._handle_shape_palette_click(mx, my)
            return

        # Click on material panel
        if MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W:
            self._handle_material_panel_click(mx, my)
            return

        # Click on grid — route through active tool
        grid_pos = self._screen_to_grid(mx, my)
        if grid_pos:
            if self._active_tool == "stamp" and self._selected_shape:
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
        """Erase pixel, remove slot, or remove module at clicked position."""
        grid_pos = self._screen_to_grid(pos[0], pos[1])
        if grid_pos:
            if self._builder_mode == "slot":
                # Right-click in slot mode: remove placed slot at position
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

    # ------------------------------------------------------------------
    # Module Mode Interactions (Phase 4)
    # ------------------------------------------------------------------

    def _get_module_catalog(self) -> dict[str, ShipModule]:
        """Get the module catalog from the data loader."""
        return getattr(self.data_loader, "ship_modules", {})

    def _get_filtered_modules(self) -> list[ShipModule]:
        """Get modules filtered by category, unlocked first, sorted by name."""
        catalog = self._get_module_catalog()
        unlocked = self.player.unlocked_modules
        modules = list(catalog.values())
        if self._module_category_filter != "all":
            modules = [m for m in modules if m.category == self._module_category_filter]
        # Sort: unlocked first, then by category and name
        modules.sort(key=lambda m: (m.id not in unlocked, m.category, m.name))
        return modules

    def _is_module_unlocked(self, module_id: str) -> bool:
        """Check if a module blueprint is unlocked for the player."""
        return module_id in self.player.unlocked_modules

    def _handle_module_catalog_click(self, mx: int, my: int) -> None:
        """Handle click on the module catalog panel (left side in module mode)."""
        # Category tabs — two rows of 4
        tab_y_start = SHAPE_PANEL_Y + 22
        tab_h = scale_y(16)
        tab_row_gap = 2
        tabs_per_row = 4
        tab_pad = 3
        tab_w = (SHAPE_PANEL_W - tab_pad * 2 - (tabs_per_row - 1) * 2) // tabs_per_row
        for i, cat in enumerate(self._module_categories):
            row = i // tabs_per_row
            col = i % tabs_per_row
            tx = SHAPE_PANEL_X + tab_pad + col * (tab_w + 2)
            ty = tab_y_start + row * (tab_h + tab_row_gap)
            if tx <= mx < tx + tab_w and ty <= my < ty + tab_h:
                self._module_category_filter = cat
                self._module_catalog_scroll = 0
                return

        # Module items below tabs
        modules = self._get_filtered_modules()
        item_h = scale_y(46)
        start_y = SHAPE_PANEL_Y + scale_y(58) - self._module_catalog_scroll
        for i, module in enumerate(modules):
            iy = start_y + i * item_h
            if SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W and iy <= my < iy + item_h:
                if not self._is_module_unlocked(module.id):
                    return  # Can't select locked modules
                if self._selected_module_id == module.id:
                    self._selected_module_id = None
                else:
                    self._selected_module_id = module.id
                    self._module_rotation = 0
                    self._module_flipped = False
                self._selected_placed_module_idx = None
                return

    def _get_oriented_preview_module(self) -> Optional[ShipModule]:
        """Get the selected module with rotation/flip applied for preview."""
        if not self._selected_module_id:
            return None
        catalog = self._get_module_catalog()
        module = catalog.get(self._selected_module_id)
        if not module:
            return None
        oriented = module
        if self._module_flipped:
            oriented = oriented.flipped()
        if self._module_rotation:
            oriented = oriented.rotated(self._module_rotation)
        return oriented

    def _place_module_at(self, gx: int, gy: int) -> None:
        """Place the selected module at the given grid position."""
        if not self._selected_module_id:
            return
        catalog = self._get_module_catalog()
        materials = getattr(self.data_loader, "hull_materials", {})

        placed = PlacedModule(
            module_id=self._selected_module_id,
            x=gx,
            y=gy,
            rotation=self._module_rotation,
            flipped=self._module_flipped,
        )
        ok, _msg = can_place_module(self.build, placed, catalog, materials)
        if ok:
            self._push_undo()
            self.build.modules.append(placed)
            self._modified = True
            self._selected_placed_module_idx = None
            self._recompute_stats()
            # Placement feedback: sound + flash + particles
            try:
                get_audio_manager().play_sfx("ui_build")
            except Exception:
                pass
            # Module placement flash at grid position
            cell = self._get_cell_size()
            ox, oy = self._get_grid_origin()
            fx = ox + gx * cell + cell
            fy = oy + gy * cell + cell
            self.particles.emit(fx, fy, SPARK_BURST)
            self._placement_flash_timer = 0.15
            self._placement_flash_pos = (gx, gy)
        else:
            # Invalid placement buzz
            try:
                get_audio_manager().play_sfx("ui_error")
            except Exception:
                pass

    def _select_module_at(self, gx: int, gy: int) -> None:
        """Select a placed module at the given grid position (for removal/info)."""
        catalog = self._get_module_catalog()
        for i, placed in enumerate(self.build.modules):
            if placed.module_id not in catalog:
                continue
            pixels = resolve_placed_module(placed, catalog)
            for p in pixels:
                if p.x == gx and p.y == gy:
                    self._selected_placed_module_idx = i
                    self._selected_module_id = None  # Deselect catalog item
                    return
        # Clicked empty space — deselect
        self._selected_placed_module_idx = None

    def _remove_module_at(self, gx: int, gy: int) -> None:
        """Remove the module at the given grid position."""
        catalog = self._get_module_catalog()
        for i, placed in enumerate(self.build.modules):
            if placed.module_id not in catalog:
                continue
            pixels = resolve_placed_module(placed, catalog)
            for p in pixels:
                if p.x == gx and p.y == gy:
                    self._push_undo()
                    self.build.modules.pop(i)
                    self._selected_placed_module_idx = None
                    self._modified = True
                    self._recompute_stats()
                    try:
                        get_audio_manager().play_sfx("ui_cancel")
                    except Exception:
                        pass
                    return

    def _recolor_pixel_at(self, gx: int, gy: int) -> None:
        """Recolor a module hull pixel at the given grid position."""
        catalog = self._get_module_catalog()
        for _i, placed in enumerate(self.build.modules):
            if placed.module_id not in catalog:
                continue
            module = catalog[placed.module_id]
            oriented = module
            if placed.flipped:
                oriented = oriented.flipped()
            if placed.rotation:
                oriented = oriented.rotated(placed.rotation)
            # Check if this grid position is within this module
            local_x = gx - placed.x
            local_y = gy - placed.y
            if 0 <= local_x < oriented.width and 0 <= local_y < oriented.height:
                if oriented.pixel_grid[local_y][local_x] == ".":
                    continue  # Empty cell
                if not is_pixel_recolorable(oriented, local_x, local_y):
                    return  # Functional pixel — locked
                # Apply the recolor
                self._push_undo()
                placed.color_overrides[(local_x, local_y)] = self._recolor_material_id
                self._modified = True
                self._recompute_stats()
                try:
                    get_audio_manager().play_sfx("ui_click")
                except Exception:
                    pass
                return

    def _handle_recolor_material_click(self, mx: int, my: int) -> None:
        """Select a hull material for recoloring from the right panel."""
        all_mats = getattr(self.data_loader, "hull_materials", {})
        hull_mats = [all_mats[mid] for mid in HULL_PIXEL_MATERIALS if mid in all_mats]
        swatch_h = scale_y(50)
        start_y = MATERIAL_PANEL_Y + scale_y(26)
        pad = 4
        for i, mat in enumerate(hull_mats):
            sy = start_y + i * (swatch_h + pad)
            if (
                MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W
                and sy <= my < sy + swatch_h
            ):
                self._recolor_material_id = mat.id
                return

    # ------------------------------------------------------------------
    # Slot Palette Interactions (S2.2/S2.3)
    # ------------------------------------------------------------------

    def _get_slot_definitions_grouped(self) -> list[tuple[str, list[SlotDefinition]]]:
        """Return slot definitions grouped by type in display order.

        Returns:
            List of (slot_type, [SlotDefinition, ...]) tuples ordered by
            _SLOT_TYPE_ORDER.
        """
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        groups: dict[str, list[SlotDefinition]] = {}
        for sd in slot_defs.values():
            groups.setdefault(sd.slot_type, []).append(sd)
        # Sort each group by size order: small, medium, large
        from spacegame.models.slot_definition import SIZE_ORDER

        for defs in groups.values():
            defs.sort(key=lambda d: SIZE_ORDER.get(d.size, 0))
        # Return in display order
        result = []
        for st in _SLOT_TYPE_ORDER:
            if st in groups:
                result.append((st, groups[st]))
        return result

    def _get_slot_type_counts(self) -> dict[str, int]:
        """Count how many placed slots exist per slot type."""
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        counts: dict[str, int] = {}
        for ps in self.build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if sdef:
                counts[sdef.slot_type] = counts.get(sdef.slot_type, 0) + 1
        return counts

    def _get_slot_type_limit(self, slot_type: str) -> int:
        """Get the frame limit for a slot type based on current weight class."""
        limits = FRAME_SLOT_LIMITS.get(self.build.weight_class, {})
        return limits.get(slot_type, 0)

    def _handle_slot_palette_click(self, mx: int, my: int) -> None:
        """Handle click on the slot palette panel (left side in slot mode)."""
        groups = self._get_slot_definitions_grouped()
        item_h = scale_y(24)
        group_header_h = scale_y(20)
        start_y = SHAPE_PANEL_Y + scale_y(26) - self._slot_palette_scroll
        y_cursor = start_y

        for _slot_type, defs in groups:
            y_cursor += group_header_h  # Skip group header
            for sdef in defs:
                if (
                    SHAPE_PANEL_X <= mx < SHAPE_PANEL_X + SHAPE_PANEL_W
                    and y_cursor <= my < y_cursor + item_h
                ):
                    if self._selected_slot_def_id == sdef.id:
                        self._selected_slot_def_id = None
                    else:
                        self._selected_slot_def_id = sdef.id
                    return
                y_cursor += item_h

    def _validate_slot_placement(self, gx: int, gy: int, sdef: SlotDefinition) -> tuple[bool, str]:
        """Validate whether a slot can be placed at the given grid position.

        Checks bounds, overlap with existing slots, frame slot limit,
        and weight budget.

        Args:
            gx: Grid column of top-left corner.
            gy: Grid row of top-left corner.
            sdef: The slot definition to place.

        Returns:
            (success, message) tuple.
        """
        cw, ch = self.build.canvas_w, self.build.canvas_h
        fw, fh = sdef.footprint_w, sdef.footprint_h

        # Bounds check
        if gx < 0 or gy < 0 or gx + fw > cw or gy + fh > ch:
            return False, "Slot extends beyond canvas"

        # Overlap check with existing placed slots
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for ps in self.build.placed_slots:
            other = slot_defs.get(ps.slot_def_id)
            if not other:
                continue
            ow, oh = other.footprint_w, other.footprint_h
            # AABB overlap test
            if gx < ps.x + ow and gx + fw > ps.x and gy < ps.y + oh and gy + fh > ps.y:
                return False, "Overlaps existing slot"

        # Frame slot limit
        counts = self._get_slot_type_counts()
        current = counts.get(sdef.slot_type, 0)
        limit = self._get_slot_type_limit(sdef.slot_type)
        if current >= limit:
            return (
                False,
                f"{_TYPE_DISPLAY.get(sdef.slot_type, sdef.slot_type)} limit reached ({limit})",
            )

        # Weight budget
        stats = self._computed_stats
        if stats:
            new_weight = stats.weight_current + sdef.weight
            if new_weight > stats.weight_max:
                return False, f"Exceeds weight limit ({new_weight:.1f}/{stats.weight_max})"

        return True, "OK"

    def _place_slot_at(self, gx: int, gy: int) -> None:
        """Place the selected slot definition at the given grid position."""
        if not self._selected_slot_def_id:
            return
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        sdef = slot_defs.get(self._selected_slot_def_id)
        if not sdef:
            return

        ok, _msg = self._validate_slot_placement(gx, gy, sdef)
        if ok:
            self._push_undo()
            self.build.placed_slots.append(PlacedSlot(slot_def_id=sdef.id, x=gx, y=gy))
            self._modified = True
            self._recompute_stats()
            # Placement feedback
            try:
                get_audio_manager().play_sfx("ui_build")
            except Exception:
                pass
            cell = self._get_cell_size()
            ox, oy = self._get_grid_origin()
            fx = ox + gx * cell + (sdef.footprint_w * cell) // 2
            fy = oy + gy * cell + (sdef.footprint_h * cell) // 2
            self.particles.emit(fx, fy, SPARK_BURST)
            self._placement_flash_timer = 0.15
            self._placement_flash_pos = (gx, gy)
        else:
            try:
                get_audio_manager().play_sfx("ui_error")
            except Exception:
                pass

    def _select_slot_at(self, gx: int, gy: int) -> None:
        """Select a placed slot at the given grid position (for info display)."""
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for ps in self.build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            if ps.x <= gx < ps.x + sdef.footprint_w and ps.y <= gy < ps.y + sdef.footprint_h:
                # Deselect the palette item when clicking an existing slot
                self._selected_slot_def_id = None
                return
        # Clicked empty space — deselect palette
        self._selected_slot_def_id = None

    def _remove_slot_at(self, gx: int, gy: int) -> None:
        """Remove the placed slot at the given grid position."""
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for i, ps in enumerate(self.build.placed_slots):
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            if ps.x <= gx < ps.x + sdef.footprint_w and ps.y <= gy < ps.y + sdef.footprint_h:
                self._push_undo()
                self.build.placed_slots.pop(i)
                self._modified = True
                self._recompute_stats()
                try:
                    get_audio_manager().play_sfx("ui_cancel")
                except Exception:
                    pass
                return

    def _handle_material_panel_click(self, mx: int, my: int) -> None:
        """Select a hull material from the panel."""
        all_mats = getattr(self.data_loader, "hull_materials", {})
        hull_mats = [all_mats[mid] for mid in HULL_PIXEL_MATERIALS if mid in all_mats]
        if not hull_mats:
            hull_mats = list(self._get_available_materials())

        swatch_h = scale_y(50)
        start_y = MATERIAL_PANEL_Y + scale_y(26)
        pad = 4
        for i, mat in enumerate(hull_mats):
            sy = start_y + i * (swatch_h + pad)
            if (
                MATERIAL_PANEL_X <= mx < MATERIAL_PANEL_X + MATERIAL_PANEL_W
                and sy <= my < sy + swatch_h
            ):
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

        ok, _msg = self.grid_manager.can_place_shape(
            shape,
            gx,
            gy,
            material,
            self.build.pixels,
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
                        self.build.pixels.append(PlacedPixel(px, py, self._selected_material_id))
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
        self.build.pixels = [p for p in self.build.pixels if not (p.x == gx and p.y == gy)]
        if self._mirror_mode:
            mx = canvas - 1 - gx
            self.build.pixels = [p for p in self.build.pixels if not (p.x == mx and p.y == gy)]
        if len(self.build.pixels) < before:
            self._modified = True
            self._recompute_stats()

    # ------------------------------------------------------------------
    # Undo/Redo (Phase B2)
    # ------------------------------------------------------------------

    def _push_undo(self) -> None:
        """Save current build state (pixels + modules + slots) to undo stack."""
        snapshot = {
            "pixels": [p.to_dict() for p in self.build.pixels],
            "modules": [m.to_dict() for m in self.build.modules],
            "slots": [s.to_dict() for s in self.build.slots],
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _restore_snapshot(self, snapshot: dict | list) -> None:
        """Restore build state from a snapshot.

        Handles both new dict format (pixels + modules + slots) and
        legacy list format (pixel dicts only, from before module support).
        """
        if isinstance(snapshot, list):
            # Legacy format: plain list of pixel dicts
            self.build.pixels = [PlacedPixel.from_dict(d) for d in snapshot]
            self.build.modules = []
            self.build.slots = []
        else:
            self.build.pixels = [PlacedPixel.from_dict(d) for d in snapshot["pixels"]]
            self.build.modules = [PlacedModule.from_dict(d) for d in snapshot.get("modules", [])]
            self.build.slots = [DesignatedSlot.from_dict(d) for d in snapshot.get("slots", [])]
        self._selected_placed_module_idx = None
        self._modified = True
        self._recompute_stats()

    def _make_current_snapshot(self) -> dict:
        """Create a snapshot of the current build state."""
        return {
            "pixels": [p.to_dict() for p in self.build.pixels],
            "modules": [m.to_dict() for m in self.build.modules],
            "slots": [s.to_dict() for s in self.build.slots],
        }

    def _undo(self) -> None:
        """Restore previous build state."""
        if not self._undo_stack:
            return
        self._redo_stack.append(self._make_current_snapshot())
        snapshot = self._undo_stack.pop()
        self._restore_snapshot(snapshot)

    def _redo(self) -> None:
        """Restore next build state (after undo)."""
        if not self._redo_stack:
            return
        self._undo_stack.append(self._make_current_snapshot())
        snapshot = self._redo_stack.pop()
        self._restore_snapshot(snapshot)

    # (Legacy slot designator & equipment modal removed — use EQUIP mode)

    def _save_draft(self) -> None:
        """Save current build as a draft (no credits charged)."""
        max_drafts = 20
        if len(self.player.build_drafts) >= max_drafts:
            self._validation_warnings.append(
                f"Draft limit reached ({max_drafts}). Delete a draft first."
            )
            return
        draft_num = len(self.player.build_drafts) + 1
        draft_name = self.build.preset_name or f"Draft {draft_num}"
        self.player.build_drafts.append(
            {
                "name": draft_name,
                "build": self.build.to_dict(),
            }
        )
        logger.info(f"Saved draft: {draft_name} ({len(self.player.build_drafts)} total)")

    def _share_build(self) -> None:
        """Export current build as a shareable text code to clipboard."""
        from spacegame.models.build_sharing import export_build_code

        code = export_build_code(self.build)
        # Copy to clipboard via pygame scrap
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, code.encode("utf-8"))
        except Exception:
            pass  # Clipboard not available on all platforms
        # Show feedback
        self._feedback_messages.append(
            {
                "text": f"Build code copied! ({len(code)} chars)",
                "x": float(WINDOW_WIDTH // 2 - 80),
                "y": float(WINDOW_HEIGHT // 2),
                "timer": 2.0,
                "color": Colors.GREEN,
            }
        )
        try:
            get_audio_manager().play_sfx("ui_confirm")
        except Exception:
            pass
        logger.info(f"Build exported: {len(code)} chars")

    def _try_import_build(self) -> None:
        """Attempt to import a build from the text in _import_text."""
        from spacegame.models.build_sharing import (
            check_blueprint_availability,
            import_build_code,
        )

        catalog = self._get_module_catalog()
        materials = getattr(self.data_loader, "hull_materials", {})
        build, err = import_build_code(self._import_text.strip(), catalog, materials)
        if build is None:
            self._import_error = err or "Invalid build code"
            self._import_missing_blueprints = []
            return

        # Check blueprint availability
        missing = check_blueprint_availability(build, catalog, self.player.unlocked_modules)
        if missing:
            self._import_missing_blueprints = missing
            self._import_error = f"{len(missing)} blueprint(s) needed"
            # Still load the build for viewing (but can't confirm)
            self._push_undo()
            self.build = build
            self.grid_manager = ShipGridManager(self.build.weight_class)
            self._modified = True
            self._recompute_stats()
            self._import_modal_open = False
            return

        # All blueprints owned — load fully
        self._push_undo()
        self.build = build
        self.grid_manager = ShipGridManager(self.build.weight_class)
        self._modified = True
        self._recompute_stats()
        self._import_modal_open = False
        self._import_error = ""
        self._import_missing_blueprints = []
        self._feedback_messages.append(
            {
                "text": "Build imported successfully!",
                "x": float(WINDOW_WIDTH // 2 - 70),
                "y": float(WINDOW_HEIGHT // 2),
                "timer": 1.5,
                "color": Colors.GREEN,
            }
        )
        try:
            get_audio_manager().play_sfx("ui_confirm")
        except Exception:
            pass

    def _confirm_build(self) -> None:
        """Apply the current build to the player's ship. Charges only the delta cost."""
        if not self._can_confirm:
            return

        # Compute delta cost: new build cost minus what was already paid at entry
        # Positive delta = player pays. Negative delta = player gets 80% refund.
        REFUND_RATE = 0.80
        new_cost = self._computed_stats.total_cost if self._computed_stats else 0
        entry_cost = getattr(self, "_entry_cost", 0)
        raw_delta = new_cost - entry_cost

        if raw_delta > 0:
            # Player is adding — charge full delta
            if raw_delta > self.player.credits:
                self._validation_warnings.append(
                    f"Cannot afford changes ({raw_delta:,} CR needed, you have {self.player.credits:,} CR)"
                )
                return
            self.player.credits -= raw_delta
            logger.info(
                f"Build cost: {raw_delta:,} CR charged (new: {new_cost:,}, was: {entry_cost:,})"
            )
        elif raw_delta < 0:
            # Player is removing — refund 80% of the reduction
            refund = int(abs(raw_delta) * REFUND_RATE)
            if refund > 0:
                self.player.credits += refund
                logger.info(f"Build refund: +{refund:,} CR (80% of {abs(raw_delta):,} removed)")
        else:
            logger.info("Build confirmed (no cost change)")

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

        catalog = self._get_module_catalog()
        has_modules = len(self.build.modules) > 0
        has_slots = len(self.build.placed_slots) > 0
        has_pixels = len(self.build.pixels) > 0
        has_content = has_modules or has_slots or has_pixels

        # NEW: Slot-based validation (primary for new builds)
        if has_slots:
            slot_defs = getattr(self.data_loader, "slot_definitions", {})
            slot_type_counts: dict[str, int] = {}
            for ps in self.build.placed_slots:
                sd = slot_defs.get(ps.slot_def_id)
                if sd:
                    slot_type_counts[sd.slot_type] = slot_type_counts.get(sd.slot_type, 0) + 1

            # Required slot checks
            if slot_type_counts.get("engine", 0) < 1:
                warnings.append("Engine required! Place at least 1 engine slot.")
            if slot_type_counts.get("reactor", 0) < 1:
                warnings.append("Reactor required! Place at least 1 reactor slot.")

            # Frame slot limit checks
            limits = FRAME_SLOT_LIMITS.get(self.build.weight_class, {})
            for stype, count in slot_type_counts.items():
                limit = limits.get(stype, 0)
                if count > limit:
                    warnings.append(f"Too many {stype} slots: {count}/{limit}")

        # LEGACY: Module-based validation
        elif has_modules:
            req_ok, req_msg = validate_requirements(self.build, catalog)
            if not req_ok:
                warnings.append(req_msg)

            conn_ok, conn_msg = validate_connectivity(self.build, catalog)
            if not conn_ok:
                warnings.append(f"Disconnected: {conn_msg}")

        # LEGACY: Old hull-only builds
        elif has_pixels:
            has_core = any(s.slot_type == "core" for s in self.build.slots)
            if not has_core:
                warnings.append("No Core slot — ship has no energy system.")
            has_weapon_or_engine = any(
                s.slot_type in ("weapon", "engine") for s in self.build.slots
            )
            if not has_weapon_or_engine:
                warnings.append("No weapons or engines — ship can't fight or flee.")

        if not has_content:
            warnings.append("Empty build. Place slots and hull pixels to design your ship.")

        # Advisory warnings (non-blocking, informational)
        advisories: list[str] = []
        if has_modules and len(warnings) == 0:
            try:
                from spacegame.models.ship_module import resolve_all_pixels
                from spacegame.models.ship_physics import (
                    BalanceRating,
                    compute_center_of_mass,
                    compute_hull_efficiency,
                )

                materials = getattr(self.data_loader, "hull_materials", {})
                _, _, offset_pct, rating = compute_center_of_mass(
                    self.build,
                    materials,
                    catalog,
                )
                if rating == BalanceRating.OFF_BALANCE:
                    advisories.append(
                        f"Center of mass {offset_pct:.0f}% off-center (handling penalty)"
                    )
                elif rating == BalanceRating.SEVERELY_OFF:
                    advisories.append(
                        f"Center of mass {offset_pct:.0f}% off-center (severe penalty)"
                    )

                all_pixels = resolve_all_pixels(self.build, catalog)
                coords = [(p.x, p.y) for p in all_pixels]
                if coords:
                    _, _, efficiency = compute_hull_efficiency(coords)
                    if efficiency < 0.15:
                        advisories.append("Low hull efficiency: ship is mostly exposed surface")

                # Check if cockpit is on exterior
                for pm in self.build.modules:
                    mod = catalog.get(pm.module_id)
                    if mod and mod.category == "cockpit":
                        cpx = resolve_placed_module(pm, catalog)
                        coord_set = {(p.x, p.y) for p in all_pixels}
                        for cp in cpx:
                            has_empty = any(
                                (cp.x + dx, cp.y + dy) not in coord_set
                                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
                            )
                            if has_empty:
                                advisories.append("Cockpit is exposed on the hull exterior")
                                break
                        break
            except ImportError:
                pass

        self._validation_warnings = warnings
        self._advisory_warnings = advisories
        was_confirmable = self._can_confirm
        self._can_confirm = has_content and len(warnings) == 0

        # Play positive feedback when all requirements first met
        if self._can_confirm and not was_confirmable and has_modules:
            try:
                get_audio_manager().play_sfx("achievement")
            except Exception:
                pass
            ox, oy = self._get_grid_origin()
            self._feedback_messages.append(
                {
                    "text": "All requirements met!",
                    "x": float(ox + GRID_AREA_W // 2 - 50),
                    "y": float(oy + GRID_AREA_H // 2),
                    "timer": 1.5,
                    "color": Colors.GREEN,
                }
            )

    def _check_builder_hint_triggers(self) -> None:
        """Check if any builder tutorial hints should fire (QA Fix #7).

        Hints trigger based on builder state milestones, checked via
        the player's dialogue_flags to ensure one-time firing.
        """
        flags = self.player.dialogue_flags if hasattr(self.player, "dialogue_flags") else {}

        # Module builder hints (Shipbuilder Upgrade)
        if self._builder_mode == "slot":
            # First entry into module builder
            if not flags.get("builder_module_welcome_seen"):
                self.player.dialogue_flags["builder_module_welcome_seen"] = True
                self._pending_hint = "builder_module_welcome"
                return

            # After placing first module (cockpit likely) → engine hint
            has_cockpit = any(
                self._get_module_catalog().get(m.module_id, None) is not None
                and self._get_module_catalog()[m.module_id].category == "cockpit"
                for m in self.build.modules
            )
            has_engine = any(
                self._get_module_catalog().get(m.module_id, None) is not None
                and self._get_module_catalog()[m.module_id].category == "engine"
                for m in self.build.modules
            )
            if has_cockpit and not has_engine and not flags.get("builder_module_engine_seen"):
                self.player.dialogue_flags["builder_module_engine_seen"] = True
                self._pending_hint = "builder_module_engine"
                return

            # After placing 2+ modules → requirements hint
            if len(self.build.modules) >= 2 and not flags.get("builder_module_requirements_seen"):
                self.player.dialogue_flags["builder_module_requirements_seen"] = True
                self._pending_hint = "builder_module_requirements"
                return

            # When all requirements met → confirm hint
            if self._can_confirm and not flags.get("builder_module_confirm_seen"):
                self.player.dialogue_flags["builder_module_confirm_seen"] = True
                self._pending_hint = "builder_module_confirm"
                return

        # Hull mode hint
        if (
            self._builder_mode == "hull"
            and not flags.get("builder_module_hull_seen")
            and flags.get("builder_module_welcome_seen", False)
        ):
            self.player.dialogue_flags["builder_module_hull_seen"] = True
            self._pending_hint = "builder_module_hull"
            return

        # Legacy shape-based hints
        if (
            len(self.build.pixels) > 0
            and not flags.get("builder_hint_shapes")
            and flags.get("builder_hint_welcome_seen", False)
        ):
            self.player.dialogue_flags["builder_hint_shapes"] = True
            self._pending_hint = "builder_shapes"

        if self._active_tool != "stamp" and not flags.get("builder_hint_tools"):
            self.player.dialogue_flags["builder_hint_tools"] = True
            self._pending_hint = "builder_tools"

        # Legacy slot hint removed — equipment managed via EQUIP mode

    def _recompute_stats(self) -> None:
        materials = getattr(self.data_loader, "hull_materials", {})
        equipment = getattr(self.data_loader, "upgrades", {})
        module_catalog = self._get_module_catalog()
        slot_definitions = getattr(self.data_loader, "slot_definitions", {})
        self._computed_stats = ShipStatsComputer.compute(
            self.build,
            materials,
            equipment,
            module_catalog=module_catalog,
            slot_definitions=slot_definitions,
        )
        # Invalidate physics overlay caches
        self._cached_integrity = None

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
        cw, ch = self.build.canvas_w, self.build.canvas_h
        base = min(GRID_AREA_W // cw, GRID_AREA_H // ch)
        return max(1, int(base * self._zoom_level))

    def _get_grid_origin(self) -> tuple[int, int]:
        cw, ch = self.build.canvas_w, self.build.canvas_h
        cell = self._get_cell_size()
        ox = GRID_AREA_X + (GRID_AREA_W - cw * cell) // 2 + int(self._pan_offset_x)
        oy = GRID_AREA_Y + (GRID_AREA_H - ch * cell) // 2 + int(self._pan_offset_y)
        return ox, oy

    def _screen_to_grid(self, sx: int, sy: int) -> Optional[tuple[int, int]]:
        ox, oy = self._get_grid_origin()
        cell = self._get_cell_size()
        if cell <= 0:
            return None
        gx = (sx - ox) // cell
        gy = (sy - oy) // cell
        cw, ch = self.build.canvas_w, self.build.canvas_h
        if 0 <= gx < cw and 0 <= gy < ch:
            return gx, gy
        return None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)

        # Track builder hint triggers (QA Fix #7)
        self._check_builder_hint_triggers()

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

        # Placement flash timer (Phase 10 visual feedback)
        if self._placement_flash_timer > 0:
            self._placement_flash_timer = max(0, self._placement_flash_timer - dt)

        # Floating feedback messages
        for msg in self._feedback_messages:
            msg["timer"] -= dt
            msg["y"] -= 25 * dt  # Rise upward
        self._feedback_messages = [m for m in self._feedback_messages if m["timer"] > 0]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Header with mode toggle
        title = self.title_font.render(
            f"DRYDOCK — {self.build.weight_class.upper()} ({self.build.canvas_w}×{self.build.canvas_h})",
            True,
            Colors.TEXT_HIGHLIGHT,
        )
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 6))

        # Mode toggle indicator (below title)
        self._render_mode_toggle(screen)

        # Credits display (top right)
        credits_text = self.small_font.render(
            f"Credits: {self.player.credits:,} CR",
            True,
            Colors.TEXT_PRIMARY,
        )
        screen.blit(credits_text, (WINDOW_WIDTH - credits_text.get_width() - scale_x(20), 14))

        # Main panels
        self._render_grid(screen)
        if self._builder_mode == "slot":
            self._render_slot_palette(screen)
            self._render_requirements_checklist(screen)
        # elif self._builder_mode == "equip":  # disabled — moves to Loadout tab
        #     self._render_equip_slot_list(screen)
        #     self._render_equip_panel(screen)
        else:
            self._render_shape_palette(screen)
            self._render_material_panel(screen)
        self._render_stats_panel(screen)

        # Floating feedback messages (Phase 10)
        for msg in self._feedback_messages:
            alpha = int(255 * min(1.0, msg["timer"] / 0.5))
            text_surf = self.label_font.render(msg["text"], True, msg["color"])
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (int(msg["x"]), int(msg["y"])))

        # Ambient particles
        self.particles.render(screen)

        # Validation warnings and advisories (above stats panel)
        all_warnings = self._validation_warnings + self._advisory_warnings
        if all_warnings:
            warn_y = STATS_PANEL_Y - scale_y(18) * len(all_warnings)
            for i, warning in enumerate(all_warnings):
                is_advisory = i >= len(self._validation_warnings)
                color = (140, 160, 200) if is_advisory else Colors.YELLOW
                prefix = "\u26a0 " if not is_advisory else "\u2139 "
                warn_surf = self.label_font.render(prefix + warning, True, color)
                screen.blit(warn_surf, (scale_x(20), warn_y))
                warn_y += scale_y(16)

        # Stat comparison preview (when hovering shape in palette)
        if self._builder_mode == "hull":
            self._render_stat_preview(screen)

        # Module hover tooltip (when hovering placed module on grid)
        if self._builder_mode == "slot":
            self._render_module_tooltip(screen)

        # Confirmation animation (overlay)
        if self._confirm_anim_timer > 0:
            self._render_confirm_animation(screen)

        # Import modal (overlay)
        if getattr(self, "_import_modal_open", False):
            self._render_import_modal(screen)

        # Help overlay (on top of everything)
        if getattr(self, "_help_overlay_open", False):
            self._render_help_overlay(screen)

    def _render_grid(self, screen: pygame.Surface) -> None:
        """Render the ship building grid with placed pixels."""
        cw, ch = self.build.canvas_w, self.build.canvas_h
        cell = self._get_cell_size()
        ox, oy = self._get_grid_origin()

        # Grid background
        grid_w = cw * cell
        grid_h = ch * cell
        pygame.draw.rect(screen, (8, 10, 20), (ox, oy, grid_w, grid_h))

        # Grid lines (subtle) — separate horizontal and vertical
        for i in range(cw + 1):
            alpha_line = 50 if i % 8 == 0 else 30
            lx = ox + i * cell
            line_surf = pygame.Surface((1, grid_h), pygame.SRCALPHA)
            line_surf.fill((100, 120, 160, alpha_line))
            screen.blit(line_surf, (lx, oy))
        for j in range(ch + 1):
            alpha_line = 50 if j % 8 == 0 else 30
            ly = oy + j * cell
            line_surf = pygame.Surface((grid_w, 1), pygame.SRCALPHA)
            line_surf.fill((100, 120, 160, alpha_line))
            screen.blit(line_surf, (ox, ly))

        # Orientation cues: BOW/STERN labels and engine zone
        # Ships face RIGHT (bow = right, stern = left)
        stern_label = self.label_font.render("STERN", True, (120, 90, 60))
        screen.blit(stern_label, (ox + 3, oy - stern_label.get_height() - 2))
        bow_label = self.label_font.render("BOW", True, (120, 90, 60))
        screen.blit(
            bow_label, (ox + grid_w - bow_label.get_width() - 3, oy - bow_label.get_height() - 2)
        )

        # Engine zone tint (left 30% of canvas = stern/rear)
        engine_zone_w = int(cw * 0.30) * cell
        if engine_zone_w > 0:
            zone_surf = pygame.Surface((engine_zone_w, grid_h), pygame.SRCALPHA)
            zone_surf.fill((200, 140, 40, 15))
            screen.blit(zone_surf, (ox, oy))

        # Filled pixels — hull pixels (material colors)
        materials = getattr(self.data_loader, "hull_materials", {})
        for pixel in self.build.pixels:
            mat = materials.get(pixel.material_id)
            color = mat.color_primary if mat else (128, 128, 128)
            px = ox + pixel.x * cell
            py = oy + pixel.y * cell
            pygame.draw.rect(screen, color, (px + 1, py + 1, cell - 1, cell - 1))

        # Module pixels — rendered from placed modules
        catalog = self._get_module_catalog()
        for mod_idx, placed_mod in enumerate(self.build.modules):
            if placed_mod.module_id not in catalog:
                continue
            mod_pixels = resolve_placed_module(placed_mod, catalog)
            is_selected = mod_idx == self._selected_placed_module_idx
            for mp in mod_pixels:
                mat = materials.get(mp.material_id)
                color = mat.color_primary if mat else (128, 128, 128)
                px = ox + mp.x * cell
                py = oy + mp.y * cell
                pygame.draw.rect(screen, color, (px + 1, py + 1, cell - 1, cell - 1))
            # Module boundary outline (dashed effect via corners)
            if is_selected or self._builder_mode == "slot":
                module = catalog[placed_mod.module_id]
                oriented = module
                if placed_mod.flipped:
                    oriented = oriented.flipped()
                if placed_mod.rotation:
                    oriented = oriented.rotated(placed_mod.rotation)
                bx = ox + placed_mod.x * cell
                by = oy + placed_mod.y * cell
                bw = oriented.width * cell
                bh = oriented.height * cell
                border_color = (255, 220, 80) if is_selected else (100, 120, 160, 80)
                border_width = 2 if is_selected else 1
                pygame.draw.rect(screen, border_color, (bx, by, bw, bh), border_width)

        # Legacy slot indicators removed — equipment managed via EQUIP mode

        # Placed slots — rendered as colored rectangles with type labels
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for ps in self.build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            fw, fh = sdef.footprint_w, sdef.footprint_h
            sx = ox + ps.x * cell
            sy = oy + ps.y * cell
            sw = fw * cell
            sh = fh * cell
            # Filled rectangle at low alpha
            fill_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            fill_surf.fill((*sdef.color, 60))
            screen.blit(fill_surf, (sx, sy))
            # Border at high alpha
            pygame.draw.rect(screen, sdef.color, (sx, sy, sw, sh), 2)
            # Center type label (e.g., "W", "D", "E")
            type_letter = _SLOT_TYPE_SHORT.get(sdef.slot_type, "?")
            if cell >= 6:
                type_surf = self.label_font.render(type_letter, True, (255, 255, 255))
                type_rect = type_surf.get_rect(center=(sx + sw // 2, sy + sh // 2))
                screen.blit(type_surf, type_rect)
            # Size label in top-left corner
            size_letter = _SIZE_DISPLAY.get(sdef.size, "?")
            if cell >= 6:
                size_surf = self.label_font.render(size_letter, True, (200, 200, 200))
                screen.blit(size_surf, (sx + 2, sy + 1))
            # Equipped indicator dot (bottom-right)
            if ps.equipped_part_id:
                dot_r = max(2, cell // 4)
                pygame.draw.circle(
                    screen, (100, 255, 100), (sx + sw - dot_r - 2, sy + sh - dot_r - 2), dot_r
                )

        # Ghost preview — slot mode or hull mode
        mouse_pos = pygame.mouse.get_pos()
        grid_pos = self._screen_to_grid(mouse_pos[0], mouse_pos[1])

        if grid_pos and self._builder_mode == "slot" and self._selected_slot_def_id:
            # Slot ghost preview
            ghost_sdef = slot_defs.get(self._selected_slot_def_id)
            if ghost_sdef:
                gx, gy = grid_pos
                fw, fh = ghost_sdef.footprint_w, ghost_sdef.footprint_h
                ok, _ = self._validate_slot_placement(gx, gy, ghost_sdef)
                ghost_color = (100, 255, 100) if ok else (255, 60, 60)
                ghost_sx = ox + gx * cell
                ghost_sy = oy + gy * cell
                ghost_sw = fw * cell
                ghost_sh = fh * cell
                ghost_surf = pygame.Surface((ghost_sw, ghost_sh), pygame.SRCALPHA)
                ghost_surf.fill((*ghost_color, 80))
                screen.blit(ghost_surf, (ghost_sx, ghost_sy))
                pygame.draw.rect(screen, ghost_color, (ghost_sx, ghost_sy, ghost_sw, ghost_sh), 2)
                # Show footprint dimensions near cursor
                dim_text = f"{fw}x{fh}"
                dim_surf = self.label_font.render(dim_text, True, ghost_color)
                screen.blit(dim_surf, (ghost_sx + ghost_sw + 3, ghost_sy))

        elif grid_pos and self._builder_mode == "slot" and self._selected_module_id:
            # Module ghost preview (legacy module placement)
            oriented = self._get_oriented_preview_module()
            if oriented:
                placed = PlacedModule(
                    module_id=self._selected_module_id,
                    x=grid_pos[0],
                    y=grid_pos[1],
                    rotation=self._module_rotation,
                    flipped=self._module_flipped,
                )
                ok, _ = can_place_module(self.build, placed, catalog, materials)
                for lx, ly, mat_char in oriented.filled_pixels():
                    gx = grid_pos[0] + lx
                    gy = grid_pos[1] + ly
                    if 0 <= gx < cw and 0 <= gy < ch:
                        px = ox + gx * cell
                        py = oy + gy * cell
                        mat_id = oriented.material_map.get(mat_char, "")
                        mat = materials.get(mat_id)
                        base_color = mat.color_primary if mat else (100, 200, 100)
                        preview_color = base_color if ok else (200, 60, 60)
                        ghost_surf = pygame.Surface((cell - 1, cell - 1), pygame.SRCALPHA)
                        ghost_surf.fill((*preview_color, 120))
                        screen.blit(ghost_surf, (px + 1, py + 1))

        elif grid_pos and self._builder_mode == "hull" and self._selected_shape:
            # Shape ghost preview (existing hull mode)
            shape = self._get_transformed_shape()
            mat = self._get_selected_material()
            ghost_color = mat.color_primary if mat else (100, 200, 100)
            valid = True
            if mat:
                ok, _ = self.grid_manager.can_place_shape(
                    shape,
                    grid_pos[0],
                    grid_pos[1],
                    mat,
                    self.build.pixels,
                )
                valid = ok
            for row_idx, row in enumerate(shape.pixel_mask):
                for col_idx, filled in enumerate(row):
                    if filled:
                        gx = grid_pos[0] + col_idx
                        gy = grid_pos[1] + row_idx
                        if 0 <= gx < cw and 0 <= gy < ch:
                            px = ox + gx * cell
                            py = oy + gy * cell
                            preview_color = ghost_color if valid else (200, 60, 60)
                            ghost_surf = pygame.Surface((cell - 1, cell - 1), pygame.SRCALPHA)
                            ghost_surf.fill((*preview_color, 100))
                            screen.blit(ghost_surf, (px + 1, py + 1))

        # Placement flash (Phase 10 visual feedback)
        if self._placement_flash_timer > 0:
            from spacegame.engine.easing import ease_out_quad

            fx, fy = self._placement_flash_pos
            flash_t = self._placement_flash_timer / 0.15  # 1→0 as flash fades
            flash_alpha = int(180 * ease_out_quad(flash_t))
            flash_surf = pygame.Surface((cell * 3, cell * 3), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, flash_alpha))
            screen.blit(flash_surf, (ox + (fx - 1) * cell, oy + (fy - 1) * cell))

        # Physics overlays (Phase 6)
        if self._show_integrity_overlay:
            self._render_integrity_overlay(screen, ox, oy, cell, cw, ch)
        if self._show_com_overlay:
            self._render_com_overlay(screen, ox, oy, cell)

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
        tab_labels = {
            "all": "All",
            "basic": "B",
            "intermediate": "I",
            "advanced": "A",
            "exotic": "X",
            "faction": "F",
        }
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
        clip_rect = pygame.Rect(
            SHAPE_PANEL_X, SHAPE_PANEL_Y + scale_y(38), SHAPE_PANEL_W, SHAPE_PANEL_H - scale_y(42)
        )
        screen.set_clip(clip_rect)

        for i, shape in enumerate(shapes):
            iy = start_y + i * item_h
            if iy + item_h < clip_rect.top or iy > clip_rect.bottom:
                continue

            is_selected = self._selected_shape and self._selected_shape.id == shape.id
            bg_color = (40, 50, 80) if is_selected else (20, 25, 40)
            pygame.draw.rect(
                screen, bg_color, (SHAPE_PANEL_X + 4, iy, SHAPE_PANEL_W - 8, item_h - 2)
            )
            if is_selected:
                pygame.draw.rect(
                    screen,
                    Colors.TEXT_HIGHLIGHT,
                    (SHAPE_PANEL_X + 4, iy, SHAPE_PANEL_W - 8, item_h - 2),
                    1,
                )

            # Shape name
            name = self.tiny_font.render(shape.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name, (SHAPE_PANEL_X + 8, iy + 2))

            # Pixel count
            info = self.label_font.render(
                f"{shape.pixel_count}px {shape.width}×{shape.height}",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(info, (SHAPE_PANEL_X + 8, iy + 18))

            # Mini preview (tiny grid of the shape)
            preview_x = SHAPE_PANEL_X + SHAPE_PANEL_W - scale_x(40)
            preview_cell = min(3, max(1, scale_x(30) // max(shape.width, shape.height)))
            for ry, row in enumerate(shape.pixel_mask):
                for cx, filled in enumerate(row):
                    if filled:
                        pygame.draw.rect(
                            screen,
                            Colors.TEXT_SECONDARY,
                            (
                                preview_x + cx * preview_cell,
                                iy + 4 + ry * preview_cell,
                                preview_cell,
                                preview_cell,
                            ),
                        )

        screen.set_clip(None)

    def _render_material_panel(self, screen: pygame.Surface) -> None:
        """Render the hull material panel on the right (hull mode)."""
        draw_panel(
            screen,
            (MATERIAL_PANEL_X, MATERIAL_PANEL_Y, MATERIAL_PANEL_W, MATERIAL_PANEL_H),
            alpha=200,
        )

        title = self.small_font.render("HULL MATERIAL", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (MATERIAL_PANEL_X + 8, MATERIAL_PANEL_Y + 6))

        # Show only the 4 hull materials as large swatches
        all_mats = getattr(self.data_loader, "hull_materials", {})
        hull_mats = [all_mats[mid] for mid in HULL_PIXEL_MATERIALS if mid in all_mats]
        if not hull_mats:
            # Fallback to old behavior if hull materials not loaded
            hull_mats = list(self._get_available_materials())

        swatch_h = scale_y(50)
        start_y = MATERIAL_PANEL_Y + scale_y(26)
        pad = 4

        for i, mat in enumerate(hull_mats):
            sy = start_y + i * (swatch_h + pad)
            is_selected = mat.id == self._selected_material_id

            # Background
            bg_color = (45, 60, 100) if is_selected else (20, 25, 40)
            pygame.draw.rect(
                screen,
                bg_color,
                (MATERIAL_PANEL_X + 4, sy, MATERIAL_PANEL_W - 8, swatch_h),
                border_radius=4,
            )
            if is_selected:
                pygame.draw.rect(
                    screen,
                    Colors.TEXT_HIGHLIGHT,
                    (MATERIAL_PANEL_X + 4, sy, MATERIAL_PANEL_W - 8, swatch_h),
                    2,
                    border_radius=4,
                )

            # Large color swatch
            swatch_w = scale_x(30)
            pygame.draw.rect(
                screen,
                mat.color_primary,
                (MATERIAL_PANEL_X + 10, sy + 6, swatch_w, swatch_h - 12),
                border_radius=2,
            )

            # Name (larger text)
            text_x = MATERIAL_PANEL_X + 14 + swatch_w
            name = self.tiny_font.render(mat.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name, (text_x, sy + 4))

            # Stats summary
            stats_parts = []
            if mat.hull_per_pixel > 0:
                stats_parts.append(f"HP:{mat.hull_per_pixel:.1f}")
            if mat.armor_per_pixel > 0:
                stats_parts.append(f"Arm:{mat.armor_per_pixel:.2f}")
            if mat.evasion_per_pixel > 0:
                stats_parts.append(f"Eva:{mat.evasion_per_pixel:.2f}")
            if stats_parts:
                stats_text = self.label_font.render(
                    "  ".join(stats_parts), True, Colors.TEXT_SECONDARY
                )
                screen.blit(stats_text, (text_x, sy + 18))

            # Weight and cost
            info = self.label_font.render(
                f"W:{mat.weight_per_pixel:.2f}  {mat.cost_per_pixel}cr/px",
                True,
                (100, 110, 130),
            )
            screen.blit(info, (text_x, sy + 32))

        # Tool hint at bottom
        tool_y = start_y + len(hull_mats) * (swatch_h + pad) + scale_y(8)
        hint = self.label_font.render(
            f"Active: {self._active_tool.upper()} [{self._active_tool[0].upper()}]",
            True,
            (100, 110, 140),
        )
        screen.blit(hint, (MATERIAL_PANEL_X + 8, tool_y))
        mirror_hint = self.label_font.render(
            f"Mirror [X]: {'ON' if self._mirror_mode else 'OFF'}",
            True,
            Colors.GREEN if self._mirror_mode else (80, 90, 110),
        )
        screen.blit(mirror_hint, (MATERIAL_PANEL_X + 8, tool_y + scale_y(14)))

    # ------------------------------------------------------------------
    # Module Mode Rendering (Phase 4)
    # ------------------------------------------------------------------

    def _render_mode_toggle(self, screen: pygame.Surface) -> None:
        """Render the SLOTS / HULL mode toggle in the header area."""
        toggle_y = scale_y(30)
        center_x = WINDOW_WIDTH // 2
        btn_w = scale_x(70)
        btn_h = scale_y(20)
        gap = 4
        total_w = btn_w * 2 + gap
        start_x = center_x - total_w // 2

        modes = [
            ("slot", "SLOTS"),
            ("hull", "HULL"),
        ]
        for i, (mode_id, label_text) in enumerate(modes):
            bx = start_x + i * (btn_w + gap)
            is_active = self._builder_mode == mode_id
            bg = (40, 80, 140) if is_active else (30, 35, 50)
            border = Colors.TEXT_HIGHLIGHT if is_active else (60, 70, 90)
            pygame.draw.rect(screen, bg, (bx, toggle_y, btn_w, btn_h), border_radius=3)
            pygame.draw.rect(screen, border, (bx, toggle_y, btn_w, btn_h), 1, border_radius=3)
            label = self.label_font.render(
                label_text, True, Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY
            )
            screen.blit(label, (bx + btn_w // 2 - label.get_width() // 2, toggle_y + 3))

        # Tab hint
        hint = self.label_font.render("[Tab]", True, (80, 90, 110))
        screen.blit(hint, (start_x + total_w + 6, toggle_y + 4))

        # Frame variant selector (Medium+ only)
        from spacegame.models.ship_build import FRAME_VARIANTS

        if self.build.weight_class in FRAME_VARIANTS:
            frame_x = scale_x(20)
            frame_y = toggle_y
            frame_btn_w = scale_x(42)
            frame_h = scale_y(20)
            variants = [("default", "Std"), ("wide", "Wide"), ("tall", "Tall")]
            frame_label = self.label_font.render("Frame:", True, (100, 110, 130))
            screen.blit(frame_label, (frame_x, frame_y + 3))
            btn_start_x = frame_x + frame_label.get_width() + 4
            self._frame_variant_rects = {}
            for i, (variant_key, label) in enumerate(variants):
                bx = btn_start_x + i * (frame_btn_w + 2)
                current = self.build.frame_variant or "default"
                is_active = variant_key == current
                bg = (40, 80, 140) if is_active else (25, 30, 45)
                border = Colors.TEXT_HIGHLIGHT if is_active else (50, 55, 70)
                rect = pygame.Rect(bx, frame_y, frame_btn_w, frame_h)
                pygame.draw.rect(screen, bg, rect, border_radius=2)
                pygame.draw.rect(screen, border, rect, 1, border_radius=2)
                v_label = self.label_font.render(
                    label, True, Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY
                )
                screen.blit(
                    v_label, (bx + frame_btn_w // 2 - v_label.get_width() // 2, frame_y + 3)
                )
                self._frame_variant_rects[variant_key] = rect

    def _render_slot_palette(self, screen: pygame.Surface) -> None:
        """Render the slot palette panel (left side, slot mode).

        Shows slot definitions grouped by type (Weapon, Defense, etc.)
        with S/M/L variants as clickable entries. Each entry shows a
        colored square, display name, footprint, weight, and cost.
        Frame slot limits are shown per group.
        """
        panel_x = SHAPE_PANEL_X
        panel_y = SHAPE_PANEL_Y
        panel_w = SHAPE_PANEL_W
        panel_h = SHAPE_PANEL_H
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        # Title
        title = self.small_font.render("SLOT PALETTE", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + 8, panel_y + 6))

        # Scrollable content
        groups = self._get_slot_definitions_grouped()
        type_counts = self._get_slot_type_counts()
        item_h = scale_y(24)
        group_header_h = scale_y(20)

        list_top = panel_y + scale_y(26)
        list_h = panel_h - scale_y(30)
        clip = pygame.Rect(panel_x, list_top, panel_w, list_h)
        screen.set_clip(clip)

        start_y = list_top - self._slot_palette_scroll
        y_cursor = start_y

        for slot_type, defs in groups:
            # Group header with limit indicator
            if (
                y_cursor + group_header_h >= list_top - group_header_h
                and y_cursor < list_top + list_h
            ):
                type_name = _TYPE_DISPLAY.get(slot_type, slot_type.title())
                placed_count = type_counts.get(slot_type, 0)
                limit = self._get_slot_type_limit(slot_type)
                header_color = defs[0].color if defs else (150, 150, 150)
                header_text = f"{type_name}: {placed_count}/{limit}"
                header_surf = self.tiny_font.render(header_text, True, header_color)
                screen.blit(header_surf, (panel_x + 8, y_cursor + 2))
                # Underline
                pygame.draw.line(
                    screen,
                    (*header_color, 80) if len(header_color) == 3 else header_color,
                    (panel_x + 6, y_cursor + group_header_h - 2),
                    (panel_x + panel_w - 6, y_cursor + group_header_h - 2),
                    1,
                )
            y_cursor += group_header_h

            for sdef in defs:
                if y_cursor + item_h >= list_top and y_cursor < list_top + list_h:
                    is_selected = sdef.id == self._selected_slot_def_id

                    # Check if limit reached for this type
                    at_limit = type_counts.get(sdef.slot_type, 0) >= self._get_slot_type_limit(
                        sdef.slot_type
                    )

                    # Background
                    if is_selected:
                        bg_color = (45, 65, 100)
                    elif at_limit:
                        bg_color = (15, 15, 22)
                    else:
                        bg_color = (20, 25, 40)
                    pygame.draw.rect(
                        screen,
                        bg_color,
                        (panel_x + 3, y_cursor, panel_w - 6, item_h - 2),
                        border_radius=3,
                    )
                    if is_selected:
                        pygame.draw.rect(
                            screen,
                            Colors.TEXT_HIGHLIGHT,
                            (panel_x + 3, y_cursor, panel_w - 6, item_h - 2),
                            1,
                            border_radius=3,
                        )

                    # Colored square for slot type
                    swatch_size = scale_y(14)
                    swatch_x = panel_x + 8
                    swatch_y = y_cursor + (item_h - swatch_size) // 2 - 1
                    swatch_color = sdef.color if not at_limit else (60, 60, 60)
                    pygame.draw.rect(
                        screen,
                        swatch_color,
                        (swatch_x, swatch_y, swatch_size, swatch_size),
                        border_radius=2,
                    )

                    # Display name
                    text_x = swatch_x + swatch_size + 6
                    name_color = (70, 70, 80) if at_limit else Colors.TEXT_PRIMARY
                    name_surf = self.label_font.render(sdef.display_name, True, name_color)
                    screen.blit(name_surf, (text_x, y_cursor + 1))

                    # Info line: footprint, weight, cost
                    info_color = (50, 50, 60) if at_limit else Colors.TEXT_SECONDARY
                    info_text = (
                        f"{sdef.footprint_w}x{sdef.footprint_h}  "
                        f"W:{sdef.weight:.0f}  "
                        f"{sdef.placement_cost:,}CR"
                    )
                    info_surf = self.label_font.render(info_text, True, info_color)
                    screen.blit(info_surf, (text_x, y_cursor + 12))

                y_cursor += item_h

        screen.set_clip(None)

        # Scroll indicator
        total_content_h = sum(group_header_h + len(defs) * item_h for _, defs in groups)
        if total_content_h > list_h:
            max_scroll = max(1, total_content_h - list_h)
            bar_h = max(10, int(list_h * (list_h / total_content_h)))
            bar_y = list_top + int((self._slot_palette_scroll / max_scroll) * (list_h - bar_h))
            pygame.draw.rect(
                screen, (80, 90, 120), (panel_x + panel_w - 5, bar_y, 3, bar_h), border_radius=1
            )

    def _render_module_catalog(self, screen: pygame.Surface) -> None:
        """Render the module catalog panel (left side, module mode)."""
        panel_x = SHAPE_PANEL_X
        panel_y = SHAPE_PANEL_Y
        panel_w = SHAPE_PANEL_W
        panel_h = SHAPE_PANEL_H
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        # Title
        title = self.small_font.render("MODULES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + 8, panel_y + 6))

        # Category filter tabs — two rows of 4 with item counts
        catalog = self._get_module_catalog()
        unlocked = self.player.unlocked_modules
        cat_counts: dict[str, int] = {"all": 0}
        for mid in unlocked:
            mod = catalog.get(mid)
            if mod:
                cat_counts["all"] = cat_counts.get("all", 0) + 1
                cat_counts[mod.category] = cat_counts.get(mod.category, 0) + 1

        tab_y_start = panel_y + 22
        tab_h = scale_y(16)
        tab_row_gap = 2
        tab_labels = {
            "all": "All",
            "cockpit": "Cockpit",
            "engine": "Engine",
            "weapon": "Weapon",
            "shield": "Shield",
            "cargo": "Cargo",
            "utility": "Utility",
            "structural": "Struct",
        }
        tabs_per_row = 4
        tab_pad = 3
        tab_w = (panel_w - tab_pad * 2 - (tabs_per_row - 1) * 2) // tabs_per_row
        for i, cat in enumerate(self._module_categories):
            row = i // tabs_per_row
            col = i % tabs_per_row
            tx = panel_x + tab_pad + col * (tab_w + 2)
            ty = tab_y_start + row * (tab_h + tab_row_gap)
            active = cat == self._module_category_filter
            bg = (50, 70, 110) if active else (25, 30, 45)
            pygame.draw.rect(screen, bg, (tx, ty, tab_w, tab_h), border_radius=2)
            count = cat_counts.get(cat, 0)
            label_text = f"{tab_labels.get(cat, cat[:5])} {count}"
            label = self.label_font.render(
                label_text, True, Colors.TEXT_PRIMARY if active else Colors.TEXT_SECONDARY
            )
            screen.blit(label, (tx + tab_w // 2 - label.get_width() // 2, ty + 1))

        # Module list (scrollable)
        modules = self._get_filtered_modules()
        item_h = scale_y(46)
        list_top = panel_y + scale_y(58)  # Below two-row tabs
        list_h = panel_h - scale_y(62)

        # Clip rect for scrollable area
        clip = pygame.Rect(panel_x, list_top, panel_w, list_h)
        screen.set_clip(clip)

        materials = getattr(self.data_loader, "hull_materials", {})
        start_y = list_top - self._module_catalog_scroll
        for i, module in enumerate(modules):
            iy = start_y + i * item_h
            if iy + item_h < list_top or iy > list_top + list_h:
                continue  # Off-screen, skip rendering

            is_selected = module.id == self._selected_module_id
            is_locked = not self._is_module_unlocked(module.id)

            if is_locked:
                bg_color = (15, 15, 22)  # Dark, grayed out
            elif is_selected:
                bg_color = (45, 65, 100)
            else:
                bg_color = (20, 25, 40)
            pygame.draw.rect(
                screen, bg_color, (panel_x + 3, iy, panel_w - 6, item_h - 2), border_radius=3
            )
            if is_selected and not is_locked:
                pygame.draw.rect(
                    screen,
                    Colors.TEXT_HIGHLIGHT,
                    (panel_x + 3, iy, panel_w - 6, item_h - 2),
                    1,
                    border_radius=3,
                )

            # Module mini-preview (render filled pixels in a small area)
            preview_size = scale_y(18)
            preview_x = panel_x + 6
            preview_y = iy + 3
            pw = module.width
            ph = module.height
            if pw > 0 and ph > 0:
                ps = min(preview_size / pw, preview_size / ph)
                for lx, ly, char in module.filled_pixels():
                    mat_id = module.material_map.get(char, "")
                    mat = materials.get(mat_id)
                    color = mat.color_primary if mat else (100, 100, 100)
                    if is_locked:
                        # Desaturate locked module previews
                        avg = (color[0] + color[1] + color[2]) // 3
                        color = (avg // 2, avg // 2, avg // 2)
                    rx = int(preview_x + lx * ps)
                    ry = int(preview_y + ly * ps)
                    rw = max(1, int(ps))
                    pygame.draw.rect(screen, color, (rx, ry, rw, rw))

            # Module name and info
            text_x = panel_x + 8 + preview_size + 4
            name_color = (70, 70, 80) if is_locked else Colors.TEXT_PRIMARY
            name_surf = self.label_font.render(module.name, True, name_color)
            screen.blit(name_surf, (text_x, iy + 2))

            # Category and weight
            cat_color = {
                "cockpit": (100, 180, 255),
                "engine": (255, 180, 80),
                "weapon": (255, 80, 80),
                "shield": (80, 220, 255),
                "cargo": (255, 220, 80),
                "utility": (80, 255, 120),
                "structural": (160, 160, 180),
                "crew": (120, 200, 120),
                "reactor": (180, 100, 240),
            }.get(module.category, Colors.TEXT_SECONDARY)
            if is_locked:
                cat_color = (50, 50, 60)
            cat_label = self.label_font.render(
                f"{module.category.upper()}  W:{module.weight:.1f}",
                True,
                cat_color,
            )
            screen.blit(cat_label, (text_x, iy + 14))

            # Cost or lock hint
            if is_locked:
                lock_hint = module.unlock_method.replace("_", " ").title()
                if module.unlock_source:
                    lock_hint += f": {module.unlock_source.replace('_', ' ').title()}"
                lock_label = self.label_font.render(
                    f"\U0001f512 {lock_hint}",
                    True,
                    (100, 70, 70),
                )
                screen.blit(lock_label, (text_x, iy + 26))
            else:
                cost_label = self.label_font.render(
                    f"{module.instantiation_cost:,} CR",
                    True,
                    Colors.TEXT_SECONDARY,
                )
                screen.blit(cost_label, (text_x, iy + 26))

        screen.set_clip(None)

        # Scroll indicator
        if len(modules) * item_h > list_h:
            max_scroll = max(1, len(modules) * item_h - list_h)
            bar_h = max(10, int(list_h * (list_h / (len(modules) * item_h))))
            bar_y = list_top + int((self._module_catalog_scroll / max_scroll) * (list_h - bar_h))
            pygame.draw.rect(
                screen, (80, 90, 120), (panel_x + panel_w - 5, bar_y, 3, bar_h), border_radius=1
            )

    def _render_requirements_checklist(self, screen: pygame.Surface) -> None:
        """Render the requirements checklist on the right panel (module mode)."""
        panel_x = MATERIAL_PANEL_X
        panel_y = MATERIAL_PANEL_Y
        panel_w = MATERIAL_PANEL_W
        panel_h = scale_y(320)
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        # Title
        title = self.small_font.render("REQUIREMENTS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + 8, panel_y + 6))

        # Count modules by category
        catalog = self._get_module_catalog()
        cat_counts: dict[str, int] = {}
        for pm in self.build.modules:
            mod = catalog.get(pm.module_id)
            if mod:
                cat_counts[mod.category] = cat_counts.get(mod.category, 0) + 1

        # Mandatory requirements
        requirements = [
            ("Cockpit", "cockpit", 1),
            ("Engine", "engine", 1),
            ("Weapon", "weapon", 1),
            ("Shield", "shield", 1),
            ("Cargo", "cargo", 1),
        ]

        # Conditional requirements
        wc = self.build.weight_class
        if wc in ("medium", "large", "xlarge"):
            requirements.append(("Crew Quarters", "crew", 1))
        if wc in ("large", "xlarge"):
            requirements.append(("Reactor", "reactor", 1))

        from spacegame.models.ship_build import MODULE_CAPS

        caps = MODULE_CAPS.get(self.build.weight_class, {})

        row_y = panel_y + scale_y(26)
        row_h = scale_y(22)
        for label, cat, needed in requirements:
            count = cat_counts.get(cat, 0)
            cap = caps.get(cat, 99)
            met = count >= needed
            at_cap = count >= cap
            check = "\u2713" if met else "\u2717"
            check_color = Colors.GREEN if met else (200, 60, 60)
            if at_cap and met:
                check_color = (200, 180, 60)  # Yellow when at cap
            label_color = Colors.TEXT_PRIMARY if met else Colors.TEXT_SECONDARY

            check_surf = self.small_font.render(check, True, check_color)
            screen.blit(check_surf, (panel_x + 8, row_y))
            name_surf = self.label_font.render(label, True, label_color)
            screen.blit(name_surf, (panel_x + 26, row_y + 3))
            count_text = f"{count}/{cap}" if cap < 99 else f"{count}"
            count_surf = self.label_font.render(count_text, True, check_color)
            screen.blit(count_surf, (panel_x + panel_w - count_surf.get_width() - 8, row_y + 3))
            row_y += row_h

        # Weight bar
        row_y += scale_y(8)
        weight_label = self.label_font.render("WEIGHT", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(weight_label, (panel_x + 8, row_y))
        row_y += scale_y(14)
        if self._computed_stats:
            cs = self._computed_stats
            ratio = cs.weight_ratio
            bar_w = panel_w - 20
            bar_color = (
                Colors.GREEN if ratio < 0.8 else (Colors.YELLOW if ratio < 0.95 else Colors.RED)
            )
            draw_bar(
                screen,
                panel_x + 10,
                row_y,
                bar_w,
                BAR_H,
                cs.weight_current,
                cs.weight_max,
                bar_color,
                font=self.label_font,
                show_value=True,
            )
            row_y += BAR_H + scale_y(6)
            ratio_label = self.label_font.render(
                f"{cs.weight_label}  ({cs.weight_current:.1f}/{cs.weight_max})",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(ratio_label, (panel_x + 10, row_y))

        # Connectivity status
        row_y += scale_y(20)
        all_pixels = resolve_all_pixels(self.build, catalog)
        if len(all_pixels) > 1:
            conn_ok, _ = validate_connectivity(self.build, catalog)
            conn_check = "\u2713" if conn_ok else "\u2717"
            conn_color = Colors.GREEN if conn_ok else (200, 60, 60)
            conn_surf = self.small_font.render(f"{conn_check} Connected", True, conn_color)
            screen.blit(conn_surf, (panel_x + 8, row_y))

        # Build cost
        row_y += scale_y(20)
        if self._computed_stats:
            cost_label = self.label_font.render(
                f"Build Cost: {self._computed_stats.total_cost:,} CR",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(cost_label, (panel_x + 8, row_y))

        # Module rotation/flip indicator
        row_y += scale_y(20)
        rot_label = self.label_font.render(
            f"[R] Rot: {self._module_rotation * 90}\u00b0  [Q] Flip: {'Y' if self._module_flipped else 'N'}",
            True,
            (100, 110, 140),
        )
        screen.blit(rot_label, (panel_x + 8, row_y))

        # Overlay toggle buttons (Phase 6)
        row_y += scale_y(20)
        overlay_label = self.label_font.render("OVERLAYS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(overlay_label, (panel_x + 8, row_y))
        row_y += scale_y(14)

        # Integrity overlay toggle
        int_active = self._show_integrity_overlay
        int_bg = (40, 70, 50) if int_active else (25, 30, 45)
        int_rect = pygame.Rect(panel_x + 6, row_y, panel_w - 12, scale_y(16))
        pygame.draw.rect(screen, int_bg, int_rect, border_radius=2)
        int_label = self.label_font.render(
            f"{'[x]' if int_active else '[ ]'} Structural Integrity",
            True,
            Colors.GREEN if int_active else Colors.TEXT_SECONDARY,
        )
        screen.blit(int_label, (panel_x + 10, row_y + 2))
        # Store rect for click detection
        self._integrity_toggle_rect = int_rect

        row_y += scale_y(18)

        # CoM overlay toggle
        com_active = self._show_com_overlay
        com_bg = (40, 70, 50) if com_active else (25, 30, 45)
        com_rect = pygame.Rect(panel_x + 6, row_y, panel_w - 12, scale_y(16))
        pygame.draw.rect(screen, com_bg, com_rect, border_radius=2)
        com_label = self.label_font.render(
            f"{'[x]' if com_active else '[ ]'} Center of Mass",
            True,
            Colors.GREEN if com_active else Colors.TEXT_SECONDARY,
        )
        screen.blit(com_label, (panel_x + 10, row_y + 2))
        self._com_toggle_rect = com_rect

    # ------------------------------------------------------------------
    # EQUIP Mode — delegated to builder_equip_mode.EquipModeHelper
    # See spacegame/views/builder_equip_mode.py for implementation.
    # ------------------------------------------------------------------

    def _get_equip_helper(self):
        """Lazy-create the EQUIP mode helper."""
        if not hasattr(self, "_equip_helper") or self._equip_helper is None:
            from spacegame.views.builder_equip_mode import EquipModeHelper

            self._equip_helper = EquipModeHelper(self)
        return self._equip_helper

    def _get_equip_slots(self) -> list[dict]:
        return self._get_equip_helper().get_equip_slots()

    def _get_compatible_upgrades(self, slot_type: str) -> list:
        return self._get_equip_helper().get_compatible_upgrades(slot_type)

    def _select_equip_module_at(self, gx: int, gy: int) -> None:
        self._get_equip_helper().select_module_at(gx, gy)

    def _handle_equip_slot_list_click(self, mx: int, my: int) -> None:
        self._get_equip_helper().handle_slot_list_click(mx, my)

    def _handle_equip_panel_click(self, mx: int, my: int) -> None:
        self._get_equip_helper().handle_panel_click(mx, my)

    def _render_equip_slot_list(self, screen: pygame.Surface) -> None:
        self._get_equip_helper().render_slot_list(screen)

    def _render_equip_panel(self, screen: pygame.Surface) -> None:
        self._get_equip_helper().render_panel(screen)

    # NOTE: ~260 lines of dead inline EQUIP code removed (was _DEAD_CODE_START).
    # Implementation lives in builder_equip_mode.py via EquipModeHelper.

    def _render_recolor_panel(self, screen: pygame.Surface) -> None:
        """Render the recolor material selection panel (right side, module recolor mode)."""
        panel_x = MATERIAL_PANEL_X
        panel_y = MATERIAL_PANEL_Y
        panel_w = MATERIAL_PANEL_W
        panel_h = scale_y(300)
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        # Title
        title = self.small_font.render("RECOLOR [C]", True, (255, 200, 80))
        screen.blit(title, (panel_x + 8, panel_y + 6))

        hint = self.label_font.render("Click hull pixels to recolor", True, Colors.TEXT_SECONDARY)
        screen.blit(hint, (panel_x + 8, panel_y + 22))

        # Material swatches (4 hull materials)
        all_mats = getattr(self.data_loader, "hull_materials", {})
        hull_mats = [all_mats[mid] for mid in HULL_PIXEL_MATERIALS if mid in all_mats]
        swatch_h = scale_y(44)
        start_y = panel_y + scale_y(40)
        pad = 3

        for i, mat in enumerate(hull_mats):
            sy = start_y + i * (swatch_h + pad)
            is_selected = mat.id == getattr(self, "_recolor_material_id", "")
            bg = (50, 65, 100) if is_selected else (20, 25, 40)
            pygame.draw.rect(screen, bg, (panel_x + 4, sy, panel_w - 8, swatch_h), border_radius=3)
            if is_selected:
                pygame.draw.rect(
                    screen,
                    (255, 200, 80),
                    (panel_x + 4, sy, panel_w - 8, swatch_h),
                    2,
                    border_radius=3,
                )
            # Color swatch
            swatch_w = scale_x(28)
            pygame.draw.rect(
                screen,
                mat.color_primary,
                (panel_x + 10, sy + 6, swatch_w, swatch_h - 12),
                border_radius=2,
            )
            # Name
            text_x = panel_x + 14 + swatch_w
            name = self.tiny_font.render(mat.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name, (text_x, sy + 6))
            info = self.label_font.render(
                f"W:{mat.weight_per_pixel:.2f}", True, Colors.TEXT_SECONDARY
            )
            screen.blit(info, (text_x, sy + 22))

        # Locked pixel hint
        lock_y = start_y + len(hull_mats) * (swatch_h + pad) + scale_y(10)
        lock_hint = self.label_font.render("Functional pixels (glass,", True, (120, 80, 80))
        screen.blit(lock_hint, (panel_x + 8, lock_y))
        lock_hint2 = self.label_font.render("exhaust, etc.) are locked.", True, (120, 80, 80))
        screen.blit(lock_hint2, (panel_x + 8, lock_y + scale_y(12)))

        # Exit hint
        exit_y = lock_y + scale_y(30)
        exit_hint = self.label_font.render("Press [C] to exit recolor", True, (100, 110, 140))
        screen.blit(exit_hint, (panel_x + 8, exit_y))

    def _render_module_tooltip(self, screen: pygame.Surface) -> None:
        """Render a tooltip for the placed module under the cursor."""
        mouse_pos = pygame.mouse.get_pos()
        grid_pos = self._screen_to_grid(mouse_pos[0], mouse_pos[1])
        if not grid_pos:
            return
        catalog = self._get_module_catalog()
        gx, gy = grid_pos
        for placed in self.build.modules:
            if placed.module_id not in catalog:
                continue
            pixels = resolve_placed_module(placed, catalog)
            for p in pixels:
                if p.x == gx and p.y == gy:
                    module = catalog[placed.module_id]
                    # Draw tooltip near cursor
                    tx = mouse_pos[0] + 16
                    ty = mouse_pos[1] - 10
                    # Keep on screen
                    tip_w = scale_x(180)
                    tip_h = scale_y(80)
                    if tx + tip_w > WINDOW_WIDTH:
                        tx = mouse_pos[0] - tip_w - 8
                    if ty + tip_h > WINDOW_HEIGHT:
                        ty = mouse_pos[1] - tip_h

                    draw_panel(screen, (tx, ty, tip_w, tip_h), alpha=230)
                    # Module name
                    name_surf = self.tiny_font.render(module.name, True, Colors.TEXT_HIGHLIGHT)
                    screen.blit(name_surf, (tx + 6, ty + 4))
                    # Manufacturer
                    mfg_name = module.manufacturer.replace("_", " ").title()
                    mfg_surf = self.label_font.render(mfg_name, True, Colors.TEXT_SECONDARY)
                    screen.blit(mfg_surf, (tx + 6, ty + 20))
                    # Category and weight
                    cat_surf = self.label_font.render(
                        f"{module.category.upper()}  W: {module.weight:.1f}  Cost: {module.instantiation_cost:,}",
                        True,
                        Colors.TEXT_SECONDARY,
                    )
                    screen.blit(cat_surf, (tx + 6, ty + 34))
                    # Key stats from provides
                    provides_parts = []
                    for key, val in module.provides.items():
                        if key == "slot_type":
                            provides_parts.append(f"Slot: {val}")
                        elif isinstance(val, (int, float)) and val > 0:
                            provides_parts.append(f"{key}: {val}")
                    if provides_parts:
                        prov_text = "  ".join(provides_parts[:4])
                        prov_surf = self.label_font.render(prov_text, True, (120, 180, 140))
                        screen.blit(prov_surf, (tx + 6, ty + 48))
                    return  # Only one tooltip at a time

    # ------------------------------------------------------------------
    # Physics Overlays (Phase 6)
    # ------------------------------------------------------------------

    def _render_integrity_overlay(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        cell: int,
        cw: int,
        ch: int,
    ) -> None:
        """Render structural integrity heat map over ship pixels."""
        from spacegame.models.ship_module import resolve_all_pixels
        from spacegame.models.ship_physics import compute_structural_integrity

        catalog = self._get_module_catalog()
        all_pixels = resolve_all_pixels(self.build, catalog)
        coords = [(p.x, p.y) for p in all_pixels]

        if not coords:
            return

        # Recompute if cache invalidated
        if self._cached_integrity is None:
            self._cached_integrity = compute_structural_integrity(coords)

        for (x, y), score in self._cached_integrity.items():
            if score <= 0:
                continue  # Green/safe pixels don't need overlay
            px = ox + x * cell
            py = oy + y * cell
            if score >= 0.7:
                color = (255, 50, 50, 100)  # Red — critical
            elif score >= 0.3:
                color = (255, 200, 50, 80)  # Yellow — moderate
            else:
                color = (100, 255, 100, 50)  # Green — mild
            overlay = pygame.Surface((cell - 1, cell - 1), pygame.SRCALPHA)
            overlay.fill(color)
            screen.blit(overlay, (px + 1, py + 1))

    def _render_com_overlay(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        cell: int,
    ) -> None:
        """Render center of mass crosshair on the grid."""
        from spacegame.models.ship_physics import compute_center_of_mass

        catalog = self._get_module_catalog()
        materials = getattr(self.data_loader, "hull_materials", {})
        com_x, com_y, offset_pct, rating = compute_center_of_mass(
            self.build,
            materials,
            catalog,
        )

        if offset_pct == 0.0 and not self.build.pixels and not self.build.modules:
            return

        # Draw crosshair at CoM position
        cx = int(ox + com_x * cell + cell // 2)
        cy = int(oy + com_y * cell + cell // 2)

        # Color based on balance rating
        from spacegame.models.ship_physics import BalanceRating

        if rating == BalanceRating.BALANCED:
            color = (80, 255, 80)
        elif rating == BalanceRating.OFF_BALANCE:
            color = (255, 200, 50)
        else:
            color = (255, 60, 60)

        # Crosshair lines
        arm_len = max(8, cell * 2)
        pygame.draw.line(screen, color, (cx - arm_len, cy), (cx + arm_len, cy), 2)
        pygame.draw.line(screen, color, (cx, cy - arm_len), (cx, cy + arm_len), 2)
        # Center dot
        pygame.draw.circle(screen, color, (cx, cy), 3)

        # Label
        label = self.label_font.render(f"CoM {offset_pct:.0f}%", True, color)
        screen.blit(label, (cx + arm_len + 4, cy - 6))

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
            (
                "Cost",
                f"{stats.total_cost:,} CR",
                Colors.GOLD if hasattr(Colors, "GOLD") else (200, 180, 80),
            ),
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
            screen,
            x_start,
            y,
            bar_w,
            BAR_H,
            stats.weight_current,
            stats.weight_max,
            weight_color,
            label="Weight",
            font=self.label_font,
        )
        # Weight label
        wt_label = self.label_font.render(
            f"{stats.weight_label} ({stats.weight_ratio:.0%})",
            True,
            weight_color,
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
                True,
                id_color,
            )
            screen.blit(id_text, (x_start, y))

        # Tool bar (right side of stats panel) — prominent labeled buttons
        tool_x = WINDOW_WIDTH - scale_x(350)
        tool_y = STATS_PANEL_Y + 6
        btn_w = scale_x(52)
        btn_h = scale_y(24)
        btn_gap = 3

        if self._builder_mode == "hull":
            # Hull mode tools
            tools = [
                ("stamp", "S", "Stamp"),
                ("pencil", "P", "Pencil"),
                ("brush", "M", "Brush"),
                ("fill", "F", "Fill"),
                ("eraser", "E", "Erase"),
            ]
            for i, (tool_id, key, label) in enumerate(tools):
                bx = tool_x + i * (btn_w + btn_gap)
                is_active = self._active_tool == tool_id
                bg = (50, 80, 140) if is_active else (25, 30, 50)
                border = Colors.TEXT_HIGHLIGHT if is_active else (50, 55, 70)
                pygame.draw.rect(screen, bg, (bx, tool_y, btn_w, btn_h), border_radius=3)
                pygame.draw.rect(screen, border, (bx, tool_y, btn_w, btn_h), 1, border_radius=3)
                t = self.label_font.render(
                    f"[{key}] {label}",
                    True,
                    Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY,
                )
                screen.blit(t, (bx + btn_w // 2 - t.get_width() // 2, tool_y + 5))

            # Mirror button
            mirror_x = tool_x + len(tools) * (btn_w + btn_gap) + btn_gap
            mirror_bg = (40, 100, 60) if self._mirror_mode else (25, 30, 50)
            mirror_border = Colors.GREEN if self._mirror_mode else (50, 55, 70)
            pygame.draw.rect(screen, mirror_bg, (mirror_x, tool_y, btn_w, btn_h), border_radius=3)
            pygame.draw.rect(
                screen, mirror_border, (mirror_x, tool_y, btn_w, btn_h), 1, border_radius=3
            )
            mir_label = self.label_font.render(
                "[X] Mirror",
                True,
                Colors.GREEN if self._mirror_mode else Colors.TEXT_SECONDARY,
            )
            screen.blit(mir_label, (mirror_x + btn_w // 2 - mir_label.get_width() // 2, tool_y + 5))

        # Row 2: Undo/Redo + rotation + zoom (both modes)
        tool_y += btn_h + 4
        undo_redo_x = tool_x

        # Undo button
        has_undo = len(self._undo_stack) > 0
        undo_bg = (40, 50, 80) if has_undo else (20, 22, 30)
        pygame.draw.rect(screen, undo_bg, (undo_redo_x, tool_y, btn_w, btn_h), border_radius=3)
        undo_label = self.label_font.render(
            f"Undo ({len(self._undo_stack)})",
            True,
            Colors.TEXT_PRIMARY if has_undo else (50, 55, 65),
        )
        screen.blit(undo_label, (undo_redo_x + 3, tool_y + 5))

        # Redo button
        redo_x = undo_redo_x + btn_w + btn_gap
        has_redo = len(self._redo_stack) > 0
        redo_bg = (40, 50, 80) if has_redo else (20, 22, 30)
        pygame.draw.rect(screen, redo_bg, (redo_x, tool_y, btn_w, btn_h), border_radius=3)
        redo_label = self.label_font.render(
            f"Redo ({len(self._redo_stack)})",
            True,
            Colors.TEXT_PRIMARY if has_redo else (50, 55, 65),
        )
        screen.blit(redo_label, (redo_x + 3, tool_y + 5))

        # Rotation/flip indicator
        rot_x = redo_x + btn_w + btn_gap * 3
        if self._builder_mode == "slot":
            rot_text = f"[R] {self._module_rotation * 90}\u00b0  [Q] Flip: {'Y' if self._module_flipped else 'N'}"
        else:
            rot_text = f"[R] {self._shape_rotation * 90}\u00b0  [Q] Flip: {'Y' if self._shape_flipped else 'N'}"
        rt = self.label_font.render(rot_text, True, Colors.TEXT_SECONDARY)
        screen.blit(rt, (rot_x, tool_y + 5))

        # Zoom indicator
        zoom_pct = int(self._zoom_level * 100)
        zoom_text = self.label_font.render(f"Zoom: {zoom_pct}%", True, Colors.TEXT_SECONDARY)
        screen.blit(zoom_text, (WINDOW_WIDTH - zoom_text.get_width() - scale_x(20), tool_y + 5))

    def _load_preset(self) -> None:
        """Load the current ship type's preset into the builder."""
        from spacegame.models.ship_presets import generate_preset_from_ship_type

        self._push_undo()
        self.build = generate_preset_from_ship_type(self.player.ship.ship_type)
        self.grid_manager = ShipGridManager(self.build.weight_class)
        self._modified = True
        self._recompute_stats()
        self._validation_warnings = [f"Loaded {self.player.ship.ship_type.name} preset"]
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
            ("  Right-click: Erase pixel / Remove module", Colors.TEXT_PRIMARY),
            ("  [R] Rotate shape 90°    [Q] Flip horizontally", Colors.TEXT_PRIMARY),
            ("  [X] Toggle Mirror Mode (symmetrical building)", Colors.TEXT_PRIMARY),
            ("  Ctrl+Z: Undo    Ctrl+Y: Redo", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("TOOLS", Colors.TEXT_HIGHLIGHT),
            ("  [S] Stamp    [P] Pencil    [M] Material Brush", Colors.TEXT_PRIMARY),
            ("  [F] Flood Fill    [E] Eraser", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("EQUIPMENT", Colors.TEXT_HIGHLIGHT),
            (
                "  Install weapons and shields via the Loadout tab in the Shipyard",
                Colors.TEXT_PRIMARY,
            ),
            ("  Place slot modules in SLOTS mode to define equipment points", Colors.TEXT_PRIMARY),
            ("", Colors.TEXT_PRIMARY),
            ("WEIGHT & IDENTITY", Colors.TEXT_HIGHLIGHT),
            ("  Hull materials are heavy → Juggernaut (armor, durability)", Colors.TEXT_PRIMARY),
            ("  Shield materials are medium → Sentinel (regen, sustain)", Colors.TEXT_PRIMARY),
            ("  Light materials are fast → Ghost (evasion, speed)", Colors.TEXT_PRIMARY),
            (
                "  Your ship's identity activates when 35%+ of pixels are one type",
                Colors.TEXT_PRIMARY,
            ),
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
            (
                f"+{shield_delta} Shield",
                (80, 180, 255) if shield_delta > 0 else Colors.TEXT_SECONDARY,
            ),
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

    def _render_import_modal(self, screen: pygame.Surface) -> None:
        """Render the import build code modal overlay."""
        # Dim background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # Modal panel
        modal_w = scale_x(500)
        modal_h = scale_y(220)
        mx = WINDOW_WIDTH // 2 - modal_w // 2
        my = WINDOW_HEIGHT // 2 - modal_h // 2
        draw_panel(screen, (mx, my, modal_w, modal_h), alpha=240)

        # Title
        title = self.small_font.render("Import Build Code", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (mx + 15, my + 10))

        # Instructions
        inst = self.label_font.render(
            "Paste a build code below (Ctrl+V), then press Enter", True, Colors.TEXT_SECONDARY
        )
        screen.blit(inst, (mx + 15, my + 32))

        # Text input area
        input_y = my + scale_y(55)
        input_h = scale_y(30)
        input_rect = pygame.Rect(mx + 10, input_y, modal_w - 20, input_h)
        pygame.draw.rect(screen, (15, 18, 30), input_rect, border_radius=3)
        pygame.draw.rect(screen, Colors.UI_BORDER, input_rect, 1, border_radius=3)

        # Display text (truncated if too long)
        display_text = self._import_text
        if len(display_text) > 60:
            display_text = display_text[:57] + "..."
        if display_text:
            text_surf = self.label_font.render(display_text, True, Colors.TEXT_PRIMARY)
        else:
            text_surf = self.label_font.render("Paste code here...", True, (60, 65, 80))
        screen.blit(text_surf, (mx + 15, input_y + 8))

        # Blinking cursor
        import time

        if int(time.time() * 2) % 2 == 0:
            cursor_x = mx + 15 + (self.label_font.size(display_text)[0] if display_text else 0)
            pygame.draw.line(
                screen,
                Colors.TEXT_PRIMARY,
                (cursor_x, input_y + 6),
                (cursor_x, input_y + input_h - 6),
            )

        # Error message
        if self._import_error:
            err_surf = self.label_font.render(self._import_error, True, (220, 60, 60))
            screen.blit(err_surf, (mx + 15, input_y + input_h + 8))

        # Missing blueprints list
        if self._import_missing_blueprints:
            bp_y = input_y + input_h + scale_y(28)
            header = self.label_font.render("Missing Blueprints:", True, (200, 160, 60))
            screen.blit(header, (mx + 15, bp_y))
            bp_y += scale_y(14)
            for bp in self._import_missing_blueprints[:5]:
                method = bp.get("unlock_method", "").replace("_", " ").title()
                line = f"\u2717 {bp['name']} ({bp['category']}) - {method}"
                if bp.get("unlock_source"):
                    line += f": {bp['unlock_source'].replace('_', ' ').title()}"
                bp_surf = self.label_font.render(line, True, (180, 100, 100))
                screen.blit(bp_surf, (mx + 20, bp_y))
                bp_y += scale_y(13)
            if len(self._import_missing_blueprints) > 5:
                more = self.label_font.render(
                    f"... and {len(self._import_missing_blueprints) - 5} more",
                    True,
                    (140, 100, 100),
                )
                screen.blit(more, (mx + 20, bp_y))

        # Buttons hint
        hint_y = my + modal_h - scale_y(22)
        hint = self.label_font.render(
            "[Enter] Import    [Esc] Cancel    [Ctrl+V] Paste", True, (80, 90, 110)
        )
        screen.blit(hint, (mx + 15, hint_y))

    def _render_confirm_animation(self, screen: pygame.Surface) -> None:
        """Render the build confirmation celebration (Phase E)."""
        from spacegame.engine.easing import ease_out_back, ease_out_quad

        t = self._confirm_anim_timer / 1.2  # 1→0 as animation plays
        progress = 1.0 - t  # 0→1 as animation advances

        # Sprite scale: ease_out_back gives a satisfying pop-in overshoot
        scale_t = ease_out_back(min(progress * 2.0, 1.0))  # Finish scaling in first half
        alpha = int(255 * ease_out_quad(min(progress * 3.0, 1.0)))  # Fade in fast

        # Flash overlay near end
        if progress > 0.8:
            flash_t = ease_out_quad((progress - 0.8) / 0.2)
            flash_alpha = int(200 * flash_t)
            flash = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            screen.blit(flash, (0, 0))

        # Ship sprite centered large with scale pop
        if self._confirm_anim_surface:
            sprite = self._confirm_anim_surface
            # Scale from 80% to 100% with overshoot
            draw_scale = 0.8 + 0.2 * scale_t
            if draw_scale != 1.0:
                sw = max(1, int(sprite.get_width() * draw_scale))
                sh = max(1, int(sprite.get_height() * draw_scale))
                scaled = pygame.transform.scale(sprite, (sw, sh))
            else:
                scaled = sprite
            scaled.set_alpha(min(255, alpha))
            rect = scaled.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            screen.blit(scaled, rect)

            # "BUILD CONFIRMED" text
            text = self.header_font.render("BUILD CONFIRMED", True, (255, 220, 100))
            text.set_alpha(min(255, alpha))
            text_rect = text.get_rect(
                center=(
                    WINDOW_WIDTH // 2,
                    WINDOW_HEIGHT // 2 + scaled.get_height() // 2 + scale_y(30),
                )
            )
            screen.blit(text, text_rect)

        # Darken edges — fade out as animation progresses
        dim_alpha = int(120 * (1.0 - ease_out_quad(progress)))
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, dim_alpha))
        screen.blit(dim, (0, 0))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
