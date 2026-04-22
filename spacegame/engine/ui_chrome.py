"""Canonical UI chrome primitives — badges, stamps, glyphs.

Implements the shared vocabulary defined in
``requirements/overhaul/42_ui_chrome_components.md §7``. All color resolution
routes through ``engine/material_palette.PALETTE_ROLES`` so chrome stays
palette-compliant and colorblind-remappable.

Three primitives:
- ``draw_badge`` — small rounded-rect status marker (state palette)
- ``draw_stamp`` — heavier rectangular stamp with canonical ``StampType``
- ``draw_glyph`` — pixel-art icon rendered in a single palette role color

A code-registered glyph library covers the Tier 2 tier-glyph and faction
insignia names. New glyphs land here (or later, in a PNG atlas) rather than
being drawn ad-hoc in view files.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import pygame

from spacegame.engine.fonts import FONT_SM, get_font
from spacegame.engine.material_palette import get_role

# ---------------------------------------------------------------------------
# Stamp system (spec §7.2 / §7.5)
# ---------------------------------------------------------------------------


class StampType(Enum):
    """Canonical stamp catalogue.

    Stamps are heavier state indicators than badges — they carry a single,
    punchy piece of legality / approval information and use the state
    palette (hud_warning / hud_critical / hud_cyan).
    """

    PERMIT = "permit"
    RESTRICTED = "restricted"
    ILLEGAL = "illegal"
    APPROVED = "approved"


_STAMP_PALETTE: dict[StampType, dict[str, str]] = {
    StampType.PERMIT: {
        "background_role": "hud_warning",
        "text_role": "void_deep",
        "default_label": "PERMIT",
    },
    StampType.RESTRICTED: {
        "background_role": "hud_critical",
        "text_role": "hud_text",
        "default_label": "RESTRICTED",
    },
    StampType.ILLEGAL: {
        # Same hue family as RESTRICTED (spec §7.2) — weight difference is
        # stylistic (darker text, heavier outline).
        "background_role": "hud_critical",
        "text_role": "void_deep",
        "default_label": "ILLEGAL",
    },
    StampType.APPROVED: {
        "background_role": "hud_cyan",
        "text_role": "void_deep",
        "default_label": "APPROVED",
    },
}


def get_stamp_palette(stamp: StampType) -> dict[str, str]:
    """Return the palette-role + default-label mapping for a stamp type."""
    return dict(_STAMP_PALETTE[stamp])


# ---------------------------------------------------------------------------
# Badge primitive (spec §7.3)
# ---------------------------------------------------------------------------


def draw_badge(
    surface: pygame.Surface,
    rect: pygame.Rect,
    background_role: str,
    label_text: Optional[str] = None,
    icon_surface: Optional[pygame.Surface] = None,
    border_role: Optional[str] = None,
    alpha: int = 255,
) -> None:
    """Draw a badge inside ``rect`` on ``surface``.

    Args:
        surface: Target surface.
        rect: Badge bounds.
        background_role: ``PALETTE_ROLES`` key for the fill color.
        label_text: Optional short label (usually 3-6 characters).
        icon_surface: Optional 8-12px icon anchored to the left.
        border_role: Optional ``PALETTE_ROLES`` key for a 1-pixel border.
        alpha: 0-255 overall opacity.

    Raises:
        KeyError: ``background_role`` or ``border_role`` is not a known role.
    """
    bg = get_role(background_role)
    _fill_badge_bg(surface, rect, bg, alpha)

    if border_role is not None:
        border = get_role(border_role)
        pygame.draw.rect(surface, (*border, alpha), rect, width=1)

    inner_x = rect.left + 4
    if icon_surface is not None:
        icon_h = icon_surface.get_height()
        icon_y = rect.top + max(0, (rect.height - icon_h) // 2)
        surface.blit(icon_surface, (inner_x, icon_y))
        inner_x += icon_surface.get_width() + 3

    if label_text:
        text_role = _contrast_text_role(bg)
        text_color = get_role(text_role)
        font = get_font("label", FONT_SM)
        # No AA: chrome voice is pixel-precise (spec §2.2); AA would blend
        # palette colors into off-role intermediates.
        text_surf = font.render(label_text, False, text_color)
        text_y = rect.top + max(0, (rect.height - text_surf.get_height()) // 2)
        surface.blit(text_surf, (inner_x, text_y))


def _fill_badge_bg(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    """Paint the rounded-rect background. Uses a 1px corner shave for the
    pixel-precise rounded look (spec §7.1 — small visual marker)."""
    fill = (*color, alpha)
    # Solid center.
    pygame.draw.rect(surface, fill, rect)
    # 1px corner transparency for a subtle rounded feel (pixel-art style).
    if rect.width >= 3 and rect.height >= 3:
        for cx, cy in (
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
        ):
            surface.set_at((cx, cy), (0, 0, 0, 0))


# ---------------------------------------------------------------------------
# Stamp primitive (spec §7.3)
# ---------------------------------------------------------------------------


def draw_stamp(
    surface: pygame.Surface,
    rect: pygame.Rect,
    stamp_type: StampType,
    text: Optional[str] = None,
    alpha: int = 255,
) -> None:
    """Draw a canonical stamp inside ``rect``.

    Args:
        surface: Target surface.
        rect: Stamp bounds. Spec §7.1 envisions these as wider than badges.
        stamp_type: One of the :class:`StampType` entries.
        text: Override the default label. None uses ``default_label``.
        alpha: 0-255 overall opacity.
    """
    palette = _STAMP_PALETTE[stamp_type]
    bg = get_role(palette["background_role"])
    text_color = get_role(palette["text_role"])
    label = text if text is not None else palette["default_label"]

    # Solid rectangular fill — no rounded corners; stamps read heavier.
    pygame.draw.rect(surface, (*bg, alpha), rect)

    if label:
        font = get_font("label", FONT_SM)
        # No AA — consistent with badge rendering (spec §2.2 pixel voice).
        text_surf = font.render(label, False, text_color)
        text_x = rect.left + max(0, (rect.width - text_surf.get_width()) // 2)
        text_y = rect.top + max(0, (rect.height - text_surf.get_height()) // 2)
        surface.blit(text_surf, (text_x, text_y))


# ---------------------------------------------------------------------------
# Glyph library + primitive (spec §7.2 / §7.3)
# ---------------------------------------------------------------------------
#
# Glyphs are small boolean pixel masks rendered in a single palette role
# color. V1 ships the masks as code-defined data for the spec-enumerated
# tier glyphs and faction insignia. Future work may migrate to a sprite
# atlas at ``data/assets/ui/glyphs.png``; the public API stays the same.


def _mask_from_strings(rows: tuple[str, ...]) -> tuple[tuple[bool, ...], ...]:
    """Convert ``"# . #"``-style rows into a boolean mask."""
    return tuple(tuple(ch == "#" for ch in row) for row in rows)


_GLYPHS: dict[str, tuple[tuple[bool, ...], ...]] = {
    # Commodity tier glyphs (spec §7.2) — 8x8 silhouettes.
    # Bulk: three stacked lines (heavy cargo).
    "tier_bulk": _mask_from_strings(
        (
            "........",
            "########",
            "........",
            "########",
            "........",
            "########",
            "........",
            "........",
        )
    ),
    # Standard: filled square.
    "tier_standard": _mask_from_strings(
        (
            "........",
            ".######.",
            ".######.",
            ".######.",
            ".######.",
            ".######.",
            ".######.",
            "........",
        )
    ),
    # Premium: diamond.
    "tier_premium": _mask_from_strings(
        (
            "...##...",
            "..####..",
            ".######.",
            "########",
            "########",
            ".######.",
            "..####..",
            "...##...",
        )
    ),
    # Luxury: crown / stepped peak.
    "tier_luxury": _mask_from_strings(
        (
            "#......#",
            "##....##",
            "##.##.##",
            "########",
            "########",
            "########",
            "########",
            "........",
        )
    ),
    # Restricted: square with diagonal slash.
    "tier_restricted": _mask_from_strings(
        (
            "########",
            "#......#",
            "#.....##",
            "#....##.",
            "#...##.#",
            "#..##..#",
            "##.....#",
            "########",
        )
    ),
    # Illegal: square with full X.
    "tier_illegal": _mask_from_strings(
        (
            "########",
            "##....##",
            ".##..##.",
            "..####..",
            "..####..",
            ".##..##.",
            "##....##",
            "########",
        )
    ),
    # Faction insignia (spec §7.2) — 8x8 silhouettes.
    # Commerce Guild: tri-point (three converging lines).
    "faction_commerce_guild": _mask_from_strings(
        (
            "...##...",
            "...##...",
            "..####..",
            "##.##.##",
            "###..###",
            "##....##",
            "#......#",
            "........",
        )
    ),
    # Miners Union: hexagon (geological glyph).
    "faction_miners_union": _mask_from_strings(
        (
            "..####..",
            ".######.",
            "########",
            "########",
            "########",
            "########",
            ".######.",
            "..####..",
        )
    ),
    # Frontier Alliance: star.
    "faction_frontier_alliance": _mask_from_strings(
        (
            "...##...",
            "...##...",
            "########",
            ".######.",
            ".######.",
            "..####..",
            ".##..##.",
            "##....##",
        )
    ),
    # Science Collective: cross / plus.
    "faction_science_collective": _mask_from_strings(
        (
            "...##...",
            "...##...",
            "...##...",
            "########",
            "########",
            "...##...",
            "...##...",
            "...##...",
        )
    ),
    # Crimson Reach: crossed bolts (spec §7.2 literal reference).
    "faction_crimson_reach": _mask_from_strings(
        (
            "##....##",
            ".##..##.",
            "..####..",
            "...##...",
            "...##...",
            "..####..",
            ".##..##.",
            "##....##",
        )
    ),
}


def glyph_names() -> tuple[str, ...]:
    """All registered glyph identifiers, in insertion order."""
    return tuple(_GLYPHS.keys())


def is_valid_glyph(name: str) -> bool:
    return name in _GLYPHS


def get_glyph_mask(name: str) -> tuple[tuple[bool, ...], ...]:
    """Return the raw boolean mask for a registered glyph.

    Raises:
        KeyError: ``name`` is not a registered glyph id.
    """
    if name not in _GLYPHS:
        raise KeyError(f"Unknown glyph '{name}'. Known: {list(_GLYPHS.keys())}")
    return _GLYPHS[name]


def draw_glyph(
    surface: pygame.Surface,
    pos: tuple[int, int],
    glyph_id: str,
    color_role: str,
    size: int = 12,
) -> None:
    """Paint a registered glyph at ``pos`` using a single palette role color.

    The glyph's source mask is scaled to a ``size x size`` square via nearest-
    neighbor sampling. Every lit pixel gets the canonical role RGB — no tint,
    no anti-aliasing, no off-palette drift.

    Args:
        surface: Target surface.
        pos: Top-left pixel (x, y) of the rendered glyph.
        glyph_id: Registry key (see :func:`glyph_names`).
        color_role: ``PALETTE_ROLES`` key for the lit pixels.
        size: Square side length in pixels. Defaults to the 12px badge tier.

    Raises:
        KeyError: ``glyph_id`` or ``color_role`` is not recognized.
    """
    mask = get_glyph_mask(glyph_id)
    color = get_role(color_role)

    src_h = len(mask)
    src_w = len(mask[0]) if mask else 0
    if src_w == 0 or size <= 0:
        return

    ox, oy = pos
    for dy in range(size):
        src_y = (dy * src_h) // size
        for dx in range(size):
            src_x = (dx * src_w) // size
            if mask[src_y][src_x]:
                surface.set_at((ox + dx, oy + dy), (*color, 255))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _contrast_text_role(bg: tuple[int, int, int]) -> str:
    """Pick a text role that reads clearly on ``bg``.

    Simple luminance check: dark backgrounds get ``hud_text`` (near-white);
    bright backgrounds get ``void_deep`` (near-black). Keeps badges legible
    without callers having to reason about contrast manually.
    """
    luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return "void_deep" if luminance > 160 else "hud_text"
