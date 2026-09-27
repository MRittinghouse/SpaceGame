"""Game.check_missions announces a completed mission's payout in a fixed order.

Task 7 moved the payout (crew, trade permit and reputation rewards, the side and
crew-quest counters, Shared Experience bonus XP, the per-mission crew XP and
loyalty) into ``MissionManager.complete_mission``; ``check_missions`` only
announces the record it returns. These tests drive the real ``check_missions``
with real models and pin what the player sees: the exact notification lines in
their order, the sound and shake cues, and the state each reward changed. They
were written against the pre-move ``check_missions`` and passed there, so they
prove the rewire kept the behavior.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from spacegame.data_loader import get_data_loader
from spacegame.engine.game import Game
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


def _mission(
    mission_id: str,
    name: str,
    rewards: list[MissionReward],
    *,
    mission_type: str = "campaign",
    crew_member_id: str = "",
) -> Mission:
    """A mission whose single objective (hold 1 credit) a fresh player already meets."""
    return Mission(
        id=mission_id,
        name=name,
        description="A test mission.",
        objectives=[
            MissionObjective(type=ObjectiveType.HAVE_CREDITS, target_id="", target_quantity=1)
        ],
        rewards=rewards,
        mission_type=mission_type,
        crew_member_id=crew_member_id,
    )


def _make_game(mission: Mission, roster: CrewRoster) -> Game:
    """A ``Game`` with just enough wiring for ``check_missions`` to complete ``mission``."""
    dl = get_data_loader()
    dl.load_all()
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = fresh_player()
    game._player.progression.skills["shared_experience"].current_level = 1
    manager = MissionManager([])
    manager.add_mission(mission, initial_status=MissionStatus.ACTIVE)
    game.mission_manager = manager
    game.crew_roster = roster
    game.data_loader = dl
    game.politics_manager = None
    game.audio_manager = MagicMock()
    game.screen_shake = MagicMock()
    game.dialogue_manager = MagicMock()
    game.journal = None
    game.galaxy_map_view = None
    game._mission_notifications = []
    game._after_player_action = MagicMock()  # type: ignore[method-assign]
    game._check_journal_triggers = MagicMock()  # type: ignore[method-assign]
    game._log_mission_audit = MagicMock()  # type: ignore[method-assign]
    return game


def _roster_with(*crew_ids: str) -> CrewRoster:
    """A real roster holding ``crew_ids``."""
    roster = CrewRoster(get_data_loader().crew_templates)
    for crew_id in crew_ids:
        ok, msg = roster.recruit(crew_id, len(crew_ids))
        assert ok, msg
    return roster


class TestCheckMissionsPayout:
    def test_crew_quest_payout_announces_in_order(self) -> None:
        dl = get_data_loader()
        roster = _roster_with("elena_reeves")
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        # Seeded so the per-mission +20 crew XP crosses the level-2 threshold (50) and
        # the +5 loyalty crosses the 50 flag threshold: both late lines then show up.
        state["xp"] = 30
        state["loyalty"] = 45
        mission = _mission(
            "elena_errand",
            "Elena's Errand",
            [
                MissionReward("xp", 100),
                MissionReward("trade_permit", 0, "all"),
                MissionReward("modify_reputation", 5, "commerce_guild"),
            ],
            mission_type="side",
            crew_member_id="elena_reeves",
        )
        game = _make_game(mission, roster)
        assert not game.player.trade_permits

        game.check_missions()

        assert game._mission_notifications == [
            "Mission Complete: Elena's Errand! +100 XP",
            "+10 Bonus XP (Shared Experience)",
            "Trade Permit Acquired: Universal Bill of Landing",
            "+5 Rep: Commerce Guild",
            "Elena Reeves reached level 2!",
        ]
        assert all(fid in game.player.trade_permits for fid in dl.factions)
        assert state["loyalty"] == 45 + 5
        game.dialogue_manager.set_flag.assert_called_once_with("crew_loyalty_elena_reeves_50")
        assert game.player.faction_reputation["commerce_guild"] == 5
        assert game.player.side_missions_completed == 1
        assert game.player.crew_quests_completed == 1
        assert game.mission_manager.get_status("elena_errand") == MissionStatus.COMPLETED

    def test_full_roster_announces_the_waiting_companion(self) -> None:
        dl = get_data_loader()
        roster = _roster_with("elena_reeves")
        game = _make_game(
            _mission(
                "marcus_signs_on",
                "Marcus Signs On",
                [MissionReward("credits", 100), MissionReward("crew", 0, "marcus_jin")],
            ),
            roster,
        )
        assert game.player.ship.ship_type.crew_slots == len(roster.recruited_ids)
        template = dl.crew_templates["marcus_jin"]
        system = dl.get_system(template.home_system_id)
        assert system is not None and system.name != template.home_system_id

        game.check_missions()

        assert game._mission_notifications == [
            "Mission Complete: Marcus Signs On! +100 Credits",
            f"Crew Full: {template.name} is waiting at {system.name}. Dismiss a crew "
            f"member and visit the cantina to recruit them.",
        ]
        assert "marcus_jin" in roster.pending_companion_ids
        assert not roster.is_recruited("marcus_jin")
        assert call("crew_recruit") not in game.audio_manager.play_sfx.call_args_list

    def test_crew_joined_plays_its_cue(self) -> None:
        roster = _roster_with()
        game = _make_game(
            _mission(
                "elena_signs_on",
                "Elena Signs On",
                [MissionReward("credits", 100), MissionReward("crew", 0, "elena_reeves")],
            ),
            roster,
        )

        game.check_missions()

        assert game._mission_notifications == [
            "Mission Complete: Elena Signs On! +100 Credits",
            "Crew Joined: Elena Reeves",
        ]
        assert roster.is_recruited("elena_reeves")
        assert game.audio_manager.play_sfx.call_args_list == [
            call("quest_complete"),
            call("crew_recruit"),
        ]
        game.screen_shake.trigger.assert_called_once_with(intensity=3.0, duration=0.2)

    def test_politics_manager_spills_reputation_over(self) -> None:
        roster = _roster_with()
        game = _make_game(
            _mission(
                "guild_favor",
                "Guild Favor",
                [MissionReward("modify_reputation", 5, "commerce_guild")],
            ),
            roster,
        )
        politics = MagicMock()
        politics.apply_reputation_with_spillover.return_value = [
            ("commerce_guild", 5),
            ("crimson_reach", -2),
        ]
        game.politics_manager = politics

        game.check_missions()

        politics.apply_reputation_with_spillover.assert_called_once_with(
            game.player, "commerce_guild", 5
        )
        crimson = get_data_loader().get_faction("crimson_reach")
        assert crimson is not None
        assert game._mission_notifications == [
            "Mission Complete: Guild Favor! ",
            "+5 Rep: Commerce Guild",
            f"-2 Rep: {crimson.name}",
        ]
        assert game.player.faction_reputation == {}, "The politics manager applies the change"
