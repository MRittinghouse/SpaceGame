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
from spacegame.models.energy_economy import compute_energy_economy
from spacegame.models.player import Player
from spacegame.models.ship_build import (
    FRAME_SLOT_LIMITS,
    ComputedShipStats,
    FrameRequirements,
    HullMaterial,
    HullShape,
    PlacedPixel,
    PlacedSlot,
    ShipBuild,
    ShipGridManager,
    ShipStatsComputer,
)
from spacegame.models.ship_module import (
    ShipModule,
    resolve_all_pixels,
)
from spacegame.models.slot_definition import _SIZE_DISPLAY, _TYPE_DISPLAY, SlotDefinition
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

# Hull-only materials for the simplified hull pixel palette
HULL_PIXEL_MATERIALS = ("light_alloy", "standard_plate", "heavy_armor", "stealth_composite")

# Single-letter labels for slot types rendered on grid cells
_SLOT_TYPE_SHORT: dict[str, str] = {
    "cockpit": "K",
    "weapon": "W",
    "defense": "D",
    "engine": "E",
    "utility": "U",
    "fuel": "F",
    "cargo": "C",
    "crew_quarters": "Q",
    "reactor": "R",
}

# Ordered slot types for palette grouping
_SLOT_TYPE_ORDER: list[str] = [
    "cockpit",
    "weapon",
    "defense",
    "engine",
    "utility",
    "fuel",
    "cargo",
    "crew_quarters",
    "reactor",
]

# PT-N: helper for the tutorial stat preview — pulls colors from the
# PALETTE_ROLES system so colorblind profiles remap automatically.
def _palette_role_color(role: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        from spacegame.engine.material_palette import get_role

        return get_role(role)
    except (KeyError, ImportError):
        return fallback


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


# Themed palette for the ship builder view.
# Keys are semantic roles. Values live here (not inline) so colorblind
# profile work in Sprint 4 can remap each role by updating this table.
# Migration target for Sprint 4: resolve entries through PALETTE_ROLES
# via the Colors-wrapper design chosen in Sprint 1.
_BUILDER_COLORS: dict[str, tuple[int, int, int]] = {
    # --- Validation feedback ---
    "valid_place": (100, 255, 100),
    "ghost_fallback": (100, 200, 100),
    "invalid_place": (255, 60, 60),
    "invalid_preview": (200, 60, 60),
    "warn_size": (220, 180, 80),
    "warn_weight_hard": (200, 80, 80),
    "warn_slot_cap": (180, 140, 80),
    "warn_tip_text": (220, 180, 100),
    "warn_tip_border": (120, 100, 60),
    "warn_at_cap": (200, 180, 60),
    "tier_ok": (120, 220, 180),
    "tier_warn": (220, 140, 40),
    "weight_green": (80, 200, 80),
    "weight_over": (220, 60, 40),
    "weight_safe": (80, 255, 80),
    "import_error": (220, 60, 60),
    "import_warn_header": (200, 160, 60),
    "import_warn_line": (180, 100, 100),
    "import_warn_dim": (140, 100, 100),
    "lock_hint": (120, 80, 80),

    # --- UI state backgrounds ---
    "cell_selected_cool": (40, 50, 80),
    "cell_selected": (45, 60, 100),
    "cell_selected_strong": (45, 65, 100),
    "cell_selected_bright": (50, 65, 100),
    "tab_active": (40, 80, 140),
    "tab_header_active": (50, 70, 110),
    "toolbar_active": (50, 80, 140),
    "cell_alt": (25, 30, 45),
    "tab_inactive": (30, 35, 50),
    "toolbar_enabled": (30, 35, 55),
    "toolbar_disabled": (20, 22, 30),
    "cell_dim": (15, 15, 22),
    "cell_section_active": (40, 70, 50),
    "input_bg_dim": (15, 18, 30),
    "panel_bg_soft": (40, 50, 70),
    "panel_divider": (50, 60, 80),
    "panel_dim_button": (40, 48, 65),

    # --- Text / border states ---
    "text_locked": (70, 70, 80),
    "text_locked_dim": (50, 50, 60),
    "text_disabled_swatch": (60, 60, 60),
    "text_placeholder": (60, 65, 80),
    "text_toolbar_disabled": (50, 55, 65),
    "text_softer_white": (200, 200, 200),
    "text_category_fallback": (150, 150, 150),
    "border_tab_inactive": (60, 70, 90),
    "border_tab_subtle": (50, 55, 70),
    "border_toolbar_enabled": (60, 65, 80),
    "border_toolbar_disabled": (40, 42, 50),

    # --- Hint / label grays ---
    "label_mute_cool": (80, 90, 110),
    "label_mute_cool_soft": (80, 90, 120),
    "label_mute_warm": (100, 110, 130),
    "label_mute_warm_soft": (100, 110, 140),
    "label_trim_warm": (120, 90, 60),

    # --- Recolor UI ---
    "recolor_accent": (255, 200, 80),

    # --- Build confirm ---
    "build_confirm": (255, 220, 100),

    # --- Stat signatures (also used as archetype colors) ---
    "stat_shield": (80, 180, 255),
    "stat_armor": (200, 150, 50),
    "stat_evasion": (160, 100, 200),
    "stat_gold_fallback": (200, 180, 80),
    "stat_tier_ring": (180, 160, 80),

    # --- Tier letter grades ---
    "grade_s": (255, 215, 80),
    "grade_a": (80, 220, 80),
    "grade_b": (80, 180, 255),
    "grade_c": (220, 200, 60),
    "grade_d": (220, 140, 40),
    "grade_f": (200, 60, 60),

    # --- Module category signatures ---
    "cat_cockpit": (100, 180, 255),
    "cat_engine": (255, 180, 80),
    "cat_weapon": (255, 80, 80),
    "cat_shield": (80, 220, 255),
    "cat_cargo": (255, 220, 80),
    "cat_utility": (80, 255, 120),
    "cat_structural": (160, 160, 180),
    "cat_crew": (120, 200, 120),
    "cat_reactor": (180, 100, 240),

    # --- Material / swatch fallbacks ---
    "material_fallback": (128, 128, 128),
    "material_fallback_dark": (100, 100, 100),
    "material_fallback_light": (120, 120, 130),
    "swatch_fallback_warm": (100, 70, 70),

    # --- Grid background ---
    "grid_bg": (8, 10, 20),
}


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
        self._bg_dim.fill(Colors.BLACK)
        self._bg_dim.set_alpha(160)
        self.particles = ParticlePool(100)

        # Tutorial mode (set externally by game.py before on_enter)
        self._tutorial_mode: bool = False
        self._tutorial_return_state: GameState = GameState.SHIPYARD
        self._tutorial_step: int = 0  # 0=cockpit, 1=engine, 2=reactor, 3=cargo
        self._tutorial_narration_font = get_font("narration", FONT_BODY)

        # PT-N: tutorial narration modal + objective strip state
        from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

        self._tutorial_narration_modal: Optional[TutorialNarrationModal] = None
        # Phases for which a narration modal has been shown this session.
        # Persisted to dialogue_flags as tutorial_phase_*_narration_seen.
        self._tutorial_last_phase_shown: str = ""

        # PT-N stat preview deltas: snapshot of last stats + per-stat
        # fade timers. When the player takes an action and a stat changes,
        # we flash "+N" or "-N" next to the stat for ~1.8s then clear.
        # Teaches action → outcome viscerally ("I painted a pixel and my
        # hull went up by 2.5").
        self._tutorial_stat_snapshot: dict[str, float] = {}
        self._tutorial_stat_deltas: dict[str, tuple[float, float]] = {}  # stat → (delta, timer)

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
        self._frame_reqs: Optional[FrameRequirements] = None

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
        self._slot_variant_index: dict[str, int] = {}  # variant_group -> active index
        self._slot_variant_lists: dict[str, list[str]] = {}  # variant_group -> [def IDs]

        # PT-007 playtest response: rotation-tip discoverability flag.
        # Set to True once the player presses R; the tutorial narration
        # stops surfacing the "Press R to rotate" hint after that.
        self._shown_rotation_tip: bool = False

        # EQUIP mode moved to Loadout tab (Phase S4)

        # Visual feedback (Phase 10)
        self._placement_flash_timer: float = 0.0
        self._placement_flash_pos: tuple[int, int] = (0, 0)
        self._feedback_messages: list[dict] = []

        # Physics overlay toggles (Phase 6 + BP4)
        self._show_integrity_overlay: bool = False
        self._show_com_overlay: bool = False
        self._show_exposure_overlay: bool = False
        self._cached_integrity: Optional[dict] = None
        self._cached_exposure: Optional[dict] = None

        # Live ship preview (BP1)
        self._preview_surface: Optional[pygame.Surface] = None
        self._preview_dirty: bool = True  # Rebuild on next render

        # Ship naming dialog (BP2)
        self._naming_active: bool = False
        self._naming_text: str = ""
        self._naming_cursor_timer: float = 0.0
        # PT-012: rename-only vs. confirm-then-name paths share the dialog
        # but have different exit behavior. See _handle_naming_event.
        self._rename_only: bool = False

        # UI elements
        self.confirm_button: Optional[pygame_gui.elements.UIButton] = None
        self.clear_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.rename_button: Optional[pygame_gui.elements.UIButton] = None

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

        if self._tutorial_mode:
            # Tutorial: fresh empty tiny build
            self.build = ShipBuild(weight_class="tiny")
            self._tutorial_step = 0
            logger.info("Ship Builder: tutorial mode active")
        elif self.player.ship.build:
            self.build = ShipBuild.from_dict(self.player.ship.build.to_dict())
        else:
            # Generate a preset from the current ship type
            from spacegame.models.ship_presets import generate_preset_from_ship_type

            self.build = generate_preset_from_ship_type(self.player.ship.ship_type)

        self.grid_manager = ShipGridManager(self.build.weight_class)
        self._modified = False
        # Resolve per-frame requirements from the player's ship type
        self._frame_reqs = FrameRequirements.from_ship_type(self.player.ship.ship_type)
        # Ensure build carries the ship_type_id for future sessions
        if not self.build.ship_type_id:
            self.build.ship_type_id = self.player.ship.ship_type.id
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
        # PT-006: in tutorial mode, the BACK button routes to the shipyard —
        # which does not exist pre-tutorial and confuses new players hunting
        # for the exit. Hide it during tutorial builds so CONFIRM BUILD is
        # the only outgoing affordance.
        if self._tutorial_mode:
            self.back_button.hide()
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
        # PT-012: explicit RENAME button. Confirmation no longer opens the
        # naming dialog; players who want to rename their ship open it here.
        # Hidden in tutorial mode — rename is not a tutorial concern.
        self.rename_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(710),
                btn_y,
                scale_x(110),
                btn_h,
            ),
            text="RENAME",
            manager=self.ui_manager,
        )
        if self._tutorial_mode:
            self.rename_button.hide()
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
            self.rename_button,
        ]:
            if btn:
                btn.kill()
        self.confirm_button = None
        self.clear_button = None
        self.back_button = None
        self.rename_button = None

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        # Block input during confirmation animation
        if self._confirm_anim_timer > 0:
            return

        # PT-N: tutorial narration modal intercepts all input while visible
        if self._tutorial_narration_modal is not None and not self._tutorial_narration_modal.dismissed:
            if self._tutorial_narration_modal.handle_event(event):
                return

        # Ship naming dialog intercepts all input
        if self._naming_active:
            self._handle_naming_event(event)
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
                self.build.placed_slots.clear()
                self._selected_placed_module_idx = None
                self._selected_slot_def_id = None
                self._modified = True
                self._recompute_stats()
                return
            if self.rename_button is not None and event.ui_element == self.rename_button:
                # PT-012: open naming dialog on demand. Player names their
                # ship at game start; this is the re-rename path.
                self._naming_active = True
                self._naming_text = (
                    self.player.ship_name or self.player.ship.ship_type.name
                )
                self._naming_cursor_timer = 0.0
                self._rename_only = True
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
                # Cycle through slot → hull → slot
                # PT-N: block keyboard cycling during Phase A so the player
                # follows the slots-first order. The click-handler mode lock
                # was previously the only guard — Tab would have bypassed it.
                if self._tutorial_mode and self._tutorial_phase() == "slots":
                    try:
                        get_audio_manager().play_sfx("ui_deny")
                    except Exception:
                        pass
                    return
                cycle = {"slot": "hull", "hull": "slot"}
                self._builder_mode = cycle.get(self._builder_mode, "slot")
                try:
                    get_audio_manager().play_sfx("ui_click")
                except Exception:
                    pass
            elif event.key == pygame.K_r:
                if self._builder_mode == "slot":
                    self._module_rotation = (self._module_rotation + 1) % 4
                    # Player discovered R — mark the rotation tip satisfied.
                    self._shown_rotation_tip = True
                    try:
                        get_audio_manager().play_sfx("build_slot_rotate")
                    except Exception:
                        pass
                else:
                    self._shape_rotation = (self._shape_rotation + 1) % 4
                    self._shown_rotation_tip = True
            elif event.key == pygame.K_q:
                if self._builder_mode == "slot":
                    self._module_flipped = not self._module_flipped
                else:
                    self._shape_flipped = not self._shape_flipped
            elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                pass  # Legacy module deletion removed
            elif event.key == pygame.K_ESCAPE:
                # PT-N: block Escape in tutorial mode so the player can only
                # exit via CONFIRM (which is itself gated on phase complete).
                # Without this guard the player could press Escape mid-tutorial,
                # land in the shipyard with a half-built ship, back out to
                # station hub, and sidestep the entire guided flow.
                if self._tutorial_mode:
                    try:
                        get_audio_manager().play_sfx("ui_deny")
                    except Exception:
                        pass
                    return
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
            elif event.key == pygame.K_v:
                if self._builder_mode == "slot":
                    self._cycle_slot_variant()
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

        # --- Tool bar click (bottom-right stats panel area) ---
        _tool_x = WINDOW_WIDTH - scale_x(420)
        _tool_y = STATS_PANEL_Y + 6
        _btn_w = scale_x(65)
        _btn_h = scale_y(28)
        _btn_gap = scale_x(4)

        if my >= _tool_y and my < _tool_y + _btn_h and mx >= _tool_x:
            # Row 1: Hull mode tools
            if self._builder_mode == "hull":
                tools = ["stamp", "pencil", "brush", "fill", "eraser", "_mirror"]
                for i, tool_id in enumerate(tools):
                    bx = _tool_x + i * (_btn_w + _btn_gap)
                    if bx <= mx < bx + _btn_w:
                        if tool_id == "_mirror":
                            self._mirror_mode = not self._mirror_mode
                        else:
                            self._active_tool = tool_id
                        try:
                            get_audio_manager().play_sfx("ui_click")
                        except Exception:
                            pass
                        return

        _row2_y = _tool_y + _btn_h + scale_y(4)
        if my >= _row2_y and my < _row2_y + _btn_h and mx >= _tool_x:
            # Row 2: Undo, Redo, Rotate, Flip, Zoom
            for i, action in enumerate(["undo", "redo", "rotate", "flip", "zoom"]):
                bx = _tool_x + i * (_btn_w + _btn_gap)
                if bx <= mx < bx + _btn_w:
                    if action == "undo" and self._undo_stack:
                        self._undo()
                    elif action == "redo" and self._redo_stack:
                        self._redo()
                    elif action == "rotate":
                        if self._builder_mode == "slot":
                            self._module_rotation = (self._module_rotation + 1) % 4
                        else:
                            self._shape_rotation = (self._shape_rotation + 1) % 4
                    elif action == "flip":
                        if self._builder_mode == "slot":
                            self._module_flipped = not self._module_flipped
                        else:
                            self._shape_flipped = not self._shape_flipped
                    try:
                        get_audio_manager().play_sfx("ui_click")
                    except Exception:
                        pass
                    return

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
                    # PT-N: lock HULL mode during tutorial Phase A so the
                    # player follows the slots-first order the narration
                    # describes. Phase B unlocks both modes (player can flip
                    # back to SLOT to tweak placement).
                    if (
                        self._tutorial_mode
                        and mode_id == "hull"
                        and self._tutorial_phase() == "slots"
                    ):
                        try:
                            get_audio_manager().play_sfx("ui_deny")
                        except Exception:
                            pass
                        return
                    self._builder_mode = mode_id
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
            if hasattr(self, "_exposure_toggle_rect") and self._exposure_toggle_rect.collidepoint(
                mx, my
            ):
                self._show_exposure_overlay = not self._show_exposure_overlay
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
        """Legacy module placement (removed)."""

    def _select_module_at(self, gx: int, gy: int) -> None:
        """Legacy module selection (removed)."""
        self._selected_placed_module_idx = None

    def _remove_module_at(self, gx: int, gy: int) -> None:
        """Legacy module removal (removed)."""

    def _recolor_pixel_at(self, gx: int, gy: int) -> None:
        """Legacy module pixel recoloring (removed)."""

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

        Faction-locked slots are hidden until the player reaches the
        required reputation tier. Within each type, variant groups are
        collapsed to show only the active variant. This keeps the palette clean.

        In tutorial mode, only the 4 tutorial parts are shown.

        Returns:
            List of (slot_type, [SlotDefinition, ...]) tuples ordered by
            _SLOT_TYPE_ORDER.
        """
        slot_defs = getattr(self.data_loader, "slot_definitions", {})

        # Tutorial mode: show only slot types matching parts the player
        # actually purchased, plus cockpit (always available).
        #
        # Bug fix (2026-04-24): the prior implementation crashed with
        # KeyError 'slot_def_id' because TUTORIAL_PARTS dicts use the key
        # 'part_id' (matching the inventory + flag wiring in the tutorial
        # shop). It also mismatched the flag name (shop sets
        # 'tutorial_bought_part_X', not 'tutorial_bought_X') AND filtered
        # slot_defs by part_id, which never matched any slot_def key.
        # Correct relationship: parts have slot_types; we filter slot_defs
        # by the slot_types of purchased parts.
        if self._tutorial_mode:
            from spacegame.constants.flags import tutorial_bought_part
            from spacegame.views.tutorial_shop_view import TUTORIAL_PARTS

            # Tutorial palette is intentionally minimal: ONE canonical
            # slot per slot_type the player has bought a part for. The
            # full multi-variant palette (Scout Pod / Observation Deck /
            # Armored Cabin / Command Bridge / etc.) is overwhelming for
            # a first-time player and not relevant to a scrapyard build.
            tutorial_slot_def_for_type: dict[str, str] = {
                "cockpit": "cockpit_scout_pod",
                "engine": "engine_small",
                "reactor": "reactor_small",
                "fuel": "fuel_small",
                "cargo": "cargo_small",
                "weapon": "weapon_small",
            }

            purchased_slot_types: set[str] = {"cockpit"}  # always available
            for p in TUTORIAL_PARTS:
                flag_key = tutorial_bought_part(p.part_id)
                if self.player.dialogue_flags.get(flag_key):
                    part = self.data_loader.ship_parts.get(p.part_id)
                    if part is not None:
                        purchased_slot_types.add(part.slot_type)
            # Fallback for first-render before any purchase flag is set:
            # show all tutorial slot types so the player can see the palette.
            if len(purchased_slot_types) == 1:
                for p in TUTORIAL_PARTS:
                    part = self.data_loader.ship_parts.get(p.part_id)
                    if part is not None:
                        purchased_slot_types.add(part.slot_type)

            result: list[tuple[str, list[SlotDefinition]]] = []
            for slot_type in _SLOT_TYPE_ORDER:
                if slot_type not in purchased_slot_types:
                    continue
                tutorial_def_id = tutorial_slot_def_for_type.get(slot_type)
                if tutorial_def_id is None:
                    continue
                sdef = slot_defs.get(tutorial_def_id)
                if sdef is None:
                    continue
                result.append((slot_type, [sdef]))
            return result

        # Build variant lists for cycling (group_id -> ordered list of def IDs)
        variant_map: dict[str, list[SlotDefinition]] = {}
        for sd in slot_defs.values():
            if sd.variant_group:
                variant_map.setdefault(sd.variant_group, []).append(sd)
        # Sort variant lists by ID to keep order stable (base first, then _v2, _v3)
        for vg_list in variant_map.values():
            vg_list.sort(key=lambda d: d.id)
        # Store for cycling
        self._slot_variant_lists = {
            vg: [sd.id for sd in vg_list] for vg, vg_list in variant_map.items()
        }

        groups: dict[str, list[SlotDefinition]] = {}
        seen_variant_groups: set[str] = set()
        for sd in slot_defs.values():
            # Hide faction-locked slots the player hasn't unlocked
            if sd.unlock_faction:
                if not self._is_slot_unlocked(sd):
                    continue
            # For variant groups, only show the active variant
            if sd.variant_group:
                if sd.variant_group in seen_variant_groups:
                    continue
                seen_variant_groups.add(sd.variant_group)
                # Pick the active variant for this group
                idx = self._slot_variant_index.get(sd.variant_group, 0)
                vg_ids = self._slot_variant_lists.get(sd.variant_group, [sd.id])
                idx = idx % len(vg_ids) if vg_ids else 0
                active_id = vg_ids[idx] if vg_ids else sd.id
                active_sd = slot_defs.get(active_id, sd)
                groups.setdefault(active_sd.slot_type, []).append(active_sd)
            else:
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

    def _is_slot_unlocked(self, sd: SlotDefinition) -> bool:
        """Check if a faction-locked slot definition is available to the player."""
        if not sd.unlock_faction:
            return True
        tier = self.player.get_reputation_tier(sd.unlock_faction)
        tier_order = {"hostile": 0, "unfriendly": 1, "neutral": 2, "friendly": 3, "allied": 4}
        required = tier_order.get(sd.unlock_rep_tier, 3)
        current = tier_order.get(tier.value, 2)
        return current >= required

    def _cycle_slot_variant(self) -> None:
        """Cycle the currently selected slot to the next shape variant.

        If the selected slot belongs to a variant group with multiple
        entries, advance the index and update the selection.
        """
        if not self._selected_slot_def_id:
            return
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        sdef = slot_defs.get(self._selected_slot_def_id)
        if not sdef or not sdef.variant_group:
            return
        vg = sdef.variant_group
        vg_ids = self._slot_variant_lists.get(vg, [])
        if len(vg_ids) <= 1:
            return
        idx = self._slot_variant_index.get(vg, 0)
        idx = (idx + 1) % len(vg_ids)
        self._slot_variant_index[vg] = idx
        self._selected_slot_def_id = vg_ids[idx]
        try:
            get_audio_manager().play_sfx("build_slot_variant")
        except Exception:
            pass

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
        """Get the frame limit for a slot type from per-frame requirements."""
        if self._frame_reqs is not None:
            return self._frame_reqs.get_max(slot_type)
        # Fallback for edge cases before on_enter
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
        # Apply rotation to get effective footprint
        fw, fh, _ = sdef.get_rotated(self._module_rotation)

        # Bounds check
        if gx < 0 or gy < 0 or gx + fw > cw or gy + fh > ch:
            return False, "Slot extends beyond canvas"

        # Overlap check with existing placed slots
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for ps in self.build.placed_slots:
            other = slot_defs.get(ps.slot_def_id)
            if not other:
                continue
            ow, oh, _ = other.get_rotated(ps.rotation)
            # AABB overlap test
            if gx < ps.x + ow and gx + fw > ps.x and gy < ps.y + oh and gy + fh > ps.y:
                return False, "Overlaps existing slot"

        # Minimum size constraint
        if self._frame_reqs is not None and not self._frame_reqs.is_slot_size_valid(
            sdef.slot_type, sdef.size
        ):
            min_sz = self._frame_reqs.get_min_size(sdef.slot_type)
            return (
                False,
                f"This frame requires {min_sz}+ {_TYPE_DISPLAY.get(sdef.slot_type, sdef.slot_type).lower()}s",
            )

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

        ok, reject_msg = self._validate_slot_placement(gx, gy, sdef)
        if ok:
            self._push_undo()
            self.build.placed_slots.append(
                PlacedSlot(slot_def_id=sdef.id, x=gx, y=gy, rotation=self._module_rotation)
            )
            self._modified = True
            self._recompute_stats()
            # Placement feedback — type-specific sound
            sfx_id = f"build_place_{sdef.slot_type}"
            try:
                get_audio_manager().play_sfx(sfx_id)
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
            # Color-coded rejection feedback
            if reject_msg:
                if "requires" in reject_msg:
                    msg_color = _BUILDER_COLORS["warn_size"]  # Amber — size constraint
                elif "weight" in reject_msg.lower() or "Exceeds" in reject_msg:
                    msg_color = _BUILDER_COLORS["warn_weight_hard"]  # Red — weight limit
                elif "limit" in reject_msg.lower():
                    msg_color = _BUILDER_COLORS["warn_slot_cap"]  # Orange — slot cap
                else:
                    msg_color = Colors.TEXT_SECONDARY  # Gray — overlap/bounds
                cell = self._get_cell_size()
                ox, oy = self._get_grid_origin()
                fx = float(ox + gx * cell + cell)
                fy = float(oy + gy * cell)
                self._feedback_messages.append(
                    {"text": reject_msg, "x": fx, "y": fy, "timer": 1.5, "color": msg_color}
                )

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
                    get_audio_manager().play_sfx("build_slot_remove")
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
        """Save current build state (pixels + placed_slots) to undo stack."""
        snapshot = {
            "pixels": [p.to_dict() for p in self.build.pixels],
            "placed_slots": [ps.to_dict() for ps in self.build.placed_slots],
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _restore_snapshot(self, snapshot: dict | list) -> None:
        """Restore build state from a snapshot.

        Handles both new dict format (pixels + placed_slots) and
        legacy list format (pixel dicts only).
        """
        if isinstance(snapshot, list):
            # Legacy format: plain list of pixel dicts
            self.build.pixels = [PlacedPixel.from_dict(d) for d in snapshot]
            self.build.placed_slots = []
        else:
            self.build.pixels = [PlacedPixel.from_dict(d) for d in snapshot["pixels"]]
            self.build.placed_slots = [
                PlacedSlot.from_dict(d) for d in snapshot.get("placed_slots", [])
            ]
        self._selected_placed_module_idx = None
        self._modified = True
        self._recompute_stats()

    def _make_current_snapshot(self) -> dict:
        """Create a snapshot of the current build state."""
        return {
            "pixels": [p.to_dict() for p in self.build.pixels],
            "placed_slots": [ps.to_dict() for ps in self.build.placed_slots],
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

    # ------------------------------------------------------------------
    # PT-N: Tutorial phase state machine
    # ------------------------------------------------------------------
    # Three-phase guided build:
    #   Phase A ("slots"):    place all 5 slots (4 purchased parts + cockpit)
    #   Phase B ("hull"):     paint at least MIN_TUTORIAL_HULL_PIXELS pixels
    #   Phase C ("complete"): CONFIRM enables; on confirm, parts auto-equip
    #                         and the build finalizes with tutorial pricing
    #                         (50% placement discount + hull at full cost;
    #                         parts already paid at the shop)

    _MIN_TUTORIAL_HULL_PIXELS: int = 20

    # Phase-transition narration content, Mechanic voice. Voice-checked:
    # no em-dashes, no "couldn't help but," no parallel-negation rhetoric.
    _TUTORIAL_NARRATION: dict[str, tuple[str, str]] = {
        "slots": (
            "Phase 1 of 3: Place the Slots",
            "Bay is yours. Frame is tiny, canvas is small, cheap to work with. "
            "Start with slots. Cockpit, engine, reactor, fuel, and your choice. "
            "Treat them like the skeleton. Drop them where you want them on the grid. "
            "Placement cost hits your wallet at CONFIRM, not while you are sliding "
            "them around. No penalty until you commit.",
        ),
        "hull": (
            "Phase 2 of 3: Paint the Hull",
            "Good layout. Now plating. Hull pixels give you armor, hull points, "
            "and shields, split across the materials you choose. Standard plate is "
            "the cheap default. Weight is the trade. Past eighty percent of your "
            "frame budget, your speed and evasion start dropping. Past ninety-five, "
            "you are overloaded. Shape matters too: narrow profiles evade more, "
            "balanced mass evades more. Paint what you need. Do not over-plate.",
        ),
        "complete": (
            "Phase 3 of 3: Confirm Build",
            "Hull is on. CONFIRM BUILD locks it in. I will mount the parts you "
            "bought into the slots you placed. One-time favor for the shakedown. "
            "Next time you do that yourself at any shipyard Loadout tab. Same idea: "
            "click a slot, pick a part. Swap whenever you want without redoing the "
            "hull. Hit CONFIRM when you are ready.",
        ),
    }

    def _tutorial_required_slot_types(self) -> set[str]:
        """Slot types the player needs to place in Phase A.

        Cockpit is always required. The other four are inferred from what
        the player bought in the tutorial shop via tutorial_bought_part_*
        flags, mapping the purchased part to its slot_type via parts_catalog.
        """
        from spacegame.constants.flags import extract_tutorial_bought_part_id

        required = {"cockpit"}  # always needed, self-fulfilling
        flags = getattr(self.player, "dialogue_flags", {})
        parts_catalog = getattr(self.data_loader, "ship_parts", {})
        for flag_name, enabled in flags.items():
            if not enabled:
                continue
            part_id = extract_tutorial_bought_part_id(flag_name)
            if part_id is None:
                continue
            part = parts_catalog.get(part_id)
            if part is not None:
                required.add(part.slot_type)
        return required

    def _is_tutorial_phase_a_complete(self) -> bool:
        """Phase A is complete when every required slot type has a placement."""
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        placed_types = set()
        for ps in self.build.placed_slots:
            sd = slot_defs.get(ps.slot_def_id)
            if sd:
                placed_types.add(sd.slot_type)
        return self._tutorial_required_slot_types().issubset(placed_types)

    def _is_tutorial_phase_b_complete(self) -> bool:
        """Phase B is complete when enough hull pixels are painted."""
        return len(self.build.pixels) >= self._MIN_TUTORIAL_HULL_PIXELS

    def _tutorial_phase(self) -> str:
        """Return the current tutorial phase name."""
        if not self._tutorial_mode:
            return "n/a"
        if not self._is_tutorial_phase_a_complete():
            return "slots"
        if not self._is_tutorial_phase_b_complete():
            return "hull"
        return "complete"

    def _tutorial_charge_amount(self) -> int:
        """Credits the player owes on CONFIRM in tutorial mode.

        Formula: hull (full cost) + slot placement (50% shakedown rate).
        Parts were paid at the shop; don't double-charge.
        """
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        materials = getattr(self.data_loader, "hull_materials", {})
        placement_total = 0
        for ps in self.build.placed_slots:
            sd = slot_defs.get(ps.slot_def_id)
            if sd:
                placement_total += sd.placement_cost
        hull_total = 0
        for px in self.build.pixels:
            mat = materials.get(px.material_id)
            if mat:
                hull_total += mat.cost_per_pixel
        return (placement_total // 2) + hull_total

    def _tutorial_maybe_fire_phase_narration(self) -> None:
        """If the player has entered a new phase, fire the Mechanic modal
        once. Uses dialogue_flags to ensure it fires at most once per phase
        per save (survives save/reload)."""
        if not self._tutorial_mode:
            return
        phase = self._tutorial_phase()
        if phase == "n/a" or phase == self._tutorial_last_phase_shown:
            return
        flag = f"tutorial_phase_{phase}_narration_seen"
        if self.player.dialogue_flags.get(flag, False):
            self._tutorial_last_phase_shown = phase
            return
        # First time entering this phase — fire the modal
        narration = self._TUTORIAL_NARRATION.get(phase)
        if narration is None:
            self._tutorial_last_phase_shown = phase
            return
        title, body = narration
        from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

        self._tutorial_narration_modal = TutorialNarrationModal(
            speaker="Mechanic",
            title=title,
            body=body,
            on_dismiss=lambda: self._tutorial_mark_phase_seen(phase),
        )
        self._tutorial_last_phase_shown = phase

    def _tutorial_mark_phase_seen(self, phase: str) -> None:
        """Persist that the player has seen this phase's narration so it
        does not re-fire on save/reload."""
        self.player.dialogue_flags[f"tutorial_phase_{phase}_narration_seen"] = True

    # Weight-threshold warning narration content, Mechanic voice.
    _TUTORIAL_WEIGHT_WARNINGS: dict[str, tuple[str, str]] = {
        "heavy": (
            "Over Weight Budget",
            "You are past eighty percent of your frame's weight cap. Evasion "
            "and speed are taking a hit from this point on. You can keep "
            "painting if you want the durability, but know what you are "
            "trading.",
        ),
        "overloaded": (
            "Overloaded",
            "Past ninety-five percent now. Evasion is tanking hard and speed "
            "is down with it. You can still fly, but you will be slow and "
            "easier to hit. Past one hundred percent the frame refuses more "
            "plating. Pull back if you want to be nimble.",
        ),
    }

    def _tutorial_maybe_fire_weight_warning(self) -> None:
        """If in tutorial mode and weight has crossed a threshold for the
        first time, fire the Mechanic warning modal. One-shot per threshold,
        persisted via dialogue_flags so it doesn't re-fire on save/reload
        or after the player drops below and climbs back up."""
        if not self._tutorial_mode:
            return
        if self._tutorial_narration_modal is not None:
            return  # Don't stack modals
        stats = self._computed_stats
        if stats is None or stats.weight_max <= 0:
            return
        ratio = stats.weight_current / stats.weight_max
        # Ordered so OVERLOADED fires before HEAVY if the player somehow
        # jumps multiple thresholds in one action — player should hear the
        # worse warning.
        threshold_checks = [
            ("overloaded", 0.95),
            ("heavy", 0.80),
        ]
        for key, threshold in threshold_checks:
            if ratio < threshold:
                continue
            flag = f"tutorial_weight_{key}_seen"
            if self.player.dialogue_flags.get(flag, False):
                continue
            content = self._TUTORIAL_WEIGHT_WARNINGS.get(key)
            if content is None:
                continue
            title, body = content
            from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

            self._tutorial_narration_modal = TutorialNarrationModal(
                speaker="Mechanic",
                title=title,
                body=body,
                on_dismiss=lambda k=key: self._tutorial_mark_weight_warning_seen(k),
            )
            # Mark flag immediately so the modal doesn't re-arm while visible
            self.player.dialogue_flags[flag] = True
            return

    def _tutorial_mark_weight_warning_seen(self, key: str) -> None:
        """Persist weight-warning dismissal (already set pre-emptively on
        fire; this is a safety net in case the pre-set was missed)."""
        self.player.dialogue_flags[f"tutorial_weight_{key}_seen"] = True

    def _render_tutorial_phase_strip(self, screen: pygame.Surface) -> None:
        """Render the persistent phase objective strip at the top of the
        screen during the tutorial. High-contrast band with current phase,
        objective, and live progress."""
        strip_h = scale_y(38)
        # Background band
        band = pygame.Surface((WINDOW_WIDTH, strip_h), pygame.SRCALPHA)
        band.fill((12, 18, 30, 235))
        screen.blit(band, (0, 0))
        # Accent stripe — flips positive when the current gate is met
        phase = self._tutorial_phase()
        accent = Colors.TEXT_HIGHLIGHT  # neutral "in progress"
        if phase == "complete":
            try:
                from spacegame.engine.material_palette import get_role
                accent = get_role("status_positive")
            except Exception:
                accent = Colors.GREEN
        pygame.draw.rect(screen, accent, (0, 0, scale_x(4), strip_h))

        # Phase label (left)
        phase_label_map = {
            "slots": "PHASE 1 OF 3: PLACE SLOTS",
            "hull": "PHASE 2 OF 3: PAINT HULL",
            "complete": "PHASE 3 OF 3: CONFIRM BUILD",
        }
        label_text = phase_label_map.get(phase, "TUTORIAL")
        label_surf = self.title_font.render(label_text, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(label_surf, (scale_x(16), (strip_h - label_surf.get_height()) // 2))

        # Progress (right)
        progress_text = self._tutorial_progress_text()
        if progress_text:
            prog_surf = self.small_font.render(progress_text, True, Colors.TEXT_SECONDARY)
            px = WINDOW_WIDTH - prog_surf.get_width() - scale_x(18)
            py = (strip_h - prog_surf.get_height()) // 2
            screen.blit(prog_surf, (px, py))

    def _tutorial_progress_text(self) -> str:
        """Return the live-progress string shown on the phase strip's right side."""
        phase = self._tutorial_phase()
        if phase == "slots":
            required = self._tutorial_required_slot_types()
            slot_defs = getattr(self.data_loader, "slot_definitions", {})
            placed_types = set()
            for ps in self.build.placed_slots:
                sd = slot_defs.get(ps.slot_def_id)
                if sd:
                    placed_types.add(sd.slot_type)
            placed = len(required & placed_types)
            total = len(required)
            return f"Slots placed: {placed}/{total}"
        if phase == "hull":
            pixels = len(self.build.pixels)
            return f"Hull pixels: {pixels}/{self._MIN_TUTORIAL_HULL_PIXELS}+"
        if phase == "complete":
            return "CONFIRM BUILD to continue"
        return ""

    def render_top(self, screen: pygame.Surface) -> None:
        """PT-N: draw the tutorial narration modal above pygame_gui elements."""
        if self._tutorial_narration_modal is not None:
            self._tutorial_narration_modal.render(screen)

    def _render_tutorial_stat_preview(self, screen: pygame.Surface) -> None:
        """Live stat preview panel shown during the tutorial.

        Contents:
          - Core combat stats (Hull, Armor, Shields, Speed, Evasion)
          - Weight gauge with HEAVY (80%) and OVERLOADED (95%) threshold marks
          - Shape classification tags (narrow/balanced) with evasion effect

        The gauge and classification tags teach the hull-painting trade-offs
        the Phase B narration describes. Colors pull from PALETTE_ROLES so
        colorblind profiles remap automatically.
        """
        panel_x = MATERIAL_PANEL_X
        panel_y = MATERIAL_PANEL_Y
        panel_w = MATERIAL_PANEL_W
        panel_h = MATERIAL_PANEL_H

        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=220)

        title = self.small_font.render("LIVE STATS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + scale_x(10), panel_y + scale_y(6)))

        stats = self._computed_stats
        if stats is None:
            return

        # --- Core stats ---
        y = panel_y + scale_y(28)
        x = panel_x + scale_x(10)
        val_x = panel_x + panel_w - scale_x(10)
        stat_rows = [
            ("Hull", "hull", str(stats.hull)),
            ("Armor", "armor", str(stats.armor)),
            ("Shields", "shields", str(stats.shields)),
            ("Speed", "speed", str(stats.speed)),
            ("Evasion", "evasion", str(stats.evasion)),
        ]
        pos_color = _palette_role_color("status_positive", Colors.GREEN)
        neg_color = _palette_role_color("status_negative", Colors.RED)
        for label, key, value in stat_rows:
            lbl = self.label_font.render(label, True, Colors.TEXT_SECONDARY)
            val = self.label_font.render(value, True, Colors.TEXT_PRIMARY)
            screen.blit(lbl, (x, y))
            screen.blit(val, (val_x - val.get_width(), y))
            # PT-N: delta flash — "+2" or "-3" next to the stat, fades
            # with the timer in _tutorial_stat_deltas. Alpha scales off
            # the timer for a smooth fade. getattr guards the rare path
            # where the view is built via __new__ in tests.
            delta_entry = getattr(self, "_tutorial_stat_deltas", {}).get(key)
            if delta_entry is not None:
                delta_val, timer = delta_entry
                sign = "+" if delta_val > 0 else ""
                delta_text = f"{sign}{int(delta_val)}"
                color = pos_color if delta_val > 0 else neg_color
                delta_surf = self.label_font.render(delta_text, True, color)
                # Fade out over last 0.6s of 1.8s lifetime
                alpha = int(min(255, 255 * (timer / 0.6))) if timer < 0.6 else 255
                delta_surf.set_alpha(alpha)
                # Position right of the value, same row
                delta_x = val_x - val.get_width() - scale_x(6) - delta_surf.get_width()
                screen.blit(delta_surf, (delta_x, y))
            y += scale_y(15)

        # --- Weight gauge ---
        y += scale_y(6)
        pos = _palette_role_color("status_positive", Colors.GREEN)
        warn = _palette_role_color("status_warning", Colors.YELLOW)
        neg = _palette_role_color("status_negative", Colors.RED)
        ratio = 0.0
        if stats.weight_max > 0:
            ratio = stats.weight_current / stats.weight_max
        weight_label = self.label_font.render(
            f"Weight {stats.weight_current:.0f}/{stats.weight_max}  ({int(ratio * 100)}%)",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(weight_label, (x, y))
        y += scale_y(14)

        # Gauge bar
        bar_w = panel_w - scale_x(20)
        bar_h = scale_y(10)
        bar_x = x
        bar_y = y
        # Background
        pygame.draw.rect(screen, Colors.UI_PANEL, (bar_x, bar_y, bar_w, bar_h))
        # Fill color depends on threshold
        if ratio >= 0.95:
            fill_color = neg
        elif ratio >= 0.80:
            fill_color = warn
        else:
            fill_color = pos
        fill_w = max(0, min(bar_w, int(bar_w * ratio)))
        pygame.draw.rect(screen, fill_color, (bar_x, bar_y, fill_w, bar_h))
        # Threshold ticks at 80% and 95%
        for t in (0.80, 0.95):
            tx = bar_x + int(bar_w * t)
            pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (tx, bar_y - 1, 1, bar_h + 2))
        # Border
        pygame.draw.rect(screen, Colors.UI_BORDER, (bar_x, bar_y, bar_w, bar_h), 1)
        y += bar_h + scale_y(4)
        tick_hint = self.label_font.render("80%   95%", True, Colors.TEXT_SECONDARY)
        screen.blit(tick_hint, (bar_x, y))
        y += scale_y(16)

        # --- Shape classifications ---
        y += scale_y(4)
        shape_label = self.small_font.render("SHAPE", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(shape_label, (x, y))
        y += scale_y(16)

        profile_tag, profile_effect, profile_color = self._tutorial_profile_classification()
        balance_tag, balance_effect, balance_color = self._tutorial_balance_classification()

        for tag, effect, color in (
            (profile_tag, profile_effect, profile_color),
            (balance_tag, balance_effect, balance_color),
        ):
            tag_surf = self.label_font.render(tag, True, color)
            screen.blit(tag_surf, (x, y))
            if effect:
                eff_surf = self.label_font.render(effect, True, Colors.TEXT_SECONDARY)
                screen.blit(eff_surf, (x + tag_surf.get_width() + scale_x(6), y))
            y += scale_y(14)

    def _tutorial_profile_classification(self) -> tuple[str, str, tuple[int, int, int]]:
        """Return (tag, effect_label, color) for the ship's frontal profile.

        Matches the thresholds used in compute_physics_modifiers:
          <0.3 → NARROW, +10% evasion
          0.3-0.6 → NORMAL, no change
          >0.6 → WIDE, -10% evasion
        """
        from spacegame.models.ship_physics import compute_frontal_profile

        coords = [(p.x, p.y) for p in self.build.pixels]
        if not coords:
            return ("NORMAL", "", Colors.TEXT_SECONDARY)
        _, _, ratio = compute_frontal_profile(coords, self.build.canvas_w)
        pos = _palette_role_color("status_positive", Colors.GREEN)
        neg = _palette_role_color("status_negative", Colors.RED)
        if ratio < 0.3:
            return ("NARROW", "+10% eva", pos)
        if ratio > 0.6:
            return ("WIDE", "-10% eva", neg)
        return ("NORMAL", "", Colors.TEXT_SECONDARY)

    def _tutorial_balance_classification(self) -> tuple[str, str, tuple[int, int, int]]:
        """Return (tag, effect_label, color) for center-of-mass balance."""
        from spacegame.models.ship_physics import BalanceRating, compute_center_of_mass

        materials = getattr(self.data_loader, "hull_materials", {})
        module_catalog = getattr(self.data_loader, "ship_modules", {})
        _, _, _, rating = compute_center_of_mass(self.build, materials, module_catalog)
        pos = _palette_role_color("status_positive", Colors.GREEN)
        warn = _palette_role_color("status_warning", Colors.YELLOW)
        neg = _palette_role_color("status_negative", Colors.RED)
        if rating == BalanceRating.BALANCED:
            return ("BALANCED", "", pos)
        if rating == BalanceRating.OFF_BALANCE:
            return ("OFF-BALANCE", "-10% eva", warn)
        return ("SEVERELY OFF", "-25% eva", neg)

    def _tutorial_auto_equip(self) -> None:
        """Auto-equip tutorial parts from player inventory into matching slots.

        Narratively framed (elsewhere) as "I mounted the parts for you this
        once — at any shipyard you'll do this yourself at the Loadout tab."
        Matches part to slot by slot_type; uses the first matching unequipped
        slot. Cockpit slots are self-fulfilling and skipped.
        """
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        parts_catalog = getattr(self.data_loader, "ship_parts", {})
        inventory = dict(getattr(self.player, "parts_inventory", {}))
        for ps in self.build.placed_slots:
            if ps.equipped_part_id:
                continue
            sd = slot_defs.get(ps.slot_def_id)
            if sd is None or sd.slot_type == "cockpit":
                continue
            # Find a part in inventory matching this slot's type
            for part_id, count in list(inventory.items()):
                if count <= 0:
                    continue
                part = parts_catalog.get(part_id)
                if part is None or part.slot_type != sd.slot_type:
                    continue
                ps.equipped_part_id = part_id
                inventory[part_id] = count - 1
                # Deduct from the player's real inventory too
                if hasattr(self.player, "remove_part"):
                    self.player.remove_part(part_id)
                break

    def _confirm_build(self) -> None:
        """Start the build confirmation flow — shows naming dialog first."""
        if not self._can_confirm:
            return
        # Tutorial mode: skip naming, auto-finalize, and return to tutorial flow
        # Set entry_cost = new build cost so delta is 0 (shop already charged)
        if self._tutorial_mode:
            # PT-N: tutorial CONFIRM pipeline.
            # 1. Verify phase complete (already gated via _can_confirm, but
            #    defensive re-check).
            # 2. Auto-equip bought parts into matching slots (narrated as
            #    "I mounted these for you this once — Loadout tab next time").
            # 3. Charge the tutorial discount amount (placement 50% + hull).
            # 4. Apply the build, set completion flag, transition.
            if self._tutorial_phase() != "complete":
                return
            self._tutorial_auto_equip()
            charge = self._tutorial_charge_amount()
            if charge > self.player.credits:
                self._validation_warnings.append(
                    f"Not enough credits ({charge:,} needed, {self.player.credits:,} on hand)"
                )
                return
            self.player.credits -= charge
            # Apply the build directly (don't route through _finalize_build's
            # delta path — tutorial pricing uses a custom charge).
            self._recompute_stats()
            self.player.ship.set_build(self.build, full_heal=True)
            if self._computed_stats:
                self.player.ship.current_hull = self._computed_stats.hull
                self.player.ship.current_shields = self._computed_stats.shields
            self._modified = False
            if self._naming_text.strip():
                self.player.ship_name = self._naming_text.strip()
            self._naming_active = False
            logger.info(
                f"Tutorial build confirmed: charged {charge:,} CR "
                f"(placement 50%, hull full, parts prepaid at shop)"
            )
            # PT-007 bookend: mechanic signs off, with explicit
            # affirmation that auto-equip ran (so the player knows the
            # parts they bought are now in the ship).
            self._pending_tutorial_farewell = (
                'Mechanic: "That\'ll fly. Parts mounted. '
                'I\'ll push you off. Galaxy\'s waiting."'
            )
            # PT-H: tutorial_builder_complete gates Arna's first-encounter
            # interception on first STATION_HUB entry after tutorial.
            self.player.dialogue_flags["tutorial_builder_complete"] = True
            self.next_state = self._tutorial_return_state
            return
        # PT-012: auto-skip the naming dialog when the ship already has a
        # name. Players named their ship at game start (or via the explicit
        # RENAME button); re-prompting on every confirm is noise. If they
        # want to rename, the RENAME button is always available on the toolbar.
        if self.player.ship_name:
            self._finalize_build()
            return
        # No name yet — show naming dialog before finalizing
        self._naming_active = True
        self._naming_text = self.player.ship.ship_type.name
        self._naming_cursor_timer = 0.0

    def _finalize_build(self) -> None:
        """Apply the current build to the player's ship. Charges only the delta cost."""
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

        self.player.ship.set_build(self.build, full_heal=True)
        # Update hull/shields to match new build stats
        if self._computed_stats:
            self.player.ship.current_hull = self._computed_stats.hull
            self.player.ship.current_shields = self._computed_stats.shields
        self._modified = False
        # Apply ship name from naming dialog
        if self._naming_text.strip():
            self.player.ship_name = self._naming_text.strip()
        self._naming_active = False
        logger.info(f"Ship build confirmed — '{self.player.display_ship_name}'")

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
        try:
            get_audio_manager().play_sfx("ui_confirm")
        except Exception:
            pass

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

        has_slots = len(self.build.placed_slots) > 0
        has_pixels = len(self.build.pixels) > 0
        has_content = has_slots or has_pixels

        # Slot-based validation (primary for new builds)
        if has_slots:
            slot_defs = getattr(self.data_loader, "slot_definitions", {})
            slot_type_counts: dict[str, int] = {}
            for ps in self.build.placed_slots:
                sd = slot_defs.get(ps.slot_def_id)
                if sd:
                    slot_type_counts[sd.slot_type] = slot_type_counts.get(sd.slot_type, 0) + 1

            # Flight readiness check via FrameRequirements
            if self._frame_reqs is not None:
                # Build size lists for min_size validation
                slot_sizes: dict[str, list[str]] = {}
                for ps in self.build.placed_slots:
                    sd = slot_defs.get(ps.slot_def_id)
                    if sd:
                        slot_sizes.setdefault(sd.slot_type, []).append(sd.size)
                _ready, reasons = self._frame_reqs.check_flight_ready(slot_type_counts, slot_sizes)
                for reason in reasons:
                    warnings.append(f"Not flight ready: {reason}")
            else:
                # Legacy fallback
                if slot_type_counts.get("cockpit", 0) < 1:
                    warnings.append("Cockpit required! Place a cockpit slot.")
                if slot_type_counts.get("engine", 0) < 1:
                    warnings.append("Engine required! Place at least 1 engine slot.")
                if slot_type_counts.get("reactor", 0) < 1:
                    warnings.append("Reactor required! Place at least 1 reactor slot.")
                if slot_type_counts.get("fuel", 0) < 1:
                    warnings.append("Fuel tank required! Place at least 1 fuel slot.")

            # Frame slot limit checks
            reqs = self._frame_reqs if self._frame_reqs is not None else None
            for stype, count in slot_type_counts.items():
                limit = (
                    reqs.get_max(stype)
                    if reqs
                    else FRAME_SLOT_LIMITS.get(self.build.weight_class, {}).get(stype, 0)
                )
                if count > limit:
                    warnings.append(f"Too many {stype} slots: {count}/{limit}")

        if not has_content:
            warnings.append("Empty build. Place slots and hull pixels to design your ship.")

        # Advisory warnings (non-blocking, informational)
        advisories: list[str] = []

        # No-weapon advisory (slot-based builds)
        if has_slots and slot_type_counts.get("weapon", 0) == 0:
            advisories.append("No weapons installed. You'll rely on crew abilities in combat.")

        self._validation_warnings = warnings
        self._advisory_warnings = advisories
        was_confirmable = self._can_confirm
        self._can_confirm = has_content and len(warnings) == 0
        # PT-N: in tutorial mode, CONFIRM is additionally gated on all three
        # phases completing. This is the structural fix for the Arna-
        # interruption report — the only path to station hub is CONFIRM,
        # and CONFIRM won't fire until slots + hull are done. Arna physically
        # cannot interrupt mid-tutorial anymore.
        if self._tutorial_mode and self._tutorial_phase() != "complete":
            self._can_confirm = False

        # Play positive feedback when all requirements first met
        if self._can_confirm and not was_confirmable and has_slots:
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

            # After placing first slot (cockpit likely) -> engine hint
            slot_defs = getattr(self.data_loader, "slot_definitions", {})
            has_cockpit = any(
                slot_defs.get(ps.slot_def_id) is not None
                and slot_defs[ps.slot_def_id].slot_type == "cockpit"
                for ps in self.build.placed_slots
            )
            has_engine = any(
                slot_defs.get(ps.slot_def_id) is not None
                and slot_defs[ps.slot_def_id].slot_type == "engine"
                for ps in self.build.placed_slots
            )
            if has_cockpit and not has_engine and not flags.get("builder_module_engine_seen"):
                self.player.dialogue_flags["builder_module_engine_seen"] = True
                self._pending_hint = "builder_module_engine"
                return

            # After placing 2+ slots -> requirements hint
            if len(self.build.placed_slots) >= 2 and not flags.get(
                "builder_module_requirements_seen"
            ):
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
        parts_catalog = getattr(self.data_loader, "ship_parts", {})
        self._computed_stats = ShipStatsComputer.compute(
            self.build,
            materials,
            equipment,
            module_catalog=module_catalog,
            slot_definitions=slot_definitions,
            parts_catalog=parts_catalog,
            ship_type=self.player.ship.ship_type,
        )
        # Invalidate physics overlay caches and preview
        self._cached_integrity = None
        self._cached_exposure = None
        self._preview_dirty = True
        # PT-N: compute deltas for the tutorial stat preview. Each stat
        # change generates a "+N" or "-N" indicator that fades after ~1.8s.
        # Only tracks in tutorial mode — non-tutorial doesn't need the
        # teaching reinforcement.
        if self._tutorial_mode and self._computed_stats is not None:
            self._tutorial_record_stat_deltas()

    def _tutorial_record_stat_deltas(self) -> None:
        """Compare current stats to the snapshot; record deltas for any
        changed stat; refresh snapshot."""
        stats = self._computed_stats
        if stats is None:
            return
        tracked = {
            "hull": stats.hull,
            "armor": stats.armor,
            "shields": stats.shields,
            "speed": stats.speed,
            "evasion": stats.evasion,
        }
        for key, current in tracked.items():
            prev = self._tutorial_stat_snapshot.get(key)
            if prev is None:
                # First-ever snapshot — no delta
                continue
            delta = current - prev
            if abs(delta) >= 0.5:  # ignore sub-integer float noise
                # Timer: 1.8 seconds of visibility
                self._tutorial_stat_deltas[key] = (delta, 1.8)
        # Refresh snapshot after comparing
        self._tutorial_stat_snapshot = dict(tracked)

    def _tutorial_tick_stat_deltas(self, dt: float) -> None:
        """Tick down delta display timers; drop expired entries."""
        to_remove: list[str] = []
        for key, (delta, timer) in list(self._tutorial_stat_deltas.items()):
            new_timer = timer - dt
            if new_timer <= 0:
                to_remove.append(key)
            else:
                self._tutorial_stat_deltas[key] = (delta, new_timer)
        for key in to_remove:
            del self._tutorial_stat_deltas[key]

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

        # PT-N: drive tutorial narration modal — fire on phase transitions
        # once per phase, tick fade-in timer, clear when dismissed. Weight
        # warnings fire via the same modal when ratio crosses thresholds.
        # Also tick stat-delta fade timers so "+2 Hull" indicators dismiss
        # after their visible window.
        if self._tutorial_mode:
            self._tutorial_maybe_fire_phase_narration()
            self._tutorial_maybe_fire_weight_warning()
            self._tutorial_tick_stat_deltas(dt)
            if self._tutorial_narration_modal is not None:
                self._tutorial_narration_modal.update(dt)
                if self._tutorial_narration_modal.dismissed:
                    self._tutorial_narration_modal = None

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

        # Header with mode toggle. PT-N: in tutorial mode, the phase
        # objective strip replaces the normal title line — it is the
        # "what do I do right now" anchor.
        if self._tutorial_mode:
            self._render_tutorial_phase_strip(screen)
        else:
            title = self.title_font.render(
                f"DRYDOCK \u2014 {self.build.weight_class.upper()} ({self.build.canvas_w}×{self.build.canvas_h})",
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
            # PT-N: tutorial mode replaces requirements checklist with the
            # live stat preview — more teaching-focused for the player
            # learning the trade-offs. Non-tutorial players see the normal
            # checklist.
            if self._tutorial_mode:
                self._render_tutorial_stat_preview(screen)
            else:
                self._render_requirements_checklist(screen)
        else:
            self._render_shape_palette(screen)
            if self._tutorial_mode:
                self._render_tutorial_stat_preview(screen)
            else:
                self._render_material_panel(screen)
        self._render_stats_panel(screen)
        self._render_ship_preview(screen)

        # Floating feedback messages (Phase 10)
        for msg in self._feedback_messages:
            alpha = int(255 * min(1.0, msg["timer"] / 0.5))
            text_surf = self.label_font.render(msg["text"], True, msg["color"])
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (int(msg["x"]), int(msg["y"])))

        # Ambient particles
        self.particles.render(screen)

        # Stat comparison preview (when hovering shape in palette)
        if self._builder_mode == "hull":
            self._render_stat_preview(screen)

        # Module hover tooltip (when hovering placed module on grid)
        if self._builder_mode == "slot":
            self._render_module_tooltip(screen)

        # Ship naming dialog (overlay, BP2)
        if self._naming_active:
            self._render_naming_dialog(screen)

        # Confirmation animation (overlay)
        if self._confirm_anim_timer > 0:
            self._render_confirm_animation(screen)

        # Import modal (overlay)
        if getattr(self, "_import_modal_open", False):
            self._render_import_modal(screen)

        # Help overlay (on top of everything)
        if getattr(self, "_help_overlay_open", False):
            self._render_help_overlay(screen)

        # Tutorial narration panel (bottom, above HUD)
        if self._tutorial_mode:
            self._render_tutorial_narration(screen)

    def _render_grid(self, screen: pygame.Surface) -> None:
        """Render the ship building grid with placed pixels."""
        cw, ch = self.build.canvas_w, self.build.canvas_h
        cell = self._get_cell_size()
        ox, oy = self._get_grid_origin()

        # Grid background
        grid_w = cw * cell
        grid_h = ch * cell
        pygame.draw.rect(screen, _BUILDER_COLORS["grid_bg"], (ox, oy, grid_w, grid_h))

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
        stern_label = self.label_font.render("STERN", True, _BUILDER_COLORS["label_trim_warm"])
        screen.blit(stern_label, (ox + 3, oy - stern_label.get_height() - 2))
        bow_label = self.label_font.render("BOW", True, _BUILDER_COLORS["label_trim_warm"])
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
            color = mat.color_primary if mat else _BUILDER_COLORS["material_fallback"]
            px = ox + pixel.x * cell
            py = oy + pixel.y * cell
            pygame.draw.rect(screen, color, (px + 1, py + 1, cell - 1, cell - 1))

        # Legacy module rendering and slot indicators removed

        # Placed slots — rendered using rotated pixel_mask for shaped slots,
        # or as solid rectangles for standard slots
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for ps in self.build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            # Get rotated footprint
            fw, fh, r_mask = sdef.get_rotated(ps.rotation)
            sx = ox + ps.x * cell
            sy = oy + ps.y * cell
            sw = fw * cell
            sh = fh * cell

            if r_mask:
                # Shaped slot — render per-cell using rotated mask
                for ly in range(fh):
                    for lx in range(fw):
                        if ly < len(r_mask) and lx < len(r_mask[ly]) and r_mask[ly][lx] == "X":
                            cx = sx + lx * cell
                            cy = sy + ly * cell
                            fill = pygame.Surface((cell, cell), pygame.SRCALPHA)
                            fill.fill((*sdef.color, 60))
                            screen.blit(fill, (cx, cy))
                            pygame.draw.rect(screen, sdef.color, (cx, cy, cell, cell), 1)
            else:
                # Standard rectangular slot
                fill_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                fill_surf.fill((*sdef.color, 60))
                screen.blit(fill_surf, (sx, sy))
                pygame.draw.rect(screen, sdef.color, (sx, sy, sw, sh), 2)

            # Center type label (e.g., "W", "D", "E", "K")
            type_letter = _SLOT_TYPE_SHORT.get(sdef.slot_type, "?")
            if cell >= 6:
                type_surf = self.label_font.render(type_letter, True, Colors.WHITE)
                type_rect = type_surf.get_rect(center=(sx + sw // 2, sy + sh // 2))
                screen.blit(type_surf, type_rect)
            # Size label in top-left corner (on first filled cell)
            size_letter = _SIZE_DISPLAY.get(sdef.size, "?")
            if cell >= 6:
                size_surf = self.label_font.render(size_letter, True, _BUILDER_COLORS["text_softer_white"])
                screen.blit(size_surf, (sx + 2, sy + 1))
            # Equipped indicator dot (bottom-right)
            if ps.equipped_part_id:
                dot_r = max(2, cell // 4)
                pygame.draw.circle(
                    screen, _BUILDER_COLORS["valid_place"], (sx + sw - dot_r - 2, sy + sh - dot_r - 2), dot_r
                )

        # Ghost preview — slot mode or hull mode
        mouse_pos = pygame.mouse.get_pos()
        grid_pos = self._screen_to_grid(mouse_pos[0], mouse_pos[1])

        if grid_pos and self._builder_mode == "slot" and self._selected_slot_def_id:
            # Slot ghost preview
            ghost_sdef = slot_defs.get(self._selected_slot_def_id)
            if ghost_sdef:
                gx, gy = grid_pos
                fw, fh, g_mask = ghost_sdef.get_rotated(self._module_rotation)
                ok, _ = self._validate_slot_placement(gx, gy, ghost_sdef)
                ghost_color = _BUILDER_COLORS["valid_place"] if ok else _BUILDER_COLORS["invalid_place"]
                ghost_sx = ox + gx * cell
                ghost_sy = oy + gy * cell
                ghost_sw = fw * cell
                ghost_sh = fh * cell
                if g_mask:
                    # Shaped ghost — render per-cell using rotated mask
                    for ly in range(fh):
                        for lx in range(fw):
                            if ly < len(g_mask) and lx < len(g_mask[ly]) and g_mask[ly][lx] == "X":
                                cx = ghost_sx + lx * cell
                                cy = ghost_sy + ly * cell
                                gc = pygame.Surface((cell, cell), pygame.SRCALPHA)
                                gc.fill((*ghost_color, 80))
                                screen.blit(gc, (cx, cy))
                                pygame.draw.rect(screen, ghost_color, (cx, cy, cell, cell), 1)
                else:
                    ghost_surf = pygame.Surface((ghost_sw, ghost_sh), pygame.SRCALPHA)
                    ghost_surf.fill((*ghost_color, 80))
                    screen.blit(ghost_surf, (ghost_sx, ghost_sy))
                    pygame.draw.rect(
                        screen, ghost_color, (ghost_sx, ghost_sy, ghost_sw, ghost_sh), 2
                    )
                # Show footprint dimensions near cursor
                dim_text = f"{fw}x{fh}"
                dim_surf = self.label_font.render(dim_text, True, ghost_color)
                screen.blit(dim_surf, (ghost_sx + ghost_sw + 3, ghost_sy))

        elif grid_pos and self._builder_mode == "hull" and self._selected_shape:
            # Shape ghost preview (existing hull mode)
            shape = self._get_transformed_shape()
            mat = self._get_selected_material()
            ghost_color = mat.color_primary if mat else _BUILDER_COLORS["ghost_fallback"]
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
                            preview_color = ghost_color if valid else _BUILDER_COLORS["invalid_preview"]
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
        if self._show_exposure_overlay:
            self._render_exposure_overlay(screen, ox, oy, cell, cw, ch)

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
            bg_color = _BUILDER_COLORS["cell_selected_cool"] if is_selected else Colors.UI_PANEL
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
            bg_color = _BUILDER_COLORS["cell_selected"] if is_selected else Colors.UI_PANEL
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
                _BUILDER_COLORS["label_mute_warm"],
            )
            screen.blit(info, (text_x, sy + 32))

        # Tool hint at bottom
        tool_y = start_y + len(hull_mats) * (swatch_h + pad) + scale_y(8)
        hint = self.label_font.render(
            f"Active: {self._active_tool.upper()} [{self._active_tool[0].upper()}]",
            True,
            _BUILDER_COLORS["label_mute_warm_soft"],
        )
        screen.blit(hint, (MATERIAL_PANEL_X + 8, tool_y))
        mirror_hint = self.label_font.render(
            f"Mirror [X]: {'ON' if self._mirror_mode else 'OFF'}",
            True,
            Colors.GREEN if self._mirror_mode else _BUILDER_COLORS["label_mute_cool"],
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
            bg = _BUILDER_COLORS["tab_active"] if is_active else _BUILDER_COLORS["tab_inactive"]
            border = Colors.TEXT_HIGHLIGHT if is_active else _BUILDER_COLORS["border_tab_inactive"]
            pygame.draw.rect(screen, bg, (bx, toggle_y, btn_w, btn_h), border_radius=3)
            pygame.draw.rect(screen, border, (bx, toggle_y, btn_w, btn_h), 1, border_radius=3)
            label = self.label_font.render(
                label_text, True, Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY
            )
            screen.blit(label, (bx + btn_w // 2 - label.get_width() // 2, toggle_y + 3))

        # Tab hint
        hint = self.label_font.render("[Tab]", True, _BUILDER_COLORS["label_mute_cool"])
        screen.blit(hint, (start_x + total_w + 6, toggle_y + 4))

        # Frame variant selector (Medium+ only)
        from spacegame.models.ship_build import FRAME_VARIANTS

        if self.build.weight_class in FRAME_VARIANTS:
            frame_x = scale_x(20)
            frame_y = toggle_y
            frame_btn_w = scale_x(42)
            frame_h = scale_y(20)
            variants = [("default", "Std"), ("wide", "Wide"), ("tall", "Tall")]
            frame_label = self.label_font.render("Frame:", True, _BUILDER_COLORS["label_mute_warm"])
            screen.blit(frame_label, (frame_x, frame_y + 3))
            btn_start_x = frame_x + frame_label.get_width() + 4
            self._frame_variant_rects = {}
            for i, (variant_key, label) in enumerate(variants):
                bx = btn_start_x + i * (frame_btn_w + 2)
                current = self.build.frame_variant or "default"
                is_active = variant_key == current
                bg = _BUILDER_COLORS["tab_active"] if is_active else _BUILDER_COLORS["cell_alt"]
                border = Colors.TEXT_HIGHLIGHT if is_active else _BUILDER_COLORS["border_tab_subtle"]
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
        mouse_pos = pygame.mouse.get_pos()
        _undersized_tooltip: Optional[str] = None  # Set if hovering an undersized slot
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
                header_color = defs[0].color if defs else _BUILDER_COLORS["text_category_fallback"]
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

                    # Check if limit reached or slot size too small for frame
                    at_limit = type_counts.get(sdef.slot_type, 0) >= self._get_slot_type_limit(
                        sdef.slot_type
                    )
                    undersized = (
                        self._frame_reqs is not None
                        and not self._frame_reqs.is_slot_size_valid(sdef.slot_type, sdef.size)
                    )
                    at_limit = at_limit or undersized

                    # Track tooltip for undersized slots on hover
                    if undersized and self._frame_reqs is not None:
                        row_rect = pygame.Rect(panel_x + 3, y_cursor, panel_w - 6, item_h - 2)
                        if row_rect.collidepoint(mouse_pos):
                            min_sz = self._frame_reqs.get_min_size(sdef.slot_type)
                            type_name = _TYPE_DISPLAY.get(sdef.slot_type, sdef.slot_type)
                            sz_label = {"medium": "medium", "large": "large"}.get(min_sz, min_sz)
                            _undersized_tooltip = (
                                f"This frame requires {sz_label}+ {type_name.lower()}s"
                            )

                    # Background
                    if is_selected:
                        bg_color = _BUILDER_COLORS["cell_selected_strong"]
                    elif at_limit:
                        bg_color = _BUILDER_COLORS["cell_dim"]
                    else:
                        bg_color = Colors.UI_PANEL
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
                    swatch_color = sdef.color if not at_limit else _BUILDER_COLORS["text_disabled_swatch"]
                    pygame.draw.rect(
                        screen,
                        swatch_color,
                        (swatch_x, swatch_y, swatch_size, swatch_size),
                        border_radius=2,
                    )

                    # Display name with variant indicator
                    text_x = swatch_x + swatch_size + 6
                    name_color = _BUILDER_COLORS["text_locked"] if at_limit else Colors.TEXT_PRIMARY
                    display_label = sdef.display_name
                    vg_ids = self._slot_variant_lists.get(sdef.variant_group, [])
                    if sdef.variant_group and len(vg_ids) > 1:
                        vg_idx = self._slot_variant_index.get(sdef.variant_group, 0)
                        vg_idx = vg_idx % len(vg_ids)
                        display_label += f" ({vg_idx + 1}/{len(vg_ids)})"
                    name_surf = self.label_font.render(display_label, True, name_color)
                    screen.blit(name_surf, (text_x, y_cursor + 1))

                    # Info line: footprint, weight, cost + variant name
                    info_color = _BUILDER_COLORS["text_locked_dim"] if at_limit else Colors.TEXT_SECONDARY
                    info_parts = (
                        f"{sdef.footprint_w}x{sdef.footprint_h}  "
                        f"W:{sdef.weight:.0f}  "
                        f"{sdef.placement_cost:,}CR"
                    )
                    if sdef.variant_name and sdef.variant_name != "Standard":
                        info_parts += f"  [{sdef.variant_name}]"
                    info_surf = self.label_font.render(info_parts, True, info_color)
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
                screen, _BUILDER_COLORS["label_mute_cool_soft"], (panel_x + panel_w - 5, bar_y, 3, bar_h), border_radius=1
            )

        # Tooltip for undersized slots (rendered outside clip region)
        if _undersized_tooltip:
            tip_surf = self.label_font.render(_undersized_tooltip, True, _BUILDER_COLORS["warn_tip_text"])
            tip_w = tip_surf.get_width() + 12
            tip_h = tip_surf.get_height() + 8
            # Position to the right of the palette, clamped to screen
            tip_x = min(mouse_pos[0] + 14, WINDOW_WIDTH - tip_w - 4)
            tip_y = max(mouse_pos[1] - tip_h - 4, 4)
            tip_bg = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
            tip_bg.fill((20, 18, 32, 230))
            screen.blit(tip_bg, (tip_x, tip_y))
            pygame.draw.rect(
                screen, _BUILDER_COLORS["warn_tip_border"], (tip_x, tip_y, tip_w, tip_h), 1, border_radius=3
            )
            screen.blit(tip_surf, (tip_x + 6, tip_y + 4))

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
            bg = _BUILDER_COLORS["tab_header_active"] if active else _BUILDER_COLORS["cell_alt"]
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
                bg_color = _BUILDER_COLORS["cell_dim"]  # Dark, grayed out
            elif is_selected:
                bg_color = _BUILDER_COLORS["cell_selected_strong"]
            else:
                bg_color = Colors.UI_PANEL
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
                    color = mat.color_primary if mat else _BUILDER_COLORS["material_fallback_dark"]
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
            name_color = _BUILDER_COLORS["text_locked"] if is_locked else Colors.TEXT_PRIMARY
            name_surf = self.label_font.render(module.name, True, name_color)
            screen.blit(name_surf, (text_x, iy + 2))

            # Category and weight
            cat_color = {
                "cockpit": _BUILDER_COLORS["cat_cockpit"],
                "engine": _BUILDER_COLORS["cat_engine"],
                "weapon": _BUILDER_COLORS["cat_weapon"],
                "shield": _BUILDER_COLORS["cat_shield"],
                "cargo": _BUILDER_COLORS["cat_cargo"],
                "utility": _BUILDER_COLORS["cat_utility"],
                "structural": _BUILDER_COLORS["cat_structural"],
                "crew": _BUILDER_COLORS["cat_crew"],
                "reactor": _BUILDER_COLORS["cat_reactor"],
            }.get(module.category, Colors.TEXT_SECONDARY)
            if is_locked:
                cat_color = _BUILDER_COLORS["text_locked_dim"]
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
                    _BUILDER_COLORS["swatch_fallback_warm"],
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
                screen, _BUILDER_COLORS["label_mute_cool_soft"], (panel_x + panel_w - 5, bar_y, 3, bar_h), border_radius=1
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

        # Count slots or modules by category
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        catalog = self._get_module_catalog()
        cat_counts: dict[str, int] = {}

        for ps in self.build.placed_slots:
            sd = slot_defs.get(ps.slot_def_id)
            if sd:
                cat_counts[sd.slot_type] = cat_counts.get(sd.slot_type, 0) + 1

        # Build requirements list from FrameRequirements or legacy fallback
        reqs = self._frame_reqs if self._frame_reqs is not None else None
        _SIZE_SUFFIX = {"small": "", "medium": " (M+)", "large": " (L+)"}

        if self.build.placed_slots and reqs:
            # Per-frame requirements: (label, cat_key, min, max)
            requirements: list[tuple[str, str, int, int]] = []
            for cat in _SLOT_TYPE_ORDER:
                mn = reqs.get_min(cat)
                mx = reqs.get_max(cat)
                if mx == 0 and mn == 0:
                    continue
                display = _TYPE_DISPLAY.get(cat, cat.replace("_", " ").title())
                sz_suffix = _SIZE_SUFFIX.get(reqs.get_min_size(cat), "")
                label = f"{display}{sz_suffix}"
                requirements.append((label, cat, mn, mx))
        else:
            # Slot-based but no frame_reqs (defensive fallback)
            caps = FRAME_SLOT_LIMITS.get(self.build.weight_class, {})
            requirements = []
            for cat in _SLOT_TYPE_ORDER:
                cap = caps.get(cat, 0)
                if cap == 0:
                    continue
                display = _TYPE_DISPLAY.get(cat, cat.replace("_", " ").title())
                needed = 1 if cat in ("cockpit", "engine", "fuel", "reactor") else 0
                requirements.append((display, cat, needed, cap))

        row_y = panel_y + scale_y(26)
        row_h = scale_y(20)
        _INFRA_CATS = {"cockpit", "engine", "fuel", "reactor", "crew_quarters"}
        all_mins_met = True
        prev_was_infra = True  # Track section transitions

        for label, cat, needed, cap in requirements:
            # Section headers (only for slot-based builds with reqs)
            is_infra = cat in _INFRA_CATS
            if self.build.placed_slots and reqs and prev_was_infra and not is_infra:
                # Draw equipment section divider
                pygame.draw.line(
                    screen,
                    _BUILDER_COLORS["panel_dim_button"],
                    (panel_x + 8, row_y),
                    (panel_x + panel_w - 8, row_y),
                    1,
                )
                row_y += scale_y(4)
            prev_was_infra = is_infra

            count = cat_counts.get(cat, 0)
            met = count >= needed if needed > 0 else True
            if needed > 0 and not met:
                all_mins_met = False
            at_cap = count >= cap
            check = "\u2713" if met else "\u2717"
            check_color = Colors.GREEN if met else _BUILDER_COLORS["invalid_preview"]
            if at_cap and met:
                check_color = _BUILDER_COLORS["warn_at_cap"]  # Yellow when at cap
            label_color = Colors.TEXT_PRIMARY if met else Colors.TEXT_SECONDARY

            check_surf = self.small_font.render(check, True, check_color)
            screen.blit(check_surf, (panel_x + 8, row_y))
            name_surf = self.label_font.render(label, True, label_color)
            screen.blit(name_surf, (panel_x + 26, row_y + 3))
            if cap >= 99:
                count_text = f"{count}"
            elif needed > 0 and needed < cap:
                count_text = f"{count}/{needed}-{cap}"
            elif needed > 0:
                # min == max (e.g., cockpit 1/1) — no range needed
                count_text = f"{count}/{cap}"
            else:
                count_text = f"{count}/{cap}"
            count_surf = self.label_font.render(count_text, True, check_color)
            screen.blit(count_surf, (panel_x + panel_w - count_surf.get_width() - 8, row_y + 3))
            row_y += row_h

        # Flight readiness indicator (slot-based builds only)
        if self.build.placed_slots and reqs:
            row_y += scale_y(4)
            if all_mins_met:
                ready_text = "\u2713 FLIGHT READY"
                ready_color = Colors.GREEN
            else:
                ready_text = "\u2717 NOT FLIGHT READY"
                ready_color = _BUILDER_COLORS["invalid_preview"]
            ready_surf = self.label_font.render(ready_text, True, ready_color)
            screen.blit(ready_surf, (panel_x + 8, row_y))
            row_y += scale_y(14)

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
            # Simple BFS connectivity check on hull pixels
            coords = {(p.x, p.y) for p in all_pixels}
            start = next(iter(coords))
            visited: set[tuple[int, int]] = set()
            queue = [start]
            visited.add(start)
            while queue:
                cx, cy = queue.pop()
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in coords and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            conn_ok = len(visited) == len(coords)
            conn_check = "\u2713" if conn_ok else "\u2717"
            conn_color = Colors.GREEN if conn_ok else _BUILDER_COLORS["invalid_preview"]
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

        # Flow guide: remind player of the 3-step process
        if self.build.placed_slots:
            row_y += scale_y(14)
            flow_lines = [
                ("1. Place slots here (Drydock)", Colors.TEXT_SECONDARY),
                ("2. Buy parts (Shop tab)", Colors.TEXT_SECONDARY),
                ("3. Equip parts (Loadout tab)", Colors.TEXT_SECONDARY),
            ]
            for flow_text, flow_color in flow_lines:
                flow_surf = self.label_font.render(flow_text, True, flow_color)
                screen.blit(flow_surf, (panel_x + 8, row_y))
                row_y += scale_y(12)

        # Module rotation/flip indicator
        row_y += scale_y(8)
        rot_label = self.label_font.render(
            f"[R] Rot: {self._module_rotation * 90}\u00b0  [Q] Flip: {'Y' if self._module_flipped else 'N'}",
            True,
            _BUILDER_COLORS["label_mute_warm_soft"],
        )
        screen.blit(rot_label, (panel_x + 8, row_y))

        # Overlay toggle buttons (Phase 6)
        row_y += scale_y(20)
        overlay_label = self.label_font.render("OVERLAYS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(overlay_label, (panel_x + 8, row_y))
        row_y += scale_y(14)

        # Integrity overlay toggle
        int_active = self._show_integrity_overlay
        int_bg = _BUILDER_COLORS["cell_section_active"] if int_active else _BUILDER_COLORS["cell_alt"]
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
        com_bg = _BUILDER_COLORS["cell_section_active"] if com_active else _BUILDER_COLORS["cell_alt"]
        com_rect = pygame.Rect(panel_x + 6, row_y, panel_w - 12, scale_y(16))
        pygame.draw.rect(screen, com_bg, com_rect, border_radius=2)
        com_label = self.label_font.render(
            f"{'[x]' if com_active else '[ ]'} Center of Mass",
            True,
            Colors.GREEN if com_active else Colors.TEXT_SECONDARY,
        )
        screen.blit(com_label, (panel_x + 10, row_y + 2))
        self._com_toggle_rect = com_rect

        row_y += scale_y(18)

        # Exposure overlay toggle (BP4)
        exp_active = self._show_exposure_overlay
        exp_bg = _BUILDER_COLORS["cell_section_active"] if exp_active else _BUILDER_COLORS["cell_alt"]
        exp_rect = pygame.Rect(panel_x + 6, row_y, panel_w - 12, scale_y(16))
        pygame.draw.rect(screen, exp_bg, exp_rect, border_radius=2)
        exp_label = self.label_font.render(
            f"{'[x]' if exp_active else '[ ]'} Combat Exposure",
            True,
            Colors.GREEN if exp_active else Colors.TEXT_SECONDARY,
        )
        screen.blit(exp_label, (panel_x + 10, row_y + 2))
        self._exposure_toggle_rect = exp_rect

    # EQUIP mode removed — equipment assignment lives in the Loadout tab (Phase S4)

    def _render_recolor_panel(self, screen: pygame.Surface) -> None:
        """Render the recolor material selection panel (right side, module recolor mode)."""
        panel_x = MATERIAL_PANEL_X
        panel_y = MATERIAL_PANEL_Y
        panel_w = MATERIAL_PANEL_W
        panel_h = scale_y(300)
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        # Title
        title = self.small_font.render("RECOLOR [C]", True, _BUILDER_COLORS["recolor_accent"])
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
            bg = _BUILDER_COLORS["cell_selected_bright"] if is_selected else Colors.UI_PANEL
            pygame.draw.rect(screen, bg, (panel_x + 4, sy, panel_w - 8, swatch_h), border_radius=3)
            if is_selected:
                pygame.draw.rect(
                    screen,
                    _BUILDER_COLORS["recolor_accent"],
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
        lock_hint = self.label_font.render("Functional pixels (glass,", True, _BUILDER_COLORS["lock_hint"])
        screen.blit(lock_hint, (panel_x + 8, lock_y))
        lock_hint2 = self.label_font.render("exhaust, etc.) are locked.", True, _BUILDER_COLORS["lock_hint"])
        screen.blit(lock_hint2, (panel_x + 8, lock_y + scale_y(12)))

        # Exit hint
        exit_y = lock_y + scale_y(30)
        exit_hint = self.label_font.render("Press [C] to exit recolor", True, _BUILDER_COLORS["label_mute_warm_soft"])
        screen.blit(exit_hint, (panel_x + 8, exit_y))

    def _render_module_tooltip(self, screen: pygame.Surface) -> None:
        """Legacy module tooltip (removed). Slot tooltips handled separately."""

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

        if offset_pct == 0.0 and not self.build.pixels:
            return

        # Draw crosshair at CoM position
        cx = int(ox + com_x * cell + cell // 2)
        cy = int(oy + com_y * cell + cell // 2)

        # Color based on balance rating
        from spacegame.models.ship_physics import BalanceRating

        if rating == BalanceRating.BALANCED:
            color = _BUILDER_COLORS["weight_safe"]
        elif rating == BalanceRating.OFF_BALANCE:
            color = Colors.YELLOW
        else:
            color = _BUILDER_COLORS["invalid_place"]

        # Crosshair lines
        arm_len = max(8, cell * 2)
        pygame.draw.line(screen, color, (cx - arm_len, cy), (cx + arm_len, cy), 2)
        pygame.draw.line(screen, color, (cx, cy - arm_len), (cx, cy + arm_len), 2)
        # Center dot
        pygame.draw.circle(screen, color, (cx, cy), 3)

        # Label
        label = self.label_font.render(f"CoM {offset_pct:.0f}%", True, color)
        screen.blit(label, (cx + arm_len + 4, cy - 6))

    def _compute_exposure(self, cw: int, ch: int) -> dict[tuple[int, int], float]:
        """Compute per-cell combat exposure scores.

        Exposure is based on:
        - Column position: bow (right) is more exposed, stern (left) is safer
        - Edge proximity: cells on the silhouette edge are more vulnerable
        - Neighbor density: isolated cells are more exposed than interior ones

        Returns:
            Dict mapping (x, y) -> exposure score (0.0 safe to 1.0 exposed).
        """
        from spacegame.models.ship_module import resolve_all_pixels

        catalog = self._get_module_catalog()
        all_pixels = resolve_all_pixels(self.build, catalog)

        # Also include slot footprint cells
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        slot_cells: set[tuple[int, int]] = set()
        for ps in self.build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            fw, fh, r_mask = sdef.get_rotated(ps.rotation)
            for ly in range(fh):
                for lx in range(fw):
                    if r_mask:
                        if ly < len(r_mask) and lx < len(r_mask[ly]) and r_mask[ly][lx] == "X":
                            slot_cells.add((ps.x + lx, ps.y + ly))
                    else:
                        slot_cells.add((ps.x + lx, ps.y + ly))

        filled: set[tuple[int, int]] = {(p.x, p.y) for p in all_pixels} | slot_cells
        if not filled:
            return {}

        # Find bounding box for normalization
        min_x = min(x for x, _ in filled)
        max_x = max(x for x, _ in filled)
        x_range = max(1, max_x - min_x)

        exposure: dict[tuple[int, int], float] = {}
        for x, y in filled:
            # Factor 1: Column position (0 at stern/left, 1 at bow/right)
            col_factor = (x - min_x) / x_range

            # Factor 2: Edge proximity — count filled neighbors in 8 directions
            neighbor_count = 0
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    if (x + dx, y + dy) in filled:
                        neighbor_count += 1
            # 8 neighbors = fully interior (0.0), 0 neighbors = fully exposed (1.0)
            edge_factor = 1.0 - (neighbor_count / 8.0)

            # Combine: 60% column position + 40% edge proximity
            score = 0.6 * col_factor + 0.4 * edge_factor
            exposure[(x, y)] = min(1.0, score)

        return exposure

    def _render_exposure_overlay(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        cell: int,
        cw: int,
        ch: int,
    ) -> None:
        """Render combat exposure heat map over ship cells."""
        if self._cached_exposure is None:
            self._cached_exposure = self._compute_exposure(cw, ch)

        for (x, y), score in self._cached_exposure.items():
            px = ox + x * cell
            py = oy + y * cell
            # Color gradient: green (safe) -> yellow -> red (exposed)
            if score >= 0.6:
                # Red zone
                t = min(1.0, (score - 0.6) / 0.4)
                r, g, b = int(200 + 55 * t), int(100 * (1 - t)), 30
            elif score >= 0.3:
                # Yellow zone
                t = (score - 0.3) / 0.3
                r, g, b = int(100 + 155 * t), int(200 - 100 * t), 30
            else:
                # Green zone
                t = score / 0.3
                r, g, b = int(50 + 50 * t), int(180 + 20 * t), int(80 - 50 * t)
            alpha = int(40 + 60 * score)  # More exposed = more visible
            overlay = pygame.Surface((cell - 1, cell - 1), pygame.SRCALPHA)
            overlay.fill((r, g, b, alpha))
            screen.blit(overlay, (px + 1, py + 1))

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
            ("Shields", str(stats.shields), _BUILDER_COLORS["stat_shield"]),
            ("Armor", str(stats.armor), _BUILDER_COLORS["stat_armor"]),
            ("Evasion", str(stats.evasion), _BUILDER_COLORS["stat_evasion"]),
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
                Colors.GOLD if hasattr(Colors, "GOLD") else _BUILDER_COLORS["stat_gold_fallback"],
            ),
            ("Pixels", str(len(self.build.pixels)), Colors.TEXT_SECONDARY),
        ]
        for i, (label, value, color) in enumerate(eco_items):
            lx = x_start + i * col_w
            lbl = self.tiny_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            val = self.tiny_font.render(value, True, color)
            screen.blit(lbl, (lx, y))
            screen.blit(val, (lx + lbl.get_width() + 4, y))

        y += scale_y(22)

        # Row 3: Energy economy (B5) — builder-visible combat budget.
        eco = compute_energy_economy(self.build, self.data_loader)
        ok_color = _BUILDER_COLORS["tier_ok"]
        warn_color = _BUILDER_COLORS["tier_warn"]
        alpha_color = ok_color if eco.can_alpha_strike else warn_color
        energy_items = [
            ("Energy", f"{eco.pool} pool", Colors.TEXT_PRIMARY),
            ("Regen", f"{eco.regen}/turn", Colors.TEXT_PRIMARY),
            ("Sidearms", str(eco.sidearm_count), Colors.TEXT_PRIMARY),
            ("Tech", str(eco.tech_count), Colors.TEXT_PRIMARY),
            ("Burst", str(eco.burst_count), Colors.TEXT_PRIMARY),
            (
                "Alpha",
                f"{eco.total_alpha_cost}/{eco.pool}" if eco.total_weapons else "--",
                alpha_color,
            ),
        ]
        for i, (label, value, color) in enumerate(energy_items):
            lx = x_start + i * col_w
            lbl = self.tiny_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            val = self.tiny_font.render(value, True, color)
            screen.blit(lbl, (lx, y))
            screen.blit(val, (lx + lbl.get_width() + 4, y))

        # First advisory, if any, rendered inline after the energy row.
        if eco.advisories:
            advisory_text = eco.advisories[0]
            if len(eco.advisories) > 1:
                advisory_text += f"  (+{len(eco.advisories) - 1} more)"
            adv_surf = self.tiny_font.render(advisory_text, True, warn_color)
            adv_x = x_start + len(energy_items) * col_w + scale_x(8)
            screen.blit(adv_surf, (adv_x, y))

        y += scale_y(24)

        # Weight bar
        bar_w = scale_x(300)
        weight_color = _BUILDER_COLORS["weight_green"]  # Green
        if stats.weight_ratio > 0.80:
            weight_color = _BUILDER_COLORS["tier_warn"]  # Orange
        if stats.weight_ratio > 0.95:
            weight_color = _BUILDER_COLORS["weight_over"]  # Red
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
                "juggernaut": _BUILDER_COLORS["stat_armor"],
                "sentinel": _BUILDER_COLORS["stat_shield"],
                "ghost": _BUILDER_COLORS["stat_evasion"],
            }
            id_color = id_colors.get(stats.defensive_identity, Colors.TEXT_SECONDARY)
            id_text = self.tiny_font.render(
                f"Identity: {stats.defensive_identity.upper()}",
                True,
                id_color,
            )
            screen.blit(id_text, (x_start, y))

        # Build rating (BP3) — rendered on Row 3 (below weight bar), right-aligned
        has_slots = len(self.build.placed_slots) > 0
        if has_slots or len(self.build.pixels) > 20:
            from spacegame.models.build_rating import compute_build_rating

            slot_defs = getattr(self.data_loader, "slot_definitions", {})
            parts_cat = getattr(self.data_loader, "ship_parts", {})
            ratings = compute_build_rating(self.build, slot_defs, parts_cat)

            grade_colors = {
                "S": _BUILDER_COLORS["grade_s"],
                "A": _BUILDER_COLORS["grade_a"],
                "B": _BUILDER_COLORS["grade_b"],
                "C": _BUILDER_COLORS["grade_c"],
                "D": _BUILDER_COLORS["grade_d"],
                "F": _BUILDER_COLORS["grade_f"],
            }
            # Place ratings on the weight bar row, right of the weight label
            rating_x = x_start + scale_x(500)
            rating_y = y - BAR_H - 6  # Same Y as weight bar
            for axis_name in ("combat", "trade", "mobility", "durability"):
                grade, _score, _feedback = ratings[axis_name]
                gc = grade_colors.get(grade, Colors.TEXT_SECONDARY)
                r_surf = self.label_font.render(f"{axis_name.title()}: {grade}", True, gc)
                screen.blit(r_surf, (rating_x, rating_y))
                rating_x += scale_x(90)

        # Guidance hint — single line integrated into the identity row
        if has_slots and stats.speed == 0 and stats.fuel_capacity == 0 and stats.shields == 0:
            hint_surf = self.label_font.render(
                "Place slots, then buy & equip parts via Shop + Loadout tabs",
                True,
                _BUILDER_COLORS["stat_tier_ring"],
            )
            screen.blit(hint_surf, (x_start + scale_x(200), y))

        # Tool bar (right side of stats panel)
        tool_x = WINDOW_WIDTH - scale_x(420)
        tool_y = STATS_PANEL_Y + 6
        btn_w = scale_x(65)
        btn_h = scale_y(28)
        btn_gap = scale_x(4)

        def _draw_tool_btn(
            bx: int, by: int, w: int, label: str, active: bool, enabled: bool = True
        ) -> None:
            bg = _BUILDER_COLORS["toolbar_active"] if active else (_BUILDER_COLORS["toolbar_enabled"] if enabled else _BUILDER_COLORS["toolbar_disabled"])
            border = (
                Colors.TEXT_HIGHLIGHT if active else (_BUILDER_COLORS["border_toolbar_enabled"] if enabled else _BUILDER_COLORS["border_toolbar_disabled"])
            )
            pygame.draw.rect(screen, bg, (bx, by, w, btn_h), border_radius=4)
            pygame.draw.rect(screen, border, (bx, by, w, btn_h), 1, border_radius=4)
            color = (
                Colors.TEXT_PRIMARY
                if active
                else (Colors.TEXT_SECONDARY if enabled else _BUILDER_COLORS["text_toolbar_disabled"])
            )
            t = self.small_font.render(label, True, color)
            screen.blit(
                t, (bx + w // 2 - t.get_width() // 2, by + btn_h // 2 - t.get_height() // 2)
            )

        if self._builder_mode == "hull":
            # Hull mode tools — row 1
            tools = [
                ("stamp", "S", "Stamp"),
                ("pencil", "P", "Pencil"),
                ("brush", "M", "Brush"),
                ("fill", "F", "Fill"),
                ("eraser", "E", "Erase"),
                (None, "X", "Mirror"),
            ]
            for i, (tool_id, key, label) in enumerate(tools):
                bx = tool_x + i * (btn_w + btn_gap)
                if tool_id is None:
                    # Mirror toggle
                    is_active = self._mirror_mode
                else:
                    is_active = self._active_tool == tool_id
                _draw_tool_btn(bx, tool_y, btn_w, f"{key} {label}", is_active)

        # Row 2: Undo, Redo, Rotate, Flip, Zoom
        tool_y += btn_h + scale_y(4)
        cx = tool_x

        # Undo
        has_undo = len(self._undo_stack) > 0
        _draw_tool_btn(cx, tool_y, btn_w, f"Undo ({len(self._undo_stack)})", False, has_undo)
        cx += btn_w + btn_gap

        # Redo
        has_redo = len(self._redo_stack) > 0
        _draw_tool_btn(cx, tool_y, btn_w, f"Redo ({len(self._redo_stack)})", False, has_redo)
        cx += btn_w + btn_gap

        # Rotate
        if self._builder_mode == "slot":
            rot_deg = self._module_rotation * 90
            is_flipped = self._module_flipped
        else:
            rot_deg = self._shape_rotation * 90
            is_flipped = self._shape_flipped
        _draw_tool_btn(cx, tool_y, btn_w, f"R {rot_deg}\u00b0", False, True)
        cx += btn_w + btn_gap

        # Flip
        _draw_tool_btn(cx, tool_y, btn_w, f"Flip {'Y' if is_flipped else 'N'}", is_flipped, True)
        cx += btn_w + btn_gap

        # Zoom
        zoom_pct = int(self._zoom_level * 100)
        _draw_tool_btn(cx, tool_y, btn_w, f"Zoom {zoom_pct}%", False, True)

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

    def _render_tutorial_narration(self, screen: pygame.Surface) -> None:
        """Render step-by-step mechanic narration for the tutorial build.

        State machine (PT-007 playtest response):
          1. Welcome — fires if no parts are placed yet
          2. Per-part prompts — one narration per unplaced-but-bought part
          3. Rotation tip — fires once a 1x2 module is selected, before it's placed
          4. Completion — fires when all bought parts are placed; points to
             the CONFIRM BUILD button explicitly so the player does not
             have to hunt for the exit (addresses PT-006).
        """
        from spacegame.engine.draw_utils import draw_panel

        # Per-part narration — each line is the mechanic pointing at the
        # next thing to place, in working-class register.
        _PART_NARRATION = {
            "cockpit_scout_pod": "Cockpit first. Select it on the left, place it on the grid.",
            "engine_small": "Engine next. Nothing leaves this bay without thrust.",
            "reactor_small": "Reactor in the core. Powers everything you've got.",
            "fuel_small": "Fuel tank. No fuel, no jumps. Simple.",
            "cargo_small": "Cargo bay. Somewhere to stash whatever pays the bills.",
            "weapon_small": "Weapon mount. At least you won't fly unarmed.",
        }

        placed_ids = {ps.slot_def_id for ps in self.build.placed_slots}
        from spacegame.views.tutorial_shop_view import TUTORIAL_PARTS

        # Narration selection in priority order.
        narration = self._pick_tutorial_narration(placed_ids, _PART_NARRATION, TUTORIAL_PARTS)

        # Panel at bottom
        panel_w = WINDOW_WIDTH - scale_x(160)
        panel_h = scale_y(50)
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - panel_h - scale_y(10)

        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=220)
        speaker = self._tutorial_narration_font.render("Mechanic: ", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(speaker, (panel_x + 16, panel_y + 14))
        text = self._tutorial_narration_font.render(narration, True, Colors.TEXT_PRIMARY)
        screen.blit(text, (panel_x + 16 + speaker.get_width(), panel_y + 14))

    def _pick_tutorial_narration(
        self,
        placed_ids: set[str],
        part_narration: dict[str, str],
        tutorial_parts: list,  # list[TutorialPart] — avoid import cycle
    ) -> str:
        """Pick the current mechanic line based on build progress.

        Priority (highest → lowest):
          1. Welcome (no parts placed, no modules selected yet)
          2. Rotation tip (a tall module is selected but not placed)
          3. Per-part placement prompt (parts bought but unplaced)
          4. Completion (all bought parts placed — point at CONFIRM BUILD)
        """
        # SI-1a/b: TUTORIAL_PARTS is now list[TutorialPart] (attribute access,
        # not dict subscript), and the flag name goes through the registry so
        # shop-set / builder-read can't drift apart.
        from spacegame.constants.flags import tutorial_bought_part

        bought_parts = [
            p
            for p in tutorial_parts
            if self.player.dialogue_flags.get(tutorial_bought_part(p.part_id))
        ]

        # 1. Welcome: nothing bought is placed yet AND nothing selected.
        if bought_parts and not placed_ids and not self._selected_slot_def_id:
            return (
                "Bay's yours. Pick a part from the list, drop it on the grid. "
                "We don't waste space if we can help it."
            )

        # 2. Rotation tip: a selected module's rotated orientation would help.
        # Fires when the player has selected a non-square slot but hasn't
        # yet rotated it this session. Discoverability of the R key is
        # the single most reported friction point.
        slot_defs = getattr(self.data_loader, "slot_definitions", {}) or {}
        if self._selected_slot_def_id and not getattr(self, "_shown_rotation_tip", False):
            sel_def = slot_defs.get(self._selected_slot_def_id)
            if sel_def and sel_def.footprint_w != sel_def.footprint_h:
                return "Tall module? Press R to rotate before you drop it."

        # 3. Per-part prompt: first bought part whose slot_type hasn't been
        # placed yet. Bought parts carry part_id; we look up the
        # corresponding slot_type from ship_parts, then find the matching
        # narration line keyed by tutorial slot_def_id.
        ship_parts = getattr(self.data_loader, "ship_parts", {}) or {}
        placed_slot_types = {
            slot_defs[sid].slot_type
            for sid in placed_ids
            if sid in slot_defs
        }
        for p in bought_parts:
            part = ship_parts.get(p.part_id)
            if part is None:
                continue
            if part.slot_type in placed_slot_types:
                continue
            # Find a part_narration entry whose slot_def matches this slot_type
            for narration_sd_id, narration_text in part_narration.items():
                narration_sd = slot_defs.get(narration_sd_id)
                if narration_sd and narration_sd.slot_type == part.slot_type:
                    return narration_text
            return "Place the next part."

        # 4. Completion: all bought parts placed. Point at the exit.
        return (
            "That'll fly. Your father would've spent another hour second-guessing. "
            "Hit CONFIRM BUILD, bottom-right, when you're ready."
        )

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
        title = self.header_font.render("Ship Builder Controls", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (px + scale_x(20), py + scale_y(10)))

        y = py + scale_y(45)
        line_h = scale_y(20)

        help_lines = [
            ("BUILDING", Colors.TEXT_HIGHLIGHT),
            ("  Left-click: Place shape / Use tool", Colors.TEXT_PRIMARY),
            ("  Right-click: Erase pixel / Remove module", Colors.TEXT_PRIMARY),
            ("  [R] Rotate shape 90°    [Q] Flip    [V] Cycle variant", Colors.TEXT_PRIMARY),
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
                _BUILDER_COLORS["stat_shield"] if shield_delta > 0 else Colors.TEXT_SECONDARY,
            ),
            (f"+{weight_delta:.1f} Weight", Colors.YELLOW),
            (f"+{cost_delta} CR", Colors.TEXT_SECONDARY),
        ]
        if armor_delta > 0:
            deltas.insert(1, (f"+{armor_delta:.2f} Armor", _BUILDER_COLORS["stat_armor"]))
        if evasion_delta > 0:
            deltas.insert(2, (f"+{evasion_delta:.2f} Evasion", _BUILDER_COLORS["stat_evasion"]))

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
        pygame.draw.rect(screen, _BUILDER_COLORS["input_bg_dim"], input_rect, border_radius=3)
        pygame.draw.rect(screen, Colors.UI_BORDER, input_rect, 1, border_radius=3)

        # Display text (truncated if too long)
        display_text = self._import_text
        if len(display_text) > 60:
            display_text = display_text[:57] + "..."
        if display_text:
            text_surf = self.label_font.render(display_text, True, Colors.TEXT_PRIMARY)
        else:
            text_surf = self.label_font.render("Paste code here...", True, _BUILDER_COLORS["text_placeholder"])
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
            err_surf = self.label_font.render(self._import_error, True, _BUILDER_COLORS["import_error"])
            screen.blit(err_surf, (mx + 15, input_y + input_h + 8))

        # Missing blueprints list
        if self._import_missing_blueprints:
            bp_y = input_y + input_h + scale_y(28)
            header = self.label_font.render("Missing Blueprints:", True, _BUILDER_COLORS["import_warn_header"])
            screen.blit(header, (mx + 15, bp_y))
            bp_y += scale_y(14)
            for bp in self._import_missing_blueprints[:5]:
                method = bp.get("unlock_method", "").replace("_", " ").title()
                line = f"\u2717 {bp['name']} ({bp['category']}) - {method}"
                if bp.get("unlock_source"):
                    line += f": {bp['unlock_source'].replace('_', ' ').title()}"
                bp_surf = self.label_font.render(line, True, _BUILDER_COLORS["import_warn_line"])
                screen.blit(bp_surf, (mx + 20, bp_y))
                bp_y += scale_y(13)
            if len(self._import_missing_blueprints) > 5:
                more = self.label_font.render(
                    f"... and {len(self._import_missing_blueprints) - 5} more",
                    True,
                    _BUILDER_COLORS["import_warn_dim"],
                )
                screen.blit(more, (mx + 20, bp_y))

        # Buttons hint
        hint_y = my + modal_h - scale_y(22)
        hint = self.label_font.render(
            "[Enter] Import    [Esc] Cancel    [Ctrl+V] Paste", True, _BUILDER_COLORS["label_mute_cool"]
        )
        screen.blit(hint, (mx + 15, hint_y))

    # ------------------------------------------------------------------
    # Ship Naming Dialog (BP2)
    # ------------------------------------------------------------------

    def _handle_naming_event(self, event: pygame.event.Event) -> None:
        """Handle input while the ship naming dialog is active."""
        if event.type == pygame.KEYDOWN:
            # PT-012: accept both main Enter and numpad Enter. Playtest
            # report "press Enter didn't work" is consistent with a numpad
            # user whose keyboard sends K_KP_ENTER instead of K_RETURN.
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                # PT-012: rename-only path saves the name and closes; build
                # finalize stays gated behind the CONFIRM BUILD button.
                if getattr(self, "_rename_only", False):
                    new_name = self._naming_text.strip()
                    if new_name:
                        self.player.ship_name = new_name
                    self._naming_active = False
                    self._rename_only = False
                else:
                    self._finalize_build()
            elif event.key == pygame.K_ESCAPE:
                self._naming_active = False
                self._rename_only = False
            elif event.key == pygame.K_BACKSPACE:
                self._naming_text = self._naming_text[:-1]
            else:
                char = event.unicode
                if char and len(self._naming_text) < 24 and char.isprintable():
                    self._naming_text += char

    def _render_naming_dialog(self, screen: pygame.Surface) -> None:
        """Render the ship naming overlay."""
        # Dim background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        screen.blit(dim, (0, 0))

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # Panel
        pw, ph = scale_x(440), scale_y(180)
        panel = pygame.Rect(cx - pw // 2, cy - ph // 2, pw, ph)
        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((12, 16, 32, 245))
        screen.blit(panel_surf, panel.topleft)
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, panel, 2, border_radius=8)

        # Title
        title = self.small_font.render("Name Your Ship", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(centerx=cx, top=panel.top + scale_y(16)))

        # Text input field
        field_w = pw - scale_x(60)
        field_h = scale_y(32)
        field_x = cx - field_w // 2
        field_y = panel.top + scale_y(60)
        pygame.draw.rect(
            screen, Colors.UI_PANEL, (field_x, field_y, field_w, field_h), border_radius=4
        )
        pygame.draw.rect(
            screen, Colors.TEXT_HIGHLIGHT, (field_x, field_y, field_w, field_h), 1, border_radius=4
        )

        # Text + blinking cursor
        display_text = self._naming_text
        self._naming_cursor_timer += 0.016  # ~60fps
        show_cursor = int(self._naming_cursor_timer * 2) % 2 == 0
        if show_cursor:
            display_text += "|"
        text_surf = self.small_font.render(display_text, True, Colors.TEXT_PRIMARY)
        screen.blit(
            text_surf, (field_x + scale_x(8), field_y + (field_h - text_surf.get_height()) // 2)
        )

        # Hint
        hint = self.label_font.render(
            "[Enter] Confirm    [Esc] Cancel", True, Colors.TEXT_SECONDARY
        )
        screen.blit(hint, hint.get_rect(centerx=cx, top=panel.top + scale_y(110)))

        # Subtitle
        sub = self.label_font.render(
            "Leave blank to use the frame name", True, Colors.TEXT_SECONDARY
        )
        screen.blit(sub, sub.get_rect(centerx=cx, top=panel.top + scale_y(140)))

    # ------------------------------------------------------------------
    # Live Ship Preview (BP1)
    # ------------------------------------------------------------------

    def _build_preview_surface(self) -> Optional[pygame.Surface]:
        """Build a small ship preview surface from the current build.

        Renders hull pixels with material colors and placed slots with
        type colors onto a canvas-sized surface. Returns None if the
        build has no content.
        """
        cw, ch = self.build.canvas_w, self.build.canvas_h
        if cw <= 0 or ch <= 0:
            return None

        has_content = self.build.pixels or self.build.placed_slots
        if not has_content:
            return None

        surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
        surf.fill((12, 16, 28, 200))  # Dark background so the ship reads clearly

        # Hull pixels — material colored
        materials = getattr(self.data_loader, "hull_materials", {})
        for pixel in self.build.pixels:
            mat = materials.get(pixel.material_id)
            if mat and 0 <= pixel.x < cw and 0 <= pixel.y < ch:
                color = getattr(mat, "color_primary", _BUILDER_COLORS["material_fallback_light"])
                surf.set_at((pixel.x, pixel.y), (*color, 255))

        # Placed slots — type colored fills
        slot_defs = getattr(self.data_loader, "slot_definitions", {})
        for ps in self.build.placed_slots:
            sdef = slot_defs.get(ps.slot_def_id)
            if not sdef:
                continue
            fw, fh, r_mask = sdef.get_rotated(ps.rotation)
            for ly in range(fh):
                for lx in range(fw):
                    px = ps.x + lx
                    py = ps.y + ly
                    if 0 <= px < cw and 0 <= py < ch:
                        if r_mask:
                            if ly < len(r_mask) and lx < len(r_mask[ly]) and r_mask[ly][lx] == "X":
                                surf.set_at((px, py), (*sdef.color, 220))
                        else:
                            surf.set_at((px, py), (*sdef.color, 220))

        return surf

    def _render_ship_preview(self, screen: pygame.Surface) -> None:
        """Render the live ship preview as a floating thumbnail in the grid corner."""
        # Rebuild if dirty
        if self._preview_dirty:
            self._preview_surface = self._build_preview_surface()
            self._preview_dirty = False

        if self._preview_surface is None:
            return

        # Fixed preview size — small, unobtrusive, in bottom-right of grid area
        preview_max_w = scale_x(100)
        preview_max_h = scale_y(80)

        # Scale the preview to fit, maintaining aspect ratio
        src_w, src_h = self._preview_surface.get_size()
        if src_w <= 0 or src_h <= 0:
            return
        scale_factor = min(preview_max_w / src_w, preview_max_h / src_h, 3.0)
        display_w = max(1, int(src_w * scale_factor))
        display_h = max(1, int(src_h * scale_factor))

        scaled = pygame.transform.scale(self._preview_surface, (display_w, display_h))

        # Position: bottom-right corner of the grid area, above the stats panel
        preview_x = GRID_AREA_X + GRID_AREA_W - display_w - scale_x(8)
        preview_y = STATS_PANEL_Y - display_h - scale_y(8)

        # Panel background
        pad = scale_x(4)
        panel_rect = pygame.Rect(
            preview_x - pad,
            preview_y - scale_y(12) - pad,
            display_w + pad * 2,
            display_h + scale_y(12) + pad * 2,
        )
        panel_bg = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel_bg.fill((10, 14, 25, 200))
        screen.blit(panel_bg, panel_rect.topleft)
        pygame.draw.rect(screen, _BUILDER_COLORS["panel_bg_soft"], panel_rect, 1, border_radius=4)

        # Label
        label = self.label_font.render("PREVIEW", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(label, (preview_x, preview_y - scale_y(14)))

        # Ship preview with thin border
        screen.blit(scaled, (preview_x, preview_y))
        pygame.draw.rect(
            screen,
            _BUILDER_COLORS["panel_divider"],
            (preview_x - 1, preview_y - 1, display_w + 2, display_h + 2),
            1,
        )

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
            text = self.header_font.render("BUILD CONFIRMED", True, _BUILDER_COLORS["build_confirm"])
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
