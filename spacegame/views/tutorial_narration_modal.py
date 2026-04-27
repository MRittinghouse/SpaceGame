"""Tutorial narration modal — PT-N.

Phase-transition narration overlay for the tutorial ship builder. Built
as a subclass of FirstTimeTipOverlay (PT-M) so we inherit the fade-in,
modal event capture, and dismiss callback infrastructure. Differences:

  - Speaker label at top (e.g., "MECHANIC") — this is in-world narration,
    not an out-of-world UI tip, so voice attribution matters.
  - Larger panel to host multi-sentence narration (4-6 sentences typical).
  - "Continue" button copy instead of "Got it." — signals progression, not
    acknowledgment of a UI hint.

Rendered via render_top so it sits above pygame_gui elements.
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from spacegame.config import Colors, WINDOW_HEIGHT, WINDOW_WIDTH, scale_x, scale_y
from spacegame.engine.draw_utils import draw_panel, word_wrap
from spacegame.engine.fonts import FONT_XS, get_font
from spacegame.views.first_time_tip import FADE_IN_DURATION, FirstTimeTipOverlay


class TutorialNarrationModal(FirstTimeTipOverlay):
    """Phase-transition narration modal with a speaker attribution."""

    def __init__(
        self,
        speaker: str,
        title: str,
        body: str,
        on_dismiss: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(title=title, body=body, on_dismiss=on_dismiss)
        self.speaker = speaker

        # Larger panel for narration — 4-6 sentence bodies are common.
        self._panel_w = scale_x(620)
        self._panel_h = scale_y(260)
        self._panel_x = (WINDOW_WIDTH - self._panel_w) // 2
        # Slightly above vertical center so the narration reads as a
        # header beat, not a blocking popup.
        self._panel_y = (WINDOW_HEIGHT - self._panel_h) // 2 + scale_y(20)

        # Rebuild the button rect against the new panel bounds.
        # Bottom margin reserves room for the "Enter / Space / Esc"
        # keyboard hint rendered below the button — without that
        # reservation the hint clamps up into the button label.
        btn_w = scale_x(140)
        btn_h = scale_y(34)
        hint_reserve = scale_y(20)  # hint glyphs (~14px) + 6px breathing room
        self._btn_rect = pygame.Rect(
            self._panel_x + (self._panel_w - btn_w) // 2,
            self._panel_y + self._panel_h - btn_h - scale_y(14) - hint_reserve,
            btn_w,
            btn_h,
        )

        self._speaker_font: Optional[pygame.font.Font] = None

    def _ensure_fonts(self) -> None:
        super()._ensure_fonts()
        if self._speaker_font is None:
            self._speaker_font = get_font("label", FONT_XS)

    def render(self, screen: pygame.Surface) -> None:
        """Render the narration modal. Skips work once dismissed."""
        if self.dismissed:
            return
        self._ensure_fonts()

        if FADE_IN_DURATION <= 0:
            progress = 1.0
        else:
            progress = max(0.0, min(1.0, 1.0 - (self._fade_timer / FADE_IN_DURATION)))
        text_alpha = int(255 * progress)

        # Backdrop dim — slightly stronger than FirstTimeTipOverlay because
        # narration is more prominent than a UI tip.
        backdrop = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, int(120 * progress)))
        screen.blit(backdrop, (0, 0))

        # Panel chrome
        draw_panel(
            screen,
            (self._panel_x, self._panel_y, self._panel_w, self._panel_h),
            alpha=int(240 * progress),
        )

        # Left accent stripe
        stripe_w = scale_x(4)
        pygame.draw.rect(
            screen,
            Colors.TEXT_HIGHLIGHT,
            (self._panel_x, self._panel_y, stripe_w, self._panel_h),
        )

        # Content padding
        pad_x = scale_x(20)
        pad_y = scale_y(14)
        content_x = self._panel_x + stripe_w + pad_x
        content_y = self._panel_y + pad_y
        content_w = self._panel_w - stripe_w - pad_x * 2

        # Speaker label — small caps, subtle
        assert self._speaker_font is not None
        speaker_surf = self._speaker_font.render(self.speaker.upper(), True, Colors.TEXT_SECONDARY)
        speaker_surf.set_alpha(text_alpha)
        screen.blit(speaker_surf, (content_x, content_y))

        # Title below speaker
        assert self._title_font is not None
        title_y = content_y + speaker_surf.get_height() + scale_y(2)
        title_surf = self._title_font.render(self.title, True, Colors.TEXT_HIGHLIGHT)
        title_surf.set_alpha(text_alpha)
        screen.blit(title_surf, (content_x, title_y))

        # Body — word-wrapped
        assert self._body_font is not None
        body_y = title_y + title_surf.get_height() + scale_y(10)
        lines = word_wrap(self.body, self._body_font, content_w)
        line_h = self._body_font.get_linesize()
        for i, line in enumerate(lines):
            line_surf = self._body_font.render(line, True, Colors.TEXT_PRIMARY)
            line_surf.set_alpha(text_alpha)
            screen.blit(line_surf, (content_x, body_y + i * line_h))

        # Continue button
        btn_bg = (40, 50, 65) if self._btn_hovered else (25, 32, 44)
        pygame.draw.rect(screen, btn_bg, self._btn_rect)
        pygame.draw.rect(screen, Colors.UI_BORDER, self._btn_rect, 1)
        assert self._button_font is not None
        btn_label = self._button_font.render("Continue", True, Colors.TEXT_PRIMARY)
        btn_label.set_alpha(text_alpha)
        lbl_rect = btn_label.get_rect(center=self._btn_rect.center)
        screen.blit(btn_label, lbl_rect)

        # Keyboard hint below button. The button's bottom margin in
        # __init__ reserves space for this — no clamp needed.
        hint_surf = self._button_font.render("Enter / Space / Esc", True, Colors.TEXT_SECONDARY)
        hint_surf.set_alpha(int(text_alpha * 0.7))
        hint_rect = hint_surf.get_rect(
            centerx=self._btn_rect.centerx,
            top=self._btn_rect.bottom + scale_y(4),
        )
        screen.blit(hint_surf, hint_rect)
