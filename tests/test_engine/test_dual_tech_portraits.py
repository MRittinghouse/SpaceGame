"""Tests for the dual tech portrait renderer (Combat C5 §4.3 + §4.9).

Covers slide positioning, alpha handling, border-stripe role compliance,
rendering determinism, and graceful no-op behavior at zero-alpha.
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.dual_tech_portraits import (
    DEFAULT_MARGIN_X,
    PortraitConfig,
    render_portraits,
)
from spacegame.engine.material_palette import get_role


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _portrait(
    w: int = 32,
    h: int = 32,
    fill: tuple[int, int, int] = (180, 180, 200),
    faction: str | None = None,
) -> PortraitConfig:
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((*fill, 255))
    return PortraitConfig(surface=surface, faction_role=faction)


def _canvas(w: int = 300, h: int = 200) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


def _any_opaque(surf: pygame.Surface) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            if surf.get_at((x, y)).a > 0:
                return True
    return False


# ---------------------------------------------------------------------------
# No-op / alpha
# ---------------------------------------------------------------------------


class TestAlphaHandling:
    def test_zero_alpha_renders_nothing(self) -> None:
        canvas = _canvas()
        render_portraits(canvas, _portrait(), _portrait(), slide_factor=1.0, alpha=0)
        assert not _any_opaque(canvas)

    def test_negative_alpha_renders_nothing(self) -> None:
        canvas = _canvas()
        render_portraits(canvas, _portrait(), _portrait(), slide_factor=1.0, alpha=-100)
        assert not _any_opaque(canvas)

    def test_full_alpha_renders_content(self) -> None:
        canvas = _canvas()
        render_portraits(canvas, _portrait(), _portrait(), slide_factor=1.0, alpha=255)
        assert _any_opaque(canvas)


# ---------------------------------------------------------------------------
# Slide positioning
# ---------------------------------------------------------------------------


class TestSlidePositioning:
    def test_slide_factor_zero_places_portraits_offscreen(self) -> None:
        """At slide=0, left portrait is at -W (fully off left edge);
        right portrait is at screen_w (fully off right edge). No opaque
        pixels should land on the visible canvas."""
        canvas = _canvas(300, 200)
        render_portraits(
            canvas,
            _portrait(w=32, h=32),
            _portrait(w=32, h=32),
            slide_factor=0.0,
            alpha=255,
        )
        # Nothing opaque within the visible canvas bounds.
        assert not _any_opaque(canvas)

    def test_slide_factor_one_places_portraits_at_rest(self) -> None:
        """At slide=1, left portrait sits at x=margin_x; right at
        x=screen_w - margin_x - W. Opaque pixels should appear in both
        corner regions."""
        canvas = _canvas(300, 200)
        render_portraits(
            canvas,
            _portrait(w=32, h=32),
            _portrait(w=32, h=32),
            slide_factor=1.0,
            alpha=255,
            bottom_y=190,
        )
        # Left corner: margin_x=20, so portrait spans x=20..52, y=190-32..190
        # Pixel at (30, 180) should be opaque (inside left portrait).
        assert canvas.get_at((30, 180)).a > 0
        # Right corner: portrait spans x=300-20-32=248..280
        assert canvas.get_at((260, 180)).a > 0

    def test_slide_factor_mid_produces_intermediate_position(self) -> None:
        """At slide=0.5, portraits are halfway between offscreen and rest."""
        canvas = _canvas(300, 200)
        render_portraits(
            canvas,
            _portrait(w=32, h=32),
            _portrait(w=32, h=32),
            slide_factor=0.5,
            alpha=255,
            bottom_y=190,
        )
        # Left portrait at x = round(-32 + (20+32)*0.5) = -6 → spans -6..26
        # Pixel at (10, 180) should be opaque.
        assert canvas.get_at((10, 180)).a > 0

    def test_slide_factor_clamped_to_unit_range(self) -> None:
        canvas = _canvas(300, 200)
        # slide_factor=2.0 is clamped to 1.0 — same as rest position.
        render_portraits(
            canvas,
            _portrait(w=32, h=32),
            _portrait(w=32, h=32),
            slide_factor=2.0,
            alpha=255,
            bottom_y=190,
        )
        assert canvas.get_at((30, 180)).a > 0

    def test_bottom_y_override_positions_portrait(self) -> None:
        canvas = _canvas(300, 200)
        render_portraits(
            canvas,
            _portrait(w=32, h=32),
            _portrait(w=32, h=32),
            slide_factor=1.0,
            alpha=255,
            bottom_y=100,
        )
        # Portraits span y = 100-32=68 .. 100. Pixel at (30, 90) should be opaque,
        # pixel at (30, 150) should not.
        assert canvas.get_at((30, 90)).a > 0
        assert canvas.get_at((30, 150)).a == 0


# ---------------------------------------------------------------------------
# Border stripe
# ---------------------------------------------------------------------------


class TestFactionBorder:
    def test_no_faction_role_draws_no_border(self) -> None:
        """A portrait without faction_role doesn't paint a border."""
        canvas = _canvas(200, 100)
        portrait_color = (150, 150, 200)
        p = _portrait(w=32, h=32, fill=portrait_color, faction=None)
        render_portraits(canvas, p, p, slide_factor=1.0, alpha=255, bottom_y=90)
        # Every opaque pixel should match portrait_color (no border color).
        for y in range(100):
            for x in range(200):
                px = canvas.get_at((x, y))
                if px.a == 0:
                    continue
                assert (px.r, px.g, px.b) == portrait_color

    def test_faction_role_paints_border_in_role_color(self) -> None:
        """A portrait with faction_role paints a 2px border stripe at
        the palette role's exact RGB."""
        canvas = _canvas(200, 100)
        faction = "hud_cyan"
        p = _portrait(w=32, h=32, faction=faction)
        render_portraits(canvas, p, p, slide_factor=1.0, alpha=255, bottom_y=90)
        cyan = get_role(faction)
        # Scan for at least one pixel exactly at the cyan RGB.
        found = False
        for y in range(100):
            for x in range(200):
                px = canvas.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) == cyan:
                    found = True
                    break
            if found:
                break
        assert found, f"Expected at least one border pixel at {cyan}"

    def test_different_faction_roles_render_differently(self) -> None:
        canvas_a = _canvas(200, 100)
        canvas_b = _canvas(200, 100)
        p_a = _portrait(faction="hud_cyan")
        p_b = _portrait(faction="hud_warning")
        render_portraits(canvas_a, p_a, p_a, slide_factor=1.0, alpha=255, bottom_y=90)
        render_portraits(canvas_b, p_b, p_b, slide_factor=1.0, alpha=255, bottom_y=90)
        # At least one pixel should differ between the two canvases.
        differ = any(
            canvas_a.get_at((x, y)) != canvas_b.get_at((x, y))
            for y in range(100)
            for x in range(200)
        )
        assert differ


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_render_is_idempotent(self) -> None:
        """Same inputs → same output. Portrait rendering is a pure function."""
        canvas_a = _canvas()
        canvas_b = _canvas()
        left = _portrait(faction="hud_cyan")
        right = _portrait(faction="hud_warning")
        render_portraits(canvas_a, left, right, slide_factor=0.6, alpha=200, bottom_y=180)
        render_portraits(canvas_b, left, right, slide_factor=0.6, alpha=200, bottom_y=180)
        for y in range(canvas_a.get_height()):
            for x in range(canvas_a.get_width()):
                assert canvas_a.get_at((x, y)) == canvas_b.get_at((x, y))


# ---------------------------------------------------------------------------
# Palette compliance
# ---------------------------------------------------------------------------


class TestPaletteCompliance:
    def test_border_stripe_is_role_compliant(self) -> None:
        """With a faction border and a neutral portrait fill, every
        border pixel is exactly the faction role RGB. The portrait's
        interior is caller-supplied and not role-constrained — caller
        is responsible for sprite palette discipline."""
        from spacegame.engine.material_palette import is_valid_role

        assert is_valid_role("hud_cyan")
        canvas = _canvas()
        p = _portrait(fill=(100, 100, 100), faction="hud_cyan")
        render_portraits(canvas, p, p, slide_factor=1.0, alpha=255, bottom_y=190)
        cyan = get_role("hud_cyan")
        # Find border pixels — they're distinct from the fill color.
        border_pixels = []
        for y in range(canvas.get_height()):
            for x in range(canvas.get_width()):
                px = canvas.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) != (100, 100, 100):
                    border_pixels.append((px.r, px.g, px.b))
        assert border_pixels, "Expected some border pixels"
        for rgb in border_pixels:
            assert rgb == cyan, f"Border pixel {rgb} must be the role RGB {cyan}"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_margin_matches_spec_constant(self) -> None:
        """DEFAULT_MARGIN_X is exposed so combat_view can position relative UI."""
        assert DEFAULT_MARGIN_X > 0
        assert DEFAULT_MARGIN_X < 100  # Sanity: not some absurd value
