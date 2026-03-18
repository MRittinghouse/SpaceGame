"""Tests for black market crafting recipes (Phase B4)."""

import pytest

from spacegame.models.refining import Recipe, RefiningSession


class TestBlackMarketRecipeData:
    """Black market recipes should load with correct properties."""

    def test_black_market_recipes_exist(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        recipe_ids = {r.id for r in dl.recipes}
        assert "craft_adrenal_compound" in recipe_ids
        assert "craft_phantom_module" in recipe_ids
        assert "craft_fortified_stims" in recipe_ids

    def test_black_market_recipes_at_crimson_reach(self) -> None:
        """All black market recipes should be available at crimson_reach."""
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        bm_ids = {"craft_adrenal_compound", "craft_phantom_module", "craft_fortified_stims"}
        for recipe in dl.recipes:
            if recipe.id in bm_ids:
                assert "crimson_reach" in recipe.location_ids, (
                    f"{recipe.id} should be available at crimson_reach"
                )

    def test_black_market_recipes_use_illegal_inputs(self) -> None:
        """Each black market recipe should require at least one illegal commodity."""
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        illegal_commodities = {"combat_stims", "stolen_data", "restricted_tech"}
        bm_ids = {"craft_adrenal_compound", "craft_phantom_module", "craft_fortified_stims"}
        for recipe in dl.recipes:
            if recipe.id in bm_ids:
                illegal_inputs = set(recipe.inputs.keys()) & illegal_commodities
                assert len(illegal_inputs) >= 1, (
                    f"{recipe.id} should use at least one illegal commodity"
                )

    def test_black_market_recipes_tier_2(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        bm_ids = {"craft_adrenal_compound", "craft_phantom_module", "craft_fortified_stims"}
        for recipe in dl.recipes:
            if recipe.id in bm_ids:
                assert recipe.tier >= 2, f"{recipe.id} should be tier 2+"


class TestBlackMarketCommodities:
    """Black market recipe output commodities should exist."""

    def test_output_commodities_exist(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        commodity_ids = {c.id for c in dl.get_all_commodities()}
        assert "crafted_adrenal_compound" in commodity_ids
        assert "crafted_phantom_module" in commodity_ids
        assert "fortified_stims" in commodity_ids

    def test_fortified_stims_is_illegal(self) -> None:
        """Fortified stims should be illegal (contraband trade good)."""
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        for c in dl.get_all_commodities():
            if c.id == "fortified_stims":
                assert c.legality.value == "illegal"
                assert c.base_price > 0, "Trade good should have a market price"
                return
        pytest.fail("fortified_stims commodity not found")


class TestBlackMarketUpgrade:
    """Phantom module ship upgrade should exist."""

    def test_phantom_module_upgrade_exists(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert "phantom_module" in dl.upgrades

    def test_phantom_module_is_craft_gated(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        upgrade = dl.upgrades["phantom_module"]
        assert upgrade.unlock_condition == "crafted_phantom_module"
        assert upgrade.price == 0


class TestBlackMarketEquipment:
    """Adrenal compound ground equipment should exist."""

    def test_adrenal_compound_equipment_exists(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        assert "adrenal_compound" in dl.ground_equipment


class TestBlackMarketSessionFilter:
    """Black market recipes should only appear at correct locations."""

    def test_recipes_not_at_nexus(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        # All recipes discovered for this test
        all_ids = {r.id for r in dl.recipes}
        session = RefiningSession(dl.recipes, "nexus_prime", discovered_recipes=all_ids)
        available_ids = {r.id for r in session.available_recipes}
        assert "craft_adrenal_compound" not in available_ids
        assert "craft_phantom_module" not in available_ids
        assert "craft_fortified_stims" not in available_ids

    def test_recipes_at_crimson_reach(self) -> None:
        from spacegame.data_loader import get_data_loader
        dl = get_data_loader()
        dl.load_all()
        all_ids = {r.id for r in dl.recipes}
        session = RefiningSession(dl.recipes, "crimson_reach", discovered_recipes=all_ids)
        available_ids = {r.id for r in session.available_recipes}
        assert "craft_adrenal_compound" in available_ids
        assert "craft_phantom_module" in available_ids
        assert "craft_fortified_stims" in available_ids
