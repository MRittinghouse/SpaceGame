"""Oracle 2 (UI leak on state exit) + Oracle 3 (softlock) tests (QF-6)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pygame_gui  # noqa: E402

from spacegame.config import GameState  # noqa: E402
from spacegame.engine.input_handler import InputHandler  # noqa: E402
from tools.crawler.crawler import Crawler, CrawlerFixtures


class LeakStateManager:
    """State manager that fires change_state() with a hook to simulate leaks."""

    def __init__(self, game: Any) -> None:
        self.current_state: GameState | None = None
        self.state_stack: list = []
        self.game = game

    def change_state(self, new_state: GameState) -> None:
        # If prior state has a "leaky exit", we simulate the leak by
        # adding an extra UI element that would normally be killed.
        if getattr(self.game, "leak_on_next_exit", False):
            self.game.leak_on_next_exit = False
            pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(400, 400, 60, 20),
                text="LEAK",
                manager=self.game.ui_manager,
            )
        self.current_state = new_state


class LeakyGame:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.leak_on_next_exit = False
        self.state_manager = LeakStateManager(self)
        self.player = None
        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        pass


class TestUILeakOracle:
    def test_ui_leak_oracle_flags_stateexit_leak(self) -> None:
        game = LeakyGame()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        # First transition establishes baseline. No leak yet.
        game.state_manager.change_state(GameState.GALAXY_MAP)
        # Prime the leak flag then transition.
        game.leak_on_next_exit = True
        game.state_manager.change_state(GameState.STATION_HUB)

        leaks = [c for c in crawler.crashes.values() if c.oracle == "ui_leak"]
        assert leaks, "UI leak oracle should have recorded the deliberate leak"
        assert "UIElementLeak" in leaks[0].exception_class


class SoftlockGame:
    """A game whose current state has zero interactive elements and no escape."""

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = _SoftlockSM()
        self.player = None  # No player = no ESC binding either
        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        pass


class _SoftlockSM:
    def __init__(self) -> None:
        # GALAXY_MAP is NOT in the softlock-exempt set.
        self.current_state = GameState.GALAXY_MAP
        self.state_stack: list = []

    def change_state(self, new_state: GameState) -> None:
        self.current_state = new_state


class TestSoftlockOracle:
    def test_softlock_oracle_detects_dead_end(self) -> None:
        game = SoftlockGame()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()

        # The player is None, so no ESC is bound. But F11 IS always bound.
        # For a true softlock scenario, we clear that too by clearing the
        # bound_escape_keys via monkeypatch:
        original = crawler.bound_escape_keys
        crawler.bound_escape_keys = lambda: []  # type: ignore[assignment]
        try:
            crawler.step_once()
        finally:
            crawler.bound_escape_keys = original  # type: ignore[assignment]

        softlocks = [c for c in crawler.crashes.values() if c.oracle == "softlock"]
        assert softlocks, "Softlock oracle should have flagged the dead end"

    def test_softlock_oracle_exempts_main_menu(self) -> None:
        game = SoftlockGame()
        game.state_manager.current_state = GameState.MAIN_MENU
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        crawler.bound_escape_keys = lambda: []  # type: ignore[assignment]
        crawler.step_once()
        softlocks = [c for c in crawler.crashes.values() if c.oracle == "softlock"]
        assert not softlocks, "MAIN_MENU is exempt from softlock oracle"
