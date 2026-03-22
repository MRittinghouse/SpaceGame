"""Centralized font cache for the game.

Eliminates redundant pygame.font.Font() construction across views by caching
one Font object per (path, size) pair. Views should use FontCache.get(size)
with semantic constants instead of magic numbers.

Font sizes are automatically scaled to the active resolution. The semantic
constants define base sizes at 720p; FontCache.get() applies a scale factor
derived from WINDOW_HEIGHT so that fonts remain proportional at higher
resolutions.
"""

import pygame

# Base resolution for font size definitions
_BASE_HEIGHT: int = 720

# Semantic font size constants — base values at 720p reference resolution.
# FontCache.get() scales these to the active WINDOW_HEIGHT automatically.
FONT_MICRO: int = 14  # Skill tree node labels, tiny UI chrome
FONT_XS: int = 16  # Small indicators, badge text, card labels
FONT_SM: int = 18  # Small labels, hints, step indicators, cell text
FONT_SM2: int = 17  # Card detail text (station hub)
FONT_MD: int = 20  # Body text, descriptions, info text
FONT_MD2: int = 21  # Hint text (ground briefing)
FONT_BODY: int = 22  # Primary body text, info labels, dialogue responses
FONT_LG: int = 24  # Headers, dialogue body, system labels
FONT_SUBTITLE: int = 26  # Name text, card names, value fonts
FONT_XL: int = 28  # Subtitles, detail titles, skill headers
FONT_XL2: int = 30  # Points display, tier labels, detail titles
FONT_HEADING: int = 32  # Feedback, summary text, button text
FONT_TITLE: int = 36  # Main view titles, section headers
FONT_SECTION: int = 40  # Section titles, achievement headers
FONT_SECTION2: int = 44  # Summary titles, ground result titles
FONT_DISPLAY: int = 48  # Large titles (character creation, pause, etc.)
FONT_RATING: int = 72  # Mini-game rating displays
FONT_HERO: int = 96  # Main menu title


def scaled_font_size(base_size: int) -> int:
    """Compute a resolution-scaled font size.

    Args:
        base_size: Font size at 720p reference resolution.

    Returns:
        Scaled size for the current WINDOW_HEIGHT.
    """
    from spacegame.config import WINDOW_HEIGHT

    return max(10, round(base_size * WINDOW_HEIGHT / _BASE_HEIGHT))


class FontCache:
    """Singleton cache for pygame Font objects with resolution-aware scaling.

    Handles pygame.quit()/init() cycles gracefully by detecting stale fonts
    and recreating them. This is important for test suites where pygame may
    be reinitialized between test classes.

    Font sizes are automatically scaled by the ratio of the current
    WINDOW_HEIGHT to the 720p base resolution.

    Usage:
        font = FontCache.get(FONT_LG)   # 24 at 720p, 36 at 1080p
        font = FontCache.get(20)         # same scaling applies
    """

    _cache: dict[tuple[str | None, int], pygame.font.Font] = {}

    @classmethod
    def get(cls, size: int, path: str | None = None) -> pygame.font.Font:
        """Get a cached font, automatically scaled to the active resolution.

        Args:
            size: Base font size (at 720p). Scaled proportionally to
                the current WINDOW_HEIGHT.
            path: Optional path to a .ttf font file. None uses pygame default.

        Returns:
            Cached pygame Font object at the scaled size.
        """
        actual_size = scaled_font_size(size)
        key = (path, actual_size)
        font = cls._cache.get(key)
        if font is not None:
            # Validate cached font is still usable (survives pygame.quit/init)
            try:
                font.size("x")
                return font
            except pygame.error:
                # Font was invalidated by pygame reinit — recreate
                del cls._cache[key]
        cls._cache[key] = pygame.font.Font(path, actual_size)
        return cls._cache[key]

    @classmethod
    def clear(cls) -> None:
        """Clear the font cache. Useful for testing or reinitializing."""
        cls._cache.clear()
