"""Tests for the dual tech element-trail renderer (Combat C5 §4.3).

Covers head positioning per progress, parabolic arc correctness, trail
fade behavior, palette compliance on rendered head, zero/out-of-range
progress handling, and variant configs (zero trail length, flat arc).
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.dual_tech_element_trail import (
    TrailConfig,
    _trail_position,
    render_element_trail,
)
from spacegame.engine.material_palette import get_role


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _canvas(w: int = 200, h: int = 120) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


def _config(
    start: tuple[float, float] = (20.0, 60.0),
    end: tuple[float, float] = (180.0, 60.0),
    dominant_role: str = "plasma_core",
    trail_role: str = "plasma_hot",
    arc_height: float = 0.0,  # flat by default for test simplicity
    trail_length: int = 8,
    head_radius: int = 6,
    trail_radius: int = 4,
) -> TrailConfig:
    return TrailConfig(
        start=start,
        end=end,
        dominant_role=dominant_role,
        trail_role=trail_role,
        arc_height=arc_height,
        trail_length=trail_length,
        head_radius=head_radius,
        trail_radius=trail_radius,
    )


def _contains_color(surf: pygame.Surface, rgb: tuple[int, int, int]) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            px = surf.get_at((x, y))
            if px.a > 0 and (px.r, px.g, px.b) == rgb:
                return True
    return False


def _count_color(surf: pygame.Surface, rgb: tuple[int, int, int]) -> int:
    count = 0
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            px = surf.get_at((x, y))
            if px.a > 0 and (px.r, px.g, px.b) == rgb:
                count += 1
    return count


# ---------------------------------------------------------------------------
# Head position geometry
# ---------------------------------------------------------------------------


class TestTrailGeometry:
    def test_progress_zero_head_at_start(self) -> None:
        cfg = _config(start=(10.0, 50.0), end=(100.0, 50.0))
        pos = _trail_position(cfg, 0.0)
        assert pos == (10.0, 50.0)

    def test_progress_one_head_at_end(self) -> None:
        cfg = _config(start=(10.0, 50.0), end=(100.0, 50.0))
        pos = _trail_position(cfg, 1.0)
        assert pos == (100.0, 50.0)

    def test_progress_half_head_at_midpoint_flat(self) -> None:
        cfg = _config(start=(10.0, 50.0), end=(100.0, 50.0), arc_height=0.0)
        pos = _trail_position(cfg, 0.5)
        assert pos == (55.0, 50.0)

    def test_arc_height_raises_y_at_apex(self) -> None:
        """Parabolic arc peaks at t=0.5, offset by full arc_height."""
        cfg = _config(start=(0.0, 100.0), end=(100.0, 100.0), arc_height=40.0)
        apex = _trail_position(cfg, 0.5)
        # arc subtracts 40 * 4 * 0.5 * 0.5 = 40 from y
        assert apex == (50.0, 60.0)

    def test_arc_zero_at_endpoints(self) -> None:
        """Arc displacement is zero at t=0 and t=1."""
        cfg = _config(start=(0.0, 100.0), end=(100.0, 100.0), arc_height=40.0)
        assert _trail_position(cfg, 0.0) == (0.0, 100.0)
        assert _trail_position(cfg, 1.0) == (100.0, 100.0)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestRendering:
    def test_progress_zero_renders_only_head_at_start(self) -> None:
        """At progress=0 the head is at start; all trail segments have
        negative progress and are skipped."""
        canvas = _canvas()
        render_element_trail(canvas, _config(), progress=0.0)
        plasma_core = get_role("plasma_core")
        assert _contains_color(canvas, plasma_core)

    def test_head_uses_dominant_role(self) -> None:
        canvas = _canvas()
        render_element_trail(canvas, _config(dominant_role="cryo_fractal"), progress=0.5)
        cryo = get_role("cryo_fractal")
        assert _contains_color(canvas, cryo)

    def test_trail_uses_trail_role(self) -> None:
        """With a head/trail distinction, trail pixels must contain the
        trail role's color exactly (pure alpha, not blended)."""
        canvas = _canvas()
        render_element_trail(
            canvas,
            _config(dominant_role="plasma_core", trail_role="plasma_hot", trail_length=8),
            progress=0.9,  # Far along so trail segments are in-bounds
        )
        # At least one trail segment draws at max alpha (the one closest
        # to the head). Its center pixel should be trail_role exactly.
        plasma_hot = get_role("plasma_hot")
        # Can't assert exact presence because alpha fades — but if we
        # render at progress > 0.2, at least one trail segment exists.
        # Use the reverse check: there must be fewer head-color pixels
        # than trail-color pixels in aggregate (trail has 8 segments).
        # Simpler: just confirm at least one trail role pixel exists.
        assert _contains_color(canvas, plasma_hot), (
            f"Expected trail to render at least one {plasma_hot} pixel"
        )

    def test_progress_one_head_at_end(self) -> None:
        """Head at progress=1 lands at config.end. Verify there are opaque
        pixels near end but not near start."""
        canvas = _canvas()
        cfg = _config(start=(20.0, 60.0), end=(180.0, 60.0), trail_length=0)
        render_element_trail(canvas, cfg, progress=1.0)
        # Pixel near end: opaque.
        assert canvas.get_at((180, 60)).a > 0
        # Pixel near start: transparent (trail_length=0 means nothing behind head).
        assert canvas.get_at((20, 60)).a == 0

    def test_progress_clamped_to_unit_range(self) -> None:
        """Negative progress is clamped to 0; > 1 clamped to 1."""
        canvas_low = _canvas()
        render_element_trail(canvas_low, _config(trail_length=0), progress=-0.5)
        # Head should still render at start.
        plasma_core = get_role("plasma_core")
        assert _contains_color(canvas_low, plasma_core)

        canvas_high = _canvas()
        render_element_trail(canvas_high, _config(trail_length=0), progress=2.0)
        assert canvas_high.get_at((180, 60)).a > 0

    def test_zero_trail_length_renders_only_head(self) -> None:
        canvas = _canvas()
        render_element_trail(canvas, _config(trail_length=0), progress=0.5)
        plasma_core = get_role("plasma_core")
        plasma_hot = get_role("plasma_hot")
        assert _contains_color(canvas, plasma_core)
        assert not _contains_color(canvas, plasma_hot)

    def test_arc_path_bends_above_straight_line(self) -> None:
        """With arc_height > 0, mid-trajectory renders above (lower y)
        the straight line between endpoints."""
        flat_canvas = _canvas()
        arc_canvas = _canvas()
        render_element_trail(
            flat_canvas,
            _config(start=(20.0, 60.0), end=(180.0, 60.0), arc_height=0.0, trail_length=0),
            progress=0.5,
        )
        render_element_trail(
            arc_canvas,
            _config(start=(20.0, 60.0), end=(180.0, 60.0), arc_height=30.0, trail_length=0),
            progress=0.5,
        )
        plasma_core = get_role("plasma_core")
        # Flat: opaque near y=60 at x=100. Arc: opaque near y=30 at x=100 (arc subtracts 30).
        assert flat_canvas.get_at((100, 60)).a > 0
        # Arc canvas should have plasma_core pixels at higher y (lower value).
        found_arc_pixel = False
        for y in range(20, 45):
            for x in range(95, 105):
                px = arc_canvas.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) == plasma_core:
                    found_arc_pixel = True
                    break
            if found_arc_pixel:
                break
        assert found_arc_pixel, "Arc trajectory should place head above the straight line"


# ---------------------------------------------------------------------------
# Palette compliance
# ---------------------------------------------------------------------------


class TestPaletteCompliance:
    def test_head_pixels_are_exactly_dominant_role(self) -> None:
        """Head renders at full alpha (255) so pixels equal dominant
        role exactly on a transparent target."""
        canvas = _canvas()
        render_element_trail(
            canvas,
            _config(dominant_role="ion_arc", trail_role="glow_cool", trail_length=0),
            progress=0.5,
        )
        ion = get_role("ion_arc")
        count = _count_color(canvas, ion)
        assert count > 0, "Head must put at least one pixel at dominant role RGB"

    def test_all_rendered_head_pixels_share_role_rgb(self) -> None:
        """Every opaque pixel from a trail_length=0 render must equal
        the dominant role (no intermediate blends when painting over
        transparent)."""
        canvas = _canvas()
        render_element_trail(
            canvas,
            _config(dominant_role="voltaic_strike", trail_length=0),
            progress=0.5,
        )
        voltaic = get_role("voltaic_strike")
        off_role = []
        for y in range(canvas.get_height()):
            for x in range(canvas.get_width()):
                px = canvas.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) != voltaic:
                    off_role.append((x, y, (px.r, px.g, px.b)))
        assert not off_role, (
            f"Every head pixel must equal voltaic_strike; stray: {off_role[:3]}"
        )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_render_is_idempotent(self) -> None:
        canvas_a = _canvas()
        canvas_b = _canvas()
        cfg = _config(arc_height=30.0, trail_length=6)
        render_element_trail(canvas_a, cfg, progress=0.4)
        render_element_trail(canvas_b, cfg, progress=0.4)
        for y in range(canvas_a.get_height()):
            for x in range(canvas_a.get_width()):
                assert canvas_a.get_at((x, y)) == canvas_b.get_at((x, y))


# ---------------------------------------------------------------------------
# Canonical element pairings (spec §4.3)
# ---------------------------------------------------------------------------


class TestCanonicalPairings:
    def test_ion_cryo_pairing(self) -> None:
        """Spec example: ion dominant + cryo trail."""
        cfg = TrailConfig(
            start=(20.0, 60.0),
            end=(180.0, 60.0),
            dominant_role="ion_arc",
            trail_role="glow_cool",
        )
        canvas = _canvas()
        render_element_trail(canvas, cfg, progress=0.7)
        assert _contains_color(canvas, get_role("ion_arc"))
        assert _contains_color(canvas, get_role("glow_cool"))

    def test_plasma_voltaic_pairing(self) -> None:
        cfg = TrailConfig(
            start=(20.0, 60.0),
            end=(180.0, 60.0),
            dominant_role="plasma_core",
            trail_role="voltaic_strike",
        )
        canvas = _canvas()
        render_element_trail(canvas, cfg, progress=0.7)
        assert _contains_color(canvas, get_role("plasma_core"))
        assert _contains_color(canvas, get_role("voltaic_strike"))
