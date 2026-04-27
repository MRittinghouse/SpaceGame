"""CE-4a: encounter view skill_check resolution + requires_credits gating.

These tests build a real EncounterView with a fake pygame_gui manager
shim and exercise the resolve / branch path without rendering.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterRef,
    EncounterSkillCheck,
)
from spacegame.models.mission import MissionReward
from spacegame.models.social import SocialManager
from spacegame.views.encounter_view import EncounterPhase, EncounterView


def _init_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _ui_manager() -> pygame_gui.UIManager:
    _init_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


class _FakePlayer:
    """Minimal player shim sufficient for EncounterView in tests."""

    def __init__(self, credits: int = 1000) -> None:
        self.credits = credits
        self.dialogue_flags: dict[str, bool] = {}


def _make_encounter_def(choices: list[EncounterChoice]) -> EncounterDefinition:
    return EncounterDefinition(
        id="ce4_test",
        encounter_type="ransom_demand",
        name="Test Ransom",
        description="Pay or fight.",
        choices=choices,
    )


def _make_view(
    choices: list[EncounterChoice],
    player: _FakePlayer | None = None,
    social: SocialManager | None = None,
) -> EncounterView:
    return EncounterView(
        ui_manager=_ui_manager(),
        encounter_def=_make_encounter_def(choices),
        encounter_ref=EncounterRef(enemy_template_ids=[], encounter_seed=42),
        player=player,
        social_manager=social,
    )


# ---------------------------------------------------------------------------
# Skill check resolution
# ---------------------------------------------------------------------------


class TestSkillCheckResolution:
    def test_passing_check_uses_success_outcome(self) -> None:
        social = SocialManager()
        # Persuasion 5 vs difficulty 3 → pass
        social._skills["persuasion"].level = 5

        success = EncounterOutcome(description="They back off.", rewards=[])
        failure = EncounterOutcome(description="They open fire.", rewards=[], leads_to_combat=True)
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=success,
            skill_check=EncounterSkillCheck("persuasion", 3, set_flag_on_success="ce4_pass"),
            failure_outcome=failure,
        )
        player = _FakePlayer()
        view = _make_view([choice], player=player, social=social)
        view.on_enter()
        view._select_choice(0)
        assert view.chosen_outcome is not None
        assert view.chosen_outcome.description == "They back off."
        assert view.pending_combat is False
        assert player.dialogue_flags.get("ce4_pass") is True
        view.on_exit()

    def test_failing_check_uses_failure_outcome(self) -> None:
        social = SocialManager()
        # Persuasion 0 vs difficulty 3 → fail
        success = EncounterOutcome(description="ok", rewards=[])
        failure = EncounterOutcome(description="They open fire.", rewards=[], leads_to_combat=True)
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=success,
            skill_check=EncounterSkillCheck("persuasion", 3, set_flag_on_failure="ce4_fail"),
            failure_outcome=failure,
        )
        player = _FakePlayer()
        view = _make_view([choice], player=player, social=social)
        view.on_enter()
        view._select_choice(0)
        assert view.chosen_outcome is not None
        assert view.chosen_outcome.description == "They open fire."
        assert view.pending_combat is True
        assert player.dialogue_flags.get("ce4_fail") is True
        view.on_exit()

    def test_failure_falls_back_to_outcome_when_no_failure_outcome(self) -> None:
        """Authoring shorthand: if no failure_outcome, the same outcome
        applies regardless of pass/fail (the skill check is purely flag /
        XP texture)."""
        social = SocialManager()
        outcome = EncounterOutcome(description="Whatever.", rewards=[])
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=outcome,
            skill_check=EncounterSkillCheck("persuasion", 5),
        )
        view = _make_view([choice], player=_FakePlayer(), social=social)
        view.on_enter()
        view._select_choice(0)
        assert view.chosen_outcome.description == "Whatever."
        view.on_exit()


# ---------------------------------------------------------------------------
# requires_credits gating
# ---------------------------------------------------------------------------


class TestRequiresCredits:
    def test_button_disabled_when_player_cannot_afford(self) -> None:
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=500,
        )
        view = _make_view([choice], player=_FakePlayer(credits=100))
        view.on_enter()
        # Button gets disabled when affordability check fails
        assert view.choice_buttons[0].is_enabled is False
        view.on_exit()

    def test_button_enabled_when_player_can_afford(self) -> None:
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=200,
        )
        view = _make_view([choice], player=_FakePlayer(credits=1000))
        view.on_enter()
        assert view.choice_buttons[0].is_enabled is True
        view.on_exit()

    def test_requires_credits_appended_as_deduct_reward(self) -> None:
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(
                description="They take the credits.",
                rewards=[MissionReward("xp", 5)],
            ),
            requires_credits=200,
        )
        view = _make_view([choice], player=_FakePlayer(credits=1000))
        view.on_enter()
        view._select_choice(0)
        deductions = [r for r in view.chosen_outcome.rewards if r.reward_type == "deduct_credits"]
        assert len(deductions) == 1
        assert deductions[0].amount == 200
        view.on_exit()


# ---------------------------------------------------------------------------
# Skill check chip rendering
# ---------------------------------------------------------------------------


class TestSkillCheckChip:
    def test_button_label_includes_pass_marker(self) -> None:
        social = SocialManager()
        social._skills["persuasion"].level = 5
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            skill_check=EncounterSkillCheck("persuasion", 3),
        )
        view = _make_view([choice], player=_FakePlayer(), social=social)
        view.on_enter()
        text = view.choice_buttons[0].text
        assert "Persuasion 3" in text
        assert "PASS" in text
        view.on_exit()

    def test_button_label_includes_fail_marker(self) -> None:
        social = SocialManager()
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            skill_check=EncounterSkillCheck("persuasion", 5),
        )
        view = _make_view([choice], player=_FakePlayer(), social=social)
        view.on_enter()
        text = view.choice_buttons[0].text
        assert "FAIL" in text
        view.on_exit()
