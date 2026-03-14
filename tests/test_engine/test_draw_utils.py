"""Tests for draw_utils — shared UI drawing functions."""

import pygame
import pytest

from spacegame.config import Colors
from spacegame.engine.draw_utils import (
    draw_bar, draw_panel, draw_nine_slice_panel, draw_summary_overlay, word_wrap,
    _make_nine_slice_pieces, _get_nine_slice, SLICE,
)
from spacegame.engine.fonts import FontCache


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    """Ensure pygame is initialized for rendering tests."""
    pygame.init()


@pytest.fixture()
def screen() -> pygame.Surface:
    return pygame.Surface((800, 600))


class TestDrawBar:
    """draw_bar renders a progress bar with fill, edge, border, and value text."""

    def test_renders_without_error(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 50, 100, Colors.GREEN)

    def test_zero_max_no_crash(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 0, 0, Colors.GREEN)

    def test_over_max_clamped(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 150, 100, Colors.GREEN)

    def test_zero_current(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 0, 100, Colors.GREEN)

    def test_full_bar(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 100, 100, Colors.GREEN)

    def test_with_label(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 50, 100, Colors.GREEN, label="HP")

    def test_no_value_text(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, 50, 100, Colors.GREEN, show_value=False)

    def test_custom_font(self, screen: pygame.Surface) -> None:
        font = FontCache.get(16)
        draw_bar(screen, 10, 10, 200, 20, 50, 100, Colors.GREEN, font=font)

    def test_negative_current_clamped(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 200, 20, -10, 100, Colors.GREEN)

    def test_very_small_bar(self, screen: pygame.Surface) -> None:
        draw_bar(screen, 10, 10, 20, 8, 5, 10, Colors.GREEN)

    def test_tiny_fill_no_edge(self, screen: pygame.Surface) -> None:
        """Fill width < 3 should skip the leading edge highlight."""
        draw_bar(screen, 10, 10, 200, 20, 1, 100, Colors.GREEN)


class TestDrawPanel:
    """draw_panel renders a semi-transparent panel with border."""

    def test_renders_without_error(self, screen: pygame.Surface) -> None:
        draw_panel(screen, pygame.Rect(10, 10, 200, 100))

    def test_custom_colors(self, screen: pygame.Surface) -> None:
        draw_panel(
            screen,
            pygame.Rect(10, 10, 200, 100),
            bg_color=(30, 30, 50),
            border_color=(100, 100, 150),
        )

    def test_custom_alpha(self, screen: pygame.Surface) -> None:
        draw_panel(screen, pygame.Rect(10, 10, 200, 100), alpha=128)

    def test_no_border(self, screen: pygame.Surface) -> None:
        draw_panel(screen, pygame.Rect(10, 10, 200, 100), border_color=None)

    def test_border_radius(self, screen: pygame.Surface) -> None:
        draw_panel(screen, pygame.Rect(10, 10, 200, 100), border_radius=8)

    def test_tuple_rect(self, screen: pygame.Surface) -> None:
        """Should accept plain tuple as rect."""
        draw_panel(screen, (10, 10, 200, 100))  # type: ignore[arg-type]

    def test_full_opacity(self, screen: pygame.Surface) -> None:
        draw_panel(screen, pygame.Rect(10, 10, 200, 100), alpha=255)

    def test_zero_size(self, screen: pygame.Surface) -> None:
        draw_panel(screen, pygame.Rect(10, 10, 0, 0))


class TestNineSlice:
    """9-slice panel rendering produces correct surfaces."""

    def test_pieces_generated(self) -> None:
        pieces = _make_nine_slice_pieces((60, 70, 100), (15, 20, 35), 200)
        expected_keys = {"tl", "tr", "bl", "br", "top", "bot", "left", "right", "center"}
        assert set(pieces.keys()) == expected_keys

    def test_corner_sizes(self) -> None:
        pieces = _make_nine_slice_pieces((60, 70, 100), (15, 20, 35), 200)
        for key in ["tl", "tr", "bl", "br"]:
            assert pieces[key].get_size() == (SLICE, SLICE), f"{key} wrong size"

    def test_edge_sizes(self) -> None:
        pieces = _make_nine_slice_pieces((60, 70, 100), (15, 20, 35), 200)
        assert pieces["top"].get_size() == (1, SLICE)
        assert pieces["bot"].get_size() == (1, SLICE)
        assert pieces["left"].get_size() == (SLICE, 1)
        assert pieces["right"].get_size() == (SLICE, 1)

    def test_center_size(self) -> None:
        pieces = _make_nine_slice_pieces((60, 70, 100), (15, 20, 35), 200)
        assert pieces["center"].get_size() == (1, 1)

    def test_cache_returns_same_instance(self) -> None:
        a = _get_nine_slice((60, 70, 100), (15, 20, 35), 200)
        b = _get_nine_slice((60, 70, 100), (15, 20, 35), 200)
        assert a is b

    def test_cache_different_colors(self) -> None:
        a = _get_nine_slice((60, 70, 100), (15, 20, 35), 200)
        b = _get_nine_slice((100, 100, 150), (30, 30, 50), 200)
        assert a is not b

    def test_draw_nine_slice_panel(self, screen: pygame.Surface) -> None:
        draw_nine_slice_panel(screen, pygame.Rect(10, 10, 200, 100))

    def test_draw_nine_slice_small_panel(self, screen: pygame.Surface) -> None:
        """Panel smaller than 2*SLICE falls back to simple fill."""
        draw_nine_slice_panel(screen, pygame.Rect(10, 10, 6, 6))

    def test_draw_nine_slice_custom_colors(self, screen: pygame.Surface) -> None:
        draw_nine_slice_panel(
            screen, pygame.Rect(10, 10, 300, 200),
            bg_color=(30, 30, 50), border_color=(100, 100, 150), alpha=180,
        )

    def test_draw_panel_uses_nine_slice(self, screen: pygame.Surface) -> None:
        """draw_panel with border should render without error (now uses 9-slice)."""
        draw_panel(screen, pygame.Rect(10, 10, 200, 100))

    def test_corners_have_border_pixels(self) -> None:
        """Corner pieces should have outer border pixels set."""
        border = (60, 70, 100)
        pieces = _make_nine_slice_pieces(border, (15, 20, 35), 255)
        tl = pieces["tl"]
        # Top-left pixel of TL corner should be the border color
        px = tl.get_at((0, 0))
        assert (px.r, px.g, px.b) == border


class TestWordWrap:
    """word_wrap splits text into lines fitting within max_width."""

    def _font(self) -> pygame.font.Font:
        return FontCache.get(20)

    def test_short_text_single_line(self) -> None:
        lines = word_wrap("Hello", self._font(), 400)
        assert lines == ["Hello"]

    def test_empty_string(self) -> None:
        lines = word_wrap("", self._font(), 400)
        assert lines == []

    def test_splits_long_text(self) -> None:
        long_text = "This is a fairly long sentence that should wrap across multiple lines"
        lines = word_wrap(long_text, self._font(), 150)
        assert len(lines) > 1
        # All original words should be present
        all_words = " ".join(lines).split()
        assert all_words == long_text.split()

    def test_single_long_word(self) -> None:
        """A single word wider than max_width should still appear."""
        lines = word_wrap("Supercalifragilisticexpialidocious", self._font(), 50)
        assert len(lines) >= 1

    def test_respects_max_width(self) -> None:
        font = self._font()
        text = "The quick brown fox jumps over the lazy dog"
        lines = word_wrap(text, font, 200)
        for line in lines:
            # Allow single-word overflow, but multi-word lines should fit
            if " " in line:
                assert font.size(line)[0] <= 200 + 5  # small tolerance

    def test_preserves_word_order(self) -> None:
        text = "One two three four five"
        lines = word_wrap(text, self._font(), 100)
        rejoined = " ".join(lines)
        assert rejoined == text

    def test_newlines_create_breaks(self) -> None:
        text = "Line one\nLine two"
        lines = word_wrap(text, self._font(), 400)
        assert "Line one" in lines
        assert "Line two" in lines


class TestDrawSummaryOverlay:
    """draw_summary_overlay renders a mini-game completion summary."""

    def test_renders_without_error(self, screen: pygame.Surface) -> None:
        draw_summary_overlay(
            screen,
            title="TEST COMPLETE",
            stats=[("Rocks Mined", "5"), ("Total Ore", "42")],
            xp_earned=100,
            rating_letter="A",
            rating_color=Colors.GREEN,
        )

    def test_empty_stats(self, screen: pygame.Surface) -> None:
        """Should render cleanly with no stats rows."""
        draw_summary_overlay(
            screen,
            title="EMPTY SESSION",
            stats=[],
            xp_earned=0,
            rating_letter="C",
            rating_color=Colors.TEXT_SECONDARY,
        )

    def test_many_stats(self, screen: pygame.Surface) -> None:
        """Should handle a large number of stat rows without crashing."""
        stats = [(f"Stat {i}", str(i * 10)) for i in range(10)]
        draw_summary_overlay(
            screen,
            title="LOTS OF STATS",
            stats=stats,
            xp_earned=999,
            rating_letter="S",
            rating_color=Colors.YELLOW,
        )

    def test_custom_panel_size(self, screen: pygame.Surface) -> None:
        draw_summary_overlay(
            screen,
            title="SALVAGE COMPLETE",
            stats=[("Items", "3")],
            xp_earned=50,
            rating_letter="B",
            rating_color=Colors.BLUE,
            panel_width=600,
            panel_height=500,
        )

    def test_small_screen(self) -> None:
        """Should render on a small surface without crashing."""
        small = pygame.Surface((400, 300))
        draw_summary_overlay(
            small,
            title="MINI",
            stats=[("A", "1")],
            xp_earned=10,
            rating_letter="D",
            rating_color=Colors.RED,
            panel_width=300,
            panel_height=250,
        )

    def test_zero_xp(self, screen: pygame.Surface) -> None:
        draw_summary_overlay(
            screen,
            title="NO XP",
            stats=[("Score", "0")],
            xp_earned=0,
            rating_letter="F",
            rating_color=Colors.RED,
        )
