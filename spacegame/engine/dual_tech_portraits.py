"""Dual tech portrait overlay renderer (Combat overhaul §4.3 + §4.9).

Pure rendering primitive for the two participating crew portraits that
slide into frame during the DARKEN_PORTRAITS phase of the dual tech
cinematic. Consumes the timeline's ``portrait_slide_factor`` and
``portrait_alpha`` — rendering is decoupled from timing so tests run
without pygame game state.

Per spec §4.9:
  - Portraits slide in from screen edges to rest at bottom-left and
    bottom-right corners.
  - Each portrait gets a palette-role faction border stripe when its
    ``faction_role`` is set (uses PALETTE_ROLES from Aesthetic Bible
    §4.8 — callers pick the right role per crew member).
  - Alpha respects the timeline's fade-out during the IMPACT phase.

Callers own portrait sprite loading and pass ``pygame.Surface`` instances
— this keeps the primitive testable without the full asset pipeline.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.3``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from spacegame.engine.material_palette import get_role

# ---------------------------------------------------------------------------
# Defaults (pixel values at 1080p — callers may scale)
# ---------------------------------------------------------------------------

DEFAULT_MARGIN_X = 20  # Gap between portrait edge and screen edge at rest
DEFAULT_BOTTOM_PADDING = 8
DEFAULT_BORDER_WIDTH = 2


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PortraitConfig:
    """Per-portrait configuration for the dual tech overlay.

    Attributes:
        surface: The portrait's pre-rendered sprite (any size; the
            primitive respects its dimensions).
        faction_role: Optional PALETTE_ROLES key for the border stripe.
            None leaves the border unpainted (transparent edge).
    """

    surface: pygame.Surface
    faction_role: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_portraits(
    target: pygame.Surface,
    left: PortraitConfig,
    right: PortraitConfig,
    slide_factor: float,
    alpha: int,
    bottom_y: Optional[int] = None,
    margin_x: int = DEFAULT_MARGIN_X,
    border_width: int = DEFAULT_BORDER_WIDTH,
) -> None:
    """Paint the two portraits onto ``target``.

    ``slide_factor`` in ``[0, 1]``: 0 means fully off-screen at the
    respective edge, 1 means fully slid in at rest position.
    ``alpha`` in ``[0, 255]``: global opacity applied to both portraits.

    Left portrait anchors to bottom-left; right to bottom-right.
    ``bottom_y`` overrides the bottom Y coordinate (default: target
    height minus a small padding).
    """
    if alpha <= 0:
        return
    slide = max(0.0, min(1.0, slide_factor))
    alpha_clamped = max(0, min(255, alpha))

    sw = target.get_width()
    sh = target.get_height()
    if bottom_y is None:
        bottom_y = sh - DEFAULT_BOTTOM_PADDING

    # Left portrait — slides in from left edge.
    left_w = left.surface.get_width()
    left_h = left.surface.get_height()
    left_x = round(-left_w + (margin_x + left_w) * slide)
    left_y = bottom_y - left_h
    _blit_portrait(
        target,
        left,
        alpha_clamped,
        left_x,
        left_y,
        border_width=border_width,
    )

    # Right portrait — slides in from right edge.
    right_w = right.surface.get_width()
    right_h = right.surface.get_height()
    right_x = round(sw - (margin_x + right_w) * slide)
    right_y = bottom_y - right_h
    _blit_portrait(
        target,
        right,
        alpha_clamped,
        right_x,
        right_y,
        border_width=border_width,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _blit_portrait(
    target: pygame.Surface,
    config: PortraitConfig,
    alpha: int,
    x: int,
    y: int,
    border_width: int,
) -> None:
    """Blit one portrait with alpha + optional faction-role border."""
    source = config.surface
    w = source.get_width()
    h = source.get_height()

    # Copy so we can apply alpha without mutating the caller's surface.
    staged = source.copy()
    staged.set_alpha(alpha)
    target.blit(staged, (x, y))

    # Faction border stripe — 1px solid rectangle at the role color.
    # The stripe reads as a chrome frame around the portrait. Alpha is
    # the same as the portrait so it fades together.
    if config.faction_role and border_width > 0:
        border_color = get_role(config.faction_role)
        border_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(
            border_surf,
            (*border_color, alpha),
            (0, 0, w, h),
            width=border_width,
        )
        target.blit(border_surf, (x, y))
