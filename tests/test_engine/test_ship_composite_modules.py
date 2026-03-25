"""Tests for Phase 3 — ShipComposite rendering with module pixels.

Covers module pixel integration into the pixel map, module material
texture rendering, manufacturer color variant rendering, engine glow
on exhaust_port pixels, and frame variant canvas sizing.
"""

import pytest
import os

pygame = pytest.importorskip("pygame")

# Initialize pygame display for surface operations (convert_alpha, etc.)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from spacegame.engine.ship_composite import ShipComposite


def _ensure_display() -> None:
    """Ensure pygame display is initialized for surface operations."""
    if not pygame.get_init():
        pygame.init()
    try:
        pygame.display.get_surface()
    except Exception:
        pass
    pygame.display.set_mode((1, 1))


from spacegame.models.ship_build import (
    HullMaterial,
    PlacedPixel,
    ShipBuild,
)
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
)


# ============================================================================
# Helpers
# ============================================================================


def _module_hull_mat(mat_id: str = "module_hull_rk") -> HullMaterial:
    return HullMaterial(
        id=mat_id,
        name="RK Hull",
        description="",
        color_primary=(176, 196, 222),
        color_highlight=(200, 220, 240),
    )


def _cockpit_glass_mat() -> HullMaterial:
    return HullMaterial(
        id="cockpit_glass",
        name="Glass",
        description="",
        color_primary=(100, 160, 220),
        color_highlight=(140, 200, 255),
    )


def _exhaust_mat() -> HullMaterial:
    return HullMaterial(
        id="exhaust_port",
        name="Exhaust",
        description="",
        color_primary=(60, 45, 30),
        color_highlight=(200, 140, 50),
    )


def _weapon_barrel_mat() -> HullMaterial:
    return HullMaterial(
        id="weapon_barrel",
        name="Barrel",
        description="",
        color_primary=(55, 55, 65),
        color_highlight=(90, 90, 110),
    )


def _shield_emitter_mat() -> HullMaterial:
    return HullMaterial(
        id="shield_emitter",
        name="Emitter",
        description="",
        color_primary=(60, 200, 230),
        color_highlight=(120, 240, 255),
    )


def _console_panel_mat() -> HullMaterial:
    return HullMaterial(
        id="console_panel",
        name="Console",
        description="",
        color_primary=(50, 80, 60),
        color_highlight=(80, 140, 90),
    )


def _cargo_interior_mat() -> HullMaterial:
    return HullMaterial(
        id="cargo_interior",
        name="Cargo",
        description="",
        color_primary=(70, 65, 55),
        color_highlight=(95, 90, 75),
    )


def _reactor_core_mat() -> HullMaterial:
    return HullMaterial(
        id="reactor_core",
        name="Reactor",
        description="",
        color_primary=(120, 60, 160),
        color_highlight=(170, 100, 220),
    )


def _sensor_dish_mat() -> HullMaterial:
    return HullMaterial(
        id="sensor_dish",
        name="Sensor",
        description="",
        color_primary=(190, 200, 210),
        color_highlight=(230, 240, 255),
    )


def _crew_quarters_mat() -> HullMaterial:
    return HullMaterial(
        id="crew_quarters_interior",
        name="Quarters",
        description="",
        color_primary=(80, 100, 75),
        color_highlight=(110, 135, 100),
    )


def _foundry_hull_mat() -> HullMaterial:
    return HullMaterial(
        id="module_hull_foundry",
        name="Foundry Hull",
        description="",
        color_primary=(160, 130, 80),
        color_highlight=(190, 160, 110),
    )


def _standard_plate_mat() -> HullMaterial:
    return HullMaterial(
        id="standard_plate",
        name="Standard Plate",
        description="",
        color_primary=(112, 120, 136),
        color_highlight=(150, 160, 180),
        hull_per_pixel=2.5,
        weight_per_pixel=0.25,
    )


def _all_materials() -> dict[str, HullMaterial]:
    mats = {}
    for m in [
        _module_hull_mat(),
        _cockpit_glass_mat(),
        _exhaust_mat(),
        _weapon_barrel_mat(),
        _shield_emitter_mat(),
        _console_panel_mat(),
        _cargo_interior_mat(),
        _reactor_core_mat(),
        _sensor_dish_mat(),
        _crew_quarters_mat(),
        _foundry_hull_mat(),
        _standard_plate_mat(),
    ]:
        mats[m.id] = m
    return mats


def _cockpit_module() -> ShipModule:
    return ShipModule(
        id="scout_pod_rk",
        name="Scout Pod",
        description="",
        category="cockpit",
        manufacturer="reyes_kowalski",
        pixel_grid=[[".", "H", "."], ["H", "G", "H"], ["H", "H", "H"]],
        material_map={"H": "module_hull_rk", "G": "cockpit_glass"},
        provides={},
        weight=3.0,
        base_cost=2000,
    )


def _engine_module() -> ShipModule:
    return ShipModule(
        id="light_thruster_rk",
        name="Light Thruster",
        description="",
        category="engine",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "E", "H"], ["H", "E", "H"]],
        material_map={"H": "module_hull_rk", "E": "exhaust_port"},
        provides={},
        weight=2.5,
        base_cost=1500,
    )


def _foundry_module() -> ShipModule:
    return ShipModule(
        id="bulkhead_foundry",
        name="Foundry Bulkhead",
        description="",
        category="structural",
        manufacturer="foundry",
        pixel_grid=[["H", "H", "H", "H"], ["H", "H", "H", "H"]],
        material_map={"H": "module_hull_foundry"},
        provides={},
        weight=4.0,
        base_cost=1500,
    )


def _module_catalog() -> dict[str, ShipModule]:
    return {
        m.id: m
        for m in [
            _cockpit_module(),
            _engine_module(),
            _foundry_module(),
        ]
    }


# ============================================================================
# Pixel Map Integration
# ============================================================================


class TestCompositePixelMap:
    """Test that module pixels are included in the rendering pixel map."""

    def test_module_pixels_in_pixel_map(self) -> None:
        """Module pixels should appear in the composite's pixel map."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="scout_pod_rk", x=5, y=5)]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        # Cockpit: .H. / HGH / HHH at (5,5)
        # (6,5) = H, (5,6)=H, (6,6)=G, (7,6)=H, ...
        assert (6, 5) in comp._pixel_map, "Module hull pixel should be in pixel map"
        assert comp._pixel_map[(6, 6)] == "cockpit_glass", (
            "Glass pixel should have correct material"
        )

    def test_hull_pixels_in_pixel_map(self) -> None:
        """Hull pixels should still appear alongside module pixels."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="scout_pod_rk", x=5, y=5)]
        build.pixels = [PlacedPixel(x=0, y=0, material_id="standard_plate")]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        assert (0, 0) in comp._pixel_map, "Hull pixel should be in pixel map"
        assert comp._pixel_map[(0, 0)] == "standard_plate"

    def test_backward_compat_no_module_catalog(self) -> None:
        """Without module_catalog, only hull pixels in pixel map."""
        materials = _all_materials()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=0, y=0, material_id="standard_plate")]

        comp = ShipComposite(build, materials)
        assert (0, 0) in comp._pixel_map

    def test_invalidate_rebuilds_with_modules(self) -> None:
        """invalidate() should rebuild pixel map including modules."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="scout_pod_rk", x=5, y=5)]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        assert (6, 5) in comp._pixel_map

        # Add another module
        build.modules.append(PlacedModule(module_id="light_thruster_rk", x=0, y=0))
        comp.invalidate()
        assert (1, 0) in comp._pixel_map, "New module should appear after invalidate"


# ============================================================================
# Rendering Pipeline with Modules
# ============================================================================


class TestCompositeRenderingWithModules:
    """Test that the rendering pipeline works with module pixels."""

    def setup_method(self) -> None:
        _ensure_display()

    def test_renders_without_error(self) -> None:
        """Full pipeline should complete without errors on a module build."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=5, y=5),
            PlacedModule(module_id="light_thruster_rk", x=5, y=8),
        ]
        build.pixels = [PlacedPixel(x=4, y=6, material_id="standard_plate")]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        surf = comp.get_surface(scale=1)
        assert surf is not None
        assert surf.get_width() == 16
        assert surf.get_height() == 16

    def test_module_material_colors_rendered(self) -> None:
        """Module pixels should render with their material's color."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="scout_pod_rk", x=5, y=5)]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        surf = comp.get_surface(scale=1)

        # Glass pixel at (6,6) should have blue-ish color (cockpit_glass primary is 100,160,220)
        # After pipeline steps it may be modified, but alpha should be 255 (not transparent)
        color = surf.get_at((6, 6))
        assert color.a == 255, f"Glass pixel should be opaque, got alpha={color.a}"
        # Blue channel should be dominant for glass
        assert color.b > color.r, "Cockpit glass should have blue > red"

    def test_manufacturer_hull_color_rendered(self) -> None:
        """Foundry hull should render with its distinctive brown/orange color."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="bulkhead_foundry", x=0, y=0)]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        surf = comp.get_surface(scale=1)

        # Foundry hull primary is (160, 130, 80) — warm brown
        # Check an interior pixel (1,0) which should be relatively unmodified
        color = surf.get_at((1, 0))
        assert color.a == 255
        # Foundry color should be warm (red > blue)
        assert color.r > color.b, (
            f"Foundry hull should be warm (r>b), got ({color.r},{color.g},{color.b})"
        )

    def test_scaled_rendering(self) -> None:
        """Scaled rendering should work with modules."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="scout_pod_rk", x=5, y=5)]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        surf4x = comp.get_surface(scale=4)
        assert surf4x.get_width() == 64
        assert surf4x.get_height() == 64


# ============================================================================
# Frame Variant Canvas Size
# ============================================================================


class TestCompositeFrameVariants:
    """Test that frame variants produce correct canvas dimensions."""

    def setup_method(self) -> None:
        _ensure_display()

    def test_default_medium_canvas(self) -> None:
        materials = _all_materials()
        build = ShipBuild(weight_class="medium")
        comp = ShipComposite(build, materials)
        surf = comp.get_surface(scale=1)
        assert surf.get_width() == 40
        assert surf.get_height() == 28

    def test_wide_medium_canvas(self) -> None:
        materials = _all_materials()
        build = ShipBuild(weight_class="medium", frame_variant="wide")
        comp = ShipComposite(build, materials)
        surf = comp.get_surface(scale=1)
        assert surf.get_width() == 48
        assert surf.get_height() == 24

    def test_tall_medium_canvas(self) -> None:
        materials = _all_materials()
        build = ShipBuild(weight_class="medium", frame_variant="tall")
        comp = ShipComposite(build, materials)
        surf = comp.get_surface(scale=1)
        assert surf.get_width() == 28
        assert surf.get_height() == 40


# ============================================================================
# Engine Glow on Exhaust Pixels
# ============================================================================


class TestCompositeEngineGlow:
    """Test engine glow applies to exhaust_port pixels from modules."""

    def setup_method(self) -> None:
        _ensure_display()

    def test_exhaust_pixels_get_glow(self) -> None:
        """Exhaust port pixels should receive warm glow coloring."""
        materials = _all_materials()
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        # Engine at (0,0): HEH / HEH — exhaust at (1,0) and (1,1)
        build.modules = [PlacedModule(module_id="light_thruster_rk", x=0, y=0)]

        comp = ShipComposite(build, materials, module_catalog=catalog)
        surf = comp.get_surface(scale=1)

        # Exhaust pixels (1,0) and (1,1) should have warm glow
        # Exhaust base color is (60,45,30) but glow overrides with warm orange
        ex_color = surf.get_at((1, 0))
        # The glow should make it warmer (red channel higher than base)
        assert ex_color.r > 60, f"Exhaust pixel should have glow (r > base 60), got r={ex_color.r}"


# ============================================================================
# Material Texture Rules for Module Materials
# ============================================================================


class TestCompositeModuleMaterialTextures:
    """Test that module-specific materials get their texture patterns."""

    def setup_method(self) -> None:
        _ensure_display()

    def _render_single_material(
        self,
        mat_id: str,
        grid_size: int = 6,
    ) -> pygame.Surface:
        """Helper: render a build filled with a single module material."""
        materials = _all_materials()
        build = ShipBuild(weight_class="tiny")
        for x in range(grid_size):
            for y in range(grid_size):
                build.pixels.append(PlacedPixel(x=x, y=y, material_id=mat_id))
        comp = ShipComposite(build, materials)
        return comp.get_surface(scale=1)

    def test_shield_emitter_shimmer(self) -> None:
        """Shield emitter should have shimmer pattern (like shield_crystal)."""
        surf = self._render_single_material("shield_emitter")
        # Even and odd rows should have different brightness
        even_row = surf.get_at((3, 2))  # y=2, even
        odd_row = surf.get_at((3, 3))  # y=3, odd
        # Even row should be brighter (shimmer effect)
        assert even_row.g >= odd_row.g or even_row.b >= odd_row.b, (
            "Shield emitter even rows should be brighter (shimmer)"
        )

    def test_cargo_interior_grid(self) -> None:
        """Cargo interior should have subtle grid pattern."""
        surf = self._render_single_material("cargo_interior")
        # Some pixels should be darker than others due to grid pattern
        colors = set()
        for x in range(1, 5):
            for y in range(1, 5):
                c = surf.get_at((x, y))
                colors.add((c.r, c.g, c.b))
        # Should have at least 2 distinct colors from the pattern
        assert len(colors) >= 2, "Cargo interior should have grid pattern variation"

    def test_reactor_core_pulse(self) -> None:
        """Reactor core should have pulse pattern."""
        surf = self._render_single_material("reactor_core")
        colors = set()
        for x in range(1, 5):
            for y in range(1, 5):
                c = surf.get_at((x, y))
                colors.add((c.r, c.g, c.b))
        assert len(colors) >= 2, "Reactor core should have pulse pattern variation"

    def test_foundry_hull_rivet_pattern(self) -> None:
        """Foundry hull should have rivet pattern like heavy_armor."""
        surf = self._render_single_material("module_hull_foundry")
        colors = set()
        for x in range(1, 5):
            for y in range(1, 5):
                c = surf.get_at((x, y))
                colors.add((c.r, c.g, c.b))
        assert len(colors) >= 2, "Foundry hull should have rivet pattern variation"
