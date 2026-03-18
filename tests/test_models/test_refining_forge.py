"""Tests for forge integration in the refining system."""

import pytest
from spacegame.models.refining import (
    Recipe,
    RefiningSession,
)
from spacegame.models.recipe_mastery import RecipeMasteryTracker, MASTERY_THRESHOLDS


class TestRecipeForgeFields:
    """Tests for new Recipe fields: category and tier."""

    def test_recipe_default_category(self) -> None:
        """Recipe with no category defaults to 'commodity'."""
        recipe = Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 5},
            outputs={"common_metals": 1},
            processing_time=5.0,
            location_ids=["test"],
        )
        assert recipe.category == "commodity"

    def test_recipe_with_category(self) -> None:
        """Recipe can be created with explicit category."""
        recipe = Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 5},
            outputs={"common_metals": 1},
            processing_time=5.0,
            location_ids=["test"],
            category="upgrade",
        )
        assert recipe.category == "upgrade"

    def test_recipe_default_tier(self) -> None:
        """Recipe with no tier defaults to 1."""
        recipe = Recipe(
            id="test",
            name="Test",
            description="Test",
            inputs={"raw_ore": 5},
            outputs={"common_metals": 1},
            processing_time=5.0,
            location_ids=["test"],
        )
        assert recipe.tier == 1


class TestRefiningSessionForgeIntegration:
    """Tests for forge-related RefiningSession features."""

    def _make_recipe(
        self,
        recipe_id: str = "test",
        inputs: dict[str, int] | None = None,
        outputs: dict[str, int] | None = None,
        processing_time: float = 10.0,
    ) -> Recipe:
        return Recipe(
            id=recipe_id,
            name=f"Test Recipe {recipe_id}",
            description="Test",
            inputs=inputs or {"raw_ore": 5},
            outputs=outputs or {"common_metals": 1},
            processing_time=processing_time,
            location_ids=["test"],
        )

    def test_session_queue_size_bonus(self) -> None:
        """Queue size bonus increases max queue beyond default 5."""
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test", queue_size_bonus=3)
        assert session.max_queue_size == 8
        inv = {"raw_ore": 1000}
        for _ in range(8):
            success, _ = session.start_job(recipe, inv)
            assert success
        # 9th should fail
        success, msg = session.start_job(recipe, inv)
        assert not success
        assert "full" in msg.lower()

    def test_session_forge_speed_bonus_applied(self) -> None:
        """Forge speed bonus stacks with skill speed bonus on effective time."""
        recipe = self._make_recipe(processing_time=10.0)
        session = RefiningSession(
            [recipe], "test", speed_bonus=0.20, forge_speed_bonus=0.10
        )
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        job = session.job_queue[0]
        # total speed = 0.20 + 0.10 = 0.30 -> effective = 10 * 0.70 = 7.0
        assert job.effective_time == pytest.approx(7.0)

    def test_session_mastery_speed_applied(self) -> None:
        """Mastery level 1+ reduces effective time by 10%."""
        recipe = self._make_recipe(processing_time=10.0)
        tracker = RecipeMasteryTracker()
        # Reach mastery level 1 (need 3 crafts)
        for _ in range(MASTERY_THRESHOLDS[0]):
            tracker.record_craft("test")
        assert tracker.get_mastery("test").mastery_level >= 1

        session = RefiningSession(
            [recipe], "test", speed_bonus=0.0, mastery_tracker=tracker
        )
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        job = session.job_queue[0]
        # mastery speed = 0.10 -> effective = 10 * (1.0 - 0.0 - 0.10) = 9.0
        assert job.effective_time == pytest.approx(9.0)

    def test_session_forge_yield_bonus(self) -> None:
        """Forge yield bonus stacks with skill yield bonus."""
        recipe = self._make_recipe(outputs={"common_metals": 2})
        # Using 100% yield bonuses for deterministic test
        session = RefiningSession(
            [recipe], "test", yield_bonus=1.0, forge_yield_bonus=1.0
        )
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert len(results) == 1
        # total yield bonus = 2.0, so each of 2 units gets +1 bonus each from
        # the per-unit roll, but yield_bonus caps effective probability at whatever
        # combined value is. With 2.0 combined, each unit produces +1 bonus.
        # Actually the roll is random.random() < combined_yield, so with 2.0
        # every roll succeeds -> 2 base + 2 bonus = 4
        assert results[0].outputs["common_metals"] == 4

    def test_session_mastery_yield_applied(self) -> None:
        """Mastery level 2+ adds +1 to each output commodity."""
        recipe = self._make_recipe(
            outputs={"common_metals": 2, "rare_metals": 1}
        )
        tracker = RecipeMasteryTracker()
        # Reach mastery level 2 (need 8 crafts)
        for _ in range(MASTERY_THRESHOLDS[1]):
            tracker.record_craft("test")
        assert tracker.get_mastery("test").mastery_level >= 2

        session = RefiningSession(
            [recipe], "test", yield_bonus=0.0, mastery_tracker=tracker
        )
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert len(results) == 1
        # Base 2 + mastery 1 = 3
        assert results[0].outputs["common_metals"] == 3
        # Base 1 + mastery 1 = 2
        assert results[0].outputs["rare_metals"] == 2

    def test_session_forge_tokens_in_result(self) -> None:
        """Completed job has forge_tokens_earned > 0."""
        recipe = self._make_recipe(
            processing_time=15.0, inputs={"raw_ore": 5, "iron_ore": 3}
        )
        tracker = RecipeMasteryTracker()
        session = RefiningSession(
            [recipe], "test", mastery_tracker=tracker
        )
        inv = {"raw_ore": 100, "iron_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(20.0)
        assert len(results) == 1
        assert results[0].forge_tokens_earned > 0

    def test_session_mastery_recorded_on_completion(self) -> None:
        """Mastery tracker gets record_craft called when job completes."""
        recipe = self._make_recipe()
        tracker = RecipeMasteryTracker()
        session = RefiningSession(
            [recipe], "test", mastery_tracker=tracker
        )
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        session.update(20.0)
        entry = tracker.get_mastery("test")
        assert entry.times_crafted == 1

    def test_session_backward_compat(self) -> None:
        """Session without mastery_tracker or forge bonuses works fine."""
        recipe = self._make_recipe(processing_time=5.0)
        session = RefiningSession([recipe], "test")
        assert session.max_queue_size == 5
        inv = {"raw_ore": 100}
        session.start_job(recipe, inv)
        results = session.update(10.0)
        assert len(results) == 1
        assert results[0].forge_tokens_earned == 0
        assert results[0].outputs["common_metals"] == 1

    def test_batch_uses_max_queue_size_with_bonus(self) -> None:
        """start_batch respects queue_size_bonus for slot calculation."""
        recipe = self._make_recipe()
        session = RefiningSession([recipe], "test", queue_size_bonus=2)
        inv = {"raw_ore": 1000}
        # Fill 5 slots
        for _ in range(5):
            session.start_job(recipe, inv)
        # Batch of 2 should work (7 total, max is 7)
        success, _ = session.start_batch(recipe, inv, 2)
        assert success
        assert session.get_queue_size() == 7
