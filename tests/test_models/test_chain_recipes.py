"""Tests for chain recipes (Phase B3) — crafted outputs as recipe inputs."""

import pytest

from spacegame.models.refining import Recipe, RefiningSession


class TestChainRecipeData:
    """Chain recipes should load with correct properties."""

    def test_chain_recipes_exist(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        recipe_ids = {r.id for r in dl.recipes}
        assert "craft_titan_plating" in recipe_ids
        assert "craft_command_array" in recipe_ids
        assert "craft_nova_core" in recipe_ids

    def test_chain_recipes_are_tier_3(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        chain_ids = {"craft_titan_plating", "craft_command_array", "craft_nova_core"}
        for recipe in dl.recipes:
            if recipe.id in chain_ids:
                assert recipe.tier == 3, f"{recipe.id} should be tier 3"
                assert recipe.category == "upgrade", f"{recipe.id} should be upgrade category"
                assert recipe.discoverable is True, f"{recipe.id} should be discoverable"

    def test_chain_recipes_use_crafted_inputs(self) -> None:
        """Chain recipes must require at least one crafted output as input."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        chain_ids = {"craft_titan_plating", "craft_command_array", "craft_nova_core"}
        for recipe in dl.recipes:
            if recipe.id in chain_ids:
                crafted_inputs = [k for k in recipe.inputs if k.startswith("crafted_")]
                assert len(crafted_inputs) >= 1, (
                    f"{recipe.id} should use at least one crafted item as input"
                )


class TestChainRecipeCommodities:
    """Chain recipe output commodities should exist."""

    def test_chain_output_commodities_exist(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        commodity_ids = {c.id for c in dl.get_all_commodities()}
        assert "crafted_titan_plating" in commodity_ids
        assert "crafted_command_array" in commodity_ids
        assert "crafted_nova_core" in commodity_ids


class TestChainRecipeUpgrades:
    """Chain recipe craft-gated ship upgrades should exist."""

    def test_chain_upgrades_exist(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        upgrade_ids = set(dl.upgrades.keys())
        assert "titan_plating" in upgrade_ids
        assert "command_array" in upgrade_ids
        assert "nova_core" in upgrade_ids

    def test_chain_upgrades_are_craft_gated(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for uid in ("titan_plating", "command_array", "nova_core"):
            upgrade = dl.upgrades[uid]
            assert upgrade.unlock_condition, f"{uid} should have unlock_condition"
            assert upgrade.unlock_condition.startswith("crafted_"), (
                f"{uid} unlock_condition should start with 'crafted_'"
            )
            assert upgrade.price == 0, f"{uid} should be free (crafted)"


class TestChainRecipeSession:
    """Chain recipes should work in RefiningSession like any other recipe."""

    def test_chain_recipe_craftable_with_ingredients(self) -> None:
        recipe = Recipe(
            id="craft_titan_plating",
            name="Forge Titan Plating",
            description="test",
            inputs={
                "crafted_reinforced_plating": 1,
                "crafted_plasma_conduit": 1,
                "stellarium_ingot": 1,
            },
            outputs={"crafted_titan_plating": 1},
            processing_time=45.0,
            location_ids=["forgeworks"],
            category="upgrade",
            tier=3,
        )
        inventory = {
            "crafted_reinforced_plating": 1,
            "crafted_plasma_conduit": 1,
            "stellarium_ingot": 1,
        }
        assert recipe.can_craft(inventory)

    def test_chain_recipe_missing_crafted_input(self) -> None:
        recipe = Recipe(
            id="craft_titan_plating",
            name="Forge Titan Plating",
            description="test",
            inputs={
                "crafted_reinforced_plating": 1,
                "crafted_plasma_conduit": 1,
                "stellarium_ingot": 1,
            },
            outputs={"crafted_titan_plating": 1},
            processing_time=45.0,
            location_ids=["forgeworks"],
            category="upgrade",
            tier=3,
        )
        inventory = {"crafted_reinforced_plating": 1, "stellarium_ingot": 1}
        assert not recipe.can_craft(inventory)
        missing = recipe.get_missing_inputs(inventory)
        assert missing == {"crafted_plasma_conduit": 1}

    def test_chain_recipe_discovery_prerequisite(self) -> None:
        """Chain recipes should have discovery prerequisites pointing to tier 2 recipes."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        chain_ids = {"craft_titan_plating", "craft_command_array", "craft_nova_core"}
        for recipe in dl.recipes:
            if recipe.id in chain_ids:
                assert recipe.discovery_prerequisite != "", (
                    f"{recipe.id} should have a discovery_prerequisite"
                )
