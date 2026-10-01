"""Game.check_crew_xp pays crew XP and loyalty for trades and jumps since its last check.

Task 8 moved the per-trade and per-jump crew payouts and the Leadership skill sync
into ``CrewRoster`` (``on_trades``, ``on_jumps``, ``apply_leadership``);
``check_crew_xp`` keeps the delta polling, the notifications, the flag writes and
the crew reaction. These tests drive the real ``check_crew_xp`` with real models and
pin the XP, level, loyalty, notifications, flags and reactions each step produces.
They were written against the pre-move ``check_crew_xp`` and passed there, so they
prove the rewire kept the behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, call, patch

from spacegame.data_loader import get_data_loader
from spacegame.engine.game import Game
from spacegame.models.crew import CrewRoster
from tests.test_scenarios._helpers import fresh_player


@dataclass
class _Rig:
    """The game under test plus the collaborators the assertions read."""

    game: Game
    roster: CrewRoster
    state: dict[str, Any]
    dialogue: MagicMock
    after_action: MagicMock


def _rig() -> _Rig:
    """A ``Game`` holding Elena Reeves (xp 40, loyalty 46), Crew Mentor 1 and Inspiring Leader 1.

    Crew Mentor 1 gives ``crew_xp_bonus`` 2 and Inspiring Leader 1 gives
    ``crew_loyalty_bonus`` 1, so a swapped pair of bonuses shows up in the numbers.
    """
    dl = get_data_loader()
    dl.load_all()
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = fresh_player()
    game._player.progression.skills["crew_mentor"].current_level = 1
    game._player.progression.skills["inspiring_leader"].current_level = 1
    roster = CrewRoster(dl.crew_templates)
    ok, msg = roster.recruit("elena_reeves", 4)
    assert ok, msg
    state = roster.get_member_state("elena_reeves")
    assert state is not None
    state["xp"] = 40
    state["loyalty"] = 46
    rig = _Rig(game, roster, state, MagicMock(), MagicMock())
    game.crew_roster = roster
    game.dialogue_manager = rig.dialogue
    game._mission_notifications = []
    game._after_player_action = rig.after_action  # type: ignore[method-assign]
    game._crew_last_trades = 0
    game._crew_last_jumps = 0
    return rig


def _two_trades(rig: _Rig) -> None:
    """Complete two trades and poll."""
    rig.game.player.trades_completed = 2
    rig.game.check_crew_xp()


def _twenty_jumps(rig: _Rig) -> None:
    """Make twenty jumps and poll."""
    rig.game.player.jumps_traveled = 20
    rig.game.check_crew_xp()


class TestCheckCrewXp:
    def test_trades_pay_xp_and_loyalty(self) -> None:
        rig = _rig()

        _two_trades(rig)

        # (5 + 2) * 2 = 14 XP and (1 + 1) * 2 = 4 loyalty; swapped bonuses give 52 and 52.
        assert rig.state["xp"] == 54
        assert rig.state["level"] == 2
        assert rig.state["loyalty"] == 50
        assert rig.game._mission_notifications == ["Elena Reeves reached level 2!"]
        assert rig.dialogue.set_flag.call_args_list == [call("crew_loyalty_elena_reeves_50")]
        # F-C09: the player's store too, or the next conversation's reload of the copy drops it
        assert rig.game.player.dialogue_flags.get("crew_loyalty_elena_reeves_50") is True
        assert rig.after_action.call_args_list == [call("sold_cargo")]

    def test_jumps_pay_xp_only(self) -> None:
        rig = _rig()
        _two_trades(rig)

        _twenty_jumps(rig)

        # (3 + 2) * 20 = 100 XP and no loyalty.
        assert rig.state["xp"] == 154
        assert rig.state["level"] == 3
        assert rig.state["loyalty"] == 50
        assert rig.game._mission_notifications == [
            "Elena Reeves reached level 2!",
            "Elena Reeves reached level 3!",
        ]
        assert rig.dialogue.set_flag.call_args_list == [call("crew_loyalty_elena_reeves_50")]
        assert rig.after_action.call_args_list == [call("sold_cargo")]

    def test_polling_pays_only_new_counts(self) -> None:
        rig = _rig()
        _two_trades(rig)
        _twenty_jumps(rig)

        rig.game.check_crew_xp()

        assert rig.state["xp"] == 154
        assert rig.state["level"] == 3
        assert rig.state["loyalty"] == 50
        assert len(rig.game._mission_notifications) == 2
        assert rig.dialogue.set_flag.call_count == 1
        assert rig.after_action.call_count == 1

        rig.game.player.trades_completed = 3
        rig.game.check_crew_xp()

        # One new trade: 7 XP and 2 loyalty, and an odd count reacts as a purchase.
        assert rig.state["xp"] == 161
        assert rig.state["loyalty"] == 52
        assert len(rig.game._mission_notifications) == 2
        assert rig.dialogue.set_flag.call_count == 1
        assert rig.after_action.call_args_list == [call("sold_cargo"), call("bought_cargo")]

    def test_leadership_skills_sync_into_the_roster(self) -> None:
        rig = _rig()
        skills = rig.game.player.progression.skills

        skills["unbreakable_bonds"].current_level = 1
        skills["legend_of_the_expanse"].current_level = 1
        rig.game.check_crew_xp()

        assert rig.roster.loyalty_floor == 30
        assert rig.roster.loyalty_flag_offset == 10

        skills["unbreakable_bonds"].current_level = 0
        skills["legend_of_the_expanse"].current_level = 0
        rig.game.check_crew_xp()

        assert rig.roster.loyalty_floor == 0
        assert rig.roster.loyalty_flag_offset == 0
