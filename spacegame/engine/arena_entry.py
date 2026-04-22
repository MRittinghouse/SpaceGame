"""Arena entry animation timeline (Combat overhaul §4.8).

A 1.5-second scripted sequence that opens every combat encounter. Sets
up tension + commitment beat so combat reads as "fight commences" rather
than "button opens menu".

Timeline (spec §4.8)::

    t=0.0  Scene transition end. Camera enters arena at WIDE zoom.
    t=0.3  Danger-level tint fades in over 500ms. Dust motes appear.
    t=0.5  Camera pushes in toward FOCUS_PLAYER over 600ms. Player ship's
           engine emissive ignites from dim to normal intensity.
    t=1.1  Camera reaches DEFAULT. Enemies slide in from right over 400ms,
           each staggered 100ms for a wave effect.
    t=1.5  Normal combat resumes, first turn begins.

This module provides only the **timeline** — a pure-data clock that
exposes alpha/offset factors. The combat view consumes these factors at
render time and drives its camera + ship-entry + atmosphere accordingly.
Keeping the animation coupling-free makes it testable without pygame and
reusable if other scenes need similar choreography.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Timeline constants (spec §4.8)
# ---------------------------------------------------------------------------

_TINT_START = 0.3
_TINT_DURATION = 0.5
_CAMERA_PUSH_START = 0.5
_CAMERA_PUSH_DURATION = 0.6
_ENEMY_SLIDE_START = 1.1
_ENEMY_SLIDE_DURATION = 0.4
_ENEMY_STAGGER = 0.1
TOTAL_DURATION = 1.5

# Slide-in horizontal offset: enemies start this many pixels to the right
# of their rest position. Negative because camera-space "right" is positive
# x; we offset in the positive-x direction pre-animation.
DEFAULT_SLIDE_OFFSET_PX = 80.0


# ---------------------------------------------------------------------------
# Phase enum (informational)
# ---------------------------------------------------------------------------


class ArenaEntryPhase(Enum):
    """Named phases of the entry animation, returned by ``phase``."""

    INTRO = "intro"  # t=0.0-0.3: camera WIDE, nothing else on screen yet
    TINT_FADE = "tint_fade"  # t=0.3-0.5: atmosphere fading in
    CAMERA_PUSH = "camera_push"  # t=0.5-1.1: camera closes on player
    ENEMY_ENTRY = "enemy_entry"  # t=1.1-1.5: enemies slide in from right
    COMPLETE = "complete"  # t>=1.5: animation done


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@dataclass
class ArenaEntry:
    """1.5-second arena entry timeline.

    Construct once at combat start, call :meth:`update(dt)` every frame,
    query factors (:attr:`tint_alpha_factor`, :attr:`dust_alpha_factor`,
    :attr:`player_engine_ignite_factor`, :meth:`enemy_slide_offset`) each
    render pass. The timeline clamps at ``TOTAL_DURATION`` and reports
    ``is_complete = True`` thereafter.
    """

    enemy_count: int = 0
    slide_offset_px: float = DEFAULT_SLIDE_OFFSET_PX
    elapsed: float = 0.0

    # ---- lifecycle --------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the timeline by ``dt`` seconds. Negative dt is ignored."""
        if dt <= 0:
            return
        self.elapsed = min(self.elapsed + dt, TOTAL_DURATION)

    def reset(self) -> None:
        """Rewind to the start of the timeline."""
        self.elapsed = 0.0

    @property
    def is_complete(self) -> bool:
        return self.elapsed >= TOTAL_DURATION

    # ---- phase reporting --------------------------------------------------

    @property
    def phase(self) -> ArenaEntryPhase:
        t = self.elapsed
        if t < _TINT_START:
            return ArenaEntryPhase.INTRO
        if t < _CAMERA_PUSH_START:
            return ArenaEntryPhase.TINT_FADE
        if t < _ENEMY_SLIDE_START:
            return ArenaEntryPhase.CAMERA_PUSH
        if t < TOTAL_DURATION:
            return ArenaEntryPhase.ENEMY_ENTRY
        return ArenaEntryPhase.COMPLETE

    # ---- query helpers ----------------------------------------------------

    @property
    def tint_alpha_factor(self) -> float:
        """Multiplier 0.0-1.0 to apply to the danger-level tint alpha.

        0.0 before tint fade begins, linear ramp during fade, 1.0 after.
        """
        t = self.elapsed
        if t < _TINT_START:
            return 0.0
        if t >= _TINT_START + _TINT_DURATION:
            return 1.0
        return (t - _TINT_START) / _TINT_DURATION

    @property
    def dust_alpha_factor(self) -> float:
        """Dust motes fade in on the same schedule as the danger tint."""
        return self.tint_alpha_factor

    @property
    def player_engine_ignite_factor(self) -> float:
        """Player engine emissive ramps from dim (0.35) to full (1.0) during
        the camera push phase.

        Returns a scalar in [0.35, 1.0]. Combat view multiplies engine
        emissive intensity by this to visualize the "ignition" beat.
        """
        dim = 0.35
        t = self.elapsed
        if t < _CAMERA_PUSH_START:
            return dim
        if t >= _CAMERA_PUSH_START + _CAMERA_PUSH_DURATION:
            return 1.0
        progress = (t - _CAMERA_PUSH_START) / _CAMERA_PUSH_DURATION
        return dim + (1.0 - dim) * progress

    @property
    def camera_push_factor(self) -> float:
        """0.0 when camera should be at WIDE, 1.0 at DEFAULT.

        Combat view uses this to interpolate between WIDE and DEFAULT
        camera states during the push phase.
        """
        t = self.elapsed
        if t < _CAMERA_PUSH_START:
            return 0.0
        if t >= _CAMERA_PUSH_START + _CAMERA_PUSH_DURATION:
            return 1.0
        return (t - _CAMERA_PUSH_START) / _CAMERA_PUSH_DURATION

    def enemy_slide_offset(self, enemy_index: int) -> float:
        """Return the x-offset (pixels, positive = right of rest) for enemy
        ``enemy_index``.

        Enemies stagger by ``_ENEMY_STAGGER`` seconds — enemy 0 starts at
        t=1.1, enemy 1 at t=1.2, etc. Each slides for 400ms from
        ``slide_offset_px`` to 0.
        """
        start = _ENEMY_SLIDE_START + enemy_index * _ENEMY_STAGGER
        if self.elapsed < start:
            return self.slide_offset_px
        if self.elapsed >= start + _ENEMY_SLIDE_DURATION:
            return 0.0
        progress = (self.elapsed - start) / _ENEMY_SLIDE_DURATION
        # Ease-out: slow to settle
        eased = 1.0 - (1.0 - progress) * (1.0 - progress)
        return self.slide_offset_px * (1.0 - eased)

    def enemy_alpha_factor(self, enemy_index: int) -> float:
        """Enemy fade-in alpha: 0 before the enemy's slide starts, 1 after
        the slide is ~50% through."""
        start = _ENEMY_SLIDE_START + enemy_index * _ENEMY_STAGGER
        if self.elapsed < start:
            return 0.0
        if self.elapsed >= start + _ENEMY_SLIDE_DURATION * 0.5:
            return 1.0
        return (self.elapsed - start) / (_ENEMY_SLIDE_DURATION * 0.5)
