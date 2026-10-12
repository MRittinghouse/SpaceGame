"""Game's crew talk: the rows, opening a scene, the spoken set and the landing.

Polish design 3.1.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from spacegame.config import GameState
from spacegame.data_loader import get_data_loader
from spacegame.engine.game import Game
from spacegame.models.crew import CrewRoster
from spacegame.models.crew_scene import (
    NEXT_PORT,
    NO_SUCH_SCENE,
    NOT_ABOARD,
    NOTHING_NOW,
    CrewScene,
    CrewTalkRow,
)
from spacegame.models.dialogue import DialogueManager
from spacegame.models.mission import MissionManager, MissionStatus
from spacegame.models.social import SocialManager
from tests.test_scenarios._helpers import fresh_player

OPENER = CrewScene(
    id="test_opener",
    quest_id="elena_old_charts",
    crew_id="elena_reeves",
    beat="opener",
    initiative="crew",
    dialogue_id="elena_old_charts_dialogue",
    entry_node="start",
    min_loyalty=50,
    hook="Captain, when you have a minute, I'd like to talk about Koren.",
)
RESOLUTION = CrewScene(
    id="test_resolution",
    quest_id="elena_old_charts",
    crew_id="elena_reeves",
    beat="resolution",
    initiative="crew",
    dialogue_id="elena_archives_dialogue",
    entry_node="start",
    system_id="stellaris_port",
    hook="The archive terminal is in the Guild Quarter. My codes should still work.",
)
STRANGER = CrewScene(
    id="test_stranger",
    quest_id="marcus_the_inspector",
    crew_id="marcus_jin",
    beat="resolution",
    initiative="crew",
    dialogue_id="marcus_inspector_dialogue",
    entry_node="start",
    system_id="forgeworks",
    with_npc_id="lira_feng",
    hook="The inspector's office is on the yard deck.",
)


def _game(*scenes: CrewScene, loyalty: int = 50) -> Game:
    """A Game holding Elena Reeves at this loyalty, with only these crew scenes."""
    dl = get_data_loader()
    dl.load_all()
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = fresh_player()
    loader: Any = SimpleNamespace(
        crew_scenes={scene.id: scene for scene in scenes},
        crew_templates=dl.crew_templates,
        systems=dl.systems,
        get_dialogue=dl.get_dialogue,
        get_npc=dl.get_npc,
    )
    game.data_loader = loader
    roster = CrewRoster(dl.crew_templates)
    ok, msg = roster.recruit("elena_reeves", 4)
    assert ok, msg
    roster.adjust_loyalty("elena_reeves", loyalty - 30)
    game.crew_roster = roster
    game.mission_manager = MissionManager(list(dl.missions))
    game.dialogue_manager = DialogueManager()
    game.social_manager = SocialManager()
    game.politics_manager = None
    game.state_manager = MagicMock()
    game.dialogue_view = None
    game.crew_roster_view = None
    game._mission_notifications = []
    game._crew_spoke = set()
    game._last_crew_scene_id = ""
    game._last_dialogue_npc_id = None
    game._start_transition = MagicMock()  # type: ignore[method-assign]

    def _ensure_view() -> None:
        game.dialogue_view = MagicMock()

    game._ensure_dialogue_view = _ensure_view  # type: ignore[method-assign]
    return game


class TestTheTalk:
    def test_the_rows_name_each_companions_matter(self) -> None:
        game = _game(OPENER)
        assert game.crew_talk() == [CrewTalkRow("elena_reeves", "test_opener", OPENER.hook, "crew")]

    def test_below_the_mark_there_is_nothing_to_raise(self) -> None:
        assert _game(OPENER, loyalty=49).crew_talk() == []


class TestStartingAScene:
    def test_a_due_scene_opens_at_its_entry_node(self) -> None:
        game = _game(OPENER)
        assert game.start_crew_scene("test_opener") == (True, "")
        node = game.dialogue_manager.get_current_node()
        assert node is not None and node.id == "start"
        assert game._last_crew_scene_id == "test_opener"
        assert game._last_dialogue_npc_id is None

    def test_a_scene_opens_with_its_stranger(self) -> None:
        game = _game(STRANGER)
        assert game.crew_roster is not None
        ok, msg = game.crew_roster.recruit("marcus_jin", 4)
        assert ok, msg
        game.mission_manager._status["marcus_the_inspector"] = MissionStatus.ACTIVE
        game.player.current_system_id = "forgeworks"
        assert game.start_crew_scene("test_stranger") == (True, "")
        assert game.dialogue_manager._current_npc_id == "lira_feng"
        assert game._last_dialogue_npc_id == "lira_feng"

    def test_a_scene_that_is_not_due_is_refused_with_the_gates_reason(self) -> None:
        game = _game(STRANGER)
        assert game.start_crew_scene("test_stranger") == (
            False,
            NOT_ABOARD.format(name="Marcus Jin"),
        )
        assert not game.dialogue_manager.is_active

    def test_an_unknown_scene_is_refused(self) -> None:
        assert _game(OPENER).start_crew_scene("nowhere") == (False, NO_SUCH_SCENE)


class TestThePace:
    def test_a_closed_scene_quiets_its_companion_until_the_next_landing(self) -> None:
        game = _game(OPENER)
        game.start_crew_scene("test_opener")
        game._close_crew_scene()
        assert game._crew_spoke == {"elena_reeves"}
        assert game._last_crew_scene_id == ""
        assert game.start_crew_scene("test_opener") == (
            False,
            NEXT_PORT.format(name="Elena Reeves"),
        )
        game._crew_landing()
        assert game.start_crew_scene("test_opener") == (True, "")


class TestTheLanding:
    def test_a_place_scene_announces_its_hook_there(self) -> None:
        game = _game(OPENER, RESOLUTION)
        game.mission_manager._status["elena_old_charts"] = MissionStatus.ACTIVE
        game.player.current_system_id = "stellaris_port"
        game._crew_landing()
        assert game._mission_notifications == [f'Elena Reeves: "{RESOLUTION.hook}"']

    def test_an_opener_announces_nothing(self) -> None:
        game = _game(OPENER)
        game._crew_landing()
        assert game._mission_notifications == []


class TestTheRosterButton:
    def test_talk_opens_the_companions_first_matter_and_returns_to_the_roster(self) -> None:
        game = _game(OPENER)
        game.crew_roster_view = MagicMock(pending_talk_id="elena_reeves")
        game._talk_from_roster()
        assert game.crew_roster_view.pending_talk_id is None
        assert game._last_crew_scene_id == "test_opener"
        assert game.dialogue_view is not None
        assert game.dialogue_view._return_state == GameState.CREW_ROSTER

    def test_talk_with_nothing_due_says_so(self) -> None:
        game = _game(OPENER, loyalty=40)
        game.crew_roster_view = MagicMock(pending_talk_id="elena_reeves")
        game._talk_from_roster()
        assert game._mission_notifications == [NOTHING_NOW.format(name="Elena Reeves")]
        assert not game.dialogue_manager.is_active
