"""
Main menu view.

Starting point for the game with options to start new game, load, settings, etc.
"""

import pygame
import pygame_gui
import math
from typing import Optional, Union
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState, IMAGES_DIR
from spacegame.save_manager import SaveManager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, STAR_TWINKLE


class MainMenuView(BaseView):
    """
    Main menu screen with game options.

    Features animated deep-space background, title glow, and particle ambiance.
    """

    def __init__(self, ui_manager: pygame_gui.UIManager, save_manager: SaveManager) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.save_manager = save_manager
        self.next_state: Optional[Union[GameState, str]] = None

        # Fonts
        self.title_font = pygame.font.Font(None, 96)
        self.subtitle_font = pygame.font.Font(None, 36)

        # UI Elements (created in on_enter)
        self.new_game_button: Optional[pygame_gui.elements.UIButton] = None
        self.continue_button: Optional[pygame_gui.elements.UIButton] = None
        self.load_game_button: Optional[pygame_gui.elements.UIButton] = None
        self.exit_button: Optional[pygame_gui.elements.UIButton] = None

        # Animated background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=7)

        # Particle system for ambient title sparkles
        self.particles = ParticlePool(100)
        self._particle_timer = 0.0

        # Fade-in animation
        self._fade_alpha = 255  # starts fully black
        self._fade_speed = 510.0  # alpha units per second (0.5s fade)

        # Title glow animation
        self._glow_time = 0.0

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered Main Menu")
        self._fade_alpha = 255

        button_width = 300
        button_height = 60
        button_x = (WINDOW_WIDTH - button_width) // 2
        start_y = WINDOW_HEIGHT // 2
        spacing = 70

        self.new_game_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y, button_width, button_height),
            text="New Game",
            manager=self.ui_manager,
        )

        self.continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing, button_width, button_height),
            text="Continue",
            manager=self.ui_manager,
        )
        # Enable Continue only if saves exist
        most_recent = self.save_manager.get_most_recent_save_slot()
        if most_recent is None:
            self.continue_button.disable()

        self.load_game_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 2, button_width, button_height),
            text="Load Game",
            manager=self.ui_manager,
        )

        self.exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 3, button_width, button_height),
            text="Exit",
            manager=self.ui_manager,
        )

    def on_exit(self) -> None:
        super().on_exit()
        for btn in [
            self.new_game_button,
            self.continue_button,
            self.load_game_button,
            self.exit_button,
        ]:
            if btn:
                btn.kill()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.new_game_button:
                logger.info("New Game button pressed")
                self.next_state = GameState.GALAXY_MAP
            elif event.ui_element == self.continue_button:
                logger.info("Continue button pressed")
                self.next_state = "continue"
            elif event.ui_element == self.load_game_button:
                logger.info("Load Game button pressed")
                self.next_state = "load_game"
            elif event.ui_element == self.exit_button:
                logger.info("Exit button pressed")
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt

        # Fade in
        if self._fade_alpha > 0:
            self._fade_alpha = max(0, self._fade_alpha - self._fade_speed * dt)

        # Emit ambient particles behind title area
        self._particle_timer += dt
        if self._particle_timer > 0.15:
            self._particle_timer = 0.0
            import random

            x = WINDOW_WIDTH // 2 + random.randint(-200, 200)
            y = WINDOW_HEIGHT // 4 + random.randint(-30, 30)
            self.particles.emit(x, y, STAR_TWINKLE)

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)

        # Particles behind title
        self.particles.render(screen)

        # Title glow (blurred duplicate behind)
        title_y = WINDOW_HEIGHT // 4
        glow_alpha = int(80 + 40 * math.sin(self._glow_time * 2))
        glow_surf = self.title_font.render("SPACE TRADER", True, Colors.GLOW_BLUE)
        glow_surf.set_alpha(glow_alpha)
        glow_rect = glow_surf.get_rect(center=(WINDOW_WIDTH // 2, title_y))
        screen.blit(glow_surf, (glow_rect.x - 2, glow_rect.y + 2))

        # Crisp title on top
        title_text = self.title_font.render("SPACE TRADER", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, title_y))
        screen.blit(title_text, title_rect)

        # Subtitle
        subtitle_text = self.subtitle_font.render(
            "A Narrative-Driven Space Trading RPG", True, Colors.TEXT
        )
        subtitle_rect = subtitle_text.get_rect(center=(WINDOW_WIDTH // 2, title_y + 80))
        screen.blit(subtitle_text, subtitle_rect)

        # Fade-in overlay
        if self._fade_alpha > 0:
            fade_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(int(self._fade_alpha))
            screen.blit(fade_surf, (0, 0))

    def get_next_state(self) -> Optional[Union[GameState, str]]:
        """Return the requested next state."""
        return self.next_state
