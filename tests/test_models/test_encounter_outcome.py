"""Encounter choice resolution and outcome application (SP3 spec 6.1)."""

from __future__ import annotations

from spacegame.constants.flags import encounter_seen
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterSkillCheck,
    apply_encounter_outcome,
    mark_unique_encounter_seen,
    resolve_choice_outcome,
    resolve_encounter_skill_check,
)
from spacegame.models.mission import MissionReward
from spacegame.models.social import SocialManager
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


class TestResolveEncounterSkillCheck:
    def test_no_social_manager_returns_false_and_writes_no_flag(self) -> None:
        player = fresh_player()
        check = EncounterSkillCheck(
            "persuasion", 3, set_flag_on_success="ok", set_flag_on_failure="bad"
        )
        assert resolve_encounter_skill_check(check, None, player) is False
        assert player.dialogue_flags == {}

    def test_success_returns_true_and_writes_only_the_success_flag(self) -> None:
        player = fresh_player()
        social = SocialManager()
        social._skills["persuasion"]._level = 3
        check = EncounterSkillCheck(
            "persuasion", 1, set_flag_on_success="ok", set_flag_on_failure="bad"
        )
        assert resolve_encounter_skill_check(check, social, player) is True
        assert player.dialogue_flags.get("ok") is True
        assert "bad" not in player.dialogue_flags

    def test_failure_at_default_level_returns_false_and_writes_only_the_failure_flag(
        self,
    ) -> None:
        player = fresh_player()
        social = SocialManager()
        check = EncounterSkillCheck(
            "persuasion", 5, set_flag_on_success="ok", set_flag_on_failure="bad"
        )
        assert resolve_encounter_skill_check(check, social, player) is False
        assert player.dialogue_flags.get("bad") is True
        assert "ok" not in player.dialogue_flags

    def test_none_player_returns_the_check_result_without_raising(self) -> None:
        social = SocialManager()
        social._skills["persuasion"]._level = 3
        check = EncounterSkillCheck(
            "persuasion", 1, set_flag_on_success="ok", set_flag_on_failure="bad"
        )
        assert resolve_encounter_skill_check(check, social, None) is True


class TestMarkUniqueEncounterSeen:
    def _definition(self, *, unique: bool) -> EncounterDefinition:
        return EncounterDefinition(
            id="once_only",
            encounter_type="diplomatic",
            name="N",
            description="",
            choices=[],
            unique=unique,
        )

    def test_none_definition_returns_none(self) -> None:
        assert mark_unique_encounter_seen(fresh_player(), None) is None

    def test_non_unique_definition_returns_none_and_sets_no_flag(self) -> None:
        player = fresh_player()
        defn = self._definition(unique=False)
        assert mark_unique_encounter_seen(player, defn) is None
        assert encounter_seen(defn.id) not in player.dialogue_flags

    def test_unique_definition_sets_and_returns_the_seen_flag(self) -> None:
        player = fresh_player()
        defn = self._definition(unique=True)
        flag = mark_unique_encounter_seen(player, defn)
        assert flag == encounter_seen("once_only")
        assert player.dialogue_flags[flag] is True


class TestApplyEncounterOutcomeMore:
    def test_affordable_deduct_credits_lowers_credits(self) -> None:
        player = fresh_player(credits=100)
        outcome = EncounterOutcome("x", [MissionReward("deduct_credits", 40)])
        apply_encounter_outcome(player, outcome)
        assert player.credits == 60

    def test_xp_advances_progression_and_mirrors_add_xp_messages(self) -> None:
        player = fresh_player()
        expected_messages = fresh_player().progression.add_xp(600)
        outcome = EncounterOutcome("x", [MissionReward("xp", 600)])
        effects = apply_encounter_outcome(player, outcome)
        assert player.progression.xp == 600
        assert effects.xp_messages == expected_messages
        assert effects.xp_messages != []

    def test_modify_reputation_without_hook_changes_player_reputation(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome("x", [MissionReward("modify_reputation", 10, "commerce_guild")])
        apply_encounter_outcome(player, outcome)
        assert player.faction_reputation.get("commerce_guild") == 10

    def test_modify_reputation_with_hook_delegates_and_leaves_player_untouched(self) -> None:
        player = fresh_player()
        calls: list[tuple[str, int]] = []

        def hook(faction_id: str, amount: int) -> None:
            calls.append((faction_id, amount))

        outcome = EncounterOutcome("x", [MissionReward("modify_reputation", 10, "commerce_guild")])
        apply_encounter_outcome(player, outcome, apply_reputation=hook)
        assert calls == [("commerce_guild", 10)]
        assert player.faction_reputation.get("commerce_guild", 0) == 0

    def test_confiscate_cargo_removes_min_of_held_and_amount(self) -> None:
        player = fresh_player()
        player.ship.add_cargo("contraband_chems", 3)
        outcome = EncounterOutcome("x", [MissionReward("confiscate_cargo", 10, "contraband_chems")])
        apply_encounter_outcome(player, outcome)
        assert player.ship.get_cargo_quantity("contraband_chems") == 0

    def test_confiscate_cargo_takes_only_the_amount_when_more_is_held(self) -> None:
        """No golden covers confiscate_cargo, so this pins the amount < held branch."""
        player = fresh_player()
        player.ship.add_cargo("contraband_chems", 10)
        outcome = EncounterOutcome("x", [MissionReward("confiscate_cargo", 3, "contraband_chems")])
        apply_encounter_outcome(player, outcome)
        assert player.ship.get_cargo_quantity("contraband_chems") == 7, (
            "a confiscation of 3 from a hold of 10 must leave 7"
        )

    def test_confiscate_cargo_does_nothing_when_commodity_absent(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome("x", [MissionReward("confiscate_cargo", 5, "not_carried")])
        apply_encounter_outcome(player, outcome)
        assert player.ship.get_cargo_quantity("not_carried") == 0

    def test_reduce_criminal_heat_lowers_heat(self) -> None:
        player = fresh_player()
        player.add_criminal_heat(50)
        outcome = EncounterOutcome("x", [MissionReward("reduce_criminal_heat", 20)])
        apply_encounter_outcome(player, outcome)
        assert player.criminal_heat == 30

    def test_start_bounty_combat_splits_target_ids(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome("x", [MissionReward("start_bounty_combat", 0, "a,b")])
        effects = apply_encounter_outcome(player, outcome)
        assert effects.bounty_combat_ids == ["a", "b"]

    def test_start_bounty_combat_with_empty_target_gives_empty_list(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome("x", [MissionReward("start_bounty_combat", 0, "")])
        effects = apply_encounter_outcome(player, outcome)
        assert effects.bounty_combat_ids == []

    def test_outcome_without_bounty_rewards_leaves_bounty_fields_none(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome("x", [MissionReward("credits", 10)])
        effects = apply_encounter_outcome(player, outcome)
        assert effects.bounty_immunity_days is None
        assert effects.bounty_combat_ids is None
        assert effects.smuggling_caught is False

    def test_set_flag_reward_without_target_id_is_skipped(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome("x", [MissionReward("set_flag", 1, "")])
        effects = apply_encounter_outcome(player, outcome)
        assert effects.flags_set == []
