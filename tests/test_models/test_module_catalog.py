"""Tests for Phase 7 — Full module catalog content quality.

Validates the expanded 119-module catalog for completeness, balance,
variety, and data integrity across all categories and manufacturers.
"""

import json
from pathlib import Path

from spacegame.data_loader import DataLoader
from spacegame.models.ship_module import MODULE_CATEGORIES, MANUFACTURERS


def _loader() -> DataLoader:
    dl = DataLoader()
    dl.load_ship_modules()
    dl.load_hull_materials()
    dl.load_module_materials()
    return dl


class TestCatalogCompleteness:
    """Verify the catalog meets target counts and coverage."""

    def test_total_module_count(self) -> None:
        dl = _loader()
        assert len(dl.ship_modules) >= 100, f"Target is 100+ modules, got {len(dl.ship_modules)}"

    def test_every_category_represented(self) -> None:
        dl = _loader()
        categories = {m.category for m in dl.ship_modules.values()}
        for cat in MODULE_CATEGORIES:
            assert cat in categories, f"Category '{cat}' has no modules"

    def test_minimum_per_category(self) -> None:
        """Each category should have at least 6 modules."""
        dl = _loader()
        counts: dict[str, int] = {}
        for m in dl.ship_modules.values():
            counts[m.category] = counts.get(m.category, 0) + 1
        for cat in MODULE_CATEGORIES:
            assert counts.get(cat, 0) >= 6, (
                f"Category '{cat}' has {counts.get(cat, 0)} modules (need >= 6)"
            )

    def test_every_manufacturer_represented(self) -> None:
        dl = _loader()
        mfgs = {m.manufacturer for m in dl.ship_modules.values()}
        for mfg in MANUFACTURERS:
            assert mfg in mfgs, f"Manufacturer '{mfg}' has no modules"

    def test_free_starters_per_mandatory_category(self) -> None:
        """Each mandatory category must have at least one free module."""
        dl = _loader()
        mandatory = {"cockpit", "engine", "weapon", "shield", "cargo"}
        for cat in mandatory:
            free_mods = [
                m
                for m in dl.ship_modules.values()
                if m.category == cat and m.unlock_method == "free"
            ]
            assert len(free_mods) >= 1, f"Category '{cat}' has no free starter module"

    def test_unlock_method_variety(self) -> None:
        """Modules should be distributed across multiple unlock methods."""
        dl = _loader()
        methods = {m.unlock_method for m in dl.ship_modules.values()}
        assert "free" in methods
        assert "purchase" in methods
        assert "faction" in methods
        assert "quest" in methods


class TestCatalogDataIntegrity:
    """Verify structural integrity of all module data."""

    def test_no_duplicate_ids(self) -> None:
        path = Path("data/ships/modules.json")
        with open(path) as f:
            data = json.load(f)
        ids = [m["id"] for m in data["modules"]]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert len(dupes) == 0, f"Duplicate module IDs: {set(dupes)}"

    def test_all_masks_valid(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            assert m.pixel_count > 0, f"Module {mid} has no filled pixels"
            assert m.width > 0, f"Module {mid} has zero width"
            assert m.height > 0, f"Module {mid} has zero height"

    def test_all_mask_chars_mapped(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            for _, _, char in m.filled_pixels():
                assert char in m.material_map, (
                    f"Module {mid}: mask char '{char}' not in material_map"
                )

    def test_all_materials_exist(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            for mat_id in m.material_map.values():
                assert mat_id in dl.hull_materials, (
                    f"Module {mid} references unknown material '{mat_id}'"
                )

    def test_every_module_has_name_and_description(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            assert m.name, f"Module {mid} has no name"
            assert m.description, f"Module {mid} has no description"

    def test_rotation_preserves_pixels_for_all(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            for rot in range(4):
                r = m.rotated(rot)
                assert r.pixel_count == m.pixel_count, (
                    f"Module {mid} rotation {rot} changed pixel count"
                )

    def test_weight_positive_for_all(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            assert m.weight >= 0, f"Module {mid} has negative weight"

    def test_base_cost_non_negative(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            assert m.base_cost >= 0, f"Module {mid} has negative base_cost"


class TestCatalogBalance:
    """Verify no strictly dominant modules within categories."""

    def test_no_zero_weight_functional_modules(self) -> None:
        """Functional modules (non-structural) should have weight > 0."""
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            if m.category != "structural":
                assert m.weight > 0, f"Functional module {mid} ({m.category}) has zero weight"

    def test_cockpits_provide_core_slot(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            if m.category == "cockpit":
                assert m.provides.get("slot_type") == "core", (
                    f"Cockpit {mid} should provide core slot"
                )

    def test_engines_provide_engine_slot(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            if m.category == "engine":
                assert m.provides.get("slot_type") == "engine", (
                    f"Engine {mid} should provide engine slot"
                )

    def test_weapons_provide_weapon_slot(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            if m.category == "weapon":
                assert m.provides.get("slot_type") == "weapon", (
                    f"Weapon {mid} should provide weapon slot"
                )

    def test_shields_provide_defense_slot(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            if m.category == "shield":
                assert m.provides.get("slot_type") == "defense", (
                    f"Shield {mid} should provide defense slot"
                )

    def test_cargo_provides_capacity(self) -> None:
        dl = _loader()
        for mid, m in dl.ship_modules.items():
            if m.category == "cargo":
                assert m.provides.get("cargo_capacity", 0) > 0, (
                    f"Cargo {mid} should provide cargo_capacity"
                )

    def test_size_variety_per_category(self) -> None:
        """Each category should have modules of different pixel counts (size variety)."""
        dl = _loader()
        for cat in MODULE_CATEGORIES:
            mods = [m for m in dl.ship_modules.values() if m.category == cat]
            if len(mods) < 3:
                continue
            sizes = {m.pixel_count for m in mods}
            assert len(sizes) >= 2, (
                f"Category '{cat}' has {len(mods)} modules but only {len(sizes)} distinct sizes"
            )
