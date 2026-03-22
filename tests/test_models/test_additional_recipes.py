"""Tests for additional recipes (Phase B5)."""

import pytest

from spacegame.models.refining import Recipe, RefiningSession


class TestAdditionalRecipesExist:
    """All B5 recipes should load from data."""

    EXPECTED_IDS = {
        "refine_rare_ore", "reclaim_rare_parts", "synthesize_phase_lattice",
        "distill_refined_propellant", "forge_combat_alloy",
        "synthesize_neural_weave", "craft_emp_grenade", "craft_arc_emitter",
        "craft_shield_capacitor", "craft_deep_scan_probe",
        "craft_contraband_serum",
    }

    def test_all_new_recipes_exist(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe_ids = {r.id for r in dl.recipes}
        for rid in self.EXPECTED_IDS:
            assert rid in recipe_ids, f"Missing recipe: {rid}"

    def test_total_recipe_count(self) -> None:
        """Total recipes should be 32 (21 existing + 11 new)."""
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert len(dl.recipes) == 38


class TestNewCommodities:
    """New commodities for B5 recipes should exist."""

    NEW_COMMODITY_IDS = {
        "phase_lattice", "refined_propellant", "neural_weave",
        "crafted_arc_emitter", "crafted_emp_grenade",
        "crafted_shield_capacitor", "crafted_deep_scan_probe",
        "crafted_black_market_serum",
    }

    def test_new_commodities_exist(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        commodity_ids = {c.id for c in dl.get_all_commodities()}
        for cid in self.NEW_COMMODITY_IDS:
            assert cid in commodity_ids, f"Missing commodity: {cid}"

    def test_total_commodity_count(self) -> None:
        """Total commodities should be 61 (60 existing + 1 sealed_audit_chip)."""
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert len(dl.get_all_commodities()) == 61


class TestNewUpgrades:
    """New craft-gated upgrades for B5."""

    def test_shield_capacitor_upgrade(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert "shield_capacitor" in dl.upgrades
        up = dl.upgrades["shield_capacitor"]
        assert up.unlock_condition == "crafted_shield_capacitor"
        assert up.price == 0

    def test_arc_emitter_upgrade(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert "arc_emitter" in dl.upgrades
        up = dl.upgrades["arc_emitter"]
        assert up.unlock_condition == "crafted_arc_emitter"
        assert up.price == 0


class TestNewEquipment:
    """New ground equipment for B5."""

    def test_emp_grenade_exists(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert "emp_grenade" in dl.ground_equipment

    def test_deep_scan_probe_exists(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert "deep_scan_probe" in dl.ground_equipment


class TestDiscoverableRecipes:
    """Discoverable B5 recipes should have proper prerequisites."""

    def test_phase_lattice_discoverable(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe = next(r for r in dl.recipes if r.id == "synthesize_phase_lattice")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "purify_crystal"

    def test_arc_emitter_discoverable(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe = next(r for r in dl.recipes if r.id == "craft_arc_emitter")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "synthesize_phase_lattice"

    def test_neural_weave_discoverable(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe = next(r for r in dl.recipes if r.id == "synthesize_neural_weave")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "advanced_electronics"

    def test_shield_capacitor_discoverable(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe = next(r for r in dl.recipes if r.id == "craft_shield_capacitor")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "forge_alloy"


class TestCrossSystemRecipes:
    """Cross-system recipes should require diverse ingredient sources."""

    def test_combat_alloy_uses_three_sources(self) -> None:
        """forge_combat_alloy uses mining (iron_ore) + combat (combat_salvage) + salvage (salvaged_electronics)."""
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe = next(r for r in dl.recipes if r.id == "forge_combat_alloy")
        assert "iron_ore" in recipe.inputs
        assert "combat_salvage" in recipe.inputs
        assert "salvaged_electronics" in recipe.inputs

    def test_neural_weave_uses_four_inputs(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe = next(r for r in dl.recipes if r.id == "synthesize_neural_weave")
        assert len(recipe.inputs) == 4


class TestTradeGoodRecipes:
    """Trade good outputs should have market prices."""

    def test_refined_propellant_tradeable(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        c = next(c for c in dl.get_all_commodities() if c.id == "refined_propellant")
        assert c.base_price > 0

    def test_neural_weave_tradeable(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        c = next(c for c in dl.get_all_commodities() if c.id == "neural_weave")
        assert c.base_price > 0
