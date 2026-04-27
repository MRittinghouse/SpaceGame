"""PT-L "Soft break" regression tests.

When the player's completed mission count reaches 3, the cockpit objective
hint auto-retires once. Silent — no banner, no announcement, just the
line stops appearing. Flag persists so re-load doesn't re-fire.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _fake_game(completed_count: int, hint_on: bool, flag_already_set: bool = False):
    """Build a minimal stand-in that exercises check_soft_break_retirement
    without spinning up the whole Game class."""
    from spacegame.engine.game import Game

    game = Game.__new__(Game)
    # Player
    game.player = MagicMock()
    game.player.dialogue_flags = {
        "objective_hint_auto_retired": flag_already_set,
    }
    # Mission manager
    game.mission_manager = MagicMock()
    game.mission_manager.get_completed_ids.return_value = {f"m{i}" for i in range(completed_count)}
    # HUD
    hud = MagicMock()
    hud.show_objective_hint = hint_on
    game._cockpit_hud = hud
    # Save manager (for persistence path) — return empty, accept saves
    sm = MagicMock()
    sm.load_settings.return_value = {}
    game.save_manager = sm
    game._persisted_show_objective_hint = hint_on
    return game


class TestSoftBreakRetirement:
    def test_fires_at_three_completions_when_hint_on(self) -> None:
        game = _fake_game(completed_count=3, hint_on=True)
        game.check_soft_break_retirement()
        assert game._cockpit_hud.show_objective_hint is False
        assert game.player.dialogue_flags["objective_hint_auto_retired"] is True
        # Persistence fired
        game.save_manager.save_settings.assert_called_once()

    def test_does_not_fire_under_three_completions(self) -> None:
        game = _fake_game(completed_count=2, hint_on=True)
        game.check_soft_break_retirement()
        assert game._cockpit_hud.show_objective_hint is True
        assert game.player.dialogue_flags.get("objective_hint_auto_retired", False) is False

    def test_does_not_re_fire_after_retired(self) -> None:
        """Once the flag is set, the check should early-out even if the
        hint has been manually re-enabled by the player."""
        game = _fake_game(completed_count=10, hint_on=True, flag_already_set=True)
        game.check_soft_break_retirement()
        # Hint left alone — player has owned this setting since the retirement
        assert game._cockpit_hud.show_objective_hint is True
        game.save_manager.save_settings.assert_not_called()

    def test_sets_flag_even_if_hint_already_off(self) -> None:
        """If the player has already manually disabled the hint before
        hitting 3 completions, we still set the flag so the check stops
        running — but we don't call save_settings since the state didn't
        change."""
        game = _fake_game(completed_count=3, hint_on=False)
        game.check_soft_break_retirement()
        assert game.player.dialogue_flags["objective_hint_auto_retired"] is True
        assert game._cockpit_hud.show_objective_hint is False
        game.save_manager.save_settings.assert_not_called()

    def test_handles_missing_cockpit_hud(self) -> None:
        """If HUD isn't initialized yet (e.g. new game, pre-first-frame),
        the check should no-op rather than crash."""
        from spacegame.engine.game import Game

        game = Game.__new__(Game)
        game.player = MagicMock()
        game.player.dialogue_flags = {}
        game.mission_manager = MagicMock()
        game.mission_manager.get_completed_ids.return_value = {"m1", "m2", "m3"}
        game._cockpit_hud = None
        # Should not raise
        game.check_soft_break_retirement()

    def test_handles_missing_player(self) -> None:
        from spacegame.engine.game import Game

        game = Game.__new__(Game)
        game.player = None
        game.mission_manager = MagicMock()
        game._cockpit_hud = MagicMock()
        # Should not raise
        game.check_soft_break_retirement()

    def test_persistence_failure_does_not_crash(self) -> None:
        game = _fake_game(completed_count=3, hint_on=True)
        game.save_manager.save_settings.side_effect = OSError("disk full")
        # Should not raise — persistence is best-effort
        game.check_soft_break_retirement()
        # In-memory state still flipped
        assert game._cockpit_hud.show_objective_hint is False
        assert game.player.dialogue_flags["objective_hint_auto_retired"] is True

    def test_called_from_gameplay_update_loop(self) -> None:
        """Regression guard: the check must actually be invoked from the
        per-frame gameplay update near the other check_* methods."""
        from pathlib import Path

        source = Path("spacegame/engine/game.py").read_text(encoding="utf-8")
        assert "self.check_soft_break_retirement()" in source
