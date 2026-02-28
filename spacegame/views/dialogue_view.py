"""
Dialogue view for NPC conversations.

Displays NPC portrait placeholder, dialogue text with typewriter effect,
and clickable player response options.
"""

import pygame
from typing import Optional

from spacegame.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    Colors,
    GameState,
    DIALOGUE_TEXT_SPEED,
    DIALOGUE_PORTRAIT_SIZE,
)
from spacegame.views.base_view import BaseView
from spacegame.models.dialogue import DialogueManager, NPC
from spacegame.data_loader import DataLoader
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.utils.logger import logger


class _ResponseButton:
    """Manually-rendered response button for the dialogue view."""

    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Update hover state from current mouse position."""
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        """Draw the response button."""
        bg_color = (40, 50, 80) if self.hovered else (25, 32, 55)
        border_color = Colors.TEXT_HIGHLIGHT if self.hovered else Colors.UI_BORDER
        text_color = Colors.TEXT_PRIMARY if self.hovered else Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=4)

        # Arrow prefix
        prefix = "\u25b8 " if self.hovered else "  "
        text_surf = self.font.render(prefix + self.text, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 12, self.rect.centery))
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        """Check if this button was clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class DialogueView(BaseView):
    """View for NPC dialogue conversations."""

    # Layout constants
    PANEL_WIDTH = 800
    PANEL_HEIGHT = 480
    PORTRAIT_W, PORTRAIT_H = DIALOGUE_PORTRAIT_SIZE
    TEXT_LEFT_MARGIN = 150  # Left edge of text area (after portrait)
    TEXT_TOP = 80  # Top of text area within panel
    RESPONSE_TOP_OFFSET = 30  # Gap between text area and responses
    RESPONSE_HEIGHT = 36
    RESPONSE_GAP = 6

    def __init__(
        self,
        ui_manager: object,
        dialogue_manager: DialogueManager,
        data_loader: DataLoader,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.dialogue_manager = dialogue_manager
        self.data_loader = data_loader
        self.next_state: Optional[GameState] = None

        # Fonts
        self.name_font = pygame.font.Font(None, 30)
        self.title_font = pygame.font.Font(None, 22)
        self.body_font = pygame.font.Font(None, 24)
        self.response_font = pygame.font.Font(None, 22)
        self.initial_font = pygame.font.Font(None, 48)

        # Panel geometry
        self.panel_x = (WINDOW_WIDTH - self.PANEL_WIDTH) // 2
        self.panel_y = (WINDOW_HEIGHT - self.PANEL_HEIGHT) // 2

        # Background
        self.background = AnimatedBackground("dialogue", WINDOW_WIDTH, WINDOW_HEIGHT, seed=77)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

        # Typewriter state
        self._full_text = ""
        self._revealed_chars = 0
        self._text_timer = 0.0
        self._text_complete = False

        # Response buttons (created dynamically)
        self._response_buttons: list[_ResponseButton] = []

        # Current speaker NPC (for portrait/name rendering; None for narration)
        self._current_npc: Optional[NPC] = None

        # Return state when dialogue ends (configurable per dialogue)
        self._return_state: GameState = GameState.TRADING

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered dialogue view")
        self._load_current_node()

    def on_exit(self) -> None:
        super().on_exit()
        self._response_buttons.clear()

    def _load_current_node(self) -> None:
        """Load display state from the current dialogue node."""
        node = self.dialogue_manager.get_current_node()
        if not node:
            # Dialogue ended or invalid — return to trading
            self.next_state = GameState.TRADING
            return

        # Look up speaker NPC (None for narrator mode)
        if node.speaker_id == "narrator":
            self._current_npc = None
        else:
            self._current_npc = self.data_loader.get_npc(node.speaker_id)

        # Start typewriter effect
        self._full_text = node.text
        self._revealed_chars = 0
        self._text_timer = 0.0
        self._text_complete = DIALOGUE_TEXT_SPEED <= 0

        # Build response buttons (only shown when text is complete)
        self._build_response_buttons()

    def _build_response_buttons(self) -> None:
        """Create response buttons for the current node."""
        self._response_buttons.clear()
        node = self.dialogue_manager.get_current_node()
        if not node:
            return

        responses = node.responses
        if not responses:
            # Terminal node — show a "[Continue]" button to end
            responses_text = ["[Continue]"]
            is_terminal = True
        else:
            responses_text = [r.text for r in responses]
            is_terminal = False

        # Calculate vertical position for responses
        # We'll position them at the bottom portion of the panel
        text_area_bottom = self.panel_y + self.PANEL_HEIGHT - 20
        total_response_height = len(responses_text) * (self.RESPONSE_HEIGHT + self.RESPONSE_GAP)
        response_start_y = text_area_bottom - total_response_height

        btn_x = self.panel_x + 30
        btn_width = self.PANEL_WIDTH - 60

        for i, text in enumerate(responses_text):
            btn_y = response_start_y + i * (self.RESPONSE_HEIGHT + self.RESPONSE_GAP)
            rect = pygame.Rect(btn_x, btn_y, btn_width, self.RESPONSE_HEIGHT)
            btn = _ResponseButton(rect, text, self.response_font)
            self._response_buttons.append(btn)

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        # Click to reveal text instantly
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self._text_complete:
                self._revealed_chars = len(self._full_text)
                self._text_complete = True
                return

        # Response button clicks (only when text is complete)
        if self._text_complete:
            for i, btn in enumerate(self._response_buttons):
                if btn.was_clicked(event):
                    self._on_response_selected(i)
                    return

        # Consume all clicks to prevent leaking
        if event.type == pygame.MOUSEBUTTONDOWN:
            return

    def _on_response_selected(self, index: int) -> None:
        """Handle a response button click."""
        node = self.dialogue_manager.get_current_node()
        if not node:
            return

        if not node.responses:
            # Terminal node — "[Continue]" was clicked
            self.dialogue_manager.end_dialogue()
            self.next_state = self._return_state
            logger.info("Dialogue ended (terminal node)")
            return

        next_node = self.dialogue_manager.select_response(index)
        if next_node is None:
            # Dialogue ended via response
            self.next_state = self._return_state
            logger.info("Dialogue ended (end response)")
        else:
            # Advance to next node
            self._load_current_node()

    def update(self, dt: float) -> None:
        self.background.update(dt)

        # Typewriter effect
        if not self._text_complete and DIALOGUE_TEXT_SPEED > 0:
            self._text_timer += dt
            chars_to_show = int(self._text_timer * DIALOGUE_TEXT_SPEED)
            if chars_to_show >= len(self._full_text):
                self._revealed_chars = len(self._full_text)
                self._text_complete = True
            else:
                self._revealed_chars = chars_to_show

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel
        panel_surf = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT), pygame.SRCALPHA)
        panel_surf.fill((*Colors.PANEL, 230))
        screen.blit(panel_surf, (self.panel_x, self.panel_y))

        # Panel border
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.PANEL_WIDTH, self.PANEL_HEIGHT)
        pygame.draw.rect(screen, Colors.UI_BORDER, panel_rect, 2)

        if self._current_npc:
            # NPC dialogue mode
            self._render_portrait(screen)
            self._render_speaker_info(screen)
            self._render_dialogue_text(screen)
        else:
            # Narrator/monologue mode — full-width text, no portrait
            self._render_narration_text(screen)

        # Separator line above responses
        if self._text_complete:
            sep_y = self._get_response_area_top() - 12
            pygame.draw.line(
                screen,
                Colors.UI_BORDER,
                (self.panel_x + 30, sep_y),
                (self.panel_x + self.PANEL_WIDTH - 30, sep_y),
                1,
            )

        # Response buttons (only when text is fully revealed)
        if self._text_complete:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self._response_buttons:
                btn.update_hover(mouse_pos)
                btn.render(screen)

    def _render_portrait(self, screen: pygame.Surface) -> None:
        """Render the NPC portrait placeholder."""
        npc = self._current_npc
        if not npc:
            return

        px = self.panel_x + 25
        py = self.panel_y + 25

        # Colored rectangle
        portrait_rect = pygame.Rect(px, py, self.PORTRAIT_W, self.PORTRAIT_H)
        portrait_surf = pygame.Surface((self.PORTRAIT_W, self.PORTRAIT_H), pygame.SRCALPHA)
        portrait_surf.fill((*npc.portrait_color, 180))
        screen.blit(portrait_surf, (px, py))

        # Border (lighter shade)
        border_color = tuple(min(c + 60, 255) for c in npc.portrait_color)
        pygame.draw.rect(screen, border_color, portrait_rect, 2)

        # Initials centered on portrait
        initials = "".join(word[0].upper() for word in npc.name.split() if word)
        initials_surf = self.initial_font.render(initials, True, Colors.WHITE)
        initials_rect = initials_surf.get_rect(center=portrait_rect.center)
        screen.blit(initials_surf, initials_rect)

    def _render_speaker_info(self, screen: pygame.Surface) -> None:
        """Render NPC name and title next to portrait."""
        npc = self._current_npc
        if not npc:
            return

        text_x = self.panel_x + self.TEXT_LEFT_MARGIN
        name_y = self.panel_y + 28

        # Name in highlight color
        name_surf = self.name_font.render(npc.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (text_x, name_y))

        # Title in secondary color
        if npc.title:
            title_surf = self.title_font.render(npc.title, True, Colors.TEXT_SECONDARY)
            screen.blit(title_surf, (text_x, name_y + 28))

    def _render_dialogue_text(self, screen: pygame.Surface) -> None:
        """Render the dialogue text with typewriter effect."""
        text_x = self.panel_x + self.TEXT_LEFT_MARGIN
        text_y = self.panel_y + self.TEXT_TOP
        max_width = self.PANEL_WIDTH - self.TEXT_LEFT_MARGIN - 30

        # Get the revealed portion of text
        visible_text = self._full_text[: self._revealed_chars]
        if not visible_text:
            return

        self._render_wrapped_text(screen, visible_text, text_x, text_y, max_width)

    def _render_narration_text(self, screen: pygame.Surface) -> None:
        """Render narrator/monologue text — full-width, no portrait."""
        text_x = self.panel_x + 40
        text_y = self.panel_y + 50
        max_width = self.PANEL_WIDTH - 80

        visible_text = self._full_text[: self._revealed_chars]
        if not visible_text:
            return

        self._render_wrapped_text(
            screen, visible_text, text_x, text_y, max_width, Colors.TEXT_SECONDARY
        )

    def _render_wrapped_text(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_width: int,
        color: tuple[int, int, int] = Colors.TEXT_PRIMARY,
    ) -> None:
        """Render multi-line text with word wrapping."""
        lines = text.split("\n")
        current_y = y

        for line in lines:
            if not line.strip():
                current_y += 12
                continue

            words = line.split(" ")
            current_line = ""

            for word in words:
                test_line = f"{current_line} {word}".strip()
                test_surf = self.body_font.render(test_line, True, color)
                if test_surf.get_width() > max_width and current_line:
                    surf = self.body_font.render(current_line, True, color)
                    screen.blit(surf, (x, current_y))
                    current_y += 24
                    current_line = word
                else:
                    current_line = test_line

            if current_line:
                surf = self.body_font.render(current_line, True, color)
                screen.blit(surf, (x, current_y))
                current_y += 24

    def _get_response_area_top(self) -> int:
        """Get the Y coordinate where response buttons start."""
        if self._response_buttons:
            return self._response_buttons[0].rect.y
        return self.panel_y + self.PANEL_HEIGHT - 60

    def get_next_state(self) -> Optional[GameState]:
        """Return the requested next state."""
        return self.next_state
