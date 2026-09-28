"""MissionManager.complete_mission pays every reward type (SP3 spec 6.1)."""

from __future__ import annotations

import copy

import pytest

from spacegame.constants.flags import campaign_mission_milestone
from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from tests.test_scenarios._helpers import fresh_player


def _manager() -> MissionManager:
    dl = get_data_loader()
    dl.load_all()
    return MissionManager(copy.deepcopy(dl.missions))


def _complete(manager: MissionManager, mission_id: str) -> None:
    manager._status[mission_id] = MissionStatus.COMPLETED


class TestCompleteMission:
    def test_universal_permit_and_crew_recruit(self) -> None:
        dl = get_data_loader()
        manager = _manager()
        player = fresh_player(credits=1000)
        roster = CrewRoster(dl.crew_templates)
        _complete(manager, "bill_of_landing")
        done = manager.complete_mission(
            "bill_of_landing", player, crew_roster=roster, faction_ids=list(dl.factions)
        )
        assert done.permits == ["all"]
        assert all(fid in player.trade_permits for fid in dl.factions)
        assert player.credits == 750
        _complete(manager, "recruit_navigator")
        done = manager.complete_mission("recruit_navigator", player, crew_roster=roster)
        assert roster.is_recruited("elena_reeves")
        assert done.crew_joined

    def test_every_completion_pays_crew_xp_and_loyalty(self) -> None:
        dl = get_data_loader()
        manager = _manager()
        roster = CrewRoster(dl.crew_templates)
        roster.recruit("elena_reeves", 4)
        _complete(manager, "bill_of_landing")
        manager.complete_mission("bill_of_landing", fresh_player(), crew_roster=roster)
        assert roster.get_state()["members"]["elena_reeves"]["loyalty"] == 35

    def test_reputation_without_a_politics_manager_applies_directly(self) -> None:
        manager = _manager()
        mission = next(
            m
            for m in manager._missions.values()
            if any(r.reward_type in ("reputation", "modify_reputation") for r in m.rewards)
        )
        _complete(manager, mission.id)
        player = fresh_player()
        done = manager.complete_mission(mission.id, player)
        assert done.reputation_changes
        totals: dict[str, int] = {}
        for fid, amount in done.reputation_changes:
            totals[fid] = totals.get(fid, 0) + amount
        for fid, total in totals.items():
            assert player.faction_reputation[fid] == max(-100, min(100, total))


def _mission(
    mission_id: str,
    *,
    mission_type: str = "campaign",
    crew_member_id: str = "",
    rewards: list[MissionReward] | None = None,
) -> Mission:
    """An inline mission; complete_mission never reads its objectives."""
    return Mission(
        id=mission_id,
        name=mission_id.replace("_", " ").title(),
        description="A test mission.",
        objectives=[
            MissionObjective(type=ObjectiveType.HAVE_CREDITS, target_id="", target_quantity=1)
        ],
        rewards=rewards or [],
        mission_type=mission_type,
        crew_member_id=crew_member_id,
    )


class TestCompletionCounters:
    def test_side_mission_counts_and_campaign_mission_does_not(self) -> None:
        manager = MissionManager([_mission("side_job", mission_type="side"), _mission("main_job")])
        player = fresh_player()
        assert player.side_missions_completed == 0
        _complete(manager, "side_job")
        manager.complete_mission("side_job", player)
        assert player.side_missions_completed == 1, "A side mission raises the side counter"
        _complete(manager, "main_job")
        manager.complete_mission("main_job", player)
        assert player.side_missions_completed == 1, "A campaign mission leaves it alone"

    def test_campaign_milestone_flag_is_set_once(self) -> None:
        side = _mission("side_errand", mission_type="side")
        campaign = [_mission(f"campaign_{i}") for i in range(1, 7)]
        manager = MissionManager([side, *campaign])
        player = fresh_player()
        flag = campaign_mission_milestone(5)
        # A completed side mission makes five completions in all once four campaign
        # missions are done, so the threshold only bites if the count is campaign-only.
        _complete(manager, "side_errand")
        for i in range(1, 5):
            _complete(manager, f"campaign_{i}")
            done = manager.complete_mission(f"campaign_{i}", player)
            assert done.milestone_flags == [], f"No milestone after {i} campaign missions"
        assert len(manager.get_completed_ids()) == 5
        assert not player.dialogue_flags.get(flag)

        _complete(manager, "campaign_5")
        done = manager.complete_mission("campaign_5", player)
        assert done.milestone_flags == [flag]
        assert player.dialogue_flags[flag] is True

        _complete(manager, "campaign_6")
        done = manager.complete_mission("campaign_6", player)
        assert done.milestone_flags == [], "The milestone flag is set only once"
        assert player.dialogue_flags[flag] is True

    def test_crew_quest_counts_and_pays_shared_experience(self) -> None:
        base_xp = 100
        quest = _mission(
            "elena_errand",
            crew_member_id="elena_reeves",
            rewards=[MissionReward(reward_type="xp", amount=base_xp)],
        )
        manager = MissionManager([quest])
        player = fresh_player()
        player.progression.skills["shared_experience"].current_level = 1
        assert player.progression.get_bonus("crew_quest_xp_bonus") == pytest.approx(0.1)
        xp_before = player.progression.xp
        _complete(manager, "elena_errand")
        done = manager.complete_mission("elena_errand", player)
        assert player.crew_quests_completed == 1
        assert done.bonus_xp == int(base_xp * 0.1) > 0
        assert player.progression.xp == xp_before + base_xp + done.bonus_xp

    def test_crew_quest_without_shared_experience_pays_no_bonus(self) -> None:
        base_xp = 100
        quest = _mission(
            "elena_errand",
            crew_member_id="elena_reeves",
            rewards=[MissionReward(reward_type="xp", amount=base_xp)],
        )
        manager = MissionManager([quest])
        player = fresh_player()
        assert player.progression.skills["shared_experience"].current_level == 0
        assert player.progression.get_bonus("crew_quest_xp_bonus") == 0
        xp_before = player.progression.xp
        _complete(manager, "elena_errand")
        done = manager.complete_mission("elena_errand", player)
        assert player.crew_quests_completed == 1
        assert done.bonus_xp == 0
        assert player.progression.xp == xp_before + base_xp


class TestCompletionRewards:
    def test_full_roster_marks_a_companion_pending(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        roster = CrewRoster(dl.crew_templates)
        player = fresh_player()
        crew_slots = player.ship.ship_type.crew_slots + int(
            player.progression.get_bonus("crew_slot_bonus")
        )
        for filler in ("marcus_jin", "dr_priya_osei", "tomas_drifter")[:crew_slots]:
            assert roster.recruit(filler, crew_slots)[0]
        assert len(roster.recruited_ids) == crew_slots, "The roster must be at capacity"
        template = roster.get_template("elena_reeves")
        assert template is not None and template.is_companion
        manager = MissionManager(
            [_mission("elena_signs_on", rewards=[MissionReward("crew", 0, "elena_reeves")])]
        )
        _complete(manager, "elena_signs_on")
        done = manager.complete_mission("elena_signs_on", player, crew_roster=roster)
        assert done.crew_joined == []
        assert done.crew_pending == ["elena_reeves"]
        assert "elena_reeves" in roster.pending_companion_ids
        assert not roster.is_recruited("elena_reeves")

    def test_reputation_hook_applies_the_change_and_reports_it(self) -> None:
        manager = MissionManager(
            [
                _mission(
                    "guild_favor",
                    rewards=[MissionReward("modify_reputation", 5, "commerce_guild")],
                )
            ]
        )
        player = fresh_player()
        before = dict(player.faction_reputation)
        calls: list[tuple[str, int]] = []

        def hook(faction_id: str, amount: int) -> list[tuple[str, int]]:
            calls.append((faction_id, amount))
            return [(faction_id, amount), ("some_rival", -2)]

        _complete(manager, "guild_favor")
        done = manager.complete_mission("guild_favor", player, apply_reputation=hook)
        assert calls == [("commerce_guild", 5)]
        assert done.reputation_changes == [("commerce_guild", 5), ("some_rival", -2)]
        assert player.faction_reputation == before, "The hook applies the change, not the model"
