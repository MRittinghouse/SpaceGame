"""Shared UI drawing utilities.

Centralizes the most-duplicated rendering patterns across views:
draw_bar, draw_panel, draw_summary_overlay, and word_wrap. Views should
import these instead of reimplementing bar/panel/text-wrapping logic.
"""

from typing import Optional, Sequence

import pygame

from spacegame.config import Colors, WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.engine.fonts import FontCache, FONT_SM, FONT_HEADING, FONT_LG, FONT_RATING


# ---------------------------------------------------------------------------
# 9-slice panel rendering
# ---------------------------------------------------------------------------

# Border slice size in pixels (each corner is SLICE x SLICE)
SLICE = 4

# Cached 9-slice panel pieces (generated on first use)
_nine_slice_cache: dict[str, dict[str, pygame.Surface]] = {}


def _make_nine_slice_pieces(
    border_color: tuple[int, int, int],
    bg_color: tuple[int, int, int],
    alpha: int,
) -> dict[str, pygame.Surface]:
    """Generate 9-slice panel pieces: 4 corners, 4 edges, 1 center.

    Creates a pixel art border effect with a 1px outer highlight,
    1px inner shadow, and filled interior.
    """
    s = SLICE
    # Derive colors
    outer = border_color
    inner = (
        max(0, bg_color[0] + 15),
        max(0, bg_color[1] + 18),
        max(0, bg_color[2] + 25),
    )
    bg_rgba = (*bg_color, alpha)
    outer_rgba = (*outer, min(255, alpha + 40))
    inner_rgba = (*inner, alpha)

    def _surf(w: int, h: int) -> pygame.Surface:
        return pygame.Surface((w, h), pygame.SRCALPHA)

    # --- Corners (s x s each) ---
    corners: dict[str, pygame.Surface] = {}

    # Top-left corner
    tl = _surf(s, s)
    tl.fill(bg_rgba)
    for i in range(s):
        tl.set_at((i, 0), outer_rgba)  # top edge
        tl.set_at((0, i), outer_rgba)  # left edge
    for i in range(1, s):
        tl.set_at((i, 1), inner_rgba)  # inner top
        tl.set_at((1, i), inner_rgba)  # inner left
    corners["tl"] = tl

    # Top-right corner
    tr = _surf(s, s)
    tr.fill(bg_rgba)
    for i in range(s):
        tr.set_at((i, 0), outer_rgba)
        tr.set_at((s - 1, i), outer_rgba)
    for i in range(s - 1):
        tr.set_at((i, 1), inner_rgba)
    for i in range(1, s):
        tr.set_at((s - 2, i), inner_rgba)
    corners["tr"] = tr

    # Bottom-left corner
    bl = _surf(s, s)
    bl.fill(bg_rgba)
    for i in range(s):
        bl.set_at((i, s - 1), outer_rgba)
        bl.set_at((0, i), outer_rgba)
    for i in range(1, s):
        bl.set_at((i, s - 2), inner_rgba)
    for i in range(s - 1):
        bl.set_at((1, i), inner_rgba)
    corners["bl"] = bl

    # Bottom-right corner
    br = _surf(s, s)
    br.fill(bg_rgba)
    for i in range(s):
        br.set_at((i, s - 1), outer_rgba)
        br.set_at((s - 1, i), outer_rgba)
    for i in range(s - 1):
        br.set_at((i, s - 2), inner_rgba)
        br.set_at((s - 2, i), inner_rgba)
    corners["br"] = br

    # --- Edges (1px wide/tall, tiled) ---
    # Top edge (1px wide, s tall)
    top = _surf(1, s)
    top.fill(bg_rgba)
    top.set_at((0, 0), outer_rgba)
    top.set_at((0, 1), inner_rgba)
    corners["top"] = top

    # Bottom edge
    bot = _surf(1, s)
    bot.fill(bg_rgba)
    bot.set_at((0, s - 1), outer_rgba)
    bot.set_at((0, s - 2), inner_rgba)
    corners["bot"] = bot

    # Left edge (s wide, 1px tall)
    left = _surf(s, 1)
    left.fill(bg_rgba)
    left.set_at((0, 0), outer_rgba)
    left.set_at((1, 0), inner_rgba)
    corners["left"] = left

    # Right edge
    right = _surf(s, 1)
    right.fill(bg_rgba)
    right.set_at((s - 1, 0), outer_rgba)
    right.set_at((s - 2, 0), inner_rgba)
    corners["right"] = right

    # --- Center (1x1 fill) ---
    center = _surf(1, 1)
    center.set_at((0, 0), bg_rgba)
    corners["center"] = center

    return corners


def _get_nine_slice(
    border_color: tuple[int, int, int],
    bg_color: tuple[int, int, int],
    alpha: int,
) -> dict[str, pygame.Surface]:
    """Get or create cached 9-slice pieces for given colors."""
    key = f"{border_color}_{bg_color}_{alpha}"
    if key not in _nine_slice_cache:
        _nine_slice_cache[key] = _make_nine_slice_pieces(
            border_color, bg_color, alpha
        )
    return _nine_slice_cache[key]


def draw_nine_slice_panel(
    screen: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    *,
    alpha: int = 200,
    bg_color: tuple[int, int, int] = Colors.PANEL_BG,
    border_color: tuple[int, int, int] = Colors.UI_BORDER,
) -> None:
    """Render a panel using 9-slice pixel art border.

    Args:
        screen: Surface to draw on.
        rect: Panel position and size.
        alpha: Panel background opacity (0-255).
        bg_color: Panel fill color.
        border_color: Border color for the pixel art frame.
    """
    r = pygame.Rect(rect)
    if r.width < SLICE * 2 or r.height < SLICE * 2:
        # Too small for 9-slice — fall back to simple rect
        surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        surf.fill((*bg_color, alpha))
        screen.blit(surf, r.topleft)
        return

    pieces = _get_nine_slice(border_color, bg_color, alpha)
    s = SLICE
    inner_w = r.width - s * 2
    inner_h = r.height - s * 2

    # Pre-render to a temp surface for single blit (faster for large panels)
    panel_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)

    # Center fill
    center_fill = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
    center_fill.fill((*bg_color, alpha))
    panel_surf.blit(center_fill, (s, s))

    # Top edge (tile 1px-wide piece across inner width)
    top_edge = pygame.transform.scale(pieces["top"], (inner_w, s))
    panel_surf.blit(top_edge, (s, 0))

    # Bottom edge
    bot_edge = pygame.transform.scale(pieces["bot"], (inner_w, s))
    panel_surf.blit(bot_edge, (s, r.height - s))

    # Left edge
    left_edge = pygame.transform.scale(pieces["left"], (s, inner_h))
    panel_surf.blit(left_edge, (0, s))

    # Right edge
    right_edge = pygame.transform.scale(pieces["right"], (s, inner_h))
    panel_surf.blit(right_edge, (r.width - s, s))

    # Corners
    panel_surf.blit(pieces["tl"], (0, 0))
    panel_surf.blit(pieces["tr"], (r.width - s, 0))
    panel_surf.blit(pieces["bl"], (0, r.height - s))
    panel_surf.blit(pieces["br"], (r.width - s, r.height - s))

    screen.blit(panel_surf, r.topleft)


def draw_bar(
    screen: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    current: float,
    maximum: float,
    color: tuple[int, int, int],
    *,
    label: Optional[str] = None,
    font: Optional[pygame.font.Font] = None,
    show_value: bool = True,
    bg_color: tuple[int, int, int] = Colors.BAR_BG,
    edge_color: tuple[int, int, int] = Colors.BAR_EDGE,
    border_color: tuple[int, int, int] = Colors.UI_BORDER,
) -> None:
    """Render a progress bar with pixel art inset frame and fill.

    Features a beveled inset border: 1px highlight (top-left) and
    1px shadow (bottom-right) inside the outer border, creating
    a recessed pixel art look.

    Args:
        screen: Surface to draw on.
        x: Left edge x coordinate.
        y: Top edge y coordinate.
        width: Total bar width in pixels.
        height: Bar height in pixels.
        current: Current value.
        maximum: Maximum value.
        color: Fill color (RGB tuple).
        label: Optional text label rendered left of the bar.
        font: Font for label/value text. Defaults to FONT_SM.
        show_value: Whether to render "current/max" centered on the bar.
        bg_color: Bar track background color.
        edge_color: Leading edge highlight color.
        border_color: Bar border color.
    """
    if font is None:
        font = FontCache.get(FONT_SM)

    bar_x = x
    bar_w = width

    # Optional label
    if label:
        label_surf = font.render(label, True, Colors.TEXT_SECONDARY)
        screen.blit(label_surf, (x, y + (height - label_surf.get_height()) // 2))
        label_w = label_surf.get_width() + 6
        bar_x = x + label_w
        bar_w = width - label_w

    # Outer border
    pygame.draw.rect(screen, border_color, (bar_x, y, bar_w, height), 1)

    # Inner bevel (only if bar is large enough)
    if bar_w > 4 and height > 4:
        # Shadow on bottom-right (darker)
        shadow = (
            max(0, border_color[0] - 25),
            max(0, border_color[1] - 25),
            max(0, border_color[2] - 25),
        )
        pygame.draw.line(screen, shadow, (bar_x + 1, y + height - 2),
                         (bar_x + bar_w - 2, y + height - 2))
        pygame.draw.line(screen, shadow, (bar_x + bar_w - 2, y + 1),
                         (bar_x + bar_w - 2, y + height - 2))
        # Highlight on top-left (brighter)
        highlight = (
            min(255, border_color[0] + 30),
            min(255, border_color[1] + 30),
            min(255, border_color[2] + 35),
        )
        pygame.draw.line(screen, highlight, (bar_x + 1, y + 1),
                         (bar_x + bar_w - 2, y + 1))
        pygame.draw.line(screen, highlight, (bar_x + 1, y + 1),
                         (bar_x + 1, y + height - 2))

        # Background (inside bevel)
        inner_x = bar_x + 2
        inner_y = y + 2
        inner_w = bar_w - 4
        inner_h = height - 4
    else:
        # Small bars: no bevel, just fill inside border
        inner_x = bar_x + 1
        inner_y = y + 1
        inner_w = bar_w - 2
        inner_h = height - 2

    # Background
    pygame.draw.rect(screen, bg_color, (inner_x, inner_y, inner_w, inner_h))

    # Fill
    ratio = current / maximum if maximum > 0 else 0
    ratio = max(0.0, min(1.0, ratio))
    fill_w = int(inner_w * ratio)
    if fill_w > 0:
        pygame.draw.rect(screen, color, (inner_x, inner_y, fill_w, inner_h))
        # Leading edge highlight
        if fill_w > 2:
            pygame.draw.rect(
                screen, edge_color, (inner_x + fill_w - 2, inner_y, 2, inner_h)
            )

    # Value text
    if show_value and maximum > 0:
        value_text = f"{int(current)}/{int(maximum)}"
        value_surf = font.render(value_text, True, Colors.TEXT_PRIMARY)
        value_rect = value_surf.get_rect(
            center=(bar_x + bar_w // 2, y + height // 2)
        )
        screen.blit(value_surf, value_rect)


def draw_panel(
    screen: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    *,
    alpha: int = 200,
    bg_color: tuple[int, int, int] = Colors.PANEL_BG,
    border_color: Optional[tuple[int, int, int]] = Colors.UI_BORDER,
    border_radius: int = 4,
) -> None:
    """Render a semi-transparent panel with pixel art 9-slice border.

    Args:
        screen: Surface to draw on.
        rect: Panel position and size (Rect or (x, y, w, h) tuple).
        alpha: Panel background opacity (0-255).
        bg_color: Panel background color.
        border_color: Border color, or None to skip border.
        border_radius: Corner radius (ignored, kept for API compat).
    """
    r = pygame.Rect(rect)
    if r.width <= 0 or r.height <= 0:
        return

    if border_color is not None:
        draw_nine_slice_panel(
            screen, r, alpha=alpha, bg_color=bg_color, border_color=border_color
        )
    else:
        # No border — simple fill
        if alpha < 255:
            surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            surf.fill((*bg_color, alpha))
            screen.blit(surf, r.topleft)
        else:
            pygame.draw.rect(screen, bg_color, r)


def word_wrap(
    text: str,
    font: pygame.font.Font,
    max_width: int,
) -> list[str]:
    """Split text into lines that fit within max_width pixels.

    Handles newlines in the input text as explicit line breaks.

    Args:
        text: Text to wrap.
        font: Font used for width measurement.
        max_width: Maximum line width in pixels.

    Returns:
        List of wrapped lines.
    """
    if not text:
        return []

    result: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            result.append("")
            continue

        words = paragraph.split()
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] > max_width and current_line:
                result.append(current_line)
                current_line = word
            else:
                current_line = test_line

        if current_line:
            result.append(current_line)

    return result


def draw_summary_overlay(
    screen: pygame.Surface,
    title: str,
    stats: list[tuple[str, str]],
    xp_earned: int,
    rating_letter: str,
    rating_color: tuple[int, int, int],
    *,
    panel_width: int = 500,
    panel_height: int = 440,
) -> None:
    """Render a mini-game completion summary overlay.

    Draws a centered semi-transparent panel with title, stats grid,
    XP earned section, rating badge, and continue prompt.

    Args:
        screen: Surface to draw on.
        title: Summary title (e.g. "MINING COMPLETE").
        stats: List of (label, value) tuples for the stats grid.
        xp_earned: XP points earned to display.
        rating_letter: Rating letter (e.g. "A", "S", "B").
        rating_color: Color for the rating letter display.
        panel_width: Panel width in pixels.
        panel_height: Panel height in pixels.
    """
    sw, sh = screen.get_size()

    # Dim overlay
    dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 160))
    screen.blit(dim, (0, 0))

    # Panel
    pw, ph = panel_width, panel_height
    px = (sw - pw) // 2
    py = (sh - ph) // 2
    panel = pygame.Rect(px, py, pw, ph)
    pygame.draw.rect(screen, (20, 24, 40), panel, border_radius=8)
    pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, panel, 2, border_radius=8)

    # Fonts
    title_font = FontCache.get(44)
    stat_font = FontCache.get(FONT_HEADING)
    rating_font = FontCache.get(FONT_RATING)
    prompt_font = FontCache.get(FONT_LG)

    # Title
    title_surf = title_font.render(title, True, Colors.TEXT_HIGHLIGHT)
    screen.blit(title_surf, title_surf.get_rect(center=(sw // 2, py + 35)))

    # Stats
    y = py + 75
    spacing = 32
    for label, value in stats:
        label_surf = stat_font.render(label, True, Colors.TEXT_SECONDARY)
        value_surf = stat_font.render(value, True, Colors.TEXT)
        screen.blit(label_surf, (px + 40, y))
        screen.blit(value_surf, (px + pw - 40 - value_surf.get_width(), y))
        y += spacing

    # XP earned (highlighted)
    y += 10
    pygame.draw.line(screen, Colors.TEXT_SECONDARY, (px + 30, y), (px + pw - 30, y))
    y += 15
    xp_label = stat_font.render("XP Earned", True, Colors.BLUE)
    xp_value = stat_font.render(f"+{xp_earned}", True, Colors.BLUE)
    screen.blit(xp_label, (px + 40, y))
    screen.blit(xp_value, (px + pw - 40 - xp_value.get_width(), y))

    # Session rating
    rating_surf = rating_font.render(rating_letter, True, rating_color)
    screen.blit(
        rating_surf,
        rating_surf.get_rect(center=(px + pw - 70, py + 35)),
    )

    # Continue prompt
    continue_text = prompt_font.render(
        "Click or press Enter to continue", True, Colors.TEXT_SECONDARY
    )
    screen.blit(
        continue_text, continue_text.get_rect(center=(sw // 2, py + ph - 30))
    )
