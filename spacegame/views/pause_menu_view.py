"""
Pause menu view.

Displayed when player presses ESC during gameplay.
Provides options to Save, Load, Settings, Resume, and Quit.
Features pulsing border glow and semi-transparent overlay.
"""

import pygame
import pygame_gui
import math
from typing import Optional

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState, scale_x, scale_y
from spacegame.views.base_view import BaseView
from spacegame.engine.fonts import FontCache, FONT_DISPLAY, FONT_HEADING
from spacegame.engine.draw_utils import draw_panel
from spacegame.utils.logger import logger


class PauseMenuView(BaseView):
    """Pause menu overlay with visual polish."""

    def __init__(self, ui_manager: pygame_gui.UIManager):
        super().__init__()
        self.ui_manager = ui_manager

        self.next_state: Optional[str] = None
        self.show_save_dialog = False
        self.show_load_dialog = False
        self.show_settings_dialog = False

        # Fonts
        self.title_font = FontCache.get(FONT_DISPLAY)
        self.button_font = FontCache.get(FONT_HEADING)

        # UI Elements
        self.resume_button: Optional[pygame_gui.elements.UIButton] = None
        self.save_button: Optional[pygame_gui.elements.UIButton] = None
        self.load_button: Optional[pygame_gui.elements.UIButton] = None
        self.settings_button: Optional[pygame_gui.elements.UIButton] = None
        self.stats_button: Optional[pygame_gui.elements.UIButton] = None
        self.achievements_button: Optional[pygame_gui.elements.UIButton] = None
        self.main_menu_button: Optional[pygame_gui.elements.UIButton] = None
        self.quit_button: Optional[pygame_gui.elements.UIButton] = None

        # Animation
        self._glow_time = 0.0

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Pause menu opened")
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        panel_width = scale_x(400)
        panel_height = scale_y(620)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        button_width = scale_x(300)
        button_height = scale_y(45)
        button_x = panel_x + (panel_width - button_width) // 2
        spacing = scale_y(60)

        self.resume_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, panel_y + 70, button_width, button_height),
            text="RESUME",
            manager=self.ui_manager,
        )
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing, button_width, button_height
            ),
            text="SAVE GAME",
            manager=self.ui_manager,
        )
        self.load_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing * 2, button_width, button_height
            ),
            text="LOAD GAME",
            manager=self.ui_manager,
        )
        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing * 3, button_width, button_height
            ),
            text="SETTINGS",
            manager=self.ui_manager,
        )
        self.stats_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing * 4, button_width, button_height
            ),
            text="STATISTICS",
            manager=self.ui_manager,
        )
        self.achievements_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing * 5, button_width, button_height
            ),
            text="ACHIEVEMENTS",
            manager=self.ui_manager,
        )
        self.main_menu_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing * 6, button_width, button_height
            ),
            text="MAIN MENU",
            manager=self.ui_manager,
        )
        self.quit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                button_x, panel_y + 70 + spacing * 7, button_width, button_height
            ),
            text="QUIT GAME",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for btn in [
            self.resume_button,
            self.save_button,
            self.load_button,
            self.settings_button,
            self.stats_button,
            self.achievements_button,
            self.main_menu_button,
            self.quit_button,
        ]:
            if btn:
                btn.kill()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.resume_button:
                logger.info("Resume game")
                self.next_state = "resume"
            elif event.ui_element == self.save_button:
                logger.info("Open save dialog")
                self.show_save_dialog = True
            elif event.ui_element == self.load_button:
                logger.info("Open load dialog")
                self.show_load_dialog = True
            elif event.ui_element == self.settings_button:
                logger.info("Open settings dialog")
                self.show_settings_dialog = True
            elif event.ui_element == self.stats_button:
                logger.info("Open statistics")
                self.next_state = GameState.STATISTICS
            elif event.ui_element == self.achievements_button:
                logger.info("Open achievements")
                self.next_state = GameState.ACHIEVEMENTS
            elif event.ui_element == self.main_menu_button:
                logger.info("Return to main menu")
                self.next_state = GameState.MAIN_MENU
            elif event.ui_element == self.quit_button:
                logger.info("Quit game")
                import sys

                pygame.quit()
                sys.exit()

    def update(self, dt: float) -> None:
        self._glow_time += dt

    def render(self, screen: pygame.Surface) -> None:
        # Semi-transparent dark overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Panel
        panel_width = scale_x(400)
        panel_height = scale_y(620)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        draw_panel(
            screen,
            pygame.Rect(panel_x, panel_y, panel_width, panel_height),
            alpha=240,
            bg_color=Colors.PANEL,
        )

        # Pulsing border glow
        glow_alpha = int(120 + 80 * math.sin(self._glow_time * 3))
        border_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # Outer dim glow
        glow_surf = pygame.Surface((panel_width + 4, panel_height + 4), pygame.SRCALPHA)
        pygame.draw.rect(
            glow_surf, (*Colors.TEXT_HIGHLIGHT, glow_alpha // 3), glow_surf.get_rect(), 2
        )
        screen.blit(glow_surf, (panel_x - 2, panel_y - 2))

        # Inner bright border
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, border_rect, 2)

        # Title
        title = self.title_font.render("PAUSED", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 40))
        screen.blit(title, title_rect)

    def get_next_state(self) -> Optional[str]:
        state = self.next_state
        self.next_state = None
        return state

    def should_show_save_dialog(self) -> bool:
        result = self.show_save_dialog
        self.show_save_dialog = False
        return result

    def should_show_load_dialog(self) -> bool:
        result = self.show_load_dialog
        self.show_load_dialog = False
        return result

    def should_show_settings_dialog(self) -> bool:
        result = self.show_settings_dialog
        self.show_settings_dialog = False
        return result
