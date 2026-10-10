"""A new game takes the captain's pronouns (writing discipline spec 2.5).

Until SP6's creator asks for them, every new game is they/them.
"""

from __future__ import annotations

import pygame

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
