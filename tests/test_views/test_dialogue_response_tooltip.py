"""Tests for NV-0.5 — long-response tooltip in dialogue view.

Response buttons are fixed-height and character-truncate long text with
a styled ``…`` indicator. When the player hovers a truncated button,
``DialogueView`` draws a tooltip near the button with the full wrapped
text. This module verifies:

  - Truncation detection on ``_ResponseButton``.
  - Tooltip geometry picks sensible positions (right of the button by
    default, flips left if the right-side panel would clip, clamps to
    screen edges as a last resort).
  - Tooltip fires only for the hovered truncated button.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _font() -> pygame.font.Font:
    return pygame.font.Font(None, 20)


# ---------------------------------------------------------------------------
# _ResponseButton truncation detection
# ---------------------------------------------------------------------------


class TestResponseButtonTruncation:
    def test_short_text_is_not_truncated(self) -> None:
        from spacegame.views.dialogue_view import _ResponseButton

        rect = pygame.Rect(0, 0, 400, 36)
        btn = _ResponseButton(rect, "Short.", _font())
        assert btn.is_truncated is False

    def test_very_long_text_is_truncated(self) -> None:
        from spacegame.views.dialogue_view import _ResponseButton

        rect = pygame.Rect(0, 0, 400, 36)
        long = (
            "You've run convoys for ten years. You know the difference between "
            "bad luck and inside information. You've already decided which this is."
        )
        btn = _ResponseButton(rect, long, _font())
        assert btn.is_truncated is True

    def test_exact_fit_text_is_not_truncated(self) -> None:
        from spacegame.views.dialogue_view import _ResponseButton

        rect = pygame.Rect(0, 0, 400, 36)
        # Probe to find a text length that exactly fits, then use length-1.
        font = _font()
        fitting = "x"
        while True:
            surf = font.render("\u25b8 " + fitting, True, (255, 255, 255))
            if surf.get_width() >= 400 - 24:
                fitting = fitting[:-1]
                break
            fitting += "x"
        btn = _ResponseButton(rect, fitting, font)
        assert btn.is_truncated is False


# ---------------------------------------------------------------------------
# DialogueView tooltip geometry
# ---------------------------------------------------------------------------


def _make_dialogue_view_shell():
    """Instantiate DialogueView bypassing __init__ — tooltip tests don't
    need the full dialogue/social/data-loader stack."""
    from spacegame.views.dialogue_view import DialogueView

    view = DialogueView.__new__(DialogueView)
    view._response_buttons = []
    return view


def _make_button(rect: pygame.Rect, truncated: bool = True) -> object:
    """Minimal stand-in for a _ResponseButton sufficient for geometry."""
    btn = MagicMock()
    btn.rect = rect
    btn.hovered = False
    btn.is_truncated = truncated
    return btn


class TestTooltipGeometry:
    def test_default_position_is_right_of_button(self) -> None:
        view = _make_dialogue_view_shell()
        btn = _make_button(pygame.Rect(100, 300, 400, 36))
        rect = view._tooltip_rect_for_button(btn, content_w=200, content_h=60)
        # Right side: x should be button.right + TOOLTIP_GAP
        assert rect.x == btn.rect.right + view.TOOLTIP_GAP
        # Top-aligned with the button
        assert rect.y == btn.rect.y

    def test_right_side_clipping_flips_to_left(self) -> None:
        from spacegame.config import WINDOW_WIDTH

        view = _make_dialogue_view_shell()
        # Place the button near the right edge so a right-side tooltip
        # would clip.
        btn_x = WINDOW_WIDTH - 50
        btn = _make_button(pygame.Rect(btn_x, 300, 40, 36))
        rect = view._tooltip_rect_for_button(btn, content_w=400, content_h=60)
        # Tooltip should have flipped to the left side
        assert rect.right <= btn.rect.left, (
            f"expected tooltip on the left of button (right={rect.right}, "
            f"button.left={btn.rect.left})"
        )

    def test_clamps_to_screen_left_edge_as_last_resort(self) -> None:
        view = _make_dialogue_view_shell()
        # Button at far left edge, tooltip wider than button x, so left
        # flip still doesn't fit → pinned to the gap.
        btn = _make_button(pygame.Rect(10, 300, 40, 36))
        rect = view._tooltip_rect_for_button(btn, content_w=800, content_h=60)
        assert rect.x >= view.TOOLTIP_GAP

    def test_tooltip_size_includes_padding(self) -> None:
        view = _make_dialogue_view_shell()
        btn = _make_button(pygame.Rect(100, 300, 400, 36))
        rect = view._tooltip_rect_for_button(btn, content_w=200, content_h=60)
        assert rect.width == 200 + view.TOOLTIP_PADDING * 2
        assert rect.height == 60 + view.TOOLTIP_PADDING * 2


# ---------------------------------------------------------------------------
# Tooltip visibility logic
# ---------------------------------------------------------------------------


class TestTooltipVisibility:
    def test_no_hovered_button_returns_none(self) -> None:
        view = _make_dialogue_view_shell()
        b1 = _make_button(pygame.Rect(0, 0, 400, 36), truncated=True)
        b2 = _make_button(pygame.Rect(0, 40, 400, 36), truncated=True)
        view._response_buttons = [b1, b2]
        assert view._find_hovered_truncated_button() is None

    def test_hovered_but_not_truncated_returns_none(self) -> None:
        view = _make_dialogue_view_shell()
        b = _make_button(pygame.Rect(0, 0, 400, 36), truncated=False)
        b.hovered = True
        view._response_buttons = [b]
        assert view._find_hovered_truncated_button() is None

    def test_hovered_and_truncated_returns_button(self) -> None:
        view = _make_dialogue_view_shell()
        b = _make_button(pygame.Rect(0, 0, 400, 36), truncated=True)
        b.hovered = True
        view._response_buttons = [b]
        assert view._find_hovered_truncated_button() is b

    def test_returns_only_first_hovered_truncated(self) -> None:
        """Sanity — UI layer guarantees at most one hovered button, but be
        explicit."""
        view = _make_dialogue_view_shell()
        b1 = _make_button(pygame.Rect(0, 0, 400, 36), truncated=True)
        b2 = _make_button(pygame.Rect(0, 40, 400, 36), truncated=True)
        b1.hovered = True
        b2.hovered = True
        view._response_buttons = [b1, b2]
        assert view._find_hovered_truncated_button() is b1
