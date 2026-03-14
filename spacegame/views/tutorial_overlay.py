"""
Tutorial overlay rendered on top of the current view.

Lightweight overlay (not a full BaseView) — renders semi-transparent background
with a dialog panel showing step title, description, and navigation buttons.
Uses manual rendering (not pygame_gui) so it draws entirely on top of the UI
manager layer, ensuring it is never buried beneath other views.
"""

import pygame
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors
from spacegame.engine.fonts import FontCache
from spacegame.tutorial_manager import TutorialManager, TUTORIAL_STEPS
from spacegame.utils.logger import logger


class _Button:
    """Simple manually-rendered button for the tutorial overlay."""

    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Update hover state from current mouse position."""
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        """Draw the button."""
        bg_color = (60, 70, 110) if self.hovered else (35, 42, 70)
        border_color = Colors.TEXT_HIGHLIGHT if self.hovered else Colors.UI_BORDER

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=4)

        text_surf = self.font.render(self.text, True, Colors.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        """Check if this button was clicked by the given event."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class TutorialOverlay:
    """Tutorial step overlay rendered on top of the active game view."""

    PANEL_WIDTH = 550
    PANEL_HEIGHT = 320

    def __init__(self, tutorial_manager: TutorialManager):
        self.tutorial_manager = tutorial_manager
        self.active = False

        # Fonts
        self.title_font = FontCache.get(36)
        self.body_font = FontCache.get(22)
        self.step_font = FontCache.get(18)
        self.btn_font = FontCache.get(24)

        # Panel geometry (computed once)
        self.panel_x = (WINDOW_WIDTH - self.PANEL_WIDTH) // 2
        self.panel_y = (WINDOW_HEIGHT - self.PANEL_HEIGHT) // 2

        # Buttons (manual, not pygame_gui)
        btn_y = self.panel_y + self.PANEL_HEIGHT - 60
        self.next_button = _Button(
            pygame.Rect(self.panel_x + self.PANEL_WIDTH - 170, btn_y, 150, 40),
            "NEXT",
            self.btn_font,
        )
        self.skip_button = _Button(
            pygame.Rect(self.panel_x + 20, btn_y, 150, 40),
            "SKIP TUTORIAL",
            self.btn_font,
        )

        # Pre-render the dim overlay surface once
        self._dim_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._dim_surface.fill((0, 0, 0, 160))

    def show(self) -> None:
        """Show the tutorial overlay with current step."""
        if self.active:
            return
        self.active = True
        logger.info(f"Tutorial step {self.tutorial_manager.current_step} shown")

    def hide(self) -> None:
        """Hide the tutorial overlay."""
        self.active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events. Returns True if the event was consumed."""
        if not self.active:
            return False

        if self.next_button.was_clicked(event):
            logger.info("Tutorial: Next clicked")
            self.hide()
            self.tutorial_manager.advance_step()
            return True

        if self.skip_button.was_clicked(event):
            logger.info("Tutorial: Skip clicked")
            self.hide()
            self.tutorial_manager.skip_tutorial()
            return True

        # Consume all mouse clicks so they don't leak through to the view below
        if event.type == pygame.MOUSEBUTTONDOWN:
            return True

        return False

    def render(self, screen: pygame.Surface) -> None:
        """Render the tutorial overlay on top of everything, including pygame_gui."""
        if not self.active:
            return

        step = self.tutorial_manager.get_current_step()
        if not step:
            return

        # Update hover state
        mouse_pos = pygame.mouse.get_pos()
        self.next_button.update_hover(mouse_pos)
        self.skip_button.update_hover(mouse_pos)

        # Full-screen dim overlay — covers the entire screen including UI elements
        screen.blit(self._dim_surface, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.PANEL_WIDTH, self.PANEL_HEIGHT)
        panel_surf = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT), pygame.SRCALPHA)
        panel_surf.fill((*Colors.PANEL, 240))
        screen.blit(panel_surf, (self.panel_x, self.panel_y))

        # Border
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, panel_rect, 2)

        # Step indicator
        total_steps = len(TUTORIAL_STEPS)
        step_text = f"Step {step['id'] + 1}/{total_steps}"
        step_surf = self.step_font.render(step_text, True, Colors.TEXT_SECONDARY)
        step_rect = step_surf.get_rect(
            topright=(self.panel_x + self.PANEL_WIDTH - 15, self.panel_y + 10)
        )
        screen.blit(step_surf, step_rect)

        # Title
        title_surf = self.title_font.render(step["title"], True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_surf.get_rect(midtop=(WINDOW_WIDTH // 2, self.panel_y + 20))
        screen.blit(title_surf, title_rect)

        # Description (word-wrapped)
        self._render_wrapped_text(
            screen,
            step["description"],
            self.panel_x + 25,
            self.panel_y + 65,
            self.PANEL_WIDTH - 50,
        )

        # Buttons
        self.next_button.render(screen)
        self.skip_button.render(screen)

    def _render_wrapped_text(
        self, screen: pygame.Surface, text: str, x: int, y: int, max_width: int
    ) -> None:
        """Render multi-line text with simple word wrapping."""
        lines = text.split("\n")
        current_y = y

        for line in lines:
            if not line.strip():
                current_y += 10
                continue

            words = line.split(" ")
            current_line = ""

            for word in words:
                test_line = f"{current_line} {word}".strip()
                test_surf = self.body_font.render(test_line, True, Colors.TEXT_PRIMARY)
                if test_surf.get_width() > max_width and current_line:
                    surf = self.body_font.render(current_line, True, Colors.TEXT_PRIMARY)
                    screen.blit(surf, (x, current_y))
                    current_y += 22
                    current_line = word
                else:
                    current_line = test_line

            if current_line:
                surf = self.body_font.render(current_line, True, Colors.TEXT_PRIMARY)
                screen.blit(surf, (x, current_y))
                current_y += 22
