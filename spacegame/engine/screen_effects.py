"""
Screen-wide visual effects: vignette overlay and screen shake.
"""

import pygame
import random
import math


class Vignette:
    """Pre-rendered dark-edge overlay for cinematic feel."""

    def __init__(self, width: int, height: int, intensity: float = 0.6):
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._generate(width, height, intensity)

    def _generate(self, w: int, h: int, intensity: float) -> None:
        """Generate vignette overlay with radial darkening."""
        cx, cy = w / 2, h / 2
        max_dist = math.sqrt(cx * cx + cy * cy)

        # Draw concentric rectangles from outside in with decreasing alpha
        steps = 30
        for i in range(steps):
            t = i / steps  # 0 = outermost, 1 = innermost
            # Alpha decreases toward center
            alpha = int(intensity * 255 * (1.0 - t) * (1.0 - t))
            if alpha <= 0:
                continue

            margin_x = int(w * t * 0.4)
            margin_y = int(h * t * 0.4)

            rect = pygame.Rect(margin_x, margin_y, w - margin_x * 2, h - margin_y * 2)
            if rect.width <= 0 or rect.height <= 0:
                continue

            # Only draw the border region of each step
            pygame.draw.rect(self.surface, (0, 0, 0, alpha), rect, max(1, w // (steps * 2)))

    def render(self, screen: pygame.Surface) -> None:
        """Blit vignette overlay onto screen."""
        screen.blit(self.surface, (0, 0))


class ScreenShake:
    """Brief random position offset triggered by events."""

    def __init__(self):
        self.intensity: float = 0.0
        self.duration: float = 0.0
        self.elapsed: float = 0.0
        self.active: bool = False
        self._offset_x: int = 0
        self._offset_y: int = 0

    def trigger(self, intensity: float = 3.0, duration: float = 0.2) -> None:
        """Start a screen shake.

        Args:
            intensity: Maximum pixel offset
            duration: How long the shake lasts (seconds)
        """
        self.intensity = intensity
        self.duration = duration
        self.elapsed = 0.0
        self.active = True

    def update(self, dt: float) -> None:
        """Update shake offset."""
        if not self.active:
            self._offset_x = 0
            self._offset_y = 0
            return

        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False
            self._offset_x = 0
            self._offset_y = 0
            return

        # Decay intensity over time
        remaining = 1.0 - (self.elapsed / self.duration)
        current_intensity = self.intensity * remaining

        self._offset_x = int(random.uniform(-current_intensity, current_intensity))
        self._offset_y = int(random.uniform(-current_intensity, current_intensity))

    @property
    def offset(self) -> tuple[int, int]:
        """Current shake offset (x, y) to apply to render position."""
        return (self._offset_x, self._offset_y)
