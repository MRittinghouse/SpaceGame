"""
Tests for the main game engine.
"""

from __future__ import annotations

import inspect
import os
import random

import numpy as np
import pygame
import pytest

# Headless SDL so Game() can be constructed without a physical display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from spacegame.config import GameState
from spacegame.engine.game import Game


def test_game_initialization() -> None:
    """Test that the game initializes correctly."""
    # Note: This test requires pygame to initialize, which may need
    # special handling in CI environments

    game = Game()

    # Verify core components exist
    assert game.screen is not None
    assert game.clock is not None
    assert game.state_manager is not None
    assert game.input_handler is not None
    assert game.running is False  # Not started yet

    # Clean up
    pygame.quit()


def test_state_manager_state_change() -> None:
    """Test state management transitions."""
    from spacegame.engine.state_manager import StateManager
    from spacegame.views.startup_view import StartupView

    # Initialize pygame for this test
    pygame.init()

    manager = StateManager()

    # Register a test state
    test_view = StartupView()
    manager.register_state(GameState.STARTUP, test_view)

    # Change to the state
    manager.change_state(GameState.STARTUP)

    assert manager.current_state == GameState.STARTUP
    assert test_view.active is True

    # Clean up
    pygame.quit()


def test_input_handler() -> None:
    """Test input handler processes events."""
    from spacegame.engine.input_handler import InputHandler

    pygame.init()  # Need pygame initialized for events

    handler = InputHandler()

    # Create a mock quit event
    quit_event = pygame.event.Event(pygame.QUIT)
    handler.handle_events([quit_event])

    assert handler.quit_requested is True

    pygame.quit()


# ---------------------------------------------------------------------------
# QF-5: Game.step() and Game.seed_rngs() tests
# ---------------------------------------------------------------------------


def test_game_step_exists_with_signature() -> None:
    """Game.step must have (self, dt: float, events: list) -> None signature."""
    assert hasattr(Game, "step"), "Game.step does not exist"
    sig = inspect.signature(Game.step)
    params = list(sig.parameters.keys())
    assert "dt" in params, f"Game.step missing 'dt' parameter; got {params}"
    assert "events" in params, f"Game.step missing 'events' parameter; got {params}"
    assert sig.return_annotation is None or sig.return_annotation == inspect.Parameter.empty or sig.return_annotation is type(None), (
        f"Game.step return annotation should be None, got {sig.return_annotation}"
    )


def test_game_step_headless_smoke() -> None:
    """Calling game.step(1/60.0, []) on an initialized Game completes without exception."""
    game = Game()
    game.initialize_states()
    # Should not raise
    game.step(1 / 60.0, [])
    pygame.quit()


def test_game_step_quit_event_stops_run() -> None:
    """QUIT event passed to step() sets game.running = False."""
    game = Game()
    game.initialize_states()
    game.running = True
    quit_event = pygame.event.Event(pygame.QUIT)
    game.step(1 / 60.0, [quit_event])
    assert game.running is False, "game.running should be False after QUIT event"
    pygame.quit()


def test_seed_rngs_signature() -> None:
    """Game.seed_rngs must have (self, seed: int) -> None signature."""
    assert hasattr(Game, "seed_rngs"), "Game.seed_rngs does not exist"
    sig = inspect.signature(Game.seed_rngs)
    params = list(sig.parameters.keys())
    assert "seed" in params, f"Game.seed_rngs missing 'seed' parameter; got {params}"


def test_seed_rngs_reproduces_random() -> None:
    """Two Game instances seeded with the same value produce identical RNG sequences."""
    game1 = Game()
    game1.seed_rngs(42)
    r1_stdlib = random.random()
    r1_numpy = np.random.random()
    pygame.quit()

    game2 = Game()
    game2.seed_rngs(42)
    r2_stdlib = random.random()
    r2_numpy = np.random.random()
    pygame.quit()

    assert r1_stdlib == r2_stdlib, (
        f"stdlib random diverged after same seed: {r1_stdlib} != {r2_stdlib}"
    )
    assert r1_numpy == r2_numpy, (
        f"numpy random diverged after same seed: {r1_numpy} != {r2_numpy}"
    )


def test_step_determinism_with_seeded_events() -> None:
    """Two seeded Game instances driven with identical step() sequences stay in sync."""
    N = 5

    def _run_sequence(seed: int) -> tuple[object, float]:
        game = Game()
        game.initialize_states()
        game.seed_rngs(seed)
        for _ in range(N):
            game.step(1 / 60.0, [])
        state = game.state_manager.current_state
        next_sample = random.random()
        pygame.quit()
        return state, next_sample

    state1, sample1 = _run_sequence(42)
    state2, sample2 = _run_sequence(42)

    assert state1 == state2, (
        f"state_manager.current_state diverged: {state1} != {state2}"
    )
    assert sample1 == sample2, (
        f"random.random() sample diverged: {sample1} != {sample2}"
    )
