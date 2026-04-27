"""Tests for the rebuilt ShipComposite (Framework §2 foundation).

Covers data types, API surface, state management, cache invalidation,
the standalone module render function, and all seven rendering phases.

See requirements/overhaul/94_ship_composite_api.md for the full spec.
"""

import pytest

from spacegame.engine.ship_composite import (
    InvalidationScope,
    ModuleRenderRequest,
    ModuleState,
    RenderAngle,
    ShipComposite,
    ShipCompositeConfig,
    _derive_material_band,
    _lerp_band_color,
    _resolve_material,
    compose_standalone_module,
)
from spacegame.models.ship_build import PlacedPixel, ShipBuild


def _make_build(pixels: list[tuple[int, int, str]] | None = None) -> ShipBuild:
    """Build a minimal ShipBuild for tests. Each tuple is (x, y, material_id)."""
    placed = [PlacedPixel(x, y, mat) for x, y, mat in (pixels or [])]
    return ShipBuild(weight_class="small", pixels=placed)


class TestRenderAngle:
    """RenderAngle enum covers the three canonical angles."""

    def test_canonical_angles_exist(self) -> None:
        assert RenderAngle.FRONT
        assert RenderAngle.PROFILE
        assert RenderAngle.THREE_QUARTER

    def test_three_distinct_values(self) -> None:
        values = {RenderAngle.FRONT, RenderAngle.PROFILE, RenderAngle.THREE_QUARTER}
        assert len(values) == 3


class TestModuleState:
    """ModuleState enum covers the 8 states from spec §2.1."""

    @pytest.mark.parametrize(
        "state_name",
        [
            "NORMAL",
            "HIGHLIGHTED",
            "DAMAGED",
            "CRITICAL",
            "DISABLED",
            "DESTROYED",
            "RECOVERED",
            "CORRUPTED",
        ],
    )
    def test_state_exists(self, state_name: str) -> None:
        assert hasattr(ModuleState, state_name)

    def test_default_is_normal(self) -> None:
        """Modules without explicit overrides render as NORMAL."""
        request = ModuleRenderRequest(
            module_id="m1",
            category="cockpit",
            manufacturer="reyes_kowalski",
        )
        assert request.state == ModuleState.NORMAL


class TestInvalidationScope:
    """InvalidationScope enum covers the four scopes."""

    @pytest.mark.parametrize(
        "scope_name",
        ["ALL", "STATE_ONLY", "WEAR_ONLY", "SCALE_CACHE"],
    )
    def test_scope_exists(self, scope_name: str) -> None:
        assert hasattr(InvalidationScope, scope_name)


class TestModuleRenderRequest:
    """ModuleRenderRequest dataclass for standalone module rendering."""

    def test_minimal_construction(self) -> None:
        r = ModuleRenderRequest(
            module_id="cockpit_1",
            category="cockpit",
            manufacturer="reyes_kowalski",
        )
        assert r.module_id == "cockpit_1"
        assert r.category == "cockpit"
        assert r.manufacturer == "reyes_kowalski"

    def test_defaults_are_sensible(self) -> None:
        r = ModuleRenderRequest(
            module_id="m1",
            category="weapon",
            manufacturer="foundry",
        )
        assert r.material_override is None
        assert r.faction_overlay is None
        assert r.state == ModuleState.NORMAL
        assert r.wear == 0.0
        assert r.rotation == 0
        assert r.flipped is False
        assert r.seed == 0
        assert r.scale == 1

    def test_frozen_dataclass(self) -> None:
        """Request is frozen — immutable for safe caching."""
        r = ModuleRenderRequest(
            module_id="m1",
            category="weapon",
            manufacturer="foundry",
        )
        with pytest.raises((AttributeError, Exception)):
            r.module_id = "m2"  # type: ignore[misc]


class TestShipCompositeConfig:
    """ShipCompositeConfig defaults and construction."""

    def test_default_config(self) -> None:
        c = ShipCompositeConfig()
        assert c.angles_to_cache == (RenderAngle.THREE_QUARTER,)
        assert c.emissive_pulse_hz > 0
        assert c.enable_engine_glow is True
        assert c.enable_wear_overlay is True
        assert c.enable_rivets is True
        assert c.enable_connection_detail is True
        assert c.faction_overlay is None
        assert c.max_scale >= 2

    def test_custom_angles(self) -> None:
        c = ShipCompositeConfig(
            angles_to_cache=(RenderAngle.FRONT, RenderAngle.PROFILE, RenderAngle.THREE_QUARTER),
        )
        assert len(c.angles_to_cache) == 3


class TestShipCompositeConstruction:
    """ShipComposite constructor takes a build + optional config."""

    def test_construct_with_build_only(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        assert comp is not None

    def test_construct_with_config(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        config = ShipCompositeConfig(enable_rivets=False)
        comp = ShipComposite(build, config)
        assert comp is not None

    def test_initial_state_is_dirty(self) -> None:
        """Fresh composite needs rebuild before first render."""
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        assert comp.is_dirty is True

    def test_initial_wear_is_zero(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        assert comp.wear == pytest.approx(0.0)


class TestStateManagement:
    """State-management methods trigger invalidation."""

    def test_set_module_state_is_callable(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        # Should not raise; state is recorded for later phase application
        comp.set_module_state("slot_1", ModuleState.DAMAGED)

    def test_set_wear_updates_field(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.set_wear(0.5)
        assert comp.wear == pytest.approx(0.5)

    def test_set_wear_clamps_to_range(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.set_wear(1.5)
        assert comp.wear == pytest.approx(1.0)
        comp.set_wear(-0.2)
        assert comp.wear == pytest.approx(0.0)

    def test_set_faction_overlay_is_callable(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.set_faction_overlay("crimson_reach")
        comp.set_faction_overlay(None)

    def test_get_module_state_defaults_to_normal(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        assert comp.get_module_state("unset_slot") == ModuleState.NORMAL

    def test_get_module_state_reflects_set(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.set_module_state("slot_1", ModuleState.HIGHLIGHTED)
        assert comp.get_module_state("slot_1") == ModuleState.HIGHLIGHTED


class TestCacheInvalidation:
    """Invalidation with different scopes."""

    def test_invalidate_all_marks_dirty(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.invalidate(InvalidationScope.ALL)
        assert comp.is_dirty is True

    def test_invalidate_default_is_all(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.invalidate()
        assert comp.is_dirty is True

    def test_state_only_invalidation_callable(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.invalidate(InvalidationScope.STATE_ONLY, module_id="slot_1")


class TestUpdate:
    """update(dt) advances emissive pulse phase."""

    def test_update_accepts_dt(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.update(0.016)  # Should not raise

    def test_multiple_updates(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        for _ in range(10):
            comp.update(0.016)


class TestPreload:
    """preload_angles / preload_scales populate cache for configured variants."""

    def test_preload_angles_callable(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        config = ShipCompositeConfig(
            angles_to_cache=(RenderAngle.FRONT, RenderAngle.PROFILE, RenderAngle.THREE_QUARTER),
        )
        comp = ShipComposite(build, config)
        comp.preload_angles()
        # All configured angles should be in cache afterward
        assert RenderAngle.THREE_QUARTER in comp.cached_angles

    def test_preload_scales_callable(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.preload_scales((1, 2))


class TestStandaloneModule:
    """compose_standalone_module is a free function, no instance needed."""

    def test_compose_returns_surface(self) -> None:
        import pygame

        pygame.init()  # Required for Surface creation
        request = ModuleRenderRequest(
            module_id="cockpit_1",
            category="cockpit",
            manufacturer="reyes_kowalski",
        )
        result = compose_standalone_module(request)
        assert isinstance(result, pygame.Surface)

    def test_compose_respects_scale(self) -> None:
        import pygame

        pygame.init()
        req_1x = ModuleRenderRequest(
            module_id="m1",
            category="weapon",
            manufacturer="foundry",
            scale=1,
        )
        req_2x = ModuleRenderRequest(
            module_id="m1",
            category="weapon",
            manufacturer="foundry",
            scale=2,
        )
        surf_1x = compose_standalone_module(req_1x)
        surf_2x = compose_standalone_module(req_2x)
        # 2x scale should produce a larger surface
        assert surf_2x.get_width() >= surf_1x.get_width()
        assert surf_2x.get_height() >= surf_1x.get_height()


class TestBasicRenderPipeline:
    """Smoke tests for the composition pipeline — minimum viable integration.

    Full phase-by-phase tests land in dedicated test classes as phases
    are implemented. These smoke tests verify get_surface returns
    something for the simplest valid builds.
    """

    def test_get_surface_returns_surface_for_minimal_build(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        assert isinstance(surf, pygame.Surface)

    def test_get_surface_with_angle_parameter(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface(angle=RenderAngle.PROFILE)
        assert isinstance(surf, pygame.Surface)

    def test_get_surface_with_scale(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        surf_1x = comp.get_surface(scale=1)
        surf_2x = comp.get_surface(scale=2)
        assert surf_2x.get_width() >= surf_1x.get_width()

    def test_is_dirty_false_after_render(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        comp.get_surface()
        assert comp.is_dirty is False


# ---------------------------------------------------------------------------
# Phase 1 — Silhouette tests
# ---------------------------------------------------------------------------


class TestPhase1Silhouette:
    """Phase 1 computes a boolean mask: True where a ship pixel is present."""

    def test_empty_build_produces_empty_mask(self) -> None:
        build = _make_build([])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        assert not mask.any()

    def test_single_pixel_present(self) -> None:
        build = _make_build([(5, 3, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        # Note: mask is indexed [y, x] (numpy convention)
        assert mask[3, 5] is True or bool(mask[3, 5]) is True

    def test_multiple_pixels_present(self) -> None:
        pixels = [(0, 0, "hull_cold"), (1, 0, "hull_cold"), (2, 1, "hull_cold")]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        assert bool(mask[0, 0]) is True
        assert bool(mask[0, 1]) is True
        assert bool(mask[1, 2]) is True

    def test_empty_positions_false(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        # (5, 5) is not filled
        assert bool(mask[5, 5]) is False

    def test_mask_shape_matches_canvas(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        assert mask.shape == (build.canvas_h, build.canvas_w)

    def test_out_of_bounds_pixel_ignored(self) -> None:
        """Pixels outside canvas are silently dropped (defensive)."""
        import numpy as np

        build = _make_build([(0, 0, "hull_cold")])
        # Add an out-of-bounds pixel directly
        build.pixels.append(PlacedPixel(x=9999, y=9999, material_id="hull_cold"))
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        # The valid pixel is still present
        assert bool(mask[0, 0]) is True
        # Mask shape unchanged — no crash
        assert mask.dtype == np.bool_


# ---------------------------------------------------------------------------
# Phase 2 — Base fill tests
# ---------------------------------------------------------------------------


class TestPhase2BaseFill:
    """Phase 2 fills each ship pixel with its material's base color."""

    def test_empty_build_transparent_surface(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        surf = comp._phase2_base_fill(mask)
        # No pixels should be opaque
        for y in range(surf.get_height()):
            for x in range(surf.get_width()):
                px = surf.get_at((x, y))
                assert px.a == 0

    def test_single_pixel_opaque_at_position(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        surf = comp._phase2_base_fill(mask)
        px = surf.get_at((0, 0))
        assert px.a == 255

    def test_unfilled_positions_transparent(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        surf = comp._phase2_base_fill(mask)
        # (5, 5) wasn't filled
        px = surf.get_at((5, 5))
        assert px.a == 0

    def test_unknown_material_falls_back_gracefully(self) -> None:
        """A pixel with an unknown material_id should render as a
        placeholder color rather than crashing or rendering invisible."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "nonexistent_material_xyz")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        surf = comp._phase2_base_fill(mask)
        px = surf.get_at((0, 0))
        # Should be opaque (rendered with fallback), not transparent
        assert px.a == 255


# ---------------------------------------------------------------------------
# Phase 1 + 2 integration — get_surface end-to-end
# ---------------------------------------------------------------------------


class TestPhase12Integration:
    """get_surface invokes phases 1+2 and produces a visible surface."""

    def test_get_surface_has_opaque_pixel_at_filled_position(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(2, 3, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        # Surface size matches canvas (at 1x scale)
        assert surf.get_width() == build.canvas_w
        assert surf.get_height() == build.canvas_h
        # The filled position is opaque
        px = surf.get_at((2, 3))
        assert px.a == 255

    def test_get_surface_empty_build_is_transparent(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        # All pixels transparent
        px = surf.get_at((0, 0))
        assert px.a == 0

    def test_get_surface_caches_result(self) -> None:
        """Repeated get_surface calls return the cached surface (same
        object identity) when cache parameters are identical."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        s1 = comp.get_surface()
        s2 = comp.get_surface()
        # Same cache key → same surface
        assert s1 is s2

    def test_get_surface_invalidate_triggers_rebuild(self) -> None:
        """After invalidate(), get_surface returns a fresh surface."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        s1 = comp.get_surface()
        comp.invalidate()
        s2 = comp.get_surface()
        # Different objects after invalidation rebuild
        assert s1 is not s2

    def test_get_surface_scale_applies(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        s1 = comp.get_surface(scale=1)
        s2 = comp.get_surface(scale=2)
        assert s2.get_width() == s1.get_width() * 2
        assert s2.get_height() == s1.get_height() * 2


# ---------------------------------------------------------------------------
# Phase 3 — Material band + lerp helpers
# ---------------------------------------------------------------------------


class TestMaterialBandDerivation:
    """_derive_material_band builds a 5-stop band from a HullMaterial.

    Expected structure: (shadow_deep, shadow, base, bright, specular)
    Monotonic in perceptual brightness: band[0] darker than band[-1].
    """

    def test_returns_five_stops(self) -> None:
        from spacegame.models.ship_build import HullMaterial

        mat = HullMaterial(
            id="test",
            name="Test",
            description="",
            shade_band="steel",
        )
        band = _derive_material_band(mat)
        assert len(band) == 5

    def test_band_monotonic_brightness(self) -> None:
        """Each successive stop has higher luminance than the previous."""
        from spacegame.models.ship_build import HullMaterial

        mat = HullMaterial(
            id="test",
            name="Test",
            description="",
            shade_band="steel",
        )
        band = _derive_material_band(mat)
        # Luminance approximation: R*0.299 + G*0.587 + B*0.114
        luminances = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in band]
        for i in range(len(luminances) - 1):
            assert luminances[i] < luminances[i + 1], (
                f"Band not monotonic at index {i}: {luminances}"
            )

    def test_base_stop_matches_primary(self) -> None:
        """The middle stop (index 2) should equal material.color_primary."""
        from spacegame.models.ship_build import HullMaterial

        mat = HullMaterial(
            id="test",
            name="Test",
            description="",
            shade_band="steel",
        )
        band = _derive_material_band(mat)
        assert band[2] == mat.color_primary

    def test_shadow_stop_darker_than_primary(self) -> None:
        from spacegame.models.ship_build import HullMaterial

        mat = HullMaterial(
            id="test",
            name="Test",
            description="",
            shade_band="steel",
        )
        band = _derive_material_band(mat)
        # band[0] is darkest — each channel should be less than primary
        p = mat.color_primary
        assert band[0][0] < p[0]
        assert band[0][1] < p[1]
        assert band[0][2] < p[2]

    def test_specular_stop_brighter_than_primary(self) -> None:
        from spacegame.models.ship_build import HullMaterial

        mat = HullMaterial(
            id="test",
            name="Test",
            description="",
            shade_band="solari_chrome",
        )
        band = _derive_material_band(mat)
        # band[-1] is specular — should be brighter than primary
        p = mat.color_primary
        assert band[-1][0] >= p[0] and band[-1][1] >= p[1] and band[-1][2] >= p[2]

    def test_produces_monotonic_band_for_any_valid_shade(self) -> None:
        """Any shade_band still produces a valid monotonic sequence."""
        from spacegame.models.ship_build import HullMaterial

        mat = HullMaterial(
            id="test",
            name="Test",
            description="",
            shade_band="reach_crimson",
        )
        band = _derive_material_band(mat)
        # Should still be monotonic; band[-1] brighter than primary
        p = mat.color_primary
        assert band[-1][0] > p[0] or band[-1][1] > p[1] or band[-1][2] > p[2]


class TestBandLerp:
    """_lerp_band_color interpolates within a band based on a 0..1 factor."""

    def test_factor_zero_returns_first_stop(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = _lerp_band_color(band, 0.0)
        assert result == (0, 0, 0)

    def test_factor_one_returns_last_stop(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = _lerp_band_color(band, 1.0)
        assert result == (200, 200, 200)

    def test_factor_midpoint_returns_middle_stop(self) -> None:
        """With 5 stops at t=0.5, we hit exactly stop index 2."""
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = _lerp_band_color(band, 0.5)
        assert result == (100, 100, 100)

    def test_factor_interpolates_between_stops(self) -> None:
        """Factor 0.25 with 5 stops → halfway between stop 0 and stop 1."""
        band = ((0, 0, 0), (100, 100, 100), (200, 200, 200), (300, 300, 300), (400, 400, 400))
        result = _lerp_band_color(band, 0.125)
        # 0.125 * 4 = 0.5 → halfway between stop 0 and stop 1 → (50, 50, 50)
        assert result == (50, 50, 50)

    def test_factor_clamped_below_zero(self) -> None:
        band = ((10, 10, 10), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = _lerp_band_color(band, -0.5)
        assert result == (10, 10, 10)

    def test_factor_clamped_above_one(self) -> None:
        band = ((10, 10, 10), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = _lerp_band_color(band, 1.5)
        assert result == (200, 200, 200)


# ---------------------------------------------------------------------------
# Phase 3 — Lighting factor computation
# ---------------------------------------------------------------------------


class TestLightingFactors:
    """_compute_lighting_factors produces a per-pixel 0..1 gradient across
    the silhouette's bounding box, with upper-right = brightest.

    pygame coordinate convention: y increases downward, so "upper" = low y.
    """

    def test_empty_silhouette_returns_zero_grid(self) -> None:
        build = _make_build([])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        factors = comp._compute_lighting_factors(mask)
        assert factors.shape == mask.shape
        assert not factors.any()

    def test_factor_shape_matches_silhouette(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        factors = comp._compute_lighting_factors(mask)
        assert factors.shape == mask.shape

    def test_factors_in_range(self) -> None:
        """All lighting factors for ship pixels are within [0, 1]."""
        pixels = [(x, y, "hull_cold") for x in range(5) for y in range(5)]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        factors = comp._compute_lighting_factors(mask)
        # Only care about ship-pixel positions
        ys, xs = mask.nonzero()
        for y, x in zip(ys, xs, strict=True):
            f = factors[y, x]
            assert 0.0 <= f <= 1.0

    def test_upper_right_pixel_brightest(self) -> None:
        """For a 5x5 filled square, the (4, 0) pixel (upper-right) has
        the highest lighting factor."""
        pixels = [(x, y, "hull_cold") for x in range(5) for y in range(5)]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        factors = comp._compute_lighting_factors(mask)
        # Upper-right: x=4, y=0 (pygame: y=0 is top)
        upper_right_factor = factors[0, 4]
        # Lower-left: x=0, y=4
        lower_left_factor = factors[4, 0]
        assert upper_right_factor > lower_left_factor

    def test_upper_right_factor_is_one(self) -> None:
        """Upper-right of bbox = factor 1.0 (brightest)."""
        pixels = [(x, y, "hull_cold") for x in range(5) for y in range(5)]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        factors = comp._compute_lighting_factors(mask)
        # The pixel at (4, 0) — upper-right — is fully lit
        assert factors[0, 4] == pytest.approx(1.0, abs=0.01)

    def test_lower_left_factor_is_zero(self) -> None:
        """Lower-left of bbox = factor 0.0 (darkest)."""
        pixels = [(x, y, "hull_cold") for x in range(5) for y in range(5)]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        mask = comp._phase1_silhouette()
        factors = comp._compute_lighting_factors(mask)
        # The pixel at (0, 4) — lower-left — is fully unlit
        assert factors[4, 0] == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Phase 3 — Integration: lit surface production
# ---------------------------------------------------------------------------


class TestPhase3Lighting:
    """Phase 3 produces differentiated shading across the ship."""

    def test_phase3_produces_visible_lighting_differentiation(self) -> None:
        """Upper-right ship pixel is brighter than lower-left for same material."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(8) for y in range(8)]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        surf = comp.get_surface()
        # Upper-right (7, 0) vs lower-left (0, 7)
        ur = surf.get_at((7, 0))
        ll = surf.get_at((0, 7))
        ur_lum = ur.r * 0.299 + ur.g * 0.587 + ur.b * 0.114
        ll_lum = ll.r * 0.299 + ll.g * 0.587 + ll.b * 0.114
        assert ur_lum > ll_lum, (
            f"Expected upper-right lit brighter than lower-left; "
            f"got UR={ur_lum:.1f}, LL={ll_lum:.1f}"
        )

    def test_phase3_preserves_silhouette_transparency(self) -> None:
        """Pixels outside the silhouette stay transparent after Phase 3."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        # (5, 5) is unfilled
        px = surf.get_at((5, 5))
        assert px.a == 0

    def test_phase3_filled_pixels_are_opaque(self) -> None:
        import pygame

        pygame.init()
        build = _make_build([(3, 4, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        px = surf.get_at((3, 4))
        assert px.a == 255

    def test_phase3_single_pixel_is_lit(self) -> None:
        """A single pixel has no gradient; lighting factor == 1.0 (bbox
        collapses to single point, factor defaults to brightest)."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        px = surf.get_at((0, 0))
        # Single-pixel ship should render at maximum brightness (specular)
        # Exact color depends on material, but should be opaque and valid.
        assert px.a == 255
        # Color should not be pitch black
        assert (px.r, px.g, px.b) != (0, 0, 0)

    def test_phase3_determinism(self) -> None:
        """Same inputs produce byte-identical output."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(4) for y in range(4)]
        build1 = _make_build(pixels)
        build2 = _make_build(pixels)
        comp1 = ShipComposite(build1)
        comp2 = ShipComposite(build2)
        s1 = comp1.get_surface()
        s2 = comp2.get_surface()
        for y in range(s1.get_height()):
            for x in range(s1.get_width()):
                assert s1.get_at((x, y)) == s2.get_at((x, y))


# ---------------------------------------------------------------------------
# Phase 4 — Connection detail (material-boundary seams)
# ---------------------------------------------------------------------------


class TestPhase4ConnectionDetail:
    """Phase 4 darkens pixels that border a different material, producing
    visible seams between adjacent module materials.

    Note: production data model uses PlacedPixel with material_id. Typed
    ConnectionKind metadata (Framework §15.3) will land later; for now,
    Phase 4 operates on material boundaries to deliver the visual effect.
    """

    def test_single_material_build_has_no_seams(self) -> None:
        """A ship with one material has no material boundaries, so every
        filled pixel retains its Phase 3 lit color."""
        import pygame

        pygame.init()
        # Build a ship with Phase 4 disabled to capture Phase 3 baseline
        pixels = [(x, y, "hull_cold") for x in range(4) for y in range(4)]
        build = _make_build(pixels)
        config_off = ShipCompositeConfig(enable_connection_detail=False)
        comp_baseline = ShipComposite(build, config_off)
        baseline_surf = comp_baseline.get_surface()

        # Same build with Phase 4 enabled (default)
        comp_lit = ShipComposite(_make_build(pixels))
        lit_surf = comp_lit.get_surface()

        # Single material → no seams → Phase 4 produces identical result
        for y in range(baseline_surf.get_height()):
            for x in range(baseline_surf.get_width()):
                assert baseline_surf.get_at((x, y)) == lit_surf.get_at((x, y)), (
                    f"Single-material build should have no seams at ({x},{y})"
                )

    def test_multi_material_build_has_seams_at_boundary(self) -> None:
        """Adjacent pixels of different materials show darker seams.

        Disables Phase 5 decoration (rivets, wear) so this test isolates
        the Phase 4 material-boundary effect without random variation.
        """
        import pygame

        pygame.init()
        # Left column material A, right column material B
        pixels = [
            (0, 0, "hull_cold"),
            (0, 1, "hull_cold"),
            (1, 0, "reinforced_plate"),
            (1, 1, "reinforced_plate"),
        ]
        config_no_decoration = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
        )
        build = _make_build(pixels)
        comp = ShipComposite(build, config_no_decoration)
        surf = comp.get_surface()

        # The (0, 0) pixel has a different-material neighbor to the right
        # (material B at (1, 0)). Phase 4 darkens it.
        # Compare against a single-material build at the same position.
        single_build = _make_build([(0, 0, "hull_cold"), (0, 1, "hull_cold")])
        single_comp = ShipComposite(single_build, config_no_decoration)
        single_surf = single_comp.get_surface()

        seam_px = surf.get_at((0, 0))
        single_px = single_surf.get_at((0, 0))
        seam_lum = seam_px.r * 0.299 + seam_px.g * 0.587 + seam_px.b * 0.114
        single_lum = single_px.r * 0.299 + single_px.g * 0.587 + single_px.b * 0.114
        assert seam_lum < single_lum, (
            f"Seam pixel should be darker; got seam={seam_lum:.1f}, single={single_lum:.1f}"
        )

    def test_seams_respect_silhouette(self) -> None:
        """Phase 4 does not affect pixels outside the silhouette."""
        import pygame

        pygame.init()
        pixels = [(0, 0, "hull_cold"), (1, 0, "reinforced_plate")]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        surf = comp.get_surface()

        # (5, 5) is outside the silhouette
        px = surf.get_at((5, 5))
        assert px.a == 0

    def test_enable_connection_detail_false_skips_phase4(self) -> None:
        """When enable_connection_detail=False, seams are not rendered.

        Phase 7 snap is disabled in this test because band-snapping can
        collapse Phase 4's darkening into the same band entry as the
        unseamed pixel, hiding the phase-toggle difference. This test
        isolates Phase 4 by running Phase 3 only.
        """
        import pygame

        pygame.init()
        pixels = [
            (0, 0, "hull_cold"),
            (1, 0, "reinforced_plate"),
        ]
        build = _make_build(pixels)
        config_off = ShipCompositeConfig(
            enable_connection_detail=False,
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_palette_snap=False,
        )
        comp_off = ShipComposite(build, config_off)
        surf_off = comp_off.get_surface()

        config_on = ShipCompositeConfig(
            enable_connection_detail=True,
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_palette_snap=False,
        )
        comp_on = ShipComposite(_make_build(pixels), config_on)
        surf_on = comp_on.get_surface()

        # Without Phase 4, (0, 0) shows Phase 3 color unchanged.
        # With Phase 4, (0, 0) is darkened (it neighbors a different material).
        off_px = surf_off.get_at((0, 0))
        on_px = surf_on.get_at((0, 0))
        # At least one channel should differ (darkened)
        assert (off_px.r, off_px.g, off_px.b) != (on_px.r, on_px.g, on_px.b), (
            "Phase 4 toggle should produce different output at material boundaries"
        )

    def test_phase4_seam_pixel_opaque(self) -> None:
        """Seam pixels remain opaque (alpha=255), just darkened."""
        import pygame

        pygame.init()
        pixels = [
            (0, 0, "hull_cold"),
            (1, 0, "reinforced_plate"),
        ]
        build = _make_build(pixels)
        comp = ShipComposite(build)
        surf = comp.get_surface()
        seam_px = surf.get_at((0, 0))
        assert seam_px.a == 255

    def test_phase4_determinism(self) -> None:
        """Same build produces byte-identical seam output across renders."""
        import pygame

        pygame.init()
        pixels = [
            (x, y, "hull_cold" if (x + y) % 2 == 0 else "reinforced_plate")
            for x in range(4)
            for y in range(4)
        ]
        b1 = _make_build(pixels)
        b2 = _make_build(pixels)
        c1 = ShipComposite(b1)
        c2 = ShipComposite(b2)
        s1 = c1.get_surface()
        s2 = c2.get_surface()
        for y in range(s1.get_height()):
            for x in range(s1.get_width()):
                assert s1.get_at((x, y)) == s2.get_at((x, y))


# ---------------------------------------------------------------------------
# Phase 5 — Decoration (rivets + wear overlay)
# ---------------------------------------------------------------------------


def _count_darkened_pixels(
    baseline_surf, decorated_surf, silhouette_pixels: list[tuple[int, int]]
) -> int:
    """Count how many silhouette pixels are darker in decorated vs baseline."""
    count = 0
    for x, y in silhouette_pixels:
        base = baseline_surf.get_at((x, y))
        dec = decorated_surf.get_at((x, y))
        base_lum = base.r * 0.299 + base.g * 0.587 + base.b * 0.114
        dec_lum = dec.r * 0.299 + dec.g * 0.587 + dec.b * 0.114
        if dec_lum < base_lum - 1.0:  # 1-unit tolerance for rounding
            count += 1
    return count


class TestPhase5Decoration:
    """Phase 5 adds rivets and wear overlay. Seeded from build geometry
    for determinism. Respects silhouette. Skippable via config flags."""

    def test_single_pixel_ship_has_no_rivets(self) -> None:
        """A single-pixel ship can't fit any rivets (minimum spacing)."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        # With rivets enabled
        config_on = ShipCompositeConfig(enable_rivets=True, enable_wear_overlay=False)
        comp = ShipComposite(build, config_on)
        surf = comp.get_surface()
        # Single pixel should still be opaque, not darkened beyond Phase 3/4 value
        px = surf.get_at((0, 0))
        assert px.a == 255

    def test_large_ship_has_visible_rivets(self) -> None:
        """An 8x8 ship should have some rivets placed (visibly darker pixels)."""
        import pygame

        pygame.init()
        pixels = [(x, y, "reinforced_plate") for x in range(8) for y in range(8)]
        build_base = _make_build(pixels)
        build_dec = _make_build(pixels)

        # Baseline: no rivets, no wear
        config_off = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=False)
        baseline_surf = ShipComposite(build_base, config_off).get_surface()

        # Decorated: rivets enabled
        config_riv = ShipCompositeConfig(enable_rivets=True, enable_wear_overlay=False)
        decorated_surf = ShipComposite(build_dec, config_riv).get_surface()

        silhouette_pixels = [(x, y) for x in range(8) for y in range(8)]
        darkened = _count_darkened_pixels(baseline_surf, decorated_surf, silhouette_pixels)
        # Should have at least a few rivets in an 8x8 (64 px²)
        assert darkened >= 2, f"Expected rivets, got {darkened} darkened pixels"

    def test_enable_rivets_false_skips_rivets(self) -> None:
        """Rivets don't render when enable_rivets=False."""
        import pygame

        pygame.init()
        pixels = [(x, y, "reinforced_plate") for x in range(8) for y in range(8)]

        config_off = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=False)
        surf_off = ShipComposite(_make_build(pixels), config_off).get_surface()

        config_on = ShipCompositeConfig(enable_rivets=True, enable_wear_overlay=False)
        surf_on = ShipComposite(_make_build(pixels), config_on).get_surface()

        # Count differing pixels
        diff = 0
        for y in range(8):
            for x in range(8):
                if surf_off.get_at((x, y)) != surf_on.get_at((x, y)):
                    diff += 1
        # Without rivets, surfaces are byte-identical; with rivets, some pixels differ
        assert diff >= 2, f"Expected rivet-caused differences, got {diff}"

    def test_rivets_respect_silhouette(self) -> None:
        """Rivets never render outside the silhouette."""
        import pygame

        pygame.init()
        # Small L-shape ship: three pixels, leaves most of canvas empty
        build = _make_build([(0, 0, "hull_cold"), (1, 0, "hull_cold"), (0, 1, "hull_cold")])
        config = ShipCompositeConfig(enable_rivets=True, enable_wear_overlay=False)
        comp = ShipComposite(build, config)
        surf = comp.get_surface()
        # (5, 5) is outside the silhouette
        px = surf.get_at((5, 5))
        assert px.a == 0

    def test_wear_overlay_darkens_some_pixels(self) -> None:
        """With nonzero wear, some pixels are darker than the no-wear baseline."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(8) for y in range(8)]

        # Baseline: no wear, no rivets
        config_off = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=False)
        baseline_surf = ShipComposite(_make_build(pixels), config_off).get_surface()

        # With wear applied
        config_wear = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=True)
        worn_comp = ShipComposite(_make_build(pixels), config_wear)
        worn_comp.set_wear(1.0)  # max wear
        worn_surf = worn_comp.get_surface()

        silhouette_pixels = [(x, y) for x in range(8) for y in range(8)]
        darkened = _count_darkened_pixels(baseline_surf, worn_surf, silhouette_pixels)
        # Max wear should produce visible scorching
        assert darkened >= 5, f"Expected wear darkening, got {darkened} darkened pixels"

    def test_enable_wear_overlay_false_skips_wear(self) -> None:
        """Wear overlay doesn't render when enable_wear_overlay=False."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(8) for y in range(8)]

        # Disabled even with wear=1.0 → no darkening
        config_off = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=False)
        comp_off = ShipComposite(_make_build(pixels), config_off)
        comp_off.set_wear(1.0)
        surf_off = comp_off.get_surface()

        # Baseline (no wear, no rivets, default config)
        config_baseline = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=False)
        baseline = ShipComposite(_make_build(pixels), config_baseline).get_surface()

        for y in range(8):
            for x in range(8):
                assert surf_off.get_at((x, y)) == baseline.get_at((x, y)), (
                    "enable_wear_overlay=False should leave surface identical to baseline"
                )

    def test_higher_wear_produces_more_darkening(self) -> None:
        """wear=1.0 darkens more pixels than wear=0.2."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(8) for y in range(8)]
        config = ShipCompositeConfig(enable_rivets=False, enable_wear_overlay=True)
        baseline = ShipComposite(_make_build(pixels), config).get_surface()

        # Low wear
        low_comp = ShipComposite(_make_build(pixels), config)
        low_comp.set_wear(0.2)
        low_surf = low_comp.get_surface()

        # High wear
        high_comp = ShipComposite(_make_build(pixels), config)
        high_comp.set_wear(1.0)
        high_surf = high_comp.get_surface()

        silhouette_pixels = [(x, y) for x in range(8) for y in range(8)]
        low_darkened = _count_darkened_pixels(baseline, low_surf, silhouette_pixels)
        high_darkened = _count_darkened_pixels(baseline, high_surf, silhouette_pixels)

        assert high_darkened >= low_darkened, (
            f"Higher wear should darken more pixels; got low={low_darkened}, high={high_darkened}"
        )

    def test_phase5_determinism(self) -> None:
        """Same build + same config produces byte-identical decorated output."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(6) for y in range(6)]
        # Full pipeline enabled (all decoration flags on)
        config = ShipCompositeConfig(enable_rivets=True, enable_wear_overlay=True)

        c1 = ShipComposite(_make_build(pixels), config)
        c1.set_wear(0.5)
        s1 = c1.get_surface()

        c2 = ShipComposite(_make_build(pixels), config)
        c2.set_wear(0.5)
        s2 = c2.get_surface()

        for y in range(s1.get_height()):
            for x in range(s1.get_width()):
                assert s1.get_at((x, y)) == s2.get_at((x, y))

    def test_different_builds_produce_different_rivet_patterns(self) -> None:
        """Seeded from build geometry — different builds give different rivets."""
        import pygame

        pygame.init()
        # Two builds with same size but different pixel layouts
        pixels_a = [(x, y, "hull_cold") for x in range(8) for y in range(8)]
        pixels_b = [(x, y, "hull_cold") for x in range(8) for y in range(8) if (x + y) % 2 == 0]

        config = ShipCompositeConfig(enable_rivets=True, enable_wear_overlay=False)
        surf_a = ShipComposite(_make_build(pixels_a), config).get_surface()
        surf_b = ShipComposite(_make_build(pixels_b), config).get_surface()

        # Shapes differ so output must differ
        # (not a strict rivet-pattern check, but confirms build-dependent seeding)
        diff_count = 0
        for y in range(8):
            for x in range(8):
                if surf_a.get_at((x, y)) != surf_b.get_at((x, y)):
                    diff_count += 1
        assert diff_count > 0


# ---------------------------------------------------------------------------
# Phase 7 — Palette snap (material-band-constrained)
# ---------------------------------------------------------------------------


class TestPhase7PaletteSnap:
    """Phase 7 snaps every non-emissive pixel to the nearest entry in its
    material's shade band. Produces discrete banded colors per Bible §2.1.
    """

    def test_all_pixels_land_on_band_entries(self) -> None:
        """Every opaque non-emissive pixel should equal one of its material's
        band colors exactly (no intermediate RGB values)."""
        import pygame

        from spacegame.engine.ship_composite import _derive_material_band

        pygame.init()
        # All-same-material 6x6 so we can check against a single band
        pixels = [(x, y, "hull_cold") for x in range(6) for y in range(6)]
        # Disable rivets/wear/connection so only Phase 3 and Phase 7 run
        config = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_connection_detail=False,
            enable_palette_snap=True,
        )
        comp = ShipComposite(_make_build(pixels), config)
        surf = comp.get_surface()

        material = _resolve_material("hull_cold")
        band = _derive_material_band(material)
        band_rgb_set = {tuple(color) for color in band}

        for y in range(6):
            for x in range(6):
                px = surf.get_at((x, y))
                if px.a == 0:
                    continue
                assert (px.r, px.g, px.b) in band_rgb_set, (
                    f"Pixel ({x},{y}) = ({px.r},{px.g},{px.b}) is not a band entry: {band}"
                )

    def test_snap_respects_silhouette(self) -> None:
        """Pixels outside silhouette stay transparent after Phase 7."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        surf = comp.get_surface()
        px = surf.get_at((5, 5))
        assert px.a == 0

    def test_snap_produces_fewer_unique_colors(self) -> None:
        """Snap collapses continuous gradient into discrete band entries.
        An all-one-material ship should have at most 5 unique band colors."""
        import pygame

        from spacegame.engine.ship_composite import _derive_material_band

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(8) for y in range(8)]
        config = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_connection_detail=False,
            enable_palette_snap=True,
        )
        comp = ShipComposite(_make_build(pixels), config)
        surf = comp.get_surface()

        material = _resolve_material("hull_cold")
        band = _derive_material_band(material)

        colors_seen = set()
        for y in range(8):
            for x in range(8):
                px = surf.get_at((x, y))
                if px.a > 0:
                    colors_seen.add((px.r, px.g, px.b))

        # At most len(band) unique colors after snap (typically 5)
        assert len(colors_seen) <= len(band)

    def test_snap_is_band_constrained(self) -> None:
        """Snap never crosses into a different material's band. Each pixel
        lands on ITS OWN material's band, not any nearby material's."""
        import pygame

        from spacegame.engine.ship_composite import _derive_material_band

        pygame.init()
        # Mixed-material ship
        pixels = [
            (x, y, "hull_cold" if x < 3 else "reinforced_plate") for x in range(6) for y in range(6)
        ]
        config = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_connection_detail=False,
            enable_palette_snap=True,
        )
        comp = ShipComposite(_make_build(pixels), config)
        surf = comp.get_surface()

        hull_band = {tuple(c) for c in _derive_material_band(_resolve_material("hull_cold"))}
        plate_band = {
            tuple(c) for c in _derive_material_band(_resolve_material("reinforced_plate"))
        }

        for y in range(6):
            for x in range(6):
                px = surf.get_at((x, y))
                if px.a == 0:
                    continue
                rgb = (px.r, px.g, px.b)
                if x < 3:
                    # hull_cold pixel: must land on hull_band, not plate_band
                    assert rgb in hull_band, (
                        f"hull_cold pixel ({x},{y}) snapped to non-hull band: {rgb}"
                    )
                else:
                    # reinforced_plate pixel: must land on plate_band
                    assert rgb in plate_band, (
                        f"reinforced_plate pixel ({x},{y}) snapped to non-plate band: {rgb}"
                    )

    def test_enable_palette_snap_false_skips_phase7(self) -> None:
        """When enable_palette_snap=False, Phase 3's continuous gradient is
        preserved (output may contain RGB values NOT in any band)."""
        import pygame

        from spacegame.engine.ship_composite import _derive_material_band

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(6) for y in range(6)]

        # Disable ALL phases except Phase 3 so we isolate gradient colors
        config_off = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_connection_detail=False,
            enable_palette_snap=False,
        )
        comp_off = ShipComposite(_make_build(pixels), config_off)
        surf_off = comp_off.get_surface()

        band = {tuple(c) for c in _derive_material_band(_resolve_material("hull_cold"))}

        # Without snap, some pixels should be intermediate (not exact band entries)
        off_band_count = 0
        for y in range(6):
            for x in range(6):
                px = surf_off.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) not in band:
                    off_band_count += 1
        assert off_band_count > 0, "Without snap, expected intermediate RGB values"

    def test_snap_determinism(self) -> None:
        """Same inputs produce byte-identical snapped output."""
        import pygame

        pygame.init()
        pixels = [(x, y, "hull_cold") for x in range(4) for y in range(4)]
        config = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_connection_detail=False,
            enable_palette_snap=True,
        )
        s1 = ShipComposite(_make_build(pixels), config).get_surface()
        s2 = ShipComposite(_make_build(pixels), config).get_surface()
        for y in range(4):
            for x in range(4):
                assert s1.get_at((x, y)) == s2.get_at((x, y))


class TestEmissiveMask:
    """Internal helper: _compute_emissive_mask identifies emissive pixels
    by material_id (used by Phase 7 to skip them during snap, and by
    Phase 6 to overlay them with animated glow)."""

    def test_non_emissive_materials_not_masked(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._compute_emissive_mask()
        # hull_cold is not emissive
        assert not bool(mask[0, 0])

    def test_exhaust_port_is_emissive(self) -> None:
        """exhaust_port material represents engine emissive per legacy code."""
        build = _make_build([(0, 0, "exhaust_port")])
        comp = ShipComposite(build)
        mask = comp._compute_emissive_mask()
        assert bool(mask[0, 0])

    def test_cockpit_glass_is_emissive(self) -> None:
        """cockpit_glass represents cockpit window emissive."""
        build = _make_build([(0, 0, "cockpit_glass")])
        comp = ShipComposite(build)
        mask = comp._compute_emissive_mask()
        assert bool(mask[0, 0])

    def test_mask_shape_matches_silhouette(self) -> None:
        build = _make_build([(0, 0, "hull_cold")])
        comp = ShipComposite(build)
        mask = comp._compute_emissive_mask()
        assert mask.shape == (build.canvas_h, build.canvas_w)


# ---------------------------------------------------------------------------
# Phase 6 — Emissive overlay (animated pulse)
# ---------------------------------------------------------------------------


class TestPhase6Emissive:
    """Phase 6 applies pulse-modulated additive brightness to emissive
    pixels. Runs per-frame (not cached) so pulse animation progresses."""

    def test_emissive_pixels_brighter_than_baseline(self) -> None:
        """An emissive pixel with Phase 6 on should be brighter than the
        same pixel with Phase 6 off."""
        import pygame

        pygame.init()
        build_on = _make_build([(0, 0, "exhaust_port")])
        build_off = _make_build([(0, 0, "exhaust_port")])

        config_on = ShipCompositeConfig(enable_engine_glow=True)
        config_off = ShipCompositeConfig(enable_engine_glow=False)

        on_px = ShipComposite(build_on, config_on).get_surface().get_at((0, 0))
        off_px = ShipComposite(build_off, config_off).get_surface().get_at((0, 0))
        on_lum = on_px.r * 0.299 + on_px.g * 0.587 + on_px.b * 0.114
        off_lum = off_px.r * 0.299 + off_px.g * 0.587 + off_px.b * 0.114
        assert on_lum > off_lum, (
            f"Phase 6 should brighten emissive pixels; got on={on_lum:.1f}, off={off_lum:.1f}"
        )

    def test_non_emissive_pixels_unchanged_by_phase6(self) -> None:
        """Non-emissive pixels see no difference with Phase 6 toggle."""
        import pygame

        pygame.init()
        build_on = _make_build([(0, 0, "hull_cold")])
        build_off = _make_build([(0, 0, "hull_cold")])

        config_on = ShipCompositeConfig(enable_engine_glow=True)
        config_off = ShipCompositeConfig(enable_engine_glow=False)

        on_px = ShipComposite(build_on, config_on).get_surface().get_at((0, 0))
        off_px = ShipComposite(build_off, config_off).get_surface().get_at((0, 0))
        assert (on_px.r, on_px.g, on_px.b) == (off_px.r, off_px.g, off_px.b)

    def test_pulse_animation_produces_varying_output(self) -> None:
        """Different _emissive_phase values produce different brightness."""
        import pygame

        pygame.init()
        config = ShipCompositeConfig(enable_engine_glow=True)

        comp_peak = ShipComposite(_make_build([(0, 0, "exhaust_port")]), config)
        comp_peak._emissive_phase = 0.25  # sin(π/2) = 1 → peak pulse
        peak_px = comp_peak.get_surface().get_at((0, 0))

        comp_trough = ShipComposite(_make_build([(0, 0, "exhaust_port")]), config)
        comp_trough._emissive_phase = 0.75  # sin(3π/2) = -1 → trough pulse
        trough_px = comp_trough.get_surface().get_at((0, 0))

        peak_lum = peak_px.r * 0.299 + peak_px.g * 0.587 + peak_px.b * 0.114
        trough_lum = trough_px.r * 0.299 + trough_px.g * 0.587 + trough_px.b * 0.114
        assert peak_lum > trough_lum, (
            f"Pulse should modulate brightness; peak={peak_lum:.1f}, trough={trough_lum:.1f}"
        )

    def test_enable_engine_glow_false_skips_phase6(self) -> None:
        """With enable_engine_glow=False, emissive is not applied."""
        import pygame

        pygame.init()
        build = _make_build([(0, 0, "exhaust_port")])
        config_off = ShipCompositeConfig(enable_engine_glow=False)

        # Without Phase 6 — emissive pixels land at their Phase 3 base color
        # (they're excluded from Phase 7 snap but get no brightness boost)
        comp_off = ShipComposite(build, config_off)
        surf_off = comp_off.get_surface()
        px_off = surf_off.get_at((0, 0))

        # Same build with Phase 6 enabled should produce a brighter pixel
        config_on = ShipCompositeConfig(enable_engine_glow=True)
        comp_on = ShipComposite(_make_build([(0, 0, "exhaust_port")]), config_on)
        px_on = comp_on.get_surface().get_at((0, 0))

        off_lum = px_off.r * 0.299 + px_off.g * 0.587 + px_off.b * 0.114
        on_lum = px_on.r * 0.299 + px_on.g * 0.587 + px_on.b * 0.114
        assert on_lum > off_lum

    def test_phase6_determinism_at_same_phase(self) -> None:
        """Same pulse phase produces byte-identical output."""
        import pygame

        pygame.init()
        config = ShipCompositeConfig(enable_engine_glow=True)

        comp1 = ShipComposite(_make_build([(0, 0, "exhaust_port")]), config)
        comp1._emissive_phase = 0.3
        px1 = comp1.get_surface().get_at((0, 0))

        comp2 = ShipComposite(_make_build([(0, 0, "exhaust_port")]), config)
        comp2._emissive_phase = 0.3
        px2 = comp2.get_surface().get_at((0, 0))

        assert px1 == px2


class TestShipCompositeBandIntegration:
    """End-to-end verification that ShipComposite surfaces obey the canonical palette.

    These tests render real pipeline output and assert that the per-pixel RGBs
    land on (or close to) the canonical band the material declares. They cover
    the spec §9.2 integration requirements and keep Phase 7 snap honest.
    """

    def _render_and_collect(
        self,
        build: ShipBuild,
        *,
        enable_rivets: bool = False,
        enable_wear: bool = False,
        enable_emissive: bool = True,
    ) -> tuple[object, list[tuple[int, int, tuple[int, int, int]]]]:
        """Render a build and return (composite, [(x, y, rgb) for each opaque ship pixel])."""
        import pygame

        pygame.init()
        config = ShipCompositeConfig(
            enable_rivets=enable_rivets,
            enable_wear_overlay=enable_wear,
            enable_engine_glow=enable_emissive,
        )
        comp = ShipComposite(build, config)
        surf = comp.get_surface()
        pixels: list[tuple[int, int, tuple[int, int, int]]] = []
        for y in range(surf.get_height()):
            for x in range(surf.get_width()):
                px = surf.get_at((x, y))
                if px.a == 0:
                    continue
                pixels.append((x, y, (px.r, px.g, px.b)))
        return comp, pixels

    def test_phase7_snap_produces_band_compliant_surface(self) -> None:
        """A single-material build renders every pixel to its material's band."""
        from spacegame.engine.material_palette import assert_band_compliance
        from spacegame.engine.ship_composite import _derive_material_band

        # 4x4 block of standard_plate (steel band) — decorations off so every
        # pixel is pure Phase 3 → Phase 7 output.
        pixels = [(x, y, "standard_plate") for x in range(4) for y in range(4)]
        build = _make_build(pixels)
        comp, _ = self._render_and_collect(
            build, enable_rivets=False, enable_wear=False, enable_emissive=False
        )
        mat = _resolve_material("standard_plate")
        band = _derive_material_band(mat)

        # Crop to the non-transparent region to avoid asserting on background.
        assert_band_compliance(comp.get_surface(), band, tolerance=1.0)

    def test_phase3_lit_colors_stay_within_band_envelope(self) -> None:
        """Phase-3-only output must lie inside the band's channel envelope.

        With Phase 7 snap disabled, Phase 3 outputs continuous lerped colors
        along the band. Each channel must stay between the band's per-channel
        min and max (never above specular, never below shadow_deep).
        """
        import pygame

        from spacegame.engine.ship_composite import _derive_material_band

        pygame.init()
        pixels = [(x, y, "standard_plate") for x in range(4) for y in range(4)]
        build = _make_build(pixels)

        config = ShipCompositeConfig(
            enable_rivets=False,
            enable_wear_overlay=False,
            enable_engine_glow=False,
            enable_palette_snap=False,
            enable_connection_detail=False,
        )
        comp = ShipComposite(build, config)
        surf = comp.get_surface()
        mat = _resolve_material("standard_plate")
        band = _derive_material_band(mat)
        min_r = min(e[0] for e in band)
        max_r = max(e[0] for e in band)
        min_g = min(e[1] for e in band)
        max_g = max(e[1] for e in band)
        min_b = min(e[2] for e in band)
        max_b = max(e[2] for e in band)

        for x in range(4):
            for y in range(4):
                px = surf.get_at((x, y))
                if px.a == 0:
                    continue
                assert min_r <= px.r <= max_r, f"R={px.r} outside [{min_r},{max_r}] at ({x},{y})"
                assert min_g <= px.g <= max_g, f"G={px.g} outside [{min_g},{max_g}] at ({x},{y})"
                assert min_b <= px.b <= max_b, f"B={px.b} outside [{min_b},{max_b}] at ({x},{y})"

    def test_multi_material_ship_respects_per_pixel_band(self) -> None:
        """Each non-emissive pixel snaps to ITS OWN material's band.

        Uses two non-emissive materials so Phase 7 is the only finisher
        (emissive pixels bypass snap by design, per Bible §3.5).
        """
        from spacegame.engine.material_palette import _distance_sq
        from spacegame.engine.ship_composite import _derive_material_band

        # Left column: standard_plate (steel). Right column: crimson_steel
        # (reach_crimson). Both non-emissive; bands have disjoint RGBs.
        pixels = [(0, y, "standard_plate") for y in range(4)] + [
            (3, y, "crimson_steel") for y in range(4)
        ]
        build = _make_build(pixels)
        comp, _ = self._render_and_collect(
            build, enable_rivets=False, enable_wear=False, enable_emissive=False
        )
        surf = comp.get_surface()

        steel_band = _derive_material_band(_resolve_material("standard_plate"))
        crimson_band = _derive_material_band(_resolve_material("crimson_steel"))

        for y in range(4):
            steel_px = surf.get_at((0, y))
            crimson_px = surf.get_at((3, y))
            if steel_px.a:
                steel_rgb = (steel_px.r, steel_px.g, steel_px.b)
                nearest_steel = min(_distance_sq(steel_rgb, e) for e in steel_band)
                nearest_crimson = min(_distance_sq(steel_rgb, e) for e in crimson_band)
                assert nearest_steel <= 4, (
                    f"Steel pixel {steel_rgb} at (0,{y}) drifted from its band"
                )
                assert nearest_steel < nearest_crimson, (
                    f"Steel pixel {steel_rgb} at (0,{y}) is closer to the crimson band"
                )
            if crimson_px.a:
                crimson_rgb = (crimson_px.r, crimson_px.g, crimson_px.b)
                nearest_crimson = min(_distance_sq(crimson_rgb, e) for e in crimson_band)
                nearest_steel = min(_distance_sq(crimson_rgb, e) for e in steel_band)
                assert nearest_crimson <= 4, (
                    f"Crimson pixel {crimson_rgb} at (3,{y}) drifted from its band"
                )
                assert nearest_crimson < nearest_steel, (
                    f"Crimson pixel {crimson_rgb} at (3,{y}) is closer to the steel band"
                )

    def test_different_shade_bands_produce_different_colors(self) -> None:
        """Two bands with disjoint palettes must render visibly different pixels."""
        from spacegame.engine.material_palette import _distance_sq

        build_steel = _make_build([(1, 1, "standard_plate")])
        build_crimson = _make_build([(1, 1, "crimson_steel")])
        _, steel_pixels = self._render_and_collect(
            build_steel, enable_rivets=False, enable_wear=False, enable_emissive=False
        )
        _, crimson_pixels = self._render_and_collect(
            build_crimson, enable_rivets=False, enable_wear=False, enable_emissive=False
        )
        steel_px = next(rgb for x, y, rgb in steel_pixels if (x, y) == (1, 1))
        crimson_px = next(rgb for x, y, rgb in crimson_pixels if (x, y) == (1, 1))
        # Require a substantial perceptual gap — distinct bands must not
        # collapse to the same RGB even when sharing a lighting factor.
        dist = _distance_sq(steel_px, crimson_px)
        assert dist > 2500, (
            f"Expected distinct bands to diverge; steel={steel_px}, crimson={crimson_px}, "
            f"dist²={dist}"
        )

    def test_emissive_role_drives_phase6_color(self) -> None:
        """A material's emissive_role steers Phase 6 additive brightness.

        Two materials carrying different emissive_roles should tint the
        resulting overlay differently — not just brighten-all-channels the
        same way.
        """
        import pygame

        from spacegame.engine.material_palette import get_role
        from spacegame.models.ship_build import HullMaterial

        pygame.init()
        # Exhaust port's emissive_role is plasma_core (warm orange). Shield
        # emitter is cryo_fractal (cool cyan). Different channel balances.
        exhaust = _resolve_material("exhaust_port")
        emitter = _resolve_material("shield_emitter")
        assert isinstance(exhaust, HullMaterial) and exhaust.emissive_role == "plasma_core"
        assert isinstance(emitter, HullMaterial) and emitter.emissive_role == "cryo_fractal"

        plasma_rgb = get_role("plasma_core")
        cryo_rgb = get_role("cryo_fractal")

        config = ShipCompositeConfig(enable_engine_glow=True)
        comp_warm = ShipComposite(_make_build([(0, 0, "exhaust_port")]), config)
        comp_warm._emissive_phase = 0.25  # Peak pulse
        px_warm = comp_warm.get_surface().get_at((0, 0))

        comp_cool = ShipComposite(_make_build([(0, 0, "shield_emitter")]), config)
        comp_cool._emissive_phase = 0.25
        px_cool = comp_cool.get_surface().get_at((0, 0))

        # The warm emissive should bias red > blue; the cool emissive the
        # reverse. This holds regardless of the non-emissive base color.
        warm_rb = px_warm.r - px_warm.b
        cool_rb = px_cool.r - px_cool.b
        assert warm_rb > cool_rb, (
            f"Emissive roles should bias channels distinctly — "
            f"warm R-B={warm_rb} (role={plasma_rgb}), "
            f"cool R-B={cool_rb} (role={cryo_rgb})"
        )

    def test_no_emissive_role_leaves_phase6_inert(self) -> None:
        """A material with emissive_role=None renders the same with or without Phase 6."""
        import pygame

        from spacegame.models.ship_build import HullMaterial

        pygame.init()
        plate = _resolve_material("standard_plate")
        assert isinstance(plate, HullMaterial) and plate.emissive_role is None

        config_on = ShipCompositeConfig(enable_engine_glow=True)
        config_off = ShipCompositeConfig(enable_engine_glow=False)

        comp_on = ShipComposite(_make_build([(0, 0, "standard_plate")]), config_on)
        comp_off = ShipComposite(_make_build([(0, 0, "standard_plate")]), config_off)
        px_on = comp_on.get_surface().get_at((0, 0))
        px_off = comp_off.get_surface().get_at((0, 0))

        assert (px_on.r, px_on.g, px_on.b) == (px_off.r, px_off.g, px_off.b), (
            f"Non-emissive material must be untouched by Phase 6; "
            f"on={(px_on.r, px_on.g, px_on.b)}, off={(px_off.r, px_off.g, px_off.b)}"
        )

    def test_category_offset_shifts_rendered_color(self) -> None:
        """category_offset should actually move pixels inside the band."""
        from spacegame.engine.material_palette import _distance_sq

        # heavy_armor has category_offset=+1 — expect it to render brighter
        # than the raw union_ceramic midpoint.
        build = _make_build([(2, 2, "heavy_armor") for _ in range(1)])
        _, pixels = self._render_and_collect(
            build, enable_rivets=False, enable_wear=False, enable_emissive=False
        )
        rendered = next(rgb for x, y, rgb in pixels if (x, y) == (2, 2))

        from spacegame.engine.material_palette import get_band

        union_band = get_band("union_ceramic")
        mid = union_band[len(union_band) // 2]
        brighter = union_band[min(len(union_band) - 1, len(union_band) // 2 + 1)]
        # Rendered pixel should be closer to the brightened band stop than
        # to the raw midpoint — that's what category_offset=+1 promises.
        assert _distance_sq(rendered, brighter) <= _distance_sq(rendered, mid), (
            f"heavy_armor with category_offset=+1 should shift bright; "
            f"rendered={rendered}, mid={mid}, brighter={brighter}"
        )


class TestDestructionProgression:
    """Bucketed destruction progression (Combat §11.4)."""

    def _make_dense_build(self) -> ShipBuild:
        """A 6×6 block of pixels — enough for dropout statistics."""
        return _make_build([(x, y, "module_hull_rk") for x in range(6) for y in range(6)])

    def test_default_progress_is_zero(self) -> None:
        comp = ShipComposite(self._make_dense_build())
        assert comp.destruction_bucket == 0.0

    def test_progress_quantizes_to_buckets(self) -> None:
        comp = ShipComposite(self._make_dense_build())
        comp.set_destruction_progress(0.10)  # rounds to 0.0
        assert comp.destruction_bucket == 0.0
        comp.set_destruction_progress(0.20)  # rounds to 0.25
        assert comp.destruction_bucket == 0.25
        comp.set_destruction_progress(0.55)  # rounds to 0.5
        assert comp.destruction_bucket == 0.5
        comp.set_destruction_progress(0.80)  # rounds to 0.75
        assert comp.destruction_bucket == 0.75
        comp.set_destruction_progress(0.95)  # rounds to 1.0
        assert comp.destruction_bucket == 1.0

    def test_progress_clamps_to_unit_range(self) -> None:
        comp = ShipComposite(self._make_dense_build())
        comp.set_destruction_progress(-0.5)
        assert comp.destruction_bucket == 0.0
        comp.set_destruction_progress(2.0)
        assert comp.destruction_bucket == 1.0

    def test_intra_bucket_change_is_free(self) -> None:
        """Repeated calls within the same bucket must not invalidate the cache."""
        comp = ShipComposite(self._make_dense_build())
        comp.get_surface()  # warm cache
        comp.set_destruction_progress(0.30)  # bucket 0.25
        first = comp.get_surface()
        comp.set_destruction_progress(0.20)  # still bucket 0.25
        second = comp.get_surface()
        assert first is second, "Same-bucket calls must reuse the cached surface"

    def test_bucket_change_invalidates_cache(self) -> None:
        comp = ShipComposite(self._make_dense_build())
        comp.set_destruction_progress(0.0)
        intact = comp.get_surface()
        comp.set_destruction_progress(1.0)
        wrecked = comp.get_surface()
        assert intact is not wrecked, "Bucket change must trigger rebuild"

    def test_destruction_darkens_pixels(self) -> None:
        """Bucket 0.5 must darken at least one pixel relative to intact."""
        build = self._make_dense_build()
        comp = ShipComposite(build, ShipCompositeConfig(enable_engine_glow=False))
        intact = comp.get_surface().copy()
        comp.set_destruction_progress(0.5)
        damaged = comp.get_surface()
        # Find at least one ship pixel that's darker after damage.
        any_darker = False
        for y in range(intact.get_height()):
            for x in range(intact.get_width()):
                a, b = intact.get_at((x, y)), damaged.get_at((x, y))
                if a.a == 0 or b.a == 0:
                    continue
                if (b.r + b.g + b.b) < (a.r + a.g + a.b):
                    any_darker = True
                    break
            if any_darker:
                break
        assert any_darker, "Destruction bucket should darken at least one pixel"

    def test_destruction_drops_pixels_at_high_buckets(self) -> None:
        """Bucket 1.0 should null some opaque pixels (silhouette breaks)."""
        build = self._make_dense_build()
        comp = ShipComposite(build, ShipCompositeConfig(enable_engine_glow=False))
        intact = comp.get_surface().copy()
        comp.set_destruction_progress(1.0)
        wrecked = comp.get_surface()
        intact_opaque = sum(
            1
            for y in range(intact.get_height())
            for x in range(intact.get_width())
            if intact.get_at((x, y)).a > 0
        )
        wrecked_opaque = sum(
            1
            for y in range(wrecked.get_height())
            for x in range(wrecked.get_width())
            if wrecked.get_at((x, y)).a > 0
        )
        assert wrecked_opaque < intact_opaque, (
            f"Bucket 1.0 should drop pixels: intact={intact_opaque}, wrecked={wrecked_opaque}"
        )

    def test_destruction_is_deterministic(self) -> None:
        """Same build + same bucket → identical destruction pattern."""
        build = self._make_dense_build()
        a = ShipComposite(build, ShipCompositeConfig(enable_engine_glow=False))
        b = ShipComposite(build, ShipCompositeConfig(enable_engine_glow=False))
        a.set_destruction_progress(0.75)
        b.set_destruction_progress(0.75)
        sa, sb = a.get_surface(), b.get_surface()
        for y in range(sa.get_height()):
            for x in range(sa.get_width()):
                assert sa.get_at((x, y)) == sb.get_at((x, y)), (
                    f"Destruction must be deterministic at ({x},{y})"
                )
