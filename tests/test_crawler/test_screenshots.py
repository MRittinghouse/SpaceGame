"""Screenshot-capture tests for the play-harness crawler (QF-7, Task 1)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class FakeStateManager:
    def __init__(self) -> None:
        from spacegame.config import GameState

        self.current_state = GameState.MAIN_MENU
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class ScreenshotCapturingGame:
    """Minimal game stand-in that lets tests control state and provides a Surface."""

    def __init__(self) -> None:
        import pygame

        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        import pygame_gui

        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = FakeStateManager()
        self._next_state: Any = None
        self._step_count = 0
        # Provide a real Surface so pygame.image.save succeeds.
        self.screen = pygame.display.get_surface()

        from spacegame.engine.input_handler import InputHandler

        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list) -> None:
        self._step_count += 1
        if self._next_state is not None:
            self.state_manager.change_state(self._next_state)
            self._next_state = None


class TestScreenshotCapture:
    """Tests for QF-7 screenshot-on-first-visit hook."""

    def _make_crawler(self, tmp_path: Path, screenshot_dir: str = "screenshots") -> Any:
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game_instance = ScreenshotCapturingGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game_instance)
        crawler = Crawler(
            seed=42,
            actions=10,
            screenshot_dir=screenshot_dir,
            output_dir=str(tmp_path / "crawler_runs"),
            fixtures=fixtures,
        )
        return crawler, game_instance

    def test_screenshot_dir_none_disables_capture(self, tmp_path: Path) -> None:
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game_instance = ScreenshotCapturingGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game_instance)
        crawler = Crawler(
            seed=42,
            actions=5,
            screenshot_dir=None,
            output_dir=str(tmp_path / "crawler_runs"),
            fixtures=fixtures,
        )
        crawler.run()
        run_dir = crawler.write_reports()
        screenshots_dir = run_dir / "screenshots"
        assert not screenshots_dir.exists(), (
            "screenshots dir should not exist when screenshot_dir=None"
        )

    def test_screenshot_capture_writes_one_png_per_reached_state(self, tmp_path: Path) -> None:
        from spacegame.config import GameState
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game_instance = ScreenshotCapturingGame()

        all_states = list(GameState)
        state_idx = [0]

        def pre_step(action_index: int, action: Any) -> None:
            # Cycle through a few states deterministically.
            if action_index % 2 == 0 and state_idx[0] < len(all_states):
                game_instance._next_state = all_states[state_idx[0] % len(all_states)]
                state_idx[0] += 1

        fixtures = CrawlerFixtures(
            game_factory=lambda: game_instance,
            pre_step_hook=pre_step,
        )
        crawler = Crawler(
            seed=42,
            actions=20,
            screenshot_dir="screenshots",
            output_dir=str(tmp_path / "crawler_runs"),
            fixtures=fixtures,
        )
        crawler.run()
        run_dir = crawler.write_reports()

        screenshots_dir = run_dir / "screenshots"
        assert screenshots_dir.exists(), "screenshots directory should be created"

        # Every reached state should have exactly one PNG.
        reached = {
            name for name, was_reached in crawler.coverage.states_reached.items() if was_reached
        }
        assert len(reached) > 0, "crawler should have reached at least one state"

        for name in reached:
            png = screenshots_dir / f"{name}.png"
            assert png.exists(), f"Expected screenshot for reached state {name!r}"

        # No PNG for unreached states.
        not_reached = {
            name for name, was_reached in crawler.coverage.states_reached.items() if not was_reached
        }
        for name in not_reached:
            png = screenshots_dir / f"{name}.png"
            assert not png.exists(), f"Should not have screenshot for unreached state {name!r}"

    def test_screenshot_capture_is_first_visit_only(self, tmp_path: Path) -> None:
        """A state visited twice should produce exactly one PNG (from the first visit)."""
        from spacegame.config import GameState
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game_instance = ScreenshotCapturingGame()
        target_state = GameState.GALAXY_MAP
        visit_count = [0]

        def pre_step(action_index: int, action: Any) -> None:
            # Always switch to GALAXY_MAP so it gets visited many times.
            game_instance._next_state = target_state
            visit_count[0] += 1

        fixtures = CrawlerFixtures(
            game_factory=lambda: game_instance,
            pre_step_hook=pre_step,
        )
        crawler = Crawler(
            seed=42,
            actions=10,
            screenshot_dir="screenshots",
            output_dir=str(tmp_path / "crawler_runs"),
            fixtures=fixtures,
        )
        crawler.run()
        run_dir = crawler.write_reports()

        screenshots_dir = run_dir / "screenshots"
        png = screenshots_dir / f"{target_state.name}.png"
        assert png.exists(), "PNG should exist for visited state"

        # Only one file should exist with that name (no duplicates, no collision).
        all_pngs = list(screenshots_dir.glob("*.png"))
        matching = [p for p in all_pngs if p.stem == target_state.name]
        assert len(matching) == 1, (
            f"Expected exactly 1 PNG for {target_state.name}, got {len(matching)}"
        )

        # The file should have been written only once: its size > 0.
        assert png.stat().st_size > 0, "PNG file should not be empty"
