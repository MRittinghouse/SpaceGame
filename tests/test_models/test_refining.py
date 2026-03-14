"""
Tests for the refining system models.
"""

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
        """Job completes when update() accumulates enough dt."""
        recipe = self._make_recipe(processing_time=5.0)
        session = RefiningSession([recipe], "test")
        inventory = {"raw_ore": 10}
        session.start_job(recipe, inventory)
        # Not done yet
        results = session.update(3.0)
        assert len(results) == 0
        assert session.get_queue_size() == 1
        # Now complete
        results = session.update(3.0)
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


class TestDeltaTime:
    """Tests for delta-time based job progression."""

    def _make_recipe(self, processing_time=10.0):
        return Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 5},
            outputs={"common_metals": 1},
            processing_time=processing_time,
            location_ids=["test"],
        )

    def test_job_elapsed_time_accumulates(self):
        """ActiveJob.elapsed_time accumulates from advance() calls."""
        recipe = self._make_recipe(processing_time=10.0)
        job = ActiveJob(recipe=recipe, effective_time=10.0)
        assert job.elapsed_time == 0.0
        job.advance(1.0)
        assert job.elapsed_time == 1.0
        job.advance(2.5)
        assert job.elapsed_time == 3.5

    def test_job_progress_from_elapsed(self):
        """Progress is elapsed_time / effective_time."""
        recipe = self._make_recipe(processing_time=10.0)
        job = ActiveJob(recipe=recipe, effective_time=10.0)
        job.advance(5.0)
        assert job.progress == pytest.approx(0.5)

    def test_job_completes_at_effective_time(self):
        """Job is complete when elapsed >= effective_time."""
        recipe = self._make_recipe(processing_time=10.0)
        job = ActiveJob(recipe=recipe, effective_time=10.0)
        job.advance(9.9)
        assert not job.is_complete
        job.advance(0.2)
        assert job.is_complete

    def test_job_remaining_time(self):
        """remaining_time = effective_time - elapsed_time, min 0."""
        recipe = self._make_recipe(processing_time=10.0)
        job = ActiveJob(recipe=recipe, effective_time=10.0)
        job.advance(3.0)
        assert job.remaining_time == pytest.approx(7.0)
        job.advance(20.0)
        assert job.remaining_time == 0.0

    def test_update_advances_all_jobs(self):
        """session.update(dt) advances elapsed_time on all queued jobs."""
        recipe = self._make_recipe(processing_time=10.0)
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        session.start_job(recipe, inv)
        session.update(3.0)
        for job in session.job_queue:
            assert job.elapsed_time == pytest.approx(3.0)

    def test_update_completes_ready_jobs(self):
        """Jobs past effective_time are returned as results."""
        recipe = self._make_recipe(processing_time=5.0)
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(6.0)
        assert len(results) == 1
        assert results[0].recipe_id == "test"

    def test_update_removes_completed_jobs(self):
        """Completed jobs are removed from the queue."""
        recipe = self._make_recipe(processing_time=5.0)
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        assert session.get_queue_size() == 1
        session.update(6.0)
        assert session.get_queue_size() == 0

    def test_progress_clamped_at_one(self):
        """Progress never exceeds 1.0."""
        recipe = self._make_recipe(processing_time=5.0)
        job = ActiveJob(recipe=recipe, effective_time=5.0)
        job.advance(100.0)
        assert job.progress == 1.0


class TestSpeedAndYieldBonuses:
    """Tests for speed and yield bonus mechanics."""

    def _make_recipe(self, processing_time=10.0, outputs=None):
        return Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 5},
            outputs=outputs or {"common_metals": 1},
            processing_time=processing_time,
            location_ids=["test"],
        )

    def test_default_speed_bonus_zero(self):
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        assert session.speed_bonus == 0.0

    def test_default_yield_bonus_zero(self):
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        assert session.yield_bonus == 0.0

    def test_speed_bonus_reduces_effective_time(self):
        """30% speed bonus → effective_time = processing_time * 0.70."""
        recipe = self._make_recipe(processing_time=10.0)
        session = RefiningSession([recipe], "test", speed_bonus=0.30)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        job = session.job_queue[0]
        assert job.effective_time == pytest.approx(7.0)

    def test_speed_bonus_clamped_at_90_percent(self):
        """95% speed bonus → clamped to 90% → effective_time = processing_time * 0.10."""
        recipe = self._make_recipe(processing_time=10.0)
        session = RefiningSession([recipe], "test", speed_bonus=0.95)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        job = session.job_queue[0]
        assert job.effective_time == pytest.approx(1.0)

    def test_speed_bonus_applied_at_job_creation(self):
        """Speed bonus is baked into effective_time at start_job time."""
        recipe = self._make_recipe(processing_time=10.0)
        session = RefiningSession([recipe], "test", speed_bonus=0.50)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        job = session.job_queue[0]
        assert job.effective_time == pytest.approx(5.0)

    def test_yield_bonus_can_increase_output(self):
        """100% yield bonus → every output unit gets +1 (deterministic)."""
        recipe = self._make_recipe(outputs={"common_metals": 2})
        session = RefiningSession([recipe], "test", yield_bonus=1.0)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert len(results) == 1
        assert results[0].outputs["common_metals"] == 4  # 2 base + 2 bonus

    def test_yield_bonus_zero_no_extra(self):
        """0% yield bonus → outputs unchanged."""
        recipe = self._make_recipe(outputs={"common_metals": 2})
        session = RefiningSession([recipe], "test", yield_bonus=0.0)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert len(results) == 1
        assert results[0].outputs["common_metals"] == 2

    def test_yield_bonus_applied_per_unit(self):
        """Recipe outputs 3 units, 100% yield → 6 total."""
        recipe = self._make_recipe(outputs={"common_metals": 3})
        session = RefiningSession([recipe], "test", yield_bonus=1.0)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert results[0].outputs["common_metals"] == 6

    def test_total_refined_includes_bonus_yield(self):
        """Bonus yield is tracked in total_refined."""
        recipe = self._make_recipe(outputs={"common_metals": 2})
        session = RefiningSession([recipe], "test", yield_bonus=1.0)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        session.update(20.0)
        assert session.total_refined["common_metals"] == 4

    def test_result_outputs_include_bonus(self):
        """RefiningResult.outputs reflects bonus yield."""
        recipe = self._make_recipe(outputs={"common_metals": 1, "rare_metals": 1})
        session = RefiningSession([recipe], "test", yield_bonus=1.0)
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert results[0].outputs["common_metals"] == 2
        assert results[0].outputs["rare_metals"] == 2


class TestBatchQueuing:
    """Tests for batch queuing of refining jobs."""

    def _make_recipe(self, processing_time=10.0, inputs=None, outputs=None):
        return Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs=inputs or {"raw_ore": 5},
            outputs=outputs or {"common_metals": 1},
            processing_time=processing_time,
            location_ids=["test"],
        )

    def test_start_batch_queues_multiple(self):
        """Batch of 3 → 3 jobs in queue."""
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        success, msg = session.start_batch(recipe, inv, 3)
        assert success
        assert session.get_queue_size() == 3

    def test_start_batch_consumes_inputs(self):
        """3x recipe needing 5 ore → consumes 15."""
        recipe = self._make_recipe(inputs={"raw_ore": 5})
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 20}
        session.start_batch(recipe, inv, 3)
        assert inv["raw_ore"] == 5

    def test_start_batch_returns_count(self):
        """Success message includes count."""
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        success, msg = session.start_batch(recipe, inv, 3)
        assert success
        assert "3" in msg

    def test_start_batch_insufficient_materials(self):
        """Not enough for batch → fails, nothing consumed."""
        recipe = self._make_recipe(inputs={"raw_ore": 5})
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 10}  # Only enough for 2
        success, msg = session.start_batch(recipe, inv, 3)
        assert not success
        assert inv["raw_ore"] == 10  # Nothing consumed

    def test_start_batch_insufficient_slots(self):
        """Not enough queue slots → fails, nothing consumed."""
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 1000}
        # Fill 3 slots
        for _ in range(3):
            session.start_job(recipe, inv)
        # Try batch of 3 (only 2 slots left)
        success, msg = session.start_batch(recipe, inv, 3)
        assert not success
        assert session.get_queue_size() == 3  # Unchanged

    def test_start_batch_atomic_no_partial(self):
        """If batch can't fully fit, nothing is consumed."""
        recipe = self._make_recipe(inputs={"raw_ore": 5})
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        # Fill 4 slots
        for _ in range(4):
            session.start_job(recipe, inv)
        starting_ore = inv["raw_ore"]
        # Batch of 2 with only 1 slot left
        success, msg = session.start_batch(recipe, inv, 2)
        assert not success
        assert inv["raw_ore"] == starting_ore

    def test_start_batch_count_zero_fails(self):
        """Count of 0 is rejected."""
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        success, msg = session.start_batch(recipe, inv, 0)
        assert not success

    def test_start_batch_single_same_as_start_job(self):
        """Batch of 1 behaves like start_job."""
        recipe = self._make_recipe(inputs={"raw_ore": 5})
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 10}
        success, msg = session.start_batch(recipe, inv, 1)
        assert success
        assert session.get_queue_size() == 1
        assert inv["raw_ore"] == 5

    def test_batch_jobs_complete_individually(self):
        """Each batch job completes as its own result."""
        recipe = self._make_recipe(processing_time=5.0)
        session = RefiningSession([recipe], "test")
        inv = {"raw_ore": 100}
        session.start_batch(recipe, inv, 3)
        results = session.update(6.0)
        assert len(results) == 3  # All complete at same time

    def test_batch_with_speed_bonus(self):
        """All batch jobs get speed-adjusted effective_time."""
        recipe = self._make_recipe(processing_time=10.0)
        session = RefiningSession([recipe], "test", speed_bonus=0.50)
        inv = {"raw_ore": 100}
        session.start_batch(recipe, inv, 2)
        for job in session.job_queue:
            assert job.effective_time == pytest.approx(5.0)


class TestNewRecipes:
    """Tests for new recipes and commodities in data files."""

    def _get_data_loader(self):
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        return dl

    def test_alloy_composite_commodity_loaded(self):
        dl = self._get_data_loader()
        assert "alloy_composite" in dl.commodities
        c = dl.commodities["alloy_composite"]
        assert c.base_price == 280

    def test_purified_crystal_commodity_loaded(self):
        dl = self._get_data_loader()
        assert "purified_crystal" in dl.commodities
        c = dl.commodities["purified_crystal"]
        assert c.base_price == 400

    def test_forge_alloy_recipe_loaded(self):
        dl = self._get_data_loader()
        recipes_by_id = {r.id: r for r in dl.recipes}
        assert "forge_alloy" in recipes_by_id
        r = recipes_by_id["forge_alloy"]
        assert r.inputs == {"common_metals": 5, "rare_metals": 2}
        assert r.outputs == {"alloy_composite": 2}

    def test_purify_crystal_recipe_loaded(self):
        dl = self._get_data_loader()
        recipes_by_id = {r.id: r for r in dl.recipes}
        assert "purify_crystal" in recipes_by_id
        r = recipes_by_id["purify_crystal"]
        assert r.inputs == {"crystal_ore": 8}
        assert r.outputs == {"purified_crystal": 1}

    def test_advanced_electronics_recipe_loaded(self):
        dl = self._get_data_loader()
        recipes_by_id = {r.id: r for r in dl.recipes}
        assert "advanced_electronics" in recipes_by_id
        r = recipes_by_id["advanced_electronics"]
        assert r.outputs == {"electronics": 3}

    def test_new_recipes_require_refining_knowledge(self):
        dl = self._get_data_loader()
        recipes_by_id = {r.id: r for r in dl.recipes}
        for rid in ["forge_alloy", "purify_crystal", "advanced_electronics"]:
            assert recipes_by_id[rid].requires_skill == "refining_knowledge"

    def test_new_recipes_at_correct_locations(self):
        dl = self._get_data_loader()
        recipes_by_id = {r.id: r for r in dl.recipes}
        assert "forgeworks" in recipes_by_id["forge_alloy"].location_ids
        assert "axiom_labs" in recipes_by_id["purify_crystal"].location_ids
        assert "axiom_labs" in recipes_by_id["advanced_electronics"].location_ids
