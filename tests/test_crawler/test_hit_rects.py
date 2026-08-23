"""Hit-rect registry tests (QF-6B, Task 3).

Verifies:
- HIT_RECTS[GameState.MAIN_MENU] contains Yes and No entries.
- hit_rects_for(game) returns them only when _confirm_new_game is truthy.
- hit_rects_for(game) returns empty when the predicate is False.
- Drift detection: removing _confirm_new_game from the view raises
  HitRectDriftError.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from spacegame.config import GameState
from tools.crawler.hit_rects import HIT_RECTS, HitRectDriftError, hit_rects_for


def _make_game(confirm_flag: bool = False, *, remove_confirm_attr: bool = False) -> Any:
    """Build a minimal game stub for hit-rect tests.

    Args:
        confirm_flag: Value to set on the view's _confirm_new_game attribute.
        remove_confirm_attr: If True, remove _confirm_new_game from the view
            to simulate a refactored/renamed attribute.
    """
    view = MagicMock()
    if remove_confirm_attr:
        # Remove the attribute entirely so predicate raises AttributeError.
        del view._confirm_new_game
    else:
        view._confirm_new_game = confirm_flag

    state_manager = MagicMock()
    state_manager.current_state = GameState.MAIN_MENU
    state_manager.get_current_view.return_value = view

    game = MagicMock()
    game.state_manager = state_manager
    return game


class TestHitRectRegistryContents:
    """Registry has correct entries for MAIN_MENU."""

    def test_main_menu_has_yes_and_no_entries(self) -> None:
        entries = HIT_RECTS.get(GameState.MAIN_MENU, [])
        names = {hr.name for hr in entries}
        assert "confirm_new_game_yes" in names, (
            "HIT_RECTS[MAIN_MENU] must have a 'confirm_new_game_yes' entry"
        )
        assert "confirm_new_game_no" in names, (
            "HIT_RECTS[MAIN_MENU] must have a 'confirm_new_game_no' entry"
        )

    def test_yes_entry_has_dialog_dismissal_keys(self) -> None:
        import pygame

        yes_entry = next(
            hr for hr in HIT_RECTS[GameState.MAIN_MENU] if hr.name == "confirm_new_game_yes"
        )
        assert pygame.K_y in yes_entry.dismissal_keys
        assert pygame.K_RETURN in yes_entry.dismissal_keys

    def test_no_entry_has_dialog_dismissal_keys(self) -> None:
        import pygame

        no_entry = next(
            hr for hr in HIT_RECTS[GameState.MAIN_MENU] if hr.name == "confirm_new_game_no"
        )
        assert pygame.K_n in no_entry.dismissal_keys
        assert pygame.K_ESCAPE in no_entry.dismissal_keys


class TestHitRectsForResolver:
    """hit_rects_for correctly filters by predicate and returns live rects."""

    def test_returns_empty_when_dialog_not_open(self) -> None:
        game = _make_game(confirm_flag=False)
        result = hit_rects_for(game)
        assert result == [], "hit_rects_for must return empty when _confirm_new_game is False"

    def test_returns_both_rects_when_dialog_open(self) -> None:
        game = _make_game(confirm_flag=True)
        result = hit_rects_for(game)
        names = {hr.name for hr, _ in result}
        assert "confirm_new_game_yes" in names
        assert "confirm_new_game_no" in names

    def test_rects_are_pygame_rect_instances(self) -> None:
        import pygame

        game = _make_game(confirm_flag=True)
        result = hit_rects_for(game)
        for hr, rect in result:
            assert isinstance(rect, pygame.Rect), (
                f"rect_fn for {hr.name!r} must return a pygame.Rect, got {type(rect)}"
            )

    def test_rect_for_yes_is_left_of_rect_for_no(self) -> None:
        """Yes button is to the left of No button (matches handle_event geometry)."""
        game = _make_game(confirm_flag=True)
        result = hit_rects_for(game)
        by_name = {hr.name: rect for hr, rect in result}
        assert by_name["confirm_new_game_yes"].x < by_name["confirm_new_game_no"].x, (
            "Yes rect must be left of No rect (matches MainMenuView.handle_event geometry)"
        )

    def test_returns_empty_for_unregistered_state(self) -> None:
        game = _make_game()
        game.state_manager.current_state = GameState.TRADING
        result = hit_rects_for(game)
        assert result == []

    def test_returns_empty_when_view_is_none(self) -> None:
        game = _make_game(confirm_flag=True)
        game.state_manager.get_current_view.return_value = None
        result = hit_rects_for(game)
        assert result == []


class TestHitRectRegistryRaisesOnDrift:
    """Drift detection: rect_fn failure raises HitRectDriftError."""

    def test_hit_rect_registry_raises_on_drift(self) -> None:
        """Patching the view to break rect_fn must raise HitRectDriftError.

        The test simulates a drift scenario by making the rect_fn throw.
        We patch the predicate to return True (so the entry is active) but
        make the rect_fn raise AttributeError (simulating a renamed attr).
        """
        import pygame

        from tools.crawler.hit_rects import HitRect

        def _bad_rect_fn(view: Any) -> Any:
            raise AttributeError("_confirm_font has been renamed — registry drift")

        drifted_entry = HitRect(
            name="drifted_entry",
            rect_fn=_bad_rect_fn,
            predicate=lambda v: True,
        )

        game = _make_game(confirm_flag=True)

        # Temporarily inject the drifted entry into the registry.
        original = HIT_RECTS[GameState.MAIN_MENU]
        HIT_RECTS[GameState.MAIN_MENU] = [drifted_entry]
        try:
            try:
                hit_rects_for(game)
                assert False, "Expected HitRectDriftError was not raised"
            except HitRectDriftError as exc:
                assert "drifted_entry" in str(exc), (
                    "HitRectDriftError message must name the offending entry"
                )
        finally:
            HIT_RECTS[GameState.MAIN_MENU] = original
