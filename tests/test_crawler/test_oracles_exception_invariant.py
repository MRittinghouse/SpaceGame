"""Oracle 1 (unhandled exception) + Oracle 4 (invariant violation) tests (QF-6)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pygame_gui

from tools.crawler.crawler import Crawler, CrawlerFixtures


class FakeStateManager:
    def __init__(self) -> None:
        from spacegame.config import GameState

        self.current_state = GameState.GALAXY_MAP
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class FakeShip:
    def __init__(
        self,
        current_fuel: int = 50,
        max_fuel: int = 100,
        current_cargo: dict | None = None,
        max_cargo: int = 100,
    ) -> None:
        self.current_fuel = current_fuel
        self.max_fuel = max_fuel
        self.current_cargo = current_cargo or {}
        self.max_cargo = max_cargo


class FakePlayer:
    def __init__(self, credits: int = 1000, ship: FakeShip | None = None) -> None:
        self.credits = credits
        self.ship = ship or FakeShip()


class ControllableGame:
    """Game stand-in whose ``step`` optionally raises."""

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = FakeStateManager()
        self.player = FakePlayer()
        self.raise_on_step_index: int | None = None
        self._step_count = 0

        from spacegame.engine.input_handler import InputHandler

        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        idx = self._step_count
        self._step_count += 1
        if self.raise_on_step_index is not None and idx == self.raise_on_step_index:
            raise RuntimeError(f"deterministic crash at step {idx}")


class TestExceptionOracle:
    def test_unhandled_exception_oracle_records_crash(self) -> None:
        game = ControllableGame()
        game.raise_on_step_index = 3
        crawler = Crawler(
            seed=1,
            actions=6,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.run()
        # Exactly one crash record — dedup handles repeats but here we
        # only raise once.
        assert len(crawler.crashes) == 1
        record = next(iter(crawler.crashes.values()))
        assert record.exception_class == "RuntimeError"
        assert record.first_action_index == 3
        assert record.oracle == "exception"

    def test_unhandled_exception_does_not_abort_session(self) -> None:
        game = ControllableGame()
        game.raise_on_step_index = 1
        crawler = Crawler(
            seed=1,
            actions=5,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.run()
        assert len(crawler.action_trace) == 5


class TestInvariantOracle:
    def test_invariant_oracle_detects_negative_credits(self) -> None:
        game = ControllableGame()

        def flip_negative(idx: int, action: Any) -> None:
            if idx == 2:
                game.player.credits = -500

        crawler = Crawler(
            seed=1,
            actions=5,
            fixtures=CrawlerFixtures(
                game_factory=lambda: game,
                pre_step_hook=flip_negative,
            ),
        )
        crawler.run()
        assert any(c.oracle == "invariant" for c in crawler.crashes.values())
        assert any("NegativeCredits" in c.exception_class for c in crawler.crashes.values())

    def test_invariant_oracle_detects_fuel_overflow(self) -> None:
        game = ControllableGame()

        def cheat_fuel(idx: int, action: Any) -> None:
            if idx == 1:
                game.player.ship.current_fuel = game.player.ship.max_fuel + 10

        crawler = Crawler(
            seed=2,
            actions=3,
            fixtures=CrawlerFixtures(
                game_factory=lambda: game,
                pre_step_hook=cheat_fuel,
            ),
        )
        crawler.run()
        assert any("FuelOverflow" in c.exception_class for c in crawler.crashes.values())

    def test_invariant_oracle_detects_cargo_overflow(self) -> None:
        game = ControllableGame()

        def overload_cargo(idx: int, action: Any) -> None:
            if idx == 0:
                game.player.ship.current_cargo = {"metals": game.player.ship.max_cargo + 20}

        crawler = Crawler(
            seed=3,
            actions=2,
            fixtures=CrawlerFixtures(
                game_factory=lambda: game,
                pre_step_hook=overload_cargo,
            ),
        )
        crawler.run()
        assert any("CargoOverflow" in c.exception_class for c in crawler.crashes.values())
