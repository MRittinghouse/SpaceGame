"""Dual tech cinematic timeline primitive (Combat overhaul §4.3).

Drives the "stop the world" 3.2-second sequence that plays when two crew
members trigger a combined technique. The timeline reports phase + per-
frame factor queries; rendering is owned by combat view (portrait blit,
screen darken, particle sequencer, impact damage number, camera shake).
Keeping this module factor-only (no pygame dependency) keeps it testable
and reusable — a future solo-ultimate phase can consume the same clock.

Canonical timeline (spec §4.3, Chrono Trigger X-Strike model)::

    t=0.0   CAMERA_ZOOM       camera pushes in on player ship (600ms)
    t=0.6   DARKEN_PORTRAITS  screen → 70% black; portraits slide in
    t=0.9   NAME_HOLD         tech name holds with element-stroke (600ms)
    t=1.5   COMBINED_RESOLVE  combined visual traces across 1200ms
    t=2.7   IMPACT            screen shake +100%, tier-4 damage number
    t=3.2   COMPLETE          normal playback resumes

Ultimate variant extends COMBINED_RESOLVE with a CHARGE phase (t=1.5 to
t=3.0) before impact resolves at t=3.0 and completes at t=4.5.

Element palette per spec §4.3 table. Dual techs combine two element
palette roles — dominant drives the tech-name stroke, secondary drives
the trail / impact flash. Single-element ultimates pass the same element
twice or leave secondary as ``None``.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.3``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from spacegame.engine.material_palette import is_valid_role

# ---------------------------------------------------------------------------
# Element → palette role (spec §4.3 table; consistent with projectiles.py)
# ---------------------------------------------------------------------------

_ELEMENT_EMISSIVE_ROLE: dict[str, str] = {
    "kinetic": "glow_warm",  # No element tint; warm muzzle
    "plasma": "plasma_core",
    "ion": "ion_arc",
    "cryo": "cryo_fractal",
    "voltaic": "voltaic_strike",
}

# Secondary "trail/glow" role per spec §4.3 table.
_ELEMENT_TRAIL_ROLE: dict[str, str] = {
    "kinetic": "glow_warm",
    "plasma": "plasma_hot",
    "ion": "glow_cool",
    "cryo": "glow_cool",
    "voltaic": "voltaic_strike",
}

_DEFAULT_ELEMENT = "plasma"


def resolve_emissive_role(element: Optional[str]) -> str:
    """Dominant-emissive role for an element (tech-name stroke, impact core)."""
    key = (element or _DEFAULT_ELEMENT).lower()
    return _ELEMENT_EMISSIVE_ROLE.get(key, _ELEMENT_EMISSIVE_ROLE[_DEFAULT_ELEMENT])


def resolve_trail_role(element: Optional[str]) -> str:
    """Trail / glow role for an element (particle trail, combined visual sweep)."""
    key = (element or _DEFAULT_ELEMENT).lower()
    return _ELEMENT_TRAIL_ROLE.get(key, _ELEMENT_TRAIL_ROLE[_DEFAULT_ELEMENT])


# ---------------------------------------------------------------------------
# Timing constants (spec §4.3)
# ---------------------------------------------------------------------------

CAMERA_ZOOM_DURATION = 0.6   # t=0.0 → 0.6
PORTRAIT_SLIDE_DURATION = 0.3  # t=0.6 → 0.9
NAME_HOLD_DURATION = 0.6     # t=0.9 → 1.5
COMBINED_RESOLVE_DURATION = 1.2  # t=1.5 → 2.7
IMPACT_DURATION = 0.5        # t=2.7 → 3.2

# Ultimate adds a charge phase between name-hold and impact (t=1.5 → 3.0)
CHARGE_DURATION = 1.5        # spec §4.3 ultimate note: 1.5s charge build

# Derived phase boundaries
_ZOOM_END = CAMERA_ZOOM_DURATION
_DARKEN_END = _ZOOM_END + PORTRAIT_SLIDE_DURATION
_NAME_END = _DARKEN_END + NAME_HOLD_DURATION
_RESOLVE_END = _NAME_END + COMBINED_RESOLVE_DURATION
_CHARGE_END = _NAME_END + CHARGE_DURATION

STANDARD_TOTAL = _RESOLVE_END + IMPACT_DURATION  # 3.2s
ULTIMATE_TOTAL = _CHARGE_END + IMPACT_DURATION  # 4.5s

# Screen darken peak per spec: 70% black.
DARKEN_PEAK_ALPHA = int(255 * 0.70)


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


class DualTechPhase(Enum):
    """Named phases returned by :attr:`DualTechCinematic.phase`."""

    CAMERA_ZOOM = "camera_zoom"
    DARKEN_PORTRAITS = "darken_portraits"
    NAME_HOLD = "name_hold"
    COMBINED_RESOLVE = "combined_resolve"
    CHARGE = "charge"  # Ultimate-only
    IMPACT = "impact"
    COMPLETE = "complete"


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@dataclass
class DualTechCinematic:
    """Pure-data timeline for a dual tech cinematic (spec §4.3).

    Attributes:
        tech_name: Display name shown during NAME_HOLD (e.g. "ICE SPEAR").
        dominant_element: The tech's primary element. Drives the tech-name
            stroke color and the impact flash. Unknown elements fall back
            to plasma.
        secondary_element: The tech's second element (for dual techs).
            Drives the combined-resolve trail. Pass the same value as
            ``dominant_element`` for single-element ultimates.
        is_ultimate: Whether to insert the CHARGE phase (extends total
            duration from 3.2s to 4.5s).
        tech_id: Optional stable identifier (for test + telemetry).
    """

    tech_name: str
    dominant_element: Optional[str] = None
    secondary_element: Optional[str] = None
    is_ultimate: bool = False
    tech_id: str = ""
    elapsed: float = 0.0
    _impact_fired: bool = field(default=False, init=False)

    # ---- resolved roles ---------------------------------------------------

    @property
    def dominant_role(self) -> str:
        return resolve_emissive_role(self.dominant_element)

    @property
    def secondary_role(self) -> str:
        return resolve_emissive_role(self.secondary_element)

    @property
    def trail_role(self) -> str:
        return resolve_trail_role(self.secondary_element or self.dominant_element)

    # ---- timing -----------------------------------------------------------

    @property
    def total_duration(self) -> float:
        return ULTIMATE_TOTAL if self.is_ultimate else STANDARD_TOTAL

    @property
    def is_complete(self) -> bool:
        return self.elapsed >= self.total_duration

    def update(self, dt: float) -> None:
        """Advance the timeline by ``dt`` seconds. Negative dt is ignored."""
        if dt <= 0:
            return
        self.elapsed = min(self.elapsed + dt, self.total_duration)

    def reset(self) -> None:
        """Rewind to the start."""
        self.elapsed = 0.0
        self._impact_fired = False

    # ---- phase reporting --------------------------------------------------

    @property
    def phase(self) -> DualTechPhase:
        t = self.elapsed
        if t < _ZOOM_END:
            return DualTechPhase.CAMERA_ZOOM
        if t < _DARKEN_END:
            return DualTechPhase.DARKEN_PORTRAITS
        if t < _NAME_END:
            return DualTechPhase.NAME_HOLD
        if self.is_ultimate:
            if t < _CHARGE_END:
                return DualTechPhase.CHARGE
            if t < self.total_duration:
                return DualTechPhase.IMPACT
        else:
            if t < _RESOLVE_END:
                return DualTechPhase.COMBINED_RESOLVE
            if t < self.total_duration:
                return DualTechPhase.IMPACT
        return DualTechPhase.COMPLETE

    # ---- factor queries ---------------------------------------------------

    @property
    def camera_zoom_factor(self) -> float:
        """0.0 at start of zoom-in, 1.0 once the camera has fully pushed in.

        Combat view interpolates the SceneCamera from DEFAULT to CINEMATIC
        using this factor. Stays at 1.0 through the remainder of the
        cinematic, then reverts on COMPLETE.
        """
        t = self.elapsed
        if t >= CAMERA_ZOOM_DURATION:
            return 1.0
        return t / CAMERA_ZOOM_DURATION

    @property
    def darken_alpha(self) -> int:
        """Screen-darken overlay alpha 0-255. Ramps during DARKEN_PORTRAITS,
        holds at peak (70%) through NAME_HOLD + CHARGE/RESOLVE, un-darkens
        during the last third of IMPACT so the player sees the impact
        resolution against the normal combat backdrop.
        """
        t = self.elapsed
        if t < _ZOOM_END:
            return 0
        if t < _DARKEN_END:
            progress = (t - _ZOOM_END) / PORTRAIT_SLIDE_DURATION
            return round(DARKEN_PEAK_ALPHA * progress)
        # Hold peak through name/resolve/charge/early-impact.
        resolve_end = _CHARGE_END if self.is_ultimate else _RESOLVE_END
        if t < resolve_end:
            return DARKEN_PEAK_ALPHA
        # Last third of IMPACT phase: un-darken linearly.
        un_darken_start = resolve_end + IMPACT_DURATION * 0.33
        if t >= self.total_duration:
            return 0
        if t < un_darken_start:
            return DARKEN_PEAK_ALPHA
        progress = (t - un_darken_start) / (self.total_duration - un_darken_start)
        return max(0, round(DARKEN_PEAK_ALPHA * (1.0 - progress)))

    @property
    def portrait_slide_factor(self) -> float:
        """0.0 = fully off-screen, 1.0 = fully slid in. Combat view blits
        the left portrait at ``(−W * (1 − factor), h)`` and the right at
        ``(screen_w − W * factor, h)``.

        Portraits start slide at t=0.6, finish at t=0.9, hold, then begin
        fading via :attr:`portrait_alpha` toward the end.
        """
        t = self.elapsed
        if t < _ZOOM_END:
            return 0.0
        if t >= _DARKEN_END:
            return 1.0
        return (t - _ZOOM_END) / PORTRAIT_SLIDE_DURATION

    @property
    def portrait_alpha(self) -> int:
        """Portrait opacity 0-255. Fades out during the last 40% of IMPACT."""
        t = self.elapsed
        if t < _ZOOM_END:
            return 0
        resolve_end = _CHARGE_END if self.is_ultimate else _RESOLVE_END
        if t < resolve_end:
            return 255
        if t >= self.total_duration:
            return 0
        # Fade during IMPACT phase.
        fade_start = resolve_end + IMPACT_DURATION * 0.60
        if t < fade_start:
            return 255
        progress = (t - fade_start) / (self.total_duration - fade_start)
        return max(0, round(255 * (1.0 - progress)))

    @property
    def tech_name_alpha(self) -> int:
        """Tech-name text opacity 0-255. Pops in at start of NAME_HOLD,
        holds full, fades out over the first third of COMBINED_RESOLVE."""
        t = self.elapsed
        if t < _DARKEN_END:
            return 0
        if t < _NAME_END:
            return 255
        # Fade over first 33% of the next phase (resolve or charge).
        next_phase_end = _CHARGE_END if self.is_ultimate else _RESOLVE_END
        fade_duration = (next_phase_end - _NAME_END) * 0.33
        if fade_duration <= 0 or t >= _NAME_END + fade_duration:
            return 0
        progress = (t - _NAME_END) / fade_duration
        return max(0, round(255 * (1.0 - progress)))

    @property
    def combined_resolve_progress(self) -> float:
        """0.0 → 1.0 during COMBINED_RESOLVE (standard) or CHARGE (ultimate).

        Combat view uses this to advance the element-combined particle
        trail. Returns 0.0 before the phase starts, 1.0 after it ends.
        """
        t = self.elapsed
        if t < _NAME_END:
            return 0.0
        phase_end = _CHARGE_END if self.is_ultimate else _RESOLVE_END
        if t >= phase_end:
            return 1.0
        phase_duration = phase_end - _NAME_END
        return (t - _NAME_END) / phase_duration

    @property
    def charge_intensity(self) -> float:
        """Ultimate-only charge build intensity 0.0-1.0.

        Returns 0.0 for non-ultimate cinematics. For ultimates, ramps
        across the CHARGE phase so combat view can build emissive
        particles / screen glow / audio hum leading to impact.
        """
        if not self.is_ultimate:
            return 0.0
        return self.combined_resolve_progress

    @property
    def impact_shake_factor(self) -> float:
        """Screen-shake amplitude multiplier during IMPACT, 0-1.

        Peaks at the start of IMPACT and decays linearly to 0 by the end.
        Spec §4.3 calls for +100% shake at impact — combat view scales
        its baseline shake amplitude by this factor.
        """
        t = self.elapsed
        resolve_end = _CHARGE_END if self.is_ultimate else _RESOLVE_END
        if t < resolve_end or t >= self.total_duration:
            return 0.0
        progress = (t - resolve_end) / IMPACT_DURATION
        return max(0.0, 1.0 - progress)

    def consume_impact_trigger(self) -> bool:
        """Return True exactly once, the first time phase reaches IMPACT.

        Consumers call this each frame during update; when it returns
        True they emit the tier-4 damage number + apply the damage event.
        Subsequent calls return False — guarantees one-shot semantics
        even if the cinematic is queried multiple times per frame.
        """
        if self._impact_fired:
            return False
        resolve_end = _CHARGE_END if self.is_ultimate else _RESOLVE_END
        if self.elapsed < resolve_end:
            return False
        self._impact_fired = True
        return True

    # ---- diagnostics ------------------------------------------------------

    @property
    def is_palette_valid(self) -> bool:
        """True when both resolved roles are canonical PALETTE_ROLES entries."""
        return is_valid_role(self.dominant_role) and is_valid_role(self.secondary_role)
