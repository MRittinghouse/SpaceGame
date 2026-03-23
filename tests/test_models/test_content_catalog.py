"""Tests for Phase D1 — Content catalog integrity and balance.

Verifies shapes have valid pixel masks, materials have reasonable
stats, no duplicate IDs, and all unlock metadata is well-formed.
"""

import json


def _load_shapes() -> list[dict]:
    with open("data/ships/shapes.json") as f:
        return json.load(f)["shapes"]


def _load_materials() -> list[dict]:
    with open("data/ships/materials.json") as f:
        return json.load(f)["materials"]


class TestShapeCatalogIntegrity:
    """Verify shape data is well-formed."""

    def test_shape_count(self) -> None:
        shapes = _load_shapes()
        assert len(shapes) >= 40, f"Expected at least 40 shapes, got {len(shapes)}"

    def test_no_duplicate_ids(self) -> None:
        shapes = _load_shapes()
        ids = [s["id"] for s in shapes]
        dupes = [id for id in ids if ids.count(id) > 1]
        assert not dupes, f"Duplicate shape IDs: {set(dupes)}"

    def test_all_have_pixel_mask(self) -> None:
        shapes = _load_shapes()
        for s in shapes:
            mask = s.get("pixel_mask_compact", [])
            assert len(mask) > 0, f"Shape {s['id']} has no pixel mask"
            # All rows should be the same length
            widths = [len(row) for row in mask]
            assert len(set(widths)) == 1, (
                f"Shape {s['id']} has inconsistent row widths: {widths}"
            )

    def test_all_have_filled_pixels(self) -> None:
        shapes = _load_shapes()
        for s in shapes:
            mask = s.get("pixel_mask_compact", [])
            pixel_count = sum(row.count("#") for row in mask)
            assert pixel_count > 0, f"Shape {s['id']} has no filled pixels"

    def test_all_have_valid_category(self) -> None:
        valid = {"basic", "intermediate", "advanced", "exotic", "faction"}
        shapes = _load_shapes()
        for s in shapes:
            cat = s.get("category", "basic")
            assert cat in valid, f"Shape {s['id']} has invalid category: {cat}"

    def test_all_have_valid_unlock_method(self) -> None:
        valid = {
            "free", "purchase", "salvage", "quest", "faction", "mining",
            "refining", "boss_drop", "crew_quest", "trading",
            "ground_exploration", "achievement",
        }
        shapes = _load_shapes()
        for s in shapes:
            method = s.get("unlock_method", "free")
            assert method in valid, f"Shape {s['id']} has invalid unlock: {method}"

    def test_basic_shapes_are_free(self) -> None:
        shapes = _load_shapes()
        basic = [s for s in shapes if s.get("category") == "basic"]
        assert len(basic) == 9, f"Expected 9 basic shapes, got {len(basic)}"
        for s in basic:
            assert s.get("unlock_method", "free") == "free", (
                f"Basic shape {s['id']} should be free"
            )

    def test_intermediate_shapes_have_cost(self) -> None:
        shapes = _load_shapes()
        intermediate = [s for s in shapes if s.get("category") == "intermediate"]
        assert len(intermediate) >= 10, f"Expected 10+ intermediate, got {len(intermediate)}"
        for s in intermediate:
            cost = s.get("unlock_cost", 0)
            assert cost > 0, f"Intermediate {s['id']} should have purchase cost"

    def test_discovery_shapes_have_flavor(self) -> None:
        """Non-purchase shapes should have discovery_flavor text."""
        shapes = _load_shapes()
        discovery_methods = {"salvage", "quest", "mining", "boss_drop", "crew_quest", "ground_exploration"}
        for s in shapes:
            if s.get("unlock_method") in discovery_methods:
                flavor = s.get("discovery_flavor", "")
                assert flavor, f"Shape {s['id']} (unlock: {s['unlock_method']}) needs discovery_flavor"

    def test_shapes_load_via_data_loader(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.ship_build import HullShape
        dl = get_data_loader()
        dl.load_hull_shapes()
        assert len(dl.hull_shapes) >= 40
        for sid, shape in dl.hull_shapes.items():
            assert isinstance(shape, HullShape)
            assert shape.pixel_count > 0


class TestMaterialCatalogIntegrity:
    """Verify material data is well-formed and balanced."""

    def test_material_count(self) -> None:
        materials = _load_materials()
        assert len(materials) == 16, f"Expected 16 materials, got {len(materials)}"

    def test_no_duplicate_ids(self) -> None:
        materials = _load_materials()
        ids = [m["id"] for m in materials]
        dupes = [id for id in ids if ids.count(id) > 1]
        assert not dupes, f"Duplicate material IDs: {set(dupes)}"

    def test_all_have_positive_hull(self) -> None:
        materials = _load_materials()
        for m in materials:
            hull = m.get("hull_per_pixel", 0)
            assert hull > 0, f"Material {m['id']} has no hull contribution"

    def test_all_have_positive_weight(self) -> None:
        materials = _load_materials()
        for m in materials:
            weight = m.get("weight_per_pixel", 0)
            assert weight > 0, f"Material {m['id']} has no weight"

    def test_all_have_positive_cost(self) -> None:
        materials = _load_materials()
        for m in materials:
            cost = m.get("cost_per_pixel", 0)
            assert cost > 0, f"Material {m['id']} has no cost"

    def test_all_have_valid_color(self) -> None:
        materials = _load_materials()
        for m in materials:
            color = m.get("color_primary", [])
            assert len(color) == 3, f"Material {m['id']} needs RGB color"
            assert all(0 <= c <= 255 for c in color), f"Material {m['id']} has invalid color"

    def test_starter_materials_are_free(self) -> None:
        materials = _load_materials()
        free = [m for m in materials if m.get("unlock_method", "free") == "free"]
        assert len(free) == 3, f"Expected 3 free starter materials, got {len(free)}"

    def test_materials_load_via_data_loader(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.ship_build import HullMaterial
        dl = get_data_loader()
        dl.load_hull_materials()
        assert len(dl.hull_materials) == 16
        for mid, mat in dl.hull_materials.items():
            assert isinstance(mat, HullMaterial)
            assert mat.hull_per_pixel > 0

    def test_identity_materials_exist(self) -> None:
        """Key identity materials must exist for the builder to work."""
        materials = _load_materials()
        ids = {m["id"] for m in materials}
        required = {
            "heavy_armor", "reinforced_plate",  # Juggernaut
            "shield_crystal", "barrier_lattice",  # Sentinel
            "stealth_composite", "phase_alloy",  # Ghost
            "light_alloy", "standard_plate", "salvage_scrap",  # Starter
        }
        missing = required - ids
        assert not missing, f"Missing required materials: {missing}"

    def test_weight_balance(self) -> None:
        """Heavier materials should give more hull/armor, lighter give evasion."""
        materials = _load_materials()
        mat_map = {m["id"]: m for m in materials}

        heavy = mat_map["heavy_armor"]
        light = mat_map["light_alloy"]
        assert heavy["weight_per_pixel"] > light["weight_per_pixel"]
        assert heavy["hull_per_pixel"] > light["hull_per_pixel"]
        assert light["evasion_per_pixel"] > heavy.get("evasion_per_pixel", 0)

    def test_cost_scales_with_power(self) -> None:
        """Advanced materials should generally cost more per pixel."""
        materials = _load_materials()
        mat_map = {m["id"]: m for m in materials}

        scrap = mat_map["salvage_scrap"]
        standard = mat_map["standard_plate"]
        ablative = mat_map["ablative_plating"]

        assert scrap["cost_per_pixel"] < standard["cost_per_pixel"]
        assert standard["cost_per_pixel"] < ablative["cost_per_pixel"]
