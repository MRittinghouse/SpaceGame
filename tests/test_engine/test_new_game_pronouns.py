"""A new game takes the captain's pronouns (writing discipline spec 2.5).

Until SP6's creator asks for them, every new game is they/them.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pygame

from spacegame.config import GameState
from spacegame.engine.game import Game
from spacegame.models.captain_tokens import Pronouns


def test_a_new_game_defaults_to_they_them() -> None:
    game = Game()
    try:
        game.initialize_new_game(player_name="Test")
        assert game.player.pronouns is Pronouns.THEY
    finally:
        pygame.quit()


def test_a_new_game_takes_the_choice() -> None:
    game = Game()
    try:
        game.initialize_new_game(player_name="Test", pronouns=Pronouns.SHE)
        assert game.player.pronouns is Pronouns.SHE
    finally:
        pygame.quit()


def test_the_dialogue_manager_addresses_the_new_player() -> None:
    game = Game()
    try:
        game.initialize_new_game(player_name="Test", pronouns=Pronouns.HE)
        assert game.dialogue_manager.player is game.player
    finally:
        pygame.quit()


def test_a_second_new_game_plays_the_intro_to_no_player() -> None:
    game = Game()
    try:
        game.initialize_new_game(player_name="First", pronouns=Pronouns.HE)
        game.main_menu_view = MagicMock(active=True)
        game.main_menu_view.get_next_state.return_value = GameState.GALAXY_MAP
        with patch.object(game, "_start_transition", lambda kind, duration, callback: callback()):
            game._route_from_main_menu()
        assert game.dialogue_manager.player is None
    finally:
        pygame.quit()
