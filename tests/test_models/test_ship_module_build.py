"""Tests for Phase 2 — ShipBuild integration with modules.

Covers ShipBuild with modules field, frame variants, resolve_all_pixels,
module placement validation, connectivity, requirements validation,
and stats computation with module contributions.
"""

from spacegame.models.ship_build import (
    HullMaterial,
    PlacedPixel,
    ShipBuild,
    ShipStatsComputer,
    WEIGHT_CLASSES,
)
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    resolve_placed_module,
    resolve_all_pixels,
    can_place_module,
    validate_connectivity,
    validate_requirements,
)
from spacegame.models.ship_build import FRAME_VARIANTS


# ============================================================================
# Helpers
# ============================================================================


def _mat_standard() -> HullMaterial:
    return HullMaterial(
        id="standard_plate",
        name="Standard Plate",
        description="Balanced",
        color_primary=(112, 120, 136),
        hull_per_pixel=2.5,
        weight_per_pixel=0.25,
        cost_per_pixel=15,
    )


def _mat_light() -> HullMaterial:
    return HullMaterial(
        id="light_alloy",
        name="Light Alloy",
        description="Light",
        color_primary=(176, 184, 200),
        hull_per_pixel=1.5,
        evasion_per_pixel=0.08,
        weight_per_pixel=0.15,
        cost_per_pixel=8,
    )


def _module_hull_mat() -> HullMaterial:
    """Module hull material (zero combat stats, purely visual)."""
    return HullMaterial(
        id="module_hull_rk",
        name="RK Hull",
        description="Visual only",
        color_primary=(176, 196, 222),
    )


def _materials_catalog() -> dict[str, HullMaterial]:
    return {
        "standard_plate": _mat_standard(),
        "light_alloy": _mat_light(),
        "module_hull_rk": _module_hull_mat(),
        "cockpit_glass": HullMaterial(
            id="cockpit_glass",
            name="Glass",
            description="",
            color_primary=(100, 160, 220),
        ),
        "exhaust_port": HullMaterial(
            id="exhaust_port",
            name="Exhaust",
            description="",
            color_primary=(60, 45, 30),
        ),
        "weapon_barrel": HullMaterial(
            id="weapon_barrel",
            name="Barrel",
            description="",
            color_primary=(55, 55, 65),
        ),
        "shield_emitter": HullMaterial(
            id="shield_emitter",
            name="Emitter",
            description="",
            color_primary=(60, 200, 230),
        ),
        "cargo_interior": HullMaterial(
            id="cargo_interior",
            name="Cargo",
            description="",
            color_primary=(70, 65, 55),
        ),
    }


def _cockpit() -> ShipModule:
    return ShipModule(
        id="scout_pod_rk",
        name="Scout Pod",
        description="",
        category="cockpit",
        manufacturer="reyes_kowalski",
        pixel_grid=[[".", "H", "."], ["H", "G", "H"], ["H", "H", "H"]],
        material_map={"H": "module_hull_rk", "G": "cockpit_glass"},
        provides={"slot_type": "core", "crew_capacity": 1},
        weight=3.0,
        base_cost=2000,
    )


def _engine() -> ShipModule:
    return ShipModule(
        id="light_thruster_rk",
        name="Light Thruster",
        description="",
        category="engine",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "E", "H"], ["H", "E", "H"]],
        material_map={"H": "module_hull_rk", "E": "exhaust_port"},
        provides={"slot_type": "engine", "thrust": 8, "fuel_efficiency": 1.0},
        weight=2.5,
        base_cost=1500,
    )


def _weapon() -> ShipModule:
    return ShipModule(
        id="light_hardpoint_rk",
        name="Light Hardpoint",
        description="",
        category="weapon",
        manufacturer="reyes_kowalski",
        pixel_grid=[["W", "H"], ["H", "H"]],
        material_map={"H": "module_hull_rk", "W": "weapon_barrel"},
        provides={"slot_type": "weapon", "weapon_size": "small"},
        weight=1.5,
        base_cost=1500,
    )


def _shield() -> ShipModule:
    return ShipModule(
        id="basic_emitter_rk",
        name="Basic Emitter",
        description="",
        category="shield",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "S"], ["S", "H"]],
        material_map={"H": "module_hull_rk", "S": "shield_emitter"},
        provides={"slot_type": "defense", "shield_hp": 30, "shield_regen": 1},
        weight=1.5,
        base_cost=1500,
    )


def _cargo() -> ShipModule:
    return ShipModule(
        id="small_hold_rk",
        name="Small Hold",
        description="",
        category="cargo",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H", "H"], ["H", "C", "H"]],
        material_map={"H": "module_hull_rk", "C": "cargo_interior"},
        provides={"cargo_capacity": 15},
        weight=2.0,
        base_cost=1000,
    )


def _crew() -> ShipModule:
    return ShipModule(
        id="standard_quarters_rk",
        name="Standard Quarters",
        description="",
        category="crew",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H", "H"], ["H", "Q", "H"], ["H", "H", "H"]],
        material_map={"H": "module_hull_rk", "Q": "module_hull_rk"},
        provides={"crew_capacity": 2},
        weight=3.5,
        base_cost=3000,
    )


def _reactor() -> ShipModule:
    return ShipModule(
        id="compact_reactor_rk",
        name="Compact Reactor",
        description="",
        category="reactor",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H", "H"], ["H", "R", "H"], ["H", "H", "H"]],
        material_map={"H": "module_hull_rk", "R": "module_hull_rk"},
        provides={"power_output": 10},
        weight=4.0,
        base_cost=5000,
    )


def _structural_2x2() -> ShipModule:
    return ShipModule(
        id="hull_connector_2x2",
        name="Connector",
        description="",
        category="structural",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"], ["H", "H"]],
        material_map={"H": "module_hull_rk"},
        provides={},
        weight=1.0,
        base_cost=300,
    )


def _module_catalog() -> dict[str, ShipModule]:
    return {
        m.id: m
        for m in [
            _cockpit(),
            _engine(),
            _weapon(),
            _shield(),
            _cargo(),
            _crew(),
            _reactor(),
            _structural_2x2(),
        ]
    }


def _valid_tiny_build() -> tuple[ShipBuild, dict[str, ShipModule]]:
    """Create a minimal valid tiny build with all mandatory modules placed adjacently."""
    catalog = _module_catalog()
    build = ShipBuild(weight_class="tiny")
    # Place modules in a connected cluster on a 16x16 canvas.
    # Engine must be in rear 30% (x < ~5 for 16-wide canvas, stern = left).
    # Engine at (0, 5) — 3×2, extends to x=2 (well within rear)
    # Cockpit at (3, 5) — 3×3 (right of engine, touching at x=3)
    # Weapon at (6, 5) — 2×2 (right of cockpit, touching at x=6)
    # Shield at (3, 8) — 2×2 (below cockpit, touching at y=8)
    # Cargo at (5, 8) — 3×2 (right of shield, touching)
    build.modules = [
        PlacedModule(module_id="light_thruster_rk", x=0, y=5),
        PlacedModule(module_id="scout_pod_rk", x=3, y=5),
        PlacedModule(module_id="light_hardpoint_rk", x=6, y=5),
        PlacedModule(module_id="basic_emitter_rk", x=3, y=8),
        PlacedModule(module_id="small_hold_rk", x=5, y=8),
    ]
    return build, catalog


# ============================================================================
# ShipBuild — Modules Field
# ============================================================================


class TestShipBuildModulesField:
    """Test ShipBuild with the new modules field."""

    def test_build_defaults_empty_modules(self) -> None:
        build = ShipBuild(weight_class="medium")
        assert build.modules == []

    def test_build_with_modules(self) -> None:
        build = ShipBuild(weight_class="medium")
        build.modules.append(PlacedModule(module_id="test", x=0, y=0))
        assert len(build.modules) == 1

    def test_build_defaults_no_frame_variant(self) -> None:
        build = ShipBuild(weight_class="medium")
        assert build.frame_variant is None


# ============================================================================
# Frame Variants
# ============================================================================


class TestFrameVariants:
    """Test canvas dimensions with frame variants."""

    def test_default_dimensions_unchanged(self) -> None:
        """No frame variant = existing WEIGHT_CLASSES dimensions."""
        build = ShipBuild(weight_class="medium")
        assert build.canvas_w == 40
        assert build.canvas_h == 28

    def test_medium_wide(self) -> None:
        build = ShipBuild(weight_class="medium", frame_variant="wide")
        w, h = FRAME_VARIANTS["medium"]["wide"]
        assert build.canvas_w == w
        assert build.canvas_h == h
        assert build.canvas_w > build.canvas_h, "Wide should be wider than tall"

    def test_medium_tall(self) -> None:
        build = ShipBuild(weight_class="medium", frame_variant="tall")
        w, h = FRAME_VARIANTS["medium"]["tall"]
        assert build.canvas_w == w
        assert build.canvas_h == h
        assert build.canvas_h > build.canvas_w, "Tall should be taller than wide"

    def test_large_wide(self) -> None:
        build = ShipBuild(weight_class="large", frame_variant="wide")
        w, h = FRAME_VARIANTS["large"]["wide"]
        assert build.canvas_w == w
        assert build.canvas_h == h

    def test_tiny_ignores_frame_variant(self) -> None:
        """Tiny and small don't have frame variants."""
        build = ShipBuild(weight_class="tiny", frame_variant="wide")
        # Should fall back to default dimensions
        assert build.canvas_w == WEIGHT_CLASSES["tiny"]["canvas_w"]
        assert build.canvas_h == WEIGHT_CLASSES["tiny"]["canvas_h"]

    def test_frame_variants_same_area(self) -> None:
        """All frame variants should have roughly the same pixel area."""
        for wc, variants in FRAME_VARIANTS.items():
            default_area = WEIGHT_CLASSES[wc]["canvas_w"] * WEIGHT_CLASSES[wc]["canvas_h"]
            for variant_name, (w, h) in variants.items():
                variant_area = w * h
                ratio = variant_area / default_area
                assert 0.90 <= ratio <= 1.10, (
                    f"{wc}/{variant_name}: area {variant_area} vs default {default_area} "
                    f"(ratio {ratio:.2f}) differs by more than 10%"
                )


# ============================================================================
# Serialization — Backward Compatibility
# ============================================================================


class TestShipBuildSerialization:
    """Test ShipBuild serialization with modules and frame variants."""

    def test_to_dict_includes_modules(self) -> None:
        build = ShipBuild(weight_class="medium")
        build.modules = [PlacedModule(module_id="test", x=5, y=3)]
        d = build.to_dict()
        assert "modules" in d
        assert len(d["modules"]) == 1
        assert d["modules"][0]["module_id"] == "test"

    def test_to_dict_includes_frame_variant(self) -> None:
        build = ShipBuild(weight_class="medium", frame_variant="wide")
        d = build.to_dict()
        assert d["frame_variant"] == "wide"

    def test_from_dict_with_modules_round_trip(self) -> None:
        build = ShipBuild(weight_class="medium", frame_variant="tall")
        build.modules = [
            PlacedModule(module_id="cockpit", x=5, y=3, rotation=1, flipped=True),
            PlacedModule(module_id="engine", x=10, y=8),
        ]
        build.pixels = [PlacedPixel(x=1, y=1, material_id="standard_plate")]
        d = build.to_dict()
        restored = ShipBuild.from_dict(d)
        assert restored.weight_class == "medium"
        assert restored.frame_variant == "tall"
        assert len(restored.modules) == 2
        assert restored.modules[0].module_id == "cockpit"
        assert restored.modules[0].rotation == 1
        assert restored.modules[0].flipped is True
        assert len(restored.pixels) == 1

    def test_from_dict_backward_compat_no_modules(self) -> None:
        """Old saves without modules field should load with empty modules list."""
        d = {"weight_class": "medium", "pixels": [], "slots": []}
        build = ShipBuild.from_dict(d)
        assert build.modules == []
        assert build.frame_variant is None

    def test_from_dict_backward_compat_full_old_save(self) -> None:
        """A complete old-format save should load without errors."""
        d = {
            "weight_class": "small",
            "pixels": [{"x": 0, "y": 0, "material_id": "standard_plate"}],
            "slots": [{"slot_type": "weapon", "x": 0, "y": 0}],
            "preset_name": "Old Ship",
        }
        build = ShipBuild.from_dict(d)
        assert build.weight_class == "small"
        assert len(build.pixels) == 1
        assert len(build.slots) == 1
        assert build.modules == []
        assert build.preset_name == "Old Ship"


# ============================================================================
# resolve_all_pixels
# ============================================================================


class TestResolveAllPixels:
    """Test flattening modules + hull pixels into one pixel list."""

    def test_modules_only(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="light_hardpoint_rk", x=0, y=0)]
        pixels = resolve_all_pixels(build, catalog)
        assert len(pixels) == 4  # 2x2 weapon, all filled

    def test_hull_pixels_only(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [
            PlacedPixel(x=0, y=0, material_id="standard_plate"),
            PlacedPixel(x=1, y=0, material_id="standard_plate"),
        ]
        pixels = resolve_all_pixels(build, catalog)
        assert len(pixels) == 2

    def test_mixed_modules_and_hull(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="light_hardpoint_rk", x=0, y=0)]
        build.pixels = [PlacedPixel(x=5, y=5, material_id="standard_plate")]
        pixels = resolve_all_pixels(build, catalog)
        assert len(pixels) == 5  # 4 from module + 1 hull pixel

    def test_module_rotation_reflected(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        # Engine is 3w x 2h; rotated 90° becomes 2w x 3h
        build.modules = [
            PlacedModule(module_id="light_thruster_rk", x=0, y=0, rotation=1),
        ]
        pixels = resolve_all_pixels(build, catalog)
        assert len(pixels) == 6
        xs = {p.x for p in pixels}
        ys = {p.y for p in pixels}
        assert max(xs) == 1, "Rotated engine should be 2 wide"
        assert max(ys) == 2, "Rotated engine should be 3 tall"


# ============================================================================
# can_place_module
# ============================================================================


class TestCanPlaceModule:
    """Test module placement validation."""

    def test_valid_placement(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")  # 16x16, 55 max weight
        pm = PlacedModule(module_id="light_hardpoint_rk", x=5, y=5)
        ok, msg = can_place_module(build, pm, catalog, materials)
        assert ok, f"Valid placement should succeed: {msg}"

    def test_out_of_bounds(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")  # 16x16
        # Weapon is 2x2, placing at x=15 means it extends to x=16 (out of bounds)
        pm = PlacedModule(module_id="light_hardpoint_rk", x=15, y=5)
        ok, msg = can_place_module(build, pm, catalog, materials)
        assert not ok, "Should reject out-of-bounds placement"
        assert "beyond" in msg.lower() or "bounds" in msg.lower()

    def test_out_of_bounds_negative(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        pm = PlacedModule(module_id="light_hardpoint_rk", x=-1, y=5)
        ok, msg = can_place_module(build, pm, catalog, materials)
        assert not ok

    def test_overlap_with_existing_module(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="light_hardpoint_rk", x=5, y=5)]
        # Try to place another module overlapping
        pm = PlacedModule(module_id="light_hardpoint_rk", x=6, y=5)
        ok, msg = can_place_module(build, pm, catalog, materials)
        assert not ok, "Should reject overlapping modules"
        assert "overlap" in msg.lower()

    def test_overlap_with_hull_pixel(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=5, y=5, material_id="standard_plate")]
        pm = PlacedModule(module_id="light_hardpoint_rk", x=5, y=5)
        ok, msg = can_place_module(build, pm, catalog, materials)
        assert not ok, "Should reject placement overlapping hull pixels"
        assert "overlap" in msg.lower()

    def test_exceeds_weight_limit(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")  # 55 max weight
        # Stack many heavy modules to exceed weight
        # Cockpit (3.0) + engine (2.5) + weapon (1.5) + shield (1.5) + cargo (2.0) = 10.5
        # That's fine. Let's manually set existing modules to use most weight
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=5),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=7),
            PlacedModule(module_id="small_hold_rk", x=0, y=9),
        ]
        # Add a lot of hull pixels to push weight close to limit
        for x in range(16):
            for y in range(12, 16):
                build.pixels.append(PlacedPixel(x=x, y=y, material_id="standard_plate"))
        # 64 pixels × 0.25 weight = 16.0 + 10.5 module weight = 26.5
        # Now add many more heavy modules (reactor = 4.0 weight)
        # Actually let me just create a build that's clearly over
        heavy_build = ShipBuild(weight_class="tiny")  # 55 max
        # Place enough modules and pixels to exceed 55
        for i in range(10):
            heavy_build.modules.append(PlacedModule(module_id="compact_reactor_rk", x=0, y=0))
        # 10 reactors × 4.0 weight = 40.0, still under 55
        # Add more...
        for i in range(5):
            heavy_build.modules.append(PlacedModule(module_id="scout_pod_rk", x=3, y=0))
        # +5 cockpits × 3.0 = 15.0, total = 55.0 exactly at limit
        pm = PlacedModule(module_id="light_hardpoint_rk", x=10, y=10)
        ok, msg = can_place_module(heavy_build, pm, catalog, materials)
        assert not ok, f"Should reject when weight would be exceeded: {msg}"
        assert "weight" in msg.lower()

    def test_rotated_module_bounds_check(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")  # 16x16
        # Engine is 3w × 2h; rotated 90° becomes 2w × 3h
        # Place at x=15 — rotated it's 2 wide so x+2=17, out of bounds
        pm = PlacedModule(module_id="light_thruster_rk", x=15, y=0, rotation=1)
        ok, msg = can_place_module(build, pm, catalog, materials)
        assert not ok, "Rotated module should check rotated dimensions"


# ============================================================================
# validate_connectivity
# ============================================================================


class TestValidateConnectivity:
    """Test 4-connected component validation."""

    def test_single_module_connected(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="scout_pod_rk", x=5, y=5)]
        ok, msg = validate_connectivity(build, catalog)
        assert ok, f"Single module should be connected: {msg}"

    def test_adjacent_modules_connected(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        # Cockpit at (5,3) is 3×3, bottom row at y=5
        # Engine at (5,6) is 3×2, top row at y=6
        # They share edge at y=5/y=6 — adjacent but not overlapping
        # Wait, cockpit bottom is y=5, engine top is y=6. They don't share an edge.
        # Cockpit occupies rows 3,4,5. Engine occupies rows 6,7.
        # Row 5 and row 6 are adjacent. If they share x coordinates, they connect.
        # Cockpit cols: 5(empty),6(H),7(empty) at row 3; 5,6,7 at rows 4,5
        # Engine cols: 5,6,7 at rows 6,7
        # At y=5: cockpit has pixels at x=5,6,7
        # At y=6: engine has pixels at x=5,6,7
        # (5,5) and (5,6) are 4-adjacent. Connected!
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=5, y=3),
            PlacedModule(module_id="light_thruster_rk", x=5, y=6),
        ]
        ok, msg = validate_connectivity(build, catalog)
        assert ok, f"Adjacent modules should be connected: {msg}"

    def test_disconnected_modules(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        # Place two modules far apart
        build.modules = [
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=0),
            PlacedModule(module_id="light_hardpoint_rk", x=14, y=14),
        ]
        ok, msg = validate_connectivity(build, catalog)
        assert not ok, "Disconnected modules should fail connectivity"

    def test_modules_bridged_by_hull_pixels(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        # Two modules separated by a gap
        build.modules = [
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=0),  # 2×2 at (0,0)
            PlacedModule(module_id="light_hardpoint_rk", x=4, y=0),  # 2×2 at (4,0)
        ]
        # Bridge with hull pixels at x=2,3
        build.pixels = [
            PlacedPixel(x=2, y=0, material_id="standard_plate"),
            PlacedPixel(x=3, y=0, material_id="standard_plate"),
        ]
        ok, msg = validate_connectivity(build, catalog)
        assert ok, f"Hull pixels should bridge disconnected modules: {msg}"

    def test_empty_build_passes(self) -> None:
        """An empty build has no pixels to check — vacuously connected."""
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        ok, msg = validate_connectivity(build, catalog)
        assert ok, "Empty build should pass connectivity (vacuously)"

    def test_hull_pixels_only_connected(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [
            PlacedPixel(x=0, y=0, material_id="standard_plate"),
            PlacedPixel(x=1, y=0, material_id="standard_plate"),
            PlacedPixel(x=2, y=0, material_id="standard_plate"),
        ]
        ok, msg = validate_connectivity(build, catalog)
        assert ok, "Connected hull pixels should pass"

    def test_hull_pixels_only_disconnected(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [
            PlacedPixel(x=0, y=0, material_id="standard_plate"),
            PlacedPixel(x=5, y=5, material_id="standard_plate"),
        ]
        ok, msg = validate_connectivity(build, catalog)
        assert not ok, "Disconnected hull pixels should fail"


# ============================================================================
# validate_requirements
# ============================================================================


class TestValidateRequirements:
    """Test mandatory module requirements per weight class."""

    def test_all_mandatory_present_tiny(self) -> None:
        build, catalog = _valid_tiny_build()
        ok, msg = validate_requirements(build, catalog)
        assert ok, f"Valid tiny build should pass: {msg}"

    def test_missing_cockpit(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="light_thruster_rk", x=0, y=0),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=3),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=5),
            PlacedModule(module_id="small_hold_rk", x=0, y=7),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "cockpit" in msg.lower()

    def test_missing_engine(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=3),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=5),
            PlacedModule(module_id="small_hold_rk", x=0, y=7),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "engine" in msg.lower()

    def test_missing_weapon(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=5),
            PlacedModule(module_id="small_hold_rk", x=0, y=7),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "weapon" in msg.lower()

    def test_missing_shield(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=5),
            PlacedModule(module_id="small_hold_rk", x=0, y=7),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "shield" in msg.lower()

    def test_missing_cargo(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=5),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=7),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "cargo" in msg.lower()

    def test_medium_requires_crew_quarters(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="medium")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=5),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=7),
            PlacedModule(module_id="small_hold_rk", x=0, y=9),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "crew" in msg.lower()

    def test_medium_with_crew_passes(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="medium")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=5),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=7),
            PlacedModule(module_id="small_hold_rk", x=0, y=9),
            PlacedModule(module_id="standard_quarters_rk", x=0, y=11),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert ok, f"Medium with crew quarters should pass: {msg}"

    def test_large_requires_reactor(self) -> None:
        catalog = _module_catalog()
        build = ShipBuild(weight_class="large")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),
            PlacedModule(module_id="light_hardpoint_rk", x=0, y=5),
            PlacedModule(module_id="basic_emitter_rk", x=0, y=7),
            PlacedModule(module_id="small_hold_rk", x=0, y=9),
            PlacedModule(module_id="standard_quarters_rk", x=0, y=11),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok
        assert "reactor" in msg.lower()

    def test_engine_in_rear_30_percent(self) -> None:
        """Engine module must be in the rear 30% of the ship bounding box."""
        catalog = _module_catalog()
        build = ShipBuild(weight_class="tiny")  # 16×16
        # Place engine at the very front (top of canvas = wrong end)
        # Ships face right, stern is left. Engine rear = left side.
        # "Rear 30%" means the left 30% of the canvas.
        # For a 16-wide canvas, rear 30% = x < 16*0.3 = 4.8
        # Place engine at x=10 (far from rear)
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=5, y=5),
            PlacedModule(module_id="light_thruster_rk", x=10, y=5),
            PlacedModule(module_id="light_hardpoint_rk", x=5, y=8),
            PlacedModule(module_id="basic_emitter_rk", x=8, y=5),
            PlacedModule(module_id="small_hold_rk", x=5, y=10),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert not ok, "Engine not in rear 30% should fail"
        assert "engine" in msg.lower()


# ============================================================================
# Stats Computation with Modules
# ============================================================================


class TestStatsComputerWithModules:
    """Test ShipStatsComputer with module stat contributions."""

    def test_module_shield_stats_added(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="basic_emitter_rk", x=0, y=0),
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.shields >= 30, f"Shield module should add 30 shield HP, got {stats.shields}"

    def test_module_cargo_added(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="small_hold_rk", x=0, y=0),
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.cargo_capacity >= 15

    def test_module_crew_added(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="medium")
        build.modules = [
            PlacedModule(module_id="standard_quarters_rk", x=0, y=0),
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.crew_slots >= 2

    def test_module_speed_from_thrust(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="light_thruster_rk", x=0, y=0),
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.speed >= 8, f"Engine thrust should add to speed, got {stats.speed}"

    def test_hull_pixel_stats_still_work(self) -> None:
        """Existing hull pixel stat accumulation should still function."""
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=i, y=0, material_id="standard_plate") for i in range(10)]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        # 10 pixels × 2.5 hull_per_pixel = 25
        assert stats.hull >= 25, f"Hull pixels should contribute hull HP, got {stats.hull}"

    def test_combined_module_and_hull_stats(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="basic_emitter_rk", x=0, y=0),
        ]
        build.pixels = [
            PlacedPixel(x=5, y=5, material_id="standard_plate"),
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.shields >= 30, "Module shields should be present"
        assert stats.hull >= 2, "Hull pixel hull HP should be present"

    def test_module_weight_included(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),  # 3.0
            PlacedModule(module_id="light_thruster_rk", x=0, y=3),  # 2.5
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.weight_current >= 5.5, (
            f"Module weights should be included, got {stats.weight_current}"
        )

    def test_module_cost_included(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),  # base 2000, RK 1.0x
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats.total_cost >= 2000

    def test_weight_ratio_with_modules(self) -> None:
        catalog = _module_catalog()
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")  # max_weight=55
        build.modules = [
            PlacedModule(module_id="scout_pod_rk", x=0, y=0),  # 3.0 weight
        ]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        expected_ratio = 3.0 / 55.0
        assert abs(stats.weight_ratio - expected_ratio) < 0.01, (
            f"Weight ratio should be ~{expected_ratio:.3f}, got {stats.weight_ratio:.3f}"
        )

    def test_backward_compat_no_module_catalog(self) -> None:
        """Calling compute without module_catalog should still work (old behavior)."""
        materials = _materials_catalog()
        build = ShipBuild(weight_class="tiny")
        build.pixels = [
            PlacedPixel(x=0, y=0, material_id="standard_plate"),
        ]
        stats = ShipStatsComputer.compute(build, materials)
        assert stats.hull >= 2, "Should compute hull from pixels without module_catalog"
