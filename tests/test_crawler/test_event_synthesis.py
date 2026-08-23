"""Event synthesis + step-invocation tests (QF-6, Task 4)."""

from __future__ import annotations

import os
from typing import Any, Callable

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pygame_gui

from tools.crawler.crawler import Crawler, CrawlerFixtures


class FakeStateManager:
    def __init__(self) -> None:
        self.current_state = None
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class MinimalGameWithStep:
    """Just enough Game to route events through pygame_gui and record them."""

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = FakeStateManager()
        self.player = None
        self.observed_ui_button_pressed = 0

        from spacegame.engine.input_handler import InputHandler

        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        # Feed events to pygame_gui; count UI_BUTTON_PRESSED after ui update.
        for event in events:
            self.ui_manager.process_events(event)
        self.ui_manager.update(dt)
        # After processing, drain the pygame event queue to observe
        # UI_BUTTON_PRESSED emitted by the manager.
        for event in pygame.event.get():
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                self.observed_ui_button_pressed += 1


class TestEventSynthesis:
    def test_click_synthesis_produces_two_mouse_events(self) -> None:
        game = MinimalGameWithStep()
        button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Fire",
            manager=game.ui_manager,
        )
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        events = crawler.synthesize_events(("click", button))
        assert len(events) == 2
        assert events[0].type == pygame.MOUSEBUTTONDOWN
        assert events[1].type == pygame.MOUSEBUTTONUP
        assert events[0].pos == button.rect.center

    def test_keypress_synthesis_produces_keydown_keyup(self) -> None:
        game = MinimalGameWithStep()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        events = crawler.synthesize_events(("keypress", pygame.K_ESCAPE))
        assert len(events) == 2
        assert events[0].type == pygame.KEYDOWN
        assert events[0].key == pygame.K_ESCAPE
        assert events[1].type == pygame.KEYUP

    def test_advance_time_synthesis_returns_empty(self) -> None:
        game = MinimalGameWithStep()
        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()
        events = crawler.synthesize_events(("advance_time",))
        assert events == []


class TestStepFiresUIButtonPressed:
    def test_click_synthesis_fires_ui_button_pressed(self) -> None:
        # Drain any leftover events from prior tests.
        pygame.event.clear()

        game = MinimalGameWithStep()
        button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Fire",
            manager=game.ui_manager,
        )
        # Warm up the ui_manager so the button is drawn/registered.
        game.ui_manager.update(0.016)

        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()

        # Manually construct the click action; do not rely on RNG.
        action = ("click", button)
        events = crawler.synthesize_events(action)
        # Post events onto the queue so pygame_gui's process_events sees them.
        for e in events:
            pygame.event.post(e)
        drained = pygame.event.get()
        game.step(1 / 60.0, drained)
        assert game.observed_ui_button_pressed >= 1, (
            "Synthesized click should have produced UI_BUTTON_PRESSED"
        )


class _MinimalGameNoQueueDrain:
    """Minimal game that processes UI events but does NOT drain the pygame queue.

    The real Game.step() does not drain the queue (Game.run() does that at the
    top of each loop iteration). This class reproduces that contract so the
    crawler's _pending_events handshake test can observe events left in the queue
    after game.step() returns.
    """

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))

        from spacegame.engine.state_manager import StateManager

        self.state_manager = StateManager()

        from spacegame.engine.input_handler import InputHandler

        self.input_handler = InputHandler()
        self.player = None
        # Track what events the step received.
        self.received_events: list[pygame.event.Event] = []

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover
        return

    def initialize_states(self) -> None:  # pragma: no cover
        return

    def step(self, dt: float, events: list[pygame.event.Event]) -> None:
        self.received_events.extend(events)
        for event in events:
            self.ui_manager.process_events(event)
        self.ui_manager.update(dt)
        # Intentionally do NOT drain the pygame event queue here.
        # The crawler owns the queue and drains it after each step.


class TestStepOnceDrainsUIEvents:
    """AC-1 sub-test: _pending_events carries UI-queue events across frames."""

    def test_step_once_drains_ui_events(self) -> None:
        """After a click step_once, _pending_events must be non-empty;
        after the following step_once, it must be empty (consumed).
        """
        pygame.event.clear()

        game = _MinimalGameNoQueueDrain()
        button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Fire",
            manager=game.ui_manager,
        )
        game.ui_manager.update(0.016)

        crawler = Crawler(
            seed=1,
            actions=0,
            fixtures=CrawlerFixtures(game_factory=lambda: game),
        )
        crawler.boot()

        # Force the crawler to click the button in step 1, then advance_time.
        step_actions: list[Any] = [("click", button), ("advance_time",)]
        step_idx = [0]
        orig = crawler._select_action

        def _force_action() -> Any:
            i = step_idx[0]
            step_idx[0] += 1
            if i < len(step_actions):
                return step_actions[i]
            return orig()

        crawler._select_action = _force_action  # type: ignore[method-assign]

        # Step 1: click — pygame_gui posts UI_BUTTON_PRESSED to the global queue
        # inside game.step(); step_once must drain that into _pending_events.
        crawler.step_once()
        assert crawler._pending_events, (
            "_pending_events must be non-empty after a click step "
            "(UI_BUTTON_PRESSED should have been drained from the pygame queue)"
        )

        # Step 2: advance_time — _pending_events must be consumed (prepended to
        # events and cleared) so it is empty after this step completes.
        pending_before = list(crawler._pending_events)
        crawler.step_once()
        assert not crawler._pending_events, (
            "_pending_events must be empty after the following step "
            "(the queued UI events must have been forwarded to game.step)"
        )
        # The pending events from step 1 must have been received by game.step
        # in step 2 (they were prepended before the synthesized advance_time).
        assert any(e in game.received_events for e in pending_before), (
            "Events from _pending_events must reach game.step in the next frame"
        )
