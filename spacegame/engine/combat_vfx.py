"""Combat visual effects: shields, damage states, destruction, and atmosphere.

ShieldRenderer manages per-ship shield bubble overlays with hit ripples
and break/restore sequences. DamageStateManager tracks progressive visual
degradation (smoke, sparks) and hit recoil effects. DestructionSequence
orchestrates spectacular ship explosion timelines. All colors route
through ``engine.material_palette`` per Combat overhaul §4.5.
"""

import math
import random as _random
from dataclasses import dataclass, field
from typing import Optional

import pygame

from spacegame.config import scale_x
from spacegame.engine.material_palette import get_role

# ==========================================================================
# Shield Visualization
# ==========================================================================

# Shield element → palette role for the bubble fill (spec §4.5).
# Default cryo_fractal reads as a cyan ice barrier; ion_arc reads as
# violet electrical containment. New shield elements add an entry here.
_SHIELD_ELEMENT_ROLE: dict[str, str] = {
    "cryo": "cryo_fractal",
    "ion": "ion_arc",
}
_DEFAULT_SHIELD_ELEMENT = "cryo"


def _shield_color_for(element: Optional[str]) -> tuple[int, int, int]:
    """Resolve shield bubble + ripple color from an element identifier."""
    key = (element or _DEFAULT_SHIELD_ELEMENT).lower()
    role = _SHIELD_ELEMENT_ROLE.get(key, _SHIELD_ELEMENT_ROLE[_DEFAULT_SHIELD_ELEMENT])
    return get_role(role)


@dataclass
class ShieldState:
    """Visual state for one ship's shield."""

    active: bool = False
    ratio: float = 1.0  # 0.0-1.0 shield fullness
    element: Optional[str] = None  # "cryo" (default) or "ion"

    # Idle shimmer
    shimmer_phase: float = 0.0

    # Hit ripple (triggered on shield damage)
    ripple_timer: float = 0.0
    ripple_max: float = 0.25
    ripple_angle: float = 0.0  # Radians — direction of incoming hit

    # Break sequence (shields drop to 0)
    breaking: bool = False
    break_timer: float = 0.0
    break_max: float = 0.4
    _break_fragments: list[dict] = field(default_factory=list)

    # Restore sequence (shields come back from 0)
    restoring: bool = False
    restore_timer: float = 0.0
    restore_max: float = 0.3


class ShieldRenderer:
    """Manages shield bubble visualization for all ships in combat.

    Each ship tracked by a string key (e.g., "player", "enemy_0").
    """

    def __init__(self) -> None:
        self._states: dict[str, ShieldState] = {}

    def clear(self) -> None:
        """Reset all shield states."""
        self._states.clear()

    def set_shield(self, key: str, ratio: float, max_shields: int) -> None:
        """Update shield ratio for a ship.

        Automatically triggers break/restore sequences when shields
        transition to/from zero.

        Args:
            key: Ship identifier.
            ratio: Current shields / max shields (0.0-1.0).
            max_shields: Maximum shield value (0 = no shields).
        """
        if max_shields <= 0:
            self._states.pop(key, None)
            return

        if key not in self._states:
            self._states[key] = ShieldState(active=ratio > 0, ratio=ratio)
            return

        state = self._states[key]
        old_active = state.active
        state.ratio = ratio
        state.active = ratio > 0

        # Detect break: was active, now zero
        if old_active and not state.active and not state.breaking:
            state.breaking = True
            state.break_timer = state.break_max
            state._break_fragments = self._generate_break_fragments()

        # Detect restore: was inactive, now active
        if not old_active and state.active and not state.restoring:
            state.restoring = True
            state.restore_timer = state.restore_max

    def trigger_ripple(self, key: str, angle: float = 0.0) -> None:
        """Trigger a shield impact ripple.

        Args:
            key: Ship identifier.
            angle: Direction of incoming hit in radians.
        """
        state = self._states.get(key)
        if state and state.active:
            state.ripple_timer = state.ripple_max
            state.ripple_angle = angle

    def update(self, dt: float) -> None:
        """Advance all shield animations.

        Args:
            dt: Delta time in seconds.
        """
        for state in self._states.values():
            # Idle shimmer
            state.shimmer_phase += dt

            # Ripple decay
            if state.ripple_timer > 0:
                state.ripple_timer = max(0.0, state.ripple_timer - dt)

            # Break sequence
            if state.breaking:
                state.break_timer -= dt
                for frag in state._break_fragments:
                    frag["x"] += frag["vx"] * dt
                    frag["y"] += frag["vy"] * dt
                    frag["vy"] += 60 * dt  # Gravity
                    frag["alpha"] = max(0, frag["alpha"] - dt * 400)
                if state.break_timer <= 0:
                    state.breaking = False
                    state._break_fragments.clear()

            # Restore sequence
            if state.restoring:
                state.restore_timer -= dt
                if state.restore_timer <= 0:
                    state.restoring = False

    def render(self, screen: pygame.Surface, key: str, cx: int, cy: int, radius: int) -> None:
        """Render shield effects for a ship.

        Args:
            screen: Surface to draw on.
            key: Ship identifier.
            cx: Ship center X.
            cy: Ship center Y.
            radius: Ship sprite radius (half of largest dimension).
        """
        state = self._states.get(key)
        if state is None:
            return

        bubble_r = radius + scale_x(8)
        bubble_color = _shield_color_for(state.element)

        # Break fragments
        if state.breaking:
            for frag in state._break_fragments:
                if frag["alpha"] > 0:
                    fx = cx + int(frag["x"])
                    fy = cy + int(frag["y"])
                    size = scale_x(4)
                    frag_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    alpha = int(min(255, frag["alpha"]))
                    pygame.draw.polygon(
                        frag_surf,
                        (*bubble_color, alpha),
                        [(size, 0), (size * 2, size * 2), (0, size * 2)],
                    )
                    screen.blit(frag_surf, (fx - size, fy - size))
            return  # Don't draw bubble during break

        # Restore sequence — bubble fading in
        if state.restoring:
            t = 1.0 - state.restore_timer / state.restore_max
            alpha = int(30 * t)
            self._draw_bubble(screen, cx, cy, bubble_r, alpha, bubble_color)
            return

        # Active shield bubble
        if state.active:
            # Base shimmer alpha (gentle oscillation)
            shimmer = 0.5 + 0.5 * math.sin(state.shimmer_phase * math.pi)
            base_alpha = int(20 + 12 * shimmer)
            self._draw_bubble(screen, cx, cy, bubble_r, base_alpha, bubble_color)

            # Ripple effect on hit
            if state.ripple_timer > 0:
                ripple_t = state.ripple_timer / state.ripple_max
                self._draw_ripple(
                    screen, cx, cy, bubble_r, ripple_t, state.ripple_angle, bubble_color
                )

    @staticmethod
    def _draw_bubble(
        screen: pygame.Surface,
        cx: int,
        cy: int,
        radius: int,
        alpha: int,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a translucent shield bubble."""
        size = radius * 2 + 4
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        pygame.draw.circle(surf, (*color, alpha), (center, center), radius)
        edge_alpha = min(255, alpha * 3)
        pygame.draw.circle(surf, (*color, edge_alpha), (center, center), radius, 2)
        screen.blit(surf, (cx - center, cy - center))

    @staticmethod
    def _draw_ripple(
        screen: pygame.Surface,
        cx: int,
        cy: int,
        radius: int,
        t: float,
        angle: float,
        color: tuple[int, int, int],
    ) -> None:
        """Draw expanding concentric ripple rings at impact point."""
        impact_x = cx + int(math.cos(angle) * radius * 0.8)
        impact_y = cy + int(math.sin(angle) * radius * 0.8)

        for i in range(3):
            ring_t = t - i * 0.1
            if ring_t <= 0:
                continue
            ring_r = int(scale_x(8) + scale_x(20) * (1.0 - ring_t))
            ring_alpha = int(180 * ring_t)
            ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
            rc = ring_r + 2
            pygame.draw.circle(ring_surf, (*color, ring_alpha), (rc, rc), ring_r, 2)
            screen.blit(ring_surf, (impact_x - rc, impact_y - rc))

    @staticmethod
    def _generate_break_fragments() -> list[dict]:
        """Generate fragment data for shield break effect."""
        rng = _random.Random()
        fragments = []
        for i in range(10):
            angle = (2 * math.pi * i / 10) + rng.uniform(-0.3, 0.3)
            speed = rng.uniform(60, 160)
            fragments.append(
                {
                    "x": 0.0,
                    "y": 0.0,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "alpha": 255.0,
                }
            )
        return fragments


# ==========================================================================
# Damage State Visualization
# ==========================================================================

_SMOKE_COLOR_START = (90, 85, 80)
_SMOKE_COLOR_END = (40, 38, 35)
_SPARK_COLORS = [(255, 200, 60), (255, 160, 30), (255, 120, 20)]


@dataclass
class DamageVisualState:
    """Per-ship damage visual tracking."""

    hull_ratio: float = 1.0

    # Persistent smoke emitter
    smoke_timer: float = 0.0
    smoke_particles: list[dict] = field(default_factory=list)

    # Intermittent spark emitter
    spark_timer: float = 0.0
    spark_particles: list[dict] = field(default_factory=list)

    # Hit recoil (brief position offset on damage)
    recoil_x: float = 0.0
    recoil_y: float = 0.0
    recoil_timer: float = 0.0
    recoil_max: float = 0.12

    # Critical pulse (red outline flash at <25% hull)
    critical_pulse_phase: float = 0.0


class DamageStateManager:
    """Manages progressive visual degradation for ships in combat.

    Tracks per-ship damage state and emits smoke/spark particles
    based on hull percentage.
    """

    def __init__(self) -> None:
        self._states: dict[str, DamageVisualState] = {}
        self._rng = _random.Random(42)

    def clear(self) -> None:
        """Reset all damage states."""
        self._states.clear()

    def set_hull(self, key: str, ratio: float) -> None:
        """Update hull ratio for a ship.

        Args:
            key: Ship identifier.
            ratio: Current hull / max hull (0.0-1.0).
        """
        if key not in self._states:
            self._states[key] = DamageVisualState(hull_ratio=ratio)
        else:
            self._states[key].hull_ratio = ratio

    def trigger_recoil(self, key: str, from_right: bool = True) -> None:
        """Trigger hit recoil on a ship.

        Args:
            key: Ship identifier.
            from_right: True if hit comes from the right (pushes left).
        """
        state = self._states.get(key)
        if state is None:
            return
        state.recoil_x = float(scale_x(-6) if from_right else scale_x(6))
        state.recoil_y = float(self._rng.uniform(-2, 2))
        state.recoil_timer = state.recoil_max

    def get_recoil_offset(self, key: str) -> tuple[int, int]:
        """Get current recoil offset for a ship.

        Args:
            key: Ship identifier.

        Returns:
            (offset_x, offset_y) in pixels. (0, 0) if no recoil active.
        """
        state = self._states.get(key)
        if state is None or state.recoil_timer <= 0:
            return (0, 0)
        t = state.recoil_timer / state.recoil_max
        # Elastic snap-back: strong initial offset, decays with overshoot
        ease = t * t
        return (int(state.recoil_x * ease), int(state.recoil_y * ease))

    def is_critical(self, key: str) -> bool:
        """Check if a ship is in critical state (<25% hull)."""
        state = self._states.get(key)
        return state is not None and state.hull_ratio < 0.25

    def get_critical_pulse_alpha(self, key: str) -> int:
        """Get red pulse alpha for critical-state ships.

        Returns:
            Alpha value 0-80 for the red outline pulse, 0 if not critical.
        """
        state = self._states.get(key)
        if state is None or state.hull_ratio >= 0.25:
            return 0
        pulse = 0.5 + 0.5 * math.sin(state.critical_pulse_phase * 6.0)
        return int(80 * pulse)

    def update(self, dt: float) -> None:
        """Advance all damage visual states.

        Args:
            dt: Delta time in seconds.
        """
        for state in self._states.values():
            # Recoil decay
            if state.recoil_timer > 0:
                state.recoil_timer = max(0.0, state.recoil_timer - dt)

            # Critical pulse
            if state.hull_ratio < 0.25:
                state.critical_pulse_phase += dt

            # Smoke emission (below 50% hull)
            if state.hull_ratio < 0.5:
                smoke_rate = 0.3 if state.hull_ratio < 0.25 else 0.6
                state.smoke_timer += dt
                if state.smoke_timer >= smoke_rate:
                    state.smoke_timer -= smoke_rate
                    state.smoke_particles.append(
                        {
                            "x": self._rng.uniform(-8, 8),
                            "y": 0.0,
                            "vx": self._rng.uniform(-5, 5),
                            "vy": self._rng.uniform(-20, -8),
                            "life": self._rng.uniform(0.8, 1.5),
                            "max_life": 1.5,
                            "size": self._rng.uniform(2, 5),
                        }
                    )

            # Update smoke particles
            for p in state.smoke_particles:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["life"] -= dt
            state.smoke_particles = [p for p in state.smoke_particles if p["life"] > 0]

            # Spark emission (below 75% hull)
            if state.hull_ratio < 0.75:
                spark_rate = (
                    0.4 if state.hull_ratio < 0.25 else (0.8 if state.hull_ratio < 0.5 else 1.5)
                )
                state.spark_timer += dt
                if state.spark_timer >= spark_rate:
                    state.spark_timer -= spark_rate
                    state.spark_particles.append(
                        {
                            "x": self._rng.uniform(-10, 10),
                            "y": self._rng.uniform(-10, 10),
                            "vx": self._rng.uniform(-40, 40),
                            "vy": self._rng.uniform(-60, -20),
                            "life": self._rng.uniform(0.15, 0.35),
                            "max_life": 0.35,
                            "color_idx": self._rng.randint(0, len(_SPARK_COLORS) - 1),
                        }
                    )

            # Update spark particles
            for p in state.spark_particles:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 120 * dt  # Gravity
                p["life"] -= dt
            state.spark_particles = [p for p in state.spark_particles if p["life"] > 0]

    def render(self, screen: pygame.Surface, key: str, cx: int, cy: int) -> None:
        """Render damage effects (smoke, sparks) for a ship.

        Args:
            screen: Surface to draw on.
            key: Ship identifier.
            cx: Ship center X.
            cy: Ship center Y.
        """
        state = self._states.get(key)
        if state is None:
            return

        # Smoke
        for p in state.smoke_particles:
            t = p["life"] / p["max_life"]
            alpha = int(80 * t)
            size = int(p["size"] * (1.0 + (1.0 - t) * 0.5))
            r = int(_SMOKE_COLOR_START[0] * t + _SMOKE_COLOR_END[0] * (1 - t))
            g = int(_SMOKE_COLOR_START[1] * t + _SMOKE_COLOR_END[1] * (1 - t))
            b = int(_SMOKE_COLOR_START[2] * t + _SMOKE_COLOR_END[2] * (1 - t))
            smoke_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke_surf, (r, g, b, alpha), (size, size), size)
            screen.blit(smoke_surf, (cx + int(p["x"]) - size, cy + int(p["y"]) - size))

        # Sparks
        for p in state.spark_particles:
            t = p["life"] / p["max_life"]
            color = _SPARK_COLORS[p["color_idx"]]
            alpha = int(255 * t)
            spark_size = max(1, scale_x(2))
            spark_surf = pygame.Surface((spark_size * 2, spark_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(spark_surf, (*color, alpha), (spark_size, spark_size), spark_size)
            screen.blit(spark_surf, (cx + int(p["x"]) - spark_size, cy + int(p["y"]) - spark_size))

        # Critical red pulse outline
        if state.hull_ratio < 0.25:
            pulse_alpha = self.get_critical_pulse_alpha(key)
            if pulse_alpha > 0:
                pulse_r = scale_x(30)
                pulse_surf = pygame.Surface((pulse_r * 2, pulse_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    pulse_surf,
                    (255, 40, 40, pulse_alpha),
                    (pulse_r, pulse_r),
                    pulse_r,
                    2,
                )
                screen.blit(pulse_surf, (cx - pulse_r, cy - pulse_r))


# ==========================================================================
# Destruction Sequence
# ==========================================================================

# Hull-fragment colors. These represent torn metal — kept as neutral
# steel/rust tones until the §4.1 unified ship pipeline lands and ship
# fragments inherit their parent material's band entries. Tracked in the
# Combat C4 phase per spec §7.
_FRAG_COLORS = [(180, 160, 140), (140, 120, 100), (100, 80, 60)]


def _fire_palette() -> list[tuple[int, int, int]]:
    """Destruction fire gradient — spec §4.5: plasma_core → plasma_hot → glow_warm.

    Resolved at call time so the colorblind remap (§5 of palette spec) can
    flip the gradient without invalidating any cached constant.
    """
    return [
        get_role("plasma_core"),
        get_role("plasma_hot"),
        get_role("glow_warm"),
        get_role("plasma_core"),  # bookend for index variance
    ]


_SECONDARY_EXPLOSION_OFFSETS = [
    (-0.3, -0.2),
    (0.4, 0.1),
    (-0.1, 0.35),
    (0.2, -0.3),
]


class DestructionSequence:
    """Orchestrates a spectacular ship destruction animation.

    Timeline:
        0.00s - Freeze frame (brief pause on killing blow)
        0.05s - White flash expanding from center
        0.20s - Ship fragments fly outward with rotation + gravity
        0.20s - Primary explosion particles burst
        0.30s - Secondary explosions at offset positions
        0.45s - Fire/smoke lingers at center
        0.60s - Fragments slow and fade
        1.10s - Sequence complete, debris remains

    Usage:
        seq = DestructionSequence(x, y, sprite_radius)
        # Each frame:
        seq.update(dt)
        seq.render(screen)
        if seq.finished:
            # Clean up
    """

    # Phase timing (cumulative)
    FREEZE_END = 0.05
    FLASH_END = 0.20
    FRAGMENT_DURATION = 0.8
    TOTAL_DURATION = 1.1

    def __init__(
        self,
        cx: float,
        cy: float,
        sprite_radius: int,
        ship_sprite: Optional[pygame.Surface] = None,
    ) -> None:
        """Start a destruction sequence.

        Args:
            cx: Ship center X at moment of destruction.
            cy: Ship center Y at moment of destruction.
            sprite_radius: Half the ship sprite's largest dimension.
            ship_sprite: Optional ship surface to generate fragments from.
        """
        self.cx = cx
        self.cy = cy
        self.sprite_radius = sprite_radius
        self.elapsed: float = 0.0
        self.finished: bool = False
        self._rng = _random.Random()

        # Freeze frame flag (external code should pause animation queue briefly)
        self.in_freeze: bool = True

        # Flash
        self._flash_radius: float = 0.0
        self._flash_max_radius = float(sprite_radius * 3)

        # Fragments — hull debris flying outward
        self._fragments: list[dict] = self._generate_fragments(sprite_radius)

        # Secondary explosion timers
        self._secondary_timers: list[dict] = []
        for i, (ox_pct, oy_pct) in enumerate(_SECONDARY_EXPLOSION_OFFSETS):
            self._secondary_timers.append(
                {
                    "x": cx + ox_pct * sprite_radius * 2,
                    "y": cy + oy_pct * sprite_radius * 2,
                    "trigger_time": 0.25 + i * 0.08,
                    "fired": False,
                    "flash_timer": 0.0,
                }
            )

        # Lingering fire/smoke at center
        self._fire_particles: list[dict] = []
        self._fire_emit_timer: float = 0.0

        # Persistent debris (stays after sequence finishes)
        self.debris: list[dict] = []

    def _generate_fragments(self, radius: int) -> list[dict]:
        """Generate hull fragment data."""
        rng = self._rng
        fragments = []
        count = rng.randint(5, 8)
        for i in range(count):
            angle = (2 * math.pi * i / count) + rng.uniform(-0.4, 0.4)
            speed = rng.uniform(80, 220)
            size = rng.randint(max(3, radius // 6), max(5, radius // 3))
            fragments.append(
                {
                    "x": 0.0,
                    "y": 0.0,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "rotation": rng.uniform(0, 360),
                    "rot_speed": rng.uniform(-300, 300),  # Degrees/sec
                    "size": size,
                    "alpha": 255.0,
                    "color_idx": rng.randint(0, len(_FRAG_COLORS) - 1),
                }
            )
        return fragments

    def update(self, dt: float) -> None:
        """Advance the destruction sequence.

        Args:
            dt: Delta time in seconds.
        """
        self.elapsed += dt

        # Freeze frame
        if self.elapsed < self.FREEZE_END:
            self.in_freeze = True
            return
        self.in_freeze = False

        # Flash expansion
        if self.elapsed < self.FLASH_END:
            flash_t = (self.elapsed - self.FREEZE_END) / (self.FLASH_END - self.FREEZE_END)
            self._flash_radius = self._flash_max_radius * flash_t

        # Fragment physics
        for frag in self._fragments:
            frag["x"] += frag["vx"] * dt
            frag["y"] += frag["vy"] * dt
            frag["vy"] += 40 * dt  # Slight gravity
            frag["vx"] *= 0.98  # Air resistance
            frag["vy"] *= 0.98
            frag["rotation"] += frag["rot_speed"] * dt
            # Fade out over the full sequence (slow enough to leave debris)
            frag_elapsed = self.elapsed - self.FLASH_END
            total_frag_time = self.TOTAL_DURATION - self.FLASH_END
            if frag_elapsed > total_frag_time * 0.3:
                fade_t = (frag_elapsed - total_frag_time * 0.3) / (total_frag_time * 0.7)
                frag["alpha"] = max(0, 255 * (1.0 - fade_t * 0.85))  # Never fully fades

        # Secondary explosions
        for sec in self._secondary_timers:
            if not sec["fired"] and self.elapsed >= sec["trigger_time"]:
                sec["fired"] = True
                sec["flash_timer"] = 0.15
            if sec["flash_timer"] > 0:
                sec["flash_timer"] -= dt

        # Fire/smoke at center
        if self.FLASH_END < self.elapsed < self.TOTAL_DURATION - 0.2:
            self._fire_emit_timer += dt
            if self._fire_emit_timer >= 0.06:
                self._fire_emit_timer -= 0.06
                rng = self._rng
                self._fire_particles.append(
                    {
                        "x": rng.uniform(-15, 15),
                        "y": rng.uniform(-15, 15),
                        "vx": rng.uniform(-15, 15),
                        "vy": rng.uniform(-35, -10),
                        "life": rng.uniform(0.3, 0.6),
                        "max_life": 0.6,
                        "size": rng.uniform(3, 8),
                        "color_idx": rng.randint(0, len(_fire_palette()) - 1),
                    }
                )

        for p in self._fire_particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._fire_particles = [p for p in self._fire_particles if p["life"] > 0]

        # Sequence complete
        if self.elapsed >= self.TOTAL_DURATION:
            self.finished = True
            # Convert remaining fragments to persistent debris
            for frag in self._fragments:
                if frag["alpha"] > 30:
                    self.debris.append(
                        {
                            "x": self.cx + frag["x"],
                            "y": self.cy + frag["y"],
                            "vx": frag["vx"] * 0.05,  # Very slow drift
                            "vy": frag["vy"] * 0.05,
                            "size": max(2, frag["size"] // 2),
                            "alpha": min(80, frag["alpha"] * 0.3),
                            "color_idx": frag["color_idx"],
                        }
                    )
            self._fragments.clear()
            self._fire_particles.clear()

    def render(self, screen: pygame.Surface) -> None:
        """Render the current frame of the destruction sequence.

        Args:
            screen: Surface to draw on.
        """
        if self.finished:
            self._render_debris(screen)
            return

        if self.in_freeze:
            return  # Nothing to draw during freeze

        cx, cy = int(self.cx), int(self.cy)

        # Expanding white flash
        if self.elapsed < self.FLASH_END and self._flash_radius > 0:
            flash_t = (self.elapsed - self.FREEZE_END) / (self.FLASH_END - self.FREEZE_END)
            flash_alpha = int(220 * (1.0 - flash_t * 0.5))
            r = int(self._flash_radius)
            if r > 0:
                flash_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                # White center fading to orange edge
                pygame.draw.circle(flash_surf, (255, 255, 240, flash_alpha), (r, r), r)
                inner_r = max(1, r // 2)
                pygame.draw.circle(
                    flash_surf, (255, 255, 255, min(255, flash_alpha + 30)), (r, r), inner_r
                )
                screen.blit(flash_surf, (cx - r, cy - r))

        # Fragments
        for frag in self._fragments:
            if frag["alpha"] <= 0:
                continue
            fx = cx + int(frag["x"])
            fy = cy + int(frag["y"])
            size = frag["size"]
            alpha = int(min(255, frag["alpha"]))
            color = _FRAG_COLORS[frag["color_idx"]]

            # Rotated rectangle fragment
            frag_surf = pygame.Surface((size * 2, size), pygame.SRCALPHA)
            pygame.draw.rect(frag_surf, (*color, alpha), (0, 0, size * 2, size))
            # Add bright edge (hot from explosion)
            edge_alpha = min(255, alpha + 40)
            hot_t = max(0, 1.0 - (self.elapsed - self.FLASH_END) / 0.3)
            if hot_t > 0:
                hot_color = (
                    min(255, color[0] + int(100 * hot_t)),
                    min(255, color[1] + int(60 * hot_t)),
                    color[2],
                    int(edge_alpha * hot_t),
                )
                pygame.draw.rect(frag_surf, hot_color, (0, 0, size * 2, 2))

            rotated = pygame.transform.rotate(frag_surf, frag["rotation"])
            screen.blit(rotated, (fx - rotated.get_width() // 2, fy - rotated.get_height() // 2))

        # Secondary explosions
        for sec in self._secondary_timers:
            if sec["flash_timer"] > 0:
                st = sec["flash_timer"] / 0.15
                sr = int(scale_x(20) * st + scale_x(8))
                s_alpha = int(200 * st)
                sx, sy = int(sec["x"]), int(sec["y"])
                sec_surf = pygame.Surface((sr * 2, sr * 2), pygame.SRCALPHA)
                pygame.draw.circle(sec_surf, (255, 220, 150, s_alpha), (sr, sr), sr)
                pygame.draw.circle(
                    sec_surf, (255, 255, 240, min(255, s_alpha + 50)), (sr, sr), max(1, sr // 2)
                )
                screen.blit(sec_surf, (sx - sr, sy - sr))

        # Fire/smoke particles — palette gradient resolved per-frame so
        # colorblind remap stays live.
        fire_palette = _fire_palette()
        for p in self._fire_particles:
            t = p["life"] / p["max_life"]
            color = fire_palette[p["color_idx"] % len(fire_palette)]
            alpha = int(180 * t)
            size = int(p["size"] * (0.5 + 0.5 * t))
            fire_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(fire_surf, (*color, alpha), (size, size), size)
            screen.blit(fire_surf, (cx + int(p["x"]) - size, cy + int(p["y"]) - size))

    def _render_debris(self, screen: pygame.Surface) -> None:
        """Render persistent floating debris after sequence completes."""
        for d in self.debris:
            d["x"] += d["vx"] * 0.016  # Approximate dt
            d["y"] += d["vy"] * 0.016
            size = d["size"]
            alpha = int(d["alpha"])
            if alpha <= 0:
                continue
            color = _FRAG_COLORS[d["color_idx"]]
            debris_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.rect(debris_surf, (*color, alpha), (0, 0, size * 2, size))
            screen.blit(debris_surf, (int(d["x"]) - size, int(d["y"]) - size))


# ==========================================================================
# Combat Atmosphere
# ==========================================================================

# Danger-level atmosphere config. Per spec §4.5, dust motes use the
# canonical ``void_light`` role with a ``glow_cool`` twinkle accent —
# danger differentiation now comes from alpha + density + tint, not from
# off-palette dust hues. Tint colors are resolved at construction time
# from palette roles so they remain colorblind-remappable.
#
# Per spec §4.6, dangerous + crimson tiers add debris streaks; crimson
# also adds a pulsing edge glow. All additions are palette-role sourced.
_ATMOSPHERE: dict[str, dict] = {
    "safe": {
        "dust_alpha": 30,
        "dust_count": 15,
        "tint_role": None,
        "tint_alpha": 0,
        "dust_speed": (3, 10),
        "debris_rate": 0.0,
        "debris_role": None,
        "edge_glow_role": None,
    },
    "moderate": {
        "dust_alpha": 40,
        "dust_count": 22,
        "tint_role": "hud_accent_warm",
        "tint_alpha": 12,
        "dust_speed": (5, 15),
        "debris_rate": 0.0,
        "debris_role": None,
        "edge_glow_role": None,
    },
    "dangerous": {
        "dust_alpha": 50,
        "dust_count": 30,
        "tint_role": "hud_warning",
        "tint_alpha": 18,
        "dust_speed": (6, 18),
        "debris_rate": 0.25,  # 1 streak every 4s — "occasional" per spec
        "debris_role": "hud_warning",
        "edge_glow_role": None,
    },
    "crimson": {
        "dust_alpha": 60,
        "dust_count": 40,
        "tint_role": "hud_critical",
        "tint_alpha": 25,
        "dust_speed": (8, 22),
        "debris_rate": 1.5,  # Heavy debris per spec
        "debris_role": "hud_critical",
        "edge_glow_role": "hud_critical",
    },
}

# Debris streak parameters. Spec §4.6: "elongated streak, 2-3s lifespan".
_DEBRIS_LIFE_RANGE = (2.0, 3.0)
_DEBRIS_LENGTH_RANGE = (28.0, 56.0)
_DEBRIS_WIDTH = 2
_DEBRIS_SPEED_RANGE = (180.0, 360.0)

# Edge-glow pulse envelope. Crimson-tier encounters get a low-alpha
# ``hud_critical`` border that oscillates via sine — faint enough to
# read as ambient mood, not an alarm.
_EDGE_GLOW_BASE_ALPHA = 22
_EDGE_GLOW_AMPLITUDE = 18
_EDGE_GLOW_PERIOD = 2.5  # seconds per full pulse
_EDGE_GLOW_THICKNESS = 10  # pixels inward from arena edge

# Arc-flash (crimson only, spec §4.6): random voltaic-style screen-edge
# flash 1-2 times per minute. Thicker than edge glow; peaks bright then
# decays. Uses ``voltaic_strike`` role per spec's "voltaic-style".
_ARC_FLASH_INTERVAL_RANGE = (30.0, 60.0)  # seconds between flashes
_ARC_FLASH_DURATION = 0.35  # peak → decay
_ARC_FLASH_PEAK_ALPHA = 120
_ARC_FLASH_THICKNESS = 24  # edge band thickness (thicker than glow)


def _atmosphere_dust_color() -> tuple[int, int, int]:
    """Canonical dust-mote color (spec §4.5). Resolved fresh each call."""
    return get_role("void_light")


def _atmosphere_twinkle_color() -> tuple[int, int, int]:
    """Twinkle accent color used at the brightest twinkle phase."""
    return get_role("glow_cool")


@dataclass
class _DustMote:
    """A single floating space dust particle."""

    x: float
    y: float
    vx: float
    vy: float
    size: float
    alpha: float
    twinkle_phase: float
    twinkle_speed: float


@dataclass
class _DebrisStreak:
    """An elongated debris streak drifting across the arena.

    Per spec §4.6, appears at dangerous + crimson danger tiers. 2-3s
    lifespan, direction parallel to velocity vector. Alpha ramps in on
    spawn, holds, fades on expiry.
    """

    x: float
    y: float
    vx: float
    vy: float
    length: float
    life_remaining: float
    max_life: float

    @property
    def alpha_factor(self) -> float:
        """Ramp-in + hold + ramp-out envelope across life_remaining."""
        if self.max_life <= 0:
            return 0.0
        age = self.max_life - self.life_remaining
        # Ramp in first 10% of life.
        if age < self.max_life * 0.10:
            return age / (self.max_life * 0.10)
        # Ramp out last 20%.
        if self.life_remaining < self.max_life * 0.20:
            return self.life_remaining / (self.max_life * 0.20)
        return 1.0


class CombatAtmosphere:
    """Ambient atmosphere for the combat arena.

    Renders floating space dust, danger-level tinting, and an arena
    frame that defines the viewport. Reinforces the tone and setting
    of the star system where combat occurs.
    """

    def __init__(
        self,
        arena_rect: pygame.Rect,
        danger_level: str = "safe",
    ) -> None:
        """Initialize combat atmosphere.

        Args:
            arena_rect: The combat arena bounds.
            danger_level: System danger level (safe/moderate/dangerous).
                Uses "crimson" for Crimson Reach encounters.
        """
        self._arena = arena_rect
        self._danger = danger_level
        self._config = _ATMOSPHERE.get(danger_level, _ATMOSPHERE["safe"])
        self._rng = _random.Random(hash(danger_level) + 777)
        self._elapsed: float = 0.0

        # Generate dust motes
        self._dust: list[_DustMote] = []
        self._spawn_dust()

        # Arena frame surface (pre-rendered)
        self._frame_surface: Optional[pygame.Surface] = None
        self._build_arena_frame()

        # Tint overlay (pre-rendered) — palette-role-derived per spec §4.5.
        self._tint_surface: Optional[pygame.Surface] = None
        tint_role = self._config.get("tint_role")
        tint_alpha = self._config.get("tint_alpha", 0)
        if tint_role and tint_alpha > 0:
            r, g, b = get_role(tint_role)
            self._tint_surface = pygame.Surface(
                (arena_rect.width, arena_rect.height), pygame.SRCALPHA
            )
            self._tint_surface.fill((r, g, b, tint_alpha))

        # Debris + edge-glow state (spec §4.6). Debris list is empty at
        # safe/moderate tiers; spawn_accumulator drives rate-based spawn
        # via update(dt).
        self._debris: list[_DebrisStreak] = []
        self._debris_spawn_accumulator: float = 0.0

        # Arc-flash (crimson-only, spec §4.6). Timer counts down to the
        # next flash; elapsed tracks the current flash's decay. When the
        # danger tier has no edge_glow_role, both stay at sentinel values.
        if self._config.get("edge_glow_role") is not None:
            self._arc_flash_timer: float = self._rng.uniform(*_ARC_FLASH_INTERVAL_RANGE)
        else:
            self._arc_flash_timer = -1.0
        # Initialize elapsed past the duration so no flash renders until
        # the first trigger.
        self._arc_flash_elapsed: float = _ARC_FLASH_DURATION + 1.0

    def _spawn_dust(self) -> None:
        """Generate initial dust mote positions across the arena."""
        count = self._config["dust_count"]
        speed_min, speed_max = self._config["dust_speed"]
        for _ in range(count):
            self._dust.append(
                _DustMote(
                    x=self._rng.uniform(self._arena.left, self._arena.right),
                    y=self._rng.uniform(self._arena.top, self._arena.bottom),
                    vx=self._rng.uniform(speed_min, speed_max),
                    vy=self._rng.uniform(-2, 2),
                    size=self._rng.uniform(1.0, 2.5),
                    alpha=self._rng.uniform(0.4, 1.0),
                    twinkle_phase=self._rng.uniform(0, math.pi * 2),
                    twinkle_speed=self._rng.uniform(1.5, 4.0),
                )
            )

    def _build_arena_frame(self) -> None:
        """Pre-render the arena viewport frame."""
        w = self._arena.width + 4
        h = self._arena.height + 4
        self._frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)

        # Outer border — subtle tech frame
        border_color = (40, 50, 70, 120)
        pygame.draw.rect(self._frame_surface, border_color, (0, 0, w, h), 1)

        # Inner glow line
        glow_color = (60, 80, 110, 60)
        pygame.draw.rect(self._frame_surface, glow_color, (1, 1, w - 2, h - 2), 1)

        # Corner accents (small bright marks at each corner)
        accent_color = (80, 140, 200, 100)
        accent_len = scale_x(12)
        # Top-left
        pygame.draw.line(self._frame_surface, accent_color, (0, 0), (accent_len, 0))
        pygame.draw.line(self._frame_surface, accent_color, (0, 0), (0, accent_len))
        # Top-right
        pygame.draw.line(self._frame_surface, accent_color, (w - 1, 0), (w - 1 - accent_len, 0))
        pygame.draw.line(self._frame_surface, accent_color, (w - 1, 0), (w - 1, accent_len))
        # Bottom-left
        pygame.draw.line(self._frame_surface, accent_color, (0, h - 1), (accent_len, h - 1))
        pygame.draw.line(self._frame_surface, accent_color, (0, h - 1), (0, h - 1 - accent_len))
        # Bottom-right
        pygame.draw.line(
            self._frame_surface, accent_color, (w - 1, h - 1), (w - 1 - accent_len, h - 1)
        )
        pygame.draw.line(
            self._frame_surface, accent_color, (w - 1, h - 1), (w - 1, h - 1 - accent_len)
        )

    def update(self, dt: float) -> None:
        """Advance dust motes, twinkle animations, and debris streaks.

        Args:
            dt: Delta time in seconds.
        """
        self._elapsed += dt

        for mote in self._dust:
            mote.x += mote.vx * dt
            mote.y += mote.vy * dt
            mote.twinkle_phase += mote.twinkle_speed * dt

            # Wrap horizontally (dust drifts right through the arena)
            if mote.x > self._arena.right + 5:
                mote.x = self._arena.left - 5
                mote.y = self._rng.uniform(self._arena.top, self._arena.bottom)

        # Debris streaks — advance position, decay life, prune expired.
        for streak in self._debris:
            streak.x += streak.vx * dt
            streak.y += streak.vy * dt
            streak.life_remaining = max(0.0, streak.life_remaining - dt)
        self._debris = [s for s in self._debris if s.life_remaining > 0]

        # Rate-based spawn. Accumulator advances with dt * rate; whenever
        # it crosses 1.0, spawn a streak and subtract.
        rate = self._config.get("debris_rate", 0.0)
        if rate > 0:
            self._debris_spawn_accumulator += dt * rate
            while self._debris_spawn_accumulator >= 1.0:
                self._spawn_debris_streak()
                self._debris_spawn_accumulator -= 1.0

        # Arc-flash (crimson only). Advance active flash decay and the
        # interval timer. When the timer hits zero, fire a new flash.
        self._arc_flash_elapsed += dt
        if self._arc_flash_timer >= 0:
            self._arc_flash_timer -= dt
            if self._arc_flash_timer <= 0:
                self.trigger_arc_flash()

    def trigger_arc_flash(self) -> None:
        """Fire a new arc-flash and schedule the next one.

        Public so tests can fire deterministically without waiting on
        the random interval timer. No-op for danger tiers that don't
        have arc-flash enabled (safe / moderate / dangerous).
        """
        # Enablement is keyed on the config (not timer value) because
        # the automatic-fire path drives the timer negative just before
        # calling us — a timer-value guard would incorrectly short-circuit.
        if self._config.get("edge_glow_role") is None:
            return
        self._arc_flash_elapsed = 0.0
        self._arc_flash_timer = self._rng.uniform(*_ARC_FLASH_INTERVAL_RANGE)

    @property
    def is_arc_flash_active(self) -> bool:
        return self._arc_flash_elapsed < _ARC_FLASH_DURATION

    def _spawn_debris_streak(self) -> None:
        """Emit one debris streak with random lane + direction + lifespan."""
        speed_min, speed_max = _DEBRIS_SPEED_RANGE
        life_min, life_max = _DEBRIS_LIFE_RANGE
        length_min, length_max = _DEBRIS_LENGTH_RANGE

        # Direction: mostly right-to-left (opposing dust drift so debris
        # reads as incoming hostile matter); slight vertical component.
        vx = -self._rng.uniform(speed_min, speed_max)
        vy = self._rng.uniform(-40.0, 40.0)

        # Spawn just off the right edge at a random y.
        x = self._arena.right + 10
        y = self._rng.uniform(self._arena.top, self._arena.bottom)
        life = self._rng.uniform(life_min, life_max)
        length = self._rng.uniform(length_min, length_max)
        self._debris.append(
            _DebrisStreak(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                length=length,
                life_remaining=life,
                max_life=life,
            )
        )

    def render_background(
        self,
        screen: pygame.Surface,
        alpha_factor: float = 1.0,
    ) -> None:
        """Render atmosphere elements BEHIND ships (tint, dust, debris, glow).

        Call this before rendering ships.

        ``alpha_factor`` scales tint + dust alpha globally (1.0 = normal).
        Combat C3 §4.8 uses this during the ArenaEntry intro to fade
        atmosphere in from 0 → 1 over the tint-fade phase.
        """
        factor = max(0.0, min(1.0, alpha_factor))

        # Danger tint overlay — scaled by factor during intro fade-in.
        if self._tint_surface and factor > 0:
            if factor >= 1.0:
                screen.blit(self._tint_surface, self._arena.topleft)
            else:
                # Stage a faded copy so we don't mutate the cached surface.
                faded = self._tint_surface.copy()
                faded.set_alpha(int(255 * factor))
                screen.blit(faded, self._arena.topleft)

        # Debris streaks — drawn before dust so they appear behind it.
        self._render_debris(screen)

        # Edge glow — crimson-tier only; pulses with sine.
        self._render_edge_glow(screen)

        # Arc-flash — crimson-tier only; brief bright pulse on random
        # timer. Renders above the sustained edge glow so it reads as
        # a distinct event rather than a pulse spike.
        self._render_arc_flash(screen)

        # Space dust — canonical void_light hue, glow_cool twinkle accent.
        dust_base_color = _atmosphere_dust_color()
        twinkle_color = _atmosphere_twinkle_color()
        dust_base_alpha = self._config["dust_alpha"]

        for mote in self._dust:
            if not (self._arena.left - 5 <= mote.x <= self._arena.right + 5):
                continue

            # Twinkle: alpha oscillates gently; at peak twinkle pixels lean
            # toward glow_cool for the "twinkle" accent. ``factor`` scales
            # dust alpha during the ArenaEntry fade-in.
            twinkle = 0.5 + 0.5 * math.sin(mote.twinkle_phase)
            alpha = int(dust_base_alpha * mote.alpha * twinkle * factor)
            if alpha <= 0:
                continue

            color = twinkle_color if twinkle > 0.85 else dust_base_color
            size = max(1, int(mote.size))
            mx, my = int(mote.x), int(mote.y)

            if size <= 1:
                if 0 <= mx < screen.get_width() and 0 <= my < screen.get_height():
                    try:
                        screen.set_at((mx, my), (*color, alpha))
                    except (IndexError, TypeError):
                        pass
            else:
                mote_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(mote_surf, (*color, alpha), (size, size), size)
                screen.blit(mote_surf, (mx - size, my - size))

    def _render_debris(self, screen: pygame.Surface) -> None:
        """Paint each active debris streak as a short oriented line.

        Line direction parallels the streak velocity; color is the
        danger tier's ``debris_role`` RGB. Alpha follows the streak's
        ramp-in/hold/ramp-out envelope.
        """
        if not self._debris:
            return
        role = self._config.get("debris_role")
        if role is None:
            return
        color = get_role(role)
        for streak in self._debris:
            alpha = max(0, min(255, int(200 * streak.alpha_factor)))
            if alpha == 0:
                continue
            # Skip streaks that have drifted out of arena bounds.
            if streak.x < self._arena.left - 20 or streak.x > self._arena.right + 20:
                continue
            if streak.y < self._arena.top - 20 or streak.y > self._arena.bottom + 20:
                continue
            # Draw a short line along the velocity direction.
            speed = math.sqrt(streak.vx * streak.vx + streak.vy * streak.vy)
            if speed <= 0:
                continue
            nx = streak.vx / speed
            ny = streak.vy / speed
            end_x = streak.x + nx * streak.length
            end_y = streak.y + ny * streak.length
            # Render onto an SRCALPHA surface so the line's per-pixel
            # alpha composites over the ship layers beneath it.
            w = int(abs(end_x - streak.x)) + _DEBRIS_WIDTH * 2 + 2
            h = int(abs(end_y - streak.y)) + _DEBRIS_WIDTH * 2 + 2
            if w <= 0 or h <= 0:
                continue
            strip = pygame.Surface((w, h), pygame.SRCALPHA)
            origin_x = int(min(streak.x, end_x)) - 1
            origin_y = int(min(streak.y, end_y)) - 1
            pygame.draw.line(
                strip,
                (*color, alpha),
                (int(streak.x) - origin_x, int(streak.y) - origin_y),
                (int(end_x) - origin_x, int(end_y) - origin_y),
                _DEBRIS_WIDTH,
            )
            screen.blit(strip, (origin_x, origin_y))

    def _render_edge_glow(self, screen: pygame.Surface) -> None:
        """Crimson-tier pulsing edge glow (spec §4.6).

        Paints a ``hud_critical`` frame band around the arena, with
        alpha oscillating via sine so the glow reads as ambient mood.
        No-op for non-crimson tiers.
        """
        role = self._config.get("edge_glow_role")
        if role is None:
            return
        color = get_role(role)
        # Sine pulse: base alpha ± amplitude over the period.
        pulse = math.sin(2.0 * math.pi * self._elapsed / _EDGE_GLOW_PERIOD)
        alpha = max(0, min(255, int(_EDGE_GLOW_BASE_ALPHA + _EDGE_GLOW_AMPLITUDE * pulse)))
        if alpha == 0:
            return
        thickness = _EDGE_GLOW_THICKNESS
        # Four edge rectangles — simpler than a gradient; reads clean at
        # arena scale.
        glow = pygame.Surface((self._arena.width, self._arena.height), pygame.SRCALPHA)
        # Top
        pygame.draw.rect(glow, (*color, alpha), (0, 0, self._arena.width, thickness))
        # Bottom
        pygame.draw.rect(
            glow,
            (*color, alpha),
            (0, self._arena.height - thickness, self._arena.width, thickness),
        )
        # Left
        pygame.draw.rect(glow, (*color, alpha), (0, 0, thickness, self._arena.height))
        # Right
        pygame.draw.rect(
            glow,
            (*color, alpha),
            (self._arena.width - thickness, 0, thickness, self._arena.height),
        )
        screen.blit(glow, self._arena.topleft)

    def _render_arc_flash(self, screen: pygame.Surface) -> None:
        """Crimson-tier arc-flash (spec §4.6).

        Thick ``voltaic_strike`` band on all four edges; alpha peaks at
        flash start and decays linearly over ``_ARC_FLASH_DURATION``.
        No-op when not active or not enabled for the tier.
        """
        if not self.is_arc_flash_active:
            return
        # Only crimson-tier enables arc-flash via the timer; double-check
        # in case the config diverges.
        if self._config.get("edge_glow_role") is None:
            return
        color = get_role("voltaic_strike")
        progress = self._arc_flash_elapsed / _ARC_FLASH_DURATION
        alpha = max(0, min(255, int(_ARC_FLASH_PEAK_ALPHA * (1.0 - progress))))
        if alpha == 0:
            return
        thickness = _ARC_FLASH_THICKNESS
        flash = pygame.Surface((self._arena.width, self._arena.height), pygame.SRCALPHA)
        # Top
        pygame.draw.rect(flash, (*color, alpha), (0, 0, self._arena.width, thickness))
        # Bottom
        pygame.draw.rect(
            flash,
            (*color, alpha),
            (0, self._arena.height - thickness, self._arena.width, thickness),
        )
        # Left
        pygame.draw.rect(flash, (*color, alpha), (0, 0, thickness, self._arena.height))
        # Right
        pygame.draw.rect(
            flash,
            (*color, alpha),
            (self._arena.width - thickness, 0, thickness, self._arena.height),
        )
        screen.blit(flash, self._arena.topleft)

    def render_foreground(self, screen: pygame.Surface) -> None:
        """Render atmosphere elements IN FRONT of ships (arena frame).

        Call this after rendering ships but before particles/UI.

        Args:
            screen: Surface to draw on.
        """
        if self._frame_surface:
            screen.blit(
                self._frame_surface,
                (self._arena.left - 2, self._arena.top - 2),
            )
