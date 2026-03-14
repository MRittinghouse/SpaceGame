"""Turn-based combat view.

Presents the combat encounter with phase-driven turn flow,
animated feedback, health bars, and action selection.
"""

import math
import random as _random

import pygame
import pygame_gui
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.combat import (
    CombatLogEntry,
    CombatMove,
    CombatResult,
)
from spacegame.models.combat_engine import (
    CombatEngine,
    FLEE_BASE_CHANCE,
    FLEE_MAX_CHANCE,
    FLEE_MIN_CHANCE,
    FLEE_SPEED_FACTOR,
)
from spacegame.models.player import Player
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar, draw_panel
from spacegame.engine.particles import (
    ParticlePool,
    LASER_HIT,
    MISSILE_EXPLOSION,
    SHIELD_IMPACT,
    HEAL_SPARKLE,
    SHIELD_RESTORE,
)
from spacegame.engine.screen_effects import ScreenShake, Vignette
from spacegame.engine.fonts import FontCache
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.utils.logger import logger


# ============================================================================
# Constants
# ============================================================================

INTRO_DURATION = 0.8
ROUND_END_DURATION = 0.3
DEFAULT_ANIMATION_DURATION = 0.5
BAR_LERP_SPEED = 8.0  # Units per second for smooth bar animation

# Layout zones
PLAYER_PANEL_X = 10
PLAYER_PANEL_Y = 55
PLAYER_PANEL_W = 220
PLAYER_PANEL_H = 460

ENEMY_PANEL_X = 1050
ENEMY_PANEL_Y = 55
ENEMY_PANEL_W = 220
ENEMY_CARD_H = 145
ENEMY_CARD_GAP = 10

# Bar rendering
BAR_HEIGHT = 14
BAR_LABEL_W = 50
SHIELD_COLOR = (80, 180, 255)
ENERGY_COLOR = (180, 100, 255)
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

ACTION_PANEL_Y = 525
ACTION_PANEL_H = 195
MOVE_BTN_W = 170
MOVE_BTN_H = 55
MOVE_BTN_GAP = 8
MOVE_BTN_COLS = 2
MOVE_BTN_X_START = 15
MOVE_BTN_Y_START = ACTION_PANEL_Y + 30

SPECIAL_BTN_Y = MOVE_BTN_Y_START + 2 * (MOVE_BTN_H + MOVE_BTN_GAP) + 4
SPECIAL_BTN_W = 120
SPECIAL_BTN_H = 36

FLEE_BTN_X = MOVE_BTN_X_START
NEGOTIATE_BTN_X = MOVE_BTN_X_START + SPECIAL_BTN_W + MOVE_BTN_GAP
BRIBE_BTN_X = NEGOTIATE_BTN_X + SPECIAL_BTN_W + 20 + MOVE_BTN_GAP

# Combat arena
ARENA_X = 240
ARENA_Y = 55
ARENA_W = 800
ARENA_H = 465
PLAYER_SHIP_POS = (380, 280)  # Player ship center in arena
ENEMY_SHIP_POS = (900, 280)   # Enemy ship center in arena



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

        # Target selection
        self.selected_target_idx: int = 0

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
        self.title_font = FontCache.get(36)
        self.header_font = FontCache.get(28)
        self.info_font = FontCache.get(24)
        self.small_font = FontCache.get(20)
        self.banner_font = FontCache.get(48)

        # Sprite manager for ship sprites
        self._sprite_mgr = get_sprite_manager()
        self._ship_sprite_cache: dict[str, Optional[AnimatedSprite]] = {}

        # Visual systems
        self.background = AnimatedBackground(
            "deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=100
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)
        self.particles = ParticlePool(500)
        self.screen_shake = ScreenShake()
        self.vignette = Vignette(WINDOW_WIDTH, WINDOW_HEIGHT, intensity=0.4)

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

        # Initialize displayed bar values from actual state
        state = self.engine.get_state()
        self._displayed_player_hull = float(state.player.hull)
        self._displayed_player_shields = float(state.player.shields)
        self._displayed_player_energy = float(state.player.energy)
        self._displayed_enemy_hulls = [float(e.current_hull) for e in state.enemies]
        self._displayed_enemy_shields = [float(e.current_shields) for e in state.enemies]
        self._enemy_flash_timers = [0.0] * len(state.enemies)
        self._player_flash_timer = 0.0
        self._enemy_sprite_flashes = [0.0] * len(state.enemies)
        self._enemy_shield_flashes = [0.0] * len(state.enemies)
        self._player_sprite_flash = 0.0
        self._player_shield_flash = 0.0
        self._destroying_enemies.clear()
        self._previously_dead: set[int] = set()  # Enemy indices dead before this round

        self._create_ui()
        logger.info("Entered combat view")

    def on_exit(self) -> None:
        """Called when leaving combat view."""
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited combat view")

    def _create_ui(self) -> None:
        """Create pygame_gui elements."""
        self.continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH // 2 - 80, WINDOW_HEIGHT // 2 + 100, 160, 45
            ),
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
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Update combat view each frame."""
        self.phase_timer += dt
        self.background.update(dt)
        self.particles.update(dt)
        self.screen_shake.update(dt)

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

        # Phase-specific logic
        if self.phase == CombatPhase.INTRO:
            if self.phase_timer >= INTRO_DURATION:
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
            if self.continue_button:
                self.continue_button.show()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        """Render the combat view."""
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        ox, oy = self.screen_shake.offset

        # Header
        self._render_header(screen, ox, oy)

        # Player panel
        self._render_player_panel(screen, ox, oy)

        # Enemy panels
        self._render_enemy_panels(screen, ox, oy)

        # Combat arena
        self._render_combat_arena(screen, ox, oy)

        # Action panel
        self._render_action_panel(screen, ox, oy)

        # Combat log
        self._render_combat_log(screen, ox, oy)

        # Particles
        self.particles.render(screen)

        # Floating texts
        self._render_floating_texts(screen)

        # Vignette
        self.vignette.render(screen)

        # Intro banner
        if self.phase == CombatPhase.INTRO:
            self._render_intro_banner(screen)

        # Combat over overlay
        if self.phase == CombatPhase.COMBAT_OVER:
            self._render_combat_over_overlay(screen)

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
            self._handle_click(event.pos)

        if event.type == pygame.MOUSEMOTION:
            self._handle_hover(event.pos)

    def _handle_key(self, event: pygame.event.Event) -> None:
        """Handle keyboard shortcuts."""
        # Enter/Return: continue from combat over screen
        if self.phase == CombatPhase.COMBAT_OVER and event.key in (
            pygame.K_RETURN, pygame.K_KP_ENTER
        ):
            self._on_continue_pressed()
            return

        if self.phase != CombatPhase.PLAYER_INPUT:
            return

        # Negotiate sub-menu is open — handle skill selection or cancel
        if self._negotiate_menu_open:
            skill_keys = {
                pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
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

        # Number keys 1-4: execute equipment moves
        key_to_idx = {
            pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3,
        }
        if event.key in key_to_idx:
            idx = key_to_idx[event.key]
            if idx < len(self.move_buttons) and self.move_buttons[idx].enabled:
                self._execute_player_action(self.move_buttons[idx].move.id)
            return

        # Tab: cycle target
        if event.key == pygame.K_TAB:
            enemies = self.engine.get_state().enemies
            if enemies:
                next_idx = (self.selected_target_idx + 1) % len(enemies)
                self.select_target(next_idx)
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

    def _handle_click(self, pos: tuple[int, int]) -> None:
        """Handle mouse clicks on move buttons and enemy cards."""
        if self.phase == CombatPhase.PLAYER_INPUT:
            # Move buttons
            for btn in self.move_buttons:
                if btn.rect.collidepoint(pos) and btn.enabled:
                    self._execute_player_action(btn.move.id)
                    return

            # Flee button area
            flee_rect = pygame.Rect(
                FLEE_BTN_X, SPECIAL_BTN_Y, SPECIAL_BTN_W, SPECIAL_BTN_H
            )
            if flee_rect.collidepoint(pos):
                self._attempt_flee()
                return

            # Negotiate button area
            neg_rect = pygame.Rect(
                NEGOTIATE_BTN_X, SPECIAL_BTN_Y,
                SPECIAL_BTN_W + 20, SPECIAL_BTN_H,
            )
            if neg_rect.collidepoint(pos):
                self._attempt_negotiate_menu()
                return

            # Bribe button area
            bribe_rect = pygame.Rect(
                BRIBE_BTN_X, SPECIAL_BTN_Y,
                SPECIAL_BTN_W, SPECIAL_BTN_H,
            )
            if bribe_rect.collidepoint(pos):
                self._attempt_bribe()
                return

            # Negotiate sub-menu skill buttons
            if self._negotiate_menu_open:
                for i, skill in enumerate(self._negotiate_skills):
                    skill_rect = pygame.Rect(
                        NEGOTIATE_BTN_X,
                        SPECIAL_BTN_Y - (len(self._negotiate_skills) - i) * 30 - 5,
                        SPECIAL_BTN_W + 20, 26,
                    )
                    if skill_rect.collidepoint(pos):
                        self._select_negotiate_skill(skill)
                        return

            # Enemy card target selection
            state = self.engine.get_state()
            for i, enemy in enumerate(state.enemies):
                card_y = ENEMY_PANEL_Y + i * (ENEMY_CARD_H + ENEMY_CARD_GAP)
                card_rect = pygame.Rect(
                    ENEMY_PANEL_X, card_y, ENEMY_PANEL_W, ENEMY_CARD_H
                )
                if card_rect.collidepoint(pos) and enemy.is_alive and not enemy.is_fled:
                    self.select_target(i)
                    return

    def _handle_hover(self, pos: tuple[int, int]) -> None:
        """Update hover state on move buttons."""
        for btn in self.move_buttons:
            btn.hovered = btn.rect.collidepoint(pos)

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def _advance_phase(self, new_phase: CombatPhase) -> None:
        """Transition to a new combat phase."""
        self.phase = new_phase
        self.phase_timer = 0.0
        self.current_animation = None
        self.animation_queue.clear()

        if new_phase == CombatPhase.PLAYER_INPUT:
            self._build_move_buttons()
            self._auto_advance_target()
            # Snapshot dead enemies so we can detect new deaths this round
            state = self.engine.get_state()
            self._previously_dead = {
                i for i, e in enumerate(state.enemies) if not e.is_alive
            }
        elif new_phase == CombatPhase.ANIMATING_CREW:
            self._start_crew_phase()
        elif new_phase == CombatPhase.ANIMATING_ENEMIES:
            self._start_enemy_phase()
        elif new_phase == CombatPhase.ROUND_END:
            self._start_round_end()
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

    def _execute_player_action(self, move_id: str) -> None:
        """Execute a player move and transition to animation phase."""
        if self.phase != CombatPhase.PLAYER_INPUT:
            return

        logs = self.engine.execute_player_move(move_id, self.selected_target_idx)
        for log in logs:
            self._enqueue_animation(log, source="player")
            self._append_log_line(log)

        self._advance_phase(CombatPhase.ANIMATING_PLAYER)

    # ------------------------------------------------------------------
    # Move buttons
    # ------------------------------------------------------------------

    def _build_move_buttons(self) -> None:
        """Build move button list from current player state."""
        state = self.engine.get_state()
        self.move_buttons = []

        for i, move in enumerate(state.player.equipment_moves):
            col = i % MOVE_BTN_COLS
            row = i // MOVE_BTN_COLS
            bx = MOVE_BTN_X_START + col * (MOVE_BTN_W + MOVE_BTN_GAP)
            by = MOVE_BTN_Y_START + row * (MOVE_BTN_H + MOVE_BTN_GAP)
            rect = pygame.Rect(bx, by, MOVE_BTN_W, MOVE_BTN_H)

            # Check if affordable and off cooldown
            on_cooldown = move.id in state.player.cooldowns
            cd_remaining = state.player.cooldowns.get(move.id, 0)
            affordable = state.player.energy >= move.energy_cost
            enabled = affordable and not on_cooldown

            self.move_buttons.append(
                _MoveButton(
                    rect=rect,
                    move=move,
                    enabled=enabled,
                    cooldown_remaining=cd_remaining,
                )
            )

    # ------------------------------------------------------------------
    # Flee
    # ------------------------------------------------------------------

    def _get_flee_chance(self) -> int:
        """Calculate flee chance percentage from engine formula."""
        state = self.engine.get_state()
        player_speed = state.player.speed

        living_enemies = [
            e for e in state.enemies if e.is_alive and not e.is_fled
        ]
        if not living_enemies:
            return FLEE_MAX_CHANCE

        avg_enemy_speed = sum(
            e.template.speed for e in living_enemies
        ) / len(living_enemies)

        return max(
            FLEE_MIN_CHANCE,
            min(
                FLEE_MAX_CHANCE,
                FLEE_BASE_CHANCE + int(
                    (player_speed - avg_enemy_speed) * FLEE_SPEED_FACTOR
                ),
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
        success, msg, logs = self.engine.attempt_negotiate(
            skill_id, self.social_manager
        )
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

        success, cost, logs = self.engine.attempt_bribe(
            self._bribe_credits_available
        )
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
            result.append({
                "id": move.id,
                "name": move.name,
                "skipped": move.id in self.skip_crew_ids,
            })
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
        """Execute crew moves and enqueue their animations."""
        logs = self.engine.execute_crew_moves()
        if not logs:
            # No crew moves — skip straight to enemy phase
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
        self.animation_queue.append(
            AnimationEvent(log_entry=log_entry, source=source)
        )

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
        """Trigger visual effects for an animation event."""
        log = anim.log_entry
        is_player_source = anim.source == "player"
        is_enemy_source = anim.source == "enemy"

        # Determine target position for floating text
        if is_player_source:
            # Player attacks enemy → effects appear at enemy panel
            target_x = float(ENEMY_PANEL_X + ENEMY_PANEL_W // 2)
            target_y = float(
                ENEMY_PANEL_Y
                + self.selected_target_idx * (ENEMY_CARD_H + ENEMY_CARD_GAP)
                + ENEMY_CARD_H // 2
            )
        else:
            # Enemy/crew attacks → effects appear at player panel
            target_x = float(PLAYER_PANEL_X + PLAYER_PANEL_W // 2)
            target_y = float(PLAYER_PANEL_Y + PLAYER_PANEL_H // 3)

        if log.hit:
            # Floating damage/effect text from log effects
            for effect_text in log.effects_applied:
                self.floating_texts.append({
                    "text": effect_text,
                    "x": target_x,
                    "y": target_y,
                    "color": Colors.RED if is_player_source else Colors.YELLOW,
                    "timer": 0.8,
                    "max_timer": 0.8,
                    "vy": -40.0,
                })
                target_y -= 20  # Stack multiple effects

            # Screen shake on hit
            self.screen_shake.trigger(intensity=3.0, duration=0.15)

            # Particle effects based on action type
            action_lower = log.action.lower()
            has_shield_text = any("shield" in e.lower() for e in log.effects_applied)
            has_hull_text = any("hull" in e.lower() and "restore" in e.lower() for e in log.effects_applied)
            has_shield_restore = any("shield" in e.lower() and "restore" in e.lower() for e in log.effects_applied)

            if has_hull_text:
                self.particles.emit(target_x, target_y, HEAL_SPARKLE)
            elif has_shield_restore:
                self.particles.emit(target_x, target_y, SHIELD_RESTORE)
            elif has_shield_text:
                self.particles.emit(target_x, target_y, SHIELD_IMPACT)
            elif "missile" in action_lower or "torpedo" in action_lower:
                self.particles.emit(target_x, target_y, MISSILE_EXPLOSION)
                get_audio_manager().play_sfx("combat_missile")
            else:
                self.particles.emit(target_x, target_y, LASER_HIT)
                get_audio_manager().play_sfx("combat_laser")

            # Flash timers (panel + sprite)
            if is_player_source:
                # Player hit an enemy — flash the target enemy card + sprite
                if self.selected_target_idx < len(self._enemy_flash_timers):
                    self._enemy_flash_timers[self.selected_target_idx] = 0.15
                    if has_shield_text and not has_shield_restore:
                        if self.selected_target_idx < len(self._enemy_shield_flashes):
                            self._enemy_shield_flashes[self.selected_target_idx] = 0.2
                            get_audio_manager().play_sfx("combat_shield")
                    else:
                        if self.selected_target_idx < len(self._enemy_sprite_flashes):
                            self._enemy_sprite_flashes[self.selected_target_idx] = 0.12
                            get_audio_manager().play_sfx("combat_hit")
            elif is_enemy_source:
                # Enemy hit the player — flash the player panel + sprite
                self._player_flash_timer = 0.15
                if has_shield_text and not has_shield_restore:
                    self._player_shield_flash = 0.2
                    get_audio_manager().play_sfx("combat_shield")
                else:
                    self._player_sprite_flash = 0.12
                    get_audio_manager().play_sfx("combat_hit")

            # Check for enemy deaths → trigger destroy animation
            if is_player_source or anim.source == "crew":
                self._check_enemy_deaths()

            # Store current animation text for arena display
            self._arena_action_text = log.action
            self._arena_action_timer = 0.5
        else:
            # Miss — show "MISS" text
            self.floating_texts.append({
                "text": "MISS",
                "x": target_x,
                "y": target_y,
                "color": Colors.TEXT_SECONDARY,
                "timer": 0.6,
                "max_timer": 0.6,
                "vy": -30.0,
            })

    def _check_enemy_deaths(self) -> None:
        """Check if any enemies just died and trigger destroy animations."""
        state = self.engine.get_state()

        for idx, enemy in enumerate(state.enemies):
            if idx in self._destroying_enemies:
                continue  # Already destroying
            if idx in self._previously_dead:
                continue  # Was already dead before this round
            if not enemy.is_alive and not enemy.is_fled:
                # Newly dead enemy — start destroy animation
                anim = self._get_ship_sprite(enemy.template.id, "enemy", scale=3)
                if anim is not None:
                    anim.play("destroy")
                    # Use the enemy's visual slot position
                    living_before = sum(
                        1 for ii in range(idx)
                        if state.enemies[ii].is_alive and not state.enemies[ii].is_fled
                    )
                    living_total = sum(
                        1 for e in state.enemies if e.is_alive and not e.is_fled
                    )
                    enemy_x = ENEMY_SHIP_POS[0]
                    enemy_y = (
                        ENEMY_SHIP_POS[1]
                        + (living_before - living_total // 2) * 80
                    )
                    self._destroying_enemies[idx] = (enemy_x, enemy_y, anim)

                    # Explosion particles + SFX
                    self.particles.emit(
                        float(enemy_x), float(enemy_y), MISSILE_EXPLOSION
                    )
                    get_audio_manager().play_sfx("combat_explosion")
                    self.screen_shake.trigger(intensity=5.0, duration=0.25)

                self._previously_dead.add(idx)

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

        return {
            "result": result,
            "title": title_map.get(result, result.value.upper()),
            "color": color_map.get(result, Colors.TEXT_PRIMARY),
            "xp_gained": xp_gained,
            "loot": loot,
            "rounds": state.round_number,
            "enemies_defeated": sum(
                1 for e in state.enemies if not e.is_alive
            ),
            "enemies_fled": sum(
                1 for e in state.enemies if e.is_fled
            ),
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
    def _lerp_toward(current: float, target: float, max_step: float) -> float:
        """Move current toward target by at most max_step."""
        diff = target - current
        if abs(diff) <= max_step:
            return target
        return current + (max_step if diff > 0 else -max_step)

    # ------------------------------------------------------------------
    # Enemy display state
    # ------------------------------------------------------------------

    def _get_enemy_display_state(self, idx: int) -> dict:
        """Get display info for an enemy card."""
        state = self.engine.get_state()
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

    def _render_player_panel(self, screen: pygame.Surface, ox: int, oy: int) -> None:
        """Render player status panel with health, shield, and energy bars."""
        state = self.engine.get_state()
        px = PLAYER_PANEL_X + ox
        py = PLAYER_PANEL_Y + oy

        # Panel background
        draw_panel(
            screen, (px, py, PLAYER_PANEL_W, PLAYER_PANEL_H),
            alpha=200, bg_color=(15, 20, 40), border_radius=4,
        )

        # Flash overlay on hit
        if self._player_flash_timer > 0:
            flash_alpha = int(80 * (self._player_flash_timer / 0.15))
            flash_surf = pygame.Surface(
                (PLAYER_PANEL_W, PLAYER_PANEL_H), pygame.SRCALPHA
            )
            flash_surf.fill((220, 50, 50, flash_alpha))
            screen.blit(flash_surf, (px, py))

        # Ship name header
        ship_name = "YOUR SHIP"
        name_surf = self.header_font.render(ship_name, True, Colors.TEXT_HIGHLIGHT)
        name_rect = name_surf.get_rect(centerx=px + PLAYER_PANEL_W // 2, top=py + 8)
        screen.blit(name_surf, name_rect)

        # Separator line
        sep_y = py + 32
        pygame.draw.line(
            screen, Colors.UI_BORDER,
            (px + 8, sep_y), (px + PLAYER_PANEL_W - 8, sep_y),
        )

        # Bars start below header
        bar_x = px + 10
        bar_w = PLAYER_PANEL_W - 20
        y = sep_y + 12

        # Hull bar
        hull_ratio = (
            self._displayed_player_hull / state.player.max_hull
            if state.player.max_hull > 0
            else 0
        )
        hull_color = _bar_color_for_ratio(hull_ratio)
        self._render_bar(
            screen, bar_x, y, bar_w, BAR_HEIGHT,
            self._displayed_player_hull, state.player.max_hull,
            hull_color, "Hull",
        )
        y += BAR_HEIGHT + 10

        # Shield bar
        shield_ratio = (
            self._displayed_player_shields / state.player.max_shields
            if state.player.max_shields > 0
            else 0
        )
        self._render_bar(
            screen, bar_x, y, bar_w, BAR_HEIGHT,
            self._displayed_player_shields, state.player.max_shields,
            SHIELD_COLOR, "Shld",
        )
        y += BAR_HEIGHT + 10

        # Energy bar
        self._render_bar(
            screen, bar_x, y, bar_w, BAR_HEIGHT,
            self._displayed_player_energy, state.player.max_energy,
            ENERGY_COLOR, "Engy",
        )
        y += BAR_HEIGHT + 16

        # Active effects badges (icon + text)
        if state.player.active_effects:
            effects_label = self.small_font.render(
                "Effects:", True, Colors.TEXT_SECONDARY
            )
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
        active_cds = {
            k: v for k, v in state.player.cooldowns.items() if v > 0
        }
        if active_cds:
            y += 4
            cd_label = self.small_font.render(
                "Cooldowns:", True, Colors.TEXT_SECONDARY
            )
            screen.blit(cd_label, (bar_x, y))
            y += 18
            for move_id, turns in active_cds.items():
                move_name = self._find_move_name(move_id, state)
                cd_text = f"{move_name}: {turns}t"
                cd_surf = self.small_font.render(
                    cd_text, True, Colors.TEXT_SECONDARY
                )
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
            screen, (x, y, ENEMY_PANEL_W, ENEMY_CARD_H),
            alpha=200, bg_color=(15, 20, 40), border_color=None, border_radius=4,
        )

        # Flash overlay on hit
        if idx < len(self._enemy_flash_timers) and self._enemy_flash_timers[idx] > 0:
            flash_alpha = int(80 * (self._enemy_flash_timers[idx] / 0.15))
            flash_surf = pygame.Surface(
                (ENEMY_PANEL_W, ENEMY_CARD_H), pygame.SRCALPHA
            )
            flash_surf.fill((220, 50, 50, flash_alpha))
            screen.blit(flash_surf, (x, y))

        # Border — highlight if selected, pulsing glow
        if is_selected and enemy.is_alive and not enemy.is_fled:
            pulse_alpha = int(180 + 60 * math.sin(self.phase_timer * 5))
            border_color = (*Colors.TEXT_HIGHLIGHT[:3],)
            # Glow border via SRCALPHA surface
            glow_surf = pygame.Surface(
                (ENEMY_PANEL_W + 4, ENEMY_CARD_H + 4), pygame.SRCALPHA
            )
            pygame.draw.rect(
                glow_surf,
                (*border_color, pulse_alpha),
                (0, 0, ENEMY_PANEL_W + 4, ENEMY_CARD_H + 4),
                2, border_radius=4,
            )
            screen.blit(glow_surf, (x - 2, y - 2))
        else:
            pygame.draw.rect(
                screen, Colors.UI_BORDER,
                (x, y, ENEMY_PANEL_W, ENEMY_CARD_H), 1, border_radius=4,
            )

        # Defeated / fled overlay
        if not enemy.is_alive:
            self._render_enemy_overlay(screen, x, y, "DEFEATED", Colors.RED)
            return
        if enemy.is_fled:
            self._render_enemy_overlay(screen, x, y, "FLED", Colors.YELLOW)
            return

        # Small ship sprite (top-right of card)
        card_anim = self._get_ship_sprite(enemy.template.id, "enemy", scale=1)
        card_sprite = card_anim.get_surface() if card_anim else None
        if card_sprite:
            sprite_rect = card_sprite.get_rect(topright=(x + ENEMY_PANEL_W - 6, y + 4))
            screen.blit(card_sprite, sprite_rect)

        # Enemy name
        name_surf = self.info_font.render(
            enemy.template.name, True, Colors.TEXT_PRIMARY
        )
        screen.blit(name_surf, (x + 8, y + 6))

        # Behavior tag
        behavior_text = enemy.template.behavior.value.capitalize()
        behavior_surf = self.small_font.render(
            behavior_text, True, Colors.TEXT_SECONDARY
        )
        screen.blit(behavior_surf, (x + 8, y + 26))

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
        hull_ratio = (
            displayed_hull / enemy.template.hull if enemy.template.hull > 0 else 0
        )
        hull_color = _bar_color_for_ratio(hull_ratio)
        self._render_bar(
            screen, bar_x, bar_y, bar_w, BAR_HEIGHT - 2,
            displayed_hull, enemy.template.hull, hull_color, "Hull",
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
                screen, bar_x, bar_y, bar_w, BAR_HEIGHT - 2,
                displayed_shields, enemy.template.shields, SHIELD_COLOR, "Shld",
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
        dim_surf = pygame.Surface(
            (ENEMY_PANEL_W, ENEMY_CARD_H), pygame.SRCALPHA
        )
        dim_surf.fill((0, 0, 0, 120))
        screen.blit(dim_surf, (x, y))

        # Centered text
        text_surf = self.header_font.render(text, True, color)
        text_rect = text_surf.get_rect(
            center=(x + ENEMY_PANEL_W // 2, y + ENEMY_CARD_H // 2)
        )
        screen.blit(text_surf, text_rect)

    # ------------------------------------------------------------------
    # Bar rendering
    # ------------------------------------------------------------------

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
    ) -> None:
        """Render a labeled health/shield/energy bar with fill and highlight edge."""
        draw_bar(
            screen, x, y, width, height, current, maximum, color,
            label=label, font=self.small_font,
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
        return move_id

    def _get_ship_sprite(
        self, sprite_id: str, role: str, scale: int = 2
    ) -> Optional[AnimatedSprite]:
        """Get a cached AnimatedSprite for a ship."""
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
                pygame.draw.line(crack_surf, (20, 15, 10, alpha),
                                 (x1, y1), (x1 + dx, y1 + dy), 1)
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
                pygame.draw.line(crack_surf, (15, 10, 5, alpha),
                                 (x1, y1), (x1 + dx, y1 + dy), 2)
                surf.blit(crack_surf, (0, 0))

            # Orange/yellow spark dots
            for _ in range(10):
                x = rng.randint(12, size - 12)
                y = rng.randint(12, size - 12)
                r = rng.randint(1, 3)
                color = rng.choice([
                    (255, 160, 40, 140),
                    (255, 200, 60, 120),
                    (255, 120, 20, 100),
                ])
                pygame.draw.circle(surf, color, (x, y), r)

        return surf

    def _apply_damage_overlay(
        self, surface: pygame.Surface, hull_ratio: float
    ) -> pygame.Surface:
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

        # Player ship (left side, facing right)
        player_x = PLAYER_SHIP_POS[0] + ox
        player_y = PLAYER_SHIP_POS[1] + oy
        hull_ratio = state.player.hull / state.player.max_hull if state.player.max_hull > 0 else 0

        player_ship_id = self.player.ship.ship_type.id if self.player else None
        player_anim = self._get_ship_sprite(player_ship_id, "player", scale=3) if player_ship_id else None
        player_sprite = player_anim.get_surface() if player_anim else None
        if player_sprite:
            # Rotate 90° so nose points right
            rotated = pygame.transform.rotate(player_sprite, -90)
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
            rect = rotated.get_rect(center=(player_x, player_y))
            screen.blit(rotated, rect)
            # Shield shimmer: cyan glow ring around ship
            if self._player_shield_flash > 0:
                shimmer_t = self._player_shield_flash / 0.2
                shimmer_alpha = int(160 * shimmer_t)
                shimmer_r = max(rotated.get_width(), rotated.get_height()) // 2 + 6
                shimmer_surf = pygame.Surface(
                    (shimmer_r * 2 + 4, shimmer_r * 2 + 4), pygame.SRCALPHA
                )
                sc = shimmer_r + 2
                pygame.draw.circle(
                    shimmer_surf, (80, 200, 255, shimmer_alpha),
                    (sc, sc), shimmer_r, 3,
                )
                screen.blit(shimmer_surf, (player_x - sc, player_y - sc))
        else:
            self._draw_ship_silhouette(screen, player_x, player_y, facing_right=True, hull_ratio=hull_ratio)

        # Enemy ships (right side, facing left)
        living_enemies = [(i, e) for i, e in enumerate(state.enemies) if e.is_alive and not e.is_fled]
        for j, (idx, enemy) in enumerate(living_enemies[:3]):
            enemy_x = ENEMY_SHIP_POS[0] + ox
            enemy_y = ENEMY_SHIP_POS[1] + oy + (j - len(living_enemies) // 2) * 80
            e_hull_ratio = enemy.current_hull / enemy.template.hull if enemy.template.hull > 0 else 0

            enemy_anim = self._get_ship_sprite(enemy.template.id, "enemy", scale=3)
            enemy_sprite = enemy_anim.get_surface() if enemy_anim else None
            if enemy_sprite:
                # Rotate 90° so nose points left
                rotated = pygame.transform.rotate(enemy_sprite, 90)
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
                        2, border_radius=4,
                    )
                    screen.blit(glow_surf, (enemy_x - rotated.get_width() // 2 - 4,
                                            enemy_y - rotated.get_height() // 2 - 4))
                rect = rotated.get_rect(center=(enemy_x, enemy_y))
                screen.blit(rotated, rect)
                # Shield shimmer: cyan glow ring around ship
                if idx < len(self._enemy_shield_flashes) and self._enemy_shield_flashes[idx] > 0:
                    shimmer_t = self._enemy_shield_flashes[idx] / 0.2
                    shimmer_alpha = int(160 * shimmer_t)
                    shimmer_r = max(rotated.get_width(), rotated.get_height()) // 2 + 6
                    shimmer_surf = pygame.Surface(
                        (shimmer_r * 2 + 4, shimmer_r * 2 + 4), pygame.SRCALPHA
                    )
                    sc = shimmer_r + 2
                    pygame.draw.circle(
                        shimmer_surf, (80, 200, 255, shimmer_alpha),
                        (sc, sc), shimmer_r, 3,
                    )
                    screen.blit(shimmer_surf, (enemy_x - sc, enemy_y - sc))
            else:
                self._draw_ship_silhouette(
                    screen, enemy_x, enemy_y, facing_right=False, hull_ratio=e_hull_ratio,
                    is_selected=(idx == self.selected_target_idx),
                )

        # Render destroying enemy ships (explosion animation)
        finished_destroys = []
        for idx, (ex, ey, anim) in self._destroying_enemies.items():
            sprite_surf = anim.get_surface()
            if sprite_surf and not anim.is_finished():
                rotated = pygame.transform.rotate(sprite_surf, 90)
                rect = rotated.get_rect(center=(ex + ox, ey + oy))
                screen.blit(rotated, rect)
            elif anim.is_finished():
                finished_destroys.append(idx)
        for idx in finished_destroys:
            del self._destroying_enemies[idx]

        # Action text flash in center arena
        if self._arena_action_timer > 0 and self._arena_action_text:
            alpha = int(255 * min(1.0, self._arena_action_timer / 0.3))
            action_surf = self.header_font.render(
                self._arena_action_text, True, Colors.TEXT_HIGHLIGHT
            )
            action_surf.set_alpha(alpha)
            action_rect = action_surf.get_rect(
                center=(WINDOW_WIDTH // 2 + ox, 180 + oy)
            )
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
            banner_rect = banner_surf.get_rect(
                center=(WINDOW_WIDTH // 2 + ox, 90 + oy)
            )
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
        r = int(60 + (1.0 - hull_ratio) * 140)
        g = int(80 + hull_ratio * 100)
        b = int(120 + hull_ratio * 60)
        body_color = (min(255, r), min(255, g), min(255, b), 220)

        # Wedge points
        if facing_right:
            points = [
                (4, cy - h // 3),      # Top-left
                (w - 4, cy),            # Nose (right)
                (4, cy + h // 3),       # Bottom-left
            ]
            engine_x = 6
        else:
            points = [
                (w, cy - h // 3),       # Top-right
                (8, cy),                # Nose (left)
                (w, cy + h // 3),       # Bottom-right
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
        # Panel background
        panel_rect = pygame.Rect(
            0 + ox, ACTION_PANEL_Y + oy, 720, ACTION_PANEL_H
        )
        draw_panel(
            screen, panel_rect,
            alpha=200, bg_color=(12, 16, 32), border_color=None, border_radius=0,
        )
        pygame.draw.line(
            screen, Colors.UI_BORDER,
            (ox, ACTION_PANEL_Y + oy), (720 + ox, ACTION_PANEL_Y + oy),
        )

        # "ACTIONS" header
        header = self.info_font.render("ACTIONS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (MOVE_BTN_X_START + ox, ACTION_PANEL_Y + 6 + oy))

        # Move buttons
        is_input = self.phase == CombatPhase.PLAYER_INPUT
        for btn in self.move_buttons:
            self._render_move_button(screen, btn, ox, oy, is_input)

        # Flee button
        flee_chance = self._get_flee_chance()
        flee_text = f"Flee ({flee_chance}%)"
        self._render_special_button(
            screen, FLEE_BTN_X + ox, SPECIAL_BTN_Y + oy,
            SPECIAL_BTN_W, SPECIAL_BTN_H,
            flee_text, is_input, Colors.YELLOW,
        )

        # Negotiate button
        neg_available = self._is_negotiate_available() and is_input
        neg_text = "Negotiate" if neg_available else "Negotiate (Used)"
        neg_color = Colors.TEXT_HIGHLIGHT if neg_available else Colors.TEXT_SECONDARY
        self._render_special_button(
            screen, NEGOTIATE_BTN_X + ox, SPECIAL_BTN_Y + oy,
            SPECIAL_BTN_W + 20, SPECIAL_BTN_H,
            neg_text, neg_available, neg_color,
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
            screen, BRIBE_BTN_X + ox, SPECIAL_BTN_Y + oy,
            SPECIAL_BTN_W, SPECIAL_BTN_H,
            bribe_text, bribe_available, bribe_color,
        )

        # Target indicator
        state = self.engine.get_state()
        if state.enemies:
            target = state.enemies[self.selected_target_idx]
            target_text = f"Target: {target.template.name}"
            target_surf = self.small_font.render(
                target_text, True, Colors.TEXT_HIGHLIGHT
            )
            screen.blit(
                target_surf,
                (BRIBE_BTN_X + SPECIAL_BTN_W + 16 + ox, SPECIAL_BTN_Y + 10 + oy),
            )

        # Negotiate sub-menu (skill options above the Negotiate button)
        if self._negotiate_menu_open and is_input:
            for i, skill in enumerate(self._negotiate_skills):
                skill_y = (
                    SPECIAL_BTN_Y
                    - (len(self._negotiate_skills) - i) * 30
                    - 5
                    + oy
                )
                skill_x = NEGOTIATE_BTN_X + ox
                skill_w = SPECIAL_BTN_W + 20
                skill_h = 26

                # Background
                sk_surf = pygame.Surface((skill_w, skill_h), pygame.SRCALPHA)
                sk_surf.fill((25, 35, 60, 230))
                screen.blit(sk_surf, (skill_x, skill_y))
                pygame.draw.rect(
                    screen, Colors.TEXT_HIGHLIGHT,
                    (skill_x, skill_y, skill_w, skill_h), 1, border_radius=2,
                )

                # Key hint + label
                label = f"[{i + 1}] {skill.capitalize()}"
                label_surf = self.small_font.render(
                    label, True, Colors.TEXT_HIGHLIGHT
                )
                label_rect = label_surf.get_rect(
                    centery=skill_y + skill_h // 2, left=skill_x + 6
                )
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
        has_damage = any(
            e.type.value == "damage" for e in btn.move.effects
        )
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
        """Render floating damage/heal numbers."""
        for ft in self.floating_texts:
            alpha = max(0, min(255, int(255 * (ft["timer"] / ft.get("max_timer", 0.8)))))
            surf = self.info_font.render(ft["text"], True, ft["color"])
            surf.set_alpha(alpha)
            screen.blit(surf, (int(ft["x"]) - surf.get_width() // 2, int(ft["y"])))

    def _render_intro_banner(self, screen: pygame.Surface) -> None:
        """Render the intro 'COMBAT!' banner."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Fade in/out
        t = self.phase_timer / INTRO_DURATION
        alpha = int(255 * (1.0 - abs(2 * t - 1)))
        text_surf = self.banner_font.render("COMBAT!", True, Colors.RED)
        text_surf.set_alpha(alpha)
        text_rect = text_surf.get_rect(
            center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30)
        )
        screen.blit(text_surf, text_rect)

        # Show enemy name
        state = self.engine.get_state()
        if state.enemies:
            names = ", ".join(e.template.name for e in state.enemies)
            name_surf = self.header_font.render(names, True, Colors.TEXT_PRIMARY)
            name_surf.set_alpha(alpha)
            name_rect = name_surf.get_rect(
                center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20)
            )
            screen.blit(name_surf, name_rect)

    def _render_combat_over_overlay(self, screen: pygame.Surface) -> None:
        """Render polished combat outcome overlay with stats."""
        # Dim background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        summary = self._get_outcome_summary()

        # Result panel (centered)
        panel_w, panel_h = 420, 300
        panel_x = WINDOW_WIDTH // 2 - panel_w // 2
        panel_y = WINDOW_HEIGHT // 2 - panel_h // 2

        # Panel background
        draw_panel(
            screen, (panel_x, panel_y, panel_w, panel_h),
            alpha=240, bg_color=(12, 16, 32),
            border_color=summary["color"], border_radius=6,
        )

        # Title
        title_surf = self.banner_font.render(
            summary["title"], True, summary["color"]
        )
        title_rect = title_surf.get_rect(
            centerx=WINDOW_WIDTH // 2, top=panel_y + 20
        )
        screen.blit(title_surf, title_rect)

        # Separator
        sep_y = panel_y + 70
        pygame.draw.line(
            screen, Colors.UI_BORDER,
            (panel_x + 20, sep_y), (panel_x + panel_w - 20, sep_y),
        )

        # Stats
        stat_x = panel_x + 30
        stat_y = sep_y + 16
        line_height = 26

        stats = [
            (f"Rounds: {summary['rounds']}", Colors.TEXT_PRIMARY),
            (f"Enemies defeated: {summary['enemies_defeated']}", Colors.TEXT_PRIMARY),
        ]

        if summary["enemies_fled"] > 0:
            stats.append(
                (f"Enemies fled: {summary['enemies_fled']}", Colors.TEXT_SECONDARY)
            )

        if summary["result"] == CombatResult.VICTORY and summary["xp_gained"] > 0:
            stats.append(
                (f"XP gained: +{summary['xp_gained']}", Colors.TEXT_HIGHLIGHT)
            )

        if summary["result"] == CombatResult.VICTORY and summary["loot"]:
            loot_items = ", ".join(
                f"{qty}x {cid.replace('_', ' ').title()}"
                for cid, qty in summary["loot"].items()
            )
            stats.append((f"Loot: {loot_items}", Colors.GREEN))

        if summary["result"] == CombatResult.DEFEAT:
            stats.append(("Cargo lost: 30%", Colors.RED))
            stats.append(("Hull reduced to 25%", Colors.RED))

        if summary["result"] == CombatResult.FLED:
            stats.append(("Escaped with hull intact", Colors.YELLOW))

        if summary["result"] == CombatResult.NEGOTIATED:
            stats.append(("Resolved without bloodshed", Colors.TEXT_HIGHLIGHT))

        for text, color in stats:
            surf = self.info_font.render(text, True, color)
            screen.blit(surf, (stat_x, stat_y))
            stat_y += line_height

        # "Press Continue" hint
        hint_y = panel_y + panel_h - 36
        hint_text = "Press ENTER or click Continue"
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
