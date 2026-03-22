"""
Tutorial overlay rendered on top of the current view.

Lightweight overlay (not a full BaseView) — renders semi-transparent background
with a dialog panel showing step title, description, and navigation buttons.
Uses manual rendering (not pygame_gui) so it draws entirely on top of the UI
manager layer, ensuring it is never buried beneath other views.
"""

from typing import Optional

import pygame
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, scale_x, scale_y
from spacegame.engine.fonts import FontCache, FONT_BODY, FONT_LG, FONT_SM, FONT_TITLE
from spacegame.tutorial_manager import TutorialManager, TUTORIAL_STEPS, MINIGAME_HINTS
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

    PANEL_WIDTH = scale_x(550)
    PANEL_HEIGHT = scale_y(320)
    HINT_PANEL_HEIGHT = scale_y(420)  # Taller panel for longer hint descriptions

    def __init__(self, tutorial_manager: TutorialManager):
        self.tutorial_manager = tutorial_manager
        self.active = False

        # Hint mode: shows a contextual hint instead of a tutorial step
        self._hint_mode: bool = False
        self._hint_data: Optional[dict] = None
        self._hint_id: Optional[str] = None

        # Fonts
        self.title_font = FontCache.get(FONT_TITLE)
        self.body_font = FontCache.get(FONT_BODY)
        self.step_font = FontCache.get(FONT_SM)
        self.btn_font = FontCache.get(FONT_LG)

        # Panel geometry — tutorial step panel (computed once)
        self.panel_x = (WINDOW_WIDTH - self.PANEL_WIDTH) // 2
        self.panel_y = (WINDOW_HEIGHT - self.PANEL_HEIGHT) // 2

        # Hint panel geometry (taller, re-centered)
        self._hint_panel_y = (WINDOW_HEIGHT - self.HINT_PANEL_HEIGHT) // 2

        # Buttons for tutorial step mode
        btn_y = self.panel_y + self.PANEL_HEIGHT - scale_y(60)
        self.next_button = _Button(
            pygame.Rect(self.panel_x + self.PANEL_WIDTH - scale_x(170), btn_y, scale_x(150), scale_y(40)),
            "NEXT",
            self.btn_font,
        )
        self.skip_button = _Button(
            pygame.Rect(self.panel_x + scale_x(20), btn_y, scale_x(150), scale_y(40)),
            "SKIP TUTORIAL",
            self.btn_font,
        )
        # "GOT IT" button for hint mode (centered, uses hint panel geometry)
        hint_btn_y = self._hint_panel_y + self.HINT_PANEL_HEIGHT - scale_y(60)
        self.got_it_button = _Button(
            pygame.Rect(
                self.panel_x + (self.PANEL_WIDTH - scale_x(150)) // 2, hint_btn_y, scale_x(150), scale_y(40)
            ),
            "GOT IT",
            self.btn_font,
        )

        # Pre-render the dim overlay surface once
        self._dim_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._dim_surface.fill((0, 0, 0, 160))

    def show(self) -> None:
        """Show the tutorial overlay with current step."""
        if self.active:
            return
        self._hint_mode = False
        self.active = True
        logger.info(f"Tutorial step {self.tutorial_manager.current_step} shown")

    def show_hint(self, hint_id: str) -> None:
        """Show a contextual mini-game hint overlay.

        Args:
            hint_id: ID of the hint (e.g., 'mining', 'salvage', 'refining').
        """
        if self.active:
            return
        # Guard: don't show if already dismissed
        if not self.tutorial_manager.should_show_hint(hint_id):
            return
        hint_data = self.tutorial_manager.get_hint(hint_id)
        if not hint_data:
            return
        self._hint_mode = True
        self._hint_data = hint_data
        self._hint_id = hint_id
        self.active = True
        logger.info(f"Mini-game hint shown: {hint_id}")

    def hide(self) -> None:
        """Hide the tutorial overlay."""
        self.active = False
        self._hint_mode = False
        self._hint_data = None
        self._hint_id = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events. Returns True if the event was consumed."""
        if not self.active:
            return False

        # Keyboard dismiss: Enter/Space/Escape work for both modes
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN,
            pygame.K_SPACE,
            pygame.K_ESCAPE,
        ):
            if self._hint_mode:
                self._dismiss_hint()
            else:
                # Enter/Space = Next, Escape = Skip
                if event.key == pygame.K_ESCAPE:
                    logger.info("Tutorial: Skip via keyboard")
                    self.hide()
                    self.tutorial_manager.skip_tutorial()
                else:
                    logger.info("Tutorial: Next via keyboard")
                    self.hide()
                    self.tutorial_manager.advance_step()
            return True

        if self._hint_mode:
            # Hint mode: GOT IT button or any click on the panel
            if self.got_it_button.was_clicked(event):
                self._dismiss_hint()
                return True
            # Also dismiss on any click inside the panel area
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                panel_rect = pygame.Rect(
                    self.panel_x, self._hint_panel_y,
                    self.PANEL_WIDTH, self.HINT_PANEL_HEIGHT,
                )
                if panel_rect.collidepoint(event.pos):
                    self._dismiss_hint()
                    return True
        else:
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

    def _dismiss_hint(self) -> None:
        """Dismiss the current hint overlay."""
        logger.info(f"Hint dismissed: {self._hint_id}")
        hint_id = self._hint_id
        self.hide()
        if hint_id:
            self.tutorial_manager.dismiss_hint(hint_id)

    def render(self, screen: pygame.Surface) -> None:
        """Render the tutorial overlay on top of everything, including pygame_gui."""
        if not self.active:
            return

        if self._hint_mode:
            self._render_hint(screen)
        else:
            self._render_tutorial_step(screen)

    def _render_hint(self, screen: pygame.Surface) -> None:
        """Render a contextual mini-game hint panel."""
        if not self._hint_data:
            return

        py = self._hint_panel_y
        ph = self.HINT_PANEL_HEIGHT

        mouse_pos = pygame.mouse.get_pos()
        self.got_it_button.update_hover(mouse_pos)

        # Full-screen dim overlay
        screen.blit(self._dim_surface, (0, 0))

        # Panel background (taller for hints)
        panel_rect = pygame.Rect(self.panel_x, py, self.PANEL_WIDTH, ph)
        panel_surf = pygame.Surface((self.PANEL_WIDTH, ph), pygame.SRCALPHA)
        panel_surf.fill((*Colors.PANEL, 240))
        screen.blit(panel_surf, (self.panel_x, py))
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, panel_rect, 2)

        # Title
        title_surf = self.title_font.render(self._hint_data["title"], True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_surf.get_rect(midtop=(WINDOW_WIDTH // 2, py + 20))
        screen.blit(title_surf, title_rect)

        # Description (word-wrapped, clamped above button)
        max_text_y = self.got_it_button.rect.top - 10
        self._render_wrapped_text(
            screen,
            self._hint_data["description"],
            self.panel_x + 25,
            py + 65,
            self.PANEL_WIDTH - 50,
            max_y=max_text_y,
        )

        # GOT IT button
        self.got_it_button.render(screen)

        # Keyboard hint below button
        hint_surf = self.step_font.render(
            "Press ENTER or click to dismiss", True, Colors.TEXT_SECONDARY
        )
        hint_rect = hint_surf.get_rect(
            midtop=(WINDOW_WIDTH // 2, self.got_it_button.rect.bottom + 6)
        )
        screen.blit(hint_surf, hint_rect)

    def _render_tutorial_step(self, screen: pygame.Surface) -> None:
        """Render a tutorial step panel."""
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
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_width: int,
        max_y: int = 0,
    ) -> None:
        """Render multi-line text with simple word wrapping.

        Args:
            screen: Surface to render on.
            text: Text to render.
            x: Left edge x position.
            y: Top y position.
            max_width: Maximum line width in pixels.
            max_y: If > 0, stop rendering lines that would start below this y.
        """
        lines = text.split("\n")
        current_y = y

        for line in lines:
            if max_y and current_y >= max_y:
                break

            if not line.strip():
                current_y += 10
                continue

            words = line.split(" ")
            current_line = ""

            for word in words:
                if max_y and current_y >= max_y:
                    break
                test_line = f"{current_line} {word}".strip()
                test_surf = self.body_font.render(test_line, True, Colors.TEXT_PRIMARY)
                if test_surf.get_width() > max_width and current_line:
                    surf = self.body_font.render(current_line, True, Colors.TEXT_PRIMARY)
                    screen.blit(surf, (x, current_y))
                    current_y += 22
                    current_line = word
                else:
                    current_line = test_line

            if current_line and (not max_y or current_y < max_y):
                surf = self.body_font.render(current_line, True, Colors.TEXT_PRIMARY)
                screen.blit(surf, (x, current_y))
                current_y += 22
