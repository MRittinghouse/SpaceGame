"""First-time tip overlay — PT-M training wheels infrastructure.

Short, one-time modal shown when the player enters a view for the first
time. Brief explanation of the view's purpose, dismissible with click or
Enter/Space/Escape. State tracked per-tip-id by the caller via
dialogue_flags.

Design (from requirements/onboarding_design.md):
  - 1-3 sentences, declarative
  - Not in-world voice, not corporate — just clean
  - Dismiss button reads "Got it."
  - Never re-fires once dismissed

This overlay is presentation-only; the caller owns the flag read (on entry)
and write (via on_dismiss callback) so literal flag strings live in view
code where the dialogue-integrity scanner can see them.
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, scale_x, scale_y
from spacegame.engine.draw_utils import draw_panel, word_wrap
from spacegame.engine.fonts import FONT_MD, FONT_SM, get_font

# 250ms fade-in. Short enough that the player isn't waiting, long enough
# that the overlay feels composed instead of popped.
FADE_IN_DURATION = 0.25


class FirstTimeTipOverlay:
    """One-time modal tip shown above pygame_gui elements via render_top."""

    def __init__(
        self,
        title: str,
        body: str,
        on_dismiss: Optional[Callable[[], None]] = None,
    ) -> None:
        """Build the overlay.

        Args:
            title: Header text. Short — one or two words typical.
            body: Declarative body. 1-3 sentences. Auto word-wrapped.
            on_dismiss: Called once when the player dismisses the tip.
                Typically used to persist "seen" state via dialogue_flags.
        """
        self.title = title
        self.body = body
        self.on_dismiss = on_dismiss
        self.dismissed = False
        self._fade_timer = FADE_IN_DURATION

        # Panel geometry — sized for a 2-3 sentence body plus title + button.
        self._panel_w = scale_x(520)
        self._panel_h = scale_y(200)
        self._panel_x = (WINDOW_WIDTH - self._panel_w) // 2
        # Offset downward from center so the view's header area stays visible.
        self._panel_y = (WINDOW_HEIGHT - self._panel_h) // 2 + scale_y(40)

        # Bottom margin reserves room for the "Enter / Space / Esc"
        # keyboard hint rendered below the button — without that
        # reservation the hint clamps up into the button label.
        btn_w = scale_x(120)
        btn_h = scale_y(32)
        hint_reserve = scale_y(20)  # hint glyphs (~14px) + 6px breathing room
        self._btn_rect = pygame.Rect(
            self._panel_x + (self._panel_w - btn_w) // 2,
            self._panel_y + self._panel_h - btn_h - scale_y(14) - hint_reserve,
            btn_w,
            btn_h,
        )
        self._btn_hovered = False

        # Fonts are lazy-created — pygame.font must be initialized before
        # a font can be constructed, and this class may be imported at
        # module load time before display init.
        self._title_font: Optional[pygame.font.Font] = None
        self._body_font: Optional[pygame.font.Font] = None
        self._button_font: Optional[pygame.font.Font] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Tick the fade-in timer. No-op once fade completes."""
        if self._fade_timer > 0:
            self._fade_timer = max(0.0, self._fade_timer - dt)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process an event and return whether it was consumed.

        Modal semantics: while active, the overlay consumes mouse clicks
        and key presses so they don't leak to the view behind. Returns
        False (passes through) once dismissed.
        """
        if self.dismissed:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._btn_hovered = self._btn_rect.collidepoint(event.pos)
            return False  # Hover doesn't consume — mouse still needs to move UI
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_rect.collidepoint(event.pos):
                self._dismiss()
            # Consume even if the click missed the button — clicks while a
            # modal is up belong to the modal, not the view behind.
            return True
        if event.type == pygame.KEYDOWN:
            if event.key in (
                pygame.K_ESCAPE,
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_SPACE,
            ):
                self._dismiss()
            return True  # Modal eats all keydowns
        return False

    def _dismiss(self) -> None:
        """Mark dismissed and fire the on_dismiss callback exactly once."""
        if self.dismissed:
            return
        self.dismissed = True
        if self.on_dismiss is not None:
            self.on_dismiss()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._title_font is None:
            self._title_font = get_font("header", FONT_MD)
        if self._body_font is None:
            self._body_font = get_font("dialogue", FONT_SM)
        if self._button_font is None:
            self._button_font = get_font("dialogue", FONT_SM)

    def render(self, screen: pygame.Surface) -> None:
        """Render the overlay. Skips work once dismissed."""
        if self.dismissed:
            return
        self._ensure_fonts()

        # Fade progress: 0 → 1 over FADE_IN_DURATION
        if FADE_IN_DURATION <= 0:
            progress = 1.0
        else:
            progress = max(0.0, min(1.0, 1.0 - (self._fade_timer / FADE_IN_DURATION)))
        text_alpha = int(255 * progress)

        # Backdrop dim — subtle so the view behind remains visible
        backdrop = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, int(100 * progress)))
        screen.blit(backdrop, (0, 0))

        # Panel
        draw_panel(
            screen,
            (self._panel_x, self._panel_y, self._panel_w, self._panel_h),
            alpha=int(230 * progress),
        )

        # Left accent stripe — distinguishes "tip" from other modal chrome
        stripe_w = scale_x(4)
        pygame.draw.rect(
            screen,
            Colors.TEXT_HIGHLIGHT,
            (self._panel_x, self._panel_y, stripe_w, self._panel_h),
        )

        # Content padding
        pad_x = scale_x(18)
        pad_y = scale_y(14)
        content_x = self._panel_x + stripe_w + pad_x
        content_y = self._panel_y + pad_y
        content_w = self._panel_w - stripe_w - pad_x * 2

        # Title
        assert self._title_font is not None
        title_surf = self._title_font.render(self.title, True, Colors.TEXT_HIGHLIGHT)
        title_surf.set_alpha(text_alpha)
        screen.blit(title_surf, (content_x, content_y))

        # Body — word-wrapped
        assert self._body_font is not None
        body_y = content_y + title_surf.get_height() + scale_y(8)
        lines = word_wrap(self.body, self._body_font, content_w)
        line_h = self._body_font.get_linesize()
        for i, line in enumerate(lines):
            line_surf = self._body_font.render(line, True, Colors.TEXT_PRIMARY)
            line_surf.set_alpha(text_alpha)
            screen.blit(line_surf, (content_x, body_y + i * line_h))

        # Dismiss button — custom rendered (not pygame_gui) so it lives
        # in render_top and doesn't pollute the UIManager's element list.
        btn_bg = (40, 50, 65) if self._btn_hovered else (25, 32, 44)
        pygame.draw.rect(screen, btn_bg, self._btn_rect)
        pygame.draw.rect(screen, Colors.UI_BORDER, self._btn_rect, 1)
        assert self._button_font is not None
        btn_label = self._button_font.render("Got it.", True, Colors.TEXT_PRIMARY)
        btn_label.set_alpha(text_alpha)
        lbl_rect = btn_label.get_rect(center=self._btn_rect.center)
        screen.blit(btn_label, lbl_rect)

        # Keyboard hint below button, subtle
        hint_surf = self._button_font.render(
            "Enter / Space / Esc",
            True,
            Colors.TEXT_SECONDARY,
        )
        hint_surf.set_alpha(int(text_alpha * 0.7))
        hint_rect = hint_surf.get_rect(
            centerx=self._btn_rect.centerx,
            top=self._btn_rect.bottom + scale_y(4),
        )
        # The button's bottom margin in __init__ reserves space for this —
        # no clamp needed.
        screen.blit(hint_surf, hint_rect)
