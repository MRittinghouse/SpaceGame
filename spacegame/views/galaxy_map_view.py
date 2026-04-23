"""
Galaxy map view.

Visual map of star systems with navigation and travel mechanics.
Features animated background, procedural planet thumbnails, and pulsing highlights.
"""

import math
from typing import Dict, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.easing import ease_in_out_quad
from spacegame.engine.fonts import FONT_DISPLAY, FONT_HEADING, FONT_MD, get_font
from spacegame.engine.particles import SCAN_PULSE, WARP_TRAIL, ParticlePool
from spacegame.engine.procedural import generate_planet
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale
from spacegame.models.encounter import (
    ENCOUNTER_CHANCE_DANGEROUS,
    ENCOUNTER_CHANCE_MODERATE,
    ENCOUNTER_CHANCE_SAFE,
    EncounterRef,
    calculate_encounter_chance,
    check_travel_encounter,
    filter_enemies_for_system,
)
from spacegame.models.faction import ReputationTier
from spacegame.models.player import Player
from spacegame.models.system import StarSystem
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# Standing pip color per reputation tier (None = no indicator)
_STANDING_COLORS: dict[ReputationTier, Optional[tuple[int, int, int]]] = {
    ReputationTier.HOSTILE: (200, 50, 50),
    ReputationTier.UNFRIENDLY: (220, 150, 50),
    ReputationTier.NEUTRAL: None,
    ReputationTier.FRIENDLY: (80, 180, 220),
    ReputationTier.ALLIED: (50, 200, 100),
}


def _get_standing_color(
    tier: ReputationTier,
) -> Optional[tuple[int, int, int]]:
    """Get standing indicator color for a reputation tier.

    Returns None for Neutral (no indicator displayed).
    """
    return _STANDING_COLORS.get(tier)


class GalaxyMapView(BaseView):
    """
    Galaxy map with coordinate-based system visualization.

    Shows all systems as procedural planet thumbnails, player location,
    and allows travel between systems.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        systems: Dict[str, StarSystem],
        active_events: Optional[Dict] = None,
        politics_manager: object = None,
        news_ticker: object = None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.systems = systems
        self.active_events: Dict = active_events or {}
        self.politics_manager = politics_manager
        self.news_ticker = news_ticker

        # Map visualization settings
        # Center the map between the info panel (left) and actions panel (right)
        # with a slight upward shift to account for the cockpit HUD at bottom
        self.map_center_x = WINDOW_WIDTH // 2 + scale_x(30)
        self.map_center_y = WINDOW_HEIGHT // 2 - scale_y(20)
        self.zoom = 2.4  # Spread systems out more to use available space

        # UI state
        self.selected_system: Optional[str] = None
        self.hovered_system: Optional[str] = None
        self.next_state: Optional[GameState] = None

        # PT-M: first-time tip (None unless the player hasn't seen it yet)
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip: Optional[FirstTimeTipOverlay] = None

        # Fonts — role-based
        from spacegame.engine.fonts import FONT_SUBTITLE

        self.system_font = get_font("dialogue", FONT_MD)  # System names on map
        self.info_font = get_font("dialogue", FONT_MD)  # Card body text, info lines
        self.card_name_font = get_font("dialogue", FONT_SUBTITLE)  # System name in info card
        self.title_font = get_font("machine", FONT_HEADING)  # Encounter alerts, overlay titles

        # UI buttons
        self.trade_button: Optional[pygame_gui.elements.UIButton] = None
        self.travel_button: Optional[pygame_gui.elements.UIButton] = None
        self.skills_button: Optional[pygame_gui.elements.UIButton] = None
        self.missions_button: Optional[pygame_gui.elements.UIButton] = None
        self.journal_button: Optional[pygame_gui.elements.UIButton] = None
        self.crew_button: Optional[pygame_gui.elements.UIButton] = None
        self.shipyard_button: Optional[pygame_gui.elements.UIButton] = None
        self.save_button: Optional[pygame_gui.elements.UIButton] = None
        self.menu_button: Optional[pygame_gui.elements.UIButton] = None
        self.info_panel: Optional[pygame_gui.elements.UIPanel] = None

        # Save request flag (consumed by game.py)
        self.save_requested: bool = False

        # Arrival notification (consumed by game.py)
        self.arrival_message: Optional[str] = None

        # Travel confirmation overlay
        self._showing_travel_confirm: bool = False
        self._confirm_button: Optional[pygame_gui.elements.UIButton] = None
        self._cancel_button: Optional[pygame_gui.elements.UIButton] = None
        self._confirm_dest_id: Optional[str] = None

        # Non-hostile encounter ref (consumed by game.py → EncounterView)
        self._pending_encounter_ref: Optional[EncounterRef] = None

        # Journal quick-add overlay
        self.journal: Optional["Journal"] = None
        self._showing_journal_quick_add: bool = False
        self._quick_add_text_entry: Optional[pygame_gui.elements.UITextEntryLine] = None
        self._quick_add_confirm_btn: Optional[pygame_gui.elements.UIButton] = None
        self._quick_add_cancel_btn: Optional[pygame_gui.elements.UIButton] = None
        self._quick_add_tag: str = ""

        # Mission markers
        self.mission_target_systems: set[str] = set()
        self.forced_encounters: list = []

        # Animated background
        self.background = AnimatedBackground("trade_routes", WINDOW_WIDTH, WINDOW_HEIGHT, seed=20)

        # Sprite manager (needed before planet thumbnails)
        self._sprite_mgr = get_sprite_manager()
        self._player_ship_anim: Optional[AnimatedSprite] = None

        # System portrait surfaces (cached)
        self._planet_surfaces: Dict[str, pygame.Surface] = {}
        self._generate_planet_thumbnails()

        # Particles
        self.particles = ParticlePool(200)

        # Animation state
        self._glow_time = 0.0
        self._dash_offset = 0.0

        # Travel animation
        self._travel_animating: bool = False
        self._travel_origin_id: Optional[str] = None
        self._travel_dest_id: Optional[str] = None
        self._travel_progress: float = 0.0
        self._travel_duration: float = 0.0
        self._travel_encounter: Optional[EncounterRef] = None
        self._travel_encounter_stop: float = 1.0
        self._travel_alert_showing: bool = False
        self._deferred_system_id: Optional[str] = None
        self._resume_travel_after_encounter: bool = False
        self._resume_travel_progress: float = 0.0
        self._travel_alert_timer: float = 0.0
        self._pending_encounter: Optional[EncounterRef] = None

    def _generate_planet_thumbnails(self) -> None:
        """Load system portrait sprites or generate procedural fallbacks.

        All portraits are clipped to a circle so they integrate with the
        circular halo system instead of showing rectangular backgrounds.
        """
        for _i, (sys_id, system) in enumerate(self.systems.items()):
            # Try system portrait sprite first
            portrait = self._sprite_mgr.get_system_portrait(sys_id)
            if portrait:
                self._planet_surfaces[sys_id] = self._clip_to_circle(portrait)
            else:
                # Procedural fallback (already circular from generate_planet)
                planet_type = system.type if system.type else "terran"
                surface = generate_planet(12, planet_type, seed=hash(sys_id) % 10000)
                self._planet_surfaces[sys_id] = surface

    @staticmethod
    def _clip_to_circle(surface: pygame.Surface) -> pygame.Surface:
        """Clip a rectangular surface to a circular mask.

        Uses an odd-sized canvas so the circle center is on a true pixel
        (avoids half-pixel rounding that shifts the portrait off-center).
        """
        w, h = surface.get_size()
        # Use odd size so center pixel is unambiguous
        size = max(w, h) | 1  # Ensure odd
        radius = size // 2
        center = size // 2

        # Create circular output
        clipped = pygame.Surface((size, size), pygame.SRCALPHA)
        # Center the portrait on the square canvas
        ox = (size - w) // 2
        oy = (size - h) // 2
        clipped.blit(surface, (ox, oy))

        # Apply circular mask
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (center, center), radius)
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return clipped

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered Galaxy Map")
        self.selected_system = self.player.current_system_id
        self.arrival_message = None
        # Load/refresh player ship sprite (composite if available, else stock)
        self._use_composite_sprite = False
        if self.player and self.player.ship:
            composite = self.player.ship.composite
            if composite and hasattr(composite, "get_surface"):
                self._use_composite_sprite = True
            else:
                self._player_ship_anim = self._sprite_mgr.get_ship_animated(
                    self.player.ship.ship_type.id, category="player", scale=res_scale(1)
                )
        self._create_ui()

        # Resume travel animation after an encounter resolved mid-route
        if self._resume_travel_after_encounter and self._travel_origin_id and self._travel_dest_id:
            self._resume_travel_after_encounter = False
            self._travel_animating = True
            self._travel_progress = self._resume_travel_progress
            self._travel_encounter = None  # No second encounter
            self._travel_encounter_stop = 1.0  # No more stops
            self._travel_alert_showing = False
            # Recalculate remaining duration proportionally
            remaining_frac = 1.0 - self._resume_travel_progress
            origin = self.systems.get(self._travel_origin_id)
            dest = self.systems.get(self._travel_dest_id)
            if origin and dest:
                full_duration = 0.5 + origin.distance_to(dest) / 180.0
                self._travel_duration = full_duration * remaining_frac
            else:
                self._travel_duration = 0.5
            logger.info(f"Resuming travel from {self._resume_travel_progress:.0%} to destination")

        self._maybe_show_tip()

    def _maybe_show_tip(self) -> None:
        """PT-M: first-time galaxy map tip."""
        if self.player is None:
            return
        if self.player.dialogue_flags.get("seen_tip_galaxy_map", False):
            return
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip = FirstTimeTipOverlay(
            title="Galaxy Map",
            body=(
                "Hover any system to see distance and fuel cost. Click to "
                "inspect, click again to travel. Danger level shapes the "
                "encounter risk along your route."
            ),
            on_dismiss=self._mark_galaxy_map_tip_seen,
        )

    def _mark_galaxy_map_tip_seen(self) -> None:
        if self.player is not None:
            self.player.dialogue_flags["seen_tip_galaxy_map"] = True

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        button_width = scale_x(150)
        button_height = scale_y(36)
        button_gap = scale_y(6)
        # Position buttons above the HUD bar with comfortable margin
        from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

        hud_h = scale_y(HUD_BASE_HEIGHT)
        num_buttons = 5
        total_btn_h = num_buttons * button_height + (num_buttons - 1) * button_gap
        card_pad = scale_y(10)
        card_h = total_btn_h + card_pad * 2 + scale_y(24)  # Extra for label
        card_w = button_width + scale_x(20)
        card_x = WINDOW_WIDTH - card_w - scale_x(10)
        card_y = WINDOW_HEIGHT - hud_h - card_h - scale_y(10)

        # Store card rect for rendering
        self._action_card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

        button_x = card_x + (card_w - button_width) // 2
        start_y = card_y + card_pad + scale_y(24)  # Below card label

        self.trade_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y, button_width, button_height),
            text="Trade",
            manager=self.ui_manager,
        )
        self.travel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, start_y + (button_height + button_gap), button_width, button_height
            ),
            text="Travel",
            manager=self.ui_manager,
        )
        self.shipyard_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, start_y + (button_height + button_gap) * 2, button_width, button_height
            ),
            text="Shipyard",
            manager=self.ui_manager,
        )
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, start_y + (button_height + button_gap) * 3, button_width, button_height
            ),
            text="Save",
            manager=self.ui_manager,
        )
        self.menu_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, start_y + (button_height + button_gap) * 4, button_width, button_height
            ),
            text="Main Menu",
            manager=self.ui_manager,
        )

        # Removed buttons — set to None for backward compat with event handlers
        self.skills_button = None
        self.missions_button = None
        self.journal_button = None
        self.crew_button = None

        self._update_button_states()

    def _destroy_ui(self) -> None:
        for btn in [
            self.trade_button,
            self.travel_button,
            self.shipyard_button,
            self.save_button,
            self.menu_button,
            self._confirm_button,
            self._cancel_button,
            self._quick_add_text_entry,
            self._quick_add_confirm_btn,
            self._quick_add_cancel_btn,
        ]:
            if btn:
                btn.kill()
        if self.info_panel:
            self.info_panel.kill()

    def _update_button_states(self) -> None:
        if not self.selected_system:
            if self.trade_button:
                self.trade_button.disable()
            if self.travel_button:
                self.travel_button.disable()
            return

        current_system = self.player.current_system_id
        selected_system = self.selected_system

        if self.trade_button:
            if selected_system == current_system:
                self.trade_button.enable()
            else:
                self.trade_button.disable()

        if self.travel_button:
            if selected_system != current_system:
                fuel_cost = self._calculate_fuel_cost(selected_system)
                if self.player.ship.has_fuel_for_jump(fuel_cost):
                    self.travel_button.enable()
                else:
                    self.travel_button.disable()
            else:
                self.travel_button.disable()

    def _calculate_fuel_cost(self, target_system_id: str) -> int:
        current = self.systems[self.player.current_system_id]
        target = self.systems[target_system_id]
        base_cost = current.fuel_cost_to(target, self.player.ship.effective_fuel_efficiency)
        # Exploration skill: fuel_reduction lowers fuel cost per jump
        fuel_reduction = self.player.progression.get_bonus("fuel_reduction")
        if fuel_reduction > 0:
            base_cost = max(1, int(base_cost * (1 - fuel_reduction)))
        return base_cost

    def _world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        screen_x = int(self.map_center_x + (world_x * self.zoom))
        screen_y = int(self.map_center_y - (world_y * self.zoom))
        return (screen_x, screen_y)

    def _get_system_at_mouse(self, mouse_pos: tuple[int, int]) -> Optional[str]:
        for system_id, system in self.systems.items():
            screen_pos = self._world_to_screen(system.coordinates.x, system.coordinates.y)
            # Use portrait-aware hit rect (80x60 if portrait, 24x24 if procedural)
            planet_surf = self._planet_surfaces.get(system_id)
            if planet_surf:
                hw = planet_surf.get_width() // 2
                hh = planet_surf.get_height() // 2
            else:
                hw = hh = 12
            dx = abs(mouse_pos[0] - screen_pos[0])
            dy = abs(mouse_pos[1] - screen_pos[1])
            if dx <= hw + 4 and dy <= hh + 4:
                return system_id
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        # PT-M: first-time tip consumes events while active
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            if self._first_time_tip.handle_event(event):
                return
        # Block all input during travel animation
        if self._travel_animating:
            return

        # Confirmation overlay: only handle confirm/cancel buttons
        if self._showing_travel_confirm:
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self._confirm_button:
                    self._on_travel_confirm()
                elif event.ui_element == self._cancel_button:
                    self._on_travel_cancel()
            return

        # Journal quick-add overlay: only handle confirm/cancel/escape
        if self._showing_journal_quick_add:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._on_quick_add_cancel()
                elif event.key == pygame.K_RETURN:
                    self._on_quick_add_confirm()
            elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self._quick_add_confirm_btn:
                    self._on_quick_add_confirm()
                elif event.ui_element == self._quick_add_cancel_btn:
                    self._on_quick_add_cancel()
            return

        if event.type == pygame.MOUSEMOTION:
            self.hovered_system = self._get_system_at_mouse(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_system = self._get_system_at_mouse(event.pos)
            if clicked_system:
                self.selected_system = clicked_system
                self._update_button_states()
                # Particle burst on selection
                pos = self._world_to_screen(
                    self.systems[clicked_system].coordinates.x,
                    self.systems[clicked_system].coordinates.y,
                )
                self.particles.emit(pos[0], pos[1], SCAN_PULSE)
                get_audio_manager().play_sfx("nav_select")
                logger.debug(f"Selected system: {clicked_system}")

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.trade_button:
                logger.info("Opening trade interface")
                self.next_state = GameState.TRADING
            elif event.ui_element == self.travel_button:
                self._on_travel_button()
            elif event.ui_element == self.skills_button:
                self.next_state = GameState.CHARACTER
            elif event.ui_element == self.missions_button:
                self.next_state = GameState.MISSION_LOG
            elif event.ui_element == self.journal_button:
                self.next_state = GameState.JOURNAL
            elif event.ui_element == self.crew_button:
                self.next_state = GameState.CREW_ROSTER
            elif event.ui_element == self.shipyard_button:
                self.next_state = GameState.SHIPYARD
            elif event.ui_element == self.save_button:
                self.save_requested = True
            elif event.ui_element == self.menu_button:
                self.next_state = GameState.MAIN_MENU

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j and self.journal:
                self._show_journal_quick_add()
            # Enter/Return: travel to selected system (same as Travel button)
            elif event.key == pygame.K_RETURN and self.selected_system:
                self._on_travel_button()
            # Escape: deselect system
            elif event.key == pygame.K_ESCAPE and self.selected_system:
                self.selected_system = None
                self._update_button_states()

    def _check_forced_encounters(self) -> Optional[EncounterRef]:
        """Check for scripted encounters from active missions."""
        for fe in self.forced_encounters:
            if fe.trigger_flag and self.player.dialogue_flags.get(fe.trigger_flag, False):
                continue  # Already triggered
            if fe.trigger_flag:
                self.player.dialogue_flags[fe.trigger_flag] = True
            return EncounterRef(
                enemy_template_ids=list(fe.enemy_template_ids),
                encounter_seed=hash(fe.trigger_flag) & 0xFFFFFFFF,
                encounter_type=fe.encounter_type,
                encounter_def_id=fe.encounter_def_id,
            )
        return None

    def _execute_travel(self) -> None:
        if not self.selected_system or self.selected_system == self.player.current_system_id:
            return

        origin_id = self.player.current_system_id
        origin_system = self.systems[origin_id]
        dest_system = self.systems[self.selected_system]
        distance = origin_system.distance_to(dest_system)

        fuel_cost = self._calculate_fuel_cost(self.selected_system)

        # Consume fuel and advance day, but DON'T update current_system_id yet.
        # The system ID changes when the travel animation completes (or after
        # an encounter resolves), so missions/dialogues don't trigger mid-flight.
        if not self.player.ship.has_fuel_for_jump(fuel_cost):
            self.message = f"Insufficient fuel. Need {fuel_cost}."
            self.message_timer = 3.0
            return
        self.player.ship.consume_fuel(fuel_cost)
        # Exploration skill: emergency_reserves ensures minimum 1 fuel after any jump
        if self.player.progression.get_bonus("emergency_reserves") > 0:
            if self.player.ship.current_fuel < 1:
                self.player.ship.current_fuel = 1
        self.player.game_day += 1
        self.player.decay_criminal_heat(1)
        self.player.jumps_traveled += 1
        self.player.fuel_consumed += fuel_cost
        self._deferred_system_id = self.selected_system
        success = True
        msg = f"Traveling to {self.selected_system}. Day {self.player.game_day}"

        logger.info(f"Travel result: {msg}")
        if success:
            # Record trade route trip
            if origin_id:
                self.player.trade_route_tracker.record_trip(origin_id, self.selected_system)
            self.player.previous_system_id = origin_id

            from spacegame.config import XP_PER_TRAVEL
            from spacegame.data_loader import get_data_loader

            xp_msgs = self.player.progression.add_xp(XP_PER_TRAVEL)
            for m in xp_msgs:
                logger.info(m)

            # Check for forced encounters from active missions first
            encounter = self._check_forced_encounters()
            if encounter is None:
                # Fall back to random encounter roll
                dl = get_data_loader()
                danger = getattr(dest_system, "danger_level", "moderate")
                faction_id = self.player.get_faction_for_system(self.selected_system) or ""
                enemy_ids = filter_enemies_for_system(dl.enemy_templates, faction_id, danger)

                # Get reputation-based encounter modifiers
                enc_mods: dict = {}
                if self.politics_manager:
                    enc_mods = self.politics_manager.get_encounter_modifier(
                        self.player, self.selected_system
                    )

                encounter = check_travel_encounter(
                    system_danger=danger,
                    enemy_template_ids=enemy_ids,
                    game_day=self.player.game_day,
                    system_id=self.selected_system,
                    distance=distance,
                    player_level=self.player.progression.level,
                    defensive_identity=self.player.ship.ship_type.defensive_identity,
                    encounter_reduction=self.player.progression.get_bonus("encounter_reduction"),
                    anomaly_sense=self.player.progression.get_bonus("anomaly_sense"),
                    anomaly_chance_bonus=self.player.progression.get_bonus("anomaly_chance"),
                )

                # Apply reputation modifiers to encounter
                if encounter and enc_mods:
                    # Scale shakedown demands by reputation multiplier
                    if encounter.shakedown_demand > 0:
                        mult = enc_mods.get("shakedown_multiplier", 1.0)
                        encounter = EncounterRef(
                            enemy_template_ids=encounter.enemy_template_ids,
                            encounter_seed=encounter.encounter_seed,
                            encounter_type=encounter.encounter_type,
                            shakedown_demand=int(encounter.shakedown_demand * mult),
                        )

                    # Safe passage perk: no hostile encounters in faction systems
                    if (
                        self.politics_manager
                        and encounter.encounter_type == "hostile"
                        and self.politics_manager.has_perk(
                            self.player, self.selected_system, "safe_passage"
                        )
                    ):
                        encounter = None  # Alliance escort grants safe passage

                    # Allied/friendly protection: chance to cancel hostile encounter
                    if encounter:
                        protection = enc_mods.get("protection_chance", 0)
                        if protection > 0 and encounter.encounter_type == "hostile":
                            import hashlib

                            seed_str = f"{self.player.game_day}_{self.selected_system}_protection"
                            seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                            if (seed % 100) < protection:
                                encounter = None  # Faction patrol escorts you safely

            # Start travel animation
            get_audio_manager().play_sfx("nav_jump")
            self._travel_animating = True
            self._travel_origin_id = origin_id
            self._travel_dest_id = self.selected_system
            self._travel_progress = 0.0
            self._travel_duration = 0.5 + distance / 180.0
            self._travel_encounter = encounter
            self._travel_alert_showing = False
            self._travel_alert_timer = 0.0

            if encounter:
                # Stop at 40-80% of route (deterministic from seed)
                import random as _rng

                rng = _rng.Random(encounter.encounter_seed)
                self._travel_encounter_stop = 0.4 + rng.random() * 0.4
                logger.info(f"Encounter will trigger at {self._travel_encounter_stop:.0%} of route")
            else:
                self._travel_encounter_stop = 1.0

            self._update_button_states()

    def _on_travel_button(self) -> None:
        """Handle Travel button press: show confirmation overlay."""
        if not self.selected_system or self.selected_system == self.player.current_system_id:
            return
        self._show_travel_confirmation()

    def _show_travel_confirmation(self) -> None:
        """Create and display the travel confirmation overlay."""
        self._showing_travel_confirm = True
        self._confirm_dest_id = self.selected_system

        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2
        btn_width = scale_x(120)
        btn_height = scale_y(36)
        gap = scale_x(20)

        self._confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                center_x - btn_width - gap // 2,
                center_y + scale_y(60),
                btn_width,
                btn_height,
            ),
            text="Confirm",
            manager=self.ui_manager,
        )
        self._cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                center_x + gap // 2,
                center_y + scale_y(60),
                btn_width,
                btn_height,
            ),
            text="Cancel",
            manager=self.ui_manager,
        )

    def _dismiss_travel_confirmation(self) -> None:
        """Destroy confirmation overlay UI elements."""
        if self._confirm_button:
            self._confirm_button.kill()
            self._confirm_button = None
        if self._cancel_button:
            self._cancel_button.kill()
            self._cancel_button = None
        self._showing_travel_confirm = False
        self._confirm_dest_id = None

    def _on_travel_confirm(self) -> None:
        """Player confirmed travel: execute it."""
        self._dismiss_travel_confirmation()
        self._execute_travel()

    def _on_travel_cancel(self) -> None:
        """Player cancelled travel: dismiss overlay."""
        self._dismiss_travel_confirmation()

    # === Journal Quick-Add Overlay ===

    def _show_journal_quick_add(self) -> None:
        """Create and display the journal quick-add overlay."""
        self._showing_journal_quick_add = True
        self._quick_add_tag = ""

        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2

        self._quick_add_text_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(center_x - 190, center_y - 20, 380, 36),
            manager=self.ui_manager,
        )
        from spacegame.models.journal import PLAYER_ENTRY_MAX_LENGTH

        self._quick_add_text_entry.set_text_length_limit(PLAYER_ENTRY_MAX_LENGTH)

        btn_width = scale_x(100)
        btn_height = scale_y(34)
        gap = scale_x(16)
        self._quick_add_confirm_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                center_x - btn_width - gap // 2,
                center_y + scale_y(30),
                btn_width,
                btn_height,
            ),
            text="Save",
            manager=self.ui_manager,
        )
        self._quick_add_cancel_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                center_x + gap // 2,
                center_y + scale_y(30),
                btn_width,
                btn_height,
            ),
            text="Cancel",
            manager=self.ui_manager,
        )

    def _dismiss_journal_quick_add(self) -> None:
        """Destroy quick-add overlay UI elements."""
        if self._quick_add_text_entry:
            self._quick_add_text_entry.kill()
            self._quick_add_text_entry = None
        if self._quick_add_confirm_btn:
            self._quick_add_confirm_btn.kill()
            self._quick_add_confirm_btn = None
        if self._quick_add_cancel_btn:
            self._quick_add_cancel_btn.kill()
            self._quick_add_cancel_btn = None
        self._showing_journal_quick_add = False

    def _on_quick_add_confirm(self) -> None:
        """Save the quick-add entry."""
        text = ""
        if self._quick_add_text_entry:
            text = self._quick_add_text_entry.get_text().strip()
        if text and self.journal:
            self.journal.add_player_entry(
                text=text,
                game_day=self.player.game_day,
                system_id=self.player.current_system_id,
                tag=self._quick_add_tag,
            )
        self._dismiss_journal_quick_add()

    def _on_quick_add_cancel(self) -> None:
        """Cancel the quick-add without saving."""
        self._dismiss_journal_quick_add()

    def _finalize_arrival(self) -> None:
        """Set the player's current_system_id to the travel destination.

        Called when the travel animation completes or when an encounter
        triggers (so the player lands at the destination after the encounter).
        Deferred from _execute_travel() so that missions and dialogues don't
        trigger while the ship is still mid-flight.
        """
        dest_id = getattr(self, "_deferred_system_id", None)
        if dest_id:
            self.player.current_system_id = dest_id
            self.player.systems_visited.add(dest_id)
            self._deferred_system_id = None
            logger.info(f"System ID finalized: {dest_id}")

            # Tier 3.F: record a commodity price snapshot when the player
            # has the price_memory skill active. Skill is a level-1 unlock
            # (bonus_per_level=1.0) — any non-zero bonus enables tracking.
            # Market is constructed on-demand (same pattern as the remote-
            # price preview below) because prices are deterministic per
            # (system, game_day) so a throwaway Market produces identical
            # values to the persistent one.
            try:
                has_memory = self.player.progression.get_bonus("price_memory") > 0
            except Exception:
                has_memory = False
            if has_memory and dest_id in self.systems:
                try:
                    from spacegame.data_loader import get_data_loader
                    from spacegame.models.market import Market

                    dl = get_data_loader()
                    commodities = list(dl.commodities.values())
                    system = self.systems[dest_id]
                    market = Market(system, commodities, self.player.game_day)
                    prices = market.get_all_prices()
                    self.player.price_memory.record(
                        dest_id, prices, self.player.game_day
                    )
                    logger.debug(
                        f"Price memory recorded for {dest_id} at day {self.player.game_day}"
                    )
                except Exception as exc:
                    logger.warning(f"Price memory record failed: {exc}")

            # Exploration skill: jump_hull_restore heals % hull on arrival
            hull_restore_pct = self.player.progression.get_bonus("jump_hull_restore")
            if hull_restore_pct > 0:
                max_hull = self.player.ship.ship_type.combat_hull
                if self.player.ship._computed_stats and self.player.ship._computed_stats.hull > 0:
                    max_hull = self.player.ship._computed_stats.hull
                heal_amount = max(1, int(max_hull * hull_restore_pct))
                healed = self.player.ship.repair_hull(heal_amount)
                if healed > 0:
                    logger.info(f"Field Repairs: restored {healed} hull on arrival")

            # Arrival feedback
            if dest_id in self.systems:
                dest = self.systems[dest_id]
                dx, dy = self._world_to_screen(dest.coordinates.x, dest.coordinates.y)
                self.particles.emit(dx, dy, SCAN_PULSE)
                get_audio_manager().play_sfx("nav_arrive")
                self.arrival_message = f"Arrived at {dest.name}"

    def update(self, dt: float) -> None:
        # PT-M: tick tip overlay; clear once dismissed
        if self._first_time_tip is not None:
            self._first_time_tip.update(dt)
            if self._first_time_tip.dismissed:
                self._first_time_tip = None
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        self._dash_offset += 30 * dt  # scrolling dash offset

        if self._player_ship_anim:
            self._player_ship_anim.update(dt)

        if self._travel_animating:
            self._update_travel_animation(dt)

    def _update_travel_animation(self, dt: float) -> None:
        """Advance travel animation: ship moves, encounters trigger mid-route."""
        if self._travel_alert_showing:
            self._travel_alert_timer -= dt
            if self._travel_alert_timer <= 0:
                self._travel_alert_showing = False
                self._travel_animating = False

                # DON'T finalize arrival yet — we'll resume travel after the
                # encounter resolves and animate the remaining journey.
                # Preserve origin/dest so on_enter can resume.
                self._resume_travel_after_encounter = True
                self._resume_travel_progress = self._travel_encounter_stop

                enc = self._travel_encounter
                if enc and enc.encounter_type == "hostile":
                    # Hostile: transition to combat
                    self._pending_encounter = enc
                    self.next_state = GameState.COMBAT
                    logger.info("Travel encounter: transitioning to combat")
                elif enc:
                    # Non-hostile: route to EncounterView
                    self._pending_encounter_ref = enc
                    self.next_state = GameState.ENCOUNTER
                    logger.info(f"Travel encounter: {enc.encounter_type} — routing to ENCOUNTER")
            return

        # Advance progress
        if self._travel_duration > 0:
            self._travel_progress += dt / self._travel_duration

        # Emit warp trail particles at ship position
        if self._travel_origin_id and self._travel_dest_id:
            origin = self.systems[self._travel_origin_id]
            dest = self.systems[self._travel_dest_id]
            t = min(self._travel_progress, self._travel_encounter_stop)
            eased_t = ease_in_out_quad(t)
            ox, oy = self._world_to_screen(origin.coordinates.x, origin.coordinates.y)
            dx, dy = self._world_to_screen(dest.coordinates.x, dest.coordinates.y)
            ship_x = ox + (dx - ox) * eased_t
            ship_y = oy + (dy - oy) * eased_t
            self.particles.emit(ship_x, ship_y, WARP_TRAIL)

        # Check if encounter triggers mid-route
        if (
            self._travel_encounter
            and self._travel_progress >= self._travel_encounter_stop
            and not self._travel_alert_showing
        ):
            self._travel_alert_showing = True
            self._travel_alert_timer = 1.2
            self._travel_progress = self._travel_encounter_stop
            # Burst particles at encounter point
            self.particles.emit(ship_x, ship_y, SCAN_PULSE)
            enc_type = (
                self._travel_encounter.encounter_type if self._travel_encounter else "hostile"
            )
            if enc_type == "hostile":
                logger.info("Travel encounter: HOSTILE CONTACT!")
            else:
                logger.info(f"Travel encounter: {enc_type.upper().replace('_', ' ')} DETECTED!")
            return

        # No encounter — animation complete
        if self._travel_progress >= 1.0:
            self._travel_animating = False

            # Finalize arrival: update current_system_id now that animation is done
            self._finalize_arrival()

            self._travel_origin_id = None
            self._travel_dest_id = None
            self.next_state = GameState.TRADING
            logger.info("Travel complete: landing at destination")

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)

        # Title + compact status line (credits/fuel/ship now in HUD bar)
        title = self.title_font.render("GALAXY MAP", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (20, 20))

        status_y = scale_y(58)
        day_text = f"Day {self.player.game_day}  |  Lv {self.player.progression.level}"
        day_surf = self.info_font.render(day_text, True, Colors.TEXT)
        screen.blit(day_surf, (20, status_y))

        # Criminal heat indicator (only shown when > 0)
        from spacegame.config import get_heat_display_color

        heat_color = get_heat_display_color(self.player.criminal_heat)
        if heat_color:
            heat_surf = self.info_font.render(
                f"Heat: {self.player.criminal_heat}", True, heat_color
            )
            screen.blit(heat_surf, (20, status_y + scale_y(22)))

        # Draw travel route line (only to selected or hovered destination)
        current_system = self.systems[self.player.current_system_id]
        current_pos = self._world_to_screen(
            current_system.coordinates.x, current_system.coordinates.y
        )

        route_target_id = self.selected_system or self.hovered_system
        if route_target_id and route_target_id != self.player.current_system_id:
            target = self.systems[route_target_id]
            target_pos = self._world_to_screen(target.coordinates.x, target.coordinates.y)
            route_color = self._get_danger_route_color(target.danger_level)
            self._draw_dashed_line(screen, route_color, current_pos, target_pos)

            # Route preview: distance + fuel cost midway along the line
            distance = current_system.distance_to(target)
            fuel_cost = self._calculate_fuel_cost(route_target_id)
            mid_x = (current_pos[0] + target_pos[0]) // 2
            mid_y = (current_pos[1] + target_pos[1]) // 2
            route_label = f"{distance:.0f}u  |  {fuel_cost} fuel"
            route_surf = self.info_font.render(route_label, True, route_color)
            # Dark pill behind text for readability against starfield
            pill_w = route_surf.get_width() + 12
            pill_h = route_surf.get_height() + 6
            pill_bg = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
            pill_bg.fill((8, 10, 20, 200))
            screen.blit(pill_bg, (mid_x - pill_w // 2, mid_y - pill_h // 2 - 10))
            screen.blit(
                route_surf,
                (mid_x - route_surf.get_width() // 2, mid_y - route_surf.get_height() // 2 - 10),
            )

        # Highlight active travel route
        if self._travel_animating and self._travel_origin_id and self._travel_dest_id:
            origin = self.systems[self._travel_origin_id]
            dest = self.systems[self._travel_dest_id]
            o_pos = self._world_to_screen(origin.coordinates.x, origin.coordinates.y)
            d_pos = self._world_to_screen(dest.coordinates.x, dest.coordinates.y)
            pygame.draw.line(screen, Colors.TEXT_HIGHLIGHT, o_pos, d_pos, 2)

        # Draw systems
        for system_id, system in self.systems.items():
            screen_x, screen_y = self._world_to_screen(system.coordinates.x, system.coordinates.y)

            # Determine portrait extents for indicator placement
            planet_surf = self._planet_surfaces.get(system_id)
            if planet_surf:
                pw, ph = planet_surf.get_size()
                half_w = pw // 2
                half_h = ph // 2
            else:
                half_w = half_h = 12

            # Soft halo radius based on portrait size
            halo_r = max(half_w, half_h) + 6

            # Pulsing glow ring on current system (circular)
            if system_id == self.player.current_system_id:
                glow_alpha = int(120 + 80 * math.sin(self._glow_time * 3))
                glow_r = halo_r + 4
                glow_d = glow_r * 2 + 2
                glow_surf = pygame.Surface((glow_d, glow_d), pygame.SRCALPHA)
                pygame.draw.circle(
                    glow_surf,
                    (*Colors.TEXT_HIGHLIGHT, glow_alpha),
                    (glow_r + 1, glow_r + 1),
                    glow_r,
                    3,
                )
                screen.blit(glow_surf, (screen_x - glow_r - 1, screen_y - glow_r - 1))

            # Selected system highlight (circular ring)
            if system_id == self.selected_system:
                sel_r = halo_r + 2
                sel_d = sel_r * 2 + 2
                sel_surf = pygame.Surface((sel_d, sel_d), pygame.SRCALPHA)
                pygame.draw.circle(
                    sel_surf,
                    (*Colors.TEXT, 180),
                    (sel_r + 1, sel_r + 1),
                    sel_r,
                    2,
                )
                screen.blit(sel_surf, (screen_x - sel_r - 1, screen_y - sel_r - 1))

            # Hovered system highlight (subtle outer glow)
            if system_id == self.hovered_system:
                hov_r = halo_r + 1
                hov_d = hov_r * 2 + 2
                hov_surf = pygame.Surface((hov_d, hov_d), pygame.SRCALPHA)
                pygame.draw.circle(
                    hov_surf,
                    (255, 255, 255, 60),
                    (hov_r + 1, hov_r + 1),
                    hov_r,
                    1,
                )
                screen.blit(hov_surf, (screen_x - hov_r - 1, screen_y - hov_r - 1))

            # Draw system portrait or procedural planet thumbnail
            if planet_surf:
                screen.blit(planet_surf, (screen_x - half_w, screen_y - half_h))
            else:
                # Fallback colored circle
                pygame.draw.circle(screen, (150, 150, 150), (screen_x, screen_y), 12)

            # Faction-colored halo (subtle ring, not a filled glow)
            faction_color = self._get_faction_color(system.faction)
            if faction_color:
                fc_r = halo_r
                fc_d = fc_r * 2 + 2
                fc_surf = pygame.Surface((fc_d, fc_d), pygame.SRCALPHA)
                # Thin outer ring only — no filled glow (cleaner, less garish)
                pygame.draw.circle(
                    fc_surf,
                    (*faction_color, 70),
                    (fc_r + 1, fc_r + 1),
                    fc_r,
                    2,
                )
                screen.blit(fc_surf, (screen_x - fc_r - 1, screen_y - fc_r - 1))

            # Danger level indicator dot (top-right of portrait)
            danger_dot_color = self._get_danger_dot_color(system.danger_level)
            if danger_dot_color:
                dot_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(dot_surf, danger_dot_color, (5, 5), 4)
                screen.blit(dot_surf, (screen_x + half_w - 2, screen_y - half_h - 2))

            # Reputation standing indicator (colored pip, bottom-left)
            faction_id = self.player.get_faction_for_system(system_id)
            if faction_id:
                tier = self.player.get_reputation_tier(faction_id)
                standing_color = _get_standing_color(tier)
                if standing_color:
                    pip_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                    pygame.draw.circle(pip_surf, (*standing_color, 200), (5, 5), 4)
                    screen.blit(pip_surf, (screen_x - half_w - 4, screen_y + half_h - 4))

            # Event indicator (pulsing warning dot)
            active_event = self.active_events.get(system_id)
            if active_event and active_event.is_active(self.player.game_day):
                indicator_alpha = int(150 + 100 * math.sin(self._glow_time * 5))
                indicator_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                pygame.draw.circle(
                    indicator_surf, (*Colors.YELLOW, min(255, indicator_alpha)), (8, 8), 6
                )
                pygame.draw.circle(
                    indicator_surf, (*Colors.RED, min(255, indicator_alpha // 2)), (8, 8), 6, 2
                )
                screen.blit(indicator_surf, (screen_x + half_w - 2, screen_y - half_h - 12))

            # Political event indicator (pulsing shield icon — cyan/purple)
            if self.politics_manager and faction_id:
                for pe in self.politics_manager.get_active_events():
                    if pe.faction_a_id == faction_id or pe.faction_b_id == faction_id:
                        pe_alpha = int(120 + 80 * math.sin(self._glow_time * 3.5))
                        pe_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
                        # Small diamond shape in cyan
                        pe_points = [(7, 1), (13, 7), (7, 13), (1, 7)]
                        pygame.draw.polygon(pe_surf, (100, 200, 255, min(255, pe_alpha)), pe_points)
                        pygame.draw.polygon(
                            pe_surf, (180, 140, 255, min(255, pe_alpha // 2)), pe_points, 1
                        )
                        screen.blit(pe_surf, (screen_x - half_w - 8, screen_y - half_h - 8))
                        break  # One indicator per system

            # Mission destination marker (pulsing diamond, larger + outer glow)
            if system_id in self.mission_target_systems:
                m_alpha = int(160 + 90 * math.sin(self._glow_time * 4))
                # Outer glow (diffuse)
                glow_size = 24
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                glow_points = [
                    (glow_size // 2, 2),
                    (glow_size - 2, glow_size // 2),
                    (glow_size // 2, glow_size - 2),
                    (2, glow_size // 2),
                ]
                pygame.draw.polygon(
                    glow_surf,
                    (*Colors.TEXT_HIGHLIGHT, min(255, m_alpha // 3)),
                    glow_points,
                )
                screen.blit(
                    glow_surf,
                    (screen_x - half_w - glow_size + 2, screen_y - glow_size // 2),
                )
                # Inner diamond (solid)
                marker_size = 16
                marker_surf = pygame.Surface((marker_size, marker_size), pygame.SRCALPHA)
                points = [
                    (marker_size // 2, 1),
                    (marker_size - 1, marker_size // 2),
                    (marker_size // 2, marker_size - 1),
                    (1, marker_size // 2),
                ]
                pygame.draw.polygon(
                    marker_surf,
                    (*Colors.TEXT_HIGHLIGHT, min(255, m_alpha)),
                    points,
                )
                screen.blit(
                    marker_surf,
                    (screen_x - half_w - marker_size + 2, screen_y - marker_size // 2),
                )

            # System name — rendered after all systems to allow overlap avoidance
            # (deferred to a second pass below)

        # System names — second pass with overlap avoidance
        name_rects: list[pygame.Rect] = []
        for system_id, system in self.systems.items():
            screen_x, screen_y = self._world_to_screen(system.coordinates.x, system.coordinates.y)
            planet_surf = self._planet_surfaces.get(system_id)
            half_h = (planet_surf.get_height() // 2) if planet_surf else 12

            # Brighter for selected, normal for visited, dimmer for unvisited
            if system_id == self.selected_system:
                name_color = Colors.TEXT_HIGHLIGHT
            elif system_id in self.player.systems_visited:
                name_color = Colors.TEXT
            else:
                name_color = Colors.TEXT_SECONDARY
            name_surf = self.system_font.render(system.name, True, name_color)
            shadow = self.system_font.render(system.name, True, (0, 0, 0))

            # Default position: below portrait
            name_rect = name_surf.get_rect(center=(screen_x, screen_y + half_h + 6))

            # Nudge if overlapping any previously placed name
            for existing in name_rects:
                if name_rect.colliderect(existing):
                    # Try above the portrait instead
                    alt_rect = name_surf.get_rect(center=(screen_x, screen_y - half_h - 8))
                    if not any(alt_rect.colliderect(e) for e in name_rects):
                        name_rect = alt_rect
                        break
                    # Try offset right
                    alt_rect = name_surf.get_rect(midleft=(screen_x + half_h + 8, screen_y))
                    if not any(alt_rect.colliderect(e) for e in name_rects):
                        name_rect = alt_rect
                        break

            name_rects.append(name_rect)
            screen.blit(shadow, (name_rect.x + 1, name_rect.y + 1))
            screen.blit(name_surf, name_rect)

        # Ship icon
        self._draw_ship(screen)

        # Particles on top of systems
        self.particles.render(screen)

        # Encounter alert overlay
        if self._travel_alert_showing:
            self._draw_encounter_alert(screen)

        # Travel confirmation overlay
        if self._showing_travel_confirm:
            self._draw_travel_confirmation(screen)

        # Journal quick-add overlay
        if self._showing_journal_quick_add:
            self._draw_journal_quick_add(screen)

        # Action card background behind buttons
        self._draw_action_card(screen)

        # Selected system info panel
        if self.selected_system:
            self._draw_system_info(screen, self.selected_system)

        # PT-K: lightweight hover tooltip — fuel cost visible before commit.
        # Only renders when hovering over a system that's NOT the current one
        # (no point telling the player "0 fuel to stay where you are") and
        # NOT the one already selected (the full info panel covers that).
        if (
            self.hovered_system
            and self.hovered_system != self.player.current_system_id
            and self.hovered_system != self.selected_system
        ):
            self._draw_hover_tooltip(screen, self.hovered_system)

        # News ticker at bottom
        self._draw_news_ticker(screen)

    def _draw_hover_tooltip(self, screen: pygame.Surface, system_id: str) -> None:
        """Render a compact fuel/distance tooltip next to the hovered system."""
        system = self.systems.get(system_id)
        if system is None:
            return
        current = self.systems.get(self.player.current_system_id)
        if current is None:
            return
        distance = current.distance_to(system)
        fuel_cost = self._calculate_fuel_cost(system_id)
        has_fuel = self.player.ship.has_fuel_for_jump(fuel_cost)

        # Anchor next to the system's on-screen position
        sx, sy = self._world_to_screen(system.coordinates.x, system.coordinates.y)
        pad_x = scale_x(6)
        pad_y = scale_y(4)
        name_surf = self.info_font.render(system.name, True, Colors.TEXT_HIGHLIGHT)
        dist_surf = self.info_font.render(f"{distance:.0f}u", True, Colors.TEXT_SECONDARY)
        fuel_color = Colors.TEXT if has_fuel else Colors.RED
        fuel_surf = self.info_font.render(f"{fuel_cost} fuel", True, fuel_color)

        tip_w = max(name_surf.get_width(), dist_surf.get_width(), fuel_surf.get_width()) + pad_x * 2
        tip_h = name_surf.get_height() + dist_surf.get_height() + fuel_surf.get_height() + pad_y * 2

        # Offset to the right of the system unless that clips the right edge
        tx = sx + scale_x(16)
        if tx + tip_w > WINDOW_WIDTH - scale_x(4):
            tx = sx - tip_w - scale_x(16)
        ty = sy - tip_h // 2

        # Background
        bg = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 200))
        screen.blit(bg, (tx, ty))
        pygame.draw.rect(screen, Colors.UI_BORDER, (tx, ty, tip_w, tip_h), 1)

        screen.blit(name_surf, (tx + pad_x, ty + pad_y))
        screen.blit(dist_surf, (tx + pad_x, ty + pad_y + name_surf.get_height()))
        screen.blit(
            fuel_surf,
            (tx + pad_x, ty + pad_y + name_surf.get_height() + dist_surf.get_height()),
        )

    def _draw_news_ticker(self, screen: pygame.Surface) -> None:
        """Render scrolling news ticker at the bottom of the map."""
        if not self.news_ticker:
            return
        headlines = self.news_ticker.get_headlines(count=3)
        if not headlines:
            return

        ticker_y = WINDOW_HEIGHT - scale_y(28)
        separator = "  \u2022  "  # bullet separator
        ticker_text = separator.join(headlines)
        surf = self.info_font.render(ticker_text, True, Colors.TEXT_SECONDARY)
        surf.set_alpha(180)
        # Center horizontally, clamp to screen width
        x = max(10, WINDOW_WIDTH // 2 - surf.get_width() // 2)
        screen.blit(surf, (x, ticker_y))

    def _get_faction_color(self, faction_name: str) -> Optional[tuple]:
        """Look up faction color by display name."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        for faction in dl.get_all_factions():
            if faction.name == faction_name:
                return faction.color
        return None

    def _draw_dashed_line(
        self,
        screen: pygame.Surface,
        color: tuple,
        start: tuple,
        end: tuple,
        dash_len: int = 8,
        gap_len: int = 6,
    ) -> None:
        """Draw animated dashed line with scrolling offset."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = max(1, math.sqrt(dx * dx + dy * dy))
        nx, ny = dx / dist, dy / dist

        total = dash_len + gap_len
        offset = self._dash_offset % total
        pos = -offset

        while pos < dist:
            seg_start = max(0, pos)
            seg_end = min(dist, pos + dash_len)
            if seg_end > seg_start:
                sx = int(start[0] + nx * seg_start)
                sy = int(start[1] + ny * seg_start)
                ex = int(start[0] + nx * seg_end)
                ey = int(start[1] + ny * seg_end)
                pygame.draw.line(screen, color, (sx, sy), (ex, ey), 1)
            pos += total

    def _get_ship_position(self) -> tuple[float, float, float]:
        """Get current ship screen position and travel angle.

        Returns:
            (screen_x, screen_y, angle_degrees) where angle points in travel direction.
        """
        if self._travel_animating and self._travel_origin_id and self._travel_dest_id:
            origin = self.systems[self._travel_origin_id]
            dest = self.systems[self._travel_dest_id]
            t = min(self._travel_progress, self._travel_encounter_stop)
            eased_t = ease_in_out_quad(t)
            ox, oy = self._world_to_screen(origin.coordinates.x, origin.coordinates.y)
            dx, dy = self._world_to_screen(dest.coordinates.x, dest.coordinates.y)
            ship_x = ox + (dx - ox) * eased_t
            ship_y = oy + (dy - oy) * eased_t
            angle = math.degrees(math.atan2(-(dy - oy), dx - ox))
            return ship_x, ship_y, angle

        # Idle: ship at current system
        current = self.systems[self.player.current_system_id]
        sx, sy = self._world_to_screen(current.coordinates.x, current.coordinates.y)
        return float(sx), float(sy), 0.0

    def _draw_ship(self, screen: pygame.Surface) -> None:
        """Draw ship sprite (or fallback chevron) at current position."""
        ship_x, ship_y, angle = self._get_ship_position()

        # Try composite first (player-built ship), then stock sprite
        player_ship_surface = None
        if self._use_composite_sprite and self.player and self.player.ship.composite:
            player_ship_surface = self.player.ship.composite.get_surface(scale=res_scale(1))
            self.player.ship.composite.update(0.016)
        elif self._player_ship_anim:
            player_ship_surface = self._player_ship_anim.get_surface()
        if player_ship_surface is not None:
            # Rotate sprite to match travel direction (pygame rotates CCW)
            rotated = pygame.transform.rotate(player_ship_surface, angle)
            ship_w = rotated.get_width()
            ship_h = rotated.get_height()
            # Offset above system node when idle, centered when travelling
            y_offset = -16 if not self._travel_animating else 0
            sprite_x = int(ship_x - ship_w // 2)
            sprite_y = int(ship_y - ship_h // 2 + y_offset)

            # Subtle glow ring behind ship (not filled — avoids obscuring planet)
            glow_radius = max(ship_w, ship_h) // 2 + 2
            glow_size = glow_radius * 2 + 2
            glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surf,
                (*Colors.TEXT_HIGHLIGHT, 40),
                (glow_radius + 1, glow_radius + 1),
                glow_radius,
                2,
            )
            screen.blit(
                glow_surf,
                (int(ship_x) - glow_radius - 1, int(ship_y + y_offset) - glow_radius - 1),
            )

            screen.blit(rotated, (sprite_x, sprite_y))
            return

        # Fallback: chevron
        rad = math.radians(angle)
        size = 8
        tip_x = ship_x + math.cos(rad) * size
        tip_y = ship_y - math.sin(rad) * size
        back_angle = math.pi * 0.75
        bl_x = ship_x + math.cos(rad + back_angle) * size * 0.7
        bl_y = ship_y - math.sin(rad + back_angle) * size * 0.7
        br_x = ship_x + math.cos(rad - back_angle) * size * 0.7
        br_y = ship_y - math.sin(rad - back_angle) * size * 0.7

        points = [(tip_x, tip_y), (bl_x, bl_y), (br_x, br_y)]

        # Glow behind ship
        glow_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*Colors.TEXT_HIGHLIGHT, 60), (12, 12), 10)
        screen.blit(glow_surf, (int(ship_x) - 12, int(ship_y) - 12))

        # Ship body
        pygame.draw.polygon(screen, Colors.TEXT_HIGHLIGHT, points)
        pygame.draw.polygon(screen, (255, 255, 255), points, 1)

    def _draw_travel_confirmation(self, screen: pygame.Surface) -> None:
        """Draw travel confirmation overlay with destination info and risk."""
        if not self._confirm_dest_id:
            return

        dest = self.systems[self._confirm_dest_id]
        origin = self.systems[self.player.current_system_id]
        distance = origin.distance_to(dest)
        fuel_cost = self._calculate_fuel_cost(self._confirm_dest_id)

        # Encounter risk % — use canonical constants from encounter.py
        base_chance = {
            "safe": ENCOUNTER_CHANCE_SAFE,
            "moderate": ENCOUNTER_CHANCE_MODERATE,
            "dangerous": ENCOUNTER_CHANCE_DANGEROUS,
        }.get(dest.danger_level, ENCOUNTER_CHANCE_MODERATE)
        risk_pct = calculate_encounter_chance(base_chance, distance)

        # Dim overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = scale_x(320), scale_y(200)
        px = (WINDOW_WIDTH - panel_w) // 2
        py = (WINDOW_HEIGHT - panel_h) // 2 - scale_y(20)
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 35, 220))
        screen.blit(panel_surf, (px, py))
        pygame.draw.rect(screen, Colors.UI_BORDER, (px, py, panel_w, panel_h), 1)

        # Title
        title = self.title_font.render("Confirm Travel", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (px + (panel_w - title.get_width()) // 2, py + scale_y(12)))

        # Info lines
        info_y = py + scale_y(50)
        line_h = scale_y(24)
        lines = [
            (f"Destination: {dest.name}", Colors.TEXT),
            (f"Distance: {distance:.0f} u", Colors.TEXT),
            (f"Fuel Cost: {fuel_cost}", Colors.TEXT),
        ]
        # Risk line — red if > 20%
        risk_color = Colors.RED if risk_pct > 20 else Colors.TEXT
        lines.append((f"Encounter Risk: {risk_pct:.0f}%", risk_color))

        for text, color in lines:
            surf = self.info_font.render(text, True, color)
            screen.blit(surf, (px + 20, info_y))
            info_y += line_h

    def _draw_encounter_alert(self, screen: pygame.Surface) -> None:
        """Draw pulsing alert when encounter triggers mid-route."""
        enc = self._travel_encounter
        enc_type = enc.encounter_type if enc else "hostile"

        # Dim overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        # Pulsing text
        pulse = 0.5 + 0.5 * math.sin(self._glow_time * 8)
        alpha = int(180 + 75 * pulse)
        alert_font = get_font("machine", FONT_DISPLAY)

        # Type-specific alert styling
        _ALERT_STYLES: dict[str, tuple[str, tuple[int, int, int], tuple[int, int, int, int]]] = {
            "hostile": ("HOSTILE CONTACT", (220, 60, 60), (40, 0, 0, 180)),
            "distress_signal": ("DISTRESS SIGNAL", (220, 200, 60), (40, 30, 0, 180)),
            "shakedown": ("SHAKEDOWN", (255, 160, 60), (40, 20, 0, 180)),
            "derelict": ("DERELICT DETECTED", (180, 140, 80), (30, 20, 0, 180)),
            "merchant": ("MERCHANT HAIL", (100, 150, 220), (0, 15, 40, 180)),
            "debris": ("DEBRIS FIELD", (160, 160, 160), (20, 20, 20, 180)),
            "anomaly": ("ANOMALY DETECTED", (180, 100, 220), (25, 0, 35, 180)),
        }
        # Legendary boss encounters get a unique flash
        enc_id = getattr(enc, "encounter_def_id", "") or getattr(enc, "id", "") or ""
        if enc_id.startswith("legendary_"):
            label = "LEGENDARY THREAT"
            color = (255, 200, 50)
            bg_base = (50, 30, 0, 200)
        else:
            label, color, bg_base = _ALERT_STYLES.get(
                enc_type, ("ENCOUNTER", (200, 200, 200), (20, 20, 20, 180))
            )
        text_surf = alert_font.render(label, True, color)
        bg_color = (bg_base[0], bg_base[1], bg_base[2], min(255, alpha))

        # Center on screen
        text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))

        # Background behind text
        bg_rect = text_rect.inflate(40, 20)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill(bg_color)
        screen.blit(bg_surf, bg_rect.topleft)

        # Text with alpha
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(text_surf, (0, 0))
        alpha_surf.set_alpha(min(255, alpha))
        screen.blit(alpha_surf, text_rect)

    def _draw_journal_quick_add(self, screen: pygame.Surface) -> None:
        """Draw journal quick-add overlay."""
        # Dim overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = scale_x(420), scale_y(140)
        px = (WINDOW_WIDTH - panel_w) // 2
        py = (WINDOW_HEIGHT - panel_h) // 2 - scale_y(20)
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 35, 220))
        screen.blit(panel_surf, (px, py))
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, (px, py, panel_w, panel_h), 1)

        # Title
        title = self.title_font.render("Quick Note", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (px + (panel_w - title.get_width()) // 2, py + 10))

        # Hint
        hint = self.info_font.render(
            "Press Enter to save, Escape to cancel", True, Colors.TEXT_SECONDARY
        )
        screen.blit(hint, (px + (panel_w - hint.get_width()) // 2, py + panel_h - 24))

    def _draw_action_card(self, screen: pygame.Surface) -> None:
        """Draw the action card background behind the side buttons."""
        if not hasattr(self, "_action_card_rect"):
            return
        rect = self._action_card_rect

        # Semi-transparent panel
        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        card_surf.fill((15, 18, 35, 190))
        screen.blit(card_surf, rect.topleft)

        # Border with subtle glow
        pygame.draw.rect(screen, Colors.UI_BORDER, rect, 1)
        inner = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, rect.height - 2)
        glow = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*Colors.TEXT_HIGHLIGHT, 25), glow.get_rect(), 1)
        screen.blit(glow, inner.topleft)

        # Label
        label = self.info_font.render("ACTIONS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(label, (rect.x + (rect.width - label.get_width()) // 2, rect.y + scale_y(6)))

    def _draw_system_info(self, screen: pygame.Surface, system_id: str) -> None:
        # Market price display is skill-gated — see the Market prices block
        # below. remote_prices shows live prices; price_memory (Tier 3.F)
        # shows last-known prices with "days ago" freshness on visited
        # systems.
        system = self.systems[system_id]

        panel_x = scale_x(15)
        panel_y = scale_y(100)
        panel_width = scale_x(340)
        line_height = scale_y(22)
        pad = 10
        header_height = scale_y(35)

        # --- Collect all content lines as (text, color) tuples ---

        # system_intel skill gates info for unvisited systems:
        #   Lv0: only type shown. Lv1+: danger. Lv2+: faction/economy.
        #   Visited systems always show everything.
        is_visited = system_id in self.player.systems_visited
        intel_level = self.player.progression.get_bonus("system_intel")

        faction_id = self.player.get_faction_for_system(system_id)

        info_lines: list[tuple[str, tuple[int, int, int]]] = [
            (f"Type: {system.type.replace('_', ' ').title()}", Colors.TEXT),
        ]

        # Faction and reputation — gated behind system_intel >= 2 for unvisited
        show_faction = is_visited or intel_level >= 2.0
        if show_faction:
            if faction_id:
                tier = self.player.get_reputation_tier(faction_id)
                rep_val = self.player.get_reputation(faction_id)
                sign = "+" if rep_val >= 0 else ""
                info_lines.append((f"Faction: {system.faction}", Colors.TEXT))
                info_lines.append(
                    (f"  Reputation: {tier.value} ({sign}{rep_val})", Colors.TEXT_SECONDARY)
                )
            else:
                info_lines.append((f"Faction: {system.faction}", Colors.TEXT))
        else:
            info_lines.append(("Faction: ???", Colors.TEXT_SECONDARY))

        # Danger — gated behind system_intel >= 1 for unvisited
        show_danger = is_visited or intel_level >= 1.0
        if show_danger:
            info_lines.append((f"Danger: {system.danger_level.title()}", Colors.TEXT))
        else:
            info_lines.append(("Danger: ???", Colors.TEXT_SECONDARY))
        info_lines.append(("", Colors.TEXT))

        if system_id != self.player.current_system_id:
            current = self.systems[self.player.current_system_id]
            distance = current.distance_to(system)
            fuel_cost = self._calculate_fuel_cost(system_id)

            from spacegame.models.encounter import (
                ENCOUNTER_CHANCE_DANGEROUS,
                ENCOUNTER_CHANCE_MODERATE,
                ENCOUNTER_CHANCE_SAFE,
            )

            base_chance = {
                "safe": ENCOUNTER_CHANCE_SAFE,
                "moderate": ENCOUNTER_CHANCE_MODERATE,
                "dangerous": ENCOUNTER_CHANCE_DANGEROUS,
            }.get(system.danger_level, 0)
            enc_chance = calculate_encounter_chance(base_chance, distance)
            risk_text = (
                f"Encounter Risk: {enc_chance:.0f}%" if enc_chance > 0 else "Encounter Risk: None"
            )

            info_lines.extend(
                [
                    (f"Distance: {distance:.1f} units", Colors.TEXT),
                    (f"Fuel Cost: {fuel_cost} units", Colors.TEXT),
                    (risk_text, Colors.TEXT),
                ]
            )

        # Active event info
        active_event = self.active_events.get(system_id)
        if active_event and active_event.is_active(self.player.game_day):
            from spacegame.data_loader import get_data_loader

            dl = get_data_loader()
            commodity = dl.commodities.get(active_event.commodity_id)
            commodity_name = commodity.name if commodity else active_event.commodity_id
            days_left = active_event.days_remaining(self.player.game_day)
            info_lines.append(("", Colors.TEXT))
            info_lines.append((f"Event: {active_event.event_type.value.upper()}", Colors.YELLOW))
            info_lines.append((f"  {commodity_name} ({days_left}d)", Colors.YELLOW))

        # Political event info
        if self.politics_manager and faction_id:
            for pe in self.politics_manager.get_active_events():
                if pe.faction_a_id == faction_id or pe.faction_b_id == faction_id:
                    days_left = pe.days_remaining(self.player.game_day)
                    info_lines.append(("", Colors.TEXT))
                    info_lines.append(
                        (
                            f"Political: {pe.event_type.value.replace('_', ' ').title()}",
                            Colors.TEXT,
                        )
                    )
                    info_lines.append((f"  {pe.description[:40]}... ({days_left}d)", Colors.TEXT))
                    break

        # Market prices on the map — priority:
        #   1. remote_prices skill: live current prices (richest info)
        #   2. price_memory skill + prior visit: remembered prices with age
        #   3. neither: no price section
        remote_price_lines: list[tuple[str, tuple[int, int, int]]] = []
        if system_id != self.player.current_system_id and hasattr(system, "economy") and system.economy:
            if self.player.progression.get_bonus("remote_prices") > 0:
                remote_price_lines = self._get_remote_price_lines(system)
            elif (
                self.player.progression.get_bonus("price_memory") > 0
                and self.player.price_memory.has_memory(system_id)
            ):
                # Tier 3.F: fall back to the player's last-known snapshot.
                remote_price_lines = self._get_price_memory_lines(system)

        # --- Calculate total panel height to fit ALL content ---
        panel_height = pad + header_height + len(info_lines) * line_height
        if remote_price_lines:
            panel_height += 4 + len(remote_price_lines) * line_height
        panel_height += pad  # bottom padding

        # --- Draw panel background sized to content ---
        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 35, 200))
        screen.blit(panel_surf, (panel_x, panel_y))

        # Panel border with faction accent
        from spacegame.views.layout import get_faction_accent

        border_accent = get_faction_accent(faction_id) if faction_id else Colors.UI_BORDER
        pygame.draw.rect(
            screen,
            Colors.UI_BORDER,
            (panel_x, panel_y, panel_width, panel_height),
            1,
        )
        # Top accent line in faction color
        pygame.draw.line(
            screen,
            border_accent,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y),
            2,
        )

        # --- Render content ---
        y_offset = panel_y + pad

        # System name header (larger, readable font)
        name_surf = self.card_name_font.render(system.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (panel_x + pad, y_offset))
        y_offset += header_height

        # Faction emblem on the faction line (index 1 in info_lines)
        faction_emblem = (
            self._sprite_mgr.get_faction_emblem(faction_id, scale=res_scale(1))
            if faction_id
            else None
        )

        for i, (line, color) in enumerate(info_lines):
            lx = panel_x + pad
            if i == 1 and faction_emblem:
                screen.blit(faction_emblem, (lx, y_offset))
                lx += faction_emblem.get_width() + 4
            surf = self.info_font.render(line, True, color)
            screen.blit(surf, (lx, y_offset))
            y_offset += line_height

        # Remote prices
        if remote_price_lines:
            y_offset += 4
            for text, color in remote_price_lines:
                surf = self.info_font.render(text, True, color)
                screen.blit(surf, (panel_x + pad, y_offset))
                y_offset += line_height

    def _get_price_memory_lines(
        self, system: "StarSystem"
    ) -> list[tuple[str, tuple[int, int, int]]]:
        """Build last-known-prices lines from the player's PriceMemory.

        Tier 3.F: shown when the ``price_memory`` skill is active and the
        player has a recorded snapshot for the system. Distinct from
        ``_get_remote_price_lines`` (which shows live current prices when
        ``remote_prices`` is active). Memory shows AGE per commodity so
        players can judge staleness.
        """
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        snapshot = self.player.price_memory.get_snapshot(system.id)
        if not snapshot:
            return []

        lines: list[tuple[str, tuple[int, int, int]]] = []
        lines.append(("── Remembered Prices ──", Colors.TEXT_HIGHLIGHT))

        # Prioritize commodities the system exports/imports (actionable info).
        exports = system.economy.specialty_exports if system.economy else []
        imports = system.economy.specialty_imports if system.economy else []

        def _format_entry(commodity_id: str, price: int, day_seen: int) -> str:
            name = dl.commodities[commodity_id].name if commodity_id in dl.commodities else commodity_id
            days_ago = max(0, self.player.game_day - day_seen)
            if days_ago == 0:
                freshness = "today"
            elif days_ago == 1:
                freshness = "1d ago"
            else:
                freshness = f"{days_ago}d ago"
            return f"  {name}: {price:,} CR ({freshness})"

        shown: set[str] = set()
        if exports:
            lines.append(("Buy cheap:", Colors.GREEN))
            for cid in exports[:3]:
                if cid in snapshot:
                    price, day = snapshot[cid]
                    lines.append((_format_entry(cid, price, day), Colors.GREEN))
                    shown.add(cid)
        if imports:
            lines.append(("Sell high:", (220, 180, 40)))
            for cid in imports[:3]:
                if cid in snapshot:
                    price, day = snapshot[cid]
                    lines.append((_format_entry(cid, price, day), (220, 180, 40)))
                    shown.add(cid)

        # If no export/import context produced lines, fall back to first
        # few entries so at least something surfaces.
        if len(shown) == 0:
            for cid, (price, day) in list(snapshot.items())[:5]:
                lines.append((_format_entry(cid, price, day), Colors.TEXT))

        return lines

    def _get_remote_price_lines(self, system: StarSystem) -> list[tuple[str, tuple[int, int, int]]]:
        """Build price summary lines for a remote system."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.market import Market

        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        market = Market(system, commodities, self.player.game_day)
        prices = market.get_all_prices()

        lines: list[tuple[str, tuple[int, int, int]]] = []
        lines.append(("── Market Prices ──", Colors.TEXT_HIGHLIGHT))

        exports = system.economy.specialty_exports
        imports = system.economy.specialty_imports

        if exports:
            lines.append(("Buy cheap:", Colors.GREEN))
            for cid in exports[:3]:
                if cid in prices:
                    name = dl.commodities[cid].name if cid in dl.commodities else cid
                    lines.append((f"  {name}: {prices[cid]:,} CR", Colors.GREEN))

        if imports:
            lines.append(("Sell high:", (220, 180, 40)))
            for cid in imports[:3]:
                if cid in prices:
                    name = dl.commodities[cid].name if cid in dl.commodities else cid
                    lines.append((f"  {name}: {prices[cid]:,} CR", (220, 180, 40)))

        return lines

    @staticmethod
    def _get_danger_route_color(danger_level: str) -> tuple[int, int, int]:
        """Get route line color based on destination danger level."""
        return {
            "safe": (40, 65, 45),
            "moderate": (65, 55, 30),
            "dangerous": (65, 35, 35),
        }.get(danger_level, (40, 45, 65))

    @staticmethod
    def _get_danger_dot_color(danger_level: str) -> Optional[tuple[int, int, int, int]]:
        """Get danger indicator dot color (RGBA) for a system."""
        return {
            "safe": (80, 200, 100, 200),
            "moderate": (220, 180, 60, 200),
            "dangerous": (220, 60, 60, 200),
        }.get(danger_level)

    def render_top(self, screen: pygame.Surface) -> None:
        """PT-M: draw the first-time tip above pygame_gui elements."""
        if self._first_time_tip is not None:
            self._first_time_tip.render(screen)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
