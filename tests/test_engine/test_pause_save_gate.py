"""A pause inside a conversation greys Save out (the author's read of W3a, 2026-10-13).

The harness patches ``Game.__init__`` out, as ``test_save_flag_stores.py`` does, and gives
the game only what ``_open_pause_menu`` and ``_close_pause_menu`` read.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState

if TYPE_CHECKING:
    from spacegame.engine.game import Game


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _game(state: GameState) -> Game:
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game.ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    game.audio_manager = MagicMock()
    game.pause_menu_view = None
    game.paused = False
    game.state_manager = MagicMock(current_state=state)
    return game


def test_a_pause_inside_a_dialogue_greys_out_save() -> None:
    game = _game(GameState.DIALOGUE)
    game._open_pause_menu()
    assert game.pause_menu_view is not None
    assert game.pause_menu_view.save_button is not None
    assert not game.pause_menu_view.save_button.is_enabled
    game._close_pause_menu()
    game.state_manager.current_state = GameState.STATION_HUB
    game._open_pause_menu()
    assert game.pause_menu_view is not None
    assert game.pause_menu_view.save_button is not None
    assert game.pause_menu_view.save_button.is_enabled
    game._close_pause_menu()
