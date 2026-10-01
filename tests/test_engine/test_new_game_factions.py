"""BB-74: a new game takes the content's faction map, whatever the entropy."""

from __future__ import annotations

import os

import pygame

# Headless SDL so Game() can be constructed without a physical display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from spacegame.engine.game import Game
from tests.test_data.test_faction_map import GUIDE_MAP


def test_a_new_game_holds_the_guide_map() -> None:
    game = Game()
    try:
        game.initialize_new_game(player_name="Test")
        assert game.player.faction_assignments == GUIDE_MAP
        assert game.player.get_faction_for_system("herons_mark") is None
        assert set(game.player.faction_reputation) == set(game.data_loader.factions)
        union = game.data_loader.factions["miners_union"].name
        assert game.data_loader.systems["breakstone"].faction == union
    finally:
        pygame.quit()
