"""Repair bay view — hull repair station service.

Displays ship hull status and allows the player to repair damage for credits.
Shields are automatically restored on docking (handled by StationHubView).
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
from spacegame.engine.fonts import FONT_BODY, FONT_LG, FONT_MD, FONT_SUBTITLE, FONT_TITLE, get_font
from spacegame.engine.particles import HEAL_SPARKLE, ParticlePool
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# Layout (centered modal pattern, also used in investment_view)
PANEL_W = scale_x(500)
PANEL_H = scale_y(400)
PANEL_X = WINDOW_WIDTH // 2 - PANEL_W // 2
PANEL_Y = WINDOW_HEIGHT // 2 - PANEL_H // 2
BAR_X = PANEL_X + scale_x(40)
BAR_W = PANEL_W - scale_x(80)
BAR_H = scale_y(28)
BUTTON_W = scale_x(200)
BUTTON_H = scale_y(44)


class RepairBayView(BaseView):
    """Hull repair service view.

    Shows current hull/shield status, repair cost, and a repair button.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        cost_per_hp: int,
        location_name: str = "Repair Bay",
        location_flavor: str = "",
    ) -> None:
        """Initialize repair bay view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player.
            cost_per_hp: Credits per hull point for repair.
            location_name: Display name from location data.
            location_flavor: Flavor text from location data.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.cost_per_hp = cost_per_hp
        self.location_name = location_name
        self.location_flavor = location_flavor
        self.next_state: Optional[GameState] = None

        # Message feedback
        self.message: Optional[str] = None
        self.message_timer: float = 0.0
        self.message_color: tuple[int, int, int] = Colors.TEXT_PRIMARY

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.subtitle_font = get_font("dialogue", FONT_MD)
        self.label_font = get_font("dialogue", FONT_SUBTITLE)
        self.value_font = get_font("stats", FONT_LG)
        self.msg_font = get_font("dialogue", FONT_BODY)

        # UI element refs
        self.repair_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Particles for repair effect
        self.particles = ParticlePool(60)

        # Background
        self.background = AnimatedBackground("station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=7777)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        """Activate view and create UI."""
        super().on_enter()
        logger.info("Entered repair bay")
        self.message = None
        self.message_timer = 0.0
        self._create_ui()

    def on_exit(self) -> None:
        """Deactivate and clean up."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create repair and back buttons."""
        self._destroy_ui()

        # Repair button
        self.repair_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W // 2 - BUTTON_W // 2,
                PANEL_Y + PANEL_H - 120,
                BUTTON_W,
                BUTTON_H,
            ),
            text="REPAIR HULL",
            manager=self.ui_manager,
        )

        # Back button
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W // 2 - BUTTON_W // 2,
                PANEL_Y + PANEL_H - 65,
                BUTTON_W,
                BUTTON_H,
            ),
            text="BACK",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all UI elements."""
        for elem in [self.repair_button, self.back_button]:
            if elem:
                elem.kill()
        self.repair_button = None
        self.back_button = None

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle button clicks."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.repair_button:
                self._execute_repair()
            elif event.ui_element == self.back_button:
                self._request_back()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._request_back()

    def update(self, dt: float) -> None:
        """Update background, particles, and message timer."""
        self.background.update(dt)
        self.particles.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None

        # Sprint 5b follow-up: pre-emptive Repair button disable with
        # tooltip reason. Replaces the click-then-error pattern for
        # "already at full hull" and "can't afford the repair."
        if self.repair_button is not None:
            reason = self._why_cannot_repair()
            if reason is not None:
                self.repair_button.disable()
                self.repair_button.tool_tip_text = reason
            else:
                self.repair_button.enable()
                self.repair_button.tool_tip_text = None

    def _why_cannot_repair(self) -> Optional[str]:
        """Return an in-voice reason Repair is disabled, or None if valid."""
        if self.get_damage_amount() <= 0:
            return "Already at full hull."
        if not self.can_afford_repair():
            return "Can't afford the full repair."
        return None

    def render(self, screen: pygame.Surface) -> None:
        """Render repair bay interface."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel background
        draw_panel(screen, (PANEL_X, PANEL_Y, PANEL_W, PANEL_H), alpha=230)
        # Green accent bar at top of panel
        pygame.draw.rect(screen, Colors.GREEN, (PANEL_X, PANEL_Y, PANEL_W, 3))

        # Title — use location name
        title = self.title_font.render(self.location_name.upper(), True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (PANEL_X + PANEL_W // 2 - title.get_width() // 2, PANEL_Y + 12))

        # Flavor text below title
        if self.location_flavor:
            flavor = self.location_flavor
            if len(flavor) > 75:
                flavor = flavor[:72] + "..."
            flavor_surf = self.subtitle_font.render(flavor, True, Colors.TEXT_SECONDARY)
            screen.blit(
                flavor_surf,
                (PANEL_X + PANEL_W // 2 - flavor_surf.get_width() // 2, PANEL_Y + 40),
            )

        # Hull bar
        ship = self.player.ship
        max_hull = ship.ship_type.combat_hull
        hull_ratio = ship.current_hull / max_hull if max_hull > 0 else 1.0
        hull_y = PANEL_Y + 70

        hull_label = self.label_font.render("Hull Integrity", True, Colors.TEXT_PRIMARY)
        screen.blit(hull_label, (BAR_X, hull_y))

        bar_y = hull_y + 26
        # Dynamic color based on hull ratio
        if hull_ratio > 0.5:
            bar_color = Colors.GREEN
        elif hull_ratio > 0.25:
            bar_color = Colors.YELLOW
        else:
            bar_color = Colors.RED
        draw_bar(
            screen,
            BAR_X,
            bar_y,
            BAR_W,
            BAR_H,
            ship.current_hull,
            max_hull,
            bar_color,
            font=self.value_font,
            bg_color=Colors.BAR_BG_LIGHT,
        )

        # Shield bar (smaller, informational)
        shield_y = bar_y + BAR_H + 14
        max_shields = ship.ship_type.combat_shields
        shield_label = self.label_font.render("Shields", True, Colors.TEXT_SECONDARY)
        screen.blit(shield_label, (BAR_X, shield_y))
        restored_label = self.value_font.render("(restored on dock)", True, Colors.TEXT_SECONDARY)
        screen.blit(restored_label, (BAR_X + shield_label.get_width() + 8, shield_y + 3))

        shield_bar_y = shield_y + 24
        shield_bar_h = 18
        draw_bar(
            screen,
            BAR_X,
            shield_bar_y,
            BAR_W,
            shield_bar_h,
            ship.current_shields,
            max_shields,
            Colors.BLUE,
            font=self.value_font,
            bg_color=Colors.BAR_BG_LIGHT,
        )

        # Repair cost info
        cost_y = shield_bar_y + shield_bar_h + 20
        damage = self.get_damage_amount()
        total_cost = self.get_repair_cost()

        if damage > 0:
            cost_text = f"Repair {damage} HP for {total_cost:,} CR ({self.cost_per_hp} CR/HP)"
            can_afford = self.can_afford_repair()
            cost_color = Colors.TEXT_PRIMARY if can_afford else Colors.RED
        else:
            cost_text = "Hull integrity is at maximum."
            cost_color = Colors.GREEN

        cost_label = self.label_font.render(cost_text, True, cost_color)
        screen.blit(cost_label, (BAR_X, cost_y))

        # Credits
        credits_y = cost_y + 30
        credits_text = self.value_font.render(
            f"Credits: {self.player.credits:,} CR", True, Colors.TEXT_SECONDARY
        )
        screen.blit(credits_text, (BAR_X, credits_y))

        # Particles (on top of panel)
        self.particles.render(screen)

        # Message
        if self.message and self.message_timer > 0:
            msg_surf = self.msg_font.render(self.message, True, self.message_color)
            screen.blit(
                msg_surf,
                (
                    PANEL_X + PANEL_W // 2 - msg_surf.get_width() // 2,
                    PANEL_Y + PANEL_H - 30,
                ),
            )

    # === Actions ===

    def _execute_repair(self) -> None:
        """Attempt to repair the ship hull."""
        success, msg = self.player.repair_at_station(self.cost_per_hp)
        if success:
            get_audio_manager().play_sfx("repair_weld")
            self.message = msg
            self.message_color = Colors.GREEN
            self.message_timer = 3.0
            logger.info(msg)
            # Emit repair particles along the hull bar
            bar_y = PANEL_Y + 70 + 26 + BAR_H // 2
            for offset in range(0, BAR_W, 40):
                self.particles.emit(BAR_X + offset, bar_y, HEAL_SPARKLE)
        else:
            self.message = msg
            self.message_color = Colors.RED
            self.message_timer = 3.0

    def _request_back(self) -> None:
        """Navigate back to station hub."""
        self.next_state = GameState.STATION_HUB

    # === Data helpers ===

    def get_damage_amount(self) -> int:
        """Get current hull damage in HP."""
        return self.player.ship.ship_type.combat_hull - self.player.ship.current_hull

    def get_repair_cost(self) -> int:
        """Get total credits to repair hull to full."""
        return self.get_damage_amount() * self.cost_per_hp

    def can_afford_repair(self) -> bool:
        """Check if player can afford full hull repair."""
        return self.player.credits >= self.get_repair_cost()

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state
