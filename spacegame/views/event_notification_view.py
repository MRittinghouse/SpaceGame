"""
Modal overlay for DISASTER market events.

Displayed on top of current view, requires player to dismiss before continuing.
"""

import pygame
import pygame_gui
import math
from typing import Optional

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, scale_x, scale_y
from spacegame.models.event import MarketEvent
from spacegame.views.base_view import BaseView
from spacegame.engine.fonts import FONT_BODY, FONT_SECTION, FONT_SUBTITLE, FontCache
from spacegame.utils.logger import logger


class EventNotificationView(BaseView):
    """Modal overlay for critical market events."""

    def __init__(self, ui_manager: pygame_gui.UIManager, event: MarketEvent):
        super().__init__()
        self.ui_manager = ui_manager
        self.event = event
        self.dismissed = False

        # Fonts
        self.title_font = FontCache.get(FONT_SECTION)
        self.body_font = FontCache.get(FONT_SUBTITLE)
        self.detail_font = FontCache.get(FONT_BODY)

        # UI Elements
        self.ok_button: Optional[pygame_gui.elements.UIButton] = None

        # Animation
        self._glow_time = 0.0

    def on_enter(self) -> None:
        super().on_enter()
        logger.info(f"Event notification shown: {self.event.description}")
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create OK button centered in panel."""
        panel_width = scale_x(500)
        panel_height = scale_y(300)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        button_width = scale_x(160)
        button_height = scale_y(45)
        self.ok_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                panel_x + (panel_width - button_width) // 2,
                panel_y + panel_height - scale_y(70),
                button_width,
                button_height,
            ),
            text="ACKNOWLEDGED",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self.ok_button:
            self.ok_button.kill()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.ok_button:
                self.dismissed = True
                logger.info("Event notification dismissed")

    def update(self, dt: float) -> None:
        self._glow_time += dt

    def render(self, screen: pygame.Surface) -> None:
        # Semi-transparent dark overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Panel
        panel_width = scale_x(500)
        panel_height = scale_y(300)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*Colors.PANEL, 240))
        screen.blit(panel_surface, (panel_x, panel_y))

        # Pulsing red border for DISASTER
        glow_alpha = int(120 + 80 * math.sin(self._glow_time * 4))
        border_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        glow_surf = pygame.Surface((panel_width + 4, panel_height + 4), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*Colors.RED, glow_alpha // 2), glow_surf.get_rect(), 3)
        screen.blit(glow_surf, (panel_x - 2, panel_y - 2))
        pygame.draw.rect(screen, Colors.RED, border_rect, 2)

        # Title
        event_type_name = self.event.event_type.value.upper()
        title = self.title_font.render(f"MARKET {event_type_name}", True, Colors.RED)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 40))
        screen.blit(title, title_rect)

        # Description
        desc = self.body_font.render(self.event.description, True, Colors.TEXT_PRIMARY)
        desc_rect = desc.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 100))
        screen.blit(desc, desc_rect)

        # Details
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        commodity = dl.commodities.get(self.event.commodity_id)
        commodity_name = commodity.name if commodity else self.event.commodity_id
        system = dl.systems.get(self.event.system_id)
        system_name = system.name if system else self.event.system_id

        details = [
            f"System: {system_name}",
            f"Commodity: {commodity_name}",
            f"Price effect: x{self.event.price_multiplier:.1f}",
            f"Duration: {self.event.duration_days} days",
        ]

        for i, line in enumerate(details):
            surf = self.detail_font.render(line, True, Colors.TEXT_SECONDARY)
            surf_rect = surf.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 140 + i * 24))
            screen.blit(surf, surf_rect)

    def is_dismissed(self) -> bool:
        """Check if the player has dismissed this notification."""
        return self.dismissed
