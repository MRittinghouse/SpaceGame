"""The banner and the crew's mini-game commentary render the captain's tokens (spec 2.7).

The banner (``Game._render_mission_notification``) prints every queued notification: ambient
crew lines, idle and after-combat banter, flag lines, thread narration, dilemma telegraphs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional
from unittest.mock import patch

from spacegame.engine.game import Game
from spacegame.models.captain_tokens import Pronouns
from tools.parity.snapshots import fresh_player


def _game(choice: Optional[Pronouns]) -> Game:
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = None
    if choice is not None:
        game._player = fresh_player()
        game._player.pronouns = choice
    game._mission_notifications = []
    return game


def test_the_banner_renders_queued_crew_talk() -> None:
    game = _game(Pronouns.SHE)
    game._mission_notifications.append("Elena: \"{They}{v:'s|'re} on the board again.\"")
    assert game._next_mission_notification() == 'Elena: "She\'s on the board again."'
    assert game._mission_notifications == []


def test_the_banner_renders_they_them_before_a_game() -> None:
    game = _game(None)
    game._mission_notifications.append("{They} {v:docks|dock} at noon.")
    assert game._next_mission_notification() == "They dock at noon."


def test_crew_commentary_renders_for_the_captain() -> None:
    game = _game(Pronouns.HE)
    game.ambient_dialogue = SimpleNamespace(
        get_player_action_line=lambda action_type, recruited, loyalty_map: (
            "elena_reeves",
            "{They} {v:sells|sell} high.",
        )
    )
    game.crew_roster = SimpleNamespace(
        get_recruited_members=lambda: [(SimpleNamespace(id="elena_reeves"), None)],
        get_member_state=lambda crew_id: {"loyalty": 60},
        get_template=lambda crew_id: SimpleNamespace(name="Elena"),
    )
    commentary = game._make_crew_commentary_fn()
    assert commentary("mining") == ("Elena", "He sells high.")
