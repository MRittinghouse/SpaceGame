"""
Salvage operations mini-game view.

Grid-based scanning and extraction puzzle.
Features scan pulse particles, cell reveal fade, metallic hidden cells, and extraction sparks.
"""

import math
import random
from typing import Dict, List, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar, draw_nine_slice_panel, draw_summary_overlay
from spacegame.engine.floating_text import FloatingItemManager
from spacegame.engine.fonts import (
    FONT_HEADING,
    FONT_LG,
    FONT_MD,
    FONT_RATING,
    FONT_SECTION2,
    FONT_SM,
    FONT_TITLE,
    FONT_XL,
    FONT_XS,
    get_font,
)
from spacegame.engine.particles import (
    COLLECT_SPARKLE,
    CORRUPTION_CRACKLE,
    EXTRACTION_SPARK,
    SCAN_RIPPLE,
    ParticlePool,
)
from spacegame.engine.salvage_vfx import (
    CorruptionOverlay,
    DeckTransition,
    ModeOverlay,
    QualityBurst,
    SalvageAtmosphere,
    SalvageDeckMeter,
    ScanPulse,
)
from spacegame.engine.sprites import get_sprite_manager, res_scale
from spacegame.engine.tooltip import TooltipState
from spacegame.models.commodity import Commodity
from spacegame.models.player import Player
from spacegame.models.rating import RATING_COLORS, SALVAGE_THRESHOLDS, calculate_rating
from spacegame.models.salvage import (
    DERELICT_TYPES,
    SALVAGE_ITEM_CONFIGS,
    CellState,
    DerelictType,
    QualityTier,
    SalvageConfig,
    SalvageResult,
    SalvageSession,
)
from spacegame.models.salvage_hold import SalvageHold
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


class SalvageView(BaseView):
    """Salvage operations mini-game with visual effects."""

    CELL_SIZE = scale_y(90)
    CELL_PADDING = 4
    GRID_OFFSET_X = scale_x(60)
    GRID_OFFSET_Y = scale_y(120)

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        commodities: Dict[str, Commodity],
        salvage_config: Optional[SalvageConfig] = None,
        progression=None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.commodities = commodities
        self.progression = progression

        if salvage_config is None:
            salvage_config = SalvageConfig(system_id=player.current_system_id)
        self.salvage_config = salvage_config

        # VFX objects (synced with session state in on_enter / deck advance)
        grid_rect = pygame.Rect(
            self.GRID_OFFSET_X,
            self.GRID_OFFSET_Y,
            self.CELL_SIZE * 6,
            self.CELL_SIZE * 6,
        )
        self._vfx_atmosphere = SalvageAtmosphere(grid_rect)
        self._vfx_deck_meter = SalvageDeckMeter(
            x=WINDOW_WIDTH - scale_x(60),
            y=self.GRID_OFFSET_Y,
            height=self.CELL_SIZE * 5,
        )
        self._vfx_corruption = CorruptionOverlay(
            bar_x=self.GRID_OFFSET_X,
            bar_y=self.GRID_OFFSET_Y - scale_y(20),
            bar_w=self.CELL_SIZE * 6,
        )
        self._vfx_deck_trans = DeckTransition()
        self._scan_pulse = ScanPulse()
        self._quality_burst = QualityBurst()
        self._mode_overlay = ModeOverlay(grid_rect)

        self.session: Optional[SalvageSession] = None
        self.next_state: Optional[GameState] = None
        self.mode: str = "scan"
        self._selecting_derelict: bool = True  # Show selection before gameplay
        self._derelict_choice_rects: list[tuple[DerelictType, pygame.Rect]] = []

        # Salvage hold for current system (decoupled from ship cargo)
        self._hold: SalvageHold = self.player.salvage_hold_manager.get_hold(
            self.salvage_config.system_id
        )

        # Intel earned this session (for summary)
        self._session_intel: int = 0

        # Upgrade panel click rects
        self._upgrade_rects: Dict[str, pygame.Rect] = {}

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.info_font = get_font("dialogue", FONT_LG)
        self.small_font = get_font("stats", FONT_MD)
        self.cell_font = get_font("stats", FONT_SM)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.scan_button: Optional[pygame_gui.elements.UIButton] = None
        self.extract_button: Optional[pygame_gui.elements.UIButton] = None
        self.next_deck_button: Optional[pygame_gui.elements.UIButton] = None
        self.regen_button: Optional[pygame_gui.elements.UIButton] = None

        # Feedback
        self.feedback_messages: List[dict] = []
        self.message: str = ""
        self.message_timer: float = 0.0

        # Animated background
        self.background = AnimatedBackground("debris", WINDOW_WIDTH, WINDOW_HEIGHT, seed=60)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(100)

        # Particles
        self.particles = ParticlePool(200)

        # Cell reveal fade-in tracking
        self._reveal_timers: Dict[tuple, float] = {}  # (gx, gy) -> timer 0.0-0.2
        self._static_time = 0.0

        # Sprite manager
        self._sprite_mgr = get_sprite_manager()

        # Salvage commodity icons (commodity_id -> Surface at 3x = 48x48)
        self._item_icons: Dict[str, Optional[pygame.Surface]] = {}
        for config in SALVAGE_ITEM_CONFIGS.values():
            self._item_icons[config.commodity_id] = self._sprite_mgr.get_commodity_icon(
                config.commodity_id, scale=res_scale(3)
            )

        # Derelict background (loaded per-session in on_enter, scaled to grid)
        self._derelict_bg: Optional[pygame.Surface] = None

        # Cell state sprites (32x32 native, scaled to cell interior)
        self._cell_sprites: Dict[str, Optional[pygame.Surface]] = {}
        cell_scale = (self.CELL_SIZE - self.CELL_PADDING * 2) // 32  # ~2x
        for state_name in ("hidden", "scanned", "item", "extracted"):
            self._cell_sprites[state_name] = self._sprite_mgr.get_static_sprite(
                "salvage", f"salvage_cell_{state_name}", scale=cell_scale
            )

        # Quality frame sprites (20x20 native, scaled to fit cell)
        self._quality_frames: Dict[str, Optional[pygame.Surface]] = {}

        for tier in QualityTier:
            frame = self._sprite_mgr.get_static_sprite(
                "salvage", f"quality_frame_{tier.value}", scale=res_scale(4)
            )
            self._quality_frames[tier.value] = frame

        # Mode icon sprites (16x16 native at 2x = 32x32)
        self._mode_icons: Dict[str, Optional[pygame.Surface]] = {
            "scan": self._sprite_mgr.get_static_sprite(
                "salvage", "icon_scan_mode", scale=res_scale(2)
            ),
            "extract": self._sprite_mgr.get_static_sprite(
                "salvage", "icon_extract_mode", scale=res_scale(2)
            ),
        }

        # Corruption overlay surface (pre-allocated, reused each frame)
        self._corruption_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

        # Heartbeat flash surface (pre-allocated)
        self._heartbeat_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

        # Transfer count (for summary)
        self._transfer_count: int = 0

        # Session summary overlay
        self._show_summary: bool = False
        self._summary_xp: int = 0
        self._session_elapsed: float = 0.0
        self._session_rating: str = "D"
        self._summary_font = get_font("header", FONT_HEADING)
        self._summary_title_font = get_font("header", FONT_SECTION2)
        self._rating_font = get_font("header", FONT_RATING)

        # Floating icon manager for item-to-hold animations
        self._floats = FloatingItemManager()

        # Scan wave ripple: list of (cx, cy, radius, max_radius, speed)
        self._scan_waves: List[list] = []

        # EXCELLENT glow burst timer: (gx, gy) -> timer
        self._excellent_glow: Dict[tuple, float] = {}

        # Corruption heartbeat state
        self._heartbeat_flash: float = 0.0

        # Corruption wave: staggered cell flip queue [(gx, gy, delay)]
        self._corruption_wave: List[list] = []

        # Deck transition: staggered cell appear [(gx, gy, delay)]
        self._deck_transition: List[list] = []
        self._deck_transition_pending: set[tuple[int, int]] = set()  # O(1) lookup
        self._deck_transition_active: bool = False

        # Derelict stories (found narrative on scan)
        self._derelict_stories: Dict[str, list[str]] = {}
        self._load_derelict_stories()
        self._story_shown: set[int] = set()  # Track which stories shown this session
        self._story_text: str = ""
        self._story_timer: float = 0.0

        # Crew commentary (set by Game class after construction)
        self._get_crew_line = lambda action_type: None
        self._crew_comment: str = ""
        self._crew_comment_name: str = ""
        self._crew_comment_timer: float = 0.0

        # Tooltip for upgrade descriptions
        self._tooltip = TooltipState(delay=0.3, fade_in=0.15)

        # Exit confirmation state
        self._confirm_exit: bool = False

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered salvage operations")

        extract_bonus = 1.0
        extra_charges = 0
        extra_parallel = 0
        if self.progression:
            extract_bonus += self.progression.get_bonus("extract_speed")
            extra_charges = int(self.progression.get_bonus("extra_scan_charges"))
            # master_extractor level 3 (3 * 0.20 = 0.60) unlocks 3rd parallel slot
            if self.progression.get_bonus("extract_speed") >= 0.60:
                extra_parallel = 1

        # Apply ship upgrade bonuses (stacks with skill tree)
        extract_bonus += self.player.upgrade_manager.get_bonus("extract_speed_bonus")
        extra_charges += int(self.player.upgrade_manager.get_bonus("scan_charge_bonus"))
        self.salvage_config.perk_yield_bonus += self.player.upgrade_manager.get_bonus(
            "salvage_yield_bonus"
        )

        # Apply wreck upgrade bonuses
        from spacegame.data_loader import get_data_loader

        wreck_upgrades = get_data_loader().wreck_upgrades
        wu_state = self.player.wreck_upgrades
        extra_charges += int(wu_state.get_effect("signal_amplifier", wreck_upgrades))
        extract_bonus += wu_state.get_effect("quick_extract", wreck_upgrades)

        # Apply salvage buffer hold capacity bonus
        buffer_bonus = int(wu_state.get_effect("salvage_buffer", wreck_upgrades))
        if buffer_bonus > 0:
            self.player.salvage_hold_manager.upgrade_all_capacity(buffer_bonus)
            self._hold = self.player.salvage_hold_manager.get_hold(self.salvage_config.system_id)

        # Store bonuses for session creation after derelict selection
        self._extract_bonus = extract_bonus
        self._extra_charges = extra_charges
        self._extra_parallel = extra_parallel

        # Start in derelict selection mode
        self._selecting_derelict = True
        self._derelict_choice_rects = []
        self.session = None
        self._session_intel = 0
        self._reveal_timers.clear()
        self._story_shown.clear()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    # Derelict type -> background sprite ID
    DERELICT_BG_MAP: Dict[str, str] = {
        "cargo_bay": "derelict_cargo_bay",
        "lab_module": "derelict_lab_module",
        "engine_room": "derelict_engine_room",
    }

    # Derelict type -> theme accent color
    DERELICT_THEME: Dict[str, tuple] = {
        "cargo_bay": (140, 100, 60),  # Rust orange
        "lab_module": (60, 160, 140),  # Teal
        "engine_room": (180, 100, 50),  # Warning orange
    }

    def _load_derelict_background(self) -> None:
        """Load and scale derelict background sprite for the current session."""
        if not self.session:
            self._derelict_bg = None
            return
        bg_id = self.DERELICT_BG_MAP.get(self.session.derelict_type.id)
        if bg_id is None:
            self._derelict_bg = None
            return

        raw = self._sprite_mgr.get_static_sprite("salvage", bg_id, scale=res_scale(1))
        if raw is None:
            self._derelict_bg = None
            return

        # Scale to cover the grid area
        grid_size = self.session.derelict_type.grid_size
        grid_px_w = grid_size * self.CELL_SIZE
        grid_px_h = grid_size * self.CELL_SIZE
        self._derelict_bg = pygame.transform.scale(raw, (grid_px_w, grid_px_h))
        # Dim it so cell contents are readable
        dim = pygame.Surface((grid_px_w, grid_px_h))
        dim.fill((0, 0, 0))
        dim.set_alpha(160)
        self._derelict_bg.blit(dim, (0, 0))

    def _get_theme_color(self) -> tuple:
        """Get the accent color for the current derelict type."""
        if self.session:
            return self.DERELICT_THEME.get(self.session.derelict_type.id, Colors.TEXT_HIGHLIGHT)
        return Colors.TEXT_HIGHLIGHT

    def _create_ui(self) -> None:
        btn_x = WINDOW_WIDTH - scale_x(200)
        btn_w = scale_x(170)
        btn_h = scale_y(35)
        self.scan_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - scale_y(220), btn_w, btn_h),
            text="Scan Mode",
            manager=self.ui_manager,
        )
        self.extract_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - scale_y(180), btn_w, btn_h),
            text="Extract Mode",
            manager=self.ui_manager,
        )
        self.next_deck_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - scale_y(140), btn_w, btn_h),
            text="Next Deck",
            manager=self.ui_manager,
        )
        self.regen_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - scale_y(100), btn_w, btn_h),
            text="New Wreck",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - scale_y(60), btn_w, btn_h),
            text="Stop Salvaging",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for btn in [
            self.back_button,
            self.scan_button,
            self.extract_button,
            self.next_deck_button,
            self.regen_button,
        ]:
            if btn:
                btn.kill()

    def _get_grid_cell(self, mouse_pos: tuple) -> Optional[tuple]:
        mx, my = mouse_pos
        gx = (mx - self.GRID_OFFSET_X) // self.CELL_SIZE
        gy = (my - self.GRID_OFFSET_Y) // self.CELL_SIZE
        if self.session:
            grid_size = self.session.derelict_type.grid_size
            if 0 <= gx < grid_size and 0 <= gy < grid_size:
                return (gx, gy)
        return None

    def _get_instruction_text(self) -> str:
        """Get contextual instruction text based on current game state."""
        if not self.session:
            return ""
        if self.session.is_corrupted:
            return "Hull corrupted! Extract what you can. Tab: switch mode"
        if self._hold.is_full():
            return "Hold full! Stop salvaging to transfer to your ship."
        extractable = self.session.get_extractable_count()
        hidden = self.session.get_hidden_count()
        pct = self.session.corruption_timer / max(1, self.session.corruption_seconds)
        if self.session.corruption_started and pct < 0.25:
            return "Corruption imminent! Extract items now before they're lost!"
        if extractable > 0 and self.mode == "scan":
            return f"{extractable} items ready! Press Tab or click Extract Mode to collect."
        if hidden == 0 and extractable == 0:
            return "Deck cleared! Click Next Deck to go deeper."
        return "Scan to find items, Extract to collect. Tab: switch mode"

    def _end_session(self) -> None:
        """End the salvage session: transfer, calculate XP, show summary."""
        # Update personal records
        if self.session:
            total_salvage = sum(self.session.session_total_salvaged.values())
            if total_salvage > self.player.best_salvage_haul:
                self.player.best_salvage_haul = total_salvage

        xp = 0
        if self.session and self.progression:
            total = sum(self.session.session_total_salvaged.values())
            if total > 0:
                from spacegame.config import XP_PER_SALVAGE

                xp = total * XP_PER_SALVAGE
                msgs = self.progression.add_xp(xp)
                for m in msgs:
                    logger.info(m)
        self._transfer_count = self._transfer_hold_to_cargo()
        self.player.salvage_sessions_completed += 1
        self._summary_xp = xp
        self._calculate_rating()
        self._show_summary = True
        self._destroy_ui()

    def handle_event(self, event: pygame.event.Event) -> None:
        # Summary dismiss: click or key
        if self._show_summary:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.next_state = GameState.TRADING
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_ESCAPE,
                pygame.K_SPACE,
            ):
                self.next_state = GameState.TRADING
            return

        # Derelict selection phase
        if self._selecting_derelict:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for derelict_type, rect in self._derelict_choice_rects:
                    if rect.collidepoint(event.pos):
                        self._start_with_derelict(derelict_type)
                        return
            elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.back_button:
                    self.next_state = GameState.TRADING
            return

        # Exit confirmation
        if self._confirm_exit:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    self._confirm_exit = False
                    self._end_session()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self._confirm_exit = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._confirm_exit = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._get_grid_cell(event.pos)
            if cell:
                self._click_cell(cell[0], cell[1])
            else:
                # Check upgrade panel clicks
                self._handle_upgrade_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._confirm_exit = True
            # Tab toggles scan/extract mode
            elif event.key == pygame.K_TAB:
                self.mode = "extract" if self.mode == "scan" else "scan"
                self._mode_overlay.set_mode(self.mode)
                self._show_message(f"{'Extract' if self.mode == 'extract' else 'Scan'} mode")

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self._confirm_exit = True
            elif event.ui_element == self.scan_button:
                self.mode = "scan"
                self._mode_overlay.set_mode(self.mode)
                self._show_message("Scan mode: click cells to reveal contents")
            elif event.ui_element == self.extract_button:
                self.mode = "extract"
                self._mode_overlay.set_mode(self.mode)
                self._show_message("Extract mode: click scanned items to extract them")
            elif event.ui_element == self.next_deck_button:
                if self.session:
                    result = self.session.advance_deck()
                    if result:
                        self.player.add_salvage_intel(result.intel_earned)
                        self._session_intel += result.intel_earned
                        self.player.max_salvage_deck = max(
                            self.player.max_salvage_deck, result.new_deck
                        )
                        self._reveal_timers.clear()
                        # Sync VFX with new deck
                        d_id = self.session.derelict_type.id
                        self._vfx_atmosphere.set_deck(result.new_deck)
                        self._vfx_deck_meter.set_state(result.new_deck, d_id)
                        self._vfx_deck_trans.trigger(result.new_deck, d_id)
                        # Trigger tile-by-tile deck transition animation
                        self._start_deck_transition()
                        bonus_text = " (deck clear!)" if result.was_clear_bonus else ""
                        self._add_feedback(
                            f"+{result.intel_earned} Intel{bonus_text}",
                            WINDOW_WIDTH // 2,
                            80,
                            Colors.SALVAGE_THEME,
                        )
                        self._show_message(f"Deck {result.new_deck}! +{result.intel_earned} Intel")
                    else:
                        # Check why it failed
                        if self.session.current_deck >= self.session.derelict_type.max_decks:
                            self._show_message("Already at deepest deck!")
                        else:
                            self._show_message("Need 60% extraction to advance")
            elif event.ui_element == self.regen_button:
                if self.session:
                    self.session.regenerate_grid()
                    self.session.current_deck = 1
                    self.session.session_total_salvaged = {}
                    self._reveal_timers.clear()
                    self._show_message("Found a new derelict hull!")

    def _click_cell(self, gx: int, gy: int) -> None:
        if not self.session:
            return

        # Auto-detect intent based on cell state
        cell = self.session.get_cell_at(gx, gy)
        if cell is None:
            return

        # Hidden or corrupted cells → always scan
        if cell.state in (CellState.HIDDEN, CellState.CORRUPTED):
            self._do_scan(gx, gy)
        # Scanned cells with items → always extract
        elif cell.state == CellState.SCANNED and cell.has_item:
            self._do_extract(gx, gy)
        # Explicit mode fallback for edge cases
        elif self.mode == "scan":
            self._do_scan(gx, gy)
        elif self.mode == "extract":
            self._do_extract(gx, gy)

    def _do_scan(self, gx: int, gy: int) -> None:
        """Perform a scan action on the given cell."""
        success, msg = self.session.scan_cell(gx, gy)
        if success:
            fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2
            self.particles.emit(fx, fy, SCAN_RIPPLE)
            get_audio_manager().play_sfx("salvage_scan")
            self._reveal_timers[(gx, gy)] = 0.0
            self._add_feedback(msg, fx, fy - self.CELL_SIZE // 2)

            # Crew commentary (15% chance on scan)
            if random.random() < 0.15:
                line = self._get_crew_line("salvage_scan")
                if line:
                    self._crew_comment_name, self._crew_comment = line[0], line[1]
                    self._crew_comment_timer = 4.0

            # Found narrative fragment (30% chance)
            story = self._get_story_fragment()
            if story:
                self._story_text = story
                self._story_timer = 5.0

            # Scan wave expanding ring
            grid_size = self.session.derelict_type.grid_size
            max_radius = grid_size * self.CELL_SIZE * 0.6
            self._scan_waves.append([float(fx), float(fy), 0.0, max_radius, 300.0])

            # VFX: scan pulse sonar ripple
            cell_cx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
            cell_cy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2
            self._scan_pulse.trigger(cell_cx, cell_cy)

            # EXCELLENT quality golden glow burst
            cell = self.session.get_cell_at(gx, gy)
            if cell and cell.has_item:
                if cell.quality_tier == QualityTier.EXCELLENT:
                    self._excellent_glow[(gx, gy)] = 0.6
                # VFX: quality burst for good/excellent items
                if cell.quality_tier:
                    self._quality_burst.trigger(cell_cx, cell_cy, cell.quality_tier.value)
        else:
            self._show_message(msg)

    def _do_extract(self, gx: int, gy: int) -> None:
        """Perform an extract action on the given cell."""
        if self._hold.is_full():
            self._show_message("Salvage hold full!")
            return
        success, msg = self.session.start_extract(gx, gy)
        if success:
            get_audio_manager().play_sfx("salvage_extract")
        else:
            self._show_message(msg)

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 2.5

    def _start_with_derelict(self, derelict_type: DerelictType) -> None:
        """Create a salvage session with the chosen derelict type."""
        self.session = SalvageSession(
            self.salvage_config,
            extract_speed_bonus=self._extract_bonus,
            extra_charges=self._extra_charges,
            extra_parallel=self._extra_parallel,
            prestige_level=self.player.salvage_prestige_level,
            derelict_type=derelict_type,
        )
        self._selecting_derelict = False
        self._load_derelict_background()

        # Sync VFX with new session
        derelict_id = self.session.derelict_type.id
        grid_rect = pygame.Rect(
            self.GRID_OFFSET_X,
            self.GRID_OFFSET_Y,
            self.CELL_SIZE * self.session.derelict_type.grid_size,
            self.CELL_SIZE * self.session.derelict_type.grid_size,
        )
        self._vfx_atmosphere = SalvageAtmosphere(grid_rect, derelict_id)
        self._vfx_atmosphere.set_deck(self.session.current_deck)
        # Anchor deck meter to grid's right edge with buffer
        grid_right = self.GRID_OFFSET_X + self.CELL_SIZE * self.session.derelict_type.grid_size
        self._vfx_deck_meter.x = grid_right + scale_x(20)
        self._vfx_deck_meter.height = self.CELL_SIZE * self.session.derelict_type.grid_size
        self._vfx_deck_meter.max_decks = self.session.derelict_type.max_decks
        self._vfx_deck_meter.set_state(self.session.current_deck, derelict_id)
        self._vfx_corruption = CorruptionOverlay(
            bar_x=self.GRID_OFFSET_X,
            bar_y=self.GRID_OFFSET_Y - scale_y(20),
            bar_w=self.CELL_SIZE * self.session.derelict_type.grid_size,
        )

    def _load_derelict_stories(self) -> None:
        """Load derelict story fragments from data file."""
        import json
        from pathlib import Path

        story_path = (
            Path(__file__).parent.parent.parent / "data" / "salvage" / "derelict_stories.json"
        )
        try:
            with open(story_path) as f:
                data = json.load(f)
            self._derelict_stories = data.get("stories", {})
        except (FileNotFoundError, json.JSONDecodeError):
            self._derelict_stories = {}

    def _get_story_fragment(self) -> Optional[str]:
        """Get a random story fragment for the current derelict type.

        Returns a fragment ~30% of the time on scan, cycling through
        available stories without repeating until all shown.
        """
        if not self.session or random.random() > 0.30:
            return None
        derelict_id = self.session.derelict_type.id
        stories = self._derelict_stories.get(derelict_id, [])
        if not stories:
            return None
        # Find unshown stories
        available = [i for i in range(len(stories)) if i not in self._story_shown]
        if not available:
            self._story_shown.clear()  # Reset cycle
            available = list(range(len(stories)))
        idx = random.choice(available)
        self._story_shown.add(idx)
        return stories[idx]

    def _start_deck_transition(self) -> None:
        """Start tile-by-tile deck transition animation.

        Cells appear from edges inward with staggered delays.
        """
        if not self.session:
            return
        self._deck_transition.clear()
        self._deck_transition_pending.clear()
        grid_size = self.session.derelict_type.grid_size
        center = grid_size / 2.0
        for cell in self.session.grid:
            # Distance from center determines delay (edges appear first)
            dx = abs(cell.grid_x + 0.5 - center)
            dy = abs(cell.grid_y + 0.5 - center)
            dist = max(dx, dy)  # Chebyshev distance
            max_dist = center
            # Invert: edges first (0 delay), center last
            delay = (1.0 - dist / max(max_dist, 1)) * 0.3 + random.uniform(0, 0.05)
            self._deck_transition.append([cell.grid_x, cell.grid_y, delay])
            self._deck_transition_pending.add((cell.grid_x, cell.grid_y))
        self._deck_transition_active = True

    def _is_cell_transitioned(self, gx: int, gy: int) -> bool:
        """Check if a cell has finished its deck transition animation."""
        if not self._deck_transition_active:
            return True
        return (gx, gy) not in self._deck_transition_pending

    def _add_feedback(self, text: str, x: int, y: int, color=Colors.SUCCESS) -> None:
        self.feedback_messages.append({"text": text, "x": x, "y": y, "timer": 1.5, "color": color})

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._static_time += dt
        if not self._show_summary:
            self._session_elapsed += dt

        if self.message_timer > 0:
            self.message_timer -= dt

        for fb in self.feedback_messages:
            fb["timer"] -= dt
            fb["y"] -= 25 * dt
        self.feedback_messages = [fb for fb in self.feedback_messages if fb["timer"] > 0]

        # Update reveal timers
        for key in list(self._reveal_timers):
            self._reveal_timers[key] += dt
            if self._reveal_timers[key] >= 0.2:
                del self._reveal_timers[key]

        # Story fragment timer
        if self._story_timer > 0:
            self._story_timer -= dt

        # Crew comment timer
        if self._crew_comment_timer > 0:
            self._crew_comment_timer -= dt

        # Floating icon animations
        self._floats.update(dt)

        # Tooltip update
        self._update_upgrade_tooltip()
        self._tooltip.update(dt)

        # Scan wave expansion
        for wave in list(self._scan_waves):
            wave[2] += wave[4] * dt  # radius += speed * dt
            if wave[2] >= wave[3]:
                self._scan_waves.remove(wave)

        # Excellent glow decay
        for key in list(self._excellent_glow):
            self._excellent_glow[key] -= dt
            if self._excellent_glow[key] <= 0:
                del self._excellent_glow[key]

        # Update VFX systems
        self._vfx_atmosphere.update(dt)
        self._vfx_deck_trans.update(dt)
        self._vfx_corruption.update(dt)
        self._scan_pulse.update(dt)
        self._quality_burst.update(dt)
        self._mode_overlay.update(dt)

        # Sync corruption ratio from session
        if self.session and self.session.corruption_started:
            max_time = self.session.corruption_seconds
            if max_time > 0:
                ratio = self.session.corruption_timer / max_time
                self._vfx_atmosphere.set_corruption(ratio)
                self._vfx_corruption.set_ratio(ratio)

        # Corruption heartbeat (pulse at <15% timer)
        if self.session and self.session.corruption_started and not self.session.is_corrupted:
            pct = self.session.corruption_timer / max(1, self.session.corruption_seconds)
            if pct < 0.15:
                # Fast heartbeat pulse
                beat_speed = 6.0 + (1.0 - pct / 0.15) * 4.0
                self._heartbeat_flash = abs(math.sin(self._static_time * beat_speed)) * 40
            else:
                self._heartbeat_flash = 0.0
        else:
            self._heartbeat_flash = 0.0

        # Corruption wave staggered particle effects
        for entry in list(self._corruption_wave):
            entry[2] -= dt
            if entry[2] <= 0:
                fx = self.GRID_OFFSET_X + entry[0] * self.CELL_SIZE + self.CELL_SIZE // 2
                fy = self.GRID_OFFSET_Y + entry[1] * self.CELL_SIZE + self.CELL_SIZE // 2
                self.particles.emit(fx, fy, CORRUPTION_CRACKLE)
                self._corruption_wave.remove(entry)

        # Deck transition staggered cell appear
        for entry in list(self._deck_transition):
            entry[2] -= dt
            if entry[2] <= 0:
                self._deck_transition_pending.discard((entry[0], entry[1]))
                self._deck_transition.remove(entry)
        if self._deck_transition_active and not self._deck_transition:
            self._deck_transition_active = False

        # Emit extraction sparks
        if self.session:
            for cell in self.session.grid:
                if cell.state == CellState.EXTRACTING:
                    fx = self.GRID_OFFSET_X + cell.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
                    fy = self.GRID_OFFSET_Y + cell.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
                    if random.random() < 0.2:
                        self.particles.emit(fx, fy, EXTRACTION_SPARK)

            # Snapshot extracting cells before update (for positioning completed results)
            self._extracting_positions: Dict[str, tuple[int, int]] = {}
            for cell in self.session.grid:
                if cell.state == CellState.EXTRACTING and cell.config:
                    self._extracting_positions[cell.config.commodity_id] = (
                        cell.grid_x,
                        cell.grid_y,
                    )

            # Check if corruption just triggered (model handles logic, we add visual wave)
            was_corrupted = self.session.is_corrupted
            results = self.session.update(dt)
            if self.session.is_corrupted and not was_corrupted:
                # Corruption just happened — the model already flipped cells,
                # but we could have added a staggered wave before. For now,
                # emit crackle particles on each corrupted cell staggered
                for ci, cell in enumerate(self.session.grid):
                    if cell.state == CellState.CORRUPTED:
                        delay = ci * 0.03  # 30ms per cell
                        fx = self.GRID_OFFSET_X + cell.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
                        fy = self.GRID_OFFSET_Y + cell.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
                        # Queue delayed particle emission
                        self._corruption_wave.append([cell.grid_x, cell.grid_y, delay])

            for result in results:
                self._handle_extract_result(result)

    def _handle_extract_result(self, result: SalvageResult) -> None:
        self._hold.add_salvage(result.commodity_id, result.quantity)
        self.player.items_salvaged += result.quantity
        if result.corrupted and result.quantity > 0:
            self.player.corrupted_items_extracted += result.quantity
        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        # Position from pre-update snapshot of extracting cells
        fx, fy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        pos = self._extracting_positions.get(result.commodity_id)
        if pos is not None:
            fx = self.GRID_OFFSET_X + pos[0] * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + pos[1] * self.CELL_SIZE + self.CELL_SIZE // 2

        if result.corrupted:
            self.particles.emit(fx, fy, CORRUPTION_CRACKLE)
            get_audio_manager().play_sfx("salvage_corrupt")
        else:
            self.particles.emit(fx, fy, COLLECT_SPARKLE)
            get_audio_manager().play_sfx("salvage_reveal")

            # Float item icon from cell to hold bar
            hold_bar_x = float(WINDOW_WIDTH - 180)
            hold_bar_y = float(370)
            self._floats.add_icon_float(
                text=f"+{result.quantity} {name}",
                origin=(float(fx), float(fy)),
                target=(hold_bar_x, hold_bar_y),
                icon_key=result.commodity_id,
                duration=0.7,
            )

        self._add_feedback(f"+{result.quantity} {name}", fx, fy)

        # Ingredient drops
        for ingredient_id, qty in result.ingredient_drops.items():
            self._hold.add_salvage(ingredient_id, qty)
            icommodity = self.commodities.get(ingredient_id)
            iname = icommodity.name if icommodity else ingredient_id
            self._add_feedback(f"+{qty} {iname}!", fx, fy - 20, Colors.YELLOW)
            self.particles.emit(fx, fy, COLLECT_SPARKLE)

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        title = self.title_font.render("SALVAGE OPERATIONS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        if self._selecting_derelict:
            self._render_derelict_selection(screen)
            return

        if not self.session:
            return

        theme_color = self._get_theme_color()

        # Instruction text (above structural integrity bar)
        mode_label = "SCAN" if self.mode == "scan" else "EXTRACT"
        tip = self.small_font.render(
            f"{mode_label} Mode — {self._get_instruction_text()}",
            True,
            theme_color,
        )
        screen.blit(tip, (self.GRID_OFFSET_X, scale_y(62)))

        # Derelict background behind grid
        if self._derelict_bg is not None:
            screen.blit(self._derelict_bg, (self.GRID_OFFSET_X, self.GRID_OFFSET_Y))

        # VFX: atmosphere behind grid cells
        self._vfx_atmosphere.render(screen)

        # VFX: corruption bar above grid
        self._vfx_corruption.render(screen)

        self._render_corruption_timer(screen)
        self._mode_overlay.render(screen)
        self._render_grid(screen)
        self._scan_pulse.render(screen)
        self._quality_burst.render(screen)
        self._render_stats(screen)
        self._render_hold_bar_panel(screen)
        self._render_upgrade_panel(screen)

        # VFX: deck meter alongside right panels
        self._vfx_deck_meter.render(screen)

        # Scan wave rings (drawn on top of grid, below particles)
        for wave in self._scan_waves:
            cx, cy, radius = int(wave[0]), int(wave[1]), int(wave[2])
            fade = 1.0 - (wave[2] / wave[3])  # Fades as it expands
            alpha = int(fade * 120)
            if alpha > 5 and radius > 2:
                wave_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                wave_center = radius + 2
                pygame.draw.circle(
                    wave_surf, (80, 180, 255, alpha), (wave_center, wave_center), radius, 2
                )
                screen.blit(wave_surf, (cx - wave_center, cy - wave_center))

        # EXCELLENT golden glow bursts
        for (gx, gy), timer in self._excellent_glow.items():
            glow_alpha = int(min(timer / 0.3, 1.0) * 180)
            gx_px = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_PADDING
            gy_px = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_PADDING
            gw = self.CELL_SIZE - self.CELL_PADDING * 2
            gh = self.CELL_SIZE - self.CELL_PADDING * 2
            glow_surf = pygame.Surface((gw + 8, gh + 8), pygame.SRCALPHA)
            glow_surf.fill((255, 215, 0, glow_alpha))
            screen.blit(
                glow_surf,
                (gx_px - 4, gy_px - 4),
                special_flags=pygame.BLEND_ADD,
            )

        # Heartbeat flash overlay at <15% corruption (pre-allocated surface)
        if self._heartbeat_flash > 1:
            self._heartbeat_surface.fill((180, 30, 30, int(self._heartbeat_flash)))
            screen.blit(self._heartbeat_surface, (0, 0))

        # Particles
        self.particles.render(screen)

        # VFX: deck transition effect (after particles, before overlays)
        self._vfx_deck_trans.render(screen)

        # Floating item icons (cell to hold)
        for item in self._floats.items:
            alpha = int(255 * item.alpha)
            if alpha <= 0:
                continue
            text_surf = self.small_font.render(item.text, True, Colors.SUCCESS)
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (int(item.x) - text_surf.get_width() // 2, int(item.y)))

        # Story fragment display (found narrative)
        if self._story_timer > 0 and self._story_text:
            story_alpha = min(int(self._story_timer / 0.5 * 255), 200)
            story_font = get_font("narration", FONT_XS)
            from spacegame.engine.draw_utils import word_wrap

            story_lines = word_wrap(self._story_text, story_font, 500)
            story_y = WINDOW_HEIGHT - 160
            for line in story_lines:
                line_surf = story_font.render(line, True, (160, 150, 120))
                line_surf.set_alpha(story_alpha)
                screen.blit(
                    line_surf,
                    line_surf.get_rect(center=(WINDOW_WIDTH // 2, story_y)),
                )
                story_y += 18

        for fb in self.feedback_messages:
            surf = self.info_font.render(fb["text"], True, fb["color"])
            screen.blit(surf, (int(fb["x"]) - surf.get_width() // 2, int(fb["y"])))

        if self.message_timer > 0:
            msg_surf = self.info_font.render(self.message, True, Colors.YELLOW)
            screen.blit(msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 90)))

        # Crew commentary
        if self._crew_comment_timer > 0 and self._crew_comment:
            alpha = min(int(self._crew_comment_timer / 0.5 * 255), 220)
            crew_text = f'{self._crew_comment_name}: "{self._crew_comment}"'
            crew_surf = self.small_font.render(crew_text, True, (180, 200, 220))
            crew_surf.set_alpha(alpha)
            screen.blit(
                crew_surf,
                crew_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 130)),
            )

        # Tooltip
        self._render_tooltip(screen)

        # Exit confirmation overlay
        if self._confirm_exit:
            self._render_confirm_exit(screen)

        # Summary overlay (drawn last, on top of everything)
        if self._show_summary:
            self._render_summary(screen)

    def _render_derelict_selection(self, screen: pygame.Surface) -> None:
        """Render derelict type selection screen."""
        cx = WINDOW_WIDTH // 2
        subtitle = self.info_font.render(
            "Choose a derelict hull to salvage:", True, Colors.TEXT_SECONDARY
        )
        screen.blit(subtitle, subtitle.get_rect(center=(cx, 80)))

        self._derelict_choice_rects.clear()
        mouse_pos = pygame.mouse.get_pos()
        card_w = 340
        card_h = 140
        total_w = len(DERELICT_TYPES) * (card_w + 20) - 20
        start_x = cx - total_w // 2

        for i, dt in enumerate(DERELICT_TYPES):
            x = start_x + i * (card_w + 20)
            y = 140
            rect = pygame.Rect(x, y, card_w, card_h)
            self._derelict_choice_rects.append((dt, rect))

            is_hovered = rect.collidepoint(mouse_pos)
            bg_color = (30, 40, 65) if is_hovered else (18, 22, 38)
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill((*bg_color, 220))
            screen.blit(card_surf, rect.topleft)

            border_color = Colors.TEXT_HIGHLIGHT if is_hovered else Colors.UI_BORDER
            pygame.draw.rect(screen, border_color, rect, 2)

            # Derelict background sprite (thumbnail)
            bg_id = self.DERELICT_BG_MAP.get(dt.id)
            if bg_id:
                thumb = self._sprite_mgr.get_static_sprite("salvage", bg_id, scale=res_scale(1))
                if thumb:
                    thumb_scaled = pygame.transform.scale(thumb, (card_w - 20, 60))
                    thumb_scaled.set_alpha(100)
                    screen.blit(thumb_scaled, (x + 10, y + 30))

            # Name
            name_surf = self.info_font.render(dt.name, True, Colors.TEXT_HIGHLIGHT)
            screen.blit(name_surf, (x + 10, y + 8))

            # Stats
            stats = [
                f"Grid: {dt.grid_size}x{dt.grid_size}  |  Density: {dt.item_density:.0%}",
                f"Decks: {dt.max_decks}  |  Timer: {dt.corruption_seconds:.0f}s",
            ]
            # Loot profile
            dist = dt.item_distribution
            loot = f"Scrap {dist.get('scrap_metal', 0):.0%}  Elec {dist.get('salvaged_electronics', 0):.0%}  Rare {dist.get('rare_parts', 0):.0%}"
            stats.append(loot)

            for j, line in enumerate(stats):
                s = self.small_font.render(line, True, Colors.TEXT_SECONDARY)
                screen.blit(s, (x + 10, y + 95 + j * 16))

        # Hint
        hint = self.small_font.render(
            "Click a hull type to begin salvaging", True, Colors.TEXT_SECONDARY
        )
        screen.blit(hint, hint.get_rect(center=(cx, 310)))

    def _render_corruption_timer(self, screen: pygame.Surface) -> None:
        """Render corruption countdown bar above the grid with urgency effects."""
        if not self.session.corruption_started:
            return
        grid_size = self.session.derelict_type.grid_size
        bar_x = self.GRID_OFFSET_X
        bar_y = self.GRID_OFFSET_Y - 24
        bar_w = grid_size * self.CELL_SIZE
        bar_h = 16

        pct = max(0, self.session.corruption_timer / self.session.corruption_seconds)
        if pct > 0.6:
            color = (50, 200, 50)
        elif pct > 0.3:
            color = (220, 200, 50)
        else:
            # Pulsing red when critical
            pulse = int(abs(math.sin(self._static_time * 6)) * 35)
            color = (220 + pulse, 50, 50)

        draw_bar(
            screen,
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            self.session.corruption_timer,
            self.session.corruption_seconds,
            color,
            show_value=False,
            border_color=Colors.TEXT_SECONDARY,
        )

        if self.session.is_corrupted:
            label = self.small_font.render("CORRUPTED", True, (255, 80, 80))
        else:
            secs = max(0, int(self.session.corruption_timer))
            label = self.small_font.render(f"Corruption: {secs}s", True, Colors.TEXT)
        screen.blit(label, label.get_rect(center=(bar_x + bar_w // 2, bar_y + bar_h // 2)))

        # Progressive screen-edge darkening as corruption approaches
        if pct < 0.5 and not self.session.is_corrupted:
            urgency = 1.0 - (pct / 0.5)  # 0.0 at 50%, 1.0 at 0%
            self._corruption_overlay.fill((0, 0, 0, 0))
            # Red vignette on edges
            edge_w = int(40 * urgency)
            if edge_w > 2:
                r_alpha = int(urgency * 80)
                for i in range(edge_w):
                    a = r_alpha * (edge_w - i) // edge_w
                    pygame.draw.rect(
                        self._corruption_overlay,
                        (120, 20, 20, a),
                        (i, 0, 1, WINDOW_HEIGHT),
                    )
                    pygame.draw.rect(
                        self._corruption_overlay,
                        (120, 20, 20, a),
                        (WINDOW_WIDTH - 1 - i, 0, 1, WINDOW_HEIGHT),
                    )
                    pygame.draw.rect(
                        self._corruption_overlay,
                        (120, 20, 20, a),
                        (0, i, WINDOW_WIDTH, 1),
                    )
                    pygame.draw.rect(
                        self._corruption_overlay,
                        (120, 20, 20, a),
                        (0, WINDOW_HEIGHT - 1 - i, WINDOW_WIDTH, 1),
                    )
                screen.blit(self._corruption_overlay, (0, 0))

    def _render_grid(self, screen: pygame.Surface) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hover_cell = self._get_grid_cell(mouse_pos)

        tier_colors = {
            QualityTier.POOR: Colors.QUALITY_POOR,
            QualityTier.NORMAL: Colors.QUALITY_NORMAL,
            QualityTier.GOOD: Colors.QUALITY_GOOD,
            QualityTier.EXCELLENT: Colors.QUALITY_EXCELLENT,
        }

        for cell in self.session.grid:
            x = self.GRID_OFFSET_X + cell.grid_x * self.CELL_SIZE + self.CELL_PADDING
            y = self.GRID_OFFSET_Y + cell.grid_y * self.CELL_SIZE + self.CELL_PADDING
            w = self.CELL_SIZE - self.CELL_PADDING * 2
            h = self.CELL_SIZE - self.CELL_PADDING * 2
            rect = pygame.Rect(x, y, w, h)
            is_hovered = (
                hover_cell and hover_cell[0] == cell.grid_x and hover_cell[1] == cell.grid_y
            )

            # Deck transition: cells not yet transitioned render as dark empty
            if not self._is_cell_transitioned(cell.grid_x, cell.grid_y):
                pygame.draw.rect(screen, Colors.CELL_TRANSITION_BG, rect)
                pygame.draw.rect(screen, Colors.CELL_TRANSITION_BORDER, rect, 1)
                continue

            if cell.state == CellState.HIDDEN:
                # Cell sprite or flat fallback
                cell_spr = self._cell_sprites.get("hidden")
                if cell_spr is not None:
                    screen.blit(cell_spr, (x, y))
                else:
                    pygame.draw.rect(screen, Colors.CELL_HIDDEN_BG, rect)
                    pygame.draw.rect(screen, Colors.CELL_HIDDEN_BORDER, rect, 1)

                # Flickering static pixels (subtle life)
                rng = random.Random(
                    int(self._static_time * 10) + cell.grid_x * 7 + cell.grid_y * 13
                )
                for _ in range(4):
                    px = x + rng.randint(6, w - 6)
                    py = y + rng.randint(6, h - 6)
                    brightness = rng.randint(55, 85)
                    screen.set_at((px, py), (brightness, brightness, brightness + 8))

                # Mode-appropriate cursor hint
                if is_hovered and self.mode == "scan":
                    pygame.draw.rect(screen, (80, 160, 255), rect, 2)

            elif cell.state == CellState.CORRUPTED:
                # Dark red with corruption noise
                pygame.draw.rect(screen, Colors.CORRUPTION_BG, rect)
                rng = random.Random(
                    int(self._static_time * 8) + cell.grid_x * 11 + cell.grid_y * 17
                )
                for _ in range(6):
                    px = x + rng.randint(4, w - 4)
                    py = y + rng.randint(4, h - 4)
                    screen.set_at((px, py), (rng.randint(80, 140), 25, 25))
                pygame.draw.rect(screen, Colors.CORRUPTION_BORDER, rect, 1)
                label = self.cell_font.render("CORRUPT", True, Colors.CORRUPTION_TEXT)
                screen.blit(label, label.get_rect(center=rect.center))

            elif cell.state == CellState.SCANNED:
                reveal_key = (cell.grid_x, cell.grid_y)
                reveal_t = 1.0
                if reveal_key in self._reveal_timers:
                    reveal_t = min(1.0, self._reveal_timers[reveal_key] / 0.2)

                if cell.has_item:
                    # Item cell sprite or colored background
                    cell_spr = self._cell_sprites.get("item")
                    color = cell.config.color
                    if cell_spr is not None and reveal_t >= 1.0:
                        screen.blit(cell_spr, (x, y))
                    else:
                        r = int(20 + (color[0] // 3 - 20) * reveal_t)
                        g = int(20 + (color[1] // 3 - 20) * reveal_t)
                        b = int(25 + (color[2] // 3 - 25) * reveal_t)
                        pygame.draw.rect(screen, (max(0, r), max(0, g), max(0, b)), rect)

                    if reveal_t > 0.5:
                        # Commodity icon
                        icon = (
                            self._item_icons.get(cell.config.commodity_id) if cell.config else None
                        )
                        if icon is not None:
                            icon_x = rect.centerx - icon.get_width() // 2
                            icon_y = rect.top + 6
                            screen.blit(icon, (icon_x, icon_y))
                        else:
                            name = cell.item_type.value.replace("_", " ").title()
                            display = name[:10] + ".." if len(name) > 12 else name
                            label = self.cell_font.render(display, True, Colors.TEXT)
                            screen.blit(label, label.get_rect(center=(rect.centerx, rect.top + 28)))

                        # Quality frame sprite or colored border
                        frame = self._quality_frames.get(cell.quality_tier.value)
                        border_color = tier_colors.get(cell.quality_tier, (140, 140, 140))
                        if frame is not None:
                            # Center frame over cell
                            fx = rect.centerx - frame.get_width() // 2
                            fy = rect.centery - frame.get_height() // 2
                            screen.blit(frame, (fx, fy))
                        else:
                            pygame.draw.rect(screen, border_color, rect, 2)

                        # Tier label
                        tier_label = self.cell_font.render(
                            cell.quality_tier.value.title(), True, border_color
                        )
                        tier_y = rect.top + 58 if icon is not None else rect.top + 50
                        screen.blit(
                            tier_label,
                            tier_label.get_rect(center=(rect.centerx, tier_y)),
                        )
                else:
                    # Empty scanned cell
                    cell_spr = self._cell_sprites.get("scanned")
                    if cell_spr is not None and reveal_t >= 1.0:
                        screen.blit(cell_spr, (x, y))
                    else:
                        dark = int(25 * reveal_t)
                        pygame.draw.rect(screen, (dark, dark, dark + 5), rect)

                    if reveal_t > 0.5:
                        if cell.adjacent_count is not None and cell.adjacent_count > 0:
                            if cell.adjacent_count <= 2:
                                hint_color = (80, 120, 200)
                            elif cell.adjacent_count <= 4:
                                hint_color = (80, 200, 80)
                            else:
                                hint_color = (220, 200, 50)
                            hint_font = get_font("dialogue", FONT_XL)
                            hint_surf = hint_font.render(str(cell.adjacent_count), True, hint_color)
                            screen.blit(hint_surf, hint_surf.get_rect(center=rect.center))
                        else:
                            label = self.cell_font.render("Empty", True, (50, 52, 60))
                            screen.blit(label, label.get_rect(center=rect.center))

            elif cell.state == CellState.EXTRACTING:
                color = cell.config.color if cell.config else (100, 100, 100)
                bg = (color[0] // 3, color[1] // 3, color[2] // 3)
                pygame.draw.rect(screen, bg, rect)

                # Icon
                icon = self._item_icons.get(cell.config.commodity_id) if cell.config else None
                if icon is not None:
                    icon_x = rect.centerx - icon.get_width() // 2
                    icon_y = rect.top + 4
                    screen.blit(icon, (icon_x, icon_y))
                else:
                    label = self.cell_font.render("Extracting...", True, Colors.TEXT)
                    screen.blit(label, label.get_rect(center=(rect.centerx, rect.top + 28)))

                # Progress bar
                bar_y = rect.bottom - 14
                draw_bar(
                    screen,
                    x + 4,
                    bar_y,
                    w - 8,
                    10,
                    cell.extract_progress * 100,
                    100,
                    Colors.TEXT_HIGHLIGHT,
                    show_value=False,
                )

                # Pulsing border during extraction
                pulse = int(abs(math.sin(self._static_time * 4)) * 60) + 80
                pygame.draw.rect(screen, (pulse, pulse, 200), rect, 1)

            elif cell.state == CellState.EXTRACTED:
                cell_spr = self._cell_sprites.get("extracted")
                if cell_spr is not None:
                    screen.blit(cell_spr, (x, y))
                else:
                    pygame.draw.rect(screen, (15, 28, 15), rect)
                    pygame.draw.rect(screen, (40, 65, 40), rect, 1)
                check = self.cell_font.render("Collected", True, (60, 100, 60))
                screen.blit(check, check.get_rect(center=rect.center))

            # Hover highlight (mode-aware color)
            if is_hovered and cell.state != CellState.HIDDEN:
                hover_color = (80, 160, 255) if self.mode == "scan" else (255, 180, 60)
                pygame.draw.rect(screen, hover_color, rect, 2)

    def _render_stats(self, screen: pygame.Surface) -> None:
        panel_x = WINDOW_WIDTH - 280
        panel_y = 120
        theme_color = self._get_theme_color()

        # Panel background
        draw_nine_slice_panel(
            screen,
            (panel_x - 10, panel_y - 8, 270, 240),
            alpha=160,
            border_color=(theme_color[0] // 2, theme_color[1] // 2, theme_color[2] // 2),
        )

        header = self.info_font.render("SALVAGE STATUS", True, theme_color)
        screen.blit(header, (panel_x, panel_y))

        y = panel_y + 28

        # Deck progress
        max_decks = self.session.derelict_type.max_decks
        deck_surf = self.small_font.render(
            f"Deck: {self.session.current_deck}/{max_decks}", True, Colors.TEXT
        )
        screen.blit(deck_surf, (panel_x, y))
        y += 22

        # Scan charges as discrete pips
        charge_label = self.small_font.render("Charges:", True, Colors.TEXT)
        screen.blit(charge_label, (panel_x, y))
        pip_x = panel_x + 80
        pip_size = 8
        pip_gap = 3
        for i in range(self.session.max_charges):
            pip_rect = pygame.Rect(pip_x + i * (pip_size + pip_gap), y + 4, pip_size, pip_size)
            if i < self.session.charges:
                pygame.draw.rect(screen, (80, 160, 255), pip_rect)
            else:
                pygame.draw.rect(screen, (30, 35, 50), pip_rect)
            pygame.draw.rect(screen, (60, 70, 100), pip_rect, 1)
        y += 22

        stats = [
            f"Hidden: {self.session.get_hidden_count()}/{len(self.session.grid)}",
            f"Ready to Extract: {self.session.get_extractable_count()}",
            f"Intel: {self.player.salvage_intel}",
        ]

        # Extraction ratio for deck advance
        item_count = self.session.get_item_count()
        if item_count > 0:
            extracted = sum(1 for c in self.session.grid if c.state == CellState.EXTRACTED)
            ratio = extracted / item_count
            ratio_color = Colors.GREEN if ratio >= 0.6 else Colors.TEXT_SECONDARY
            ratio_surf = self.small_font.render(
                f"Extraction: {ratio:.0%} (60% to advance)", True, ratio_color
            )
            screen.blit(ratio_surf, (panel_x, y))
            y += 22

        for line in stats:
            surf = self.small_font.render(line, True, Colors.TEXT)
            screen.blit(surf, (panel_x, y))
            y += 22

        if self.session.total_salvaged:
            y += 4
            deck_hdr = self.small_font.render("Salvaged this deck:", True, Colors.TEXT_SECONDARY)
            screen.blit(deck_hdr, (panel_x, y))
            y += 20
            for cid, qty in self.session.total_salvaged.items():
                commodity = self.commodities.get(cid)
                name = commodity.name if commodity else cid
                # Commodity icon inline
                icon = self._item_icons.get(cid)
                if icon is not None:
                    # Scale to 16x16 for inline display
                    mini_icon = pygame.transform.scale(icon, (16, 16))
                    screen.blit(mini_icon, (panel_x + 4, y + 1))
                    item_surf = self.small_font.render(f"{name}: {qty}", True, Colors.TEXT)
                    screen.blit(item_surf, (panel_x + 24, y))
                else:
                    item_surf = self.small_font.render(f"  {name}: {qty}", True, Colors.TEXT)
                    screen.blit(item_surf, (panel_x, y))
                y += 20

    def _render_hold_bar_panel(self, screen: pygame.Surface) -> None:
        """Render salvage hold capacity bar below the stats panel."""
        panel_x = WINDOW_WIDTH - 280
        panel_y = 370  # Below stats panel
        bar_w = 200
        bar_h = 18

        stored = self._hold.get_total_stored()
        capacity = self._hold.capacity
        ratio = stored / max(1, capacity)
        if ratio > 0.9:
            bar_color = Colors.RED
        elif ratio > 0.7:
            bar_color = Colors.YELLOW
        else:
            bar_color = Colors.SALVAGE_THEME

        draw_bar(
            screen,
            panel_x,
            panel_y,
            bar_w,
            bar_h,
            stored,
            capacity,
            bar_color,
            show_value=False,
        )
        label = f"HOLD: {stored}/{capacity}"
        surf = self.small_font.render(label, True, Colors.TEXT)
        screen.blit(surf, (panel_x + 8, panel_y + 1))

        # Pulsing red border when nearly full
        if ratio > 0.9:
            pulse = int(abs(math.sin(self._static_time * 4)) * 80) + 80
            pygame.draw.rect(
                screen,
                (pulse, 30, 30),
                (panel_x - 1, panel_y - 1, bar_w + 2, bar_h + 2),
                1,
            )

    def _render_upgrade_panel(self, screen: pygame.Surface) -> None:
        """Render wreck upgrade purchase panel."""
        from spacegame.data_loader import get_data_loader

        wreck_upgrades = get_data_loader().wreck_upgrades
        if not wreck_upgrades:
            return

        wu_state = self.player.wreck_upgrades

        # Position below the grid on the left side (avoids right-side button conflicts)
        grid_size = self.session.derelict_type.grid_size if self.session else 5
        panel_x = self.GRID_OFFSET_X
        panel_y = self.GRID_OFFSET_Y + grid_size * self.CELL_SIZE + scale_y(24)
        if panel_y > WINDOW_HEIGHT - scale_y(120):
            return  # Not enough room below grid

        # Panel background
        upgrade_count = len(wreck_upgrades)
        row_h = scale_y(24)
        panel_w = grid_size * self.CELL_SIZE  # Match grid width
        panel_h = scale_y(28) + upgrade_count * row_h + scale_y(8)
        from spacegame.engine.draw_utils import draw_panel

        draw_panel(screen, (panel_x - 8, panel_y - 6, panel_w + 16, panel_h), alpha=160)

        # Header
        header = self.small_font.render("WRECK UPGRADES", True, Colors.SALVAGE_THEME)
        screen.blit(header, (panel_x, panel_y))

        intel_surf = self.small_font.render(
            f"Intel: {self.player.salvage_intel}", True, Colors.SALVAGE_THEME
        )
        screen.blit(intel_surf, (panel_x + panel_w - intel_surf.get_width(), panel_y))

        y = panel_y + scale_y(24)
        mouse_pos = pygame.mouse.get_pos()
        self._upgrade_rects.clear()

        pip_size = scale_y(8)
        pip_gap = 2
        # Fixed pip column for alignment (based on widest upgrade name)
        pip_col_x = panel_x + scale_x(140)

        for uid, definition in wreck_upgrades.items():
            if y > WINDOW_HEIGHT - 70:
                break
            level = wu_state.get_level(uid)
            next_cost = definition.get_cost(level + 1)

            btn_rect = pygame.Rect(panel_x, y, panel_w, row_h)
            self._upgrade_rects[uid] = btn_rect

            is_hover = btn_rect.collidepoint(mouse_pos)
            if is_hover:
                pygame.draw.rect(screen, (25, 40, 55), btn_rect, border_radius=3)

            # Upgrade name
            if next_cost is not None:
                can_buy = self.player.salvage_intel >= next_cost
                name_color = Colors.TEXT if can_buy else Colors.TEXT_SECONDARY
            else:
                name_color = Colors.TEXT_SECONDARY
            name_surf = self.small_font.render(definition.name, True, name_color)
            screen.blit(name_surf, (panel_x + 4, y + 3))

            # Level pips (aligned column, salvage cyan-blue theme)
            pip_x = pip_col_x
            pip_y = y + 6
            for i in range(definition.max_level):
                pip_rect = pygame.Rect(pip_x, pip_y, pip_size, pip_size)
                if i < level:
                    pygame.draw.rect(screen, (60, 140, 200), pip_rect)
                    pygame.draw.rect(screen, (100, 200, 255), pip_rect, 1)
                else:
                    pygame.draw.rect(screen, (20, 30, 40), pip_rect)
                    pygame.draw.rect(screen, (40, 60, 80), pip_rect, 1)
                pip_x += pip_size + pip_gap

            # Cost (right-aligned)
            if next_cost is not None:
                cost_color = Colors.TEXT if can_buy else Colors.RED
                cost_surf = self.small_font.render(f"{next_cost} SI", True, cost_color)
            else:
                cost_surf = self.small_font.render("MAX", True, (100, 200, 255))
            screen.blit(
                cost_surf,
                (panel_x + panel_w - cost_surf.get_width(), y + 3),
            )
            y += row_h

    def _handle_upgrade_click(self, pos: tuple) -> None:
        """Check if click hit an upgrade button and attempt purchase."""
        from spacegame.data_loader import get_data_loader

        wreck_upgrades = get_data_loader().wreck_upgrades
        for uid, rect in self._upgrade_rects.items():
            if rect.collidepoint(pos):
                success, msg, cost = self.player.wreck_upgrades.purchase(
                    uid, wreck_upgrades, self.player.salvage_intel
                )
                if success:
                    self.player.spend_salvage_intel(cost)
                    self._show_message(msg)
                    get_audio_manager().play_sfx("salvage_reveal")
                    # Apply upgrade effects immediately where possible
                    if uid == "salvage_buffer":
                        silo_bonus = int(wreck_upgrades[uid].effect_per_level)
                        self.player.salvage_hold_manager.upgrade_all_capacity(silo_bonus)
                        self._hold = self.player.salvage_hold_manager.get_hold(
                            self.salvage_config.system_id
                        )
                    elif uid == "signal_amplifier" and self.session:
                        charge_add = int(wreck_upgrades[uid].effect_per_level)
                        self.session.max_charges += charge_add
                        self.session.charges = min(
                            self.session.charges + charge_add, self.session.max_charges
                        )
                    elif uid == "quick_extract" and self.session:
                        self.session.extract_speed_bonus += wreck_upgrades[uid].effect_per_level
                else:
                    self._show_message(msg)
                break

    def _transfer_hold_to_cargo(self) -> int:
        """Transfer as much salvage hold contents as possible into ship cargo.

        Returns:
            Total units transferred.
        """
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        total_transferred = 0
        for commodity_id in list(self._hold.contents.keys()):
            stored = self._hold.contents.get(commodity_id, 0)
            if stored <= 0:
                continue
            available_space = self.player.ship.get_available_cargo(commodity_volumes)
            volume = commodity_volumes.get(commodity_id, 1)
            can_fit = available_space // volume if volume > 0 else stored
            transfer = min(stored, can_fit)
            if transfer > 0:
                self._hold.remove_salvage(commodity_id, transfer)
                self.player.ship.add_cargo(commodity_id, transfer, price_per_unit=0)
                total_transferred += transfer
        return total_transferred

    def _update_upgrade_tooltip(self) -> None:
        """Check if mouse is hovering over an upgrade row and update tooltip."""
        mouse_pos = pygame.mouse.get_pos()
        from spacegame.data_loader import get_data_loader

        wreck_upgrades = get_data_loader().wreck_upgrades
        for uid, rect in self._upgrade_rects.items():
            if rect.collidepoint(mouse_pos):
                definition = wreck_upgrades.get(uid)
                if definition:
                    level = self.player.wreck_upgrades.get_level(uid)
                    effect = definition.get_effect(level)
                    tip = f"{definition.description}"
                    if level > 0:
                        tip += f" (current: {effect:.2g})"
                    self._tooltip.set_hover(uid, mouse_pos)
                return
        self._tooltip.clear()

    def _render_tooltip(self, screen: pygame.Surface) -> None:
        """Render the upgrade tooltip if visible."""
        if not self._tooltip.visible or self._tooltip.content is None:
            return
        from spacegame.data_loader import get_data_loader

        wreck_upgrades = get_data_loader().wreck_upgrades
        definition = wreck_upgrades.get(self._tooltip.content)
        if not definition:
            return

        level = self.player.wreck_upgrades.get_level(self._tooltip.content)
        effect = definition.get_effect(level)
        lines = [definition.name, definition.description]
        if level > 0:
            lines.append(f"Current effect: {effect:.2g}")

        font = self.small_font
        line_surfaces = [font.render(line, True, Colors.TEXT) for line in lines]
        tip_w = max(s.get_width() for s in line_surfaces) + 20
        tip_h = len(line_surfaces) * 20 + 12
        alpha = int(255 * self._tooltip.alpha)

        tx, ty = self._tooltip.get_screen_position(tip_w, tip_h, WINDOW_WIDTH, WINDOW_HEIGHT)

        tip_surf = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        tip_surf.fill((15, 18, 30, min(alpha, 230)))
        pygame.draw.rect(tip_surf, (60, 70, 100, alpha), tip_surf.get_rect(), 1)
        screen.blit(tip_surf, (tx, ty))

        for i, surf in enumerate(line_surfaces):
            surf.set_alpha(alpha)
            screen.blit(surf, (tx + 10, ty + 6 + i * 20))

    def _render_confirm_exit(self, screen: pygame.Surface) -> None:
        """Render exit confirmation overlay."""
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        screen.blit(dim, (0, 0))

        prompt = self.info_font.render("End salvage session?", True, Colors.TEXT)
        screen.blit(prompt, prompt.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 15)))

        hint = self.small_font.render(
            "Y / Enter = Yes    N / Esc = Cancel", True, Colors.TEXT_SECONDARY
        )
        screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 15)))

    def _calculate_rating(self) -> None:
        """Calculate session performance rating."""
        if self.session:
            total_items = self.session.get_item_count()
            if total_items > 0:
                extracted = sum(self.session.session_total_salvaged.values())
                ratio = min(1.0, extracted / max(1, total_items * self.session.current_deck))
                self._session_rating = calculate_rating(ratio, SALVAGE_THRESHOLDS)
                if self._session_rating == "S":
                    self.player.s_ranks_earned += 1
                return
        self._session_rating = "D"

    def _render_summary(self, screen: pygame.Surface) -> None:
        """Render session summary overlay."""
        stats: list[tuple[str, str]] = []
        if self.session:
            total_items = sum(self.session.session_total_salvaged.values())

            if self.session.is_corrupted:
                corruption_status = "Survived"
            elif self.session.corruption_started:
                corruption_status = "Avoided"
            else:
                corruption_status = "Not started"

            stats = [
                ("Derelict Type", self.session.derelict_type.name),
                ("Deepest Deck", str(self.session.current_deck)),
                ("Items Extracted", str(total_items)),
                ("Intel Earned", str(self._session_intel)),
                ("Transferred to Cargo", str(self._transfer_count)),
                ("Corruption", corruption_status),
            ]
            # Hold remainder
            hold_remaining = self._hold.get_total_stored()
            if hold_remaining > 0:
                stats.append(("Remaining in Hold", str(hold_remaining)))
        draw_summary_overlay(
            screen,
            title="SALVAGE COMPLETE",
            stats=stats,
            xp_earned=self._summary_xp,
            rating_letter=self._session_rating,
            rating_color=RATING_COLORS.get(self._session_rating, Colors.TEXT_SECONDARY),
            panel_height=420,
        )

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
