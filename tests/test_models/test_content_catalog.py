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
            assert len(set(widths)) == 1, f"Shape {s['id']} has inconsistent row widths: {widths}"

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
            "free",
            "purchase",
            "salvage",
            "quest",
            "faction",
            "mining",
            "refining",
            "boss_drop",
            "crew_quest",
            "trading",
            "ground_exploration",
            "achievement",
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
            assert s.get("unlock_method", "free") == "free", f"Basic shape {s['id']} should be free"

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
        discovery_methods = {
            "salvage",
            "quest",
            "mining",
            "boss_drop",
            "crew_quest",
            "ground_exploration",
        }
        for s in shapes:
            if s.get("unlock_method") in discovery_methods:
                flavor = s.get("discovery_flavor", "")
                assert flavor, (
                    f"Shape {s['id']} (unlock: {s['unlock_method']}) needs discovery_flavor"
                )

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

    def test_all_have_valid_shade_band(self) -> None:
        from spacegame.engine.material_palette import is_valid_band

        materials = _load_materials()
        for m in materials:
            band = m.get("shade_band", "")
            assert band, f"Material {m['id']} needs a shade_band"
            assert is_valid_band(band), f"Material {m['id']} has unknown shade_band '{band}'"

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
            "heavy_armor",
            "reinforced_plate",  # Juggernaut
            "shield_crystal",
            "barrier_lattice",  # Sentinel
            "stealth_composite",
            "phase_alloy",  # Ghost
            "light_alloy",
            "standard_plate",
            "salvage_scrap",  # Starter
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


def _load_module_materials() -> list[dict]:
    with open("data/ships/module_materials.json") as f:
        return json.load(f)["module_materials"]


class TestPaletteDataCompliance:
    """Enforce palette-field discipline across all material JSON data.

    Every material (hull + module) must:
      - Name a valid canonical shade_band
      - If it sets emissive_role or signature_stripe_role, the role must
        be a valid PALETTE_ROLES entry
      - Keep category_offset bounded within what apply_category_offset can
        meaningfully express (|offset| <= 4 covers the widest 5-stop band)
      - Keep noise_intensity / wear_intensity / gloss in [0, 1] and
        rivet_density >= 0

    Catches regressions where a new material lands with a stale color_primary
    triplet or a typo'd band name.
    """

    def _all_materials(self) -> list[tuple[str, dict]]:
        """Return (source_tag, material_dict) across hull + module catalogs."""
        entries: list[tuple[str, dict]] = []
        for m in _load_materials():
            entries.append(("materials.json", m))
        for m in _load_module_materials():
            entries.append(("module_materials.json", m))
        return entries

    def test_every_material_declares_valid_shade_band(self) -> None:
        from spacegame.engine.material_palette import is_valid_band

        for source, m in self._all_materials():
            band = m.get("shade_band")
            assert band, f"{source}:{m['id']} missing shade_band"
            assert is_valid_band(band), (
                f"{source}:{m['id']} has unknown shade_band '{band}'"
            )

    def test_emissive_role_is_valid_palette_role_when_set(self) -> None:
        from spacegame.engine.material_palette import is_valid_role

        for source, m in self._all_materials():
            role = m.get("emissive_role")
            if role is None:
                continue
            assert is_valid_role(role), (
                f"{source}:{m['id']} has unknown emissive_role '{role}'"
            )

    def test_signature_stripe_role_is_valid_palette_role_when_set(self) -> None:
        from spacegame.engine.material_palette import is_valid_role

        for source, m in self._all_materials():
            role = m.get("signature_stripe_role")
            if role is None:
                continue
            assert is_valid_role(role), (
                f"{source}:{m['id']} has unknown signature_stripe_role '{role}'"
            )

    def test_category_offset_within_bounds(self) -> None:
        # A 5-stop band can meaningfully shift -4..+4 (clamping beyond that
        # flattens the band). Flag wider values as likely typos.
        for source, m in self._all_materials():
            offset = m.get("category_offset", 0)
            assert isinstance(offset, int), (
                f"{source}:{m['id']} category_offset must be int, got {type(offset).__name__}"
            )
            assert -4 <= offset <= 4, (
                f"{source}:{m['id']} category_offset={offset} outside [-4, 4]"
            )

    def test_render_params_in_unit_range(self) -> None:
        """noise_intensity, wear_intensity, gloss must lie in [0, 1]."""
        for source, m in self._all_materials():
            for field in ("noise_intensity", "wear_intensity", "gloss"):
                value = m.get(field)
                if value is None:
                    continue
                assert 0.0 <= value <= 1.0, (
                    f"{source}:{m['id']} {field}={value} outside [0, 1]"
                )

    def test_rivet_density_non_negative(self) -> None:
        for source, m in self._all_materials():
            density = m.get("rivet_density")
            if density is None:
                continue
            assert density >= 0.0, (
                f"{source}:{m['id']} rivet_density={density} negative"
            )

    def test_legacy_color_fields_fully_purged(self) -> None:
        """No material JSON retains color_primary / color_accent / color_highlight."""
        banned = {"color_primary", "color_accent", "color_highlight"}
        for source, m in self._all_materials():
            leaked = banned & m.keys()
            assert not leaked, (
                f"{source}:{m['id']} still carries legacy color fields: {leaked}"
            )

    def test_module_materials_emissive_coverage_matches_bible_intent(self) -> None:
        """Bible §3.5 identifies these module kinds as emissive. Enforce it.

        Prevents silent regressions where a refactor strips emissive_role
        off a glowing module, making the ship go visually dead.
        """
        expected_emissive = {
            "cockpit_glass",
            "console_panel",
            "exhaust_port",
            "reactor_core",
            "shield_emitter",
            "sensor_dish",
            "legendary_hull",
            "legendary_core",
        }
        mat_map = {m["id"]: m for m in _load_module_materials()}
        for mid in expected_emissive:
            assert mid in mat_map, f"Module material '{mid}' missing from catalog"
            assert mat_map[mid].get("emissive_role"), (
                f"Module material '{mid}' must declare an emissive_role "
                f"(Bible §3.5 identifies it as a light source)"
            )
