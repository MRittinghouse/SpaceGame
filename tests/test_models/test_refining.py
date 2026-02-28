"""
Tests for the refining system models.
"""

import time
import pytest
from spacegame.models.refining import (
    Recipe,
    ActiveJob,
    RefiningSession,
    RefiningResult,
)


class TestRecipe:
    """Tests for Recipe."""

    def test_recipe_creation(self):
        recipe = Recipe(
            id="smelt_iron",
            name="Smelt Iron",
            description="Convert raw ore into common metals",
            inputs={"raw_ore": 10},
            outputs={"common_metals": 2},
            processing_time=5.0,
            location_ids=["forgeworks"],
        )
        assert recipe.id == "smelt_iron"
        assert recipe.processing_time == 5.0

    def test_can_craft(self):
        recipe = Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 10, "iron_ore": 5},
            outputs={"common_metals": 2},
            processing_time=5.0,
            location_ids=["test"],
        )
        assert recipe.can_craft({"raw_ore": 10, "iron_ore": 5})
        assert recipe.can_craft({"raw_ore": 20, "iron_ore": 10})
        assert not recipe.can_craft({"raw_ore": 5, "iron_ore": 5})
        assert not recipe.can_craft({})

    def test_get_missing_inputs(self):
        recipe = Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 10, "iron_ore": 5},
            outputs={"common_metals": 2},
            processing_time=5.0,
            location_ids=["test"],
        )
        missing = recipe.get_missing_inputs({"raw_ore": 3})
        assert missing["raw_ore"] == 7
        assert missing["iron_ore"] == 5


class TestRefiningSession:
    """Tests for RefiningSession."""

    def _make_recipe(
        self, recipe_id="test", inputs=None, outputs=None, processing_time=0.1, location="test"
    ):
        return Recipe(
            id=recipe_id,
            name=f"Test Recipe {recipe_id}",
            description="Test",
            inputs=inputs or {"raw_ore": 5},
            outputs=outputs or {"common_metals": 1},
            processing_time=processing_time,
            location_ids=[location],
        )

    def test_session_creation(self):
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        assert len(session.available_recipes) == 1
        assert session.get_queue_size() == 0

    def test_filters_by_location(self):
        recipe1 = self._make_recipe(recipe_id="r1", location="forgeworks")
        recipe2 = self._make_recipe(recipe_id="r2", location="axiom_labs")
        session = RefiningSession([recipe1, recipe2], "forgeworks")
        assert len(session.available_recipes) == 1
        assert session.available_recipes[0].id == "r1"

    def test_start_job(self):
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inventory = {"raw_ore": 10}
        success, msg = session.start_job(recipe, inventory)
        assert success
        assert session.get_queue_size() == 1
        assert inventory["raw_ore"] == 5  # Consumed 5

    def test_start_job_insufficient_materials(self):
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inventory = {"raw_ore": 2}
        success, msg = session.start_job(recipe, inventory)
        assert not success
        assert "Missing" in msg

    def test_queue_full(self):
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inventory = {"raw_ore": 100}
        for _ in range(5):
            session.start_job(recipe, inventory)
        success, msg = session.start_job(recipe, inventory)
        assert not success
        assert "full" in msg.lower()

    def test_job_completion(self):
        recipe = self._make_recipe(processing_time=0.01)
        session = RefiningSession([recipe], "test")
        inventory = {"raw_ore": 10}
        session.start_job(recipe, inventory)
        # Wait for job to complete
        time.sleep(0.05)
        results = session.update(0.1)
        assert len(results) == 1
        assert results[0].recipe_id == "test"
        assert results[0].outputs["common_metals"] == 1
        assert session.get_queue_size() == 0

    def test_get_available_recipes(self):
        recipe1 = self._make_recipe(recipe_id="r1", inputs={"raw_ore": 5})
        recipe2 = self._make_recipe(recipe_id="r2", inputs={"iron_ore": 5})
        session = RefiningSession([recipe1, recipe2], "test")
        inventory = {"raw_ore": 10}
        available = session.get_available_recipes(inventory)
        assert len(available) == 1
        assert available[0].id == "r1"

    def test_skill_gated_recipe(self):
        recipe = self._make_recipe()
        recipe.requires_skill = "refining_knowledge"
        session = RefiningSession([recipe], "test")
        inventory = {"raw_ore": 10}

        # Without skill
        available = session.get_available_recipes(inventory)
        assert len(available) == 0

        # With skill
        available = session.get_available_recipes(
            inventory, unlocked_skills={"refining_knowledge": True}
        )
        assert len(available) == 1
