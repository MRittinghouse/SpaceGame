"""
Simple startup/test view.

This is a temporary view to test the game engine. Shows a simple
message and responds to input.
"""

import pygame
from spacegame.views.base_view import BaseView
from spacegame.config import Colors, WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.engine.fonts import FontCache, FONT_HEADING, FONT_RATING
from spacegame.utils.logger import logger


class StartupView(BaseView):
    """
    Simple test view that demonstrates rendering and input handling.

    This will be replaced with a proper main menu later.
    """

    def __init__(self) -> None:
        """Initialize the startup view."""
        super().__init__()

        # Create a default font
        self.font_large = FontCache.get(FONT_RATING)
        self.font_small = FontCache.get(FONT_HEADING)

        # Track mouse position for interaction demo
        self.mouse_pos = (0, 0)
        self.click_count = 0

    def on_enter(self) -> None:
        """Called when this view becomes active."""
        super().on_enter()
        logger.info("Entered StartupView")

    def update(self, dt: float) -> None:
        """
        Update logic (currently minimal).

        Args:
            dt: Delta time in seconds
        """
        # Nothing to update yet
        pass

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the startup screen.

        Args:
            screen: Surface to render to
        """
        # Clear background (already done in main loop, but showing here for clarity)
        # screen.fill(Colors.BACKGROUND)

        # Title text
        title_text = self.font_large.render("SPACE TRADER", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 3))
        screen.blit(title_text, title_rect)

        # Subtitle
        subtitle_text = self.font_small.render(
            "PyGame Foundation Test", True, Colors.TEXT_SECONDARY
        )
        subtitle_rect = subtitle_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        screen.blit(subtitle_text, subtitle_rect)

        # Instructions
        instructions = self.font_small.render(
            "Click anywhere or press ESC to quit", True, Colors.TEXT_PRIMARY
        )
        instructions_rect = instructions.get_rect(
            center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50)
        )
        screen.blit(instructions, instructions_rect)

        # Show mouse position
        mouse_text = self.font_small.render(
            f"Mouse: {self.mouse_pos} | Clicks: {self.click_count}", True, Colors.GREEN
        )
        mouse_rect = mouse_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 100))
        screen.blit(mouse_text, mouse_rect)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle input events.

        Args:
            event: Pygame event to process
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                logger.info("ESC pressed - quitting")
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.click_count += 1
            logger.debug(f"Mouse clicked at {event.pos}, total clicks: {self.click_count}")
