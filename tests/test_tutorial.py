"""Tests for tutorial system: progression, skip, reset, serialization, mini-game hints."""

from spacegame.tutorial_manager import TutorialManager, TUTORIAL_STEPS, MINIGAME_HINTS


class TestTutorialProgression:
    """Test step progression through the tutorial."""

    def test_initial_state(self) -> None:
        """Tutorial should start inactive."""
        tm = TutorialManager()
        assert tm.current_step == 0
        assert not tm.completed
        assert not tm.skipped
        assert not tm.active

    def test_reset_activates_tutorial(self) -> None:
        """reset_tutorial() should activate the tutorial."""
        tm = TutorialManager()
        tm.reset_tutorial()
        assert tm.active
        assert tm.current_step == 0
        assert not tm.completed
        assert not tm.skipped

    def test_step_progression(self) -> None:
        """Should advance through all 5 steps to completion."""
        tm = TutorialManager()
        tm.reset_tutorial()

        for i in range(len(TUTORIAL_STEPS)):
            assert tm.current_step == i, f"Should be at step {i}"
            assert not tm.completed
            step = tm.start_step()
            assert step is not None
            assert step["id"] == i
            tm.advance_step()

        assert tm.completed, "Tutorial should be completed after all steps"

    def test_advance_past_end_completes(self) -> None:
        """Advancing past the last step should mark completed."""
        tm = TutorialManager()
        tm.reset_tutorial()

        for _ in range(len(TUTORIAL_STEPS)):
            tm.start_step()
            tm.advance_step()

        assert tm.completed
        result = tm.advance_step()
        assert result is None

    def test_should_show_step_matching_trigger(self) -> None:
        """should_show_step returns True for matching trigger."""
        tm = TutorialManager()
        tm.reset_tutorial()
        assert tm.should_show_step("galaxy_map")
        assert not tm.should_show_step("trading")

    def test_should_show_step_not_while_showing(self) -> None:
        """should_show_step returns False if already showing."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.start_step()
        assert not tm.should_show_step("galaxy_map")


class TestTutorialSkip:
    """Test skip functionality."""

    def test_skip_stops_tutorial(self) -> None:
        """Skipping should stop the tutorial."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.start_step()
        tm.skip_tutorial()

        assert tm.skipped
        assert not tm.is_showing()

    def test_no_steps_after_skip(self) -> None:
        """No steps should show after skip."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.skip_tutorial()

        assert not tm.should_show_step("galaxy_map")
        assert not tm.should_show_step("trading")
        result = tm.start_step()
        assert result is None


class TestTutorialReset:
    """Test reset for replay."""

    def test_reset_after_completion(self) -> None:
        """Reset should allow replaying after completion."""
        tm = TutorialManager()
        tm.reset_tutorial()

        # Complete tutorial
        for _ in range(len(TUTORIAL_STEPS)):
            tm.start_step()
            tm.advance_step()

        assert tm.completed

        # Reset
        tm.reset_tutorial()
        assert not tm.completed
        assert not tm.skipped
        assert tm.current_step == 0
        assert tm.active

    def test_reset_after_skip(self) -> None:
        """Reset should allow replaying after skip."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.skip_tutorial()
        assert tm.skipped

        tm.reset_tutorial()
        assert not tm.skipped
        assert tm.current_step == 0
        assert tm.active


class TestTutorialSerialization:
    """Test serialization round-trip."""

    def test_roundtrip_fresh(self) -> None:
        """Fresh tutorial should round-trip correctly."""
        tm = TutorialManager()
        data = tm.to_dict()
        restored = TutorialManager.from_dict(data)

        assert restored.current_step == 0
        assert not restored.completed
        assert not restored.skipped

    def test_roundtrip_midway(self) -> None:
        """Tutorial partway through should round-trip correctly."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.start_step()
        tm.advance_step()
        tm.start_step()
        tm.advance_step()

        data = tm.to_dict()
        restored = TutorialManager.from_dict(data)

        assert restored.current_step == 2
        assert not restored.completed
        assert restored.active

    def test_roundtrip_completed(self) -> None:
        """Completed tutorial should round-trip correctly."""
        tm = TutorialManager()
        tm.reset_tutorial()
        for _ in range(len(TUTORIAL_STEPS)):
            tm.start_step()
            tm.advance_step()

        data = tm.to_dict()
        restored = TutorialManager.from_dict(data)

        assert restored.completed
        assert restored.current_step == len(TUTORIAL_STEPS)

    def test_roundtrip_skipped(self) -> None:
        """Skipped tutorial should round-trip correctly."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.skip_tutorial()

        data = tm.to_dict()
        restored = TutorialManager.from_dict(data)

        assert restored.skipped

    def test_roundtrip_hints_dismissed(self) -> None:
        """Dismissed hints should round-trip correctly."""
        tm = TutorialManager()
        tm.dismiss_hint("mining_hint")
        tm.dismiss_hint("trading_hint")

        data = tm.to_dict()
        restored = TutorialManager.from_dict(data)

        assert "mining_hint" in restored.hints_dismissed
        assert "trading_hint" in restored.hints_dismissed


class TestHintsDismissed:
    """Test hints_dismissed tracking."""

    def test_dismiss_hint(self) -> None:
        """Dismissing a hint should add it to the set."""
        tm = TutorialManager()
        assert len(tm.hints_dismissed) == 0

        tm.dismiss_hint("test_hint")
        assert "test_hint" in tm.hints_dismissed

    def test_dismiss_same_hint_twice(self) -> None:
        """Dismissing same hint twice should not duplicate."""
        tm = TutorialManager()
        tm.dismiss_hint("test_hint")
        tm.dismiss_hint("test_hint")
        assert len(tm.hints_dismissed) == 1


class TestMinigameHints:
    """Tests for per-mini-game contextual hints."""

    def test_minigame_hints_defined(self) -> None:
        """All three mini-game hints should be defined."""
        assert "mining" in MINIGAME_HINTS
        assert "salvage" in MINIGAME_HINTS
        assert "refining" in MINIGAME_HINTS

    def test_hints_have_title_and_description(self) -> None:
        """Each hint should have title and description."""
        for hint_id, hint in MINIGAME_HINTS.items():
            assert "title" in hint, f"{hint_id} missing title"
            assert "description" in hint, f"{hint_id} missing description"
            assert len(hint["title"]) > 0
            assert len(hint["description"]) > 0

    def test_should_show_hint_first_time(self) -> None:
        """Hint should show when not yet dismissed."""
        tm = TutorialManager()
        assert tm.should_show_hint("mining")
        assert tm.should_show_hint("salvage")
        assert tm.should_show_hint("refining")

    def test_should_not_show_hint_after_dismiss(self) -> None:
        """Hint should not show after being dismissed."""
        tm = TutorialManager()
        tm.dismiss_hint("mining")
        assert not tm.should_show_hint("mining")
        # Other hints still show
        assert tm.should_show_hint("salvage")

    def test_should_not_show_unknown_hint(self) -> None:
        """Unknown hint IDs should return False."""
        tm = TutorialManager()
        assert not tm.should_show_hint("nonexistent")

    def test_get_hint_returns_data(self) -> None:
        """get_hint should return hint dict for known IDs."""
        tm = TutorialManager()
        hint = tm.get_hint("mining")
        assert hint is not None
        assert hint["title"] == "Asteroid Mining"

    def test_get_hint_unknown_returns_none(self) -> None:
        """get_hint should return None for unknown IDs."""
        tm = TutorialManager()
        assert tm.get_hint("nonexistent") is None

    def test_hints_persist_across_serialization(self) -> None:
        """Dismissed hints should survive save/load."""
        tm = TutorialManager()
        tm.dismiss_hint("mining")
        tm.dismiss_hint("salvage")

        data = tm.to_dict()
        restored = TutorialManager.from_dict(data)

        assert not restored.should_show_hint("mining")
        assert not restored.should_show_hint("salvage")
        assert restored.should_show_hint("refining")

    def test_hints_independent_of_tutorial(self) -> None:
        """Hints should work even when tutorial is completed or skipped."""
        tm = TutorialManager()
        tm.reset_tutorial()
        tm.skip_tutorial()

        # Hints should still show despite tutorial being skipped
        assert tm.should_show_hint("mining")

    def test_hints_independent_of_tutorial_inactive(self) -> None:
        """Hints should work even when tutorial was never activated."""
        tm = TutorialManager()
        assert not tm.active
        assert tm.should_show_hint("mining")
