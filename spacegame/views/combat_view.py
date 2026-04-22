"""Turn-based combat view with multi-action queue system.

Phase-driven state machine: INTRO → PLAYER_INPUT → ANIMATING_PLAYER →
ANIMATING_CREW → ANIMATING_ENEMIES → ROUND_END → (loop or COMBAT_OVER).

During PLAYER_INPUT, the player queues multiple actions (weapons, shields,
abilities) constrained by energy budget and cooldowns. Pressing Enter
executes the queue, resolving all actions with individual animations.

File structure (~3,770 lines):
  Lines ~1-50:      Imports and layout constants
  Lines ~50-220:    CombatPhase enum, _MoveButton, helper classes
  Lines ~220-350:   CombatView.__init__ — visual systems, state init
  Lines ~350-430:   Lifecycle: on_enter, on_exit
  Lines ~430-620:   update() — phase timing, bar lerp, animation processing
  Lines ~620-830:   Event handling — keyboard, mouse, hover
  Lines ~830-960:   Action queue — queue/execute/undo, legendary ability activation
  Lines ~960-1000:  Move button building
  Lines ~1000-1200: Special actions — flee, ultimate, negotiate, bribe
  Lines ~1200-1500: Animation system — enqueue, process, start effects, impacts
  Lines ~1500-1700: Enemy phase, round end, target selection, death checks
  Lines ~1700-1950: Player panel rendering (hull/shield/energy/momentum bars)
  Lines ~1950-2200: Enemy panel rendering (stacked cards with bars)
  Lines ~2200-2400: Move tooltips
  Lines ~2400-2700: Combat arena rendering (ships, projectiles, destruction)
  Lines ~2700-2960: Atmosphere, debris, damage state overlays
  Lines ~2960-3250: Action panel rendering (move buttons, queue display)
  Lines ~3250-3350: Move button rendering with queue badges
  Lines ~3350-3500: Action queue panel, legendary buttons, combat log
  Lines ~3500-3770: Intro banner, combat over overlay, floating texts

Extraction candidates: action panel (~300 lines), animation system (~300 lines),
arena rendering (~300 lines). Currently well-organized with section comments.
"""

import math
import random as _random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from spacegame.engine.dual_tech_portraits import PortraitConfig

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar, draw_panel
from spacegame.engine.fonts import FONT_DISPLAY, FONT_LG, FONT_MD, FONT_TITLE, FONT_XL, get_font
from spacegame.engine.particles import (
    HEAL_SPARKLE,
    LASER_HIT,
    MISSILE_EXPLOSION,
    SHIELD_IMPACT,
    SHIELD_RESTORE,
    SPARK_BURST,
    ParticlePool,
)
from spacegame.engine.scene_camera import SceneCamera
from spacegame.engine.screen_effects import ScreenShake, Vignette
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale
from spacegame.models.combat import (
    CombatLogEntry,
    CombatMove,
    CombatResult,
    EffectTarget,
    EffectType,
)
from spacegame.models.combat_engine import (
    FLEE_BASE_CHANCE,
    FLEE_MAX_CHANCE,
    FLEE_MIN_CHANCE,
    FLEE_SPEED_FACTOR,
    CombatEngine,
)
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# ============================================================================
# Constants
# ============================================================================

INTRO_DURATION = 0.8
ROUND_END_DURATION = 0.3
DEFAULT_ANIMATION_DURATION = 0.5
BAR_LERP_SPEED = 10.0  # Exponential decay factor — higher = snappier

# Layout zones — proportional to window dimensions
_MARGIN = scale_x(10)
_TOP_Y = scale_y(55)

PLAYER_PANEL_X = _MARGIN
PLAYER_PANEL_Y = _TOP_Y
PLAYER_PANEL_W = scale_x(220)

ENEMY_PANEL_W = PLAYER_PANEL_W
ENEMY_PANEL_X = WINDOW_WIDTH - ENEMY_PANEL_W - _MARGIN
ENEMY_PANEL_Y = _TOP_Y
ENEMY_CARD_H = scale_y(145)
ENEMY_CARD_GAP = scale_y(14)

# Bar rendering
BAR_HEIGHT = scale_y(18)
BAR_LABEL_W = scale_x(50)

# Themed palette for the combat view.
# Keys are semantic roles. Values live here (not inline) so colorblind
# profile work in Sprint 4 can remap each role by updating this table.
# Migration target for Sprint 4: resolve entries through PALETTE_ROLES
# via the Colors-wrapper design chosen in Sprint 1.
_COMBAT_COLORS: dict[str, tuple[int, int, int]] = {
    # --- Core element signatures ---
    "shield": (80, 180, 255),
    "energy": (180, 100, 255),

    # --- Banners / callouts ---
    "combo_banner": (255, 220, 100),
    "boss_header": (255, 200, 60),
    "boss_accent": (255, 80, 60),
    "boss_bg_dark": (20, 15, 10),
    "boss_bg_border": (100, 60, 30),
    "combo_tag": (180, 150, 50),
    "ult_text_pulse": (255, 255, 200),

    # --- Momentum / ultimate bar thresholds ---
    "momentum_charged": (100, 200, 255),
    "momentum_surging": (80, 200, 80),
    "momentum_overload": (220, 180, 50),
    "momentum_blazing": (255, 255, 220),
    "double_damage": (80, 220, 80),

    # --- Telegraph (enemy intent) ---
    "tele_evading": (100, 200, 255),
    "tele_fortifying": (100, 255, 150),
    "tele_draining": (200, 100, 255),
    "tele_charging": (255, 100, 60),
    "tele_attacking": (255, 180, 60),
    "tele_frozen": (150, 220, 255),

    # --- Archetype identities (shared visual with ship builder) ---
    "archetype_juggernaut": (200, 150, 50),
    "archetype_sentinel": (80, 180, 255),
    "archetype_ghost": (160, 100, 200),

    # --- Boss bar stages ---
    "boss_bar_low": (200, 60, 40),
    "boss_bar_mid": (220, 120, 30),
    "boss_bar_danger": (255, 40, 40),

    # --- Damage text palette ---
    "dmg_cryo": (100, 200, 255),
    "dmg_generic_warm": (255, 120, 80),
    "dmg_armor_deflect": (180, 180, 200),
    "dmg_near_miss": (255, 180, 80),
    "dmg_shield_regen": (80, 180, 255),
    "dmg_energy_boost": (180, 100, 255),
    "dmg_momentum": (255, 220, 100),
    "dmg_chill": (140, 210, 255),
    "dmg_burn": (255, 140, 60),
    "dmg_voltaic": (200, 160, 255),
    "dmg_counterstrike": (100, 220, 255),
    "dmg_vulnerability": (255, 100, 100),

    # --- Passive text colors ---
    "passive_last_stand": (255, 80, 80),
    "passive_positive_dim": (100, 180, 100),
    "passive_counterstrike_bright": (200, 255, 100),

    # --- Modal / summary panel bg ---
    "panel_modal_bg": (15, 20, 40),
    "panel_modal_bg_dark": (12, 16, 32),

    # --- Action tab bg / border pairs ---
    "tab_attack_bg": (200, 80, 80),
    "tab_attack_border": (140, 50, 50),
    "tab_defend_bg": (80, 140, 220),
    "tab_defend_border": (40, 80, 140),
    "tab_utility_bg": (80, 180, 100),
    "tab_utility_border": (40, 110, 55),
    "tab_coord_bg": (220, 180, 80),
    "tab_coord_border": (150, 120, 50),
    "tab_inactive_text": (50, 55, 65),

    # --- Queue / execute button ---
    "exec_active_bg": (40, 100, 60),
    "exec_inactive_bg": (25, 35, 30),
    "exec_inactive_border": (50, 60, 55),
    "exec_inactive_text": (60, 70, 65),
    "undo_active_bg": (50, 40, 30),
    "undo_inactive_bg": (25, 25, 25),
    "undo_active_border": (100, 80, 60),
    "undo_inactive_border": (40, 40, 40),
    "undo_inactive_text": (50, 50, 50),
    "skip_hint_text": (55, 60, 70),
    "queue_hint_dim": (60, 65, 80),
    "queue_bullet_dim": (80, 90, 110),
    "queue_recap_text": (80, 90, 115),
    "queue_recap_label": (90, 100, 130),
    "queue_summary_color": (100, 130, 170),
    "queue_target_dim": (120, 140, 160),
    "queue_number": (80, 140, 220),

    # --- Legendary active buttons ---
    "void_release_bg": (40, 15, 60),
    "void_release_border": (140, 60, 200),
    "void_release_text": (180, 100, 240),
    "overdrive_bg": (50, 40, 15),
    "overdrive_border": (200, 170, 60),
    "overdrive_text": (220, 190, 80),

    # --- Notification accents ---
    "notify_warning_red": (220, 80, 80),
    "notify_amber": (200, 160, 60),
}

# Module-level aliases, kept as named constants for legacy call sites.
SHIELD_COLOR = _COMBAT_COLORS["shield"]
ENERGY_COLOR = _COMBAT_COLORS["energy"]
BAR_BG_COLOR = Colors.BAR_BG
BAR_EDGE_HIGHLIGHT = Colors.BAR_EDGE


# ============================================================================
# Utility functions
# ============================================================================


def _bar_color_for_ratio(ratio: float) -> tuple[int, int, int]:
    """Return green/yellow/red color based on a 0.0–1.0 ratio."""
    if ratio > 0.5:
        return Colors.GREEN
    elif ratio > 0.25:
        return Colors.YELLOW
    return Colors.RED


# ============================================================================
# CombatPhase
# ============================================================================


class CombatPhase(Enum):
    """Phases of the combat turn flow."""

    INTRO = "intro"
    PLAYER_INPUT = "player_input"
    ANIMATING_PLAYER = "anim_player"
    ANIMATING_CREW = "anim_crew"
    ANIMATING_ENEMIES = "anim_enemies"
    ROUND_END = "round_end"
    COMBAT_OVER = "combat_over"


class ArenaCameraState(Enum):
    """Canonical camera states for the combat view. Driven through
    SceneCamera via _enter_camera_state.
    """

    DEFAULT = "default"
    FOCUS_PLAYER = "focus_player"
    FOCUS_ENEMY = "focus_enemy"
    WIDE = "wide"


# Camera state parameters: (offset_x, offset_y, zoom, duration_seconds).
# FOCUS_ENEMY's offset is computed dynamically toward the targeted enemy;
# this table holds zoom/duration only for that state.
_CAMERA_STATE_PARAMS = {
    ArenaCameraState.DEFAULT: ((0.0, 0.0), 1.0, 0.25),      # 250ms pacing beat
    ArenaCameraState.FOCUS_PLAYER: ((-80.0, 0.0), 1.25, 0.3),
    ArenaCameraState.FOCUS_ENEMY: ((60.0, 0.0), 1.25, 0.3),  # toward right side where enemies are
    ArenaCameraState.WIDE: ((0.0, 0.0), 0.85, 0.5),
}


# ============================================================================
# AnimationEvent
# ============================================================================


@dataclass
class AnimationEvent:
    """Visual event to animate in sequence."""

    log_entry: CombatLogEntry
    source: str = "player"
    duration: float = DEFAULT_ANIMATION_DURATION


@dataclass
class _MoveButton:
    """Custom rendered move button with energy cost and cooldown overlay."""

    rect: pygame.Rect
    move: CombatMove
    enabled: bool = True
    hovered: bool = False
    cooldown_remaining: int = 0


# ============================================================================
# Layout constants for action panel
# ============================================================================

ACTION_PANEL_H = scale_y(195)
ACTION_PANEL_Y = WINDOW_HEIGHT - ACTION_PANEL_H
PLAYER_PANEL_H = ACTION_PANEL_Y - PLAYER_PANEL_Y - _MARGIN

MOVE_BTN_W = scale_x(210)
MOVE_BTN_H = scale_y(55)
MOVE_BTN_GAP = scale_y(8)
MOVE_BTN_COLS = 2
MOVE_BTN_X_START = scale_x(15)
MOVE_BTN_Y_START = ACTION_PANEL_Y + scale_y(30)

SPECIAL_BTN_Y = MOVE_BTN_Y_START + 2 * (MOVE_BTN_H + MOVE_BTN_GAP) + 4
SPECIAL_BTN_W = scale_x(120)
SPECIAL_BTN_H = scale_y(36)

FLEE_BTN_X = MOVE_BTN_X_START
NEGOTIATE_BTN_X = MOVE_BTN_X_START + SPECIAL_BTN_W + MOVE_BTN_GAP
BRIBE_BTN_X = NEGOTIATE_BTN_X + SPECIAL_BTN_W + scale_x(20) + MOVE_BTN_GAP

# Combat arena — fills center between side panels
ARENA_X = PLAYER_PANEL_X + PLAYER_PANEL_W + _MARGIN
ARENA_Y = _TOP_Y
ARENA_W = ENEMY_PANEL_X - ARENA_X - _MARGIN
ARENA_H = PLAYER_PANEL_H
PLAYER_SHIP_POS = (ARENA_X + ARENA_W // 3, ARENA_Y + ARENA_H // 2)
ENEMY_SHIP_POS = (ARENA_X + 2 * ARENA_W // 3, ARENA_Y + ARENA_H // 2)

# Ship display scale based on class (base values — res_scale applied at load time)
# Larger ships get larger scale for visual weight and class distinction
SHIP_CLASS_SCALE: dict[str, int] = {
    "starter": 3,
    "early_game": 3,
    "mid_game": 4,
    "late_game": 4,
    "faction": 4,
}
# Enemy danger tier → display scale
ENEMY_TIER_SCALE: dict[str, int] = {
    "low": 3,
    "moderate": 3,
    "dangerous": 4,
}
# Vertical spacing between stacked enemies (scales with ship size)
ENEMY_STACK_SPACING = scale_y(100)

# Idle ship bob animation
IDLE_BOB_AMPLITUDE = scale_y(3)  # Pixels of vertical oscillation
IDLE_BOB_PERIOD = 2.5  # Seconds per full cycle


def _roll_loot(loot_table: list[dict], seed: int = 0) -> dict[str, int]:
    """Roll loot drops from an enemy's loot table.

    Args:
        loot_table: List of {commodity_id, min_qty, max_qty, chance} dicts.
        seed: RNG seed for deterministic results.

    Returns:
        Dict of commodity_id -> quantity for items that dropped.
    """
    import random as _rng

    rng = _rng.Random(seed)
    result: dict[str, int] = {}

    for entry in loot_table:
        if rng.random() < entry["chance"]:
            qty = rng.randint(entry["min_qty"], entry["max_qty"])
            commodity = entry["commodity_id"]
            result[commodity] = result.get(commodity, 0) + qty

    return result


# ============================================================================
# CombatView
# ============================================================================


class CombatView(BaseView):
    """Turn-based combat interface with animated phase flow."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        combat_engine: CombatEngine,
        player: Optional[Player],
        social_manager: object = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.engine = combat_engine
        self.player = player
        self.social_manager = social_manager

        # Phase state machine
        self.phase: CombatPhase = CombatPhase.INTRO
        self.phase_timer: float = 0.0

        # Animation queue
        self.animation_queue: list[AnimationEvent] = []
        self.current_animation: Optional[AnimationEvent] = None
        self.animation_timer: float = 0.0

        # Tutorial helper (set externally when first combat tutorial is active)
        self._tutorial_helper: Optional[object] = None

        # Target selection
        self.selected_target_idx: int = 0

        # Crew tactical choice: selected crew ability for this turn (None = skip)
        self._selected_crew_move_id: Optional[str] = None
        self._crew_move_buttons: list[_MoveButton] = []
        self._combo_buttons: list[dict] = []  # {"rect": Rect, "combo": CrewCombo, "enabled": bool}
        self._selected_combo_id: Optional[str] = None

        # Floating text feedback
        self.floating_texts: list[dict] = []

        # Combat log display
        self.visible_log_lines: list[str] = []

        # Displayed values for smooth bar animation
        self._displayed_player_hull: float = 0.0
        self._displayed_player_shields: float = 0.0
        self._displayed_player_energy: float = 0.0
        self._displayed_enemy_hulls: list[float] = []
        self._displayed_enemy_shields: list[float] = []

        # Enemy card flash timers (for damage flash)
        self._enemy_flash_timers: list[float] = []
        self._player_flash_timer: float = 0.0

        # Ship sprite flash timers (white=hull hit, cyan=shield hit)
        self._player_sprite_flash: float = 0.0
        self._player_shield_flash: float = 0.0
        self._enemy_sprite_flashes: list[float] = []
        self._enemy_shield_flashes: list[float] = []

        # Move buttons (rebuilt each PLAYER_INPUT phase)
        self.move_buttons: list[_MoveButton] = []
        self.skip_crew_ids: set[str] = set()

        # Action panel category tabs
        self._action_tab: str = "attack"  # "attack", "defend", "utility", "coordinated"
        self._action_tab_scroll: dict[str, int] = {
            "attack": 0,
            "defend": 0,
            "utility": 0,
            "coordinated": 0,
        }
        self._categorized_moves: dict[str, list[_MoveButton]] = {
            "attack": [],
            "defend": [],
            "utility": [],
        }

        # Ship destruction animation tracking
        # Maps enemy index -> (x, y, AnimatedSprite) for dying enemies
        self._destroying_enemies: dict[int, tuple[int, int, "AnimatedSprite"]] = {}

        # Arena action display
        self._arena_action_text: str = ""
        self._arena_action_timer: float = 0.0

        # Negotiate sub-menu
        self._negotiate_menu_open: bool = False
        self._negotiate_skills: list[str] = ["persuasion", "intimidation", "observation"]

        # Bribe state (credits set by game.py before on_enter)
        self._bribe_credits_available: int = 0
        self._bribe_cost: int = 0  # Set after successful bribe for game.py to read

        # Return state
        self.next_state: Optional[GameState] = None
        self._return_state: GameState = GameState.TRADING

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)  # Screen titles: Press Start 2P
        self.header_font = get_font("header", FONT_XL)  # Section headers
        self.info_font = get_font("dialogue", FONT_LG)  # Action names, descriptions
        self.small_font = get_font("stats", FONT_MD)  # Stat values, energy costs
        self.banner_font = get_font("machine", FONT_DISPLAY)  # LEGENDARY THREAT, boss intros

        # Sprite manager for ship sprites
        self._sprite_mgr = get_sprite_manager()
        self._ship_sprite_cache: dict[str, Optional[AnimatedSprite]] = {}

        # ShipComposite-backed enemy portrait provider (Combat C4 §4.1).
        # Lazily constructs builds + composites per enemy template. Falls
        # back to the legacy AnimatedSprite path when a template isn't
        # registered with the data loader (defensive; shouldn't happen in
        # production, but keeps the view stable if a save file references
        # a since-removed template).
        from spacegame.engine.enemy_composite_provider import EnemyCompositeProvider

        def _enemy_template_lookup(template_id: str):  # type: ignore[no-untyped-def]
            from spacegame.data_loader import get_data_loader
            return get_data_loader().enemy_templates.get(template_id)

        self._enemy_composite_provider = EnemyCompositeProvider(
            lookup=_enemy_template_lookup
        )

        # Tier 3.C: per-enemy module overlays. Painted over the card
        # composite for subsystem targeting feedback (focus highlight,
        # destruction marks, hit flashes). Construction is lazy via
        # get_overlay on first render.
        from spacegame.engine.enemy_overlay_provider import (
            EnemyModuleOverlayProvider,
        )

        self._enemy_overlay_provider = EnemyModuleOverlayProvider()

        # Dual tech cinematic slot (Combat C5 §4.3). None when no
        # cinematic is playing; populated by ``trigger_dual_tech()``
        # and cleared on completion. The controller owns all cinematic
        # rendering + timing; combat view just forwards dt + screen.
        from spacegame.engine.dual_tech_controller import DualTechController

        self._dual_tech_controller: Optional[DualTechController] = None
        # Snapshot of the camera zoom at cinematic start so we can
        # restore on completion. Set when a cinematic triggers.
        self._pre_cinematic_zoom: float = 1.0

        # Projectile system for weapon visualization
        from spacegame.engine.projectiles import ProjectileManager

        self._projectile_mgr = ProjectileManager()

        # Shield, damage, destruction, and atmosphere visualization
        from spacegame.engine.combat_vfx import (
            CombatAtmosphere,
            DamageStateManager,
            DestructionSequence,
            ShieldRenderer,
        )

        self._shield_renderer = ShieldRenderer()
        self._damage_state_mgr = DamageStateManager()
        self._destruction_sequences: list[DestructionSequence] = []
        self._persistent_debris: list[dict] = []
        self._atmosphere: Optional[CombatAtmosphere] = None

        # Visual systems
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=100)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill(Colors.BLACK)
        self._bg_dim.set_alpha(25)
        self.particles = ParticlePool(500)
        self.screen_shake = ScreenShake()  # retained for legacy compat — superseded by scene_camera for shake
        self.scene_camera = SceneCamera()
        self.vignette = Vignette(WINDOW_WIDTH, WINDOW_HEIGHT, intensity=0.2)

        # Damage state overlays (96x96 at 3x scale)
        self._damage_overlay_light = self._create_damage_overlay(severity="light")
        self._damage_overlay_heavy = self._create_damage_overlay(severity="heavy")

        # UI element refs (created in _create_ui)
        self.continue_button: Optional[pygame_gui.elements.UIButton] = None

    # ------------------------------------------------------------------
    # BaseView lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Called when combat view becomes active."""
        super().on_enter()
        self.phase = CombatPhase.INTRO
        self.phase_timer = 0.0
        self.animation_queue.clear()
        self.current_animation = None
        self.floating_texts.clear()
        self.visible_log_lines.clear()
        self.next_state = None
        self.selected_target_idx = 0
        self._projectile_mgr.clear()
        self._shield_renderer.clear()
        self._damage_state_mgr.clear()
        self._destruction_sequences.clear()
        self._persistent_debris.clear()
        # Combat §11.4: clear destruction progress on cached composites so
        # prior-encounter wreckage doesn't bleed into a fresh fight.
        self._enemy_composite_provider.reset_destruction()
        # Tier 3.A: evict stale per-instance entries from prior encounters.
        # Current enemy list is the living-instance set we want to keep.
        state = self.engine.get_state()
        self._enemy_composite_provider.prune_dead_instances(state.enemies)
        # Tier 3.C: same for module overlays.
        self._enemy_overlay_provider.prune_dead_instances(state.enemies)

        # Initialize displayed bar values from actual state
        self._displayed_player_hull = float(state.player.hull)
        self._displayed_player_shields = float(state.player.shields)
        self._displayed_player_energy = float(state.player.energy)
        self._displayed_player_momentum = 0.0
        self._momentum_pulse_timer = 0.0  # Brief glow on threshold cross
        self._momentum_pulse_color: tuple[int, int, int] = _COMBAT_COLORS["momentum_charged"]
        self._dodge_jink_timer = 0.0  # Lateral ship offset on dodge
        self._dodge_jink_direction = 1  # 1 = right, -1 = left
        self._rng_visual = _random.Random(42)  # Visual variety RNG
        self._ultimate_zoom_timer = 0.0  # Cinematic zoom on ultimate
        self._ultimate_darken_timer = 0.0  # Darken overlay on ultimate
        self._combo_banner_text = ""  # Combo name banner
        self._combo_banner_timer = 0.0
        self._selected_crew_move_id: Optional[str] = getattr(self, "_selected_crew_move_id", None)
        self._action_queue = None  # ActionQueue, created at start of each PLAYER_INPUT
        self._void_release_rect: Optional[pygame.Rect] = None
        self._overdrive_rect: Optional[pygame.Rect] = None
        self._displayed_enemy_hulls = [float(e.current_hull) for e in state.enemies]
        self._displayed_enemy_shields = [float(e.current_shields) for e in state.enemies]
        self._enemy_flash_timers = [0.0] * len(state.enemies)
        self._player_flash_timer = 0.0
        self._enemy_sprite_flashes = [0.0] * len(state.enemies)
        self._enemy_shield_flashes = [0.0] * len(state.enemies)

        # Initialize combat atmosphere based on enemy danger tiers
        from spacegame.engine.combat_vfx import CombatAtmosphere

        danger = "safe"
        for e in state.enemies:
            tier = e.template.danger_tier
            if tier == "dangerous":
                danger = "dangerous"
                break
            if tier == "moderate" and danger == "safe":
                danger = "moderate"
        # Special case: Crimson Reach enemies
        if any(
            e.template.faction_id == "crimson_reach"
            for e in state.enemies
            if hasattr(e.template, "faction_id")
        ):
            danger = "crimson"
        arena_rect = pygame.Rect(ARENA_X, ARENA_Y, ARENA_W, ARENA_H)
        self._atmosphere = CombatAtmosphere(arena_rect, danger)
        self._player_sprite_flash = 0.0
        self._player_shield_flash = 0.0
        self._destroying_enemies.clear()

        # ArenaEntry scripted intro (Combat C3 §4.8). Replaces the legacy
        # timer-based INTRO phase — drives camera push, tint fade-in,
        # and dust fade-in through the 1.5s choreography.
        from spacegame.engine.arena_entry import ArenaEntry

        self._arena_entry: Optional[ArenaEntry] = ArenaEntry(
            enemy_count=len(state.enemies)
        )
        self._previously_dead: set[int] = set()  # Enemy indices dead before this round

        # Camera at DEFAULT; combat opens at neutral viewport.
        self.scene_camera.reset_immediate()

        self._create_ui()
        logger.info("Entered combat view")

    def on_exit(self) -> None:
        """Called when leaving combat view."""
        # Clear camera state so leftover shake/transitions don't bleed
        # into the next view.
        self.scene_camera.clear_shakes()
        self.scene_camera.reset_immediate()
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited combat view")

    def _create_ui(self) -> None:
        """Create pygame_gui elements."""
        self.continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 - 80, WINDOW_HEIGHT // 2 + 100, 160, 45),
            text="Continue",
            manager=self.ui_manager,
        )
        self.continue_button.hide()

    def _destroy_ui(self) -> None:
        """Destroy all pygame_gui elements."""
        if self.continue_button:
            self.continue_button.kill()
            self.continue_button = None

    # ------------------------------------------------------------------
    # State query
    # ------------------------------------------------------------------

    def get_next_state(self) -> Optional[GameState]:
        """Return the next state if combat is done and player pressed continue."""
        return self.next_state

    # ------------------------------------------------------------------
    # Target index safety
    # ------------------------------------------------------------------

    def _render_combat_tutorial(self, screen: pygame.Surface) -> None:
        """Render crew member guidance during combat tutorial."""
        hint = self._tutorial_helper.get_current_hint() if self._tutorial_helper else ""
        if not hint:
            return
        from spacegame.engine.draw_utils import draw_panel
        from spacegame.engine.fonts import FONT_BODY, get_font

        font = get_font("narration", FONT_BODY)
        panel_w = scale_x(500)
        panel_h = scale_y(40)
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = scale_y(25)

        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=220)
        sp = font.render("Crew: ", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(sp, (panel_x + 12, panel_y + 10))
        txt = font.render(hint, True, Colors.TEXT_PRIMARY)
        screen.blit(txt, (panel_x + 12 + sp.get_width(), panel_y + 10))

    def _clamp_selected_target(self) -> None:
        """Ensure selected_target_idx is within bounds of the enemy list.

        Called at the start of update/render to prevent stale indices from
        causing IndexError crashes in multi-ship combat when enemies die.
        """
        if not hasattr(self, "engine") or not self.engine:
            return
        enemies = self.engine.get_state().enemies
        if not enemies:
            self.selected_target_idx = 0
            return
        if self.selected_target_idx >= len(enemies):
            self.selected_target_idx = len(enemies) - 1

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Update combat view each frame."""
        self._clamp_selected_target()
        self.phase_timer += dt
        self.background.update(dt)
        self.particles.update(dt)
        self.screen_shake.update(dt)
        self.scene_camera.update(dt)
        self._projectile_mgr.update(dt)
        self._shield_renderer.update(dt)
        self._damage_state_mgr.update(dt)
        # Tier 3.C: advance module-overlay flash timers for every cached
        # enemy overlay. Cheap — overlays only tick flashes; persistent
        # state is set from game state on render.
        for overlay in self._enemy_overlay_provider.all_overlays():
            overlay.update(dt)
        if self._atmosphere:
            self._atmosphere.update(dt)

        # Sync shield and hull states from combat engine
        if hasattr(self, "engine") and self.engine:
            state = self.engine.get_state()
            if state:
                p = state.player
                self._shield_renderer.set_shield(
                    "player", p.shields / max(1, p.max_shields), p.max_shields
                )
                self._damage_state_mgr.set_hull("player", p.hull / max(1, p.max_hull))
                for i, e in enumerate(state.enemies):
                    ekey = f"enemy_{i}"
                    self._shield_renderer.set_shield(
                        ekey, e.current_shields / max(1, e.template.shields), e.template.shields
                    )
                    self._damage_state_mgr.set_hull(ekey, e.current_hull / max(1, e.template.hull))

        # Update destruction sequences
        for seq in self._destruction_sequences:
            seq.update(dt)
        finished = [s for s in self._destruction_sequences if s.finished]
        for seq in finished:
            self._persistent_debris.extend(seq.debris)
            self._destruction_sequences.remove(seq)

        # Update floating texts
        for ft in self.floating_texts:
            ft["timer"] -= dt
            ft["y"] += ft.get("vy", -40) * dt
        self.floating_texts = [ft for ft in self.floating_texts if ft["timer"] > 0]

        # Smooth bar animation (lerp displayed toward actual)
        self._update_displayed_bars(dt)

        # Flash timers (panel + sprite)
        self._player_flash_timer = max(0.0, self._player_flash_timer - dt)
        self._player_sprite_flash = max(0.0, self._player_sprite_flash - dt)
        self._player_shield_flash = max(0.0, self._player_shield_flash - dt)
        self._momentum_pulse_timer = max(0.0, self._momentum_pulse_timer - dt)
        self._dodge_jink_timer = max(0.0, self._dodge_jink_timer - dt)
        self._ultimate_zoom_timer = max(0.0, self._ultimate_zoom_timer - dt)
        self._ultimate_darken_timer = max(0.0, self._ultimate_darken_timer - dt)
        self._combo_banner_timer = max(0.0, self._combo_banner_timer - dt)
        for i in range(len(self._enemy_flash_timers)):
            self._enemy_flash_timers[i] = max(0.0, self._enemy_flash_timers[i] - dt)
        for i in range(len(self._enemy_sprite_flashes)):
            self._enemy_sprite_flashes[i] = max(0.0, self._enemy_sprite_flashes[i] - dt)
        for i in range(len(self._enemy_shield_flashes)):
            self._enemy_shield_flashes[i] = max(0.0, self._enemy_shield_flashes[i] - dt)

        # Arena action text timer
        self._arena_action_timer = max(0.0, self._arena_action_timer - dt)

        # Update ship animations
        for sprite in self._ship_sprite_cache.values():
            if sprite is not None:
                sprite.update(dt)

        # Dual tech cinematic (Combat C5 §4.3) — owns camera zoom while
        # active. Fires on_impact callback at IMPACT phase for damage
        # resolution, then clears on completion.
        if self._dual_tech_controller is not None:
            self._dual_tech_controller.update(dt)
            # Drive camera zoom from the controller — lerps from 1.0 to
            # a cinematic zoom during CAMERA_ZOOM phase, holds through
            # the rest of the timeline.
            zoom_factor = self._dual_tech_controller.camera_zoom_factor
            cinematic_zoom = 1.25
            self.scene_camera.zoom = (
                self._pre_cinematic_zoom
                + (cinematic_zoom - self._pre_cinematic_zoom) * zoom_factor
            )
            if self._dual_tech_controller.is_complete:
                # Restore camera and clear the slot. Camera shake from
                # the impact (triggered via on_impact callback) has its
                # own decay managed by SceneCamera.
                self.scene_camera.zoom = self._pre_cinematic_zoom
                self._dual_tech_controller = None

        # Phase-specific logic — pauses during dual tech cinematic (spec §5.1
        # "turn-clock pause"). Animation queue + phase timers keep ticking
        # for continuity (ambient effects + projectile physics mid-flight)
        # but phase *advancement* is frozen until the cinematic completes.
        if self.dual_tech_active:
            pass
        elif self.phase == CombatPhase.INTRO:
            # ArenaEntry drives the 1.5s scripted intro (spec §4.8). Update
            # the entry and apply camera-push-factor to SceneCamera zoom
            # (WIDE 0.85 → DEFAULT 1.0). Advance to PLAYER_INPUT when the
            # entry completes — the old INTRO_DURATION timer path is
            # retained as a fallback for defensive cases where no
            # arena_entry is present.
            if self._arena_entry is not None:
                self._arena_entry.update(dt)
                wide_zoom = 0.85
                default_zoom = 1.0
                self.scene_camera.zoom = (
                    wide_zoom
                    + (default_zoom - wide_zoom) * self._arena_entry.camera_push_factor
                )
                if self._arena_entry.is_complete:
                    self.scene_camera.zoom = default_zoom
                    self._arena_entry = None
                    self._advance_phase(CombatPhase.PLAYER_INPUT)
            elif self.phase_timer >= INTRO_DURATION:
                self._advance_phase(CombatPhase.PLAYER_INPUT)

        elif self.phase == CombatPhase.PLAYER_INPUT:
            pass  # Waiting for player input

        elif self.phase in (
            CombatPhase.ANIMATING_PLAYER,
            CombatPhase.ANIMATING_CREW,
            CombatPhase.ANIMATING_ENEMIES,
        ):
            self._process_animation_queue(dt)

        elif self.phase == CombatPhase.ROUND_END:
            if self.phase_timer >= ROUND_END_DURATION:
                if self.engine.is_combat_over():
                    self._advance_phase(CombatPhase.COMBAT_OVER)
                else:
                    self._advance_phase(CombatPhase.PLAYER_INPUT)

        elif self.phase == CombatPhase.COMBAT_OVER:
            # Continue is handled via click-anywhere and keyboard (Enter/Space)
            # No need to show the pygame_gui button — it overlaps the overlay text
            pass

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        """Render the combat view."""
        self._clamp_selected_target()
        # Background — parallax starfield reads the SceneCamera offset so
        # far/mid/near layers shift at their respective factors during
        # cinematic camera pushes + shakes (Combat overhaul §4.6). Uses
        # full offset (shake + pan) to avoid the starfield feeling
        # detached from the arena when the camera pushes in.
        bg_offset = self.scene_camera.get_offset()
        self.background.render(screen, camera_offset=bg_offset)
        screen.blit(self._bg_dim, (0, 0))

        # UI elements use shake-only offset (screen-anchored; don't pan with camera).
        # Arena content uses full camera offset (shake + pan) so the arena can lean
        # in toward player-committed actions during FOCUS states.
        shake_ox_f, shake_oy_f = self.scene_camera.get_shake_offset()
        arena_ox_f, arena_oy_f = self.scene_camera.get_offset()
        ui_ox, ui_oy = int(shake_ox_f), int(shake_oy_f)
        arena_ox, arena_oy = int(arena_ox_f), int(arena_oy_f)

        # Header
        self._render_header(screen, ui_ox, ui_oy)

        # Player panel
        self._render_player_panel(screen, ui_ox, ui_oy)

        # Enemy panels
        self._render_enemy_panels(screen, ui_ox, ui_oy)

        # Atmosphere background (dust, tint — behind ships)
        if self._atmosphere:
            # During the scripted intro (spec §4.8), fade atmosphere in
            # with the entry's tint_alpha_factor so tint + dust appear
            # progressively. After intro, render at full alpha.
            intro_factor = (
                self._arena_entry.tint_alpha_factor
                if self._arena_entry is not None
                else 1.0
            )
            self._atmosphere.render_background(screen, alpha_factor=intro_factor)

        # Combat arena (ships, damage overlays) — uses full camera offset for pan
        self._render_combat_arena(screen, arena_ox, arena_oy)

        # Atmosphere foreground (arena frame — in front of ships)
        if self._atmosphere:
            self._atmosphere.render_foreground(screen)

        # Action panel
        self._render_action_panel(screen, ui_ox, ui_oy)

        # Action queue (during player input) or combat log (during animations)
        if self.phase == CombatPhase.PLAYER_INPUT and self._action_queue is not None:
            self._render_action_queue_panel(screen, ui_ox, ui_oy)
        else:
            self._render_combat_log(screen, ui_ox, ui_oy)

        # Projectiles (rendered between arena and particles for layering)
        self._projectile_mgr.render(screen)

        # Particles
        self.particles.render(screen)

        # Floating texts
        self._render_floating_texts(screen)

        # Ultimate cinematic darken (Gap #6)
        if self._ultimate_darken_timer > 0:
            darken_alpha = int(100 * (self._ultimate_darken_timer / 0.5))
            darken_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            darken_surf.fill((0, 0, 0, darken_alpha))
            screen.blit(darken_surf, (0, 0))

        # Combo name banner (Gap #7)
        if self._combo_banner_timer > 0:
            banner_alpha = int(255 * min(1.0, self._combo_banner_timer / 0.3))
            banner_surf = self.banner_font.render(self._combo_banner_text, True, _COMBAT_COLORS["combo_banner"])
            banner_surf.set_alpha(banner_alpha)
            banner_rect = banner_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
            screen.blit(banner_surf, banner_rect)

        # Intro banner
        if self.phase == CombatPhase.INTRO:
            self._render_intro_banner(screen)

        # Tutorial narration panel
        if self._tutorial_helper and self._tutorial_helper.get_current_hint():
            self._render_combat_tutorial(screen)

        # Combat over overlay
        if self.phase == CombatPhase.COMBAT_OVER:
            self._render_combat_over_overlay(screen)

        # Dual tech cinematic renders last — stops the world. Covers
        # UI + tutorial + combat-over overlays if any are active when
        # the cinematic fires (shouldn't happen in practice, but the
        # z-order enforces it if it ever does).
        if self._dual_tech_controller is not None:
            self._dual_tech_controller.render(screen)

    # ------------------------------------------------------------------
    # Dual tech cinematic (Combat C5 §4.3)
    # ------------------------------------------------------------------

    def trigger_dual_tech(
        self,
        tech_name: str,
        dominant_element: str,
        secondary_element: str,
        left_portrait: "PortraitConfig",
        right_portrait: "PortraitConfig",
        trail_start: tuple[float, float],
        trail_end: tuple[float, float],
        is_ultimate: bool = False,
        on_impact: Optional[Callable[[], None]] = None,
    ) -> None:
        """Fire a dual tech cinematic.

        Spec §4.3 stops the world for ~3.2s (ultimates: ~4.5s) while
        the cinematic plays. Combat view constructs a controller and
        lets it own camera + screen + damage dispatch. The impact
        callback wires into the combat engine's damage resolution.

        **Trigger-detection is intentionally external** — this method
        exposes the cinematic as a primitive. Content/mechanics code
        (combat engine, combo detector, scripted encounters) decides
        which moves qualify as dual techs and invokes this method.
        """
        from spacegame.engine.dual_tech_controller import DualTechController

        self._pre_cinematic_zoom = self.scene_camera.zoom
        self._dual_tech_controller = DualTechController.from_inputs(
            tech_name=tech_name,
            dominant_element=dominant_element,
            secondary_element=secondary_element,
            left_portrait=left_portrait,
            right_portrait=right_portrait,
            trail_start=trail_start,
            trail_end=trail_end,
            is_ultimate=is_ultimate,
            on_impact=on_impact,
        )

    @property
    def dual_tech_active(self) -> bool:
        """True while a dual tech cinematic is playing."""
        return self._dual_tech_controller is not None

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle input events."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.continue_button:
                self._on_continue_pressed()
                return

        if event.type == pygame.KEYDOWN:
            self._handle_key(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Click anywhere to continue from combat over
            if self.phase == CombatPhase.COMBAT_OVER:
                self._on_continue_pressed()
                return
            self._handle_click(event.pos)

        if event.type == pygame.MOUSEMOTION:
            self._handle_hover(event.pos)

        # Scroll action tabs with mouse wheel
        if event.type == pygame.MOUSEWHEEL and self.phase == CombatPhase.PLAYER_INPUT:
            _mx, my = pygame.mouse.get_pos()
            if my >= ACTION_PANEL_Y:  # Mouse is in action panel area
                tab = self._action_tab
                active_count = len(self._categorized_moves.get(tab, []))
                max_scroll = max(0, active_count - 3)
                current = self._action_tab_scroll.get(tab, 0)
                new_scroll = max(0, min(max_scroll, current - event.y))
                self._action_tab_scroll[tab] = new_scroll

    def _handle_key(self, event: pygame.event.Event) -> None:
        """Handle keyboard shortcuts."""
        # Enter/Return/Space: continue from combat over screen
        if self.phase == CombatPhase.COMBAT_OVER and event.key in (
            pygame.K_RETURN,
            pygame.K_KP_ENTER,
            pygame.K_SPACE,
        ):
            self._on_continue_pressed()
            return

        if self.phase != CombatPhase.PLAYER_INPUT:
            return

        # Negotiate sub-menu is open — handle skill selection or cancel
        if self._negotiate_menu_open:
            skill_keys = {
                pygame.K_1: 0,
                pygame.K_2: 1,
                pygame.K_3: 2,
            }
            if event.key in skill_keys:
                idx = skill_keys[event.key]
                if idx < len(self._negotiate_skills):
                    self._select_negotiate_skill(self._negotiate_skills[idx])
                return
            if event.key == pygame.K_ESCAPE:
                self._close_negotiate_menu()
                return
            return  # Consume other keys while menu is open

        # Enter: execute queued turn
        if event.key == pygame.K_RETURN:
            self._execute_queued_turn()
            return

        # Backspace: undo last queued action
        if event.key == pygame.K_BACKSPACE:
            self._undo_last_queued_action()
            return

        # Number keys 1-6: queue moves from active tab
        key_to_idx = {
            pygame.K_1: 0,
            pygame.K_2: 1,
            pygame.K_3: 2,
            pygame.K_4: 3,
            pygame.K_5: 4,
            pygame.K_6: 5,
        }
        if event.key in key_to_idx:
            idx = key_to_idx[event.key]
            active_moves = self._categorized_moves.get(self._action_tab, [])
            scroll = self._action_tab_scroll.get(self._action_tab, 0)
            actual_idx = idx + scroll
            if actual_idx < len(active_moves) and active_moves[actual_idx].enabled:
                m = active_moves[actual_idx].move
                self._execute_player_action(m.id, move=m)
            return

        # Q/W/E/R: switch action tabs (R = Coordinated / dual techs)
        if event.key == pygame.K_q:
            self._action_tab = "attack"
            return
        if event.key == pygame.K_w:
            self._action_tab = "defend"
            return
        if event.key == pygame.K_e:
            self._action_tab = "utility"
            return
        if event.key == pygame.K_r:
            self._action_tab = "coordinated"
            return

        # Tab: cycle target
        if event.key == pygame.K_TAB:
            enemies = self.engine.get_state().enemies
            if enemies:
                next_idx = (self.selected_target_idx + 1) % len(enemies)
                self.select_target(next_idx)
            return

        # Backtick: cycle subsystem focus on current target (Combat §11.2)
        if event.key == pygame.K_BACKQUOTE:
            self._cycle_subsystem_focus()
            return

        # F or Escape: flee
        if event.key in (pygame.K_f, pygame.K_ESCAPE):
            self._attempt_flee()
            return

        # N: negotiate
        if event.key == pygame.K_n:
            self._attempt_negotiate_menu()
            return

        # B: bribe
        if event.key == pygame.K_b:
            self._attempt_bribe()
            return

        # U: activate ultimate
        if event.key == pygame.K_u:
            self._activate_ultimate()
            return

    def _handle_click(self, pos: tuple[int, int]) -> None:
        """Handle mouse clicks on move buttons and enemy cards."""
        if self.phase == CombatPhase.PLAYER_INPUT:
            # Combo buttons (select combo, replaces individual crew ability)
            for cb in self._combo_buttons:
                if cb["rect"].collidepoint(pos) and cb["enabled"]:
                    combo = cb["combo"]
                    if self._selected_combo_id == combo.id:
                        self._selected_combo_id = None  # Deselect
                    else:
                        self._selected_combo_id = combo.id
                        self._selected_crew_move_id = None  # Combo replaces crew ability
                    return

            # Crew ability buttons (toggle selection, doesn't execute yet)
            for btn in self._crew_move_buttons:
                if btn.rect.collidepoint(pos) and btn.enabled:
                    if self._selected_crew_move_id == btn.move.id:
                        self._selected_crew_move_id = None  # Deselect
                    else:
                        self._selected_crew_move_id = btn.move.id  # Select
                        self._selected_combo_id = None  # Crew ability replaces combo
                    return

            # Action tab clicks
            for tab_id, tab_rect in getattr(self, "_tab_rects", {}).items():
                if tab_rect.collidepoint(pos):
                    self._action_tab = tab_id
                    return

            # Move buttons (active tab only — queues action)
            active_moves = self._categorized_moves.get(self._action_tab, [])
            scroll = self._action_tab_scroll.get(self._action_tab, 0)
            for idx, btn in enumerate(active_moves):
                vis_idx = idx - scroll
                if 0 <= vis_idx < 3 and btn.rect.collidepoint(pos) and btn.enabled:
                    self._execute_player_action(btn.move.id, move=btn.move)
                    return

            # Execute Turn button (action queue)
            if hasattr(self, "_execute_btn_rect") and self._execute_btn_rect.collidepoint(pos):
                self._execute_queued_turn()
                return

            # Legendary: Void Release
            if getattr(self, "_void_release_rect", None) and self._void_release_rect.collidepoint(
                pos
            ):
                self._activate_void_release()
                return

            # Legendary: Overdrive
            if getattr(self, "_overdrive_rect", None) and self._overdrive_rect.collidepoint(pos):
                self._activate_overdrive()
                return

            # Undo button (action queue)
            if hasattr(self, "_undo_btn_rect") and self._undo_btn_rect.collidepoint(pos):
                self._undo_last_queued_action()
                return

            # Flee button area
            flee_rect = pygame.Rect(FLEE_BTN_X, SPECIAL_BTN_Y, SPECIAL_BTN_W, SPECIAL_BTN_H)
            if flee_rect.collidepoint(pos):
                self._attempt_flee()
                return

            # Negotiate button area
            neg_rect = pygame.Rect(
                NEGOTIATE_BTN_X,
                SPECIAL_BTN_Y,
                SPECIAL_BTN_W + 20,
                SPECIAL_BTN_H,
            )
            if neg_rect.collidepoint(pos):
                self._attempt_negotiate_menu()
                return

            # Bribe button area
            bribe_rect = pygame.Rect(
                BRIBE_BTN_X,
                SPECIAL_BTN_Y,
                SPECIAL_BTN_W,
                SPECIAL_BTN_H,
            )
            if bribe_rect.collidepoint(pos):
                self._attempt_bribe()
                return

            # Ultimate button (rendered below crew buttons when available)
            state_ult = self.engine.get_state()
            if state_ult.player.momentum and state_ult.player.momentum.ultimate_available:
                ult_y = SPECIAL_BTN_Y + SPECIAL_BTN_H + scale_y(42)
                ult_rect = pygame.Rect(
                    MOVE_BTN_X_START,
                    ult_y,
                    scale_x(280),
                    scale_y(36),
                )
                if ult_rect.collidepoint(pos):
                    self._activate_ultimate()
                    return

            # Negotiate sub-menu skill buttons
            if self._negotiate_menu_open:
                for i, skill in enumerate(self._negotiate_skills):
                    skill_rect = pygame.Rect(
                        NEGOTIATE_BTN_X,
                        SPECIAL_BTN_Y - (len(self._negotiate_skills) - i) * 30 - 5,
                        SPECIAL_BTN_W + 20,
                        26,
                    )
                    if skill_rect.collidepoint(pos):
                        self._select_negotiate_skill(skill)
                        return

            # Enemy card target selection
            state = self.engine.get_state()
            for i, enemy in enumerate(state.enemies):
                card_y = ENEMY_PANEL_Y + i * (ENEMY_CARD_H + ENEMY_CARD_GAP)
                card_rect = pygame.Rect(ENEMY_PANEL_X, card_y, ENEMY_PANEL_W, ENEMY_CARD_H)
                if card_rect.collidepoint(pos) and enemy.is_alive and not enemy.is_fled:
                    self.select_target(i)
                    return

    def _handle_hover(self, pos: tuple[int, int]) -> None:
        """Update hover state on move buttons and crew buttons."""
        self._hovered_move: Optional[CombatMove] = None
        for btn in self.move_buttons:
            btn.hovered = btn.rect.collidepoint(pos)
            if btn.hovered and btn.enabled:
                self._hovered_move = btn.move
        for btn in self._crew_move_buttons:
            btn.hovered = btn.rect.collidepoint(pos)

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def _enter_camera_state(self, state: ArenaCameraState) -> None:
        """Drive the SceneCamera toward a canonical combat state.

        FOCUS_PLAYER: camera leans left (-80, zoom 1.25) emphasizing the
        player ship during committed actions.
        FOCUS_ENEMY: camera leans right toward enemy position, zoom 1.25.
        DEFAULT: resolved viewport, zoom 1.0. 250ms relax = pacing beat.
        WIDE: zoomed-out establishing shot for cinematic moments (C5 scope).
        """
        offset, zoom, duration = _CAMERA_STATE_PARAMS[state]
        self.scene_camera.transition_to(offset=offset, zoom=zoom, duration=duration)

    def _advance_phase(self, new_phase: CombatPhase) -> None:
        """Transition to a new combat phase."""
        self.phase = new_phase
        self.phase_timer = 0.0
        self.current_animation = None
        self.animation_queue.clear()

        # Camera state follows phase. PLAYER_INPUT returns to DEFAULT (250ms
        # relax = pacing beat between turns). ANIMATING_* phases focus the
        # camera to emphasize action. ROUND_END uses DEFAULT's relax so the
        # breathing room between actions is palpable.
        if new_phase == CombatPhase.PLAYER_INPUT:
            self._enter_camera_state(ArenaCameraState.DEFAULT)
        elif new_phase in (CombatPhase.ANIMATING_PLAYER, CombatPhase.ANIMATING_CREW):
            self._enter_camera_state(ArenaCameraState.FOCUS_PLAYER)
        elif new_phase == CombatPhase.ANIMATING_ENEMIES:
            self._enter_camera_state(ArenaCameraState.FOCUS_ENEMY)
        elif new_phase == CombatPhase.ROUND_END:
            self._enter_camera_state(ArenaCameraState.DEFAULT)
        elif new_phase == CombatPhase.COMBAT_OVER:
            self._enter_camera_state(ArenaCameraState.DEFAULT)

        if new_phase == CombatPhase.PLAYER_INPUT:
            self._build_move_buttons()
            self._auto_advance_target()
            # Tutorial: provide guidance at start of each player turn
            if self._tutorial_helper:
                self._tutorial_helper.on_round_start(self.engine.get_state())
            # Initialize action queue for this turn
            from spacegame.models.action_queue import ActionQueue

            state = self.engine.get_state()
            # Volley Commander: allow one extra action per turn
            has_volley = False
            prog = state.progression
            if prog and hasattr(prog, "get_bonus"):
                has_volley = prog.get_bonus("extra_combat_action") > 0
            self._action_queue = ActionQueue(
                energy_available=state.player.energy,
                cooldowns=dict(state.player.cooldowns),
                extra_action=has_volley,
            )
            # Telegraph enemy intentions so player can react
            self.engine.telegraph_enemy_moves()
            # Snapshot dead enemies so we can detect new deaths this round
            state = self.engine.get_state()
            self._previously_dead = {i for i, e in enumerate(state.enemies) if not e.is_alive}
        elif new_phase == CombatPhase.ANIMATING_CREW:
            self._start_crew_phase()
        elif new_phase == CombatPhase.ANIMATING_ENEMIES:
            self._start_enemy_phase()
        elif new_phase == CombatPhase.ROUND_END:
            self._start_round_end()
            # Tutorial: analyze what happened this round
            if self._tutorial_helper:
                self._tutorial_helper.on_round_end(self.engine.get_state())
        elif new_phase == CombatPhase.COMBAT_OVER:
            result = self.engine.get_state().result
            if result == CombatResult.VICTORY:
                get_audio_manager().play_sfx("combat_victory")
            elif result == CombatResult.DEFEAT:
                get_audio_manager().play_sfx("combat_defeat")
            elif result in (CombatResult.FLED, CombatResult.NEGOTIATED, CombatResult.BRIBED):
                get_audio_manager().play_sfx("combat_defeat")

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def _execute_player_action(self, move_id: str, move: Optional[CombatMove] = None) -> None:
        """Queue a player move for execution this turn.

        In the multi-action system, clicking a move button adds it to
        the action queue. The turn executes when the player clicks
        EXECUTE TURN or presses Enter.
        """
        if self.phase != CombatPhase.PLAYER_INPUT:
            return

        if self._action_queue is None:
            return

        # Use provided move object (preserves slot_key), or look up by ID
        if move is None:
            move = self.engine._find_player_move(move_id)
        if move is None:
            return

        ok, msg = self._action_queue.add(move_id, self.selected_target_idx, move)
        if ok:
            try:
                get_audio_manager().play_sfx("ui_click")
            except Exception:
                pass
            # Update displayed energy to reflect queued cost
            self._displayed_player_energy = float(self._action_queue.energy_remaining)
        else:
            # Show feedback for why it couldn't be queued
            self.floating_texts.append(
                {
                    "text": msg,
                    "x": WINDOW_WIDTH // 2,
                    "y": ACTION_PANEL_Y - 20,
                    "timer": 1.5,
                    "color": _COMBAT_COLORS["notify_warning_red"],
                    "size": "small",
                }
            )

    def _activate_void_release(self) -> None:
        """Release accumulated void charge as AOE damage."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return
        state = self.engine.get_state()
        legendary = getattr(state.player, "_legendary", None)
        if not legendary or not legendary.void_release_available or legendary.void_charge <= 0:
            return
        from spacegame.models.legendary_effects import process_void_release

        damage = process_void_release(legendary)
        if damage > 0:
            # Apply AOE damage to all enemies
            for enemy in state.enemies:
                if enemy.is_alive:
                    enemy.current_hull = max(0, enemy.current_hull - damage)
            log_entry = CombatLogEntry(
                round_number=state.round_number,
                actor="player",
                action="Void Release",
                effects_applied=[f"VOID RELEASE! {damage} damage to all enemies!"],
                hit=True,
            )
            state.combat_log.append(log_entry)
            self._enqueue_animation(log_entry, source="player")
            self._append_log_line(log_entry)
            from spacegame.engine.damage_text import DamageTier
            from spacegame.engine.material_palette import get_role
            self.floating_texts.append(
                {
                    "text": f"VOID RELEASE: {damage}",
                    "x": WINDOW_WIDTH // 2,
                    "y": scale_y(200),
                    "timer": 2.4,
                    "max_timer": 2.4,
                    "color": get_role("ion_arc"),  # Spec §4.5: ion_arc violet
                    "tier": DamageTier.CINEMATIC,
                }
            )
            try:
                get_audio_manager().play_sfx("combat_explosion")
            except Exception:
                pass

    def _activate_overdrive(self) -> None:
        """Activate Overdrive: execute the current queue twice this turn."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return
        state = self.engine.get_state()
        legendary = getattr(state.player, "_legendary", None)
        if not legendary or not legendary.overdrive_available:
            return
        legendary.overdrive_available = False
        # Execute current queue, then allow the player to queue AGAIN
        if self._action_queue and not self._action_queue.is_empty:
            logs = self.engine.execute_player_turn(self._action_queue)
            for log in logs:
                self._enqueue_animation(log, source="player")
                self._append_log_line(log)
            # Reinitialize queue for second wave of actions
            from spacegame.models.action_queue import ActionQueue

            has_volley_2 = False
            prog = state.progression
            if prog and hasattr(prog, "get_bonus"):
                has_volley_2 = prog.get_bonus("extra_combat_action") > 0
            self._action_queue = ActionQueue(
                energy_available=state.player.energy,
                cooldowns=dict(state.player.cooldowns),
                extra_action=has_volley_2,
            )
            self._displayed_player_energy = float(state.player.energy)
            from spacegame.engine.damage_text import DamageTier
            from spacegame.engine.material_palette import get_role
            self.floating_texts.append(
                {
                    "text": "OVERDRIVE: Queue again!",
                    "x": WINDOW_WIDTH // 2,
                    "y": scale_y(200),
                    "timer": 2.4,
                    "max_timer": 2.4,
                    "color": get_role("voltaic_strike"),  # Spec §4.5: voltaic yellow
                    "tier": DamageTier.CINEMATIC,
                }
            )
            try:
                get_audio_manager().play_sfx("ui_confirm")
            except Exception:
                pass
        else:
            self.floating_texts.append(
                {
                    "text": "Queue actions first, then Overdrive",
                    "x": WINDOW_WIDTH // 2,
                    "y": ACTION_PANEL_Y - 20,
                    "timer": 1.5,
                    "color": _COMBAT_COLORS["notify_amber"],
                    "size": "small",
                }
            )
            legendary.overdrive_available = True  # Undo the consumption

    def _undo_last_queued_action(self) -> None:
        """Remove the last queued action."""
        if self._action_queue and not self._action_queue.is_empty:
            self._action_queue.remove_last()
            self._displayed_player_energy = float(self._action_queue.energy_remaining)
            try:
                get_audio_manager().play_sfx("ui_cancel")
            except Exception:
                pass

    def _execute_queued_turn(self) -> None:
        """Execute all queued actions and transition to animation phase."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return
        if self._action_queue is None or self._action_queue.is_empty:
            # Empty queue: skip directly to crew phase (player chose to do nothing)
            self._advance_phase(CombatPhase.ANIMATING_PLAYER)
            return

        # Dual tech cinematic trigger (Combat C5 §4.3). If any queued move
        # is a registered dual tech, fire the cinematic BEFORE engine
        # dispatch. The turn-clock pause hook (§5.1) freezes phase
        # advancement during the 3.2s cinematic so normal ANIMATING_PLAYER
        # resumes after the cinematic completes.
        self._maybe_trigger_dual_tech_cinematic()

        logs = self.engine.execute_player_turn(self._action_queue)
        for log in logs:
            self._enqueue_animation(log, source="player")
            self._append_log_line(log)

        try:
            get_audio_manager().play_sfx("ui_confirm")
        except Exception:
            pass

        self._action_queue = None  # Queue consumed
        self._advance_phase(CombatPhase.ANIMATING_PLAYER)

    def _maybe_trigger_dual_tech_cinematic(self) -> None:
        """Scan the action queue for a dual tech move; fire cinematic if found.

        The first dual tech in the queue wins — in practice there's
        usually only one per turn. Uses placeholder portrait surfaces
        (colored rectangles) until the real portrait-sprite pipeline is
        wired; element palette + tech name come from the bridge.
        """
        if self._action_queue is None:
            return
        from spacegame.models.dual_tech_cinematic_bridge import (
            get_cinematic_inputs,
            is_dual_tech_move,
        )

        for action in self._action_queue.actions:
            if not is_dual_tech_move(action.move_id):
                continue
            inputs = get_cinematic_inputs(action.move_id)
            if inputs is None:
                continue
            left_portrait = self._dual_tech_placeholder_portrait(
                inputs.crew_ids[0] if inputs.crew_ids else ""
            )
            right_portrait = self._dual_tech_placeholder_portrait(
                inputs.crew_ids[-1] if inputs.crew_ids else ""
            )
            # Trail endpoints — start at player ship, end at first enemy.
            trail_start = (float(PLAYER_SHIP_POS[0]), float(PLAYER_SHIP_POS[1]))
            trail_end = (float(ENEMY_SHIP_POS[0]), float(ENEMY_SHIP_POS[1]))
            self.trigger_dual_tech(
                tech_name=inputs.tech_name,
                dominant_element=inputs.dominant_element,
                secondary_element=inputs.secondary_element,
                left_portrait=left_portrait,
                right_portrait=right_portrait,
                trail_start=trail_start,
                trail_end=trail_end,
                is_ultimate=inputs.is_ultimate,
            )
            return

    def _dual_tech_placeholder_portrait(self, crew_id: str) -> "PortraitConfig":
        """Build a placeholder portrait for a crew member.

        Real portrait-sprite integration is tracked separately. For now
        we render a 64x80 solid rectangle in a neutral hud role so the
        slide-in reads clearly during playtests. The faction_role is
        left unset; callers can add crew-to-faction lookup later.
        """
        from spacegame.engine.dual_tech_portraits import PortraitConfig
        from spacegame.engine.material_palette import get_role

        surf = pygame.Surface((64, 80), pygame.SRCALPHA)
        # Deterministic colorization by crew id so each crew reads distinct.
        if crew_id:
            role = "hud_accent_warm" if hash(crew_id) % 2 == 0 else "hud_cyan"
        else:
            role = "hud_muted"
        color = get_role(role)
        surf.fill((*color, 230))
        return PortraitConfig(surface=surf, faction_role=role)

    # ------------------------------------------------------------------
    # Move buttons
    # ------------------------------------------------------------------

    def _build_move_buttons(self) -> None:
        """Build categorized move button lists from current player state."""
        state = self.engine.get_state()
        self.move_buttons = []
        self._categorized_moves = {"attack": [], "defend": [], "utility": [], "coordinated": []}

        # Categorize by slot_type stored in move.category
        _TAB_MAP = {
            "weapon": "attack",
            "defense": "defend",
            "coordinated": "coordinated",
        }

        # B8.4: combine equipment moves with any injected dual techs so
        # coordinated abilities render alongside weapons. Dual techs use
        # category "coordinated" and fall back to the utility tab via
        # _TAB_MAP's default.
        for move in list(state.player.equipment_moves) + list(
            getattr(state.player, "dual_tech_moves", [])
        ):
            tab = _TAB_MAP.get(move.category, "utility")

            cd_key = move.slot_key or move.id
            on_cooldown = cd_key in state.player.cooldowns
            cd_remaining = state.player.cooldowns.get(cd_key, 0)
            affordable = state.player.energy >= move.energy_cost
            enabled = affordable and not on_cooldown

            btn = _MoveButton(
                rect=pygame.Rect(0, 0, 0, 0),  # Positioned dynamically during render
                move=move,
                enabled=enabled,
                cooldown_remaining=cd_remaining,
            )
            self._categorized_moves[tab].append(btn)
            self.move_buttons.append(btn)  # Flat list for cooldown/enable refresh

        # Auto-select first tab that has moves
        if self._categorized_moves["attack"]:
            self._action_tab = "attack"
        elif self._categorized_moves["defend"]:
            self._action_tab = "defend"
        elif self._categorized_moves["utility"]:
            self._action_tab = "utility"

        # Pre-calculate button positions for the active tab
        self._update_active_tab_rects()

        # Build crew ability buttons (player chooses ONE or skips)
        self._crew_move_buttons = []
        self._selected_crew_move_id = None
        crew_btn_y = SPECIAL_BTN_Y + SPECIAL_BTN_H + scale_y(8)
        crew_btn_w = scale_x(130)
        crew_btn_h = scale_y(28)
        crew_btn_gap = scale_x(4)
        crew_btn_x = MOVE_BTN_X_START

        for i, crew_move in enumerate(state.player.crew_moves):
            bx = crew_btn_x + i * (crew_btn_w + crew_btn_gap)
            if bx + crew_btn_w > ACTION_PANEL_Y + scale_x(500):
                bx = crew_btn_x + (i % 4) * (crew_btn_w + crew_btn_gap)
            rect = pygame.Rect(bx, crew_btn_y, crew_btn_w, crew_btn_h)

            on_cooldown = crew_move.id in state.player.cooldowns
            cd_remaining = state.player.cooldowns.get(crew_move.id, 0)
            affordable = state.player.energy >= crew_move.energy_cost
            enabled = affordable and not on_cooldown

            self._crew_move_buttons.append(
                _MoveButton(
                    rect=rect, move=crew_move, enabled=enabled, cooldown_remaining=cd_remaining
                )
            )

        # Build combo buttons (Phase 9 — available when momentum >= 25%)
        self._combo_buttons = []
        self._selected_combo_id = None
        if hasattr(self, "player") and self.player:
            from spacegame.models.crew_combos import check_combo_discoveries, get_available_combos

            recruited = set()
            if hasattr(self.player, "crew_roster") and self.player.crew_roster:
                roster = self.player.crew_roster
                if hasattr(roster, "get_recruited_members"):
                    recruited = {t.id for t, _ in roster.get_recruited_members()}
            discovered = getattr(self.player, "discovered_combos", set())
            momentum_pct = state.player.momentum.current if state.player.momentum else 0.0

            newly = check_combo_discoveries(recruited, discovered)
            for combo in newly:
                discovered.add(combo.id)
                if hasattr(self.player, "discovered_combos"):
                    self.player.discovered_combos.add(combo.id)

            available = get_available_combos(
                recruited, discovered, momentum_pct, state.player.energy
            )
            combo_y = crew_btn_y + crew_btn_h + scale_y(6)
            for ci, combo in enumerate(available):
                combo_w = scale_x(200)
                combo_h = scale_y(30)
                cx = crew_btn_x + ci * (combo_w + crew_btn_gap)
                combo_rect = pygame.Rect(cx, combo_y, combo_w, combo_h)
                self._combo_buttons.append({"rect": combo_rect, "combo": combo, "enabled": True})

    def _update_active_tab_rects(self) -> None:
        """Pre-calculate button positions for the active tab's visible moves."""
        tab_header_h = scale_y(22) + scale_y(6) + scale_y(4)
        btn_y_start = ACTION_PANEL_Y + tab_header_h
        btn_w = scale_x(430)
        btn_h = scale_y(48)
        btn_gap = scale_y(4)
        btn_x = MOVE_BTN_X_START
        scroll = self._action_tab_scroll.get(self._action_tab, 0)
        active = self._categorized_moves.get(self._action_tab, [])
        for idx, btn in enumerate(active):
            vis_idx = idx - scroll
            by = btn_y_start + vis_idx * (btn_h + btn_gap)
            btn.rect = pygame.Rect(btn_x, by, btn_w, btn_h)

    # ------------------------------------------------------------------
    # Flee
    # ------------------------------------------------------------------

    def _get_flee_chance(self) -> int:
        """Calculate flee chance percentage from engine formula."""
        state = self.engine.get_state()
        player_speed = state.player.speed

        living_enemies = [e for e in state.enemies if e.is_alive and not e.is_fled]
        if not living_enemies:
            return FLEE_MAX_CHANCE

        avg_enemy_speed = sum(e.template.speed for e in living_enemies) / len(living_enemies)

        return max(
            FLEE_MIN_CHANCE,
            min(
                FLEE_MAX_CHANCE,
                FLEE_BASE_CHANCE + int((player_speed - avg_enemy_speed) * FLEE_SPEED_FACTOR),
            ),
        )

    def _attempt_flee(self) -> None:
        """Attempt to flee combat."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return

        success, logs = self.engine.attempt_flee()
        for log in logs:
            self._enqueue_animation(log, source="player")
            self._append_log_line(log)

        if success:
            # Combat is over — go to COMBAT_OVER after animations
            self._advance_phase(CombatPhase.ANIMATING_PLAYER)
        else:
            self._advance_phase(CombatPhase.ANIMATING_PLAYER)

    # ------------------------------------------------------------------
    # Ultimate
    # ------------------------------------------------------------------

    def _activate_ultimate(self) -> None:
        """Activate the ship's ultimate ability (requires 100% momentum)."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return

        state = self.engine.get_state()
        if not state.player.momentum or not state.player.momentum.ultimate_available:
            return

        logs = self.engine.execute_ultimate()
        for log in logs:
            self._enqueue_animation(log, source="player")
            self._append_log_line(log)

        # Trigger pulse animation
        self._momentum_pulse_timer = 0.8
        self._momentum_pulse_color = _COMBAT_COLORS["ult_text_pulse"]

        # Cinematic zoom effect (Gap #6)
        self._ultimate_zoom_timer = 0.4
        self._ultimate_darken_timer = 0.5

        # Emit celebration particles at player ship position
        from spacegame.engine.particles import EMPOWERED_BURST

        px = ARENA_X + ARENA_W // 4
        py = ARENA_Y + ARENA_H // 2
        self.particles.emit(px, py, EMPOWERED_BURST)

        # Audio cue (Gap #5)
        get_audio_manager().play_sfx("combat_victory")

        self._advance_phase(CombatPhase.ANIMATING_PLAYER)

    # ------------------------------------------------------------------
    # Negotiate
    # ------------------------------------------------------------------

    def _is_negotiate_available(self) -> bool:
        """Check if negotiate action is available."""
        return not self.engine.get_state().negotiate_used

    def _attempt_negotiate_menu(self) -> None:
        """Open the negotiate skill selection sub-menu."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return
        if not self._is_negotiate_available():
            return
        self._open_negotiate_menu()

    def _open_negotiate_menu(self) -> None:
        """Show the negotiate skill selection sub-menu."""
        self._negotiate_menu_open = True

    def _close_negotiate_menu(self) -> None:
        """Close the negotiate sub-menu without acting."""
        self._negotiate_menu_open = False

    def _select_negotiate_skill(self, skill_id: str) -> None:
        """Execute negotiate with the chosen social skill."""
        self._negotiate_menu_open = False
        _success, _msg, logs = self.engine.attempt_negotiate(skill_id, self.social_manager)
        for log in logs:
            self._enqueue_animation(log, source="player")
            self._append_log_line(log)
        self._advance_phase(CombatPhase.ANIMATING_PLAYER)

    # ------------------------------------------------------------------
    # Bribe
    # ------------------------------------------------------------------

    def _is_bribe_available(self) -> bool:
        """Check if bribe action is available."""
        return not self.engine.get_state().bribe_used

    def _attempt_bribe(self) -> None:
        """Attempt to bribe enemies to end combat."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return
        if not self._is_bribe_available():
            return

        success, cost, logs = self.engine.attempt_bribe(self._bribe_credits_available)
        for log in logs:
            self._enqueue_animation(log, source="player")
            self._append_log_line(log)

        if success:
            self._bribe_cost = cost

        self._advance_phase(CombatPhase.ANIMATING_PLAYER)

    def _get_bribe_display_cost(self) -> str:
        """Get bribe cost text for button display."""
        state = self.engine.get_state()
        if state.revealed_bribe_cost >= 0:
            return f"{state.revealed_bribe_cost} CR"
        return "? CR"

    # ------------------------------------------------------------------
    # Crew moves info
    # ------------------------------------------------------------------

    def _get_crew_move_info(self) -> list[dict]:
        """Get display info for crew auto-moves."""
        state = self.engine.get_state()
        result = []
        for move in state.player.crew_moves:
            result.append(
                {
                    "id": move.id,
                    "name": move.name,
                    "skipped": move.id in self.skip_crew_ids,
                }
            )
        return result

    def _toggle_skip_crew(self, move_id: str) -> None:
        """Toggle whether a crew move is skipped this round."""
        if move_id in self.skip_crew_ids:
            self.skip_crew_ids.discard(move_id)
        else:
            self.skip_crew_ids.add(move_id)

    # ------------------------------------------------------------------
    # Crew phase
    # ------------------------------------------------------------------

    def _start_crew_phase(self) -> None:
        """Execute the player's chosen crew ability or combo (or skip if none selected)."""
        # Combo takes priority over individual crew ability
        if self._selected_combo_id:
            # Set combo banner (Gap #7)
            from spacegame.models.crew_combos import get_combo_by_id

            combo = get_combo_by_id(self._selected_combo_id)
            if combo:
                self._combo_banner_text = combo.name.upper()
                self._combo_banner_timer = 1.5
                get_audio_manager().play_sfx("ui_confirm")
            logs = self.engine.execute_crew_combo(self._selected_combo_id)
            self._selected_combo_id = None
            self._selected_crew_move_id = None
        else:
            logs = self.engine.execute_crew_moves(chosen_move_id=self._selected_crew_move_id)
            # Reset selection for next turn
            self._selected_crew_move_id = None
            self._selected_combo_id = None
        if not logs:
            # No crew move executed — skip straight to enemy phase
            self._advance_phase(CombatPhase.ANIMATING_ENEMIES)
            return
        for log in logs:
            self._enqueue_animation(log, source="crew")
            self._append_log_line(log)

    # ------------------------------------------------------------------
    # Enemy phase
    # ------------------------------------------------------------------

    def _start_enemy_phase(self) -> None:
        """Execute enemy turns and enqueue their animations."""
        logs = self.engine.execute_enemy_turns()
        if not logs:
            self._advance_phase(CombatPhase.ROUND_END)
            return
        for log in logs:
            self._enqueue_animation(log, source="enemy")
            self._append_log_line(log)

    # ------------------------------------------------------------------
    # Round end
    # ------------------------------------------------------------------

    def _start_round_end(self) -> None:
        """Process end-of-round effects."""
        logs = self.engine.end_round()
        for log in logs:
            self._append_log_line(log)

    # ------------------------------------------------------------------
    # Animation queue
    # ------------------------------------------------------------------

    def _enqueue_animation(self, log_entry: CombatLogEntry, source: str) -> None:
        """Add an animation event to the queue."""
        self.animation_queue.append(AnimationEvent(log_entry=log_entry, source=source))

    def _process_animation_queue(self, dt: float) -> None:
        """Process the animation queue one event at a time."""
        if self.current_animation is None:
            if not self.animation_queue:
                self._on_animation_phase_complete()
                return
            self.current_animation = self.animation_queue.pop(0)
            self.animation_timer = 0.0
            self._start_animation_effects(self.current_animation)

        self.animation_timer += dt
        if self.animation_timer >= self.current_animation.duration:
            self.current_animation = None

    def _start_animation_effects(self, anim: AnimationEvent) -> None:
        """Trigger visual effects for an animation event.

        For offensive actions, spawns a projectile that travels from source
        to target. Impact effects (particles, shake, damage numbers) are
        deferred to the projectile's on_impact callback.
        """
        log = anim.log_entry
        is_player_source = anim.source == "player"
        is_enemy_source = anim.source == "enemy"

        # Determine target position for impact effects
        if is_player_source:
            target_x = float(ENEMY_PANEL_X + ENEMY_PANEL_W // 2)
            target_y = float(
                ENEMY_PANEL_Y
                + self.selected_target_idx * (ENEMY_CARD_H + ENEMY_CARD_GAP)
                + ENEMY_CARD_H // 2
            )
        else:
            target_x = float(PLAYER_PANEL_X + PLAYER_PANEL_W // 2)
            target_y = float(PLAYER_PANEL_Y + PLAYER_PANEL_H // 3)

        # Source position for projectiles (ship position in arena)
        if is_player_source:
            source_x = float(PLAYER_SHIP_POS[0])
            source_y = float(PLAYER_SHIP_POS[1])
            impact_x = float(ENEMY_SHIP_POS[0])
            impact_y = float(ENEMY_SHIP_POS[1])
        else:
            source_x = float(ENEMY_SHIP_POS[0])
            source_y = float(ENEMY_SHIP_POS[1])
            impact_x = float(PLAYER_SHIP_POS[0])
            impact_y = float(PLAYER_SHIP_POS[1])

        # Determine weapon element from the move name
        # Check player equipment + crew moves for a matching name
        from spacegame.models.combat import WeaponElement as _WE

        move_element = _WE.KINETIC  # Default
        if hasattr(self, "engine") and self.engine:
            cs = self.engine.get_state()
            all_moves = (
                list(cs.player.equipment_moves)
                + list(cs.player.crew_moves)
                + list(getattr(cs.player, "dual_tech_moves", []))
            )
            for m in all_moves:
                if m.name == log.action:
                    move_element = m.element
                    break

        # Classify weapon type from action text
        action_lower = log.action.lower()
        has_shield_text = any("shield" in e.lower() for e in log.effects_applied)
        has_hull_text = any(
            "hull" in e.lower() and "restore" in e.lower() for e in log.effects_applied
        )
        has_shield_restore = any(
            "shield" in e.lower() and "restore" in e.lower() for e in log.effects_applied
        )
        is_healing = has_hull_text or has_shield_restore

        # Store action text for arena display
        self._arena_action_text = log.action
        self._arena_action_timer = 0.5

        if is_healing:
            # Healing/restore — no projectile, immediate particle effect
            if has_hull_text:
                self.particles.emit(
                    source_x if is_player_source else impact_x,
                    source_y if is_player_source else impact_y,
                    HEAL_SPARKLE,
                )
            else:
                self.particles.emit(
                    source_x if is_player_source else impact_x,
                    source_y if is_player_source else impact_y,
                    SHIELD_RESTORE,
                )
            return

        # Non-attack actions (Flee, Frozen, system) — floating text only, no projectile
        non_attack_actions = {"Flee", "Frozen", "Fled"}
        if log.action in non_attack_actions or log.actor == "system":
            ty = target_y if is_enemy_source else source_y
            tx = target_x if is_enemy_source else source_x
            for effect_text in log.effects_applied:
                if "FROZEN" in effect_text:
                    text_color = _COMBAT_COLORS["dmg_cryo"]  # Ice blue
                elif "Escaped" in effect_text:
                    text_color = Colors.GREEN
                elif "Failed" in effect_text:
                    text_color = _COMBAT_COLORS["dmg_generic_warm"]  # Warm red
                else:
                    text_color = Colors.TEXT_SECONDARY
                self.floating_texts.append(
                    {
                        "text": effect_text,
                        "x": tx,
                        "y": ty,
                        "color": text_color,
                        "timer": 1.0,
                        "max_timer": 1.0,
                        "vy": -30.0,
                    }
                )
                ty -= 20
            return

        # Build impact callback — deferred until projectile arrives
        def _on_impact() -> None:
            # Floating damage/effect text
            ty = target_y
            for effect_text in log.effects_applied:
                # Split module hit info out of damage text for distinct display
                display_text = effect_text
                module_text = ""
                if "[" in effect_text and "]" in effect_text:
                    bracket_start = effect_text.index("[")
                    bracket_end = effect_text.index("]") + 1
                    module_text = effect_text[bracket_start + 1 : bracket_end - 1]
                    display_text = effect_text[:bracket_start].rstrip()

                # Color coding for defensive identity feedback
                if "Armor absorbed" in display_text:
                    text_color = _COMBAT_COLORS["dmg_armor_deflect"]  # Silver — armor deflection
                elif "GRAZE" in display_text:
                    text_color = _COMBAT_COLORS["dmg_near_miss"]  # Orange — near miss
                elif "Shield regen" in display_text:
                    text_color = _COMBAT_COLORS["dmg_shield_regen"]  # Cyan — shield regen
                elif "Overclock" in display_text:
                    text_color = _COMBAT_COLORS["dmg_energy_boost"]  # Purple — energy boost
                elif "Momentum" in display_text:
                    text_color = _COMBAT_COLORS["dmg_momentum"]  # Gold — momentum threshold
                    get_audio_manager().play_sfx("ui_confirm")
                elif "FROZEN" in display_text:
                    text_color = _COMBAT_COLORS["dmg_cryo"]  # Ice blue — cryo freeze
                elif "Chill" in display_text:
                    text_color = _COMBAT_COLORS["dmg_chill"]  # Light blue — chill stacks
                elif "Burn" in display_text and "x" in display_text:
                    text_color = _COMBAT_COLORS["dmg_burn"]  # Warm orange — burn stacks
                elif "Suppressed" in display_text:
                    text_color = _COMBAT_COLORS["dmg_voltaic"]  # Lavender — voltaic suppress
                elif "Counterstrike" in display_text:
                    text_color = _COMBAT_COLORS["dmg_counterstrike"]  # Cyan — ghost counterstrike
                elif "SHIELDS BROKEN" in display_text:
                    text_color = _COMBAT_COLORS["dmg_vulnerability"]  # Red — sentinel vulnerability
                else:
                    text_color = Colors.RED if is_player_source else Colors.YELLOW
                # Tier classification per spec §4.7 — threshold/cinematic
                # events get the heavier weight treatment.
                from spacegame.engine.damage_text import classify_damage_text
                auto_tier = classify_damage_text(display_text)
                ft_entry: dict = {
                    "text": display_text,
                    "x": target_x,
                    "y": ty,
                    "color": text_color,
                    "timer": 0.8,
                    "max_timer": 0.8,
                    "vy": -40.0,
                }
                # Only attach tier for above-standard classifications so the
                # dispatcher falls back to the legacy info_font path for the
                # common case (no visual regression on standard damage).
                from spacegame.engine.damage_text import DamageTier
                if auto_tier in (DamageTier.THRESHOLD, DamageTier.CINEMATIC):
                    ft_entry["tier"] = auto_tier
                    # Threshold duration matches cfg.total_duration so the
                    # pop + hold + fade reads cleanly.
                    from spacegame.engine.damage_text import get_tier_config
                    total = get_tier_config(auto_tier).total_duration
                    ft_entry["timer"] = total
                    ft_entry["max_timer"] = total
                self.floating_texts.append(ft_entry)
                ty -= 20

                # Module hit: separate line in warm orange
                if module_text:
                    self.floating_texts.append(
                        {
                            "text": module_text,
                            "x": target_x,
                            "y": ty,
                            "color": _COMBAT_COLORS["dmg_burn"],  # Warm orange — module damage
                            "timer": 1.0,
                            "max_timer": 1.0,
                            "vy": -30.0,
                        }
                    )
                    ty -= 20

            # Camera shake — severity based on action
            is_missile = "missile" in action_lower or "torpedo" in action_lower
            shake_intensity = 4.5 if is_missile else 3.0
            shake_duration = 0.2 if is_missile else 0.15
            self.scene_camera.add_shake(amplitude=shake_intensity, duration=shake_duration)

            # Impact particles
            if has_shield_text and not has_shield_restore:
                self.particles.emit(impact_x, impact_y, SHIELD_IMPACT)
                get_audio_manager().play_sfx("combat_shield")
                # Shield ripple on the target
                if is_player_source:
                    self._shield_renderer.trigger_ripple(
                        f"enemy_{self.selected_target_idx}", angle=math.pi
                    )
                else:
                    self._shield_renderer.trigger_ripple("player", angle=0.0)
            elif is_missile:
                self.particles.emit(impact_x, impact_y, MISSILE_EXPLOSION)
                get_audio_manager().play_sfx("combat_missile")
            else:
                self.particles.emit(impact_x, impact_y, LASER_HIT)
                get_audio_manager().play_sfx("combat_laser")

            # Armor deflection particle burst (Phase 12E)
            has_armor_text = any("Armor absorbed" in eff for eff in log.effects_applied)
            if has_armor_text:
                self.particles.emit(impact_x, impact_y, SPARK_BURST)

            # Shield regen pulse particles (Phase 12E — on end-of-round regen)
            has_regen_text = any("Shield regen" in eff for eff in log.effects_applied)
            if has_regen_text:
                px = PLAYER_SHIP_POS[0]
                py = PLAYER_SHIP_POS[1]
                self.particles.emit(px, py, SHIELD_RESTORE)

            # Dodge jink animation (Phase 12E — player ship lateral offset on dodge/graze)
            has_dodge = any("Missed" in eff or "GRAZE" in eff for eff in log.effects_applied)
            if has_dodge and is_enemy_source:
                self._dodge_jink_timer = 0.15
                self._dodge_jink_direction = 1 if self._rng_visual.random() > 0.5 else -1

            # Hit recoil on the target ship
            if is_player_source:
                self._damage_state_mgr.trigger_recoil(
                    f"enemy_{self.selected_target_idx}", from_right=False
                )
            elif is_enemy_source:
                self._damage_state_mgr.trigger_recoil("player", from_right=True)

            # Flash timers
            if is_player_source:
                if self.selected_target_idx < len(self._enemy_flash_timers):
                    self._enemy_flash_timers[self.selected_target_idx] = 0.15
                    if has_shield_text and not has_shield_restore:
                        if self.selected_target_idx < len(self._enemy_shield_flashes):
                            self._enemy_shield_flashes[self.selected_target_idx] = 0.2
                    else:
                        if self.selected_target_idx < len(self._enemy_sprite_flashes):
                            self._enemy_sprite_flashes[self.selected_target_idx] = 0.12
                            get_audio_manager().play_sfx("combat_hit")
            elif is_enemy_source:
                self._player_flash_timer = 0.15
                if has_shield_text and not has_shield_restore:
                    self._player_shield_flash = 0.2
                else:
                    self._player_sprite_flash = 0.12
                    get_audio_manager().play_sfx("combat_hit")

            # Check for enemy deaths
            if is_player_source or anim.source == "crew":
                self._check_enemy_deaths()

        # Choose projectile type based on element and action keywords.
        # Element string is forwarded to the projectile so its color
        # resolves through the canonical palette per spec §4.5.
        def _spawn_projectile(hit: bool) -> None:
            cb = _on_impact if hit else None
            src = (source_x, source_y)
            tgt = (impact_x, impact_y)
            element_str = move_element.value if move_element is not None else None

            if "missile" in action_lower or "torpedo" in action_lower:
                self._projectile_mgr.spawn_missile(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )
            elif move_element == _WE.PLASMA:
                # Plasma: missile-style fireball with arc
                self._projectile_mgr.spawn_missile(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )
            elif move_element == _WE.ION:
                # Ion: fast laser-style bolt
                self._projectile_mgr.spawn_laser(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )
            elif move_element == _WE.CRYO:
                # Cryo: laser-style shard
                self._projectile_mgr.spawn_laser(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )
            elif move_element == _WE.VOLTAIC:
                # Voltaic: cannon-style burst
                self._projectile_mgr.spawn_cannon(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )
            elif "cannon" in action_lower or "kinetic" in action_lower or "burst" in action_lower:
                self._projectile_mgr.spawn_cannon(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )
            else:
                self._projectile_mgr.spawn_laser(
                    src, tgt, on_impact=cb, hit=hit, element=element_str
                )

        if log.hit:
            _spawn_projectile(hit=True)
        else:
            _spawn_projectile(hit=False)
            # Show "MISS" text immediately (no impact to defer to)
            self.floating_texts.append(
                {
                    "text": "MISS",
                    "x": target_x,
                    "y": target_y,
                    "color": Colors.TEXT_SECONDARY,
                    "timer": 0.6,
                    "max_timer": 0.6,
                    "vy": -30.0,
                }
            )

    def _check_enemy_deaths(self) -> None:
        """Check if any enemies just died and trigger destroy animations."""
        state = self.engine.get_state()

        for idx, enemy in enumerate(state.enemies):
            if idx in self._destroying_enemies:
                continue  # Already destroying
            if idx in self._previously_dead:
                continue  # Was already dead before this round
            if not enemy.is_alive and not enemy.is_fled:
                # Newly dead enemy — start spectacular destruction sequence
                from spacegame.engine.combat_vfx import DestructionSequence

                living_before = sum(
                    1
                    for ii in range(idx)
                    if state.enemies[ii].is_alive and not state.enemies[ii].is_fled
                )
                living_total = sum(1 for e in state.enemies if e.is_alive and not e.is_fled)
                enemy_x = ENEMY_SHIP_POS[0]
                enemy_y = (
                    ENEMY_SHIP_POS[1] + (living_before - living_total // 2) * ENEMY_STACK_SPACING
                )

                # Determine sprite radius from ship scale
                scale = self._get_combat_ship_scale("enemy", danger_tier=enemy.template.danger_tier)
                sprite_radius = 16 * scale  # 32x32 native * scale / 2

                # Boss death: larger destruction (Gap #8)
                boss_mult = 1.5 if enemy.template.is_boss else 1.0
                seq = DestructionSequence(
                    float(enemy_x),
                    float(enemy_y),
                    int(sprite_radius * boss_mult),
                )
                self._destruction_sequences.append(seq)
                if enemy.template.is_boss:
                    # Extra camera shake for boss death
                    self.scene_camera.add_shake(amplitude=8.0, duration=0.4)

                # Also track in old dict for backward compat (animation playback)
                anim = self._get_ship_sprite(
                    enemy.template.id, "enemy", danger_tier=enemy.template.danger_tier
                )
                if anim is not None:
                    anim.play("destroy")
                    self._destroying_enemies[idx] = (enemy_x, enemy_y, anim)

                # Explosion particles + SFX + heavy camera shake
                self.particles.emit(float(enemy_x), float(enemy_y), MISSILE_EXPLOSION)
                get_audio_manager().play_sfx("combat_explosion")
                self.scene_camera.add_shake(amplitude=8.0, duration=0.35)

                self._previously_dead.add(idx)

        # Auto-advance target away from dead enemies immediately
        self._auto_advance_target()

    def _on_animation_phase_complete(self) -> None:
        """Called when an animation phase's queue is fully drained."""
        if self.phase == CombatPhase.ANIMATING_PLAYER:
            self._advance_phase(CombatPhase.ANIMATING_CREW)
        elif self.phase == CombatPhase.ANIMATING_CREW:
            self._advance_phase(CombatPhase.ANIMATING_ENEMIES)
        elif self.phase == CombatPhase.ANIMATING_ENEMIES:
            self._advance_phase(CombatPhase.ROUND_END)

    # ------------------------------------------------------------------
    # Target selection
    # ------------------------------------------------------------------

    def select_target(self, idx: int) -> None:
        """Select an enemy target by index, skipping dead/fled enemies."""
        enemies = self.engine.get_state().enemies
        if not enemies:
            return

        idx = min(idx, len(enemies) - 1)
        idx = max(idx, 0)

        # If selected enemy is dead/fled, find next living one
        if not enemies[idx].is_alive or enemies[idx].is_fled:
            idx = self._find_next_living_target(idx)

        self.selected_target_idx = idx

    def _cycle_subsystem_focus(self) -> None:
        """Cycle focused_subsystem through available subsystems on the selected enemy.

        Cycle order: None -> tag[0] -> tag[1] -> ... -> None. Destroyed subsystems
        are skipped. No-op when the enemy has no targetable subsystems.
        """
        enemies = self.engine.get_state().enemies
        if not enemies or self.selected_target_idx >= len(enemies):
            return
        enemy = enemies[self.selected_target_idx]
        if not enemy.is_alive or enemy.is_fled:
            return
        tags = [t for t in enemy.template.targetable_subsystems if t not in enemy.subsystems_destroyed]
        if not tags:
            return
        current = getattr(enemy, "focused_subsystem", None)
        if current is None:
            enemy.focused_subsystem = tags[0]
            return
        if current in tags:
            pos = tags.index(current)
            next_pos = pos + 1
            enemy.focused_subsystem = tags[next_pos] if next_pos < len(tags) else None
        else:
            enemy.focused_subsystem = tags[0]

    def _auto_advance_target(self) -> None:
        """Auto-advance target if current target is dead/fled."""
        enemies = self.engine.get_state().enemies
        if not enemies:
            return

        idx = self.selected_target_idx
        if idx >= len(enemies) or not enemies[idx].is_alive or enemies[idx].is_fled:
            self.selected_target_idx = self._find_next_living_target(idx)

    def _find_next_living_target(self, from_idx: int) -> int:
        """Find the next living, non-fled enemy starting from from_idx."""
        enemies = self.engine.get_state().enemies
        n = len(enemies)
        for offset in range(n):
            candidate = (from_idx + offset) % n
            if enemies[candidate].is_alive and not enemies[candidate].is_fled:
                return candidate
        # All dead — return 0 as fallback
        return 0

    # ------------------------------------------------------------------
    # Combat log
    # ------------------------------------------------------------------

    def _append_log_line(self, log: CombatLogEntry) -> None:
        """Add a combat log entry to the visible log."""
        prefix = log.actor.replace(":", " ")
        line = f"[R{log.round_number}] {prefix}: {log.action}"
        self.visible_log_lines.append(line)
        for effect in log.effects_applied:
            self.visible_log_lines.append(f"    {effect}")
        # Keep last 20 lines
        if len(self.visible_log_lines) > 20:
            self.visible_log_lines = self.visible_log_lines[-20:]

    # ------------------------------------------------------------------
    # Continue / outcome
    # ------------------------------------------------------------------

    def _on_continue_pressed(self) -> None:
        """Handle continue button press after combat ends."""
        if self.next_state is None:  # Guard against double-fire during transition
            self.next_state = self._return_state

    # ------------------------------------------------------------------
    # Outcome summary
    # ------------------------------------------------------------------

    def _get_outcome_summary(self) -> dict:
        """Build outcome summary data for display."""
        state = self.engine.get_state()
        result = state.result

        color_map = {
            CombatResult.VICTORY: Colors.GREEN,
            CombatResult.DEFEAT: Colors.RED,
            CombatResult.FLED: Colors.YELLOW,
            CombatResult.NEGOTIATED: Colors.TEXT_HIGHLIGHT,
            CombatResult.BRIBED: Colors.YELLOW,
        }
        title_map = {
            CombatResult.VICTORY: "VICTORY",
            CombatResult.DEFEAT: "DEFEATED",
            CombatResult.FLED: "ESCAPED",
            CombatResult.NEGOTIATED: "NEGOTIATED",
            CombatResult.BRIBED: "BRIBED",
        }

        xp_gained = 0
        loot: dict[str, int] = {}
        rare_loot: dict[str, int] = {}
        if result == CombatResult.VICTORY:
            xp_gained = sum(e.template.xp_reward for e in state.enemies)
            # Roll loot from all defeated enemies
            for enemy in state.enemies:
                if not enemy.is_alive and enemy.template.loot_table:
                    enemy_loot = _roll_loot(
                        enemy.template.loot_table,
                        seed=state.encounter.encounter_seed + hash(enemy.template.id),
                    )
                    for cid, qty in enemy_loot.items():
                        loot[cid] = loot.get(cid, 0) + qty
                # Roll rare loot separately
                if not enemy.is_alive and enemy.template.rare_loot:
                    enemy_rare = _roll_loot(
                        enemy.template.rare_loot,
                        seed=state.encounter.encounter_seed + hash(enemy.template.id) + 7919,
                    )
                    for cid, qty in enemy_rare.items():
                        rare_loot[cid] = rare_loot.get(cid, 0) + qty

        return {
            "result": result,
            "title": title_map.get(result, result.value.upper()),
            "color": color_map.get(result, Colors.TEXT_PRIMARY),
            "xp_gained": xp_gained,
            "loot": loot,
            "rare_loot": rare_loot,
            "rounds": state.round_number,
            "enemies_defeated": sum(1 for e in state.enemies if not e.is_alive),
            "enemies_fled": sum(1 for e in state.enemies if e.is_fled),
        }

    # ------------------------------------------------------------------
    # Displayed bar smoothing
    # ------------------------------------------------------------------

    def _update_displayed_bars(self, dt: float) -> None:
        """Lerp displayed bar values toward actual values."""
        state = self.engine.get_state()
        speed = BAR_LERP_SPEED

        self._displayed_player_hull = self._lerp_toward(
            self._displayed_player_hull, float(state.player.hull), speed * dt
        )
        self._displayed_player_shields = self._lerp_toward(
            self._displayed_player_shields, float(state.player.shields), speed * dt
        )
        self._displayed_player_energy = self._lerp_toward(
            self._displayed_player_energy, float(state.player.energy), speed * dt
        )
        if state.player.momentum:
            self._displayed_player_momentum = self._lerp_toward(
                self._displayed_player_momentum,
                state.player.momentum.current * 100.0,  # Display as 0-100
                speed * dt * 2,  # Faster lerp for momentum (feels responsive)
            )

        for i, enemy in enumerate(state.enemies):
            if i < len(self._displayed_enemy_hulls):
                self._displayed_enemy_hulls[i] = self._lerp_toward(
                    self._displayed_enemy_hulls[i], float(enemy.current_hull), speed * dt
                )
            if i < len(self._displayed_enemy_shields):
                self._displayed_enemy_shields[i] = self._lerp_toward(
                    self._displayed_enemy_shields[i],
                    float(enemy.current_shields),
                    speed * dt,
                )

    @staticmethod
    def _lerp_toward(current: float, target: float, speed_dt: float) -> float:
        """Move current toward target with exponential decay.

        Big differences snap quickly; small differences settle smoothly.
        Snaps to exact target when within 0.5 to avoid asymptotic drift.
        """
        diff = target - current
        if abs(diff) < 0.5:
            return target
        return current + diff * min(speed_dt, 1.0)

    # ------------------------------------------------------------------
    # Enemy display state
    # ------------------------------------------------------------------

    def _get_enemy_display_state(self, idx: int) -> dict:
        """Get display info for an enemy card."""
        state = self.engine.get_state()
        if idx >= len(state.enemies):
            return {
                "name": "???",
                "alive": False,
                "fled": False,
                "selected": False,
                "hull": 0,
                "max_hull": 1,
                "shields": 0,
                "max_shields": 0,
                "behavior": "aggressive",
                "active_effects": [],
            }
        enemy = state.enemies[idx]
        return {
            "name": enemy.template.name,
            "alive": enemy.is_alive,
            "fled": enemy.is_fled,
            "selected": idx == self.selected_target_idx,
            "hull": enemy.current_hull,
            "max_hull": enemy.template.hull,
            "shields": enemy.current_shields,
            "max_shields": enemy.template.shields,
            "behavior": enemy.template.behavior.value,
            "active_effects": enemy.active_effects,
        }

    # ------------------------------------------------------------------
    # Render helpers
    # ------------------------------------------------------------------

    def _render_header(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render header bar with round counter and phase banner."""
        state = self.engine.get_state()
        round_text = f"Round {state.round_number}"
        round_surf = self.header_font.render(round_text, True, Colors.TEXT_SECONDARY)
        screen.blit(round_surf, (20 + ox, 15 + oy))

        phase_text = self._get_phase_display_text()
        phase_surf = self.header_font.render(phase_text, True, Colors.TEXT_HIGHLIGHT)
        phase_rect = phase_surf.get_rect(center=(WINDOW_WIDTH // 2 + ox, 25 + oy))
        screen.blit(phase_surf, phase_rect)

        # Boss health bar (wide bar across top of arena)
        for enemy in state.enemies:
            if enemy.template.is_boss and enemy.is_alive:
                self._render_boss_health_bar(screen, enemy, ox, oy)
                break  # Only one boss bar

    def _render_boss_health_bar(
        self,
        screen: pygame.Surface,
        boss: "EnemyShip",
        ox: int,
        oy: int,
    ) -> None:
        """Render a wide health bar across the top of the arena for a boss enemy."""
        bar_x = ARENA_X + scale_x(20) + ox
        bar_y = 45 + oy
        bar_w = ARENA_W - scale_x(40)
        bar_h = scale_y(18)

        # Boss name + phase name
        phase_name = ""
        if boss.template.phases and boss.current_phase_idx < len(boss.template.phases):
            phase_name = f" — {boss.template.phases[boss.current_phase_idx].name}"
        name_text = f"{boss.template.name}{phase_name}"
        name_surf = self.small_font.render(name_text, True, _COMBAT_COLORS["boss_header"])
        screen.blit(name_surf, (bar_x, bar_y - 14))

        # Background
        bg_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(screen, _COMBAT_COLORS["boss_bg_dark"], bg_rect)
        pygame.draw.rect(screen, _COMBAT_COLORS["boss_bg_border"], bg_rect, 1)

        # HP fill (hull + shields combined)
        total_max = boss.max_hull + boss.max_shields
        total_current = boss.current_hull + boss.current_shields
        if total_max > 0:
            ratio = total_current / total_max
            fill_w = int((bar_w - 2) * ratio)

            # Color shifts with HP: red → orange → red
            if ratio > 0.5:
                bar_color = _COMBAT_COLORS["boss_bar_low"]  # Dark red
            elif ratio > 0.25:
                bar_color = _COMBAT_COLORS["boss_bar_mid"]  # Orange-red
            else:
                bar_color = _COMBAT_COLORS["boss_bar_danger"]  # Bright red — danger

            if fill_w > 0:
                pygame.draw.rect(screen, bar_color, (bar_x + 1, bar_y + 1, fill_w, bar_h - 2))

            # Phase threshold markers
            for phase in boss.template.phases:
                if phase.hp_threshold < 1.0:
                    mx = bar_x + 1 + int((bar_w - 2) * phase.hp_threshold)
                    pygame.draw.line(screen, _COMBAT_COLORS["boss_header"], (mx, bar_y), (mx, bar_y + bar_h), 1)

            # HP text
            hp_text = f"{total_current}/{total_max}"
            hp_surf = self.small_font.render(hp_text, True, Colors.TEXT_PRIMARY)
            hp_rect = hp_surf.get_rect(center=(bar_x + bar_w // 2, bar_y + bar_h // 2))
            screen.blit(hp_surf, hp_rect)

    def _render_player_panel(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render player status panel with health, shield, and energy bars."""
        state = self.engine.get_state()
        px = PLAYER_PANEL_X + ox
        py = PLAYER_PANEL_Y + oy

        # Panel background
        draw_panel(
            screen,
            (px, py, PLAYER_PANEL_W, PLAYER_PANEL_H),
            alpha=200,
            bg_color=_COMBAT_COLORS["panel_modal_bg"],
            border_radius=4,
        )

        # Identity accent line at top of panel (Phase 12E)
        identity_colors = {
            "juggernaut": _COMBAT_COLORS["archetype_juggernaut"],  # Bronze
            "sentinel": _COMBAT_COLORS["archetype_sentinel"],  # Cyan
            "ghost": _COMBAT_COLORS["archetype_ghost"],  # Purple
        }
        id_accent = identity_colors.get(state.player.defensive_identity)
        if id_accent:
            pygame.draw.rect(screen, id_accent, (px, py, PLAYER_PANEL_W, 2))

        # Flash overlay on hit
        if self._player_flash_timer > 0:
            flash_alpha = int(80 * (self._player_flash_timer / 0.15))
            flash_surf = pygame.Surface((PLAYER_PANEL_W, PLAYER_PANEL_H), pygame.SRCALPHA)
            flash_surf.fill((220, 50, 50, flash_alpha))
            screen.blit(flash_surf, (px, py))

        # Ship name header
        ship_name = self.player.display_ship_name
        name_surf = self.header_font.render(ship_name, True, Colors.TEXT_HIGHLIGHT)
        name_rect = name_surf.get_rect(centerx=px + PLAYER_PANEL_W // 2, top=py + 8)
        screen.blit(name_surf, name_rect)

        # Separator line
        sep_y = py + 32
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (px + 8, sep_y),
            (px + PLAYER_PANEL_W - 8, sep_y),
        )

        # Bars start below header
        bar_x = px + 10
        bar_w = PLAYER_PANEL_W - 20
        y = sep_y + 12

        # Hull bar (label color-coded green to match bar)
        hull_ratio = (
            self._displayed_player_hull / state.player.max_hull if state.player.max_hull > 0 else 0
        )
        hull_color = _bar_color_for_ratio(hull_ratio)
        self._render_bar(
            screen,
            bar_x,
            y,
            bar_w,
            BAR_HEIGHT,
            self._displayed_player_hull,
            state.player.max_hull,
            hull_color,
            "Hull",
            label_color=Colors.GREEN,
        )
        y += BAR_HEIGHT + 8

        # Shield bar (label color-coded blue)
        self._render_bar(
            screen,
            bar_x,
            y,
            bar_w,
            BAR_HEIGHT,
            self._displayed_player_shields,
            state.player.max_shields,
            SHIELD_COLOR,
            "Shld",
            label_color=SHIELD_COLOR,
        )
        y += BAR_HEIGHT + 8

        # Energy bar (label color-coded purple)
        self._render_bar(
            screen,
            bar_x,
            y,
            bar_w,
            BAR_HEIGHT,
            self._displayed_player_energy,
            state.player.max_energy,
            ENERGY_COLOR,
            "Engy",
            label_color=ENERGY_COLOR,
        )
        y += BAR_HEIGHT + 8

        # Momentum bar
        if state.player.momentum:
            self._render_momentum_bar(screen, bar_x, y, bar_w, state)
            y += BAR_HEIGHT + 16
        else:
            y += 6

        # Defensive identity status (Phase 12A)
        identity = state.player.defensive_identity
        if identity:
            identity_colors = {
                "juggernaut": _COMBAT_COLORS["archetype_juggernaut"],  # Bronze
                "sentinel": _COMBAT_COLORS["archetype_sentinel"],  # Cyan
                "ghost": _COMBAT_COLORS["archetype_ghost"],  # Purple
            }
            id_color = identity_colors.get(identity, Colors.TEXT_SECONDARY)
            id_label = identity.upper()

            # Active passive indicators
            passive_texts: list[tuple[str, tuple[int, int, int]]] = []
            if identity == "juggernaut":
                if state.player.armor > 0:
                    passive_texts.append((f"Armor: {state.player.armor}", id_color))
                if state.player.hull_ratio < 0.25:
                    passive_texts.append(("LAST STAND!", _COMBAT_COLORS["passive_last_stand"]))
                elif state.player.hull_ratio > 0.75:
                    passive_texts.append(("Integrity: +5% DR", _COMBAT_COLORS["passive_positive_dim"]))
            elif identity == "sentinel":
                if state.player.shield_regen > 0:
                    passive_texts.append((f"Regen: +{state.player.shield_regen}/turn", id_color))
                if state.player.shield_break_vulnerable:
                    passive_texts.append(("SHIELDS BROKEN!", _COMBAT_COLORS["passive_last_stand"]))
            elif identity == "ghost":
                if state.player.counterstrike_stacks > 0:
                    pct = state.player.counterstrike_stacks * 10
                    passive_texts.append((f"Counterstrike: +{pct}%", _COMBAT_COLORS["passive_counterstrike_bright"]))
                if state.player.evasion_decay > 0:
                    passive_texts.append(("Shaken: -5 evasion", _COMBAT_COLORS["dmg_near_miss"]))

            id_surf = self.small_font.render(id_label, True, id_color)
            screen.blit(id_surf, (bar_x, y))
            y += 16
            for pt_text, pt_color in passive_texts:
                pt_surf = self.small_font.render(pt_text, True, pt_color)
                screen.blit(pt_surf, (bar_x + 8, y))
                y += 14
            y += 4

        # Active effects badges (icon + text)
        if state.player.active_effects:
            effects_label = self.small_font.render("Effects:", True, Colors.TEXT_SECONDARY)
            screen.blit(effects_label, (bar_x, y))
            y += 18
            for effect, turns_left in state.player.active_effects:
                icon = self._sprite_mgr.get_status_icon(effect.type.value)
                ix = bar_x + 4
                if icon:
                    screen.blit(icon, (ix, y + 1))
                    ix += 14
                badge = self._effect_badge_text(effect, turns_left)
                badge_surf = self.small_font.render(badge, True, Colors.YELLOW)
                screen.blit(badge_surf, (ix, y))
                y += 16

        # Cooldowns
        active_cds = {k: v for k, v in state.player.cooldowns.items() if v > 0}
        if active_cds:
            y += 4
            cd_label = self.small_font.render("Cooldowns:", True, Colors.TEXT_SECONDARY)
            screen.blit(cd_label, (bar_x, y))
            y += 18
            for move_id, turns in active_cds.items():
                move_name = self._find_move_name(move_id, state)
                cd_text = f"{move_name}: {turns}t"
                cd_surf = self.small_font.render(cd_text, True, Colors.TEXT_SECONDARY)
                screen.blit(cd_surf, (bar_x + 4, y))
                y += 16

    def _render_enemy_panels(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render enemy status cards stacked vertically."""
        state = self.engine.get_state()

        for i, enemy in enumerate(state.enemies):
            card_y = ENEMY_PANEL_Y + i * (ENEMY_CARD_H + ENEMY_CARD_GAP) + oy
            card_x = ENEMY_PANEL_X + ox
            self._render_enemy_card(screen, enemy, i, card_x, card_y)

    def _render_enemy_card(
        self,
        screen: pygame.Surface,
        enemy: object,
        idx: int,
        x: int,
        y: int,
    ) -> None:
        """Render a single enemy status card."""
        is_selected = idx == self.selected_target_idx

        # Card background
        draw_panel(
            screen,
            (x, y, ENEMY_PANEL_W, ENEMY_CARD_H),
            alpha=200,
            bg_color=_COMBAT_COLORS["panel_modal_bg"],
            border_color=None,
            border_radius=4,
        )

        # Flash overlay on hit
        if idx < len(self._enemy_flash_timers) and self._enemy_flash_timers[idx] > 0:
            flash_alpha = int(80 * (self._enemy_flash_timers[idx] / 0.15))
            flash_surf = pygame.Surface((ENEMY_PANEL_W, ENEMY_CARD_H), pygame.SRCALPHA)
            flash_surf.fill((220, 50, 50, flash_alpha))
            screen.blit(flash_surf, (x, y))

        # Border — highlight if selected, pulsing glow
        if is_selected and enemy.is_alive and not enemy.is_fled:
            pulse_alpha = int(180 + 60 * math.sin(self.phase_timer * 5))
            border_color = (*Colors.TEXT_HIGHLIGHT[:3],)
            # Glow border via SRCALPHA surface
            glow_surf = pygame.Surface((ENEMY_PANEL_W + 4, ENEMY_CARD_H + 4), pygame.SRCALPHA)
            pygame.draw.rect(
                glow_surf,
                (*border_color, pulse_alpha),
                (0, 0, ENEMY_PANEL_W + 4, ENEMY_CARD_H + 4),
                2,
                border_radius=4,
            )
            screen.blit(glow_surf, (x - 2, y - 2))
        else:
            pygame.draw.rect(
                screen,
                Colors.UI_BORDER,
                (x, y, ENEMY_PANEL_W, ENEMY_CARD_H),
                1,
                border_radius=4,
            )

        # Defeated / fled overlay
        if not enemy.is_alive:
            self._render_enemy_overlay(screen, x, y, "DEFEATED", Colors.RED)
            return
        if enemy.is_fled:
            self._render_enemy_overlay(screen, x, y, "FLED", Colors.YELLOW)
            return

        # Small ship sprite (top-right of card).
        # Combat C4 §4.1: prefer the ShipComposite path when available,
        # fall back to the legacy AnimatedSprite so any template the
        # composite provider can't resolve still renders something.
        # Combat §11.4 (wired QA Pass 5 Tier 3.B — 2026-04-21):
        # destruction progress is now driven from hull damage. Per-instance
        # composite caching (Tier 3.A) means two enemies of the same
        # template keep their own destruction state, so this no longer
        # thrashes the cache.
        card_composite = self._enemy_composite_provider.get_composite(
            enemy.template.id, instance_key=enemy
        )
        if card_composite is not None and enemy.template.hull > 0:
            hull_ratio = max(0.0, min(1.0, enemy.current_hull / enemy.template.hull))
            card_composite.set_destruction_progress(1.0 - hull_ratio)
        card_sprite: Optional[pygame.Surface] = (
            self._enemy_composite_provider.get_surface(
                enemy.template.id, instance_key=enemy
            )
        )
        if card_sprite is None:
            card_anim = self._get_ship_sprite(
                enemy.template.id, "enemy", scale=res_scale(1)
            )
            card_sprite = card_anim.get_surface() if card_anim else None
        # Tier 3.C: module overlay (subsystem targeting feedback). Rendered
        # over the card composite only — the legacy sprite path doesn't
        # have overlay-compatible regions. Fetched lazily; state synced
        # from enemy.subsystems_destroyed + enemy.focused_subsystem.
        if card_sprite is not None and card_composite is not None:
            build = self._enemy_composite_provider.get_build(enemy.template.id)
            if build is not None and enemy.template.targetable_subsystems:
                overlay = self._enemy_overlay_provider.get_overlay(
                    template_id=enemy.template.id,
                    build=build,
                    subsystem_tags=enemy.template.targetable_subsystems,
                    instance_key=enemy,
                )
                self._enemy_overlay_provider.sync_state_from_enemy(overlay, enemy)
                # card_sprite is cached by ShipComposite — copy before
                # drawing so overlay doesn't bleed into the cached frame.
                card_sprite = card_sprite.copy()
                overlay.render(card_sprite, 0, 0, cell_size=1)
        if card_sprite is not None:
            sprite_rect = card_sprite.get_rect(topright=(x + ENEMY_PANEL_W - 6, y + 4))
            screen.blit(card_sprite, sprite_rect)

        # Enemy name
        name_surf = self.info_font.render(enemy.template.name, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (x + 8, y + 6))

        # Behavior tag
        behavior_text = enemy.template.behavior.value.capitalize()
        behavior_surf = self.small_font.render(behavior_text, True, Colors.TEXT_SECONDARY)
        screen.blit(behavior_surf, (x + 8, y + 26))

        # Subsystem focus badge (Combat §11.2) — shows currently focused subsystem
        # on the selected target. Tucked in the top-right under the sprite area.
        focused = getattr(enemy, "focused_subsystem", None)
        if is_selected and focused and focused not in enemy.subsystems_destroyed:
            focus_label = focused.replace("_", " ").upper()
            focus_surf = self.small_font.render(
                f"> {focus_label}", True, Colors.TEXT_HIGHLIGHT
            )
            focus_bg = pygame.Surface(
                (focus_surf.get_width() + 6, focus_surf.get_height() + 2), pygame.SRCALPHA
            )
            focus_bg.fill((0, 0, 0, 140))
            focus_x = x + ENEMY_PANEL_W - focus_bg.get_width() - 6
            focus_y = y + 26
            screen.blit(focus_bg, (focus_x, focus_y))
            screen.blit(focus_surf, (focus_x + 3, focus_y + 1))

        # Telegraph indicator (what enemy plans to do next)
        # Check for frozen state (Cryo 3-stack)
        is_frozen = any(hasattr(eff, "_frozen") and eff._frozen for eff, _ in enemy.active_effects)
        if is_frozen and self.phase == CombatPhase.PLAYER_INPUT:
            from spacegame.engine.fonts import FONT_XS as _FXS

            tele_font = get_font("machine", _FXS)
            tele_surf = tele_font.render("FROZEN", True, _COMBAT_COLORS["tele_frozen"])
            tele_bg = pygame.Surface(
                (tele_surf.get_width() + 8, tele_surf.get_height() + 4), pygame.SRCALPHA
            )
            tele_bg.fill((0, 0, 0, 120))
            screen.blit(tele_bg, (x + 8, y + ENEMY_CARD_H - tele_bg.get_height() - 4))
            screen.blit(tele_surf, (x + 12, y + ENEMY_CARD_H - tele_surf.get_height() - 4))
        elif (
            hasattr(enemy, "telegraphed_move")
            and enemy.telegraphed_move
            and self.phase == CombatPhase.PLAYER_INPUT
        ):
            tele_move = enemy.telegraphed_move
            # Classify the telegraphed intent
            has_dmg = any(e.type == EffectType.DAMAGE for e in tele_move.effects)
            is_def = any(
                e.type
                in (EffectType.SHIELD_RESTORE, EffectType.HULL_RESTORE, EffectType.DAMAGE_REDUCTION)
                for e in tele_move.effects
            )
            is_eva = any(
                e.type == EffectType.EVASION_MOD and e.target == EffectTarget.SELF
                for e in tele_move.effects
            )
            is_drain = any(e.type == EffectType.ENERGY_DRAIN for e in tele_move.effects)

            if is_eva:
                tele_label, tele_color = "EVADING", _COMBAT_COLORS["tele_evading"]
            elif is_def:
                tele_label, tele_color = "FORTIFYING", _COMBAT_COLORS["tele_fortifying"]
            elif is_drain:
                tele_label, tele_color = "DRAINING", _COMBAT_COLORS["tele_draining"]
            elif has_dmg and tele_move.energy_cost >= 4:
                tele_label, tele_color = "CHARGING", _COMBAT_COLORS["tele_charging"]
            elif has_dmg:
                tele_label, tele_color = "ATTACKING", _COMBAT_COLORS["tele_attacking"]
            else:
                tele_label, tele_color = "ACTING", Colors.TEXT_SECONDARY

            # Render as a small colored badge
            from spacegame.engine.fonts import FONT_XS as _FXS

            tele_font = get_font("machine", _FXS)
            tele_surf = tele_font.render(tele_label, True, tele_color)
            tele_bg = pygame.Surface(
                (tele_surf.get_width() + 8, tele_surf.get_height() + 4), pygame.SRCALPHA
            )
            tele_bg.fill((0, 0, 0, 120))
            screen.blit(tele_bg, (x + 8, y + ENEMY_CARD_H - tele_bg.get_height() - 4))
            screen.blit(tele_surf, (x + 12, y + ENEMY_CARD_H - tele_surf.get_height() - 4))

        # Bars
        bar_x = x + 8
        bar_w = ENEMY_PANEL_W - 16
        bar_y = y + 44

        # Hull bar
        displayed_hull = (
            self._displayed_enemy_hulls[idx]
            if idx < len(self._displayed_enemy_hulls)
            else float(enemy.current_hull)
        )
        hull_ratio = displayed_hull / enemy.template.hull if enemy.template.hull > 0 else 0
        hull_color = _bar_color_for_ratio(hull_ratio)
        self._render_bar(
            screen,
            bar_x,
            bar_y,
            bar_w,
            BAR_HEIGHT - 2,
            displayed_hull,
            enemy.template.hull,
            hull_color,
            "Hull",
        )

        # Damage preview ghost fill (when player hovers a move during input phase)
        if (
            is_selected
            and self.phase == CombatPhase.PLAYER_INPUT
            and hasattr(self, "_hovered_move")
            and self._hovered_move is not None
        ):
            self._render_damage_ghost(
                screen,
                bar_x,
                bar_y,
                bar_w,
                BAR_HEIGHT - 2,
                displayed_hull,
                enemy.template.hull,
                enemy,
            )

        bar_y += BAR_HEIGHT + 6

        # Shield bar
        if enemy.template.shields > 0:
            displayed_shields = (
                self._displayed_enemy_shields[idx]
                if idx < len(self._displayed_enemy_shields)
                else float(enemy.current_shields)
            )
            self._render_bar(
                screen,
                bar_x,
                bar_y,
                bar_w,
                BAR_HEIGHT - 2,
                displayed_shields,
                enemy.template.shields,
                SHIELD_COLOR,
                "Shld",
            )
            bar_y += BAR_HEIGHT + 6

        # Active effects (compact, icon + text)
        if enemy.active_effects:
            for effect, turns_left in enemy.active_effects[:2]:
                icon = self._sprite_mgr.get_status_icon(effect.type.value)
                ix = bar_x
                if icon:
                    screen.blit(icon, (ix, bar_y + 1))
                    ix += 14
                badge = self._effect_badge_text(effect, turns_left)
                badge_surf = self.small_font.render(badge, True, Colors.YELLOW)
                screen.blit(badge_surf, (ix, bar_y))
                bar_y += 14

    def _render_enemy_overlay(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        text: str,
        color: tuple,
    ) -> None:
        """Render a defeated/fled overlay on an enemy card."""
        # Dim the card
        dim_surf = pygame.Surface((ENEMY_PANEL_W, ENEMY_CARD_H), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 120))
        screen.blit(dim_surf, (x, y))

        # Centered text
        text_surf = self.header_font.render(text, True, color)
        text_rect = text_surf.get_rect(center=(x + ENEMY_PANEL_W // 2, y + ENEMY_CARD_H // 2))
        screen.blit(text_surf, text_rect)

    # ------------------------------------------------------------------
    # Bar rendering
    # ------------------------------------------------------------------

    def _render_damage_ghost(
        self,
        screen: pygame.Surface,
        bar_x: int,
        bar_y: int,
        bar_w: int,
        bar_h: int,
        displayed_hull: float,
        max_hull: int,
        enemy: object,
    ) -> None:
        """Render a translucent ghost fill on the enemy hull bar showing projected damage."""
        move = self._hovered_move
        if move is None:
            return

        # Calculate projected damage range
        damage_effects = [e for e in move.effects if e.type == EffectType.DAMAGE]
        if not damage_effects:
            return

        total_damage = sum(e.value for e in damage_effects)

        # Account for attacker's damage boost
        state = self.engine.get_state()
        boost_pct = 0.0
        for eff, _ in state.player.active_effects:
            if eff.type == EffectType.DAMAGE_BOOST:
                boost_pct += eff.value
        if boost_pct > 0:
            total_damage *= 1.0 + boost_pct / 100.0

        # Account for enemy damage reduction
        dr = 0.0
        for eff, _ in enemy.active_effects:
            if eff.type == EffectType.DAMAGE_REDUCTION:
                dr += eff.value
        total_damage *= 1.0 - min(dr, 0.9)

        # Calculate bar label offset (match _render_bar's label width)
        label_w = BAR_LABEL_W + 6

        # Ghost fill: shows the damage as a translucent red overlay from current hull backward
        hull_ratio = displayed_hull / max(1, max_hull)
        damage_ratio = total_damage / max(1, max_hull)

        fill_bar_x = bar_x + label_w
        fill_bar_w = bar_w - label_w

        # Ghost starts at current hull position and extends left by damage amount
        ghost_start_pct = max(0, hull_ratio - damage_ratio)
        ghost_end_pct = hull_ratio

        ghost_x = fill_bar_x + int(fill_bar_w * ghost_start_pct)
        ghost_w = int(fill_bar_w * (ghost_end_pct - ghost_start_pct))

        if ghost_w > 0:
            ghost_surf = pygame.Surface((ghost_w, bar_h), pygame.SRCALPHA)
            ghost_surf.fill((220, 50, 50, 80))  # Translucent red
            screen.blit(ghost_surf, (ghost_x, bar_y))
            # Bright leading edge
            pygame.draw.line(
                screen,
                (255, 80, 80, 160),
                (ghost_x, bar_y),
                (ghost_x, bar_y + bar_h - 1),
            )

    def _render_move_tooltip(
        self,
        screen: pygame.Surface,
        btn: "_MoveButton",
        ox: int,
        oy: int,
    ) -> None:
        """Render an enhanced tooltip for a hovered move button."""
        move = btn.move
        state = self.engine.get_state()

        lines: list[tuple[str, tuple[int, int, int]]] = []

        # Damage info
        damage_effects = [e for e in move.effects if e.type == EffectType.DAMAGE]
        if damage_effects:
            total = sum(e.value for e in damage_effects)
            lines.append((f"Damage: {int(total)}", Colors.TEXT_PRIMARY))

        # Other effects
        for eff in move.effects:
            if eff.type == EffectType.DAMAGE:
                continue
            name = eff.type.value.replace("_", " ").title()
            sign = "+" if eff.value > 0 else ""
            dur = f" ({eff.duration}t)" if eff.duration > 0 else ""
            lines.append((f"{name}: {sign}{int(eff.value)}{dur}", Colors.TEXT_SECONDARY))

        # Accuracy
        player_acc = state.player.accuracy
        target = (
            state.enemies[self.selected_target_idx]
            if self.selected_target_idx < len(state.enemies)
            else None
        )
        if target and target.is_alive:
            evasion = (
                target.get_effective_evasion() if hasattr(target, "get_effective_evasion") else 0
            )
            from spacegame.config import COMBAT_HIT_CHANCE_MAX, COMBAT_HIT_CHANCE_MIN

            hit_chance = max(
                COMBAT_HIT_CHANCE_MIN,
                min(COMBAT_HIT_CHANCE_MAX, player_acc + move.accuracy_modifier - evasion),
            )
            acc_color = (
                Colors.GREEN
                if hit_chance >= 70
                else (Colors.YELLOW if hit_chance >= 50 else Colors.RED)
            )
            lines.append((f"Hit Chance: {hit_chance}%", acc_color))

        # Energy remaining after use
        remaining = state.player.energy - move.energy_cost
        energy_color = (
            Colors.TEXT_SECONDARY
            if remaining >= 2
            else (Colors.YELLOW if remaining >= 0 else Colors.RED)
        )
        lines.append((f"Energy After: {remaining}/{state.player.max_energy}", energy_color))

        # Cooldown
        if move.cooldown > 0:
            lines.append((f"Cooldown: {move.cooldown} turns", Colors.TEXT_SECONDARY))

        if not lines:
            return

        # Render tooltip above the button
        font = self.small_font
        line_h = font.get_linesize() + 2
        pad = 6
        tip_w = max(font.size(text)[0] for text, _ in lines) + pad * 2
        tip_h = len(lines) * line_h + pad * 2

        tip_x = btn.rect.x + ox
        tip_y = btn.rect.y + oy - tip_h - 4
        # Keep on screen
        if tip_x + tip_w > WINDOW_WIDTH:
            tip_x = WINDOW_WIDTH - tip_w - 4
        if tip_y < 0:
            tip_y = btn.rect.bottom + oy + 4

        # Background
        tip_surf = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        tip_surf.fill((12, 15, 28, 230))
        screen.blit(tip_surf, (tip_x, tip_y))
        pygame.draw.rect(screen, Colors.UI_BORDER, (tip_x, tip_y, tip_w, tip_h), 1)

        # Lines
        ty = tip_y + pad
        for text, color in lines:
            surf = font.render(text, True, color)
            screen.blit(surf, (tip_x + pad, ty))
            ty += line_h

    def _render_momentum_bar(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        width: int,
        state: object,
    ) -> None:
        """Render the momentum gauge with gradient fill and threshold markers."""
        from spacegame.models.momentum import (
            THRESHOLD_CHARGED,
            THRESHOLD_OVERLOAD,
            THRESHOLD_SURGING,
        )

        momentum = state.player.momentum
        if momentum is None:
            return

        # Color based on current level (gradient: blue → cyan → green → gold → white)
        pct = momentum.current
        if pct >= 1.0:
            bar_color = _COMBAT_COLORS["momentum_blazing"]  # Blazing white-gold
        elif pct >= 0.75:
            t = (pct - 0.75) / 0.25
            bar_color = (
                int(200 + 55 * t),
                int(180 + 75 * t),
                int(50 + 170 * t),
            )  # Gold → white-gold
        elif pct >= 0.50:
            t = (pct - 0.50) / 0.25
            bar_color = (int(50 + 150 * t), int(200 - 20 * t), int(50 * (1 - t)))  # Green → gold
        elif pct >= 0.25:
            t = (pct - 0.25) / 0.25
            bar_color = (int(40 + 10 * t), int(180 + 20 * t), int(230 - 180 * t))  # Cyan → green
        else:
            t = pct / 0.25 if pct > 0 else 0
            bar_color = (int(30 + 10 * t), int(60 + 120 * t), int(140 + 90 * t))  # Dark blue → cyan

        # Render bar with label
        draw_bar(
            screen,
            x,
            y,
            width,
            BAR_HEIGHT,
            self._displayed_player_momentum,
            100.0,
            bar_color,
            label="Mtm",
            font=self.small_font,
            show_value=True,
        )

        # Threshold markers (vertical lines on the bar)
        label_w = self.small_font.size("Mtm")[0] + 8 if self.small_font else 30
        inner_x = x + label_w + 2
        inner_w = width - label_w - 4

        for threshold, marker_color in [
            (THRESHOLD_CHARGED, _COMBAT_COLORS["momentum_charged"]),  # Cyan
            (THRESHOLD_SURGING, _COMBAT_COLORS["momentum_surging"]),  # Green
            (THRESHOLD_OVERLOAD, _COMBAT_COLORS["momentum_overload"]),  # Gold
        ]:
            mx = inner_x + int(inner_w * threshold)
            pygame.draw.line(screen, marker_color, (mx, y + 1), (mx, y + BAR_HEIGHT - 2), 1)

        # Pulse effect when threshold crossed
        if self._momentum_pulse_timer > 0:
            pulse_alpha = int(120 * (self._momentum_pulse_timer / 0.5))
            pulse_surf = pygame.Surface((width, BAR_HEIGHT + 4), pygame.SRCALPHA)
            pulse_surf.fill((*self._momentum_pulse_color, pulse_alpha))
            screen.blit(pulse_surf, (x, y - 2))

        # Ultimate ready indicator
        if momentum.ultimate_available:
            ult_text = self.small_font.render("ULTIMATE READY!", True, _COMBAT_COLORS["ult_text_pulse"])
            ult_rect = ult_text.get_rect(centerx=x + width // 2, top=y + BAR_HEIGHT + 2)
            screen.blit(ult_text, ult_rect)

        # Overdriven indicator
        if momentum.overdriven_available:
            ovd_text = self.small_font.render("2X DAMAGE", True, _COMBAT_COLORS["double_damage"])
            ovd_rect = ovd_text.get_rect(right=x + width, top=y + BAR_HEIGHT + 2)
            screen.blit(ovd_text, ovd_rect)

    def _render_bar(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        width: int,
        height: int,
        current: float,
        maximum: float,
        color: tuple,
        label: str,
        label_color: tuple | None = None,
    ) -> None:
        """Render a labeled health/shield/energy bar with fill and highlight edge."""
        draw_bar(
            screen,
            x,
            y,
            width,
            height,
            current,
            maximum,
            color,
            label=label,
            font=self.small_font,
            label_color=label_color,
        )

    # ------------------------------------------------------------------
    # Effect display helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _effect_badge_text(effect: object, turns_left: int) -> str:
        """Format an active effect as a short badge string."""
        type_labels = {
            "evasion_mod": "EVA",
            "accuracy_mod": "ACC",
            "damage_reduction": "DMG RED",
            "energy_drain": "E.DRAIN",
            "shield_drain": "S.DRAIN",
        }
        label = type_labels.get(effect.type.value, effect.type.value.upper())
        sign = "+" if effect.value >= 0 else ""
        return f"[{sign}{int(effect.value)} {label} {turns_left}t]"

    @staticmethod
    def _find_move_name(move_id: str, state: object) -> str:
        """Find move name by ID from player state."""
        for move in state.player.equipment_moves:
            if move.id == move_id:
                return move.name
        for move in state.player.crew_moves:
            if move.id == move_id:
                return move.name
        for move in getattr(state.player, "dual_tech_moves", []):
            if move.id == move_id:
                return move.name
        return move_id

    def _get_combat_ship_scale(self, role: str, ship_class: str = "", danger_tier: str = "") -> int:
        """Get the display scale for a ship based on its class or danger tier.

        Args:
            role: "player" or "enemy".
            ship_class: Ship class string (for player ships).
            danger_tier: Enemy danger tier (for enemy ships).

        Returns:
            Resolution-aware integer scale factor.
        """
        if role == "player":
            base = SHIP_CLASS_SCALE.get(ship_class, 3)
        else:
            base = ENEMY_TIER_SCALE.get(danger_tier, 3)
        return res_scale(base)

    def _get_ship_sprite(
        self,
        sprite_id: str,
        role: str,
        scale: Optional[int] = None,
        ship_class: str = "",
        danger_tier: str = "",
    ) -> Optional[AnimatedSprite]:
        """Get a cached AnimatedSprite for a ship.

        Args:
            sprite_id: Ship or enemy template ID.
            role: "player" or "enemy".
            scale: Explicit scale override. None uses class-based scaling.
            ship_class: Ship class for player ships (used if scale is None).
            danger_tier: Danger tier for enemies (used if scale is None).
        """
        if scale is None:
            scale = self._get_combat_ship_scale(role, ship_class, danger_tier)
        cache_key = f"{role}_{sprite_id}_{scale}"
        if cache_key not in self._ship_sprite_cache:
            category = "player" if role == "player" else "enemies"
            self._ship_sprite_cache[cache_key] = self._sprite_mgr.get_ship_animated(
                sprite_id, category=category, scale=scale
            )
        return self._ship_sprite_cache[cache_key]

    @staticmethod
    def _create_damage_overlay(severity: str = "light") -> pygame.Surface:
        """Create a procedural damage overlay surface (96x96).

        Args:
            severity: "light" for scorch marks, "heavy" for sparks + panel gaps.

        Returns:
            Semi-transparent surface to composite onto ship sprites.
        """
        size = 96
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        rng = _random.Random(42 if severity == "light" else 99)

        if severity == "light":
            # Scorch marks: small dark circles with low opacity
            for _ in range(6):
                x = rng.randint(20, size - 20)
                y = rng.randint(20, size - 20)
                r = rng.randint(3, 7)
                alpha = rng.randint(40, 80)
                pygame.draw.circle(surf, (30, 20, 10, alpha), (x, y), r)

            # Thin cracks: short dark lines
            for _ in range(4):
                x1 = rng.randint(15, size - 15)
                y1 = rng.randint(15, size - 15)
                dx = rng.randint(-12, 12)
                dy = rng.randint(-12, 12)
                alpha = rng.randint(50, 90)
                crack_surf = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.line(crack_surf, (20, 15, 10, alpha), (x1, y1), (x1 + dx, y1 + dy), 1)
                surf.blit(crack_surf, (0, 0))

        else:  # heavy
            # Larger dark burn patches
            for _ in range(8):
                x = rng.randint(15, size - 15)
                y = rng.randint(15, size - 15)
                r = rng.randint(5, 11)
                alpha = rng.randint(60, 120)
                pygame.draw.circle(surf, (20, 10, 5, alpha), (x, y), r)

            # Prominent cracks
            for _ in range(6):
                x1 = rng.randint(10, size - 10)
                y1 = rng.randint(10, size - 10)
                dx = rng.randint(-18, 18)
                dy = rng.randint(-18, 18)
                alpha = rng.randint(70, 130)
                crack_surf = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.line(crack_surf, (15, 10, 5, alpha), (x1, y1), (x1 + dx, y1 + dy), 2)
                surf.blit(crack_surf, (0, 0))

            # Orange/yellow spark dots
            for _ in range(10):
                x = rng.randint(12, size - 12)
                y = rng.randint(12, size - 12)
                r = rng.randint(1, 3)
                color = rng.choice(
                    [
                        (255, 160, 40, 140),
                        (255, 200, 60, 120),
                        (255, 120, 20, 100),
                    ]
                )
                pygame.draw.circle(surf, color, (x, y), r)

        return surf

    def _apply_damage_overlay(self, surface: pygame.Surface, hull_ratio: float) -> pygame.Surface:
        """Composite damage overlay onto a ship sprite based on hull ratio.

        Args:
            surface: The rotated ship sprite (modified in place).
            hull_ratio: 0.0 (dead) to 1.0 (full health).

        Returns:
            The surface with damage overlay applied (same reference).
        """
        if hull_ratio >= 0.75:
            return surface  # Clean — no damage

        # Pick overlay and compute opacity
        if hull_ratio >= 0.5:
            overlay = self._damage_overlay_light
            # Fade in from 0 at 75% to full at 50%
            t = 1.0 - (hull_ratio - 0.5) / 0.25
        else:
            overlay = self._damage_overlay_heavy
            # Full intensity below 50%, slightly stronger near 0
            t = min(1.0, 0.7 + 0.3 * (1.0 - hull_ratio * 2))

        # Scale overlay to match surface if sizes differ
        if overlay.get_size() != surface.get_size():
            overlay = pygame.transform.scale(overlay, surface.get_size())

        # Apply with alpha modulation
        scaled_overlay = overlay.copy()
        scaled_overlay.set_alpha(int(255 * t))
        surface.blit(scaled_overlay, (0, 0))
        return surface

    def _render_combat_arena(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render central combat arena with ship sprites and effects."""
        state = self.engine.get_state()

        # Player ship (left side, facing right) — class-based scale + idle bob
        bob_offset = int(
            IDLE_BOB_AMPLITUDE * math.sin(self.phase_timer * 2 * math.pi / IDLE_BOB_PERIOD)
        )
        player_x = PLAYER_SHIP_POS[0] + ox
        player_y = PLAYER_SHIP_POS[1] + oy + bob_offset
        hull_ratio = state.player.hull / state.player.max_hull if state.player.max_hull > 0 else 0

        # Use composite sprite if player has a build, otherwise stock sprite
        player_sprite = None
        composite = self.player.ship.composite if self.player else None
        if composite and hasattr(composite, "get_surface"):
            from spacegame.engine.sprites import res_scale

            player_sprite = composite.get_surface(scale=res_scale(2))
            composite.update(0.016)  # Advance engine glow
        else:
            player_ship_id = self.player.ship.ship_type.id if self.player else None
            player_class = self.player.ship.ship_type.ship_class if self.player else ""
            player_anim = (
                self._get_ship_sprite(player_ship_id, "player", ship_class=player_class)
                if player_ship_id
                else None
            )
            player_sprite = player_anim.get_surface() if player_anim else None
        if player_sprite:
            # Flip to face right (sprites are natively oriented left)
            rotated = pygame.transform.flip(player_sprite, True, False)
            # Damage overlay (scorch marks / sparks based on hull %)
            rotated = self._apply_damage_overlay(rotated, hull_ratio)
            # Tint red on low hull (BLEND_RGB_MULT preserves alpha)
            if hull_ratio < 0.5:
                intensity = hull_ratio * 2  # 0.0 at 0 hull, 1.0 at 50% hull
                r_mult = 255
                gb_mult = int(100 + 155 * intensity)  # 100-255 range
                tint = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
                tint.fill((r_mult, gb_mult, gb_mult, 255))
                rotated.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            # Hit flash: white overlay on hull damage
            if self._player_sprite_flash > 0:
                flash_t = self._player_sprite_flash / 0.12
                flash_surf = rotated.copy()
                white = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
                white.fill((255, 255, 255, int(180 * flash_t)))
                flash_surf.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                rotated = flash_surf
            # Apply hit recoil offset + dodge jink (Phase 12E)
            recoil_ox, recoil_oy = self._damage_state_mgr.get_recoil_offset("player")
            jink_ox = 0
            if self._dodge_jink_timer > 0:
                jink_t = self._dodge_jink_timer / 0.15
                jink_ox = int(12 * jink_t * self._dodge_jink_direction)
            draw_x = player_x + recoil_ox + jink_ox
            draw_y = player_y + recoil_oy
            # ArenaEntry engine ignite fade (Combat C3 §4.8). During INTRO
            # the player ship fades from dim (engines dormant) to full
            # brightness as engines "ignite" over the camera-push phase.
            # After intro, _arena_entry is None and rendering is unaffected.
            if self._arena_entry is not None:
                ignite_factor = self._arena_entry.player_engine_ignite_factor
                ignite_alpha = max(0, min(255, int(255 * ignite_factor)))
                rotated = rotated.copy()
                rotated.set_alpha(ignite_alpha)
            rect = rotated.get_rect(center=(draw_x, draw_y))
            screen.blit(rotated, rect)

            # Identity visual overlays (Phase 12E)
            identity = state.player.defensive_identity
            if identity == "juggernaut" and state.player.hull_ratio < 0.25:
                # Last Stand: pulsing red glow around ship
                pulse = 0.5 + 0.5 * math.sin(self.phase_timer * 6)
                glow_alpha = int(60 * pulse)
                glow_surf = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
                glow_surf.fill((255, 40, 20, glow_alpha))
                screen.blit(glow_surf, rect)
            elif identity == "ghost" and state.player.counterstrike_stacks > 0:
                # Counterstrike: brightening cyan glow per stack
                stacks = state.player.counterstrike_stacks
                glow_alpha = int(25 * stacks)
                glow_surf = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
                glow_surf.fill((100, 220, 255, glow_alpha))
                screen.blit(glow_surf, rect)

            # Shield bubble + ripple (replaces old shimmer)
            sprite_r = max(rotated.get_width(), rotated.get_height()) // 2
            self._shield_renderer.render(screen, "player", draw_x, draw_y, sprite_r)

            # Damage smoke/sparks
            self._damage_state_mgr.render(screen, "player", draw_x, draw_y)
        else:
            self._draw_ship_silhouette(
                screen, player_x, player_y, facing_right=True, hull_ratio=hull_ratio
            )

        # Enemy ships (right side, facing left) — tier-based scale + idle bob
        living_enemies = [
            (i, e) for i, e in enumerate(state.enemies) if e.is_alive and not e.is_fled
        ]
        for j, (idx, enemy) in enumerate(living_enemies[:3]):
            # Offset bob phase per enemy so they don't all move in sync
            enemy_bob = int(
                IDLE_BOB_AMPLITUDE
                * math.sin((self.phase_timer + j * 0.7) * 2 * math.pi / IDLE_BOB_PERIOD)
            )
            # ArenaEntry slide-in (Combat C3 §4.8). During INTRO each enemy
            # starts offset right of its rest position and slides in on a
            # 100ms per-enemy stagger. After intro, _arena_entry is None
            # and slide_offset is 0 so enemies render at rest position.
            slide_offset = 0
            if self._arena_entry is not None:
                slide_offset = int(self._arena_entry.enemy_slide_offset(j))
            enemy_x = ENEMY_SHIP_POS[0] + ox + slide_offset
            enemy_y = (
                ENEMY_SHIP_POS[1]
                + oy
                + enemy_bob
                + (j - len(living_enemies) // 2) * ENEMY_STACK_SPACING
            )
            e_hull_ratio = (
                enemy.current_hull / enemy.template.hull if enemy.template.hull > 0 else 0
            )

            enemy_anim = self._get_ship_sprite(
                enemy.template.id, "enemy", danger_tier=enemy.template.danger_tier
            )
            enemy_sprite = enemy_anim.get_surface() if enemy_anim else None
            if enemy_sprite:
                # Apply per-template rotation fix (0 for most, -90 for upward-facing)
                rot = getattr(enemy.template, "sprite_rotation", 0)
                rotated = pygame.transform.rotate(enemy_sprite, rot) if rot else enemy_sprite
                # Damage overlay (scorch marks / sparks based on hull %)
                rotated = self._apply_damage_overlay(rotated, e_hull_ratio)
                if e_hull_ratio < 0.5:
                    tint = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
                    tint_alpha = int(120 * (1.0 - e_hull_ratio * 2))
                    tint.fill((220, 50, 50, tint_alpha))
                    rotated.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # Hit flash: white overlay on hull damage
                if idx < len(self._enemy_sprite_flashes) and self._enemy_sprite_flashes[idx] > 0:
                    flash_t = self._enemy_sprite_flashes[idx] / 0.12
                    flash_surf = rotated.copy()
                    white = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
                    white.fill((255, 255, 255, int(180 * flash_t)))
                    flash_surf.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                    rotated = flash_surf
                # Selected glow
                if idx == self.selected_target_idx:
                    pulse = int(40 + 30 * math.sin(self.phase_timer * 4))
                    glow_surf = pygame.Surface(
                        (rotated.get_width() + 8, rotated.get_height() + 8),
                        pygame.SRCALPHA,
                    )
                    pygame.draw.rect(
                        glow_surf,
                        (*Colors.TEXT_HIGHLIGHT, pulse),
                        glow_surf.get_rect(),
                        2,
                        border_radius=4,
                    )
                    screen.blit(
                        glow_surf,
                        (
                            enemy_x - rotated.get_width() // 2 - 4,
                            enemy_y - rotated.get_height() // 2 - 4,
                        ),
                    )
                # Apply hit recoil offset
                ekey = f"enemy_{idx}"
                e_recoil_ox, e_recoil_oy = self._damage_state_mgr.get_recoil_offset(ekey)
                draw_ex = enemy_x + e_recoil_ox
                draw_ey = enemy_y + e_recoil_oy
                rect = rotated.get_rect(center=(draw_ex, draw_ey))
                screen.blit(rotated, rect)

                # Shield bubble + ripple (replaces old shimmer)
                e_sprite_r = max(rotated.get_width(), rotated.get_height()) // 2
                self._shield_renderer.render(screen, ekey, draw_ex, draw_ey, e_sprite_r)

                # Damage smoke/sparks
                self._damage_state_mgr.render(screen, ekey, draw_ex, draw_ey)
            else:
                self._draw_ship_silhouette(
                    screen,
                    enemy_x,
                    enemy_y,
                    facing_right=False,
                    hull_ratio=e_hull_ratio,
                    is_selected=(idx == self.selected_target_idx),
                )

        # Render destroying enemy ships (sprite sheet animation + destruction VFX)
        finished_destroys = []
        for idx, (ex, ey, anim) in self._destroying_enemies.items():
            sprite_surf = anim.get_surface()
            if sprite_surf and not anim.is_finished():
                rotated = sprite_surf  # Enemy destruction — already faces left
                rect = rotated.get_rect(center=(ex + ox, ey + oy))
                screen.blit(rotated, rect)
            elif anim.is_finished():
                finished_destroys.append(idx)
        for idx in finished_destroys:
            del self._destroying_enemies[idx]

        # Render spectacular destruction sequences (fragments, flash, fire)
        for seq in self._destruction_sequences:
            seq.render(screen)

        # Render persistent debris from completed destructions
        for d in self._persistent_debris:
            d["x"] += d.get("vx", 0) * 0.016
            d["y"] += d.get("vy", 0) * 0.016
            size = d.get("size", 2)
            alpha = int(d.get("alpha", 40))
            if alpha <= 0:
                continue
            from spacegame.engine.combat_vfx import _FRAG_COLORS

            color = _FRAG_COLORS[d.get("color_idx", 0)]
            debris_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.rect(debris_surf, (*color, alpha), (0, 0, size * 2, size))
            screen.blit(debris_surf, (int(d["x"]) - size, int(d["y"]) - size))

        # Action text flash in center arena
        if self._arena_action_timer > 0 and self._arena_action_text:
            alpha = int(255 * min(1.0, self._arena_action_timer / 0.3))
            action_surf = self.header_font.render(
                self._arena_action_text, True, Colors.TEXT_HIGHLIGHT
            )
            action_surf.set_alpha(alpha)
            action_rect = action_surf.get_rect(center=(WINDOW_WIDTH // 2 + ox, 180 + oy))
            screen.blit(action_surf, action_rect)

        # Phase banner (centered)
        phase_text = self._get_phase_display_text()
        if phase_text and self.phase in (
            CombatPhase.PLAYER_INPUT,
            CombatPhase.ANIMATING_CREW,
            CombatPhase.ANIMATING_ENEMIES,
        ):
            # Banner with brief slide/fade effect
            banner_alpha = min(255, int(self.phase_timer * 800))
            banner_surf = self.title_font.render(phase_text, True, Colors.TEXT_HIGHLIGHT)
            banner_surf.set_alpha(banner_alpha)
            banner_rect = banner_surf.get_rect(center=(WINDOW_WIDTH // 2 + ox, 90 + oy))
            screen.blit(banner_surf, banner_rect)

    def _draw_ship_silhouette(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        facing_right: bool = True,
        hull_ratio: float = 1.0,
        is_selected: bool = False,
    ) -> None:
        """Draw a procedural ship silhouette at the given position."""
        # Ship body — arrow/wedge shape
        w, h = 80, 36
        ship_surf = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        cx, cy = w // 2 + 4, h // 2 + 4

        # Hull color: tint more red as hull drops
        hr = max(0.0, min(1.0, hull_ratio))
        r = int(60 + (1.0 - hr) * 140)
        g = int(80 + hr * 100)
        b = int(120 + hr * 60)
        body_color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), 220)

        # Wedge points
        if facing_right:
            points = [
                (4, cy - h // 3),  # Top-left
                (w - 4, cy),  # Nose (right)
                (4, cy + h // 3),  # Bottom-left
            ]
            engine_x = 6
        else:
            points = [
                (w, cy - h // 3),  # Top-right
                (8, cy),  # Nose (left)
                (w, cy + h // 3),  # Bottom-right
            ]
            engine_x = w - 2

        pygame.draw.polygon(ship_surf, body_color, points)
        pygame.draw.polygon(ship_surf, (*Colors.UI_BORDER, 200), points, 2)

        # Engine glow (small circle at rear)
        engine_color = (100, 180, 255, 180)
        pygame.draw.circle(ship_surf, engine_color, (engine_x, cy), 4)

        # Selected indicator — soft glow ring
        if is_selected:
            pulse = int(30 + 20 * math.sin(self.phase_timer * 4))
            glow_color = (*Colors.TEXT_HIGHLIGHT, pulse)
            pygame.draw.circle(ship_surf, glow_color, (cx, cy), w // 2 + 4, 2)

        screen.blit(ship_surf, (x - cx, y - cy))

    def _render_action_panel(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render action panel with move buttons, flee, negotiate, and crew info."""
        # Refresh move button enabled state based on action queue
        if self.phase == CombatPhase.PLAYER_INPUT and self._action_queue:
            for btn in self.move_buttons:
                can_queue, _ = self._action_queue.can_add(btn.move.id, btn.move)
                btn.enabled = can_queue

        # Panel background
        panel_rect = pygame.Rect(0 + ox, ACTION_PANEL_Y + oy, 720, ACTION_PANEL_H)
        draw_panel(
            screen,
            panel_rect,
            alpha=200,
            bg_color=_COMBAT_COLORS["panel_modal_bg_dark"],
            border_color=None,
            border_radius=0,
        )
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (ox, ACTION_PANEL_Y + oy),
            (720 + ox, ACTION_PANEL_Y + oy),
        )

        # Category tabs
        tab_y = ACTION_PANEL_Y + 4 + oy
        tab_w = scale_x(100)
        tab_h = scale_y(22)
        tab_gap = scale_x(4)
        tab_x_start = MOVE_BTN_X_START + ox

        _TAB_CONFIG = [
            ("attack", "ATK", _COMBAT_COLORS["tab_attack_bg"], _COMBAT_COLORS["tab_attack_border"]),
            ("defend", "DEF", _COMBAT_COLORS["tab_defend_bg"], _COMBAT_COLORS["tab_defend_border"]),
            ("utility", "UTL", _COMBAT_COLORS["tab_utility_bg"], _COMBAT_COLORS["tab_utility_border"]),
            ("coordinated", "CREW", _COMBAT_COLORS["tab_coord_bg"], _COMBAT_COLORS["tab_coord_border"]),
        ]
        self._tab_rects: dict[str, pygame.Rect] = {}
        for i, (tab_id, label, active_color, dim_color) in enumerate(_TAB_CONFIG):
            tx = tab_x_start + i * (tab_w + tab_gap)
            rect = pygame.Rect(tx, tab_y, tab_w, tab_h)
            self._tab_rects[tab_id] = rect
            is_active = self._action_tab == tab_id
            count = len(self._categorized_moves.get(tab_id, []))
            bg = active_color if is_active else Colors.UI_PANEL
            border = active_color if is_active else dim_color
            pygame.draw.rect(screen, bg, rect, border_radius=3)
            pygame.draw.rect(screen, border, rect, 1, border_radius=3)
            tab_text = f"{label} ({count})" if count > 0 else label
            text_color = (
                Colors.TEXT_PRIMARY if is_active else (active_color if count > 0 else _COMBAT_COLORS["tab_inactive_text"])
            )
            t = self.small_font.render(tab_text, True, text_color)
            screen.blit(
                t, (tx + tab_w // 2 - t.get_width() // 2, tab_y + tab_h // 2 - t.get_height() // 2)
            )

        # Move buttons for active tab (single column, scrollable)
        is_input = self.phase == CombatPhase.PLAYER_INPUT
        active_moves = self._categorized_moves.get(self._action_tab, [])
        btn_x = MOVE_BTN_X_START + ox
        btn_y_start = tab_y + tab_h + scale_y(6)
        btn_w = scale_x(430)
        btn_h = scale_y(48)
        btn_gap = scale_y(4)
        max_visible = 3
        scroll = self._action_tab_scroll.get(self._action_tab, 0)

        # Clip region for scrollable area
        clip_h = max_visible * (btn_h + btn_gap)
        clip_rect = pygame.Rect(btn_x - 2, btn_y_start, btn_w + 4, clip_h)
        screen.set_clip(clip_rect)

        for idx, btn in enumerate(active_moves):
            vis_idx = idx - scroll
            by = btn_y_start + vis_idx * (btn_h + btn_gap)
            btn.rect = pygame.Rect(btn_x, by, btn_w, btn_h)
            if vis_idx >= 0 and vis_idx < max_visible:
                self._render_move_button(screen, btn, 0, 0, is_input)

        screen.set_clip(None)

        # Scroll indicator
        if len(active_moves) > max_visible:
            if scroll > 0:
                up_surf = self.small_font.render("\u25b2", True, Colors.TEXT_SECONDARY)
                screen.blit(up_surf, (btn_x + btn_w + 4, btn_y_start))
            if scroll + max_visible < len(active_moves):
                dn_surf = self.small_font.render("\u25bc", True, Colors.TEXT_SECONDARY)
                screen.blit(dn_surf, (btn_x + btn_w + 4, btn_y_start + clip_h - scale_y(14)))

        # Crew ability buttons (below special buttons)
        if self._crew_move_buttons:
            # "CREW" label
            crew_label_y = SPECIAL_BTN_Y + SPECIAL_BTN_H + scale_y(2) + oy
            crew_label = self.small_font.render("CREW", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(crew_label, (MOVE_BTN_X_START + ox, crew_label_y - scale_y(12)))

            for btn in self._crew_move_buttons:
                bx = btn.rect.x + ox
                by = btn.rect.y + oy
                bw = btn.rect.width
                bh = btn.rect.height

                is_selected = self._selected_crew_move_id == btn.move.id
                is_active_phase = self.phase == CombatPhase.PLAYER_INPUT

                # Background
                if is_selected:
                    bg = (40, 60, 90, 230)
                elif btn.hovered and btn.enabled and is_active_phase:
                    bg = (30, 42, 65, 220)
                elif not btn.enabled or not is_active_phase:
                    bg = (18, 20, 30, 180)
                else:
                    bg = (22, 28, 48, 200)

                btn_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
                btn_surf.fill(bg)
                screen.blit(btn_surf, (bx, by))

                # Border (highlight if selected)
                border_color = Colors.TEXT_HIGHLIGHT if is_selected else Colors.UI_BORDER
                if btn.hovered and btn.enabled and is_active_phase:
                    border_color = Colors.TEXT_HIGHLIGHT
                pygame.draw.rect(screen, border_color, (bx, by, bw, bh), 1, border_radius=2)

                # Move name (compact)
                name_surf = self.small_font.render(btn.move.name, True, Colors.TEXT_PRIMARY)
                max_name_w = bw - scale_x(30)
                if name_surf.get_width() > max_name_w:
                    display_name = btn.move.name
                    while len(display_name) > 3 and name_surf.get_width() > max_name_w:
                        display_name = display_name[:-1]
                    display_name = display_name.rstrip() + ".."
                    name_surf = self.small_font.render(display_name, True, Colors.TEXT_PRIMARY)
                screen.blit(name_surf, (bx + 4, by + (bh - name_surf.get_height()) // 2))

                # Energy cost (right side)
                cost_text = f"{btn.move.energy_cost}E"
                cost_surf = self.small_font.render(cost_text, True, ENERGY_COLOR)
                screen.blit(
                    cost_surf,
                    (bx + bw - cost_surf.get_width() - 4, by + (bh - cost_surf.get_height()) // 2),
                )

                # Cooldown overlay
                if btn.cooldown_remaining > 0:
                    cd_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
                    cd_surf.fill((0, 0, 0, 140))
                    screen.blit(cd_surf, (bx, by))

        # Combo buttons (Phase 9 — gold border, special styling)
        for cb in self._combo_buttons:
            combo = cb["combo"]
            rect = cb["rect"]
            bx = rect.x + ox
            by = rect.y + oy
            bw = rect.width
            bh = rect.height
            is_selected = self._selected_combo_id == combo.id

            # Gold background for combos
            if is_selected:
                bg = (50, 45, 15, 240)
            elif is_input:
                bg = (35, 32, 12, 220)
            else:
                bg = (20, 18, 8, 180)
            combo_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            combo_surf.fill(bg)
            screen.blit(combo_surf, (bx, by))

            # Gold border (brighter when selected)
            border = _COMBAT_COLORS["boss_header"] if is_selected else _COMBAT_COLORS["combo_tag"]
            pygame.draw.rect(screen, border, (bx, by, bw, bh), 1, border_radius=3)

            # Combo name
            combo_name = self.small_font.render(combo.name, True, _COMBAT_COLORS["combo_banner"])
            max_name_w = bw - scale_x(30)
            if combo_name.get_width() > max_name_w:
                name_text = combo.name
                while len(name_text) > 3 and self.small_font.size(name_text)[0] > max_name_w:
                    name_text = name_text[:-1]
                name_text = name_text.rstrip() + ".."
                combo_name = self.small_font.render(name_text, True, _COMBAT_COLORS["combo_banner"])
            screen.blit(combo_name, (bx + 4, by + (bh - combo_name.get_height()) // 2))

            # Energy cost (right side)
            cost_text = f"{combo.energy_cost}E"
            cost_surf = self.small_font.render(cost_text, True, ENERGY_COLOR)
            screen.blit(
                cost_surf,
                (bx + bw - cost_surf.get_width() - 4, by + (bh - cost_surf.get_height()) // 2),
            )

            # "COMBO" tag (small label)
            tag_surf = self.small_font.render("COMBO", True, _COMBAT_COLORS["combo_tag"])
            screen.blit(tag_surf, (bx + bw - tag_surf.get_width() - 4, by - 10))

        # Enhanced tooltip for hovered move (rendered on top of all buttons)
        if is_input:
            for btn in self.move_buttons:
                if btn.hovered and btn.enabled:
                    self._render_move_tooltip(screen, btn, ox, oy)
                    break
            # Also tooltip for hovered crew buttons
            for btn in self._crew_move_buttons:
                if btn.hovered and btn.enabled:
                    self._render_move_tooltip(screen, btn, ox, oy)
                    break

        # Flee button
        flee_chance = self._get_flee_chance()
        flee_text = f"Flee ({flee_chance}%)"
        self._render_special_button(
            screen,
            FLEE_BTN_X + ox,
            SPECIAL_BTN_Y + oy,
            SPECIAL_BTN_W,
            SPECIAL_BTN_H,
            flee_text,
            is_input,
            Colors.YELLOW,
        )

        # Negotiate button
        neg_available = self._is_negotiate_available() and is_input
        neg_text = "Negotiate" if neg_available else "Negotiate (Used)"
        neg_color = Colors.TEXT_HIGHLIGHT if neg_available else Colors.TEXT_SECONDARY
        self._render_special_button(
            screen,
            NEGOTIATE_BTN_X + ox,
            SPECIAL_BTN_Y + oy,
            SPECIAL_BTN_W + 20,
            SPECIAL_BTN_H,
            neg_text,
            neg_available,
            neg_color,
        )

        # Bribe button
        bribe_available = self._is_bribe_available() and is_input
        bribe_cost_text = self._get_bribe_display_cost()
        if bribe_available:
            bribe_text = f"Bribe ({bribe_cost_text})"
        else:
            bribe_text = "Bribe (Used)"
        bribe_color = Colors.YELLOW if bribe_available else Colors.TEXT_SECONDARY
        self._render_special_button(
            screen,
            BRIBE_BTN_X + ox,
            SPECIAL_BTN_Y + oy,
            SPECIAL_BTN_W,
            SPECIAL_BTN_H,
            bribe_text,
            bribe_available,
            bribe_color,
        )

        # Ultimate button (appears when momentum reaches 100%)
        state = self.engine.get_state()
        if state.player.momentum and state.player.momentum.ultimate_available and is_input:
            from spacegame.data_loader import get_data_loader

            ult_def = get_data_loader().ship_ultimates.get(state.player.ship_class_category)
            ult_name = ult_def.name if ult_def else "ULTIMATE"
            ult_y = SPECIAL_BTN_Y + SPECIAL_BTN_H + scale_y(42) + oy
            ult_w = scale_x(280)
            ult_h = scale_y(36)
            ult_x = MOVE_BTN_X_START + ox

            # Pulsing gold background
            import math

            pulse = 0.7 + 0.3 * math.sin(self.phase_timer * 4)
            bg_alpha = int(220 * pulse)
            ult_surf = pygame.Surface((ult_w, ult_h), pygame.SRCALPHA)
            ult_surf.fill((60, 50, 15, bg_alpha))
            screen.blit(ult_surf, (ult_x, ult_y))

            # Gold border
            pygame.draw.rect(
                screen, _COMBAT_COLORS["boss_header"], (ult_x, ult_y, ult_w, ult_h), 2, border_radius=4
            )

            # Text
            ult_text = self.info_font.render(f"[U] {ult_name}", True, _COMBAT_COLORS["combo_banner"])
            text_rect = ult_text.get_rect(center=(ult_x + ult_w // 2, ult_y + ult_h // 2))
            screen.blit(ult_text, text_rect)

        # Target indicator
        if state.enemies and self.selected_target_idx < len(state.enemies):
            target = state.enemies[self.selected_target_idx]
            target_text = f"Target: {target.template.name}"
            target_surf = self.small_font.render(target_text, True, Colors.TEXT_HIGHLIGHT)
            screen.blit(
                target_surf,
                (BRIBE_BTN_X + SPECIAL_BTN_W + 16 + ox, SPECIAL_BTN_Y + 10 + oy),
            )

        # Negotiate sub-menu (skill options above the Negotiate button)
        if self._negotiate_menu_open and is_input:
            for i, skill in enumerate(self._negotiate_skills):
                skill_y = SPECIAL_BTN_Y - (len(self._negotiate_skills) - i) * 30 - 5 + oy
                skill_x = NEGOTIATE_BTN_X + ox
                skill_w = SPECIAL_BTN_W + 20
                skill_h = 26

                # Background
                sk_surf = pygame.Surface((skill_w, skill_h), pygame.SRCALPHA)
                sk_surf.fill((25, 35, 60, 230))
                screen.blit(sk_surf, (skill_x, skill_y))
                pygame.draw.rect(
                    screen,
                    Colors.TEXT_HIGHLIGHT,
                    (skill_x, skill_y, skill_w, skill_h),
                    1,
                    border_radius=2,
                )

                # Key hint + label
                label = f"[{i + 1}] {skill.capitalize()}"
                label_surf = self.small_font.render(label, True, Colors.TEXT_HIGHLIGHT)
                label_rect = label_surf.get_rect(centery=skill_y + skill_h // 2, left=skill_x + 6)
                screen.blit(label_surf, label_rect)

        # Crew moves info
        crew_info = self._get_crew_move_info()
        if crew_info:
            crew_y = SPECIAL_BTN_Y + SPECIAL_BTN_H + 8 + oy
            crew_label = self.small_font.render("Crew:", True, Colors.TEXT_SECONDARY)
            screen.blit(crew_label, (MOVE_BTN_X_START + ox, crew_y))
            crew_x = MOVE_BTN_X_START + 40 + ox
            for info in crew_info:
                marker = "x" if info["skipped"] else "+"
                color = Colors.TEXT_SECONDARY if info["skipped"] else Colors.GREEN
                text = f"[{marker}] {info['name']}"
                surf = self.small_font.render(text, True, color)
                screen.blit(surf, (crew_x, crew_y))
                crew_x += surf.get_width() + 16

    def _render_move_button(
        self,
        screen: pygame.Surface,
        btn: _MoveButton,
        ox: int,
        oy: int,
        is_input_phase: bool,
    ) -> None:
        """Render a single equipment move button."""
        bx = btn.rect.x + ox
        by = btn.rect.y + oy
        bw = btn.rect.width
        bh = btn.rect.height

        # Background
        if not btn.enabled or not is_input_phase:
            bg_color = (20, 22, 35, 200)
        elif btn.hovered:
            bg_color = (35, 45, 70, 230)
        else:
            bg_color = (25, 32, 55, 220)

        btn_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        btn_surf.fill(bg_color)
        screen.blit(btn_surf, (bx, by))

        # Border
        border_color = Colors.TEXT_HIGHLIGHT if btn.hovered and btn.enabled else Colors.UI_BORDER
        pygame.draw.rect(screen, border_color, (bx, by, bw, bh), 1, border_radius=3)

        # Move type icon
        has_damage = any(e.type.value == "damage" for e in btn.move.effects)
        icon = "ATK" if has_damage else "DEF"
        icon_color = Colors.RED if has_damage else Colors.TEXT_HIGHLIGHT
        icon_surf = self.small_font.render(icon, True, icon_color)
        screen.blit(icon_surf, (bx + 6, by + 6))

        # Energy cost badge (render first to know available space)
        cost_text = f"{btn.move.energy_cost}E"
        cost_surf = self.small_font.render(cost_text, True, ENERGY_COLOR)
        cost_x = bx + bw - cost_surf.get_width() - 6
        screen.blit(cost_surf, (cost_x, by + 4))

        # Move name (clipped to available width before cost badge)
        max_name_w = cost_x - (bx + 36) - 4
        display_name = btn.move.name
        name_surf = self.info_font.render(display_name, True, Colors.TEXT_PRIMARY)
        if name_surf.get_width() > max_name_w and max_name_w > 0:
            while len(display_name) > 3 and name_surf.get_width() > max_name_w:
                display_name = display_name[:-1]
            display_name = display_name.rstrip() + ".."
            name_surf = self.info_font.render(display_name, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (bx + 36, by + 4))

        # Description / effect hint
        if btn.move.effects:
            eff = btn.move.effects[0]
            hint = f"{int(eff.value)} {eff.type.value.replace('_', ' ')}"
            hint_surf = self.small_font.render(hint, True, Colors.TEXT_SECONDARY)
            screen.blit(hint_surf, (bx + 36, by + 24))

        # Cooldown overlay
        if btn.cooldown_remaining > 0:
            cd_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            cd_surf.fill((0, 0, 0, 140))
            screen.blit(cd_surf, (bx, by))
            cd_text = f"CD: {btn.cooldown_remaining}"
            cd_render = self.info_font.render(cd_text, True, Colors.YELLOW)
            cd_rect = cd_render.get_rect(center=(bx + bw // 2, by + bh // 2))
            screen.blit(cd_render, cd_rect)

        # Disabled overlay (insufficient energy, no cooldown)
        elif not btn.enabled:
            dis_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            dis_surf.fill((0, 0, 0, 100))
            screen.blit(dis_surf, (bx, by))

        # Queued overlay: show queue position number if this move is queued
        if self._action_queue and btn.move.id in self._action_queue.get_queued_move_ids():
            # Find queue position
            for qi, qa in enumerate(self._action_queue.actions):
                if qa.move_id == btn.move.id:
                    q_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
                    q_surf.fill((40, 80, 160, 100))
                    screen.blit(q_surf, (bx, by))
                    # Queue number badge
                    badge_text = str(qi + 1)
                    badge = self.info_font.render(badge_text, True, Colors.WHITE)
                    badge_bg = pygame.Surface((22, 22), pygame.SRCALPHA)
                    badge_bg.fill((40, 100, 200, 220))
                    screen.blit(badge_bg, (bx + bw - 24, by + 2))
                    screen.blit(badge, (bx + bw - 24 + (22 - badge.get_width()) // 2, by + 4))
                    break

    def _render_special_button(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        text: str,
        enabled: bool,
        color: tuple,
    ) -> None:
        """Render a special action button (Flee / Negotiate)."""
        bg_alpha = 220 if enabled else 150
        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_surf.fill((20, 25, 40, bg_alpha))
        screen.blit(bg_surf, (x, y))

        border_color = color if enabled else Colors.UI_BORDER
        pygame.draw.rect(screen, border_color, (x, y, w, h), 1, border_radius=3)

        text_color = color if enabled else Colors.TEXT_SECONDARY
        text_surf = self.small_font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
        screen.blit(text_surf, text_rect)

    def _render_action_queue_panel(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render the action queue display during PLAYER_INPUT phase."""
        from spacegame.engine.draw_utils import draw_panel

        panel_x = scale_x(710) + ox
        panel_y = scale_y(525) + oy
        panel_w = scale_x(350)
        panel_h = scale_y(175)
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=210)

        # Header
        header = self.small_font.render("ACTION QUEUE", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (panel_x + 8, panel_y + 4))

        # Energy remaining
        if self._action_queue:
            remaining = self._action_queue.energy_remaining
            state = self.engine.get_state()
            total = state.player.max_energy
            e_color = (
                Colors.GREEN
                if remaining > total * 0.3
                else (Colors.YELLOW if remaining > 0 else Colors.RED)
            )
            energy_text = self.small_font.render(
                f"Energy: {remaining}/{total}",
                True,
                e_color,
            )
            screen.blit(energy_text, (panel_x + panel_w - energy_text.get_width() - 8, panel_y + 4))

        # Queued actions list
        queue_y = panel_y + scale_y(24)
        has_actions = self._action_queue and not self._action_queue.is_empty
        if has_actions:
            for i, action in enumerate(self._action_queue.actions):
                line_y = queue_y + i * scale_y(18)
                if line_y + scale_y(18) > panel_y + panel_h - scale_y(52):
                    break  # Don't overflow into summary/buttons
                # Queue number
                num = self.small_font.render(f"{i + 1}.", True, _COMBAT_COLORS["queue_number"])
                screen.blit(num, (panel_x + 8, line_y))
                # Move name
                name = self.small_font.render(action.move_name, True, Colors.TEXT_PRIMARY)
                screen.blit(name, (panel_x + 28, line_y))
                # Energy cost
                cost = self.small_font.render(
                    f"-{action.energy_cost}E", True, Colors.TEXT_SECONDARY
                )
                screen.blit(cost, (panel_x + panel_w - cost.get_width() - 40, line_y))
                # Target
                if action.target_idx >= 0:
                    enemies = self.engine.get_state().enemies
                    if action.target_idx < len(enemies):
                        tgt_name = enemies[action.target_idx].template.name
                        tgt_text = self.small_font.render(f"→ {tgt_name}", True, _COMBAT_COLORS["queue_target_dim"])
                        screen.blit(tgt_text, (panel_x + 140, line_y))
        else:
            # Empty queue: show last round recap for strategic context
            state_recap = self.engine.get_state()
            prev_round = state_recap.round_number - 1
            if prev_round >= 1:
                # Gather enemy actions from last round
                recap_entries = [
                    log
                    for log in state_recap.combat_log
                    if log.round_number == prev_round and log.actor.startswith("enemy")
                ]
                if recap_entries:
                    label = self.small_font.render("Last Round:", True, _COMBAT_COLORS["queue_recap_label"])
                    screen.blit(label, (panel_x + 8, queue_y))
                    ry = queue_y + scale_y(16)
                    recap_line_h = scale_y(15)
                    max_recap_y = panel_y + panel_h - scale_y(60)
                    for entry in recap_entries[:3]:
                        if ry + recap_line_h > max_recap_y:
                            break
                        # Extract enemy name from actor "enemy:0" → template name
                        enemy_name = entry.actor.replace(":", " ").title()
                        try:
                            eidx = int(entry.actor.split(":")[1])
                            if eidx < len(state_recap.enemies):
                                enemy_name = state_recap.enemies[eidx].template.name
                        except (ValueError, IndexError):
                            pass
                        # Extract damage from effects if present
                        dmg_text = ""
                        for eff in entry.effects_applied:
                            if "Dealt" in eff and "damage" in eff:
                                # "Dealt 45 damage ..." → "45 dmg"
                                try:
                                    dmg_val = eff.split("Dealt ")[1].split(" damage")[0]
                                    dmg_text = f" ({dmg_val} dmg)"
                                except (IndexError, ValueError):
                                    pass
                                break
                            if "Missed" in eff:
                                dmg_text = " (missed)"
                                break
                            if "Frozen" in eff or "frozen" in eff:
                                dmg_text = " (frozen)"
                                break
                        recap_line = f"{enemy_name}: {entry.action}{dmg_text}"
                        recap_surf = self.small_font.render(recap_line, True, _COMBAT_COLORS["queue_recap_text"])
                        screen.blit(recap_surf, (panel_x + 12, ry))
                        ry += recap_line_h
                    # Hint below recap
                    hint_y = ry + scale_y(4)
                    hint = self.small_font.render("Click weapons to queue", True, _COMBAT_COLORS["queue_hint_dim"])
                    screen.blit(hint, (panel_x + 8, hint_y))
                else:
                    # No enemy actions last round (rare)
                    hint = self.small_font.render(
                        "Click weapons to queue, Enter to execute",
                        True,
                        _COMBAT_COLORS["queue_bullet_dim"],
                    )
                    screen.blit(hint, (panel_x + 8, queue_y + scale_y(10)))
            else:
                # Round 1: no previous round to recap
                empty = self.small_font.render("No actions queued", True, Colors.TEXT_SECONDARY)
                screen.blit(empty, (panel_x + 8, queue_y + scale_y(10)))
                hint = self.small_font.render(
                    "Click weapons to queue, Enter to execute",
                    True,
                    _COMBAT_COLORS["queue_bullet_dim"],
                )
                screen.blit(hint, (panel_x + 8, queue_y + scale_y(28)))

        # Queue summary line (above buttons, when actions are queued)
        if self._action_queue and not self._action_queue.is_empty:
            n_actions = len(self._action_queue.actions)
            committed = self._action_queue.energy_committed
            state_q = self.engine.get_state()
            total_e = state_q.player.max_energy
            summary_text = (
                f"{n_actions} action{'s' if n_actions != 1 else ''}, {committed}/{total_e} energy"
            )
            summary_color = _COMBAT_COLORS["queue_summary_color"]
            summary_surf = self.small_font.render(summary_text, True, summary_color)
            summary_y = panel_y + panel_h - scale_y(50)
            screen.blit(summary_surf, (panel_x + 8, summary_y))

        # Execute and Undo buttons
        btn_y = panel_y + panel_h - scale_y(28)
        exec_w = scale_x(140)
        undo_w = scale_x(80)

        # Execute Turn button
        has_actions = self._action_queue and not self._action_queue.is_empty
        exec_bg = _COMBAT_COLORS["exec_active_bg"] if has_actions else _COMBAT_COLORS["exec_inactive_bg"]
        exec_border = Colors.GREEN if has_actions else _COMBAT_COLORS["exec_inactive_border"]
        exec_rect = pygame.Rect(panel_x + 8, btn_y, exec_w, scale_y(24))
        pygame.draw.rect(screen, exec_bg, exec_rect, border_radius=3)
        pygame.draw.rect(screen, exec_border, exec_rect, 1, border_radius=3)
        exec_label = self.small_font.render(
            "EXECUTE [Enter]",
            True,
            Colors.GREEN if has_actions else _COMBAT_COLORS["exec_inactive_text"],
        )
        screen.blit(
            exec_label, (exec_rect.x + exec_w // 2 - exec_label.get_width() // 2, btn_y + 4)
        )
        self._execute_btn_rect = exec_rect

        # Undo button
        undo_bg = _COMBAT_COLORS["undo_active_bg"] if has_actions else _COMBAT_COLORS["undo_inactive_bg"]
        undo_rect = pygame.Rect(panel_x + exec_w + 16, btn_y, undo_w, scale_y(24))
        pygame.draw.rect(screen, undo_bg, undo_rect, border_radius=3)
        pygame.draw.rect(
            screen, _COMBAT_COLORS["undo_active_border"] if has_actions else _COMBAT_COLORS["undo_inactive_border"], undo_rect, 1, border_radius=3
        )
        undo_label = self.small_font.render(
            "Undo [←]",
            True,
            Colors.TEXT_SECONDARY if has_actions else _COMBAT_COLORS["undo_inactive_text"],
        )
        screen.blit(
            undo_label, (undo_rect.x + undo_w // 2 - undo_label.get_width() // 2, btn_y + 4)
        )
        self._undo_btn_rect = undo_rect

        # Skip Turn hint (below buttons, centered in panel)
        skip = self.small_font.render("Enter with empty queue to skip turn", True, _COMBAT_COLORS["skip_hint_text"])
        skip_x = panel_x + (panel_w - skip.get_width()) // 2
        screen.blit(skip, (skip_x, btn_y + scale_y(26)))

        # Legendary ability buttons (Void Release, Overdrive)
        self._void_release_rect = None
        self._overdrive_rect = None
        state = self.engine.get_state()
        legendary = getattr(state.player, "_legendary", None)
        if legendary:
            leg_y = btn_y - scale_y(28)
            leg_btn_w = scale_x(120)
            leg_btn_h = scale_y(22)

            # Void Release — available when void_charge > 0 and release available
            if getattr(legendary, "void_release_available", False) and legendary.void_charge > 0:
                vr_rect = pygame.Rect(panel_x + 8, leg_y, leg_btn_w, leg_btn_h)
                pygame.draw.rect(screen, _COMBAT_COLORS["void_release_bg"], vr_rect, border_radius=3)
                pygame.draw.rect(screen, _COMBAT_COLORS["void_release_border"], vr_rect, 1, border_radius=3)
                vr_text = self.small_font.render(
                    f"Void Release ({legendary.void_charge} dmg)", True, _COMBAT_COLORS["void_release_text"]
                )
                screen.blit(vr_text, (vr_rect.x + 4, leg_y + 3))
                self._void_release_rect = vr_rect

            # Overdrive — available once per combat
            if getattr(legendary, "overdrive_available", False):
                od_x = panel_x + 8 + (leg_btn_w + 8 if self._void_release_rect else 0)
                od_rect = pygame.Rect(od_x, leg_y, leg_btn_w, leg_btn_h)
                pygame.draw.rect(screen, _COMBAT_COLORS["overdrive_bg"], od_rect, border_radius=3)
                pygame.draw.rect(screen, _COMBAT_COLORS["overdrive_border"], od_rect, 1, border_radius=3)
                od_text = self.small_font.render("Overdrive (2x turn)", True, _COMBAT_COLORS["overdrive_text"])
                screen.blit(od_text, (od_rect.x + 4, leg_y + 3))
                self._overdrive_rect = od_rect

    def _render_combat_log(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render scrollable combat log."""
        log_x = 730 + ox
        log_y = 530 + oy
        header = self.small_font.render("COMBAT LOG", True, Colors.TEXT_SECONDARY)
        screen.blit(header, (log_x, log_y))

        y = log_y + 20
        for line in self.visible_log_lines[-8:]:
            surf = self.small_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(surf, (log_x, y))
            y += 18

    def _render_floating_texts(self, screen: pygame.Surface) -> None:
        """Render floating damage/heal numbers.

        Dict-entries may carry a ``tier`` key (DamageTier) — when present,
        the renderer uses the tier's canonical font size + bold + stroke
        per spec §4.7 rather than the default info_font treatment.
        """
        from spacegame.engine.damage_text import DamageTier, get_tier_config

        for ft in self.floating_texts:
            alpha = max(0, min(255, int(255 * (ft["timer"] / ft.get("max_timer", 0.8)))))
            tier = ft.get("tier")
            if isinstance(tier, DamageTier):
                cfg = get_tier_config(tier)
                font = self._get_tier_font(cfg.font_size, cfg.bold)
                surf = font.render(ft["text"], False, ft["color"])
                if cfg.stroke:
                    # Void-deep stroke for cinematic-tier legibility.
                    from spacegame.engine.material_palette import get_role

                    stroke_color = get_role("void_deep")
                    stroke_surf = font.render(ft["text"], False, stroke_color)
                    stroke_surf.set_alpha(alpha)
                    bx = int(ft["x"]) - surf.get_width() // 2
                    by = int(ft["y"])
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        screen.blit(stroke_surf, (bx + dx, by + dy))
                surf.set_alpha(alpha)
                screen.blit(surf, (int(ft["x"]) - surf.get_width() // 2, int(ft["y"])))
            else:
                surf = self.info_font.render(ft["text"], True, ft["color"])
                surf.set_alpha(alpha)
                screen.blit(surf, (int(ft["x"]) - surf.get_width() // 2, int(ft["y"])))

    def _get_tier_font(self, size: int, bold: bool) -> pygame.font.Font:
        """Tier-font cache. Keeps the bold toggle from mutating the shared
        get_font() instances."""
        cache = getattr(self, "_damage_tier_font_cache", None)
        if cache is None:
            cache = {}
            self._damage_tier_font_cache = cache
        key = (size, bold)
        if key not in cache:
            font = pygame.font.Font(None, size)
            font.set_bold(bold)
            cache[key] = font
        return cache[key]

    def _render_intro_banner(self, screen: pygame.Surface) -> None:
        """Render the intro banner. Boss encounters get a dramatic treatment."""
        state = self.engine.get_state()
        is_boss_fight = any(e.template.is_boss for e in state.enemies)

        # Darker overlay for boss fights
        dim = 180 if is_boss_fight else 120
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, dim))
        screen.blit(overlay, (0, 0))

        # Fade in/out
        t = self.phase_timer / INTRO_DURATION
        alpha = int(255 * (1.0 - abs(2 * t - 1)))

        if is_boss_fight:
            boss = next((e for e in state.enemies if e.template.is_boss), None)
            if boss:
                # Boss intro: dramatic red-gold treatment
                # "BOSS ENCOUNTER" header
                header = self.info_font.render("BOSS ENCOUNTER", True, _COMBAT_COLORS["boss_header"])
                header.set_alpha(alpha)
                header_rect = header.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 60))
                screen.blit(header, header_rect)

                # Boss name in large dramatic text
                name_surf = self.banner_font.render(boss.template.name.upper(), True, _COMBAT_COLORS["boss_accent"])
                name_surf.set_alpha(alpha)
                name_rect = name_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 10))
                screen.blit(name_surf, name_rect)

                # Boss description
                desc_surf = self.small_font.render(
                    boss.template.description, True, Colors.TEXT_SECONDARY
                )
                desc_surf.set_alpha(alpha)
                desc_rect = desc_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 35))
                screen.blit(desc_surf, desc_rect)

                # Phase 1 name
                if boss.template.phases:
                    phase_name = boss.template.phases[0].name
                    phase_surf = self.small_font.render(phase_name, True, _COMBAT_COLORS["boss_header"])
                    phase_surf.set_alpha(alpha)
                    phase_rect = phase_surf.get_rect(
                        center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60)
                    )
                    screen.blit(phase_surf, phase_rect)

                # Accent lines (decorative)
                accent_color = _COMBAT_COLORS["boss_accent"]
                cx = WINDOW_WIDTH // 2
                cy = WINDOW_HEIGHT // 2 - 75
                line_w = int(200 * t)
                pygame.draw.line(screen, accent_color, (cx - line_w, cy), (cx + line_w, cy), 2)
                pygame.draw.line(
                    screen, accent_color, (cx - line_w, cy + 120), (cx + line_w, cy + 120), 2
                )
        else:
            # Standard combat intro
            text_surf = self.banner_font.render("COMBAT!", True, Colors.RED)
            text_surf.set_alpha(alpha)
            text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
            screen.blit(text_surf, text_rect)

            if state.enemies:
                names = ", ".join(e.template.name for e in state.enemies)
                name_surf = self.header_font.render(names, True, Colors.TEXT_PRIMARY)
                name_surf.set_alpha(alpha)
                name_rect = name_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
                screen.blit(name_surf, name_rect)

    def _render_combat_over_overlay(self, screen: pygame.Surface) -> None:
        """Render polished combat outcome overlay with stats."""
        # Dim background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        summary = self._get_outcome_summary()

        # Build all stat lines first so we can size the panel dynamically
        line_height = scale_y(26)
        pad = scale_x(30)
        panel_w = scale_x(500)
        max_text_w = panel_w - pad * 2

        stats: list[tuple[str, tuple[int, int, int]]] = [
            (f"Rounds: {summary['rounds']}", Colors.TEXT_PRIMARY),
            (f"Enemies defeated: {summary['enemies_defeated']}", Colors.TEXT_PRIMARY),
        ]

        if summary["enemies_fled"] > 0:
            stats.append((f"Enemies fled: {summary['enemies_fled']}", Colors.TEXT_SECONDARY))

        if summary["result"] == CombatResult.VICTORY and summary["xp_gained"] > 0:
            stats.append((f"XP gained: +{summary['xp_gained']}", Colors.TEXT_HIGHLIGHT))

        if summary["result"] == CombatResult.VICTORY and summary["loot"]:
            for cid, qty in summary["loot"].items():
                name = cid.replace("_", " ").title()
                stats.append((f"  Loot: {qty}x {name}", Colors.GREEN))

        if summary["result"] == CombatResult.VICTORY and summary.get("rare_loot"):
            for cid, qty in summary["rare_loot"].items():
                name = cid.replace("_", " ").title()
                stats.append((f"  RARE: {qty}x {name}", Colors.YELLOW))

        if summary["result"] == CombatResult.DEFEAT:
            stats.append(("Cargo lost: 30%", Colors.RED))
            stats.append(("Hull reduced to 25%", Colors.RED))

        if summary["result"] == CombatResult.FLED:
            stats.append(("Escaped with hull intact", Colors.YELLOW))

        if summary["result"] == CombatResult.NEGOTIATED:
            stats.append(("Resolved without bloodshed", Colors.TEXT_HIGHLIGHT))

        if summary["result"] == CombatResult.BRIBED:
            stats.append(("Enemies stood down", Colors.YELLOW))

        # Module damage report (player ship)
        state_end = self.engine.get_state()
        if state_end.player.module_states:
            damaged = [ms for ms in state_end.player.module_states if ms.current_hp < ms.max_hp]
            if damaged:
                disabled = [ms for ms in damaged if ms.disabled]
                intact = [ms for ms in damaged if not ms.disabled]
                if disabled:
                    names = ", ".join(ms.category.title() for ms in disabled[:3])
                    suffix = f" +{len(disabled) - 3} more" if len(disabled) > 3 else ""
                    stats.append((f"Modules destroyed: {names}{suffix}", Colors.RED))
                if intact:
                    names = ", ".join(ms.category.title() for ms in intact[:3])
                    suffix = f" +{len(intact) - 3} more" if len(intact) > 3 else ""
                    stats.append((f"Modules damaged: {names}{suffix}", _COMBAT_COLORS["dmg_near_miss"]))
            else:
                stats.append(("All modules intact", _COMBAT_COLORS["passive_positive_dim"]))

        # Calculate panel height dynamically
        title_h = scale_y(80)  # Title + separator
        stats_h = len(stats) * line_height
        hint_h = scale_y(50)  # Continue hint area
        panel_h = title_h + stats_h + hint_h + scale_y(20)

        panel_x = WINDOW_WIDTH // 2 - panel_w // 2
        panel_y = WINDOW_HEIGHT // 2 - panel_h // 2

        # Panel background
        draw_panel(
            screen,
            (panel_x, panel_y, panel_w, panel_h),
            alpha=240,
            bg_color=_COMBAT_COLORS["panel_modal_bg_dark"],
            border_color=summary["color"],
            border_radius=6,
        )

        # Title
        title_surf = self.banner_font.render(summary["title"], True, summary["color"])
        title_rect = title_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=panel_y + scale_y(18))
        screen.blit(title_surf, title_rect)

        # Separator
        sep_y = panel_y + title_h - scale_y(10)
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (panel_x + pad, sep_y),
            (panel_x + panel_w - pad, sep_y),
        )

        # Stats (clipped to panel width)
        stat_x = panel_x + pad
        stat_y = sep_y + scale_y(14)

        for text, color in stats:
            surf = self.info_font.render(text, True, color)
            # Clip text to panel width
            if surf.get_width() > max_text_w:
                clip_rect = pygame.Rect(0, 0, max_text_w, surf.get_height())
                screen.blit(surf, (stat_x, stat_y), clip_rect)
            else:
                screen.blit(surf, (stat_x, stat_y))
            stat_y += line_height

        # "Click or press ENTER to continue" hint (bottom of panel)
        hint_y = panel_y + panel_h - scale_y(30)
        hint_text = "Click or press ENTER to continue"
        hint_surf = self.small_font.render(hint_text, True, Colors.TEXT_SECONDARY)
        hint_rect = hint_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=hint_y)
        screen.blit(hint_surf, hint_rect)

    def _get_phase_display_text(self) -> str:
        """Get human-readable text for the current phase."""
        return {
            CombatPhase.INTRO: "",
            CombatPhase.PLAYER_INPUT: "YOUR TURN",
            CombatPhase.ANIMATING_PLAYER: "YOUR TURN",
            CombatPhase.ANIMATING_CREW: "CREW SUPPORT",
            CombatPhase.ANIMATING_ENEMIES: "ENEMY TURN",
            CombatPhase.ROUND_END: "",
            CombatPhase.COMBAT_OVER: "",
        }.get(self.phase, "")
