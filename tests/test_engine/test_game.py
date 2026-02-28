"""
Tests for the main game engine.
"""

import pytest
import pygame
from spacegame.engine.game import Game
from spacegame.config import GameState


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
