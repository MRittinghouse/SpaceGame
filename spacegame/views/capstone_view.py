"""Modal overlay pushed when a capstone fires (A2-20).

The player presses Continue; the engine pops the modal and records the
acknowledge. Play continues from wherever it was interrupted.

This view is deliberately spartan. The narration template below is placeholder
text shipped to prove the plumbing mechanism works before any authored cutscenes
exist. When a future authored-content sprint (A2-21 or its successor) ships real
per-lens capstone narration, replace _TEMPLATE with per-lens strings and remove
this comment.

The view never reads player.lens_investment or the DataLoader. The engine
passes the pre-loaded Capstone and Lens at construction time so the view is a
pure rendering surface with no model dependencies beyond what is handed to it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, scale_x, scale_y
from spacegame.engine.fonts import FONT_LG, FONT_SECTION, FONT_SUBTITLE, get_font
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

if TYPE_CHECKING:
    from spacegame.models.capstone import Capstone
    from spacegame.models.lens import Lens

# Placeholder narration template (A2-20). The engine substitutes lens_name and
# core_fantasy at display time. This is generated text, not authored content.
# Replace when a future sprint ships authored per-lens capstone narration.
_TEMPLATE = (
    "You have reached the {lens_name} capstone. This is who you have chosen to be:"
    " {core_fantasy_lowercased_no_trailing_period}. Play continues."
)


class CapstoneView(BaseView):
    """Full-screen dim + centered panel with a single Continue button."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        capstone: "Capstone",
        lens: "Lens",
        on_acknowledge: Callable[[], None],
    ) -> None:
        """Initialize the capstone view.

        Args:
            ui_manager: The pygame_gui UIManager to attach the button to.
            capstone: The capstone record being presented.
            lens: The Lens record for capstone.lens_id. Pre-loaded by the
                engine so the view does not import DataLoader.
            on_acknowledge: Callback invoked when the player presses Continue.
                The engine writes capstones_reached and the dialogue flag there.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.capstone = capstone
        self.lens = lens
        self.on_acknowledge = on_acknowledge
        self.dismissed = False

        self.title_font = get_font("header", FONT_SECTION)
        self.body_font = get_font("dialogue", FONT_SUBTITLE)
        self.detail_font = get_font("narration", FONT_LG)

        self._continue_button: Optional[pygame_gui.elements.UIButton] = None
        self._pulse_time = 0.0

    def on_enter(self) -> None:
        super().on_enter()
        logger.info(
            f"Capstone modal: capstone_id={self.capstone.capstone_id!r}"
            f" lens_id={self.capstone.lens_id!r}"
        )
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _narration(self) -> str:
        """Build the substituted template string for this lens."""
        raw_fantasy = self.lens.core_fantasy.rstrip(".")
        lowercased = raw_fantasy[0].lower() + raw_fantasy[1:] if raw_fantasy else raw_fantasy
        return _TEMPLATE.format(
            lens_name=self.lens.name,
            core_fantasy_lowercased_no_trailing_period=lowercased,
        )

    def _create_ui(self) -> None:
        panel_bottom = (WINDOW_HEIGHT + scale_y(320)) // 2

        button_width = scale_x(200)
        button_height = scale_y(46)
        button_x = (WINDOW_WIDTH - button_width) // 2
        button_y = panel_bottom - button_height - scale_y(24)

        self._continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, button_y, button_width, button_height),
            text="CONTINUE",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self._continue_button is not None:
            self._continue_button.kill()
            self._continue_button = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return
        if self._continue_button is not None and event.ui_element is self._continue_button:
            logger.info(f"Capstone acknowledged: capstone_id={self.capstone.capstone_id!r}")
            self.dismissed = True
            self.on_acknowledge()

    def update(self, dt: float) -> None:
        self._pulse_time += dt

    def render(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(210)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        panel_width = scale_x(560)
        panel_height = scale_y(320)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*Colors.PANEL, 240))
        screen.blit(panel_surface, (panel_x, panel_y))

        pulse_alpha = int(140 + 80 * math.sin(self._pulse_time * 3))
        pulse_color = (*Colors.TEXT_HIGHLIGHT, max(0, min(255, pulse_alpha)))
        pulse_surf = pygame.Surface((panel_width + 4, panel_height + 4), pygame.SRCALPHA)
        pygame.draw.rect(pulse_surf, pulse_color, pulse_surf.get_rect(), 3)
        screen.blit(pulse_surf, (panel_x - 2, panel_y - 2))
        pygame.draw.rect(
            screen,
            Colors.TEXT_HIGHLIGHT,
            pygame.Rect(panel_x, panel_y, panel_width, panel_height),
            2,
        )

        title = self.title_font.render(
            self.lens.name.upper() + " CAPSTONE", True, Colors.TEXT_HIGHLIGHT
        )
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + scale_y(40)))
        screen.blit(title, title_rect)

        narration = self._narration()
        narration_surf = self.detail_font.render(narration, True, Colors.TEXT_PRIMARY)
        narration_rect = narration_surf.get_rect(center=(WINDOW_WIDTH // 2, panel_y + scale_y(130)))
        screen.blit(narration_surf, narration_rect)

    def is_dismissed(self) -> bool:
        """Return True after the player has pressed Continue."""
        return self.dismissed

    def get_next_state(self) -> Optional[str]:
        """Modal state; the engine drives transitions, not the view."""
        return None
