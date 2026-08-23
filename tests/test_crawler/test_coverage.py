"""Coverage tracker tests (QF-6, Task 10)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pygame_gui  # noqa: E402

from spacegame.config import GameState  # noqa: E402
from spacegame.engine.input_handler import InputHandler  # noqa: E402
from tools.crawler.coverage import CoverageTracker  # noqa: E402
from tools.crawler.crawler import Crawler, CrawlerFixtures  # noqa: E402


class TestCoverageTracker:
    def test_all_41_states_are_present_after_init(self) -> None:
        tracker = CoverageTracker()
        assert len(tracker.states_reached) == 41
        assert all(v is False for v in tracker.states_reached.values())

    def test_coverage_report_lists_all_41_states(self) -> None:
        tracker = CoverageTracker()
        for state in GameState:
            assert state.name in tracker.states_reached

    def test_record_visit_flips_flag(self) -> None:
        tracker = CoverageTracker()
        tracker.record_visit(GameState.GALAXY_MAP)
        assert tracker.states_reached["GALAXY_MAP"] is True

    def test_record_transition_appends_and_visits(self) -> None:
        tracker = CoverageTracker()
        tracker.record_transition(GameState.MAIN_MENU, GameState.GALAXY_MAP)
        assert ("MAIN_MENU", "GALAXY_MAP") in tracker.transitions
        assert tracker.states_reached["GALAXY_MAP"] is True

    def test_serializes_to_json_shape(self) -> None:
        tracker = CoverageTracker()
        tracker.record_transition(None, GameState.MAIN_MENU)
        data = tracker.to_dict()
        assert "states_reached" in data
        assert "transitions" in data
        assert isinstance(data["transitions"][0], list)


class _CoverageSM:
    def __init__(self) -> None:
        self.current_state = GameState.MAIN_MENU
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class _CoverageGame:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = _CoverageSM()
        self.player = None
        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        pass


class TestCoverageIntegration:
    def test_coverage_report_records_transitions(self) -> None:
        game = _CoverageGame()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()

        # Drive a few transitions via the instrumented state_manager.
        game.state_manager.change_state(GameState.GALAXY_MAP)
        game.state_manager.change_state(GameState.STATION_HUB)
        game.state_manager.change_state(GameState.TRADING)

        assert crawler.coverage.states_reached["GALAXY_MAP"] is True
        assert crawler.coverage.states_reached["STATION_HUB"] is True
        assert crawler.coverage.states_reached["TRADING"] is True

        assert crawler.coverage.transitions[0] == ("MAIN_MENU", "GALAXY_MAP")
        assert crawler.coverage.transitions[-1] == ("STATION_HUB", "TRADING")
