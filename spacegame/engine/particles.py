"""
Pool-based particle system for visual effects.

Supports color lerping, alpha fade, gravity, and additive glow rendering.
Max 500 particles with dead-particle recycling (no GC churn).
"""

import pygame
import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Particle:
    """Single particle state."""

    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0
    max_life: float = 1.0
    color_start: tuple = (255, 255, 255)
    color_end: tuple = (255, 255, 255)
    alpha_start: int = 255
    alpha_end: int = 0
    size_start: float = 2.0
    size_end: float = 0.5
    gravity: float = 0.0
    alive: bool = False
    glow: bool = False


@dataclass
class ParticleConfig:
    """Configuration preset for particle emission."""

    count: int = 10
    speed_min: float = 20.0
    speed_max: float = 80.0
    life_min: float = 0.3
    life_max: float = 1.0
    color_start: tuple = (255, 255, 255)
    color_end: tuple = (100, 100, 100)
    alpha_start: int = 255
    alpha_end: int = 0
    size_start: float = 2.0
    size_end: float = 0.5
    gravity: float = 0.0
    spread: float = 360.0  # degrees of spread (360 = full circle)
    direction: float = 0.0  # base direction in degrees (0 = right)
    glow: bool = False


# Preset configurations
SPARK_BURST = ParticleConfig(
    count=15,
    speed_min=60,
    speed_max=150,
    life_min=0.2,
    life_max=0.6,
    color_start=(255, 200, 80),
    color_end=(255, 100, 20),
    alpha_start=255,
    alpha_end=0,
    size_start=2.0,
    size_end=0.5,
    gravity=40.0,
    spread=360.0,
    glow=True,
)

MINING_DUST = ParticleConfig(
    count=25,
    speed_min=40,
    speed_max=120,
    life_min=0.4,
    life_max=1.0,
    color_start=(180, 160, 120),
    color_end=(100, 80, 60),
    alpha_start=220,
    alpha_end=0,
    size_start=3.0,
    size_end=1.0,
    gravity=30.0,
    spread=360.0,
    glow=False,
)

SCAN_PULSE = ParticleConfig(
    count=20,
    speed_min=80,
    speed_max=120,
    life_min=0.3,
    life_max=0.7,
    color_start=(100, 200, 255),
    color_end=(40, 100, 200),
    alpha_start=200,
    alpha_end=0,
    size_start=2.0,
    size_end=1.0,
    gravity=0.0,
    spread=360.0,
    glow=True,
)

WARP_TRAIL = ParticleConfig(
    count=8,
    speed_min=10,
    speed_max=40,
    life_min=0.5,
    life_max=1.5,
    color_start=(150, 200, 255),
    color_end=(40, 60, 150),
    alpha_start=180,
    alpha_end=0,
    size_start=2.0,
    size_end=0.5,
    gravity=0.0,
    spread=30.0,
    direction=180.0,
    glow=True,
)

COLLECT_SPARKLE = ParticleConfig(
    count=12,
    speed_min=30,
    speed_max=80,
    life_min=0.3,
    life_max=0.8,
    color_start=(100, 255, 150),
    color_end=(50, 200, 100),
    alpha_start=255,
    alpha_end=0,
    size_start=2.5,
    size_end=0.5,
    gravity=-20.0,
    spread=360.0,
    glow=True,
)

CLICK_HIT = ParticleConfig(
    count=5,
    speed_min=40,
    speed_max=100,
    life_min=0.15,
    life_max=0.4,
    color_start=(255, 180, 60),
    color_end=(255, 100, 20),
    alpha_start=255,
    alpha_end=0,
    size_start=2.0,
    size_end=0.5,
    gravity=30.0,
    spread=120.0,
    direction=270.0,
    glow=True,
)

DRONE_SPARK = ParticleConfig(
    count=3,
    speed_min=10,
    speed_max=30,
    life_min=0.2,
    life_max=0.5,
    color_start=(80, 160, 255),
    color_end=(40, 80, 200),
    alpha_start=200,
    alpha_end=0,
    size_start=1.5,
    size_end=0.5,
    gravity=0.0,
    spread=360.0,
    glow=True,
)

STAR_TWINKLE = ParticleConfig(
    count=1,
    speed_min=0,
    speed_max=2,
    life_min=1.0,
    life_max=3.0,
    color_start=(200, 220, 255),
    color_end=(100, 120, 180),
    alpha_start=200,
    alpha_end=0,
    size_start=1.5,
    size_end=0.5,
    gravity=0.0,
    spread=360.0,
    glow=True,
)


# Combat presets
LASER_HIT = ParticleConfig(
    count=15,
    speed_min=60,
    speed_max=150,
    life_min=0.15,
    life_max=0.4,
    color_start=(255, 150, 50),
    color_end=(255, 50, 0),
    gravity=60.0,
    spread=360.0,
    glow=True,
)

MISSILE_EXPLOSION = ParticleConfig(
    count=30,
    speed_min=80,
    speed_max=200,
    life_min=0.2,
    life_max=0.6,
    color_start=(255, 200, 80),
    color_end=(200, 50, 0),
    size_start=3.0,
    size_end=1.0,
    gravity=40.0,
    spread=360.0,
    glow=True,
)

SHIELD_IMPACT = ParticleConfig(
    count=12,
    speed_min=40,
    speed_max=100,
    life_min=0.2,
    life_max=0.5,
    color_start=(100, 200, 255),
    color_end=(40, 100, 200),
    gravity=0.0,
    spread=360.0,
    glow=True,
)

HEAL_SPARKLE = ParticleConfig(
    count=10,
    speed_min=20,
    speed_max=60,
    life_min=0.3,
    life_max=0.8,
    color_start=(100, 255, 150),
    color_end=(50, 200, 100),
    gravity=-30.0,
    spread=360.0,
    glow=True,
)

SHIELD_RESTORE = ParticleConfig(
    count=8,
    speed_min=30,
    speed_max=70,
    life_min=0.3,
    life_max=0.6,
    color_start=(80, 180, 255),
    color_end=(40, 80, 200),
    gravity=-20.0,
    spread=360.0,
    glow=True,
)


MINING_CHAIN = ParticleConfig(
    count=20,
    speed_min=80,
    speed_max=200,
    life_min=0.3,
    life_max=0.7,
    color_start=(255, 180, 40),
    color_end=(200, 80, 20),
    gravity=0.0,
    spread=360.0,
    glow=True,
)

ENERGY_REGEN = ParticleConfig(
    count=6,
    speed_min=20,
    speed_max=50,
    life_min=0.4,
    life_max=0.8,
    color_start=(100, 220, 255),
    color_end=(40, 100, 200),
    gravity=-60.0,
    spread=60.0,
    direction=90.0,
    glow=True,
)

SALVAGE_SCAN = ParticleConfig(
    count=12,
    speed_min=40,
    speed_max=100,
    life_min=0.3,
    life_max=0.6,
    color_start=(80, 150, 255),
    color_end=(30, 60, 180),
    gravity=0.0,
    spread=360.0,
    glow=True,
)

SALVAGE_CORRUPT = ParticleConfig(
    count=8,
    speed_min=10,
    speed_max=40,
    life_min=0.5,
    life_max=1.0,
    color_start=(220, 40, 40),
    color_end=(100, 20, 20),
    gravity=50.0,
    spread=120.0,
    direction=270.0,
)

REFINE_COMPLETE = ParticleConfig(
    count=15,
    speed_min=50,
    speed_max=120,
    life_min=0.3,
    life_max=0.6,
    color_start=(50, 220, 100),
    color_end=(20, 100, 40),
    gravity=-30.0,
    spread=360.0,
    glow=True,
)


class ParticlePool:
    """Fixed-size particle pool with recycling."""

    MAX_PARTICLES = 500

    def __init__(self, max_particles: int = MAX_PARTICLES):
        self.particles = [Particle() for _ in range(max_particles)]
        self._glow_surface: Optional[pygame.Surface] = None

    def emit(self, x: float, y: float, config: ParticleConfig) -> None:
        """Emit particles at position using config preset."""
        spawned = 0
        for p in self.particles:
            if spawned >= config.count:
                break
            if p.alive:
                continue

            # Calculate random direction within spread
            angle_deg = config.direction + random.uniform(-config.spread / 2, config.spread / 2)
            angle_rad = math.radians(angle_deg)
            speed = random.uniform(config.speed_min, config.speed_max)

            p.x = x
            p.y = y
            p.vx = math.cos(angle_rad) * speed
            p.vy = math.sin(angle_rad) * speed
            p.life = 0.0
            p.max_life = random.uniform(config.life_min, config.life_max)
            p.color_start = config.color_start
            p.color_end = config.color_end
            p.alpha_start = config.alpha_start
            p.alpha_end = config.alpha_end
            p.size_start = config.size_start
            p.size_end = config.size_end
            p.gravity = config.gravity
            p.alive = True
            p.glow = config.glow
            spawned += 1

    def update(self, dt: float) -> None:
        """Update all alive particles."""
        for p in self.particles:
            if not p.alive:
                continue
            p.life += dt
            if p.life >= p.max_life:
                p.alive = False
                continue
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt

    def render(self, screen: pygame.Surface) -> None:
        """Render all alive particles."""
        for p in self.particles:
            if not p.alive:
                continue

            t = p.life / p.max_life if p.max_life > 0 else 1.0

            # Lerp color
            r = int(p.color_start[0] + (p.color_end[0] - p.color_start[0]) * t)
            g = int(p.color_start[1] + (p.color_end[1] - p.color_start[1]) * t)
            b = int(p.color_start[2] + (p.color_end[2] - p.color_start[2]) * t)
            color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

            # Lerp alpha
            alpha = int(p.alpha_start + (p.alpha_end - p.alpha_start) * t)
            alpha = max(0, min(255, alpha))

            # Lerp size
            size = p.size_start + (p.size_end - p.size_start) * t
            size = max(0.5, size)

            ix, iy = int(p.x), int(p.y)
            isize = max(1, int(size))

            if alpha >= 250 and not p.glow:
                # Fast path: fully opaque, no glow
                pygame.draw.circle(screen, color, (ix, iy), isize)
            else:
                # Alpha blended particle
                d = (isize + 2) * 2
                surf = pygame.Surface((d, d), pygame.SRCALPHA)
                center = d // 2

                if p.glow:
                    # Glow: larger dim circle behind
                    glow_alpha = max(0, alpha // 3)
                    glow_color = (color[0], color[1], color[2], glow_alpha)
                    pygame.draw.circle(surf, glow_color, (center, center), isize + 1)

                particle_color = (color[0], color[1], color[2], alpha)
                pygame.draw.circle(surf, particle_color, (center, center), isize)
                screen.blit(surf, (ix - center, iy - center))

    def clear(self) -> None:
        """Kill all particles."""
        for p in self.particles:
            p.alive = False

    @property
    def alive_count(self) -> int:
        return sum(1 for p in self.particles if p.alive)
