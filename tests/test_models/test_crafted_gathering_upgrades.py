"""Tests for crafted gathering upgrades (Tasks 54-56).

Verifies all 6 new crafted gathering upgrades load correctly with
proper recipes, commodities, and craft-gated upgrades.
"""

import pytest

from spacegame.data_loader import get_data_loader


def _load() -> object:
    dl = get_data_loader()
    dl.load_all()
    return dl


class TestCraftedMiningUpgrades:
    """Task 54: Resonant Drill Array + Seismic Bore Engine."""

    def test_resonant_drill_recipe_exists(self) -> None:
        dl = _load()
        recipe_ids = {r.id for r in dl.recipes}
        assert "craft_resonant_drill" in recipe_ids

    def test_resonant_drill_recipe_inputs(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_resonant_drill")
        assert "alloy_composite" in recipe.inputs
        assert "flux_catalyst" in recipe.inputs
        assert "common_metals" in recipe.inputs

    def test_resonant_drill_discoverable(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_resonant_drill")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "forge_alloy"
        assert recipe.schematic_cost == 3

    def test_resonant_drill_commodity_exists(self) -> None:
        dl = _load()
        commodity_ids = {c.id for c in dl.get_all_commodities()}
        assert "crafted_resonant_drill" in commodity_ids

    def test_resonant_drill_upgrade_exists(self) -> None:
        dl = _load()
        assert "resonant_drill" in dl.upgrades
        up = dl.upgrades["resonant_drill"]
        assert up.unlock_condition == "crafted_resonant_drill"
        assert up.price == 0
        assert up.bonus_type == "drill_speed_bonus"
        assert up.bonus_value == pytest.approx(0.30)

    def test_seismic_bore_recipe_exists(self) -> None:
        dl = _load()
        recipe_ids = {r.id for r in dl.recipes}
        assert "craft_seismic_bore" in recipe_ids

    def test_seismic_bore_chain_recipe(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_seismic_bore")
        assert "crafted_resonant_drill" in recipe.inputs
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "craft_resonant_drill"
        assert recipe.schematic_cost == 5

    def test_seismic_bore_upgrade_exists(self) -> None:
        dl = _load()
        assert "seismic_bore" in dl.upgrades
        up = dl.upgrades["seismic_bore"]
        assert up.unlock_condition == "crafted_seismic_bore"
        assert up.price == 0
        assert up.bonus_type == "drill_speed_bonus"
        assert up.bonus_value == pytest.approx(0.40)


class TestCraftedSalvageUpgrades:
    """Task 55: Precision Extractor Array + Quantum Salvage Suite."""

    def test_precision_extractor_recipe_exists(self) -> None:
        dl = _load()
        recipe_ids = {r.id for r in dl.recipes}
        assert "craft_precision_extractor" in recipe_ids

    def test_precision_extractor_inputs(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_precision_extractor")
        assert "electronics" in recipe.inputs
        assert "charged_filament" in recipe.inputs
        assert "alloy_composite" in recipe.inputs

    def test_precision_extractor_discoverable(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_precision_extractor")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "advanced_electronics"
        assert recipe.schematic_cost == 3

    def test_precision_extractor_upgrade_exists(self) -> None:
        dl = _load()
        assert "precision_extractor" in dl.upgrades
        up = dl.upgrades["precision_extractor"]
        assert up.unlock_condition == "crafted_precision_extractor"
        assert up.price == 0
        assert up.bonus_type == "salvage_yield_bonus"

    def test_quantum_salvage_chain_recipe(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_quantum_salvage")
        assert "crafted_precision_extractor" in recipe.inputs
        assert "phase_lattice" in recipe.inputs
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "craft_precision_extractor"
        assert recipe.schematic_cost == 5

    def test_quantum_salvage_upgrade_exists(self) -> None:
        dl = _load()
        assert "quantum_salvage" in dl.upgrades
        up = dl.upgrades["quantum_salvage"]
        assert up.unlock_condition == "crafted_quantum_salvage"
        assert up.price == 0
        assert up.bonus_type == "salvage_yield_bonus"
        assert up.bonus_value == pytest.approx(0.35)


class TestCraftedRefiningUpgrades:
    """Task 56: Catalyst Forge Module + Stellarium Crucible."""

    def test_catalyst_forge_recipe_exists(self) -> None:
        dl = _load()
        recipe_ids = {r.id for r in dl.recipes}
        assert "craft_catalyst_forge" in recipe_ids

    def test_catalyst_forge_inputs(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_catalyst_forge")
        assert "alloy_composite" in recipe.inputs
        assert "flux_catalyst" in recipe.inputs
        assert "charged_filament" in recipe.inputs
        assert "electronics" in recipe.inputs

    def test_catalyst_forge_discoverable(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_catalyst_forge")
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "forge_alloy"
        assert recipe.schematic_cost == 3

    def test_catalyst_forge_upgrade_exists(self) -> None:
        dl = _load()
        assert "catalyst_forge" in dl.upgrades
        up = dl.upgrades["catalyst_forge"]
        assert up.unlock_condition == "crafted_catalyst_forge"
        assert up.price == 0
        assert up.bonus_type == "refining_yield_bonus"
        assert up.bonus_value == pytest.approx(0.15)

    def test_stellarium_crucible_chain_recipe(self) -> None:
        dl = _load()
        recipe = next(r for r in dl.recipes if r.id == "craft_stellarium_crucible")
        assert "crafted_catalyst_forge" in recipe.inputs
        assert "stellarium_ingot" in recipe.inputs
        assert recipe.discoverable is True
        assert recipe.discovery_prerequisite == "craft_catalyst_forge"
        assert recipe.schematic_cost == 5

    def test_stellarium_crucible_upgrade_exists(self) -> None:
        dl = _load()
        assert "stellarium_crucible" in dl.upgrades
        up = dl.upgrades["stellarium_crucible"]
        assert up.unlock_condition == "crafted_stellarium_crucible"
        assert up.price == 0
        assert up.bonus_type == "refining_yield_bonus"
        assert up.bonus_value == pytest.approx(0.25)


class TestTotalCounts:
    """Verify total counts after adding all gathering upgrades."""

    def test_total_recipe_count(self) -> None:
        """32 existing + 6 new = 38 recipes."""
        dl = _load()
        assert len(dl.recipes) == 38

    def test_total_commodity_count(self) -> None:
        """60 existing + sealed_audit_chip + SA-P3 (fresh_water, hydroponics_yield) = 63."""
        dl = _load()
        assert len(dl.get_all_commodities()) == 63

    def test_total_upgrade_count(self) -> None:
        """85 existing + 27 Phase 12B defense/utility = 112 upgrades."""
        dl = _load()
        assert len(dl.upgrades) == 112
