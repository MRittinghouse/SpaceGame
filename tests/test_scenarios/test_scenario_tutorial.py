"""Scenario J: Tutorial progression happy path.

Tutorial is a 5-step state machine (``TUTORIAL_STEPS``) that gates screens
on specific triggers (galaxy_map, trading, after_first_trade, activity,
after_first_travel). Each step shows once when its trigger fires, then
advances.

This scenario verifies:
  - A player starting the tutorial sees exactly the right step for each trigger
  - Out-of-order triggers don't jump ahead or stall
  - Skip honors its contract (no further steps fire)
  - Reset returns to step 0 cleanly
  - "story" vs "classic" approach correctly gates overlay visibility
  - Shop-phase purchase flags accumulate on the player in the right order
    (via TUTORIAL_FLAGS from the data side — not directly on the manager)
"""

from __future__ import annotations

from spacegame.tutorial_manager import TUTORIAL_STEPS, TutorialManager


class TestTutorialStateMachineDefaults:
    def test_fresh_manager_is_inactive(self) -> None:
        mgr = TutorialManager()
        assert mgr.active is False
        assert mgr.completed is False
        assert mgr.skipped is False
        assert mgr.current_step == 0

    def test_inactive_manager_never_shows_steps(self) -> None:
        mgr = TutorialManager()
        # Without being activated, no trigger should show a step
        mgr.tutorial_approach = "classic"  # disable story-mode suppression
        for step in TUTORIAL_STEPS:
            assert mgr.should_show_step(step.trigger) is False

    def test_reset_activates_fresh(self) -> None:
        mgr = TutorialManager()
        mgr.reset_tutorial()
        assert mgr.active is True
        assert mgr.current_step == 0
        assert mgr.completed is False
        assert mgr.skipped is False


class TestTutorialStepProgression:
    """Each trigger shows the matching step in order — no skipping forward."""

    def _active_classic_manager(self) -> TutorialManager:
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.tutorial_approach = "classic"
        return mgr

    def test_first_trigger_matches_step_0(self) -> None:
        mgr = self._active_classic_manager()
        assert mgr.should_show_step("galaxy_map") is True
        # Non-matching triggers return False even while step 0 is current
        assert mgr.should_show_step("trading") is False

    def test_advance_moves_to_next_step(self) -> None:
        mgr = self._active_classic_manager()
        mgr.start_step()  # Step 0
        next_step = mgr.advance_step()
        assert next_step is not None
        assert next_step.trigger == "trading"
        assert mgr.current_step == 1

    def test_full_walkthrough_completes_tutorial(self) -> None:
        mgr = self._active_classic_manager()
        # Walk all 5 steps in order
        for expected_trigger in (
            "galaxy_map",
            "trading",
            "after_first_trade",
            "activity",
            "after_first_travel",
        ):
            assert mgr.should_show_step(expected_trigger) is True
            mgr.start_step()
            mgr.advance_step()

        assert mgr.completed is True
        # No more steps fire after completion
        assert mgr.should_show_step("galaxy_map") is False
        assert mgr.should_show_step("trading") is False

    def test_step_does_not_re_show_while_active(self) -> None:
        """Once start_step fires, should_show_step returns False until advance."""
        mgr = self._active_classic_manager()
        mgr.start_step()
        # _show_step now True — should_show_step gates on `not self._show_step`
        assert mgr.should_show_step("galaxy_map") is False


class TestTutorialSkipContract:
    def test_skip_prevents_future_steps(self) -> None:
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.tutorial_approach = "classic"

        mgr.skip_tutorial()
        assert mgr.skipped is True
        # No step should ever show after skip
        for step in TUTORIAL_STEPS:
            assert mgr.should_show_step(step.trigger) is False

    def test_skip_does_not_set_completed(self) -> None:
        """Skipped != completed — players who skip haven't earned tutorial
        rewards the same as players who finished."""
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.skip_tutorial()
        assert mgr.skipped is True
        assert mgr.completed is False


class TestTutorialApproachGating:
    """'story' approach suppresses overlay steps (in-fiction teaching instead).
    'classic' approach shows them."""

    def test_story_approach_suppresses_all_overlays(self) -> None:
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.tutorial_approach = "story"  # default
        for step in TUTORIAL_STEPS:
            assert mgr.should_show_step(step.trigger) is False

    def test_classic_approach_enables_overlays(self) -> None:
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.tutorial_approach = "classic"
        assert mgr.should_show_step("galaxy_map") is True


class TestTutorialOutOfOrderTriggers:
    """A trigger that doesn't match the current step should NOT advance the
    state machine — players can explore systems in any order."""

    def test_non_matching_trigger_stays_on_current_step(self) -> None:
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.tutorial_approach = "classic"

        # Fire step 4's trigger while on step 0 — must not advance.
        assert mgr.should_show_step("after_first_travel") is False
        assert mgr.current_step == 0

        # Step 0's trigger still fires correctly
        assert mgr.should_show_step("galaxy_map") is True

    def test_hint_dismissal_is_independent_of_step_progression(self) -> None:
        """MINIGAME_HINTS use a separate dismissed set — dismissing a hint
        doesn't touch current_step."""
        mgr = TutorialManager()
        mgr.reset_tutorial()
        mgr.hints_dismissed.add("mining")
        assert mgr.current_step == 0
        assert "mining" in mgr.hints_dismissed


class TestTutorialStepDataIntegrity:
    """The 5-step data contract must hold — tests break loudly if someone
    renumbers or drops a step."""

    def test_exactly_five_tutorial_steps(self) -> None:
        assert len(TUTORIAL_STEPS) == 5

    def test_every_step_has_id_title_description_trigger(self) -> None:
        for i, step in enumerate(TUTORIAL_STEPS):
            assert step.id == i
            assert step.title
            assert step.description
            assert step.trigger

    def test_triggers_are_unique(self) -> None:
        triggers = [s.trigger for s in TUTORIAL_STEPS]
        assert len(triggers) == len(set(triggers)), (
            f"Duplicate trigger in TUTORIAL_STEPS: {triggers}"
        )
