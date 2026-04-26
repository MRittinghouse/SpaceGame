"""Shared pulsing-glow primitive for view-layer salience highlights.

Originated as `_render_quest_receiver_glow` in `cantina_view.py` (PT-016)
to flag NPCs that receive active quests. SL-3 (station_legibility.md)
factors the pattern out so the station hub view can paint the same glow
on the recommended station card. One visual vocabulary across views: a
player who has learned the cantina's "this is your next step" glow
reads the same glow on a station card without retraining.

Two-layer pulse: a soft outer halo + a crisp inner border. Alpha
oscillates ~1 Hz between 100 and 240. Identical to the original PT-016
parameters; existing cantina behavior is preserved when the helper
replaces the inline implementation.
"""

from __future__ import annotations

import math

import pygame

# Pulse parameters. Match the original PT-016 values exactly so the
# refactored cantina view is visually indistinguishable from the
# pre-extraction implementation.
_PULSE_HZ: float = 1.0  # frequency in cycles per second
_PULSE_BASE: float = 170.0
_PULSE_AMPLITUDE: float = 50.0
_PULSE_MIN: int = 100
_PULSE_MAX: int = 240


def render_pulsing_glow(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    elapsed: float,
) -> None:
    """Render a two-layer pulsing glow around ``rect``.

    Args:
        screen: Surface to blit the glow onto.
        rect: Inner rectangle the glow surrounds. The halo extends 4 px
            outside this rect on every side.
        color: Base RGB for the glow. Caller picks: cyan
            ``(100, 220, 255)`` for mission-objective semantic, or the
            target card's own accent color for general recommendations.
        elapsed: Seconds since the glow started, used to phase the pulse.
            Typically a per-view monotonic timer that ticks during update.
    """
    pulse = int(_PULSE_BASE + _PULSE_AMPLITUDE * math.sin(elapsed * 2.0 * math.pi * _PULSE_HZ))
    pulse = max(_PULSE_MIN, min(_PULSE_MAX, pulse))

    halo = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
    # Outer soft halo
    pygame.draw.rect(
        halo,
        (*color, pulse // 3),
        halo.get_rect(),
        border_radius=6,
    )
    # Inner crisp border
    pygame.draw.rect(
        halo,
        (*color, pulse),
        halo.get_rect().inflate(-4, -4),
        width=2,
        border_radius=4,
    )
    screen.blit(halo, (rect.x - 4, rect.y - 4))
