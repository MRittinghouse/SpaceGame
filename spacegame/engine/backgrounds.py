"""
Animated background system with parallax starfield layers.

Composites cached procedural background + live parallax stars.
"""

import pygame
import random
from typing import Optional
from spacegame.engine.procedural import generate_background


class ParallaxStarfield:
    """3-layer parallax scrolling starfield."""

    def __init__(self, width: int, height: int, seed: int = 0):
        self.width = width
        self.height = height
        self.layers: list[list[list]] = [[], [], []]  # 3 depth layers
        self._generate_stars(seed)
        self.scroll_x = 0.0
        self.scroll_y = 0.0

    def _generate_stars(self, seed: int) -> None:
        rng = random.Random(seed)

        # Layer 0: far (slow, dim, small)
        for _ in range(80):
            self.layers[0].append(
                [
                    rng.uniform(0, self.width),
                    rng.uniform(0, self.height),
                    rng.randint(40, 70),  # brightness
                    1,  # size
                ]
            )

        # Layer 1: mid
        for _ in range(40):
            self.layers[1].append(
                [
                    rng.uniform(0, self.width),
                    rng.uniform(0, self.height),
                    rng.randint(80, 150),
                    rng.choice([1, 1, 2]),
                ]
            )

        # Layer 2: near (fast, bright, larger)
        for _ in range(15):
            self.layers[2].append(
                [
                    rng.uniform(0, self.width),
                    rng.uniform(0, self.height),
                    rng.randint(160, 230),
                    rng.choice([1, 2, 2]),
                ]
            )

    def update(self, dt: float, speed_x: float = 8.0, speed_y: float = 2.0) -> None:
        """Scroll all layers at different speeds."""
        layer_speeds = [0.3, 0.7, 1.2]

        for layer_idx, stars in enumerate(self.layers):
            sx = speed_x * layer_speeds[layer_idx] * dt
            sy = speed_y * layer_speeds[layer_idx] * dt

            for star in stars:
                star[0] -= sx
                star[1] += sy

                # Wrap around
                if star[0] < 0:
                    star[0] += self.width
                elif star[0] >= self.width:
                    star[0] -= self.width
                if star[1] < 0:
                    star[1] += self.height
                elif star[1] >= self.height:
                    star[1] -= self.height

    def render(self, screen: pygame.Surface) -> None:
        """Render all star layers."""
        for stars in self.layers:
            for star in stars:
                x, y, brightness, size = int(star[0]), int(star[1]), star[2], star[3]
                color = (brightness, brightness, min(255, brightness + 10))
                if size <= 1:
                    screen.set_at((x, y), color)
                else:
                    pygame.draw.circle(screen, color, (x, y), size)


class AnimatedBackground:
    """Composite animated background: static procedural base + live parallax."""

    def __init__(
        self, theme: str = "deep_space", width: int = 1280, height: int = 720, seed: int = 42
    ):
        self.theme = theme
        self.width = width
        self.height = height

        # Cached static background
        self.static_bg = generate_background(width, height, theme, seed)

        # Live parallax stars on top
        self.parallax = ParallaxStarfield(width, height, seed + 5000)

        # Optional nebula drift offset
        self.nebula_offset_x = 0.0
        self.nebula_offset_y = 0.0

    def update(self, dt: float) -> None:
        """Update animated elements."""
        self.parallax.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render the full animated background."""
        screen.blit(self.static_bg, (0, 0))
        self.parallax.render(screen)
