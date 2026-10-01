"""A save keeps the flags code writes outside a conversation (SpaceGame register F-C09).

Python keeps two flag stores. Code outside a conversation writes the player's store
alone: a mission's accept flag (``MissionManager.accept_mission``), a reward's
``set_flag`` (``apply_rewards``), the iron job's clock at a rest and its sale sensor
(``iron_consignment``), and the first sale's clear. The dialogue manager's copy is loaded
only when a conversation opens or a game loads, so a save that replaced the player's
store with that copy dropped every such flag. A save now lays the player's store over
the copy. The harness patches ``Game.__init__`` out, as
``test_scenario_procedural_board_reload.py`` does, and gives the game only what
``_save_game`` reads. The last test builds a whole Game, as ``test_new_game_factions.py``
does: the dialogue manager outlives a main-menu New Game, so the new game reloads its copy.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pygame

from spacegame.constants.flags import talked_to_npc
from spacegame.data_loader import get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.mission import MissionManager
from spacegame.models.player import Player
from tests.test_scenarios._helpers import fresh_player

if TYPE_CHECKING:
    from spacegame.engine.game import Game


def _game(player: Player) -> Game:
    """A Game whose dialogue manager holds the last conversation's copy of the flags."""
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = player
    game.dialogue_manager = DialogueManager()
    game.dialogue_manager.load_flags(player.dialogue_flags)
    for name in (
        "mission_manager",
        "crew_roster",
        "journal",
        "ground_contract_manager",
        "smuggling_contract_manager",
        "politics_manager",
        "price_history",
        "investment_manager",
        "ambient_dialogue",
    ):
        setattr(game, name, None)
    game.social_manager = MagicMock()
    game.tutorial_manager = MagicMock()
    game.save_manager = MagicMock()
    game.playtime_start = time.time()
    game.total_playtime_seconds = 0
    game.active_galaxy_events = {}
    game.markets = {}
    game.active_events = []
    game.event_log = []
    game._mission_notifications = []
    return game


def test_flags_written_outside_a_conversation_survive_a_save() -> None:
    dl = get_data_loader()
    dl.load_all()
    player = fresh_player()
    player.dialogue_flags["met_dex_halloran"] = True
    game = _game(player)
    manager = MissionManager(dl.missions)
    manager.load_state({"status": {"cargo_lost": "available"}})
    manager.accept_mission("cargo_lost", game_day=5, player=player)
    player.dialogue_flags["cargo_lost_complete"] = True  # a reward's set_flag
    player.dialogue_flags["broker_ore_sold"] = True  # the sale sensor
    game._save_game(0)
    for flag in ("cargo_lost_accepted", "cargo_lost_complete", "broker_ore_sold"):
        assert player.dialogue_flags.get(flag) is True, flag
    assert player.dialogue_flags["met_dex_halloran"] is True
    game.save_manager.save_game.assert_called_once()


def test_the_players_store_wins_over_the_last_conversations_copy() -> None:
    player = fresh_player()
    player.dialogue_flags["first_trade_bonus_available"] = True
    game = _game(player)
    player.dialogue_flags["first_trade_bonus_available"] = False  # the first sale spent it
    game.dialogue_manager.set_flag("talked_to_test_npc")  # set inside a conversation
    game._save_game(0)
    assert player.dialogue_flags["first_trade_bonus_available"] is False
    assert player.dialogue_flags["talked_to_test_npc"] is True


def test_a_new_game_keeps_none_of_the_last_games_flags() -> None:
    """The manager outlives a main-menu New Game, so the new game reloads its copy."""
    from spacegame.engine.game import Game

    game = Game()
    try:
        game.dialogue_manager.set_flag(talked_to_npc("officer_larsen"))  # the last game's copy
        game.initialize_new_game(player_name="Test")
        game.save_manager = MagicMock()
        game._save_game(0)  # the galaxy map's save, before the first conversation
        assert talked_to_npc("officer_larsen") not in game.player.dialogue_flags
        game.save_manager.save_game.assert_called_once()
    finally:
        pygame.quit()
