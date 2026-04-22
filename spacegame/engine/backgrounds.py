"""
Animated background system with parallax starfield layers.

Composites cached procedural background + live parallax stars.
"""

import random

import pygame

from spacegame.engine.procedural import generate_background


class ParallaxStarfield:
    """3-layer parallax scrolling starfield.

    Each layer drifts at its own speed (far = slow, near = fast). When a
    camera offset is supplied to :meth:`render`, layers additionally
    translate by ``offset * layer_parallax_factor`` — far layers shift
    the least, matching how distant objects parallax less than near ones.
    Combat view wires this to :class:`SceneCamera` so cinematic pushes
    + shakes propagate through the starfield (Combat overhaul §4.6).
    """

    # Parallax factors per layer — far < mid < near. Shared between
    # scroll update (drift speed) and render-time camera offset so the
    # two mechanisms feel coherent.
    LAYER_PARALLAX = (0.3, 0.7, 1.2)

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
        for layer_idx, stars in enumerate(self.layers):
            sx = speed_x * self.LAYER_PARALLAX[layer_idx] * dt
            sy = speed_y * self.LAYER_PARALLAX[layer_idx] * dt

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

    def render(
        self,
        screen: pygame.Surface,
        camera_offset: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        """Render all star layers with optional camera-driven parallax.

        ``camera_offset`` is the offset from the :class:`SceneCamera`;
        each layer shifts by ``offset * LAYER_PARALLAX[layer]`` so far
        layers move less than near ones (Combat overhaul §4.6). Zero
        offset matches the legacy behavior.
        """
        cam_x, cam_y = camera_offset
        sw = screen.get_width()
        sh = screen.get_height()
        for layer_idx, stars in enumerate(self.layers):
            factor = self.LAYER_PARALLAX[layer_idx]
            dx = cam_x * factor
            dy = cam_y * factor
            for star in stars:
                x = int(star[0] + dx) % self.width
                y = int(star[1] + dy) % self.height
                brightness = star[2]
                size = star[3]
                color = (brightness, brightness, min(255, brightness + 10))
                # After modulo wrap, make sure we're still on-screen.
                if x < 0 or y < 0 or x >= sw or y >= sh:
                    continue
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

    def render(
        self,
        screen: pygame.Surface,
        camera_offset: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        """Render the full animated background.

        ``camera_offset`` passes through to the parallax layer so the
        starfield responds to a :class:`SceneCamera` during cinematic
        camera pushes + shakes (Combat overhaul §4.6). The static base
        image doesn't parallax — it's treated as the backdrop at
        infinite depth.
        """
        screen.blit(self.static_bg, (0, 0))
        self.parallax.render(screen, camera_offset=camera_offset)
