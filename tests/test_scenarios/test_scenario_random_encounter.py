"""Scenario: random encounter lifecycle — trigger, choose, resolve, apply.

SI-2 Stream 1. 131 encounters across 11 types live in ``data/encounters/``;
no scenario currently exercises them as a full flow.

Walks the four hops a playtester triggers when an encounter fires during
travel:

  1. **Trigger** — ``check_travel_encounter`` returns an EncounterRef
     under live conditions. Deterministic on (game_day, system_id).
  2. **Selection** — ``select_encounter_definition`` filters by
     eligibility (type, danger, required flags, level, unique-once,
     resolved captains) and weighted-picks among survivors.
  3. **Choice**: player picks an EncounterChoice. If the choice has a
     ``skill_check``, success returns ``outcome``; failure returns
     ``failure_outcome`` (or ``outcome`` if no failure path is authored).
  4. **Apply**: ``apply_encounter_outcome`` (models/encounter.py) walks
     ``outcome.rewards`` and dispatches each ``MissionReward`` to the
     right player primitive (credits, XP, dialogue_flags, reputation,
     cargo confiscation, criminal heat, etc.).

The helpers below delegate to the model functions that own this logic
(``resolve_encounter_skill_check``, ``resolve_choice_outcome`` and
``apply_encounter_outcome``, all in ``spacegame.models.encounter``), so a
regression in any reward primitive or skill-check branch surfaces here too.

Coverage in this scenario stops short of the leads_to_combat path —
combat itself is covered by ``test_scenario_combat_victory`` and
``test_scenario_death_respawn``. This file covers the
encounter-resolution contract that hands off to combat.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterContext,
    EncounterDefinition,
    EncounterOutcome,
    EncounterSkillCheck,
    apply_encounter_outcome,
    check_travel_encounter,
    mark_unique_encounter_seen,
    resolve_choice_outcome,
    resolve_encounter_skill_check,
    select_encounter_definition,
)
from spacegame.models.mission import MissionReward
from spacegame.models.social import SocialManager
from tests.test_scenarios._helpers import fresh_player

# ---------------------------------------------------------------------------
# Reward-dispatch helper — mirrors Game._apply_encounter_result (game.py:2921).
# Kept inline so a regression in any reward primitive surfaces here.
# ---------------------------------------------------------------------------


def _apply_outcome_rewards(player, outcome: EncounterOutcome) -> None:
    """Delegate reward application to ``apply_encounter_outcome``.

    Skips the politics/dialogue-manager/crew-reaction side channels that
    only Game has access to; those are covered in
    ``test_qa_ce_encounter_pipeline.py``. This helper covers the player-
    state mutations every encounter reward type triggers, by exercising
    the same model function ``Game._apply_encounter_result`` calls.
    """
    apply_encounter_outcome(player, outcome)


def _resolve_choice(player, choice: EncounterChoice, social: SocialManager) -> EncounterOutcome:
    """Delegate skill-check resolution and outcome selection to the model.

    Resolves the skill_check (if present) through
    ``resolve_encounter_skill_check``, which writes the success or
    failure flag, then returns the resolved outcome (main or failure
    branch) through ``resolve_choice_outcome``. This scenario never
    exercises a shakedown demand, so it always passes 0.
    """
    passed = (
        resolve_encounter_skill_check(choice.skill_check, social, player)
        if choice.skill_check is not None
        else True
    )
    return resolve_choice_outcome(choice, 0, passed)


# ---------------------------------------------------------------------------
# Synthetic encounter fixtures — surgical tests don't depend on content drift
# ---------------------------------------------------------------------------


def _simple_encounter(
    *,
    enc_id: str = "test_simple_encounter",
    rewards: list[MissionReward] | None = None,
    enc_type: str = "diplomatic",
    danger_levels: list[str] | None = None,
    unique: bool = False,
) -> EncounterDefinition:
    rewards = rewards or [MissionReward(reward_type="credits", amount=100)]
    return EncounterDefinition(
        id=enc_id,
        encounter_type=enc_type,
        name="Test",
        description="A simple test encounter.",
        choices=[
            EncounterChoice(
                id="accept",
                label="Accept",
                description="Take the deal.",
                outcome=EncounterOutcome(description="Done.", rewards=rewards),
            ),
        ],
        weight=10,
        danger_levels=danger_levels or ["safe", "moderate", "dangerous"],
        unique=unique,
    )


# ---------------------------------------------------------------------------
# 1. Trigger
# ---------------------------------------------------------------------------


class TestTrigger:
    def test_returns_encounter_ref_under_live_conditions(self) -> None:
        """Dangerous system + non-trivial distance + non-empty enemy pool
        produces an EncounterRef on at least one of several deterministic
        seeds (the function is seeded by game_day + system_id)."""
        # Try several days — the deterministic seeding means at least one
        # day in a small window must roll under the dangerous-system chance.
        triggered = False
        for day in range(1, 30):
            ref = check_travel_encounter(
                system_danger="dangerous",
                enemy_template_ids=["pirate_scout", "pirate_raider"],
                game_day=day,
                system_id="frontier_outpost",
                distance=200.0,
            )
            if ref is not None:
                triggered = True
                # ref.encounter_type is always set; enemy_template_ids
                # is empty for non-hostile encounters (derelict, anomaly
                # etc.) and non-empty for hostile ones — both legal.
                assert ref.encounter_type
                break
        assert triggered, (
            "No trigger fired across 29 days in dangerous space — "
            "either the chance constant collapsed or the seed pipeline broke"
        )

    def test_returns_none_in_safe_system_short_hop(self) -> None:
        """Short hops in safe space should never trigger across many seeds."""
        # Heavy reduction should suppress entirely, regardless of seed.
        for day in range(1, 100):
            ref = check_travel_encounter(
                system_danger="safe",
                enemy_template_ids=["pirate_scout"],
                game_day=day,
                system_id="nexus_prime",
                distance=10.0,
                encounter_reduction=0.99,  # crush the chance to ~0
            )
            assert ref is None, f"day {day}: encounter fired despite encounter_reduction=0.99"

    def test_empty_enemy_pool_returns_none(self) -> None:
        """No enemies available → no encounter, even in dangerous space."""
        ref = check_travel_encounter(
            system_danger="dangerous",
            enemy_template_ids=[],
            game_day=1,
            system_id="frontier_outpost",
            distance=300.0,
        )
        assert ref is None


# ---------------------------------------------------------------------------
# 2. Selection — eligibility filters
# ---------------------------------------------------------------------------


class TestSelectionEligibility:
    def test_filters_by_required_flags(self) -> None:
        """An encounter requiring a flag the player lacks must not be selected."""
        gated = _simple_encounter(enc_id="needs_flag")
        gated.requires_flags = ["completed_act_one"]
        ungated = _simple_encounter(enc_id="open")

        ctx_no_flag = EncounterContext(
            encounter_type="diplomatic",
            danger_level="moderate",
            seed=42,
            dialogue_flags={},
        )
        picked = select_encounter_definition([gated, ungated], ctx_no_flag)
        assert picked is ungated, "gated encounter must be filtered out"

        ctx_with_flag = EncounterContext(
            encounter_type="diplomatic",
            danger_level="moderate",
            seed=42,
            dialogue_flags={"completed_act_one": True},
        )
        # Both eligible now; weighted-random picks one
        picked2 = select_encounter_definition([gated, ungated], ctx_with_flag)
        assert picked2 in (gated, ungated)

    def test_unique_encounter_filtered_after_seen(self) -> None:
        """Unique encounters drop out of the pool after their seen-flag is set."""
        unique_enc = _simple_encounter(enc_id="once_only", unique=True)
        ctx = EncounterContext(
            encounter_type="diplomatic",
            danger_level="moderate",
            seed=1,
        )
        # First selection: present
        first = select_encounter_definition([unique_enc], ctx)
        assert first is unique_enc

        # Producer: mark_unique_encounter_seen writes the flag consumed below.
        player = fresh_player()
        flag = mark_unique_encounter_seen(player, unique_enc)
        assert flag == "encounter_seen_once_only"

        # After marking seen, drops out
        ctx_seen = EncounterContext(
            encounter_type="diplomatic",
            danger_level="moderate",
            seed=1,
            dialogue_flags=player.dialogue_flags,
        )
        second = select_encounter_definition([unique_enc], ctx_seen)
        assert second is None

    def test_danger_level_mismatch_filters(self) -> None:
        safe_only = _simple_encounter(enc_id="peaceful", danger_levels=["safe"])
        ctx = EncounterContext(
            encounter_type="diplomatic",
            danger_level="dangerous",
            seed=7,
        )
        picked = select_encounter_definition([safe_only], ctx)
        assert picked is None


# ---------------------------------------------------------------------------
# 3. Skill-check branching
# ---------------------------------------------------------------------------


class TestSkillCheckBranching:
    def test_success_returns_main_outcome_and_sets_success_flag(self) -> None:
        player = fresh_player()
        social = SocialManager()
        # Bump persuasion past difficulty 1
        social._skills["persuasion"]._level = 3

        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="Convince them.",
            outcome=EncounterOutcome(
                description="Success",
                rewards=[MissionReward(reward_type="credits", amount=50)],
            ),
            skill_check=EncounterSkillCheck(
                skill="persuasion",
                difficulty=1,
                set_flag_on_success="encounter_talked_down",
                set_flag_on_failure="encounter_talk_failed",
            ),
            failure_outcome=EncounterOutcome(
                description="Failure",
                rewards=[MissionReward(reward_type="credits", amount=10)],
            ),
        )

        outcome = _resolve_choice(player, choice, social)
        assert outcome.description == "Success"
        assert player.dialogue_flags.get("encounter_talked_down") is True
        assert "encounter_talk_failed" not in player.dialogue_flags

    def test_failure_returns_failure_outcome_and_sets_failure_flag(self) -> None:
        player = fresh_player()
        social = SocialManager()
        # Persuasion at default 0 — can't pass difficulty 5
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="Convince them.",
            outcome=EncounterOutcome(description="Success", rewards=[]),
            skill_check=EncounterSkillCheck(
                skill="persuasion",
                difficulty=5,
                set_flag_on_success="encounter_talked_down",
                set_flag_on_failure="encounter_talk_failed",
            ),
            failure_outcome=EncounterOutcome(
                description="Failure",
                rewards=[MissionReward(reward_type="credits", amount=10)],
            ),
        )

        outcome = _resolve_choice(player, choice, social)
        assert outcome.description == "Failure"
        assert player.dialogue_flags.get("encounter_talk_failed") is True
        assert "encounter_talked_down" not in player.dialogue_flags

    def test_failure_falls_back_to_outcome_when_no_failure_path(self) -> None:
        """Per encounter_view contract: a check with no failure_outcome
        still returns the main outcome on failure (so the player isn't
        stranded)."""
        player = fresh_player()
        social = SocialManager()
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="Convince them.",
            outcome=EncounterOutcome(description="Single path", rewards=[]),
            skill_check=EncounterSkillCheck(skill="persuasion", difficulty=5),
            failure_outcome=None,
        )
        outcome = _resolve_choice(player, choice, social)
        assert outcome.description == "Single path"


# ---------------------------------------------------------------------------
# 4. Reward dispatch — every primitive reward type lands
# ---------------------------------------------------------------------------


class TestRewardDispatch:
    def test_credits_reward_grants_credits(self) -> None:
        player = fresh_player(credits=1000)
        outcome = EncounterOutcome(
            description="paid",
            rewards=[MissionReward(reward_type="credits", amount=250)],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.credits == 1250
        assert player.encounters_survived == 1

    def test_deduct_credits_with_sufficient_funds(self) -> None:
        player = fresh_player(credits=500)
        outcome = EncounterOutcome(
            description="paid the bribe",
            rewards=[MissionReward(reward_type="deduct_credits", amount=200)],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.credits == 300

    def test_deduct_credits_insufficient_funds_waived(self) -> None:
        """Per game.py:2942: insufficient credits 'waives' the cost — no
        crash, no negative balance."""
        player = fresh_player(credits=50)
        outcome = EncounterOutcome(
            description="bribe attempt",
            rewards=[MissionReward(reward_type="deduct_credits", amount=200)],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.credits == 50

    def test_xp_reward_advances_progression(self) -> None:
        player = fresh_player()
        starting = player.progression.xp
        outcome = EncounterOutcome(
            description="lesson learned",
            rewards=[MissionReward(reward_type="xp", amount=75)],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.progression.xp == starting + 75

    def test_set_flag_writes_dialogue_flag(self) -> None:
        player = fresh_player()
        outcome = EncounterOutcome(
            description="story beat",
            rewards=[MissionReward(reward_type="set_flag", amount=1, target_id="met_torres")],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.dialogue_flags.get("met_torres") is True

    def test_modify_reputation_routes_through_player_api(self) -> None:
        player = fresh_player()
        before = player.faction_reputation.get("commerce_guild", 0)
        outcome = EncounterOutcome(
            description="favor done",
            rewards=[
                MissionReward(
                    reward_type="modify_reputation",
                    amount=5,
                    target_id="commerce_guild",
                )
            ],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.faction_reputation.get("commerce_guild", 0) == before + 5

    def test_confiscate_cargo_removes_only_what_exists(self) -> None:
        player = fresh_player()
        player.ship.add_cargo("contraband_chems", 3)
        outcome = EncounterOutcome(
            description="searched",
            rewards=[
                MissionReward(
                    reward_type="confiscate_cargo",
                    amount=10,  # asks for 10, only 3 exist
                    target_id="contraband_chems",
                )
            ],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.ship.get_cargo_quantity("contraband_chems") == 0

    def test_add_criminal_heat_increments_counter_and_heat(self) -> None:
        player = fresh_player()
        before_heat = player.criminal_heat
        before_caught = player.times_caught_smuggling
        outcome = EncounterOutcome(
            description="busted",
            rewards=[MissionReward(reward_type="add_criminal_heat", amount=20)],
        )
        _apply_outcome_rewards(player, outcome)
        assert player.criminal_heat > before_heat
        assert player.times_caught_smuggling == before_caught + 1


# ---------------------------------------------------------------------------
# 5. Full chain — real loaded encounter content walks end to end
# ---------------------------------------------------------------------------


class TestFullEncounterChain:
    def test_real_encounter_definitions_load_and_a_choice_resolves(self) -> None:
        """Smoke: the real loaded encounter pool contains usable definitions
        and at least one of them resolves cleanly through the pipeline.
        Catches authoring bugs where rewards reference unknown reward_types,
        choices have empty outcomes, etc."""
        dl = get_data_loader()
        dl.load_all()
        defs = dl.encounter_definitions
        assert defs, "no encounter definitions loaded"

        # Find any non-skill-check, non-leads-to-combat choice with a
        # credits reward — the simplest path. With 131 definitions there's
        # always at least one.
        target = None
        for d in defs:
            for c in d.choices:
                if c.skill_check is not None:
                    continue
                if c.outcome.leads_to_combat:
                    continue
                if any(r.reward_type == "credits" for r in c.outcome.rewards):
                    target = (d, c)
                    break
            if target:
                break

        assert target, (
            "no non-combat, non-skill-check, credits-rewarding choice in "
            "131 encounter definitions — content drift suspect"
        )
        _defn, choice = target

        player = fresh_player(credits=1000)
        social = SocialManager()
        outcome = _resolve_choice(player, choice, social)
        assert outcome == choice.outcome

        before_credits = player.credits
        _apply_outcome_rewards(player, outcome)

        credits_in_reward = sum(r.amount for r in outcome.rewards if r.reward_type == "credits")
        assert player.credits == before_credits + credits_in_reward
        assert player.encounters_survived == 1
