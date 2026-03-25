"""Tests for ship module data models — Phase 1 of Shipbuilder Upgrade.

Covers ShipModule creation, multi-character mask parsing, rotation,
flipping, pixel resolution, PlacedModule positioning, serialization
round-trips, and DataLoader integration.
"""

from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    resolve_placed_module,
    MODULE_CATEGORIES,
    MANUFACTURERS,
    MANUFACTURER_COST_MULTIPLIERS,
)
from spacegame.models.ship_build import PlacedPixel


# ============================================================================
# Helpers
# ============================================================================


def _cockpit_3x3() -> ShipModule:
    """A simple 3x3 cockpit module."""
    return ShipModule(
        id="scout_pod",
        name="Scout Pod",
        description="A cramped one-seater cockpit.",
        category="cockpit",
        manufacturer="reyes_kowalski",
        pixel_grid=[
            [".", "H", "."],
            ["H", "G", "H"],
            ["H", "H", "H"],
        ],
        material_map={"H": "module_hull_rk", "G": "cockpit_glass"},
        provides={"slot_type": "core", "crew_capacity": 1},
        weight=3.0,
        base_cost=2000,
    )


def _engine_3x2() -> ShipModule:
    """A simple 3x2 engine module."""
    return ShipModule(
        id="light_thruster",
        name="Light Thruster",
        description="Compact, efficient propulsion.",
        category="engine",
        manufacturer="reyes_kowalski",
        pixel_grid=[
            ["H", "E", "H"],
            ["H", "E", "H"],
        ],
        material_map={"H": "module_hull_rk", "E": "exhaust_port"},
        provides={"slot_type": "engine", "thrust": 8, "fuel_efficiency": 1.0},
        weight=2.5,
        base_cost=1500,
    )


def _weapon_2x2() -> ShipModule:
    """A minimal 2x2 weapon hardpoint."""
    return ShipModule(
        id="light_hardpoint",
        name="Light Hardpoint",
        description="A small weapon mount.",
        category="weapon",
        manufacturer="reyes_kowalski",
        pixel_grid=[
            ["W", "H"],
            ["H", "H"],
        ],
        material_map={"H": "module_hull_rk", "W": "weapon_barrel"},
        provides={"slot_type": "weapon", "weapon_size": "small"},
        weight=1.5,
        base_cost=1500,
    )


def _asymmetric_module() -> ShipModule:
    """A 4x3 L-shaped module for testing rotation/flip distinctness."""
    return ShipModule(
        id="test_l_shape",
        name="L-Shape Test",
        description="Asymmetric test module.",
        category="structural",
        manufacturer="reyes_kowalski",
        pixel_grid=[
            ["H", ".", ".", "."],
            ["H", ".", ".", "."],
            ["H", "H", "H", "H"],
        ],
        material_map={"H": "module_hull_rk"},
        provides={},
        weight=3.0,
        base_cost=500,
    )


# ============================================================================
# ShipModule — Creation and Properties
# ============================================================================


class TestShipModuleProperties:
    """Test basic ShipModule creation and computed properties."""

    def test_width(self) -> None:
        m = _cockpit_3x3()
        assert m.width == 3, f"Expected width 3, got {m.width}"

    def test_height(self) -> None:
        m = _cockpit_3x3()
        assert m.height == 3, f"Expected height 3, got {m.height}"

    def test_width_rectangular(self) -> None:
        m = _engine_3x2()
        assert m.width == 3
        assert m.height == 2

    def test_pixel_count_excludes_empty(self) -> None:
        m = _cockpit_3x3()
        # Grid: .H. / HGH / HHH = 7 filled, 2 empty
        assert m.pixel_count == 7, f"Expected 7 filled pixels, got {m.pixel_count}"

    def test_pixel_count_all_filled(self) -> None:
        m = _weapon_2x2()
        assert m.pixel_count == 4

    def test_pixel_count_l_shape(self) -> None:
        m = _asymmetric_module()
        # H... / H... / HHHH = 6 filled
        assert m.pixel_count == 6

    def test_empty_module(self) -> None:
        m = ShipModule(
            id="empty",
            name="Empty",
            description="",
            category="structural",
            manufacturer="reyes_kowalski",
            pixel_grid=[],
            material_map={},
            provides={},
            weight=0,
            base_cost=0,
        )
        assert m.width == 0
        assert m.height == 0
        assert m.pixel_count == 0


# ============================================================================
# ShipModule — Filled Pixels (Local Coordinates)
# ============================================================================


class TestShipModuleFilledPixels:
    """Test extraction of filled pixel coordinates with material chars."""

    def test_filled_pixels_simple(self) -> None:
        m = _weapon_2x2()
        pixels = m.filled_pixels()
        assert len(pixels) == 4
        # All cells filled: (0,0)=W, (1,0)=H, (0,1)=H, (1,1)=H
        assert (0, 0, "W") in pixels
        assert (1, 0, "H") in pixels
        assert (0, 1, "H") in pixels
        assert (1, 1, "H") in pixels

    def test_filled_pixels_with_empty(self) -> None:
        m = _cockpit_3x3()
        pixels = m.filled_pixels()
        assert len(pixels) == 7
        # Top-left and top-right are empty
        chars = {(x, y): c for x, y, c in pixels}
        assert (0, 0) not in chars, "Top-left should be empty"
        assert (2, 0) not in chars, "Top-right should be empty"
        assert chars[(1, 0)] == "H"  # Top-center
        assert chars[(1, 1)] == "G"  # Center = glass

    def test_filled_pixels_multi_material(self) -> None:
        m = _engine_3x2()
        pixels = m.filled_pixels()
        chars = {(x, y): c for x, y, c in pixels}
        assert chars[(1, 0)] == "E"  # Exhaust center-top
        assert chars[(1, 1)] == "E"  # Exhaust center-bottom
        assert chars[(0, 0)] == "H"  # Hull left-top


# ============================================================================
# ShipModule — Resolved Pixels (Material IDs)
# ============================================================================


class TestShipModuleResolvedPixels:
    """Test resolution of material chars to material IDs via material_map."""

    def test_resolved_pixels(self) -> None:
        m = _cockpit_3x3()
        pixels = m.resolved_pixels()
        assert len(pixels) == 7
        mats = {(x, y): mid for x, y, mid in pixels}
        assert mats[(1, 0)] == "module_hull_rk"
        assert mats[(1, 1)] == "cockpit_glass"
        assert mats[(0, 1)] == "module_hull_rk"

    def test_resolved_pixels_engine(self) -> None:
        m = _engine_3x2()
        pixels = m.resolved_pixels()
        mats = {(x, y): mid for x, y, mid in pixels}
        assert mats[(1, 0)] == "exhaust_port"
        assert mats[(0, 0)] == "module_hull_rk"


# ============================================================================
# ShipModule — Rotation
# ============================================================================


class TestShipModuleRotation:
    """Test 90° clockwise rotation of module pixel grids."""

    def test_rotate_90_changes_dimensions(self) -> None:
        m = _engine_3x2()  # 3 wide x 2 tall
        r = m.rotated(1)
        assert r.width == 2, f"After 90° CW, width should be 2, got {r.width}"
        assert r.height == 3, f"After 90° CW, height should be 3, got {r.height}"

    def test_rotate_90_preserves_pixel_count(self) -> None:
        m = _cockpit_3x3()
        r = m.rotated(1)
        assert r.pixel_count == m.pixel_count

    def test_rotate_180_same_dimensions(self) -> None:
        m = _engine_3x2()
        r = m.rotated(2)
        assert r.width == 3
        assert r.height == 2

    def test_rotate_360_is_identity(self) -> None:
        m = _asymmetric_module()
        r = m.rotated(4)
        assert r.pixel_grid == m.pixel_grid

    def test_rotate_90_pixel_positions(self) -> None:
        """Verify specific pixel positions after 90° CW rotation.

        Original (4x3):
            H...
            H...
            HHHH

        After 90° CW (3x4):
            HHH
            H..
            H..
            H..
        """
        m = _asymmetric_module()
        r = m.rotated(1)
        assert r.width == 3
        assert r.height == 4
        pixels = {(x, y) for x, y, _ in r.filled_pixels()}
        # Top row should be HHH
        assert (0, 0) in pixels
        assert (1, 0) in pixels
        assert (2, 0) in pixels
        # Left column should extend down
        assert (0, 1) in pixels
        assert (0, 2) in pixels
        assert (0, 3) in pixels
        # Interior should be empty
        assert (1, 1) not in pixels
        assert (2, 1) not in pixels

    def test_four_rotations_produce_distinct_grids(self) -> None:
        """An asymmetric shape should have 4 distinct rotations."""
        m = _asymmetric_module()
        grids = set()
        for i in range(4):
            r = m.rotated(i)
            grid_key = tuple(tuple(row) for row in r.pixel_grid)
            grids.add(grid_key)
        assert len(grids) == 4, "Asymmetric module should have 4 distinct rotations"

    def test_rotation_preserves_material_chars(self) -> None:
        m = _engine_3x2()
        r = m.rotated(1)
        chars = {c for _, _, c in r.filled_pixels()}
        assert "E" in chars, "Exhaust port chars should survive rotation"
        assert "H" in chars, "Hull chars should survive rotation"


# ============================================================================
# ShipModule — Flip
# ============================================================================


class TestShipModuleFlip:
    """Test horizontal flipping of module pixel grids."""

    def test_flip_preserves_dimensions(self) -> None:
        m = _asymmetric_module()
        f = m.flipped()
        assert f.width == m.width
        assert f.height == m.height

    def test_flip_preserves_pixel_count(self) -> None:
        m = _asymmetric_module()
        f = m.flipped()
        assert f.pixel_count == m.pixel_count

    def test_double_flip_is_identity(self) -> None:
        m = _asymmetric_module()
        ff = m.flipped().flipped()
        assert ff.pixel_grid == m.pixel_grid

    def test_flip_pixel_positions(self) -> None:
        """Verify specific pixel positions after horizontal flip.

        Original (4x3):
            H...
            H...
            HHHH

        After flip (4x3):
            ...H
            ...H
            HHHH
        """
        m = _asymmetric_module()
        f = m.flipped()
        pixels = {(x, y) for x, y, _ in f.filled_pixels()}
        # Top-right should now be filled (was top-left)
        assert (3, 0) in pixels
        assert (3, 1) in pixels
        # Top-left should now be empty (was filled)
        assert (0, 0) not in pixels
        assert (0, 1) not in pixels
        # Bottom row still all filled
        for x in range(4):
            assert (x, 2) in pixels

    def test_flip_preserves_material_chars(self) -> None:
        m = _engine_3x2()
        f = m.flipped()
        chars = {c for _, _, c in f.filled_pixels()}
        assert "E" in chars
        assert "H" in chars


# ============================================================================
# ShipModule — Rotation + Flip Composition
# ============================================================================


class TestShipModuleOrientations:
    """Test all 8 possible orientations (4 rotations × 2 flip states)."""

    def test_eight_distinct_orientations(self) -> None:
        """An asymmetric module should produce 8 distinct orientations."""
        m = _asymmetric_module()
        orientations = set()
        for rot in range(4):
            for flip in (False, True):
                oriented = m
                if flip:
                    oriented = oriented.flipped()
                oriented = oriented.rotated(rot)
                grid_key = tuple(tuple(row) for row in oriented.pixel_grid)
                orientations.add(grid_key)
        assert len(orientations) == 8, f"Expected 8 distinct orientations, got {len(orientations)}"


# ============================================================================
# PlacedModule
# ============================================================================


class TestPlacedModule:
    """Test PlacedModule creation and serialization."""

    def test_create(self) -> None:
        pm = PlacedModule(
            module_id="scout_pod",
            x=5,
            y=3,
            rotation=1,
            flipped=False,
        )
        assert pm.module_id == "scout_pod"
        assert pm.x == 5
        assert pm.y == 3
        assert pm.rotation == 1
        assert pm.flipped is False

    def test_to_dict(self) -> None:
        pm = PlacedModule(
            module_id="light_thruster",
            x=10,
            y=8,
            rotation=2,
            flipped=True,
        )
        d = pm.to_dict()
        assert d["module_id"] == "light_thruster"
        assert d["x"] == 10
        assert d["y"] == 8
        assert d["rotation"] == 2
        assert d["flipped"] is True

    def test_from_dict_round_trip(self) -> None:
        pm = PlacedModule(
            module_id="heavy_drive",
            x=20,
            y=15,
            rotation=3,
            flipped=True,
        )
        d = pm.to_dict()
        restored = PlacedModule.from_dict(d)
        assert restored.module_id == pm.module_id
        assert restored.x == pm.x
        assert restored.y == pm.y
        assert restored.rotation == pm.rotation
        assert restored.flipped == pm.flipped

    def test_from_dict_defaults(self) -> None:
        d = {"module_id": "scout_pod", "x": 0, "y": 0}
        pm = PlacedModule.from_dict(d)
        assert pm.rotation == 0
        assert pm.flipped is False


# ============================================================================
# resolve_placed_module — World Coordinate Resolution
# ============================================================================


class TestResolvePlacedModule:
    """Test resolving a PlacedModule into world-space PlacedPixels."""

    def _catalog(self) -> dict[str, ShipModule]:
        return {
            "scout_pod": _cockpit_3x3(),
            "light_thruster": _engine_3x2(),
            "light_hardpoint": _weapon_2x2(),
            "test_l_shape": _asymmetric_module(),
        }

    def test_resolve_at_origin(self) -> None:
        catalog = self._catalog()
        pm = PlacedModule(module_id="light_hardpoint", x=0, y=0, rotation=0, flipped=False)
        pixels = resolve_placed_module(pm, catalog)
        assert len(pixels) == 4
        coords = {(p.x, p.y) for p in pixels}
        assert coords == {(0, 0), (1, 0), (0, 1), (1, 1)}

    def test_resolve_with_offset(self) -> None:
        catalog = self._catalog()
        pm = PlacedModule(module_id="light_hardpoint", x=5, y=10, rotation=0, flipped=False)
        pixels = resolve_placed_module(pm, catalog)
        assert len(pixels) == 4
        coords = {(p.x, p.y) for p in pixels}
        assert coords == {(5, 10), (6, 10), (5, 11), (6, 11)}

    def test_resolve_preserves_materials(self) -> None:
        catalog = self._catalog()
        pm = PlacedModule(module_id="light_hardpoint", x=0, y=0, rotation=0, flipped=False)
        pixels = resolve_placed_module(pm, catalog)
        mat_at = {(p.x, p.y): p.material_id for p in pixels}
        assert mat_at[(0, 0)] == "weapon_barrel"
        assert mat_at[(1, 0)] == "module_hull_rk"

    def test_resolve_with_rotation(self) -> None:
        catalog = self._catalog()
        # Engine is 3w x 2h; after 90° CW becomes 2w x 3h
        pm = PlacedModule(module_id="light_thruster", x=0, y=0, rotation=1, flipped=False)
        pixels = resolve_placed_module(pm, catalog)
        assert len(pixels) == 6
        # Check dimensions of bounding box
        xs = {p.x for p in pixels}
        ys = {p.y for p in pixels}
        assert max(xs) - min(xs) + 1 == 2, "Rotated width should be 2"
        assert max(ys) - min(ys) + 1 == 3, "Rotated height should be 3"

    def test_resolve_with_flip(self) -> None:
        catalog = self._catalog()
        # L-shape: H at (0,0),(0,1),(0,2),(1,2),(2,2),(3,2)
        # Flipped: H at (3,0),(3,1),(3,2),(2,2),(1,2),(0,2)
        pm = PlacedModule(module_id="test_l_shape", x=0, y=0, rotation=0, flipped=True)
        pixels = resolve_placed_module(pm, catalog)
        assert len(pixels) == 6
        coords = {(p.x, p.y) for p in pixels}
        assert (3, 0) in coords, "Top-right should be filled after flip"
        assert (0, 0) not in coords, "Top-left should be empty after flip"

    def test_resolve_with_rotation_and_flip(self) -> None:
        catalog = self._catalog()
        pm = PlacedModule(
            module_id="test_l_shape",
            x=2,
            y=3,
            rotation=1,
            flipped=True,
        )
        pixels = resolve_placed_module(pm, catalog)
        assert len(pixels) == 6
        # All pixels should be offset by (2, 3)
        for p in pixels:
            assert p.x >= 2
            assert p.y >= 3

    def test_resolve_returns_placed_pixels(self) -> None:
        catalog = self._catalog()
        pm = PlacedModule(module_id="scout_pod", x=0, y=0, rotation=0, flipped=False)
        pixels = resolve_placed_module(pm, catalog)
        for p in pixels:
            assert isinstance(p, PlacedPixel), f"Expected PlacedPixel, got {type(p)}"


# ============================================================================
# ShipModule — Serialization
# ============================================================================


class TestShipModuleSerialization:
    """Test ShipModule to_dict / from_dict round-trips."""

    def test_to_dict_has_required_fields(self) -> None:
        m = _cockpit_3x3()
        d = m.to_dict()
        assert d["id"] == "scout_pod"
        assert d["name"] == "Scout Pod"
        assert d["category"] == "cockpit"
        assert d["manufacturer"] == "reyes_kowalski"
        assert "pixel_mask_compact" in d
        assert d["material_map"] == {"H": "module_hull_rk", "G": "cockpit_glass"}
        assert d["provides"] == {"slot_type": "core", "crew_capacity": 1}
        assert d["weight"] == 3.0
        assert d["base_cost"] == 2000

    def test_to_dict_compact_format(self) -> None:
        m = _cockpit_3x3()
        d = m.to_dict()
        assert d["pixel_mask_compact"] == [".H.", "HGH", "HHH"]

    def test_from_dict_round_trip(self) -> None:
        m = _cockpit_3x3()
        d = m.to_dict()
        restored = ShipModule.from_dict(d)
        assert restored.id == m.id
        assert restored.name == m.name
        assert restored.category == m.category
        assert restored.manufacturer == m.manufacturer
        assert restored.pixel_grid == m.pixel_grid
        assert restored.material_map == m.material_map
        assert restored.provides == m.provides
        assert restored.weight == m.weight
        assert restored.base_cost == m.base_cost
        assert restored.width == m.width
        assert restored.height == m.height
        assert restored.pixel_count == m.pixel_count

    def test_from_dict_with_defaults(self) -> None:
        d = {
            "id": "test",
            "name": "Test",
            "pixel_mask_compact": ["HH", "HH"],
            "material_map": {"H": "module_hull_rk"},
        }
        m = ShipModule.from_dict(d)
        assert m.category == "structural"
        assert m.manufacturer == "reyes_kowalski"
        assert m.description == ""
        assert m.provides == {}
        assert m.weight == 0.0
        assert m.base_cost == 0
        assert m.unlock_method == "free"
        assert m.unlock_cost == 0

    def test_from_dict_preserves_unlock_fields(self) -> None:
        d = {
            "id": "rare_part",
            "name": "Rare Part",
            "pixel_mask_compact": ["HH"],
            "material_map": {"H": "module_hull_rk"},
            "unlock_method": "quest",
            "unlock_cost": 0,
            "unlock_source": "quest_iron_heart",
            "discovery_flavor": "Pulled from the wreckage of the Iron Heart.",
        }
        m = ShipModule.from_dict(d)
        assert m.unlock_method == "quest"
        assert m.unlock_source == "quest_iron_heart"
        assert m.discovery_flavor == "Pulled from the wreckage of the Iron Heart."


# ============================================================================
# Constants
# ============================================================================


class TestModuleConstants:
    """Test module-level constants are properly defined."""

    def test_module_categories(self) -> None:
        expected = {
            "cockpit",
            "engine",
            "weapon",
            "shield",
            "cargo",
            "crew",
            "reactor",
            "utility",
            "structural",
        }
        assert MODULE_CATEGORIES == expected

    def test_manufacturers(self) -> None:
        expected = {
            "reyes_kowalski",
            "foundry",
            "talon",
            "sable",
            "meridian",
            "salvage_rat",
        }
        assert MANUFACTURERS == expected

    def test_manufacturer_cost_multipliers(self) -> None:
        assert MANUFACTURER_COST_MULTIPLIERS["reyes_kowalski"] == 1.0
        assert MANUFACTURER_COST_MULTIPLIERS["salvage_rat"] == 0.6
        assert MANUFACTURER_COST_MULTIPLIERS["meridian"] == 1.5
        # All manufacturers should have a multiplier
        for mfg in MANUFACTURERS:
            assert mfg in MANUFACTURER_COST_MULTIPLIERS, f"Missing multiplier for {mfg}"

    def test_instantiation_cost(self) -> None:
        """Module instantiation cost = base_cost × manufacturer multiplier."""
        m = _cockpit_3x3()  # base_cost=2000, manufacturer=reyes_kowalski (1.0x)
        expected = int(m.base_cost * MANUFACTURER_COST_MULTIPLIERS[m.manufacturer])
        assert m.instantiation_cost == expected

    def test_instantiation_cost_expensive_manufacturer(self) -> None:
        m = ShipModule(
            id="test",
            name="Test",
            description="",
            category="cockpit",
            manufacturer="meridian",
            pixel_grid=[["H"]],
            material_map={"H": "module_hull_meridian"},
            provides={},
            weight=1.0,
            base_cost=1000,
        )
        # Meridian = 1.5x
        assert m.instantiation_cost == 1500


# ============================================================================
# DataLoader Integration
# ============================================================================


class TestDataLoaderModules:
    """Test loading modules and module materials from JSON via DataLoader."""

    def _loader(self):
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_ship_modules()
        loader.load_hull_materials()
        loader.load_module_materials()
        return loader

    def test_load_ship_modules(self) -> None:
        loader = self._loader()
        assert len(loader.ship_modules) > 0, "Should load at least one module"

    def test_all_modules_have_valid_masks(self) -> None:
        loader = self._loader()
        for mid, module in loader.ship_modules.items():
            assert module.pixel_count > 0, f"Module {mid} has no filled pixels"
            assert module.width > 0, f"Module {mid} has zero width"
            assert module.height > 0, f"Module {mid} has zero height"

    def test_all_material_map_chars_used_in_mask(self) -> None:
        """Every char in material_map should appear at least once in the mask."""
        loader = self._loader()
        for mid, module in loader.ship_modules.items():
            chars_in_mask = {c for _, _, c in module.filled_pixels()}
            for char in module.material_map:
                assert char in chars_in_mask, (
                    f"Module {mid}: material_map char '{char}' not used in mask"
                )

    def test_all_mask_chars_in_material_map(self) -> None:
        """Every non-'.' char in the mask should be in material_map."""
        loader = self._loader()
        for mid, module in loader.ship_modules.items():
            for _, _, char in module.filled_pixels():
                assert char in module.material_map, (
                    f"Module {mid}: mask char '{char}' not in material_map"
                )

    def test_no_duplicate_ids(self) -> None:
        import json
        from pathlib import Path

        path = Path("data/ships/modules.json")
        with open(path) as f:
            data = json.load(f)
        ids = [m["id"] for m in data["modules"]]
        assert len(ids) == len(set(ids)), (
            f"Duplicate module IDs found: {[i for i in ids if ids.count(i) > 1]}"
        )

    def test_every_mandatory_category_has_starter(self) -> None:
        """Each mandatory category must have at least one free module."""
        loader = self._loader()
        mandatory = {"cockpit", "engine", "weapon", "shield", "cargo"}
        for cat in mandatory:
            free_mods = [
                m
                for m in loader.ship_modules.values()
                if m.category == cat and m.unlock_method == "free"
            ]
            assert len(free_mods) >= 1, f"Category '{cat}' has no free starter module"

    def test_module_materials_loaded(self) -> None:
        loader = self._loader()
        assert "cockpit_glass" in loader.hull_materials
        assert "exhaust_port" in loader.hull_materials
        assert "weapon_barrel" in loader.hull_materials
        assert "shield_emitter" in loader.hull_materials

    def test_manufacturer_hull_colors_loaded(self) -> None:
        loader = self._loader()
        for mfg in ["rk", "foundry", "talon", "sable", "meridian", "salvage"]:
            mat_id = f"module_hull_{mfg}"
            assert mat_id in loader.hull_materials, f"Missing manufacturer hull material: {mat_id}"

    def test_all_module_materials_have_colors(self) -> None:
        loader = self._loader()
        module_mat_ids = set()
        for module in loader.ship_modules.values():
            for mat_id in module.material_map.values():
                module_mat_ids.add(mat_id)
        for mat_id in module_mat_ids:
            assert mat_id in loader.hull_materials, (
                f"Module references material '{mat_id}' which is not in hull_materials"
            )
            mat = loader.hull_materials[mat_id]
            assert mat.color_primary != (0, 0, 0) or mat_id == "exhaust_port", (
                f"Material '{mat_id}' has default black color_primary"
            )

    def test_rotation_works_for_all_loaded_modules(self) -> None:
        loader = self._loader()
        for mid, module in loader.ship_modules.items():
            for rot in range(4):
                rotated = module.rotated(rot)
                assert rotated.pixel_count == module.pixel_count, (
                    f"Module {mid} rotation {rot} changed pixel count"
                )
