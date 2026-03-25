"""Easing functions and tween utilities for smooth animations.

Provides standard easing curves and a Tween class that interpolates
a numeric value over time using any easing function.
"""

import math
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Easing functions: map t in [0, 1] -> value (usually [0, 1])
# ---------------------------------------------------------------------------

EasingFn = Callable[[float], float]


def _clamp01(t: float) -> float:
    """Clamp t to [0, 1]."""
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


def linear(t: float) -> float:
    """Linear interpolation (no easing)."""
    t = _clamp01(t)
    return t


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in (accelerating)."""
    t = _clamp01(t)
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out (decelerating)."""
    t = _clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out (accelerate then decelerate)."""
    t = _clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out (fast start, slow finish)."""
    t = _clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out."""
    t = _clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_out_back(t: float) -> float:
    """Ease-out with slight overshoot past target, then settle."""
    t = _clamp01(t)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def ease_out_bounce(t: float) -> float:
    """Bounce ease-out (ball-drop style, settles at target)."""
    t = _clamp01(t)
    n1 = 7.5625
    d1 = 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    elif t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def ease_out_elastic(t: float) -> float:
    """Elastic ease-out (spring-like oscillation)."""
    t = _clamp01(t)
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * c4) + 1.0


def lerp(a: float, b: float, t: float, ease: Optional[EasingFn] = None) -> float:
    """Linearly interpolate from a to b, optionally applying an easing curve.

    Args:
        a: Start value.
        b: End value.
        t: Progress in [0, 1] (clamped).
        ease: Optional easing function to apply to t before interpolation.

    Returns:
        Interpolated value between a and b.
    """
    t = _clamp01(t)
    if ease is not None:
        t = ease(t)
    return a + (b - a) * t


def lerp_color(
    c1: tuple[int, ...],
    c2: tuple[int, ...],
    t: float,
    ease: Optional[EasingFn] = None,
) -> tuple[int, ...]:
    """Interpolate between two RGB or RGBA color tuples.

    Args:
        c1: Start color (3 or 4 channels).
        c2: End color (same length as c1).
        t: Progress in [0, 1] (clamped).
        ease: Optional easing function.

    Returns:
        Interpolated color tuple with integer channels clamped to [0, 255].
    """
    t = _clamp01(t)
    if ease is not None:
        t = ease(t)
    return tuple(max(0, min(255, int(c1[i] + (c2[i] - c1[i]) * t))) for i in range(len(c1)))


# ---------------------------------------------------------------------------
# Tween: interpolates a value from start to end over a duration
# ---------------------------------------------------------------------------


class Tween:
    """Interpolates a numeric value over time using an easing function.

    Args:
        start: Initial value.
        end: Target value.
        duration: Time in seconds.
        easing: Easing function (default: ease_out_quad).
        on_complete: Optional callback when tween finishes.
    """

    def __init__(
        self,
        start: float,
        end: float,
        duration: float,
        easing: EasingFn = ease_out_quad,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self._start = start
        self._end = end
        self._duration = max(duration, 0.0)
        self._easing = easing
        self._on_complete = on_complete
        self._elapsed = 0.0
        self._finished = False
        self._callback_fired = False

    @property
    def value(self) -> float:
        """Current interpolated value."""
        if self._duration <= 0.0:
            if self._finished:
                return self._end
            return self._start
        t = self._easing(min(self._elapsed / self._duration, 1.0))
        return self._start + (self._end - self._start) * t

    @property
    def finished(self) -> bool:
        """Whether the tween has completed."""
        return self._finished

    def update(self, dt: float) -> None:
        """Advance the tween by dt seconds.

        Args:
            dt: Delta time in seconds.
        """
        if self._finished:
            return
        self._elapsed += dt
        if self._elapsed >= self._duration:
            self._elapsed = self._duration
            self._finished = True
            if self._on_complete and not self._callback_fired:
                self._callback_fired = True
                self._on_complete()

    def reset(self) -> None:
        """Reset the tween to its initial state."""
        self._elapsed = 0.0
        self._finished = False
        self._callback_fired = False


# ---------------------------------------------------------------------------
# TweenGroup: manages multiple tweens, auto-removes finished ones
# ---------------------------------------------------------------------------


class TweenGroup:
    """Manages a collection of tweens, updating and pruning them together."""

    def __init__(self) -> None:
        self._tweens: list[Tween] = []

    def add(self, tween: Tween) -> None:
        """Add a tween to the group."""
        self._tweens.append(tween)

    def update(self, dt: float) -> None:
        """Update all tweens and remove finished ones.

        Args:
            dt: Delta time in seconds.
        """
        for tw in self._tweens:
            tw.update(dt)
        self._tweens = [tw for tw in self._tweens if not tw.finished]

    def clear(self) -> None:
        """Remove all tweens."""
        self._tweens.clear()

    def is_empty(self) -> bool:
        """Return True if no active tweens remain."""
        return len(self._tweens) == 0

    def __len__(self) -> int:
        return len(self._tweens)
