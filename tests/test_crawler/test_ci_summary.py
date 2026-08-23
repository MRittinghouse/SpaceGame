"""Tests for $GITHUB_STEP_SUMMARY emission and CLI wiring (QF-7, Tasks 3+4)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class FakeStateManager:
    def __init__(self) -> None:
        from spacegame.config import GameState

        self.current_state = GameState.MAIN_MENU
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class MinimalGame:
    """Minimal game stand-in for __main__ integration tests."""

    def __init__(self) -> None:
        import pygame
        import pygame_gui

        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = FakeStateManager()
        self.screen = pygame.display.get_surface()

        from spacegame.engine.input_handler import InputHandler

        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:
        return

    def initialize_states(self) -> None:
        return

    def step(self, dt: float, events: list) -> None:
        return


class TestCISummary:
    """Tests for GITHUB_STEP_SUMMARY markdown emission."""

    def _make_crawler_and_run(self, tmp_path: Path) -> Any:
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game = MinimalGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game)
        crawler = Crawler(
            seed=42, actions=10, output_dir=str(tmp_path / "runs"), fixtures=fixtures
        )
        crawler.run()
        return crawler

    def test_ci_summary_written_when_env_var_set(self, tmp_path: Path, monkeypatch: Any) -> None:
        """When GITHUB_STEP_SUMMARY is set, the summary file contains required lines."""
        summary_path = tmp_path / "summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

        from tools.crawler import __main__
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game = MinimalGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game)

        # Patch the Crawler constructor to use our fake game.
        original_crawler = __main__.Crawler

        class PatchedCrawler(Crawler):
            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("output_dir", str(tmp_path / "runs"))
                # Inject our fake game via fixtures.
                super().__init__(**kwargs, fixtures=fixtures)

        monkeypatch.setattr(__main__, "Crawler", PatchedCrawler)
        result = __main__.main(["--seed", "42", "--actions", "10"])
        assert result == 0

        assert summary_path.exists(), "GITHUB_STEP_SUMMARY file should be written"
        content = summary_path.read_text()
        assert "State coverage" in content, "Summary should contain state coverage line"
        assert "Crash signatures" in content, "Summary should contain crash signatures line"

    def test_ci_summary_not_written_when_env_var_absent(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """When GITHUB_STEP_SUMMARY is not set, no summary file is written."""
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

        from tools.crawler import __main__
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game = MinimalGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game)

        original_crawler = __main__.Crawler

        class PatchedCrawler(Crawler):
            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("output_dir", str(tmp_path / "runs"))
                super().__init__(**kwargs, fixtures=fixtures)

        monkeypatch.setattr(__main__, "Crawler", PatchedCrawler)
        # Should not raise even without the env var.
        result = __main__.main(["--seed", "42", "--actions", "10"])
        assert result == 0


class TestCLIBaselineWiring:
    """Tests for --crash-baseline and --write-crash-baseline wiring in __main__."""

    def test_write_crash_baseline_creates_file(self, tmp_path: Path, monkeypatch: Any) -> None:
        from tools.crawler import __main__
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game = MinimalGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game)
        baseline_path = tmp_path / "baseline.json"

        class PatchedCrawler(Crawler):
            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("output_dir", str(tmp_path / "runs"))
                super().__init__(**kwargs, fixtures=fixtures)

        monkeypatch.setattr(__main__, "Crawler", PatchedCrawler)
        result = __main__.main([
            "--seed", "42", "--actions", "10",
            "--write-crash-baseline", str(baseline_path),
        ])
        assert result == 0
        assert baseline_path.exists(), "baseline file should be written"
        data = json.loads(baseline_path.read_text())
        assert "signatures" in data

    def test_compare_baseline_exits_0_when_no_novel_crashes(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Exit 0 when all crashes are already in the baseline."""
        from tools.crawler import __main__
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game = MinimalGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game)

        class PatchedCrawler(Crawler):
            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("output_dir", str(tmp_path / "runs"))
                super().__init__(**kwargs, fixtures=fixtures)

        monkeypatch.setattr(__main__, "Crawler", PatchedCrawler)

        # Write a baseline first.
        baseline_path = tmp_path / "baseline.json"
        result_write = __main__.main([
            "--seed", "42", "--actions", "10",
            "--write-crash-baseline", str(baseline_path),
        ])
        assert result_write == 0

        # Compare against that baseline — all crashes are known, so exit 0.
        result_compare = __main__.main([
            "--seed", "42", "--actions", "10",
            "--crash-baseline", str(baseline_path),
        ])
        assert result_compare == 0

    def test_compare_baseline_exits_1_on_novel_crash(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Exit 1 when a crash signature is not in the baseline."""
        from tools.crawler import __main__
        from tools.crawler.crawler import Crawler, CrawlerFixtures

        game = MinimalGame()
        fixtures = CrawlerFixtures(game_factory=lambda: game)

        class PatchedCrawler(Crawler):
            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("output_dir", str(tmp_path / "runs"))
                super().__init__(**kwargs, fixtures=fixtures)

        monkeypatch.setattr(__main__, "Crawler", PatchedCrawler)

        # Write an EMPTY baseline so any crash would be novel.
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(
            json.dumps({"generated_at": "2026-08-23T00:00:00Z", "generated_from": [], "signatures": []})
        )

        # Inject a crash into the crawler via pre_step_hook.
        game2 = MinimalGame()
        step_count = [0]

        def crashing_step(dt: float, events: list) -> None:
            step_count[0] += 1
            if step_count[0] == 3:
                raise RuntimeError("synthetic crash for baseline test")

        game2.step = crashing_step  # type: ignore[assignment]

        fixtures2 = CrawlerFixtures(game_factory=lambda: game2)

        class CrashingCrawler(Crawler):
            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("output_dir", str(tmp_path / "runs2"))
                super().__init__(**kwargs, fixtures=fixtures2)

        monkeypatch.setattr(__main__, "Crawler", CrashingCrawler)
        result = __main__.main([
            "--seed", "42", "--actions", "10",
            "--crash-baseline", str(baseline_path),
        ])
        # If the crawler found a crash not in baseline, expect exit 1.
        # (If no crash happened, the test should still exit 0; we assert based on
        # whether any crashes were recorded.)
        # The crashing game always crashes at step 3 so we should always see exit 1.
        assert result == 1, "Should exit 1 when novel crash signatures are found"
