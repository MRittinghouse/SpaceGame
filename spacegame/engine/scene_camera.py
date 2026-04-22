"""Shared 2D camera primitive used by combat, builder, galaxy, mining,
salvage, station hub, and ground exploration views.

Tracks offset + zoom + shake state with smooth eased transitions and
per-layer parallax factors. Consumer views define their own state
machines that call transition_to / add_shake / set_parallax_factor.

See requirements/overhaul/91_scene_camera_api.md for the full spec.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from spacegame.engine.easing import EasingFn, ease_out_cubic

# ---------------------------------------------------------------------------
# ShakeSource — individual shake event
# ---------------------------------------------------------------------------


def _linear_decay(t: float) -> float:
    """Default decay curve: amplitude scales from 1.0 at t=0 to 0.0 at t=1."""
    if t < 0.0:
        return 1.0
    if t > 1.0:
        return 0.0
    return 1.0 - t


@dataclass
class ShakeSource:
    """A single shake event. Multiple shakes compose additively via SceneCamera."""

    amplitude: float
    duration: float
    elapsed: float = 0.0
    frequency: float = 30.0
    decay: Callable[[float], float] = field(default=_linear_decay)

    @property
    def alive(self) -> bool:
        """True while elapsed < duration."""
        return self.elapsed < self.duration

    def current_offset(self) -> tuple[float, float]:
        """Return (dx, dy) offset contribution for this frame.

        Returns (0.0, 0.0) once the shake has expired.
        """
        if not self.alive or self.duration <= 0.0:
            return (0.0, 0.0)
        t = self.elapsed / self.duration
        scale = self.amplitude * self.decay(t)
        # Two axes with slightly different phases to avoid 1D-looking motion.
        phase_x = self.elapsed * self.frequency * 2.0 * math.pi
        phase_y = self.elapsed * self.frequency * 2.0 * math.pi * 1.3
        return (math.sin(phase_x) * scale, math.sin(phase_y) * scale)


# ---------------------------------------------------------------------------
# SceneCamera — the shared primitive
# ---------------------------------------------------------------------------


@dataclass
class SceneCamera:
    """Shared 2D camera. Used by every view that needs smooth transitions,
    composable shake, and per-layer parallax.

    Consumer views:
        - Create a SceneCamera instance in their __init__.
        - Call update(dt) each frame.
        - Call transition_to(...) on state changes.
        - Call add_shake(...) on impact events.
        - Register parallax layers via set_parallax_factor(layer_id, factor).
        - Use world_to_screen(world_pos, screen_center, layer) during render.
    """

    # Current transform
    offset: tuple[float, float] = (0.0, 0.0)
    zoom: float = 1.0

    # Target transform (interpolated toward)
    target_offset: tuple[float, float] = (0.0, 0.0)
    target_zoom: float = 1.0

    # Transition interpolation state
    _origin_offset: tuple[float, float] = (0.0, 0.0)
    _origin_zoom: float = 1.0
    _transition_elapsed: float = 0.0
    _transition_duration: float = 0.0
    _transition_ease: EasingFn = field(default=ease_out_cubic)

    # Active shake sources; compose additively
    _shakes: list[ShakeSource] = field(default_factory=list)

    # Parallax layer factors; 1.0 = full motion, 0.0 = static
    parallax_factors: dict[int, float] = field(default_factory=dict)

    # Optional pan bounds (min_x, min_y, max_x, max_y); unused if None
    pan_bounds: Optional[tuple[float, float, float, float]] = None

    def __post_init__(self) -> None:
        # Mirror current state to targets unless explicitly set. This prevents
        # partial-argument transitions (e.g., transition_to(offset=...)) from
        # inheriting stale target_zoom/target_offset defaults.
        if self.target_offset == (0.0, 0.0) and self.offset != (0.0, 0.0):
            self.target_offset = self.offset
        if self.target_zoom == 1.0 and self.zoom != 1.0:
            self.target_zoom = self.zoom
        self._origin_offset = self.offset
        self._origin_zoom = self.zoom

    # -----------------------------------------------------------------
    # Transitions
    # -----------------------------------------------------------------

    def transition_to(
        self,
        offset: Optional[tuple[float, float]] = None,
        zoom: Optional[float] = None,
        duration: float = 0.5,
        ease: Optional[EasingFn] = None,
    ) -> None:
        """Begin an eased transition to the given target transform.

        Either or both of offset/zoom can be specified; unspecified values
        keep their current targets. Replaces any in-flight transition,
        interpolating from the current (partial) position.

        Args:
            offset: Target (x, y) offset. None = keep current target.
            zoom: Target zoom multiplier. None = keep current target.
            duration: Seconds until arrival.
            ease: Curve function mapping 0..1 -> 0..1. Defaults to ease_out_cubic.
        """
        # Snapshot current as the new transition origin (preserves partial
        # progress when replacing an in-flight transition).
        self._origin_offset = self.offset
        self._origin_zoom = self.zoom

        # Update targets; unspecified fields keep their current targets.
        if offset is not None:
            self.target_offset = offset
        if zoom is not None:
            self.target_zoom = zoom

        self._transition_elapsed = 0.0
        self._transition_duration = max(duration, 0.0)
        self._transition_ease = ease if ease is not None else ease_out_cubic

        # Zero-duration transition: snap immediately.
        if self._transition_duration <= 0.0:
            self.offset = self.target_offset
            self.zoom = self.target_zoom

    def reset_immediate(
        self,
        offset: tuple[float, float] = (0.0, 0.0),
        zoom: float = 1.0,
    ) -> None:
        """Snap current and target state to the given transform without animation."""
        self.offset = offset
        self.zoom = zoom
        self.target_offset = offset
        self.target_zoom = zoom
        self._origin_offset = offset
        self._origin_zoom = zoom
        self._transition_elapsed = 0.0
        self._transition_duration = 0.0

    # -----------------------------------------------------------------
    # Shake
    # -----------------------------------------------------------------

    def add_shake(
        self,
        amplitude: float,
        duration: float,
        frequency: float = 30.0,
        decay: Optional[Callable[[float], float]] = None,
    ) -> None:
        """Add a shake source. Multiple active shakes compose additively.

        Args:
            amplitude: Peak offset in pixels.
            duration: Total seconds.
            frequency: Oscillation frequency (Hz).
            decay: 0..1 -> 0..1 amplitude scaling curve. Default: linear decay.
        """
        self._shakes.append(
            ShakeSource(
                amplitude=amplitude,
                duration=duration,
                frequency=frequency,
                decay=decay if decay is not None else _linear_decay,
            )
        )

    def clear_shakes(self) -> None:
        """Remove all active shake sources immediately."""
        self._shakes.clear()

    # -----------------------------------------------------------------
    # Per-frame update
    # -----------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance camera state by `dt` seconds.

        Interpolates offset and zoom toward targets. Advances shake sources
        and prunes dead ones. Call once per frame.
        """
        # Advance transition
        if self._transition_duration > 0.0:
            self._transition_elapsed += dt
            if self._transition_elapsed >= self._transition_duration:
                # Arrived
                self.offset = self.target_offset
                self.zoom = self.target_zoom
                self._transition_elapsed = self._transition_duration
                self._transition_duration = 0.0
            else:
                t_raw = self._transition_elapsed / self._transition_duration
                t_eased = self._transition_ease(t_raw)
                ox, oy = self._origin_offset
                tx, ty = self.target_offset
                self.offset = (
                    ox + (tx - ox) * t_eased,
                    oy + (ty - oy) * t_eased,
                )
                self.zoom = self._origin_zoom + (self.target_zoom - self._origin_zoom) * t_eased

        # Clamp to pan bounds if configured
        if self.pan_bounds is not None:
            min_x, min_y, max_x, max_y = self.pan_bounds
            x = max(min_x, min(self.offset[0], max_x))
            y = max(min_y, min(self.offset[1], max_y))
            self.offset = (x, y)

        # Advance shakes and prune dead ones
        if self._shakes:
            for shake in self._shakes:
                shake.elapsed += dt
            self._shakes = [s for s in self._shakes if s.alive]

    # -----------------------------------------------------------------
    # Transform queries
    # -----------------------------------------------------------------

    def get_offset(self) -> tuple[float, float]:
        """Current camera offset including stacked shake contributions."""
        ox, oy = self.offset
        for shake in self._shakes:
            sx, sy = shake.current_offset()
            ox += sx
            oy += sy
        return (ox, oy)

    def get_shake_offset(self) -> tuple[float, float]:
        """Only the shake contribution, excluding pan. For UI elements that
        should shake-with-impact but stay anchored (not pan with camera).
        """
        ox, oy = 0.0, 0.0
        for shake in self._shakes:
            sx, sy = shake.current_offset()
            ox += sx
            oy += sy
        return (ox, oy)

    def get_zoom(self) -> float:
        """Current camera zoom factor."""
        return self.zoom

    def get_transform(self) -> tuple[tuple[float, float], float]:
        """Convenience: return ((offset_x, offset_y), zoom) including shake."""
        return (self.get_offset(), self.zoom)

    def get_layer_offset(self, layer: int) -> tuple[float, float]:
        """Parallax-scaled offset for a rendering layer.

        Layers with registered factor < 1.0 drift less than foreground.
        Unregistered layers default to factor 1.0 (full camera motion).
        """
        factor = self.parallax_factors.get(layer, 1.0)
        ox, oy = self.get_offset()
        return (ox * factor, oy * factor)

    def world_to_screen(
        self,
        world_pos: tuple[float, float],
        screen_center: tuple[float, float],
        layer: int = 1,
    ) -> tuple[float, float]:
        """Transform a world position to screen coordinates.

        Applies layer parallax, camera offset, zoom, and screen centering.

        Args:
            world_pos: (x, y) in world coordinates.
            screen_center: (cx, cy) typically (view_width/2, view_height/2).
            layer: Rendering layer for parallax selection. Default 1.

        Returns:
            (screen_x, screen_y) pixel coordinates.
        """
        wx, wy = world_pos
        cam_x, cam_y = self.get_layer_offset(layer)
        cx, cy = screen_center
        # Apply camera (subtract camera position from world) then zoom around origin
        # then translate to screen center.
        screen_x = (wx - cam_x) * self.zoom + cx
        screen_y = (wy - cam_y) * self.zoom + cy
        return (screen_x, screen_y)

    # -----------------------------------------------------------------
    # Parallax registration
    # -----------------------------------------------------------------

    def set_parallax_factor(self, layer: int, factor: float) -> None:
        """Register or update the parallax factor for a rendering layer."""
        self.parallax_factors[layer] = factor

    def get_parallax_factor(self, layer: int) -> float:
        """Return registered factor for layer, or 1.0 if unregistered."""
        return self.parallax_factors.get(layer, 1.0)

    # -----------------------------------------------------------------
    # State queries
    # -----------------------------------------------------------------

    @property
    def is_transitioning(self) -> bool:
        """True while a transition is in flight."""
        return self._transition_duration > 0.0

    @property
    def transition_progress(self) -> float:
        """0.0 (just started) .. 1.0 (arrived). Returns 1.0 when idle."""
        if self._transition_duration <= 0.0:
            return 1.0
        return min(self._transition_elapsed / self._transition_duration, 1.0)

    @property
    def has_active_shakes(self) -> bool:
        """True if any shake source is currently contributing offset."""
        return any(s.alive for s in self._shakes)
