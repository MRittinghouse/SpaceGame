"""
Name input view for new game character creation.

Allows the player to enter their name before starting a new game.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.views.base_view import BaseView
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FontCache
from spacegame.utils.logger import logger


class NameInputView(BaseView):
    """Simple view for entering the player's name at game start."""

    def __init__(self, ui_manager: pygame_gui.UIManager) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = FontCache.get(48)
        self.subtitle_font = FontCache.get(28)

        # UI elements (created in _create_ui)
        self.name_input: Optional[pygame_gui.elements.UITextEntryLine] = None
        self.begin_button: Optional[pygame_gui.elements.UIButton] = None

        # Visual systems
        self.background = AnimatedBackground("name_input", WINDOW_WIDTH, WINDOW_HEIGHT, seed=99)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

        # Stored player name
        self._player_name: str = "Captain"

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered name input view")
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        """Create UI elements for name entry."""
        cx = WINDOW_WIDTH // 2

        # Name text input
        input_width = 300
        input_rect = pygame.Rect(cx - input_width // 2, 340, input_width, 40)
        self.name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=input_rect,
            manager=self.ui_manager,
        )
        self.name_input.set_text("Captain")

        # Begin Journey button
        btn_width = 200
        self.begin_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(cx - btn_width // 2, 420, btn_width, 45),
            text="BEGIN JOURNEY",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Clean up UI elements."""
        for elem in [self.name_input, self.begin_button]:
            if elem:
                elem.kill()
        self.name_input = None
        self.begin_button = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.begin_button:
                name = self.name_input.get_text().strip() if self.name_input else ""
                if name:
                    self._player_name = name
                    self.next_state = GameState.GALAXY_MAP
                    logger.info(f"Player name entered: {self._player_name}")

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        cx = WINDOW_WIDTH // 2

        # Title
        title_surf = self.title_font.render("Enter Your Name", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_surf.get_rect(center=(cx, 240))
        screen.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = self.subtitle_font.render(
            "What shall we call you, spacer?", True, Colors.TEXT_SECONDARY
        )
        sub_rect = sub_surf.get_rect(center=(cx, 290))
        screen.blit(sub_surf, sub_rect)

    def get_next_state(self) -> Optional[GameState]:
        """Return the requested next state."""
        return self.next_state

    def get_player_name(self) -> str:
        """Get the entered player name."""
        return self._player_name
