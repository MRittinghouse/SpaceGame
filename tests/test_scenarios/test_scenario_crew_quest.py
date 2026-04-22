"""Scenario H: Crew quest lifecycle.

Crew quests differ from generic missions in important ways:
  - They gate on crew membership: ``check_objectives`` skips a crew quest when
    its ``crew_member_id`` is not in the recruited set.
  - They commonly gate on loyalty thresholds via `crew_loyalty_<id>_50/70/85`
    dialogue flags produced dynamically by ``CrewRoster.adjust_loyalty``.
  - Their rewards can grow loyalty further, creating a positive-feedback arc.

This scenario verifies those crew-specific behaviors don't silently regress.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.mission import MissionManager, MissionStatus
from tests.test_scenarios._helpers import fresh_player


def _loaded_manager_and_roster() -> tuple[MissionManager, CrewRoster]:
    dl = get_data_loader()
    dl.load_all()
    mgr = MissionManager(dl.missions)
    roster = CrewRoster(templates=dl.crew_templates)
    return mgr, roster


def _pick_crew_quest(mgr: MissionManager) -> object | None:
    """Find a crew quest with at least one known crew_member_id."""
    for _mid, mission in mgr._missions.items():
        if mission.crew_member_id and mission.objectives:
            return mission
    return None


class TestCrewMembershipGatesQuestProgression:
    """check_objectives must skip crew quests whose crew member isn't recruited.
    This prevents quest objectives from completing via 'ambient' player state
    while the crew member is off the ship."""

    def test_crew_quest_progress_skipped_when_crew_not_recruited(self) -> None:
        mgr, _ = _loaded_manager_and_roster()
        player = fresh_player()

        quest = _pick_crew_quest(mgr)
        assert quest is not None, "Need a crew quest in data to run this test"

        # Force quest to ACTIVE regardless of prereqs
        mgr._status[quest.id] = MissionStatus.ACTIVE

        # Set whichever flag the objective reads — would trivially complete
        # if crew gating didn't apply.
        for obj in quest.objectives:
            if obj.target_id:
                player.dialogue_flags[obj.target_id] = True

        # Empty recruited set — crew member is NOT aboard
        newly = mgr.check_objectives(player, recruited_crew_ids=set())

        assert quest.id not in newly, (
            f"Crew quest '{quest.id}' must not complete when "
            f"crew_member_id='{quest.crew_member_id}' is not recruited"
        )
        assert mgr.get_status(quest.id) == MissionStatus.ACTIVE

    def test_crew_quest_progresses_when_crew_is_recruited(self) -> None:
        mgr, _ = _loaded_manager_and_roster()
        player = fresh_player()

        quest = _pick_crew_quest(mgr)
        assert quest is not None

        mgr._status[quest.id] = MissionStatus.ACTIVE
        for obj in quest.objectives:
            if obj.target_id:
                player.dialogue_flags[obj.target_id] = True

        # Crew member IS recruited
        newly = mgr.check_objectives(
            player, recruited_crew_ids={quest.crew_member_id}
        )

        # At least the objectives should have been evaluated — whether the
        # quest completes depends on objective types. Confirm the quest was
        # NOT skipped (as evidenced by at least one objective marked complete
        # or the quest status changing).
        some_progress = any(mgr._progress[quest.id])
        assert some_progress or quest.id in newly, (
            "Recruited crew member must allow objective progression"
        )


class TestLoyaltyThresholdFlagsProduction:
    """Loyalty flags (`crew_loyalty_<id>_50/70/85`) are produced dynamically
    by ``adjust_loyalty``. These flags gate many crew quests.

    Critical contract: crossing UP through a threshold yields the flag;
    staying below it or crossing DOWN through it does NOT.
    """

    def test_crossing_loyalty_50_yields_flag(self) -> None:
        _, roster = _loaded_manager_and_roster()
        # Recruit a companion
        companion_id = "elena_reeves"
        roster.recruit(companion_id, crew_slots=4)

        # Elena starts at some base loyalty — push to 49 first
        current = roster._state[companion_id]["loyalty"]
        # Level down to exactly 49 if already above
        if current > 49:
            roster.adjust_loyalty(companion_id, 49 - current)
        elif current < 49:
            roster.adjust_loyalty(companion_id, 49 - current)

        assert roster._state[companion_id]["loyalty"] == 49
        # Cross the 50 threshold
        flags = roster.adjust_loyalty(companion_id, 1)

        expected_flag = f"crew_loyalty_{companion_id}_50"
        assert expected_flag in flags, (
            f"Crossing loyalty 50 must yield '{expected_flag}'. Got: {flags}"
        )

    def test_loyalty_below_threshold_yields_no_flag(self) -> None:
        _, roster = _loaded_manager_and_roster()
        companion_id = "elena_reeves"
        roster.recruit(companion_id, crew_slots=4)
        current = roster._state[companion_id]["loyalty"]
        if current > 40:
            roster.adjust_loyalty(companion_id, 40 - current)

        # Bump from 40 to 45 — still below threshold
        flags = roster.adjust_loyalty(companion_id, 5)

        assert not any("_50" in f for f in flags), (
            f"No loyalty flag should fire below 50. Got: {flags}"
        )

    def test_losing_loyalty_yields_no_flag(self) -> None:
        """Threshold flags fire only on UPWARD crossings."""
        _, roster = _loaded_manager_and_roster()
        companion_id = "elena_reeves"
        roster.recruit(companion_id, crew_slots=4)

        # Push to 60, then drop to 40 — should NOT re-trigger 50 flag
        current = roster._state[companion_id]["loyalty"]
        roster.adjust_loyalty(companion_id, 60 - current)
        flags = roster.adjust_loyalty(companion_id, -20)
        assert flags == [], "Losing loyalty must not yield threshold flags"


class TestCrewQuestsExistInData:
    """Sanity check: every companion has at least one crew_member_id quest."""

    def test_all_companions_have_at_least_one_quest(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        mgr = MissionManager(dl.missions)

        companions = {tid for tid, t in dl.crew_templates.items() if t.is_companion}
        quests_by_companion: dict[str, list[str]] = {cid: [] for cid in companions}
        for mid, mission in mgr._missions.items():
            if mission.crew_member_id in quests_by_companion:
                quests_by_companion[mission.crew_member_id].append(mid)

        missing = [cid for cid, quests in quests_by_companion.items() if not quests]
        assert not missing, (
            f"Every companion should have at least one crew quest. Missing: {missing}"
        )


class TestCrewQuestRewardsFireNormally:
    """Mission rewards on crew quests (credits, xp, set_flag) follow the same
    pipeline as regular missions — verify one end-to-end."""

    def test_crew_quest_reward_application(self) -> None:
        mgr, _ = _loaded_manager_and_roster()
        player = fresh_player(credits=100)

        # Find a crew quest with a credits reward
        quest = None
        for _mid, mission in mgr._missions.items():
            if mission.crew_member_id and any(
                r.reward_type == "credits" and r.amount > 0 for r in mission.rewards
            ):
                quest = mission
                break
        assert quest is not None

        credits_reward = sum(
            r.amount for r in quest.rewards if r.reward_type == "credits"
        )
        before = player.credits
        mgr.apply_rewards(quest.id, player)
        assert player.credits == before + credits_reward


class TestCompanionRecruitmentState:
    """Recruitment must persist runtime state (loyalty, level) correctly."""

    def test_recruit_initializes_state_once(self) -> None:
        _, roster = _loaded_manager_and_roster()
        companion_id = "marcus_jin"

        ok, _msg = roster.recruit(companion_id, crew_slots=4)
        assert ok
        assert companion_id in roster.recruited_ids
        assert companion_id in roster._state
        assert "loyalty" in roster._state[companion_id]
        assert "xp" in roster._state[companion_id]

    def test_cannot_recruit_twice(self) -> None:
        _, roster = _loaded_manager_and_roster()
        companion_id = "marcus_jin"
        roster.recruit(companion_id, crew_slots=4)

        ok, msg = roster.recruit(companion_id, crew_slots=4)
        assert not ok, f"Second recruit should fail, got ok={ok} msg={msg}"
