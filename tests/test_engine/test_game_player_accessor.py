"""Three-part contract test for the Game.player raising accessor.

SH-1 introduces ``Game._player: Optional[Player]`` as raw storage and a
``@property player -> Player`` that raises ``RuntimeError`` when the storage
is ``None``.  These tests verify the three lifecycle states of that accessor:

1. Before ``initialize_new_game()``     — must raise
2. After  ``initialize_new_game()``     — must return a live Player
3. After  ``game._player = None`` reset — must raise again
"""

from __future__ import annotations

import os

import pygame
import pytest

# Headless SDL so Game() can be constructed without a physical display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from spacegame.engine.game import Game


class TestGamePlayerAccessor:
    def test_game_player_raises_before_initialize_new_game(self) -> None:
        """Game.player must raise RuntimeError on a freshly constructed Game."""
        game = Game()
        try:
            with pytest.raises(RuntimeError) as excinfo:
                _ = game.player
            msg = str(excinfo.value)
            assert "Game" in msg, f"Expected 'Game' in error message; got: {msg!r}"
            assert "player" in msg, f"Expected 'player' in error message; got: {msg!r}"
            assert "initialize_new_game" in msg, (
                f"Expected 'initialize_new_game' in error message; got: {msg!r}"
            )
        finally:
            pygame.quit()

    def test_game_player_returns_after_initialize_new_game(self) -> None:
        """Game.player must return a live Player after initialize_new_game()."""
        game = Game()
        try:
            game.initialize_new_game(player_name="Test")
            player = game.player
            assert player is not None, (
                "player property must return non-None after initialize_new_game"
            )
            assert hasattr(player, "credits"), "returned Player must have .credits attribute"
        finally:
            pygame.quit()

    def test_game_player_raises_after_main_menu_reset(self) -> None:
        """Game.player must raise again after _player is cleared (main-menu reset)."""
        game = Game()
        try:
            game.initialize_new_game(player_name="Test")
            # Mirror the MAIN_MENU -> New Game closure at line 1076
            game._player = None
            with pytest.raises(RuntimeError) as excinfo:
                _ = game.player
            msg = str(excinfo.value)
            assert "Game" in msg
            assert "player" in msg
            assert "initialize_new_game" in msg
        finally:
            pygame.quit()
