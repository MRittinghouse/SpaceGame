"""
Galaxy map view.

Visual map of star systems with navigation and travel mechanics.
Features animated background, procedural planet thumbnails, and pulsing highlights.
"""

import pygame
import pygame_gui
import math
from typing import Optional, Dict
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.system import StarSystem
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.procedural import generate_planet
from spacegame.engine.particles import ParticlePool, SCAN_PULSE, WARP_TRAIL


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
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.systems = systems
        self.active_events: Dict = active_events or {}

        # Map visualization settings
        self.map_center_x = WINDOW_WIDTH // 2
        self.map_center_y = WINDOW_HEIGHT // 2
        self.zoom = 2.0

        # UI state
        self.selected_system: Optional[str] = None
        self.hovered_system: Optional[str] = None
        self.next_state: Optional[GameState] = None

        # Fonts
        self.system_font = pygame.font.Font(None, 24)
        self.info_font = pygame.font.Font(None, 20)
        self.title_font = pygame.font.Font(None, 32)

        # UI buttons
        self.trade_button: Optional[pygame_gui.elements.UIButton] = None
        self.travel_button: Optional[pygame_gui.elements.UIButton] = None
        self.skills_button: Optional[pygame_gui.elements.UIButton] = None
        self.missions_button: Optional[pygame_gui.elements.UIButton] = None
        self.crew_button: Optional[pygame_gui.elements.UIButton] = None
        self.shipyard_button: Optional[pygame_gui.elements.UIButton] = None
        self.save_button: Optional[pygame_gui.elements.UIButton] = None
        self.menu_button: Optional[pygame_gui.elements.UIButton] = None
        self.info_panel: Optional[pygame_gui.elements.UIPanel] = None

        # Save request flag (consumed by game.py)
        self.save_requested: bool = False

        # Mission markers
        self.mission_target_systems: set[str] = set()

        # Animated background
        self.background = AnimatedBackground("trade_routes", WINDOW_WIDTH, WINDOW_HEIGHT, seed=20)

        # Procedural planet surfaces (cached)
        self._planet_surfaces: Dict[str, pygame.Surface] = {}
        self._generate_planet_thumbnails()

        # Particles
        self.particles = ParticlePool(200)

        # Animation state
        self._glow_time = 0.0
        self._dash_offset = 0.0

    def _generate_planet_thumbnails(self) -> None:
        """Generate procedural planet thumbnails for each system."""
        for i, (sys_id, system) in enumerate(self.systems.items()):
            planet_type = system.type if system.type else "terran"
            surface = generate_planet(12, planet_type, seed=hash(sys_id) % 10000)
            self._planet_surfaces[sys_id] = surface

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered Galaxy Map")
        self.selected_system = self.player.current_system_id
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        button_width = 150
        button_height = 40
        button_x = WINDOW_WIDTH - button_width - 20
        start_y = WINDOW_HEIGHT - 294
        spacing = 34

        self.trade_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y, button_width, button_height),
            text="Trade",
            manager=self.ui_manager,
        )
        self.travel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing, button_width, button_height),
            text="Travel",
            manager=self.ui_manager,
        )
        self.skills_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 2, button_width, button_height),
            text="Skills",
            manager=self.ui_manager,
        )
        self.missions_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 3, button_width, button_height),
            text="Missions",
            manager=self.ui_manager,
        )
        self.crew_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 4, button_width, button_height),
            text="Crew",
            manager=self.ui_manager,
        )
        self.shipyard_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 5, button_width, button_height),
            text="Shipyard",
            manager=self.ui_manager,
        )
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 6, button_width, button_height),
            text="Save",
            manager=self.ui_manager,
        )
        self.menu_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 7, button_width, button_height),
            text="Main Menu",
            manager=self.ui_manager,
        )
        self._update_button_states()

    def _destroy_ui(self) -> None:
        for btn in [
            self.trade_button,
            self.travel_button,
            self.skills_button,
            self.missions_button,
            self.crew_button,
            self.shipyard_button,
            self.save_button,
            self.menu_button,
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
        return current.fuel_cost_to(target, self.player.ship.effective_fuel_efficiency)

    def _world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        screen_x = int(self.map_center_x + (world_x * self.zoom))
        screen_y = int(self.map_center_y - (world_y * self.zoom))
        return (screen_x, screen_y)

    def _get_system_at_mouse(self, mouse_pos: tuple[int, int]) -> Optional[str]:
        for system_id, system in self.systems.items():
            screen_pos = self._world_to_screen(system.coordinates.x, system.coordinates.y)
            distance = (
                (mouse_pos[0] - screen_pos[0]) ** 2 + (mouse_pos[1] - screen_pos[1]) ** 2
            ) ** 0.5
            if distance < 20:
                return system_id
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
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
                logger.debug(f"Selected system: {clicked_system}")

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.trade_button:
                logger.info("Opening trade interface")
                self.next_state = GameState.TRADING
            elif event.ui_element == self.travel_button:
                self._execute_travel()
            elif event.ui_element == self.skills_button:
                self.next_state = GameState.SKILL_TREE
            elif event.ui_element == self.missions_button:
                self.next_state = GameState.MISSION_LOG
            elif event.ui_element == self.crew_button:
                self.next_state = GameState.CREW_ROSTER
            elif event.ui_element == self.shipyard_button:
                self.next_state = GameState.SHIPYARD
            elif event.ui_element == self.save_button:
                self.save_requested = True
            elif event.ui_element == self.menu_button:
                self.next_state = GameState.MAIN_MENU

    def _execute_travel(self) -> None:
        if not self.selected_system or self.selected_system == self.player.current_system_id:
            return

        fuel_cost = self._calculate_fuel_cost(self.selected_system)
        success, msg = self.player.travel_to_system(self.selected_system, fuel_cost)

        logger.info(f"Travel result: {msg}")
        if success:
            from spacegame.config import XP_PER_TRAVEL

            xp_msgs = self.player.progression.add_xp(XP_PER_TRAVEL)
            for m in xp_msgs:
                logger.info(m)
            self._update_button_states()

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        self._dash_offset += 30 * dt  # scrolling dash offset

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)

        # Title
        title = self.title_font.render("GALAXY MAP", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (20, 20))

        # Player stats
        stats_y = 60
        stats_text = [
            f"Day: {self.player.game_day}  |  Level: {self.player.progression.level}",
            f"Credits: {self.player.credits:,} CR",
            f"Ship: {self.player.ship.name}",
            f"Fuel: {self.player.ship.current_fuel}/{self.player.ship.max_fuel}",
        ]
        for i, text in enumerate(stats_text):
            surf = self.info_font.render(text, True, Colors.TEXT)
            screen.blit(surf, (20, stats_y + i * 25))

        # Draw travel lines from current system (animated dashes)
        current_system = self.systems[self.player.current_system_id]
        current_pos = self._world_to_screen(
            current_system.coordinates.x, current_system.coordinates.y
        )

        for system in self.systems.values():
            if system.id == self.player.current_system_id:
                continue
            target_pos = self._world_to_screen(system.coordinates.x, system.coordinates.y)
            self._draw_dashed_line(screen, (40, 45, 65), current_pos, target_pos)

        # Draw systems
        for system_id, system in self.systems.items():
            screen_x, screen_y = self._world_to_screen(system.coordinates.x, system.coordinates.y)

            # Pulsing glow ring on current system
            if system_id == self.player.current_system_id:
                glow_alpha = int(120 + 80 * math.sin(self._glow_time * 3))
                glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*Colors.TEXT_HIGHLIGHT, glow_alpha), (30, 30), 25, 3)
                screen.blit(glow_surf, (screen_x - 30, screen_y - 30))

            # Selected system highlight
            if system_id == self.selected_system:
                pygame.draw.circle(screen, Colors.TEXT, (screen_x, screen_y), 22, 2)

            # Hovered system highlight
            if system_id == self.hovered_system:
                pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y), 20, 1)

            # Draw procedural planet thumbnail
            planet_surf = self._planet_surfaces.get(system_id)
            if planet_surf:
                pw, ph = planet_surf.get_size()
                screen.blit(planet_surf, (screen_x - pw // 2, screen_y - ph // 2))
            else:
                # Fallback colored circle
                pygame.draw.circle(screen, (150, 150, 150), (screen_x, screen_y), 12)

            # Faction-colored ring
            faction_color = self._get_faction_color(system.faction)
            if faction_color:
                ring_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*faction_color, 160), (22, 22), 18, 2)
                screen.blit(ring_surf, (screen_x - 22, screen_y - 22))

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
                screen.blit(indicator_surf, (screen_x + 14, screen_y - 20))

            # Mission destination marker (pulsing diamond)
            if system_id in self.mission_target_systems:
                m_alpha = int(150 + 100 * math.sin(self._glow_time * 4))
                marker_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
                points = [(7, 0), (14, 7), (7, 14), (0, 7)]
                pygame.draw.polygon(
                    marker_surf,
                    (*Colors.TEXT_HIGHLIGHT, min(255, m_alpha)),
                    points,
                )
                screen.blit(marker_surf, (screen_x - 20, screen_y - 7))

            # System name
            name_surf = self.system_font.render(system.name, True, Colors.TEXT)
            name_rect = name_surf.get_rect(center=(screen_x, screen_y - 25))
            screen.blit(name_surf, name_rect)

        # Particles on top of systems
        self.particles.render(screen)

        # Selected system info panel
        if self.selected_system:
            self._draw_system_info(screen, self.selected_system)

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

    def _draw_system_info(self, screen: pygame.Surface, system_id: str) -> None:
        system = self.systems[system_id]

        panel_x = WINDOW_WIDTH - 320
        panel_y = 60
        panel_width = 300
        panel_height = 250

        # Background with glow border
        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 35, 200))
        screen.blit(panel_surf, (panel_x, panel_y))

        # Border with inner glow
        pygame.draw.rect(screen, Colors.UI_BORDER, (panel_x, panel_y, panel_width, panel_height), 1)
        # Bright inner edge
        inner_rect = pygame.Rect(panel_x + 1, panel_y + 1, panel_width - 2, panel_height - 2)
        glow_surf = pygame.Surface((inner_rect.width, inner_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*Colors.TEXT_HIGHLIGHT, 30), glow_surf.get_rect(), 1)
        screen.blit(glow_surf, inner_rect.topleft)

        # Content
        y_offset = panel_y + 10
        line_height = 22

        name_surf = self.title_font.render(system.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (panel_x + 10, y_offset))
        y_offset += 35

        # Build faction line with rep info
        faction_id = self.player.get_faction_for_system(system_id)
        if faction_id:
            tier = self.player.get_reputation_tier(faction_id)
            rep_val = self.player.get_reputation(faction_id)
            sign = "+" if rep_val >= 0 else ""
            faction_line = f"Faction: {system.faction} ({tier.value}, {sign}{rep_val})"
        else:
            faction_line = f"Faction: {system.faction}"

        info_lines = [
            f"Type: {system.type.replace('_', ' ').title()}",
            faction_line,
            f"Danger: {system.danger_level.title()}",
            "",
        ]

        if system_id != self.player.current_system_id:
            current = self.systems[self.player.current_system_id]
            distance = current.distance_to(system)
            fuel_cost = self._calculate_fuel_cost(system_id)
            info_lines.extend(
                [
                    f"Distance: {distance:.1f} units",
                    f"Fuel Cost: {fuel_cost} units",
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
            info_lines.append("")
            info_lines.append(f"Event: {active_event.event_type.value.upper()}")
            info_lines.append(f"  {commodity_name} ({days_left}d)")

        for line in info_lines:
            surf = self.info_font.render(line, True, Colors.TEXT)
            screen.blit(surf, (panel_x + 10, y_offset))
            y_offset += line_height

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
