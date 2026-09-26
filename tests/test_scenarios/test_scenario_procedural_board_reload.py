"""A same-day reload never re-offers an accepted procedural contract.

Board content is keyed by (player seed, system, day), so the refresh that runs
when the player re-enters the station hub after a load rebuilds the board the
player saw before saving. The rebuilt copy of an accepted contract must collide
with the restored mission's ID rather than appear as a second, identical offer.

The ``_game_for`` helper patches ``Game.__init__`` out (the pattern in
``test_scenario_post_capstone_generation.py``) and wires the mission manager
and generator the way ``Game._load_game`` does. ``_refresh_procedural_missions``
is the real method.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import Mission, MissionManager, MissionStatus
from spacegame.models.player import Player
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.sim_rng import stable_seed
from tests.test_scenarios._helpers import fresh_player, round_trip_save

if TYPE_CHECKING:
    from spacegame.engine.game import Game


def _game_for(player: Player) -> Game:
    """A Game holding only what the board refresh reads, wired as ``_load_game`` wires it."""
    from spacegame.engine.game import Game

    dl = get_data_loader()
    dl.load_all()
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game.data_loader = dl
    game._player = player
    game.mission_manager = MissionManager(list(dl.missions))
    if player.mission_state:
        game.mission_manager.load_state(player.mission_state)
    game.mission_manager.update_availability(
        player.dialogue_flags,
        player_reputation=player.faction_reputation,
        game_day=player.game_day,
        player=player,
    )
    game.procedural_mission_gen = ProceduralMissionGenerator(
        systems=dl.systems,
        commodities=dl.commodities,
        enemy_templates=dl.enemy_templates,
        seed=stable_seed("player", player.name),
    )
    game._proc_missions_day = -1
    return game


def _content(mission: Mission) -> dict[str, Any]:
    """A mission's definition without its ID, to spot a copy under another name."""
    data = mission.to_dict()
    del data["id"]
    return data


def _procedural(manager: MissionManager) -> list[Mission]:
    return [
        mission
        for status in MissionStatus
        for mission in manager.get_missions_by_status(status)
        if mission.id.startswith("proc_")
    ]


class TestProceduralBoardReload:
    def test_same_day_reload_does_not_reoffer_an_accepted_contract(self) -> None:
        player = fresh_player(name="Ledger Scenario")
        player.game_day = 4
        game = _game_for(player)
        game._refresh_procedural_missions()  # board one, day 4

        player.game_day = 5
        game._refresh_procedural_missions()  # board two, day 5
        board = [m.id for m in _procedural(game.mission_manager)]
        assert board, "board two should offer procedural contracts"
        accepted_id = board[0]
        ok, msg = game.mission_manager.accept_mission(accepted_id, game_day=5, player=player)
        assert ok, msg
        accepted_mission = game.mission_manager.get_mission(accepted_id)
        assert accepted_mission is not None
        accepted = _content(accepted_mission)

        # Save (as _save_game syncs mission state), then load and re-enter the hub on day 5.
        player.mission_state = game.mission_manager.get_state()
        restored = round_trip_save(player)
        reloaded = _game_for(restored)
        reloaded._refresh_procedural_missions()
        manager = reloaded.mission_manager

        assert manager.get_status(accepted_id) == MissionStatus.ACTIVE, (
            "the accepted contract must survive the load and the board refresh"
        )
        twins = [m.id for m in _procedural(manager) if _content(m) == accepted]
        assert twins == [accepted_id], (
            f"the refreshed board re-offers the accepted contract under another ID: {twins}"
        )

        copies = [
            m
            for m in reloaded.procedural_mission_gen.generate_for_system(
                restored.current_system_id, 5
            )
            if _content(m) == accepted
        ]
        assert copies, "the same-day board must regenerate the accepted contract's content"
        for copy in copies:
            added, _msg = manager.add_mission(copy)
            assert not added, f"a regenerated copy must collide with {accepted_id}"
        accepted_again, _msg = manager.accept_mission(accepted_id, game_day=5, player=restored)
        assert not accepted_again, "an ACTIVE contract cannot be accepted a second time"
