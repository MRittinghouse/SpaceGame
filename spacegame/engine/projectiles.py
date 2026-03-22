"""Weapon projectile system for combat visual effects.

Manages projectiles that travel from source to target with distinct
visual identities per weapon type: laser beams, missile arcs, and
cannon bursts.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

import pygame

from spacegame.config import Colors, scale_x, scale_y


class WeaponType(Enum):
    """Visual weapon type for projectile rendering."""

    LASER = "laser"
    MISSILE = "missile"
    CANNON = "cannon"
    REPAIR = "repair"


# Weapon colors
_LASER_CORE = (255, 240, 220)
_LASER_GLOW = (255, 120, 40)
_MISSILE_BODY = (200, 210, 220)
_MISSILE_TRAIL = (255, 160, 40)
_CANNON_ROUND = (255, 255, 180)


@dataclass
class Projectile:
    """A single in-flight projectile."""

    start_x: float
    start_y: float
    end_x: float
    end_y: float
    weapon_type: WeaponType
    speed: float  # Pixels per second
    progress: float = 0.0  # 0.0 (launched) to 1.0 (arrived)
    hit: bool = True  # False for misses (deflected trajectory)
    on_impact: Optional[Callable[[], None]] = None
    arc_height: float = 0.0  # Vertical arc for missiles (pixels)

    # Internal state
    _trail_timer: float = 0.0
    _sub_index: int = 0  # For cannon burst sequencing

    @property
    def x(self) -> float:
        """Current X position (linear interpolation)."""
        return self.start_x + (self.end_x - self.start_x) * self.progress

    @property
    def y(self) -> float:
        """Current Y position with optional arc."""
        base_y = self.start_y + (self.end_y - self.start_y) * self.progress
        if self.arc_height != 0.0:
            # Parabolic arc: peaks at progress=0.5
            arc = self.arc_height * 4.0 * self.progress * (1.0 - self.progress)
            base_y -= arc
        return base_y

    @property
    def distance(self) -> float:
        """Total distance from start to end."""
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        return math.sqrt(dx * dx + dy * dy)

    @property
    def angle(self) -> float:
        """Angle in degrees from start to end (for sprite rotation)."""
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        return math.degrees(math.atan2(-dy, dx))


class ProjectileManager:
    """Manages active projectiles and their rendering.

    Projectiles are spawned by the combat animation system and travel
    from source to target over time. On arrival, they trigger impact
    callbacks (particles, screen shake, damage numbers).
    """

    def __init__(self) -> None:
        self._projectiles: list[Projectile] = []
        self._muzzle_flashes: list[dict] = []  # {x, y, timer, max_timer}

    @property
    def has_active(self) -> bool:
        """True if any projectiles are still in flight."""
        return len(self._projectiles) > 0 or len(self._muzzle_flashes) > 0

    def clear(self) -> None:
        """Remove all active projectiles."""
        self._projectiles.clear()
        self._muzzle_flashes.clear()

    def spawn_laser(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        on_impact: Optional[Callable[[], None]] = None,
        hit: bool = True,
    ) -> None:
        """Spawn a laser beam projectile.

        Args:
            start: Source position (weapon mount).
            end: Target position (impact point).
            on_impact: Callback fired when beam reaches target.
            hit: False for misses (beam deflects past target).
        """
        miss_end = end
        if not hit:
            # Deflect past target by 40-80px
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                extend = scale_x(60)
                miss_end = (end[0] + dx / dist * extend, end[1] + dy / dist * extend + scale_y(30))

        self._projectiles.append(Projectile(
            start_x=start[0], start_y=start[1],
            end_x=miss_end[0], end_y=miss_end[1],
            weapon_type=WeaponType.LASER,
            speed=800.0,  # Fast — beam extends quickly
            on_impact=on_impact if hit else None,
            hit=hit,
        ))
        self._muzzle_flashes.append({
            "x": start[0], "y": start[1], "timer": 0.08, "max_timer": 0.08,
        })

    def spawn_missile(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        on_impact: Optional[Callable[[], None]] = None,
        hit: bool = True,
    ) -> None:
        """Spawn a missile with arcing trajectory.

        Args:
            start: Launch position.
            end: Target position.
            on_impact: Callback fired on impact.
            hit: False for misses.
        """
        miss_end = end
        if not hit:
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                extend = scale_x(80)
                miss_end = (end[0] + dx / dist * extend, end[1] + scale_y(40))

        self._projectiles.append(Projectile(
            start_x=start[0], start_y=start[1],
            end_x=miss_end[0], end_y=miss_end[1],
            weapon_type=WeaponType.MISSILE,
            speed=400.0,
            arc_height=float(scale_y(35)),
            on_impact=on_impact if hit else None,
            hit=hit,
        ))
        self._muzzle_flashes.append({
            "x": start[0], "y": start[1], "timer": 0.05, "max_timer": 0.05,
        })

    def spawn_cannon(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        on_impact: Optional[Callable[[], None]] = None,
        hit: bool = True,
        burst_count: int = 3,
    ) -> None:
        """Spawn a burst of cannon rounds.

        Args:
            start: Weapon mount position.
            end: Target position.
            on_impact: Callback fired when last round hits.
            hit: False for misses.
            burst_count: Number of rounds in the burst.
        """
        for i in range(burst_count):
            miss_end = end
            if not hit:
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0:
                    spread = scale_y(15 + i * 10)
                    miss_end = (end[0] + dx / dist * scale_x(50), end[1] + spread)

            # Only the last round triggers the impact callback
            impact_cb = on_impact if (hit and i == burst_count - 1) else None

            proj = Projectile(
                start_x=start[0], start_y=start[1],
                end_x=miss_end[0], end_y=miss_end[1],
                weapon_type=WeaponType.CANNON,
                speed=600.0,
                on_impact=impact_cb,
                hit=hit,
            )
            # Stagger launch: each round delayed slightly
            proj.progress = -(i * 0.08 * 600.0 / max(1.0, proj.distance))
            proj._sub_index = i
            self._projectiles.append(proj)

        self._muzzle_flashes.append({
            "x": start[0], "y": start[1], "timer": 0.12, "max_timer": 0.12,
        })

    def update(self, dt: float) -> None:
        """Advance all projectiles and trigger arrivals.

        Args:
            dt: Delta time in seconds.
        """
        arrived: list[Projectile] = []

        for proj in self._projectiles:
            dist = proj.distance
            if dist > 0:
                proj.progress += (proj.speed * dt) / dist
            else:
                proj.progress = 1.0

            if proj.progress >= 1.0:
                proj.progress = 1.0
                arrived.append(proj)

        for proj in arrived:
            if proj.on_impact is not None:
                proj.on_impact()
            self._projectiles.remove(proj)

        # Update muzzle flashes
        for flash in self._muzzle_flashes[:]:
            flash["timer"] -= dt
            if flash["timer"] <= 0:
                self._muzzle_flashes.remove(flash)

    def render(self, screen: pygame.Surface) -> None:
        """Render all active projectiles and muzzle flashes.

        Args:
            screen: Surface to draw on.
        """
        # Muzzle flashes
        for flash in self._muzzle_flashes:
            t = flash["timer"] / flash["max_timer"]
            radius = int(scale_x(8) * t + scale_x(4))
            alpha = int(220 * t)
            flash_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 240, 200, alpha), (radius, radius), radius)
            screen.blit(flash_surf, (int(flash["x"]) - radius, int(flash["y"]) - radius))

        # Projectiles
        for proj in self._projectiles:
            if proj.progress < 0:
                continue  # Staggered cannon round not yet launched

            if proj.weapon_type == WeaponType.LASER:
                self._render_laser(screen, proj)
            elif proj.weapon_type == WeaponType.MISSILE:
                self._render_missile(screen, proj)
            elif proj.weapon_type == WeaponType.CANNON:
                self._render_cannon(screen, proj)

    def _render_laser(self, screen: pygame.Surface, proj: Projectile) -> None:
        """Render a laser beam that extends from source toward target."""
        # Beam extends progressively (not a dot traveling — a LINE growing)
        beam_end_x = proj.start_x + (proj.end_x - proj.start_x) * proj.progress
        beam_end_y = proj.start_y + (proj.end_y - proj.start_y) * proj.progress

        sx, sy = int(proj.start_x), int(proj.start_y)
        ex, ey = int(beam_end_x), int(beam_end_y)

        # Outer glow (wider, dimmer)
        pygame.draw.line(screen, _LASER_GLOW, (sx, sy), (ex, ey), max(1, scale_x(4)))
        # Inner core (thinner, brighter)
        pygame.draw.line(screen, _LASER_CORE, (sx, sy), (ex, ey), max(1, scale_x(2)))

        # Bright tip
        tip_radius = scale_x(4)
        tip_surf = pygame.Surface((tip_radius * 2, tip_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(tip_surf, (255, 255, 255, 200), (tip_radius, tip_radius), tip_radius)
        screen.blit(tip_surf, (ex - tip_radius, ey - tip_radius))

    def _render_missile(self, screen: pygame.Surface, proj: Projectile) -> None:
        """Render a missile projectile with exhaust trail."""
        px, py = int(proj.x), int(proj.y)

        # Exhaust trail: draw a few fading dots behind the missile
        trail_points = 5
        for i in range(trail_points):
            t = max(0.0, proj.progress - i * 0.04)
            if t <= 0:
                break
            tx = proj.start_x + (proj.end_x - proj.start_x) * t
            ty = proj.start_y + (proj.end_y - proj.start_y) * t
            if proj.arc_height != 0.0:
                arc = proj.arc_height * 4.0 * t * (1.0 - t)
                ty -= arc
            alpha = int(180 * (1.0 - i / trail_points))
            radius = max(1, scale_x(3) - i)
            trail_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*_MISSILE_TRAIL, alpha), (radius, radius), radius)
            screen.blit(trail_surf, (int(tx) - radius, int(ty) - radius))

        # Missile body
        body_radius = scale_x(5)
        pygame.draw.circle(screen, _MISSILE_BODY, (px, py), body_radius)
        # Bright nose
        pygame.draw.circle(screen, (255, 255, 255), (px, py), max(1, body_radius // 2))

    def _render_cannon(self, screen: pygame.Surface, proj: Projectile) -> None:
        """Render a small bright cannon round."""
        px, py = int(proj.x), int(proj.y)
        radius = max(1, scale_x(3))

        # Bright round
        pygame.draw.circle(screen, _CANNON_ROUND, (px, py), radius)
        # Core
        pygame.draw.circle(screen, (255, 255, 255), (px, py), max(1, radius - 1))
