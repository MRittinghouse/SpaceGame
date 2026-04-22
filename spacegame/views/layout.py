"""Shared layout constants for consistent UI across all views.

Provides a standard vocabulary for spacing, sizing, and positioning.
Views import what they need rather than defining their own ad-hoc values.
View-specific constants (combat zones, builder grid) remain in their views.

All values are pre-scaled for the active resolution via scale_x/scale_y.
"""

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, scale_x, scale_y

# ============================================================================
# SCREEN REGIONS
# ============================================================================

# Usable area above the HUD bar (HUD_BASE_HEIGHT = 90 in cockpit_hud.py)
HUD_HEIGHT = scale_y(90)
CONTENT_BOTTOM = WINDOW_HEIGHT - HUD_HEIGHT

# Standard screen margins (edge of screen to content)
MARGIN_EDGE = scale_x(40)  # Minimum distance from screen edge
MARGIN_WIDE = scale_x(80)  # Wider margin for centered content

# ============================================================================
# SPACING VOCABULARY
# ============================================================================

# Padding (inside containers)
PAD_XS = scale_y(4)  # Tight: inside bar labels, between icon and text
PAD_SM = scale_y(8)  # Small: inside cards, between grouped elements
PAD_MD = scale_y(14)  # Medium: between sections within a panel
PAD_LG = scale_y(20)  # Large: between major content blocks
PAD_XL = scale_y(30)  # Extra: between screen regions

# Gaps (between sibling elements)
GAP_ITEM = 6  # Between items in a list (unscaled, tight)
GAP_CARD = scale_y(10)  # Between cards in a grid
GAP_SECTION = scale_y(20)  # Between sections

# ============================================================================
# LIST-DETAIL PATTERN (crew roster, mission log, journal)
# ============================================================================

LIST_DETAIL_LEFT = MARGIN_EDGE  # Left edge of list panel
LIST_DETAIL_TOP = scale_y(90)  # Top of list area (below header)
LIST_WIDTH = scale_x(360)  # Width of the list panel
LIST_ITEM_HEIGHT = scale_y(44)  # Height of a single list item
LIST_DETAIL_GAP = scale_x(30)  # Gap between list and detail panel

# Detail panel (computed from list)
DETAIL_LEFT = LIST_DETAIL_LEFT + LIST_WIDTH + LIST_DETAIL_GAP
DETAIL_WIDTH = WINDOW_WIDTH - DETAIL_LEFT - MARGIN_EDGE
LIST_HEIGHT = CONTENT_BOTTOM - LIST_DETAIL_TOP - scale_y(80)

# ============================================================================
# HEADER REGION
# ============================================================================

HEADER_Y = 10  # Top of header card (minimal top margin)
HEADER_MARGIN_X = MARGIN_WIDE  # Left/right margin for header
HEADER_HEIGHT = scale_y(105)  # Standard header card height

# ============================================================================
# CARD GRID (station hub, skill tree)
# ============================================================================

CARD_W_STANDARD = scale_x(370)  # Standard card width
CARD_H_STANDARD = scale_y(110)  # Standard card height (increased from 80)
CARD_GAP = GAP_CARD  # Gap between cards

# ============================================================================
# BUTTONS
# ============================================================================

BUTTON_H_SM = scale_y(34)  # Small button (list actions, compact)
BUTTON_H_MD = scale_y(40)  # Medium button (standard actions)
BUTTON_H_LG = scale_y(48)  # Large button (primary actions)
BUTTON_W_SM = scale_x(120)  # Small button width
BUTTON_W_MD = scale_x(160)  # Medium button width
BUTTON_W_LG = scale_x(200)  # Large button width
BUTTON_W_BACK = scale_x(140)  # Back button (consistent across views)

# ============================================================================
# CHATTER / AMBIENT TEXT REGION
# ============================================================================

CHATTER_MARGIN_X = MARGIN_WIDE
CHATTER_HEIGHT = scale_y(80)
CHATTER_BOTTOM_OFFSET = scale_y(185)  # Distance from screen bottom
CHATTER_Y = WINDOW_HEIGHT - CHATTER_BOTTOM_OFFSET
CHATTER_WIDTH = WINDOW_WIDTH - 2 * CHATTER_MARGIN_X

# ============================================================================
# FACTION ACCENT SYSTEM
# ============================================================================

# Primary faction colors (for labels, emblems, indicators)
# These match config.py Colors.FACTION_* but are accessible by faction_id
FACTION_COLORS: dict[str, tuple[int, int, int]] = {
    "commerce_guild": (100, 150, 255),
    "miners_union": (200, 150, 50),
    "science_collective": (150, 100, 200),
    "frontier_alliance": (100, 200, 100),
}

# Accent colors (brighter, for HUD highlights and panel borders)
FACTION_ACCENTS: dict[str, tuple[int, int, int]] = {
    "commerce_guild": (80, 140, 220),
    "miners_union": (220, 170, 60),
    "science_collective": (140, 170, 220),
    "frontier_alliance": (80, 200, 120),
}

# Dimmed accent colors (for subtle tints on panel edges)
FACTION_TINTS: dict[str, tuple[int, int, int]] = {
    "commerce_guild": (40, 60, 100),
    "miners_union": (90, 70, 30),
    "science_collective": (60, 50, 90),
    "frontier_alliance": (40, 80, 50),
}

# Default accent when faction is unknown or unaligned
DEFAULT_ACCENT = (80, 90, 110)
DEFAULT_TINT = (40, 45, 55)


def get_faction_color(faction_id: str) -> tuple[int, int, int]:
    """Get the primary color for a faction (labels, emblems)."""
    return FACTION_COLORS.get(faction_id, DEFAULT_ACCENT)


def get_faction_accent(faction_id: str) -> tuple[int, int, int]:
    """Get the bright accent color for a faction (HUD highlights, borders)."""
    return FACTION_ACCENTS.get(faction_id, DEFAULT_ACCENT)


def get_faction_tint(faction_id: str) -> tuple[int, int, int]:
    """Get the dimmed tint color for a faction (subtle panel edge tint)."""
    return FACTION_TINTS.get(faction_id, DEFAULT_TINT)
