"""Encounter choice resolution and outcome application (SP3 spec 6.1)."""

from __future__ import annotations

from spacegame.models.encounter import (
    EncounterChoice,
    EncounterOutcome,
    EncounterSkillCheck,
    apply_encounter_outcome,
    resolve_choice_outcome,
)
from spacegame.models.mission import MissionReward
from tests.test_scenarios._helpers import fresh_player


def _choice(*, failure: bool = False, requires: int = 0, check: bool = False) -> EncounterChoice:
    return EncounterChoice(
        id="c",
        label="C",
        description="",
        outcome=EncounterOutcome(
            "ok",
            [MissionReward("deduct_credits", -1), MissionReward("xp", 5)],
            True,
            ["pirate_scout"],
        ),
        skill_check=EncounterSkillCheck("persuasion", 3) if check else None,
        failure_outcome=EncounterOutcome("bad", [MissionReward("credits", 1)]) if failure else None,
        requires_credits=requires,
    )


class TestResolve:
    def test_sentinel_takes_the_shakedown_demand(self) -> None:
        out = resolve_choice_outcome(_choice(), shakedown_demand=120, skill_check_passed=True)
        assert [(r.reward_type, r.amount) for r in out.rewards] == [
            ("deduct_credits", 120),
            ("xp", 5),
        ]
        assert out.enemy_template_ids == ["pirate_scout"]

    def test_failed_check_takes_the_failure_outcome(self) -> None:
        choice = _choice(failure=True, check=True)
        assert resolve_choice_outcome(choice, 0, skill_check_passed=False).description == "bad"
        assert resolve_choice_outcome(choice, 0, skill_check_passed=True).description == "ok"

    def test_requires_credits_becomes_a_deduction_when_none_exists(self) -> None:
        choice = EncounterChoice(
            "c", "C", "", EncounterOutcome("ok", [MissionReward("xp", 5)]), requires_credits=40
        )
        out = resolve_choice_outcome(choice, 0, skill_check_passed=True)
        assert (out.rewards[0].reward_type, out.rewards[0].amount) == ("deduct_credits", 40)


class TestApply:
    def test_rewards_apply_in_order(self) -> None:
        player = fresh_player(credits=100)
        outcome = EncounterOutcome(
            "x",
            [
                MissionReward("credits", 50),
                MissionReward("deduct_credits", 500),  # unaffordable: waived
                MissionReward("set_flag", 0, "met_them"),
                MissionReward("add_criminal_heat", 3),
                MissionReward("bounty_immunity", 4),
            ],
        )
        effects = apply_encounter_outcome(player, outcome)
        assert player.credits == 150
        assert player.max_credits_held >= 150, "credits go through add_credits (ruling P3)"
        assert player.dialogue_flags["met_them"] is True
        assert effects.flags_set == ["met_them"]
        assert effects.smuggling_caught is True
        assert effects.bounty_immunity_days == 4
        assert player.encounters_survived == 1
