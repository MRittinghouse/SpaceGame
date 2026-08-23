"""Crash dedup + replay tests (QF-6, Tasks 8-9)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pygame_gui  # noqa: E402

from spacegame.config import GameState  # noqa: E402
from spacegame.engine.input_handler import InputHandler  # noqa: E402
from tools.crawler.crash_record import normalized_signature  # noqa: E402
from tools.crawler.crawler import Crawler, CrawlerFixtures  # noqa: E402


class _SM:
    def __init__(self) -> None:
        self.current_state = GameState.GALAXY_MAP
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class RepeatCrashGame:
    """Raises the SAME RuntimeError on every step from a specific site."""

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = _SM()
        self.player = None
        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        # Raise from the same call site each time so the traceback
        # signature is stable.
        _throw()


def _throw() -> None:
    raise RuntimeError("same-site failure")


class DifferentCrashGame:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = _SM()
        self.player = None
        self.input_handler = InputHandler()
        self._n = 0

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        n = self._n
        self._n += 1
        if n % 2 == 0:
            _throw_a()
        else:
            _throw_b()


def _throw_a() -> None:
    raise RuntimeError("A")


def _throw_b() -> None:
    raise ValueError("B")


def _throw_planted() -> None:
    raise RuntimeError("planted crash")


class TestSignatureNormalization:
    def test_signature_hash_is_stable_for_same_input(self) -> None:
        sig1 = normalized_signature("Foo", [("bar.py", 10, "func")])
        sig2 = normalized_signature("Foo", [("bar.py", 10, "func")])
        assert sig1 == sig2
        assert len(sig1) == 16

    def test_signature_differs_for_different_traceback(self) -> None:
        sig1 = normalized_signature("Foo", [("a.py", 1, "f")])
        sig2 = normalized_signature("Foo", [("a.py", 2, "f")])
        assert sig1 != sig2


class TestCrashDedup:
    def test_crash_dedup_collapses_identical_signatures(self) -> None:
        game = RepeatCrashGame()
        crawler = Crawler(
            seed=1,
            actions=5,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.run()
        assert len(crawler.crashes) == 1
        record = next(iter(crawler.crashes.values()))
        assert record.occurrence_count == 5

    def test_crash_dedup_preserves_earliest_seed_action_index(self) -> None:
        game = RepeatCrashGame()
        crawler = Crawler(
            seed=99,
            actions=4,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.run()
        record = next(iter(crawler.crashes.values()))
        assert record.first_seed == 99
        assert record.first_action_index == 0

    def test_multiple_distinct_signatures_kept_separate(self) -> None:
        game = DifferentCrashGame()
        crawler = Crawler(
            seed=1,
            actions=4,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.run()
        # RuntimeError from _throw_a and ValueError from _throw_b
        assert len(crawler.crashes) == 2
        classes = {c.exception_class for c in crawler.crashes.values()}
        assert classes == {"RuntimeError", "ValueError"}


class TestReplay:
    def test_crawler_replay_reproduces_crash(self) -> None:
        # Inject a deterministic crash on the 3rd action via a step
        # monkeypatch. Every fresh game constructed by the factory has the
        # same monkeypatch, so a replay reproduces the exception.
        def make_game() -> Any:
            g = RepeatCrashGame()
            counter = {"n": 0}

            def step_that_raises_at_3(
                dt: float, events: list[pygame.event.Event]
            ) -> None:
                n = counter["n"]
                counter["n"] = n + 1
                if n == 3:
                    _throw_planted()

            g.step = step_that_raises_at_3  # type: ignore[assignment]
            return g

        crawler = Crawler(
            seed=17,
            actions=5,
            fixtures=CrawlerFixtures(game_factory=make_game),
        )
        crawler.run()
        assert len(crawler.crashes) == 1
        original = next(iter(crawler.crashes.values()))
        assert original.first_action_index == 3

        replay_record = crawler.replay(seed=17, up_to_action_index=3)
        assert replay_record is not None
        assert replay_record.signature == original.signature

    def test_replay_returns_none_when_no_crash_at_index(self) -> None:
        # RepeatCrashGame with step=no-op means no crashes at all.
        def make_game() -> Any:
            g = RepeatCrashGame()
            g.step = lambda dt, events: None  # type: ignore[assignment]
            return g

        crawler = Crawler(
            seed=1,
            actions=3,
            fixtures=CrawlerFixtures(game_factory=make_game),
        )
        crawler.run()
        assert crawler.replay(seed=1, up_to_action_index=1) is None
