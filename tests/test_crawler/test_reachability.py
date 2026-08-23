"""Crawler reachability tests (QF-6B, Tasks 1, 2, 3, 4, 5, 7).

Verifies the two blockers found in post-QF-6 verification are fixed:

Blocker 1 — event-cycle: synthetic clicks generate UI_BUTTON_PRESSED events
that pygame_gui posts to the global queue, but the crawler's step_once() never
drained that queue, so button presses were never delivered to views.

Blocker 2 — hand-drawn dialogs: once the "New Game" confirmation dialog
opens, enumerate_interactive() returns nothing because the dialog uses raw
pygame.Rect hit-testing rather than pygame_gui widgets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from spacegame.config import GameState
from spacegame.save_manager import SaveManager
from tools.crawler.crawler import Crawler

# Path to the crawler fixtures directory (has real save files for slots 1-3).
_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tools" / "crawler" / "fixtures"


class TestNewGameClickReachesConfirmationDialog:
    """AC-1: clicking New Game within the crawl loop opens the confirmation dialog."""

    def test_new_game_click_reaches_confirmation_dialog(self) -> None:
        """A synthetic click on New Game must flip _confirm_new_game to True.

        Requires the event-cycle fix (Blocker 1): UI_BUTTON_PRESSED posted by
        pygame_gui in frame N must be delivered to the view in frame N+1.
        """
        # Boot without checkpoint — game starts in MAIN_MENU.
        crawler = Crawler(seed=42, actions=0)
        crawler.boot()

        # Point the view's save_manager at the crawler fixtures directory so
        # that has_saves=True when the New Game button is clicked, causing the
        # confirmation dialog to appear instead of jumping straight to GALAXY_MAP.
        view = crawler.game.main_menu_view
        view.save_manager = SaveManager(save_directory=_FIXTURES_DIR)

        # Find the New Game button.
        interactive = crawler.enumerate_interactive()
        new_game_btn = next(
            (e for e in interactive if getattr(e, "text", "") == "New Game"),
            None,
        )
        assert new_game_btn is not None, (
            "New Game button not found in main-menu interactive elements"
        )

        # Pre-condition: confirmation dialog is not open.
        assert not view._confirm_new_game

        # Patch _select_action so the first step clicks New Game and the second
        # step is a no-op. This gives a controlled two-frame sequence without
        # depending on the action RNG.
        actions: list[Any] = [("click", new_game_btn), ("advance_time",)]
        call_count = [0]
        original_select = crawler._select_action

        def _patched_select() -> Any:
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(actions):
                return actions[idx]
            return original_select()

        crawler._select_action = _patched_select  # type: ignore[method-assign]

        # Frame 1: synthesize the click. Without the event-cycle fix, the
        # resulting UI_BUTTON_PRESSED stays stranded in the pygame queue and
        # the view never sees it.
        crawler.step_once()

        # Frame 2: with the fix, _pending_events carries UI_BUTTON_PRESSED into
        # game.step(), which delivers it to MainMenuView.handle_event().
        # Without the fix, nothing happens and _confirm_new_game stays False.
        crawler.step_once()

        assert view._confirm_new_game, (
            "Clicking 'New Game' should set _confirm_new_game=True "
            "within the crawl loop (requires event-cycle fix)"
        )


class TestCrawlerReachesGalaxyMap:
    """AC-2: crawler can navigate past MAIN_MENU to reach GameState.GALAXY_MAP."""

    def test_crawler_reaches_galaxy_map_from_main_menu(self) -> None:
        """A bounded crawl session progresses from MAIN_MENU to GALAXY_MAP.

        After the event-cycle fix, clicking "Continue" delivers the
        UI_BUTTON_PRESSED event which loads the saved game and transitions
        the state to GALAXY_MAP.

        Without the fix: UI events are stranded, no button press succeeds,
        and the crawler stays in MAIN_MENU for the entire session.
        """
        # Boot without checkpoint — game starts in MAIN_MENU.
        crawler = Crawler(seed=42, actions=0)
        crawler.boot()

        view = crawler.game.main_menu_view

        # Point the view's save_manager at the fixtures directory so
        # the Continue button can be enabled (fixtures has slot 1).
        view.save_manager = SaveManager(save_directory=_FIXTURES_DIR)

        # Re-enable the Continue button (it was disabled in on_enter because
        # the original save_manager had no saves at that point).
        if view.continue_button is not None:
            view.continue_button.enable()

        # Also point game.save_manager at fixtures so _load_game() succeeds
        # when next_state == "continue" is processed.
        crawler.game.save_manager = SaveManager(save_directory=_FIXTURES_DIR)

        # Force the crawler to click Continue first (deterministic).
        assert view.continue_button is not None
        actions: list[Any] = [("click", view.continue_button), ("advance_time",)]
        call_count = [0]
        original_select = crawler._select_action

        def _patched_select() -> Any:
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(actions):
                return actions[idx]
            return original_select()

        crawler._select_action = _patched_select  # type: ignore[method-assign]
        crawler.config.actions = 10

        # Run a short session.
        crawler.run()

        reached = crawler.coverage.states_reached
        assert reached.get("GALAXY_MAP", False), (
            f"Expected GALAXY_MAP to be reached. "
            f"States reached: {[k for k, v in reached.items() if v]}"
        )


class TestCoverageFloorReachesMinStates:
    """AC-3: seeded 2,000-action session reaches at least N of 41 GameState values."""

    # Floor value is a ratchet start (8); implementer ratchets to max(8, measured)
    # before marking the sprint done.
    COVERAGE_FLOOR = 8

    def test_coverage_floor_reaches_min_states(self) -> None:
        """A 2,000-action seed=42 session reaches >= COVERAGE_FLOOR states.

        Uses the 'early' checkpoint which starts in GALAXY_MAP with a full
        player save, giving the crawler access to all game systems.
        Without the event-cycle fix the crawler is stuck in GALAXY_MAP
        (all button presses produce stranded UI events, so only 1 state
        is visited). After the fix, buttons work and many states are reached.
        """
        crawler = Crawler(seed=42, actions=2000, checkpoint="early")
        crawler.boot()
        crawler.run()

        reached = {k for k, v in crawler.coverage.states_reached.items() if v}
        assert len(reached) >= self.COVERAGE_FLOOR, (
            f"Coverage floor not met: reached {len(reached)} states "
            f"(need >= {self.COVERAGE_FLOOR}). "
            f"States reached: {sorted(reached)}"
        )
