"""Tests for ParallaxStarfield + AnimatedBackground camera-offset hook.

Verifies that passing a non-zero camera_offset to render shifts star
positions per-layer, with far layers shifting less than near layers
(Combat overhaul §4.6).
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.backgrounds import AnimatedBackground, ParallaxStarfield


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _surface(w: int = 200, h: int = 200) -> pygame.Surface:
    return pygame.Surface((w, h))


class TestParallaxOffset:
    def test_render_without_offset_matches_legacy_behavior(self) -> None:
        """Zero camera_offset (default) produces the pre-hook render."""
        field = ParallaxStarfield(200, 200, seed=42)
        a = _surface()
        a.fill((0, 0, 0))
        b = _surface()
        b.fill((0, 0, 0))
        field.render(a)
        field.render(b, camera_offset=(0.0, 0.0))
        for y in range(200):
            for x in range(200):
                assert a.get_at((x, y)) == b.get_at((x, y))

    def test_nonzero_offset_shifts_render(self) -> None:
        """A non-zero camera_offset produces a visibly different render."""
        field = ParallaxStarfield(200, 200, seed=42)
        a = _surface()
        a.fill((0, 0, 0))
        b = _surface()
        b.fill((0, 0, 0))
        field.render(a, camera_offset=(0.0, 0.0))
        field.render(b, camera_offset=(50.0, 0.0))
        differ = any(
            a.get_at((x, y)) != b.get_at((x, y))
            for y in range(200)
            for x in range(200)
        )
        assert differ

    def test_layer_parallax_factors_canonical(self) -> None:
        """Far < mid < near per spec §4.6."""
        assert ParallaxStarfield.LAYER_PARALLAX == (0.3, 0.7, 1.2)
        assert ParallaxStarfield.LAYER_PARALLAX[0] < ParallaxStarfield.LAYER_PARALLAX[1]
        assert ParallaxStarfield.LAYER_PARALLAX[1] < ParallaxStarfield.LAYER_PARALLAX[2]

    def test_offset_wraps_modulo_field_dimensions(self) -> None:
        """Offset beyond field width wraps — stars stay on-screen."""
        field = ParallaxStarfield(200, 200, seed=42)
        surf = _surface()
        surf.fill((0, 0, 0))
        # Huge offset — should still render without crash + at least one star visible.
        field.render(surf, camera_offset=(10_000.0, 0.0))
        any_lit = any(
            surf.get_at((x, y)) != (0, 0, 0, 255)
            for y in range(200)
            for x in range(200)
        )
        assert any_lit


class TestAnimatedBackgroundOffset:
    def test_render_accepts_camera_offset(self) -> None:
        """AnimatedBackground.render accepts + respects camera_offset."""
        bg = AnimatedBackground(theme="deep_space", width=200, height=200, seed=42)
        a = _surface()
        b = _surface()
        bg.render(a, camera_offset=(0.0, 0.0))
        bg.render(b, camera_offset=(50.0, 20.0))
        # Parallax stars differ; static base is the same.
        differ = any(
            a.get_at((x, y)) != b.get_at((x, y))
            for y in range(200)
            for x in range(200)
        )
        assert differ

    def test_default_offset_is_backward_compatible(self) -> None:
        """No offset arg = legacy behavior."""
        bg = AnimatedBackground(theme="deep_space", width=200, height=200, seed=42)
        surf = _surface()
        # Must not raise.
        bg.render(surf)
