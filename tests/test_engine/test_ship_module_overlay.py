"""Tests for ship_module_overlay (Combat C4 §4.2).

Covers:
  - Region registration + accessors
  - Persistent state transitions (with destroyed as terminal)
  - Flash trigger + expiry + destroyed blocks flash
  - Hit detection in ship-local pixel coordinates
  - Per-state rendering produces the right palette role(s)
  - Rendered surface is palette-role compliant
  - Flash decays monotonically toward zero
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.material_palette import (
    assert_role_compliance,
    get_band,
    get_role,
)
from spacegame.engine.ship_module_overlay import (
    FLASH_DURATION,
    ModuleOverlayState,
    ModuleRegion,
    ShipModuleOverlay,
)


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _overlay_with(*regions: ModuleRegion) -> ShipModuleOverlay:
    ov = ShipModuleOverlay()
    for r in regions:
        ov.register_region(r)
    return ov


def _region(
    module_id: str = "weapon_01",
    x: int = 2,
    y: int = 2,
    w: int = 4,
    h: int = 4,
) -> ModuleRegion:
    return ModuleRegion(module_id=module_id, x=x, y=y, w=w, h=h)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_empty_overlay(self) -> None:
        ov = ShipModuleOverlay()
        assert ov.module_ids() == ()
        assert ov.get_region("x") is None

    def test_register_region(self) -> None:
        ov = _overlay_with(_region("weapon_01"))
        assert "weapon_01" in ov.module_ids()
        assert ov.get_region("weapon_01") is not None

    def test_reregistration_overwrites(self) -> None:
        ov = _overlay_with(_region("m", x=0, y=0, w=2, h=2))
        ov.register_region(_region("m", x=5, y=5, w=3, h=3))
        r = ov.get_region("m")
        assert r is not None and r.x == 5 and r.w == 3

    def test_clear_removes_regions_and_flashes(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.trigger_flash("m")
        ov.clear()
        assert ov.module_ids() == ()
        assert not ov.has_active_flash("m")


# ---------------------------------------------------------------------------
# Persistent state transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    def test_default_state_is_normal(self) -> None:
        ov = _overlay_with(_region("m"))
        r = ov.get_region("m")
        assert r is not None and r.state == ModuleOverlayState.NORMAL

    def test_set_state_returns_true_on_change(self) -> None:
        ov = _overlay_with(_region("m"))
        assert ov.set_state("m", ModuleOverlayState.HIGHLIGHTED) is True
        assert ov.get_region("m").state == ModuleOverlayState.HIGHLIGHTED  # type: ignore[union-attr]

    def test_set_state_returns_false_on_noop(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.HIGHLIGHTED)
        assert ov.set_state("m", ModuleOverlayState.HIGHLIGHTED) is False

    def test_set_state_returns_false_for_unknown_module(self) -> None:
        ov = ShipModuleOverlay()
        assert ov.set_state("missing", ModuleOverlayState.HIGHLIGHTED) is False

    def test_destroyed_is_terminal(self) -> None:
        """Spec §4.2: 'persistent visual marker stays for rest of combat'."""
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.DESTROYED)
        assert ov.set_state("m", ModuleOverlayState.NORMAL) is False
        assert ov.get_region("m").state == ModuleOverlayState.DESTROYED  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Flash
# ---------------------------------------------------------------------------


class TestFlash:
    def test_trigger_flash_activates(self) -> None:
        ov = _overlay_with(_region("m"))
        assert ov.trigger_flash("m") is True
        assert ov.has_active_flash("m")

    def test_unknown_module_flash_rejected(self) -> None:
        ov = ShipModuleOverlay()
        assert ov.trigger_flash("nope") is False

    def test_destroyed_module_cannot_flash(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.DESTROYED)
        assert ov.trigger_flash("m") is False
        assert not ov.has_active_flash("m")

    def test_flash_expires_after_duration(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.trigger_flash("m")
        ov.update(FLASH_DURATION + 0.01)
        assert not ov.has_active_flash("m")

    def test_flash_persists_before_duration(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.trigger_flash("m")
        ov.update(FLASH_DURATION * 0.5)
        assert ov.has_active_flash("m")

    def test_negative_dt_ignored(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.trigger_flash("m")
        ov.update(-1.0)
        assert ov.has_active_flash("m")

    def test_unknown_band_falls_back_to_solari_chrome(self) -> None:
        ov = _overlay_with(_region("m"))
        assert ov.trigger_flash("m", band_name="nonexistent_band") is True
        assert ov.has_active_flash("m")


# ---------------------------------------------------------------------------
# Hit detection
# ---------------------------------------------------------------------------


class TestHitDetection:
    def test_module_at_pixel_inside_region(self) -> None:
        ov = _overlay_with(_region("m", x=2, y=2, w=4, h=4))
        # grid (2,2) at cell_size=4 → pixel (8, 8)
        assert ov.module_at_pixel(8, 8, cell_size=4) == "m"
        # center of region (3,3)*4 = (12,12)
        assert ov.module_at_pixel(14, 14, cell_size=4) == "m"

    def test_module_at_pixel_outside_region(self) -> None:
        ov = _overlay_with(_region("m", x=2, y=2, w=4, h=4))
        assert ov.module_at_pixel(0, 0, cell_size=4) is None
        assert ov.module_at_pixel(100, 100, cell_size=4) is None

    def test_module_at_pixel_boundary(self) -> None:
        ov = _overlay_with(_region("m", x=2, y=2, w=4, h=4))
        # Right edge at (2+4)*4 = 24 — exclusive
        assert ov.module_at_pixel(24, 10, cell_size=4) is None
        # Just inside
        assert ov.module_at_pixel(23, 10, cell_size=4) == "m"

    def test_module_at_pixel_multiple_regions(self) -> None:
        ov = _overlay_with(
            _region("a", x=0, y=0, w=3, h=3),
            _region("b", x=5, y=0, w=3, h=3),
        )
        assert ov.module_at_pixel(4, 4, cell_size=4) == "a"  # inside a
        assert ov.module_at_pixel(24, 4, cell_size=4) == "b"  # inside b
        # Gap between regions
        assert ov.module_at_pixel(16, 4, cell_size=4) is None

    def test_invalid_cell_size_returns_none(self) -> None:
        ov = _overlay_with(_region("m"))
        assert ov.module_at_pixel(10, 10, cell_size=0) is None
        assert ov.module_at_pixel(10, 10, cell_size=-5) is None


# ---------------------------------------------------------------------------
# Rendering — state-specific palette coloring
# ---------------------------------------------------------------------------


def _render(ov: ShipModuleOverlay, w: int = 80, h: int = 60) -> pygame.Surface:
    target = pygame.Surface((w, h), pygame.SRCALPHA)
    target.fill((0, 0, 0, 0))
    ov.render(target, origin_x=0, origin_y=0, cell_size=4)
    return target


def _surface_contains_color(
    surf: pygame.Surface, expected: tuple[int, int, int]
) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            px = surf.get_at((x, y))
            if px.a == 0:
                continue
            if (px.r, px.g, px.b) == expected:
                return True
    return False


class TestStateRendering:
    def test_normal_state_produces_no_pixels(self) -> None:
        ov = _overlay_with(_region("m"))
        surf = _render(ov)
        any_opaque = any(
            surf.get_at((x, y)).a > 0
            for y in range(surf.get_height())
            for x in range(surf.get_width())
        )
        assert not any_opaque

    def test_highlighted_uses_hud_warning(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.HIGHLIGHTED)
        surf = _render(ov)
        assert _surface_contains_color(surf, get_role("hud_warning"))

    def test_committed_uses_hud_critical(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.COMMITTED)
        surf = _render(ov)
        assert _surface_contains_color(surf, get_role("hud_critical"))

    def test_damaged_uses_rivet_role(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.DAMAGED)
        surf = _render(ov)
        # The tint is alpha-blended over transparent — at full region
        # depth no blending occurs, so the expected role RGB is present.
        assert _surface_contains_color(surf, get_role("rivet"))

    def test_destroyed_uses_steel_shadow_deep_and_seam(self) -> None:
        """Spec §4.2: steel_shadow_deep fill + seam outline."""
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.DESTROYED)
        surf = _render(ov)
        steel_deep = get_band("steel")[0]
        seam = get_role("seam")
        # Blended fill: over transparent background, RGB == steel_deep.
        assert _surface_contains_color(surf, steel_deep)
        assert _surface_contains_color(surf, seam)

    def test_flash_uses_band_specular(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.trigger_flash("m", band_name="solari_chrome")
        surf = _render(ov)
        specular = get_band("solari_chrome")[-1]
        # At t=0 the flash is at peak alpha. Over transparent, RGB matches.
        assert _surface_contains_color(surf, specular)

    def test_flash_decays_to_zero_alpha(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.trigger_flash("m", band_name="solari_chrome")
        # Sample flash alphas at progressively later elapsed times.
        ov.update(FLASH_DURATION - 0.001)
        surf_late = _render(ov)
        # Late-flash surface should have substantially less opacity than
        # early. Sample by summing alphas.
        ov2 = _overlay_with(_region("m"))
        ov2.trigger_flash("m", band_name="solari_chrome")
        surf_early = _render(ov2)

        def alpha_sum(s: pygame.Surface) -> int:
            return sum(
                s.get_at((x, y)).a
                for y in range(s.get_height())
                for x in range(s.get_width())
            )

        assert alpha_sum(surf_late) < alpha_sum(surf_early)


# ---------------------------------------------------------------------------
# Palette compliance
# ---------------------------------------------------------------------------


class TestPaletteCompliance:
    def test_highlighted_render_is_role_compliant(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.HIGHLIGHTED)
        surf = _render(ov)
        assert_role_compliance(surf, tolerance=4.0)

    def test_committed_render_is_role_compliant(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.COMMITTED)
        surf = _render(ov)
        assert_role_compliance(surf, tolerance=4.0)

    def test_damaged_render_is_role_compliant(self) -> None:
        ov = _overlay_with(_region("m"))
        ov.set_state("m", ModuleOverlayState.DAMAGED)
        surf = _render(ov)
        assert_role_compliance(surf, tolerance=4.0)


# ---------------------------------------------------------------------------
# Rendering layering
# ---------------------------------------------------------------------------


class TestRenderLayering:
    def test_flash_renders_above_persistent_state(self) -> None:
        """Flash alters the rendered output while active; tint returns after expiry.

        Alpha-blending the specular flash over the rivet tint produces
        intermediate RGBs that don't match either role exactly — so we
        assert *difference from baseline* rather than exact colors. The
        pure states elsewhere are palette-compliant; this test just
        verifies the flash layer actually composites on top.
        """
        # Baseline: DAMAGED only.
        ov_base = _overlay_with(_region("m"))
        ov_base.set_state("m", ModuleOverlayState.DAMAGED)
        surf_base = _render(ov_base)

        # Same region, DAMAGED + active flash at peak.
        ov_flash = _overlay_with(_region("m"))
        ov_flash.set_state("m", ModuleOverlayState.DAMAGED)
        ov_flash.trigger_flash("m", band_name="solari_chrome")
        surf_flash = _render(ov_flash)

        differ = any(
            surf_base.get_at((x, y)) != surf_flash.get_at((x, y))
            for y in range(surf_base.get_height())
            for x in range(surf_base.get_width())
        )
        assert differ, "Peak flash should visibly differ from DAMAGED-only render"

        # After expiry, rivet tint remains visible.
        ov_flash.update(FLASH_DURATION + 0.01)
        assert not ov_flash.has_active_flash("m")
        surf_after = _render(ov_flash)
        assert _surface_contains_color(surf_after, get_role("rivet"))

    def test_origin_offset_applies_to_all_regions(self) -> None:
        ov = _overlay_with(_region("m", x=1, y=1, w=2, h=2))
        ov.set_state("m", ModuleOverlayState.HIGHLIGHTED)
        target = pygame.Surface((40, 40), pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        ov.render(target, origin_x=10, origin_y=10, cell_size=4)
        # Region with x=1,y=1 at cell_size=4 starts at grid (4,4);
        # origin-offset by (10,10) puts it at screen (14,14).
        # No pixels before origin.
        assert all(target.get_at((x, y)).a == 0 for y in range(14) for x in range(14))
        # Some pixels inside the expected region.
        any_opaque = any(
            target.get_at((x, y)).a > 0 for y in range(14, 22) for x in range(14, 22)
        )
        assert any_opaque

    def test_cell_size_scales_region(self) -> None:
        ov = _overlay_with(_region("m", x=0, y=0, w=2, h=2))
        ov.set_state("m", ModuleOverlayState.COMMITTED)
        # cell_size=8 → rendered region is 16x16 starting at (0,0)
        target = pygame.Surface((40, 40), pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        ov.render(target, origin_x=0, origin_y=0, cell_size=8)
        # Pixels at (20, 20) are outside the 16x16 region.
        assert target.get_at((20, 20)).a == 0
        # Pixels inside.
        any_opaque = any(
            target.get_at((x, y)).a > 0 for y in range(2, 14) for x in range(2, 14)
        )
        assert any_opaque
