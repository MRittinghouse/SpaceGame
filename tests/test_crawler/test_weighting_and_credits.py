"""Action weighting + debug credits hook tests (QF-6, Task 13)."""

from __future__ import annotations

import os
import statistics
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pygame_gui

from spacegame.config import GameState
from spacegame.engine.input_handler import InputHandler
from tools.crawler.crawler import Crawler, CrawlerFixtures


class _SM:
    def __init__(self) -> None:
        self.current_state = GameState.STATION_HUB
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class _Player:
    def __init__(self, credits: int = 0) -> None:
        self.credits = credits
        self.ship = None


class _WeightingGame:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = _SM()
        self.player = _Player(credits=0)
        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        pass


class TestActionWeighting:
    def test_action_weighting_prefers_unvisited_targets(self) -> None:
        # Two buttons: "Shipyard" (unvisited state → SHIPYARD) and
        # "Cargo Manifest" (no nav match). Over many draws, the shipyard
        # button should be chosen more often thanks to the 2x boost.
        game = _WeightingGame()
        shipyard = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Shipyard",
            manager=game.ui_manager,
        )
        neutral = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(150, 10, 100, 30),
            text="Cargo Manifest",
            manager=game.ui_manager,
        )
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        # Mark SHIPYARD as unvisited to force the 2x boost.
        assert crawler.coverage.states_reached["SHIPYARD"] is False

        # Directly probe the weighted picker to keep noise low.
        shipyard_hits = 0
        neutral_hits = 0
        # Force clicks only by asking the picker directly.
        for _ in range(400):
            chosen = crawler._weighted_element_choice([shipyard, neutral])
            if chosen is shipyard:
                shipyard_hits += 1
            else:
                neutral_hits += 1

        # 2x weight → roughly 2/3 → 267/133. Allow slack for randomness.
        assert shipyard_hits > neutral_hits, (
            f"shipyard {shipyard_hits} not preferred over neutral {neutral_hits}"
        )
        assert shipyard_hits >= 1.4 * neutral_hits, (
            f"weight boost too weak: {shipyard_hits} vs {neutral_hits}"
        )

    def test_visited_state_button_does_not_get_boost(self) -> None:
        game = _WeightingGame()
        shipyard = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Shipyard",
            manager=game.ui_manager,
        )
        neutral = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(150, 10, 100, 30),
            text="Cargo Manifest",
            manager=game.ui_manager,
        )
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        # Mark SHIPYARD as visited — weight boost should not apply.
        crawler.coverage.states_reached["SHIPYARD"] = True

        # Direct weight probe: both must be baseline 1.0.
        assert crawler._weight_for_element(shipyard) == 1.0
        assert crawler._weight_for_element(neutral) == 1.0

    def test_weighting_is_deterministic_per_seed(self) -> None:
        game_a = _WeightingGame()
        game_b = _WeightingGame()
        for game in (game_a, game_b):
            pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(10, 10, 100, 30),
                text="Shipyard",
                manager=game.ui_manager,
            )
            pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(150, 10, 100, 30),
                text="Cargo Manifest",
                manager=game.ui_manager,
            )
        crawler_a = Crawler(
            seed=7,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game_a),
        )
        crawler_a.boot()
        crawler_b = Crawler(
            seed=7,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game_b),
        )
        crawler_b.boot()
        a_draws = [crawler_a._action_rng.random() for _ in range(20)]
        b_draws = [crawler_b._action_rng.random() for _ in range(20)]
        assert a_draws == b_draws
        # Silence unused-import warning
        _ = statistics


class TestDebugCredits:
    def test_debug_credits_hook_adjusts_player_credits(self) -> None:
        game = _WeightingGame()
        crawler = Crawler(
            seed=1,
            actions=0,
            debug_credits=42_000,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        assert game.player.credits == 42_000

    def test_debug_credits_zero_is_default_noop(self) -> None:
        game = _WeightingGame()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        assert game.player.credits == 0
