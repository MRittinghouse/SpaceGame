"""Centralized font system with role-based custom fonts.

Provides a FontCache for resolution-aware font loading, and a role-based
font registry that maps narrative roles (dialogue, headers, narration,
machine, stats, labels) to specific TTF files.

Font roles serve a storytelling purpose:
- Pixel fonts (dialogue, narration, stats, labels) feel HUMAN — warm, crafted
- Space Mono (machine) feels SYNTHETIC — cold, precise, mechanical
- Press Start 2P (headers) commands attention — bold, iconic, arcade
- When an NPC speaks, it's Pixeloid Sans. When the ship computer reports,
  it's Space Mono. The font IS the voice.

All fonts fall back to the pygame system font if the TTF file is missing,
so the game always runs even without the font assets.
"""

from pathlib import Path
from typing import Optional

import pygame

# Base resolution for font size definitions
_BASE_HEIGHT: int = 720

# ============================================================================
# Font Size Constants (base values at 720p, auto-scaled by FontCache)
# ============================================================================

FONT_MICRO: int = 14  # Skill tree node labels, tiny UI chrome
FONT_XS: int = 16  # Small indicators, badge text, card labels
FONT_SM: int = 18  # Small labels, hints, step indicators
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

# ============================================================================
# Font Role Registry — maps narrative roles to TTF file paths
# ============================================================================

# Resolve font directory from this file's location
_FONT_DIR = Path(__file__).parent.parent / "data" / "assets" / "fonts"

# Font role → TTF path mapping. If a TTF is missing, falls back to system font.
# Download missing fonts from the sources listed in requirements/polish_and_tooling.md
FONT_ROLES: dict[str, Optional[str]] = {}


def _resolve_font_path(filename: str) -> Optional[str]:
    """Resolve a font filename to an absolute path, or None if missing."""
    path = _FONT_DIR / filename
    if path.exists():
        return str(path)
    return None


def _init_font_roles() -> None:
    """Initialize the font role registry from available TTF files."""
    global FONT_ROLES
    FONT_ROLES = {
        # Human voices — pixel fonts for warmth and character
        "dialogue": _resolve_font_path("PixeloidSans.ttf"),  # NPC speech, menu body
        "header": _resolve_font_path("PressStart2P-Regular.ttf"),  # Screen titles, bold headers
        "narration": _resolve_font_path("Silver.ttf"),  # Flavor text, atmosphere
        # Synthetic voice — clean monospace for machine/digital feel
        "machine": _resolve_font_path("SpaceMono-Regular.ttf"),  # System messages, scan data
        "machine_bold": _resolve_font_path("SpaceMono-Bold.ttf"),  # Alerts, warnings
        # Data display — compact monospace for numbers and stats
        "stats": _resolve_font_path("monogram.ttf"),  # Stat panels, credits, damage
        # Tiny labels — readable at very small sizes
        "label": _resolve_font_path("Tiny5-Regular.ttf"),  # Badges, category tabs
    }


# Width compensation factors per role.
# Custom fonts are wider than the system font at the same point size.
# These factors scale the requested size DOWN so rendered text occupies
# roughly the same horizontal space as the system font would have.
# Measured empirically: header=3.1x, machine=1.9x, dialogue=1.6x, etc.
# Target: ~1.05-1.15x overshoot (slightly wider is OK, overflow is not).
_ROLE_SIZE_SCALE: dict[str, float] = {
    "header": 0.50,  # Press Start 2P: 3.1x width → aim for ~1.55x
    "dialogue": 0.72,  # Pixeloid Sans: 1.6x width → aim for ~1.15x
    "machine": 0.62,  # Space Mono: 1.9x width → aim for ~1.18x
    "machine_bold": 0.62,  # Space Mono Bold: same metrics
    "label": 0.82,  # Tiny5: 1.3x width → aim for ~1.07x
    "stats": 0.92,  # monogram: 1.2x width → aim for ~1.10x
    "narration": 1.0,  # Silver: ~1.0x width, no compensation needed
}


# Initialize on import
_init_font_roles()


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


def get_font(role: str, size: int) -> pygame.font.Font:
    """Get a font by narrative role and size.

    Resolves the role to a TTF file path via FONT_ROLES, then returns
    a cached font at the resolution-scaled size. Falls back to the
    system default font if the role's TTF is not available.

    Args:
        role: Font role name ("dialogue", "header", "narration",
              "machine", "machine_bold", "stats", "label").
        size: Base font size at 720p.

    Returns:
        Cached pygame Font at the scaled size.

    Example:
        title = get_font("header", FONT_TITLE).render("SHIPYARD", True, color)
        body = get_font("dialogue", FONT_MD).render("Welcome aboard.", True, color)
        scan = get_font("machine", FONT_SM).render("SCAN COMPLETE", True, color)
    """
    path = FONT_ROLES.get(role)
    # Apply width compensation so custom fonts don't overflow UI containers
    scale = _ROLE_SIZE_SCALE.get(role, 1.0)
    adjusted_size = max(8, int(size * scale))
    return FontCache.get(adjusted_size, path=path)


def get_available_roles() -> dict[str, bool]:
    """Get which font roles have TTF files available.

    Returns:
        Dict mapping role name → True if TTF exists, False if falling back.
    """
    return {role: path is not None for role, path in FONT_ROLES.items()}
