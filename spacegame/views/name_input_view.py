"""
Name input view for new game character creation.

Allows the player to enter their name before starting a new game.
"""

import re
from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_DISPLAY, FONT_MD, FONT_XL, get_font
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# Name validation constants
MAX_NAME_LENGTH = 20
_VALID_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 ]+$")


class NameInputView(BaseView):
    """Simple view for entering the player's name at game start."""

    def __init__(self, ui_manager: pygame_gui.UIManager) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_DISPLAY)
        self.subtitle_font = get_font("dialogue", FONT_XL)
        self.error_font = get_font("machine", FONT_MD)

        # UI elements (created in _create_ui)
        self.name_input: Optional[pygame_gui.elements.UITextEntryLine] = None
        self.ship_name_input: Optional[pygame_gui.elements.UITextEntryLine] = None
        self.begin_button: Optional[pygame_gui.elements.UIButton] = None

        # Visual systems
        self.background = AnimatedBackground("name_input", WINDOW_WIDTH, WINDOW_HEIGHT, seed=99)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

        # Stored names
        self._player_name: str = "Captain"
        self._ship_name: str = ""
        self._error_message: str = ""
        self._error_timer: float = 0.0

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered name input view")
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create UI elements for name entry."""
        cx = WINDOW_WIDTH // 2

        # Name text input
        input_width = scale_x(300)
        input_rect = pygame.Rect(cx - input_width // 2, scale_y(340), input_width, scale_y(40))
        self.name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=input_rect,
            manager=self.ui_manager,
        )
        # Left empty so the player types their own name. The intro narration
        # establishes them as a scrapyard kid; pre-filling "Captain" would
        # undercut the unearned-rank discipline enforced elsewhere.
        self.name_input.set_text("")
        self.name_input.set_text_length_limit(MAX_NAME_LENGTH)

        # Ship name text input
        ship_rect = pygame.Rect(cx - input_width // 2, scale_y(430), input_width, scale_y(40))
        self.ship_name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=ship_rect,
            manager=self.ui_manager,
        )
        self.ship_name_input.set_text("")
        self.ship_name_input.set_text_length_limit(MAX_NAME_LENGTH)

        # Launch button. Avoided "Begin Journey" style per the Writing
        # Bible's corporate-voice ban. "Launch" is action-oriented and
        # native to the genre.
        btn_width = scale_x(200)
        self.begin_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(cx - btn_width // 2, scale_y(510), btn_width, scale_y(45)),
            text="LAUNCH",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Clean up UI elements."""
        for elem in [self.name_input, self.ship_name_input, self.begin_button]:
            if elem:
                elem.kill()
        self.name_input = None
        self.ship_name_input = None
        self.begin_button = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.begin_button:
                name = self.name_input.get_text().strip() if self.name_input else ""
                if not name:
                    self._error_message = "Type a name first."
                    self._error_timer = 3.0
                elif len(name) > MAX_NAME_LENGTH:
                    self._error_message = f"Name too long. Keep it under {MAX_NAME_LENGTH} characters."
                    self._error_timer = 3.0
                elif not _VALID_NAME_PATTERN.match(name):
                    self._error_message = "Letters, numbers, and spaces only."
                    self._error_timer = 3.0
                else:
                    self._player_name = name
                    # Ship name is optional — validate if provided
                    ship_name = (
                        self.ship_name_input.get_text().strip() if self.ship_name_input else ""
                    )
                    if ship_name and not _VALID_NAME_PATTERN.match(ship_name):
                        self._error_message = (
                            "Ship name can only contain letters, numbers, and spaces."
                        )
                        self._error_timer = 3.0
                        return
                    self._ship_name = ship_name
                    self.next_state = GameState.GALAXY_MAP
                    logger.info(
                        f"Player: {self._player_name}, Ship: {self._ship_name or '(default)'}"
                    )

    def update(self, dt: float) -> None:
        self.background.update(dt)
        if self._error_timer > 0:
            self._error_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        cx = WINDOW_WIDTH // 2

        # Title
        title_surf = self.title_font.render("Enter Your Name", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_surf.get_rect(center=(cx, scale_y(240)))
        screen.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = self.subtitle_font.render(
            "What shall we call you, spacer?", True, Colors.TEXT_SECONDARY
        )
        sub_rect = sub_surf.get_rect(center=(cx, scale_y(290)))
        screen.blit(sub_surf, sub_rect)

        # Ship name label
        ship_label = self.subtitle_font.render(
            "Name your ship (optional):", True, Colors.TEXT_SECONDARY
        )
        screen.blit(ship_label, ship_label.get_rect(center=(cx, scale_y(410))))

        # Error message
        if self._error_timer > 0 and self._error_message:
            err_surf = self.error_font.render(self._error_message, True, Colors.RED)
            err_rect = err_surf.get_rect(center=(cx, scale_y(490)))
            screen.blit(err_surf, err_rect)

    def get_next_state(self) -> Optional[GameState]:
        """Return the requested next state."""
        return self.next_state

    def get_player_name(self) -> str:
        """Get the entered player name."""
        return self._player_name

    def get_ship_name(self) -> str:
        """Get the entered ship name (empty string if not provided)."""
        return self._ship_name
