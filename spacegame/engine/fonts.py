"""Centralized font cache for the game.

Eliminates redundant pygame.font.Font() construction across views by caching
one Font object per (path, size) pair. Views should use FontCache.get(size)
instead of creating fonts directly.
"""

import pygame

# Semantic font size constants — use these instead of magic numbers
FONT_XS: int = 16  # Skill node labels, tiny indicators
FONT_SM: int = 18  # Small labels, hints, step indicators
FONT_MD: int = 20  # Body text, descriptions, subtitles
FONT_BODY: int = 22  # Primary body text, info labels
FONT_LG: int = 24  # Headers, dialogue body, info text
FONT_SUBTITLE: int = 26  # Name text, card names, value fonts
FONT_XL: int = 28  # Subtitles, detail titles, skill headers
FONT_HEADING: int = 32  # Feedback, summary text, button text
FONT_TITLE: int = 36  # Main view titles, section headers
FONT_SECTION: int = 40  # Section titles, achievement headers
FONT_DISPLAY: int = 48  # Large titles (character creation, pause, etc.)
FONT_RATING: int = 72  # Mini-game rating displays


class FontCache:
    """Singleton cache for pygame Font objects.

    Handles pygame.quit()/init() cycles gracefully by detecting stale fonts
    and recreating them. This is important for test suites where pygame may
    be reinitialized between test classes.

    Usage:
        font = FontCache.get(FONT_LG)
        font = FontCache.get(24)  # equivalent
        font = FontCache.get(20, path="custom.ttf")
    """

    _cache: dict[tuple[str | None, int], pygame.font.Font] = {}

    @classmethod
    def get(cls, size: int, path: str | None = None) -> pygame.font.Font:
        """Get a cached font for the given size and optional path.

        Args:
            size: Font size in pixels.
            path: Optional path to a .ttf font file. None uses pygame default.

        Returns:
            Cached pygame Font object.
        """
        key = (path, size)
        font = cls._cache.get(key)
        if font is not None:
            # Validate cached font is still usable (survives pygame.quit/init)
            try:
                font.size("x")
                return font
            except pygame.error:
                # Font was invalidated by pygame reinit — recreate
                del cls._cache[key]
        cls._cache[key] = pygame.font.Font(path, size)
        return cls._cache[key]

    @classmethod
    def clear(cls) -> None:
        """Clear the font cache. Useful for testing or reinitializing."""
        cls._cache.clear()
