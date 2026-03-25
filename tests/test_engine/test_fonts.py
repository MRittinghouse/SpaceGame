"""Tests for FontCache — centralized font management."""

import pygame
import pytest

from spacegame.engine.fonts import (
    FontCache,
    FONT_XS,
    FONT_SM,
    FONT_MD,
    FONT_BODY,
    FONT_LG,
    FONT_XL,
    FONT_SUBTITLE,
    FONT_HEADING,
    FONT_TITLE,
    FONT_SECTION,
    FONT_DISPLAY,
    FONT_RATING,
)


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    """Ensure pygame is initialized for font tests."""
    pygame.init()


class TestFontCacheSingleton:
    """FontCache should be accessed via get(), not instantiated."""

    def test_get_returns_font(self) -> None:
        font = FontCache.get(20)
        assert isinstance(font, pygame.font.Font)

    def test_same_size_returns_same_object(self) -> None:
        f1 = FontCache.get(24)
        f2 = FontCache.get(24)
        assert f1 is f2, "Same size should return cached font object"

    def test_different_sizes_return_different_objects(self) -> None:
        f1 = FontCache.get(20)
        f2 = FontCache.get(36)
        assert f1 is not f2

    def test_none_path_explicit_and_implicit_same(self) -> None:
        f1 = FontCache.get(20)
        f2 = FontCache.get(20, path=None)
        assert f1 is f2, "Explicit None path should match implicit default"

    def test_clear_cache(self) -> None:
        f1 = FontCache.get(18)
        FontCache.clear()
        f2 = FontCache.get(18)
        assert f1 is not f2, "After clear(), should create new font object"


class TestFontSizeConstants:
    """Semantic size constants should have expected values."""

    def test_size_values(self) -> None:
        assert FONT_XS == 16
        assert FONT_SM == 18
        assert FONT_MD == 20
        assert FONT_BODY == 22
        assert FONT_LG == 24
        assert FONT_XL == 28
        assert FONT_SUBTITLE == 26
        assert FONT_HEADING == 32
        assert FONT_TITLE == 36
        assert FONT_SECTION == 40
        assert FONT_DISPLAY == 48
        assert FONT_RATING == 72

    def test_constants_are_ascending(self) -> None:
        sizes = [
            FONT_XS,
            FONT_SM,
            FONT_MD,
            FONT_BODY,
            FONT_LG,
            FONT_XL,
            FONT_HEADING,
            FONT_TITLE,
            FONT_SECTION,
            FONT_DISPLAY,
            FONT_RATING,
        ]
        assert sizes == sorted(sizes), "Size constants should be in ascending order"

    def test_all_constants_produce_valid_fonts(self) -> None:
        for size in [
            FONT_XS,
            FONT_SM,
            FONT_MD,
            FONT_BODY,
            FONT_LG,
            FONT_SUBTITLE,
            FONT_XL,
            FONT_HEADING,
            FONT_TITLE,
            FONT_SECTION,
            FONT_DISPLAY,
            FONT_RATING,
        ]:
            font = FontCache.get(size)
            assert isinstance(font, pygame.font.Font), f"Size {size} should produce a valid font"
