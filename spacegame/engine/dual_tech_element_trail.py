"""Dual tech element-trail renderer (Combat overhaul §4.3).

Paints the combined-element trail that traces from source to target
during the COMBINED_RESOLVE phase of the cinematic. The head lands at
``dominant_role``; trailing segments fade toward ``trail_role`` then
toward transparent. Rendered per-frame from the timeline's
``combined_resolve_progress`` (or ``charge_intensity`` for the
ultimate's building particle swirl).

Palette discipline: head + trail points sit at their role RGBs exactly
when blitted onto a transparent target, preserving compliance. Callers
composite the trail onto the darkened cinematic canvas; the spec
exempts the fade window from compliance testing so the additive blend
during the full scene render is acceptable.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.3``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from spacegame.engine.material_palette import get_role

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrailConfig:
    """Endpoint + palette configuration for one element trail.

    Attributes:
        start: Source pixel coordinates (x, y).
        end: Target pixel coordinates (x, y).
        dominant_role: PALETTE_ROLES key for the head of the trail.
            Spec §4.3 maps this to the tech's primary emissive
            (plasma_core / ion_arc / cryo_fractal / voltaic_strike /
            glow_warm for kinetic).
        trail_role: PALETTE_ROLES key for trail segments behind the head.
            Usually the secondary element's trail role (glow_cool for
            cryo/ion, plasma_hot for plasma, etc.).
        arc_height: Peak vertical displacement of the parabolic path in
            pixels. ``0`` renders a straight line.
        trail_length: Number of trail segments behind the head. Each
            segment draws at reduced alpha + smaller radius.
        head_radius: Head-circle radius in pixels.
        trail_radius: Starting radius for trail segments.
    """

    start: tuple[float, float]
    end: tuple[float, float]
    dominant_role: str
    trail_role: str
    arc_height: float = 40.0
    trail_length: int = 8
    head_radius: int = 6
    trail_radius: int = 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_element_trail(
    target: pygame.Surface,
    config: TrailConfig,
    progress: float,
) -> None:
    """Paint the trail onto ``target`` at the given ``progress``.

    ``progress`` in ``[0, 1]``: 0 → head at ``start``; 1 → head at
    ``end``. Values outside the range are clamped. The trail extends
    BEHIND the head toward ``start``; trail segments with effective
    progress < 0 are skipped so the trail never renders off-segment.

    Rendered in additive-friendly order: the head draws last so it
    reads bright on top of the trail tint.
    """
    p = max(0.0, min(1.0, progress))

    dominant_color = get_role(config.dominant_role)
    trail_color = get_role(config.trail_role)

    # Trail segments first (back-to-front) — painted behind the head.
    segments = max(0, config.trail_length)
    if segments > 0:
        step = _trail_spacing(config)
        for i in range(segments, 0, -1):
            seg_progress = p - i * step
            if seg_progress < 0.0:
                continue
            seg_pos = _trail_position(config, seg_progress)
            fade = 1.0 - (i / segments)
            alpha = max(0, min(255, round(220 * fade)))
            radius = max(1, round(config.trail_radius * (0.4 + 0.6 * fade)))
            _draw_dot(target, seg_pos, radius, trail_color, alpha)

    # Head at the leading position.
    head_pos = _trail_position(config, p)
    _draw_dot(target, head_pos, config.head_radius, dominant_color, 255)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _trail_position(config: TrailConfig, t: float) -> tuple[float, float]:
    """Return the (x, y) point on the parabolic arc at parameter ``t``.

    ``t=0`` → ``config.start``; ``t=1`` → ``config.end``. ``arc_height``
    controls peak displacement (subtracted from y since pygame y
    increases downward).
    """
    sx, sy = config.start
    ex, ey = config.end
    x = sx + (ex - sx) * t
    y = sy + (ey - sy) * t
    if config.arc_height != 0.0:
        y -= config.arc_height * 4.0 * t * (1.0 - t)
    return (x, y)


def _trail_spacing(config: TrailConfig) -> float:
    """Spacing between trail segments in progress units.

    Keeps the trail visually compact: the full trail spans roughly the
    last 20% of the journey, regardless of how many segments there are.
    """
    if config.trail_length <= 0:
        return 0.0
    return 0.20 / config.trail_length


def _draw_dot(
    target: pygame.Surface,
    pos: tuple[float, float],
    radius: int,
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    """Blit a circle of the given color + alpha centered on pos."""
    if radius <= 0 or alpha <= 0:
        return
    size = radius * 2
    dot = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(dot, (*color, alpha), (radius, radius), radius)
    target.blit(dot, (int(pos[0]) - radius, int(pos[1]) - radius))
