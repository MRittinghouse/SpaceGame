"""Crawler bootstrap tests (QF-6, Task 2).

Focus:
- SDL_VIDEODRIVER=dummy is set before pygame imports.
- The crawler seeds process-wide RNG (stdlib + numpy) BEFORE calling
  initialize_states(). This is verified by patching initialize_states
  and observing that random.random() returns the same value both times
  when we boot twice with the same seed.
"""

from __future__ import annotations

import os
import random
from typing import Any

from tools.crawler.crawler import Crawler, CrawlerFixtures


class FakeStateManager:
    """A minimal state_manager stand-in for bootstrap tests."""

    def __init__(self) -> None:
        self.current_state = None
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class FakeGame:
    """A minimal Game stand-in used to isolate bootstrap sequencing."""

    def __init__(self) -> None:
        # Called during Crawler.boot AFTER pre-seed.
        self.init_random_sample: float | None = None
        self.seed_calls: list[int] = []
        self.initialized = False
        self.state_manager = FakeStateManager()
        self.ui_manager = _EmptyUIManager()
        self.player = None

    def seed_rngs(self, seed: int) -> None:
        self.seed_calls.append(seed)

    def initialize_states(self) -> None:
        # Sample the RNG here — if the crawler seeded correctly, the sample
        # must be identical across two boot() calls with the same seed.
        self.init_random_sample = random.random()
        self.initialized = True


class _EmptyUIManager:
    """Empty pygame_gui.UIManager stand-in for enumeration returns []."""

    def get_sprite_group(self) -> Any:
        class _Group:
            def sprites(self_inner) -> list:
                return []

        return _Group()


class TestCrawlerBootstrap:
    """Verify SDL headless mode + RNG seeding order."""

    def test_headless_sdl_env_set_by_crawler_module(self) -> None:
        # The crawler module setdefault's the driver at import time.
        assert os.environ.get("SDL_VIDEODRIVER") == "dummy"
        assert os.environ.get("SDL_AUDIODRIVER") == "dummy"

    def test_boot_seeds_before_initialize_states(self) -> None:
        game_a = FakeGame()
        game_b = FakeGame()

        crawler_a = Crawler(
            seed=42,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game_a),
        )
        crawler_a.boot()

        crawler_b = Crawler(
            seed=42,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game_b),
        )
        crawler_b.boot()

        assert game_a.initialized is True
        assert game_b.initialized is True
        assert game_a.init_random_sample == game_b.init_random_sample, (
            "RNG sampled inside initialize_states must be identical when seeds match"
        )

    def test_boot_calls_seed_rngs_belt_and_braces(self) -> None:
        game = FakeGame()
        crawler = Crawler(
            seed=13,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        assert 13 in game.seed_calls

    def test_boot_records_initial_current_state(self) -> None:
        class GameWithInitialState(FakeGame):
            def initialize_states(self) -> None:
                super().initialize_states()
                from spacegame.config import GameState

                self.state_manager.current_state = GameState.MAIN_MENU

        game = GameWithInitialState()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        assert crawler.coverage.states_reached["MAIN_MENU"] is True


class TestCrawlerDisablesAudio:
    """The crawler must not drive SDL_mixer.

    `pygame.mixer.music.unpause()` deadlocks intermittently and never returns.
    py-spy caught it twice on live runs, both times inside a crawler step:

        resume_music -> _close_pause_menu -> _handle_pause_menu
        -> Game.step -> Crawler.step_once

    It blocks in a C call holding the GIL, so pytest-timeout's thread method
    cannot fire; the entire pytest process wedges until killed from outside.
    That repeatedly took down the ralph harness's baseline and test gate, in
    both an interactive session and under the Scheduled Task.

    The crawler is a headless fuzzer that drives thousands of pause/resume
    cycles, so the audio is pure liability. It disables audio on its own Game
    instance -- not on the `get_audio_manager()` singleton, which is
    process-global and shared with tests asserting real mixer behaviour.
    """

    def test_boot_disables_audio_on_the_game(self) -> None:
        crawler = Crawler(seed=1, actions=1)
        crawler.boot()
        assert crawler.game.audio_manager.enabled is False, (
            "crawler booted a Game whose audio manager still talks to SDL_mixer"
        )

    def test_boot_tolerates_a_game_without_an_audio_manager(self) -> None:
        """Fixture-injected fakes need not have one."""

        class BareGame:
            def __init__(self) -> None:
                self.state_manager = FakeStateManager()

            def seed_rngs(self, seed: int) -> None:
                pass

            def initialize_states(self) -> None:
                pass

        crawler = Crawler(seed=1, actions=1, fixtures=CrawlerFixtures(game_factory=BareGame))
        crawler.boot()  # must not raise
