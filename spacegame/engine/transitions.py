"""
Screen transition effects between game states.

Supports fade, warp distortion, slide, and pixelate transitions.
"""

import math
import random
from enum import Enum
from typing import Callable, Optional

import pygame


class TransitionType(Enum):
    FADE = "fade"
    WARP = "warp"
    SLIDE = "slide"
    PIXELATE = "pixelate"


class TransitionManager:
    """Manages screen transitions between game states."""

    def __init__(self):
        self.active = False
        self.transition_type: Optional[TransitionType] = None
        self.duration: float = 0.4
        self.elapsed: float = 0.0
        self.callback: Optional[Callable] = None
        self.callback_fired: bool = False

        # Screen captures
        self.old_screen: Optional[pygame.Surface] = None
        self.new_screen: Optional[pygame.Surface] = None

        # Slide direction (1 = left, -1 = right)
        self.slide_direction: int = 1

        # Warp scanline offsets (pre-generated)
        self._warp_offsets: list = []

    def start(
        self,
        transition_type: TransitionType,
        duration: float,
        callback: Optional[Callable] = None,
        old_surface: Optional[pygame.Surface] = None,
    ) -> None:
        """Start a transition.

        Args:
            transition_type: Type of transition effect
            duration: Total duration in seconds
            callback: Called at midpoint to swap state
            old_surface: Screenshot of current screen before transition
        """
        self.active = True
        self.transition_type = transition_type
        self.duration = duration
        self.elapsed = 0.0
        self.callback = callback
        self.callback_fired = False

        if old_surface:
            self.old_screen = old_surface.copy()
        else:
            self.old_screen = None

        # Pre-generate warp offsets
        if transition_type == TransitionType.WARP:
            h = old_surface.get_height() if old_surface else 720
            rng = random.Random(42)
            self._warp_offsets = [rng.randint(-30, 30) for _ in range(h)]

    def update(self, dt: float) -> None:
        """Update transition timer."""
        if not self.active:
            return

        self.elapsed += dt

        # Fire callback at midpoint
        midpoint = self.duration / 2
        if not self.callback_fired and self.elapsed >= midpoint:
            self.callback_fired = True
            if self.callback:
                self.callback()

        # End transition
        if self.elapsed >= self.duration:
            self.active = False
            self.old_screen = None
            self.new_screen = None

    def render(self, screen: pygame.Surface) -> None:
        """Render transition overlay on top of current screen content."""
        if not self.active:
            return

        progress = min(1.0, self.elapsed / self.duration)
        w, h = screen.get_size()

        if self.transition_type == TransitionType.FADE:
            self._render_fade(screen, progress, w, h)
        elif self.transition_type == TransitionType.WARP:
            self._render_warp(screen, progress, w, h)
        elif self.transition_type == TransitionType.SLIDE:
            self._render_slide(screen, progress, w, h)
        elif self.transition_type == TransitionType.PIXELATE:
            self._render_pixelate(screen, progress, w, h)

    def _render_fade(self, screen: pygame.Surface, progress: float, w: int, h: int) -> None:
        """Fade through black."""
        if progress < 0.5:
            # Fade to black (0 -> 1 in first half)
            alpha = int(255 * (progress * 2))
        else:
            # Fade from black (1 -> 0 in second half)
            alpha = int(255 * (1.0 - (progress - 0.5) * 2))

        alpha = max(0, min(255, alpha))
        overlay = pygame.Surface((w, h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(alpha)
        screen.blit(overlay, (0, 0))

    def _render_warp(self, screen: pygame.Surface, progress: float, w: int, h: int) -> None:
        """Horizontal scanline distortion effect."""
        if progress < 0.5:
            intensity = progress * 2  # 0 -> 1
        else:
            intensity = (1.0 - progress) * 2  # 1 -> 0

        if intensity < 0.01:
            return

        # Create distorted copy
        source = screen.copy()
        screen.fill((0, 0, 0))

        max_offset = int(40 * intensity)
        scanline_height = 2

        for y in range(0, h, scanline_height):
            idx = y % len(self._warp_offsets) if self._warp_offsets else 0
            base_offset = self._warp_offsets[idx] if self._warp_offsets else 0
            offset = int(base_offset * intensity)

            # Time-varying component
            wave = math.sin(y * 0.05 + self.elapsed * 15) * max_offset * 0.3
            offset += int(wave)

            strip = source.subsurface(pygame.Rect(0, y, w, min(scanline_height, h - y)))
            screen.blit(strip, (offset, y))

        # Color fringing
        if intensity > 0.3:
            fringe_alpha = int(30 * intensity)
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 100, 255, fringe_alpha))
            screen.blit(overlay, (0, 0))

    def _render_slide(self, screen: pygame.Surface, progress: float, w: int, h: int) -> None:
        """Slide old screen out, new content slides in."""
        if progress < 0.5 and self.old_screen:
            # Old screen sliding out
            offset = int(w * (progress * 2) * self.slide_direction)
            screen.fill((0, 0, 0))
            screen.blit(self.old_screen, (-offset, 0))
        elif progress >= 0.5:
            # New content sliding in (already rendered underneath)
            slide_progress = (progress - 0.5) * 2  # 0 to 1
            offset = int(w * (1.0 - slide_progress) * self.slide_direction)
            if offset != 0:
                temp = screen.copy()
                screen.fill((0, 0, 0))
                screen.blit(temp, (-offset, 0))

    def _render_pixelate(self, screen: pygame.Surface, progress: float, w: int, h: int) -> None:
        """Pixelation effect — screen resolves to blocky pixels then back.

        Uses nearest-neighbor downscale then upscale to create a retro
        pixel mosaic effect that peaks at midpoint.
        """
        if progress < 0.5:
            intensity = progress * 2  # 0 -> 1
        else:
            intensity = (1.0 - progress) * 2  # 1 -> 0

        if intensity < 0.02:
            return

        # Scale factor: 1 (no effect) to 16 (very blocky)
        # Use exponential curve for pleasing ramp
        max_block = 16
        block_size = max(1, int(1 + (max_block - 1) * (intensity**1.5)))

        if block_size <= 1:
            return

        small_w = max(1, w // block_size)
        small_h = max(1, h // block_size)

        # Downscale (smooth) then upscale (nearest-neighbor = blocky)
        small = pygame.transform.smoothscale(screen, (small_w, small_h))
        pixelated = pygame.transform.scale(small, (w, h))
        screen.blit(pixelated, (0, 0))
