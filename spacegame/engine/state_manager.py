"""
Game state management system.

Manages transitions between different game states (menu, gameplay, etc.)
and delegates update/render calls to the active state.
"""

from typing import Dict, Optional

import pygame

from spacegame.config import GameState
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


class StateManager:
    """
    Manages game states and transitions.

    Each state is responsible for its own update and render logic.
    The StateManager coordinates which state is active and handles transitions.
    """

    def __init__(self) -> None:
        """Initialize the state manager."""
        self.states: Dict[GameState, BaseView] = {}
        self.current_state: Optional[GameState] = None
        self.previous_state: Optional[GameState] = None
        self.state_stack: list[GameState] = []  # For overlays (pause, modals)

    def register_state(self, state: GameState, view: BaseView) -> None:
        """
        Register a view for a specific game state.

        Args:
            state: GameState enum value
            view: View instance that handles this state
        """
        self.states[state] = view
        logger.debug(f"Registered state: {state.value}")

    def change_state(self, new_state: GameState) -> None:
        """
        Change to a new game state, replacing the current one.

        Args:
            new_state: The state to transition to
        """
        if new_state not in self.states:
            logger.error(f"Attempted to change to unregistered state: {new_state.value}")
            return

        # Exit current state
        if self.current_state and self.current_state in self.states:
            self.states[self.current_state].on_exit()

        self.previous_state = self.current_state
        self.current_state = new_state

        # Enter new state
        self.states[new_state].on_enter()

        logger.info(f"State changed: {self.previous_state} -> {self.current_state.value}")

    def push_state(self, overlay_state: GameState) -> None:
        """
        Push a new state onto the stack (for overlays like pause menu).

        Args:
            overlay_state: State to overlay on top of current state
        """
        if self.current_state:
            self.state_stack.append(self.current_state)

        self.current_state = overlay_state
        self.states[overlay_state].on_enter()

        logger.debug(f"Pushed state: {overlay_state.value}, stack depth: {len(self.state_stack)}")

    def pop_state(self) -> None:
        """Pop the current state and return to the previous one in the stack."""
        if not self.state_stack:
            logger.warning("Attempted to pop state but stack is empty")
            return

        # Exit current state
        if self.current_state:
            self.states[self.current_state].on_exit()

        # Restore previous state
        self.current_state = self.state_stack.pop()
        self.states[self.current_state].on_enter()

        logger.debug(f"Popped state, now at: {self.current_state.value}")

    def update(self, dt: float) -> None:
        """
        Update the current active state.

        Args:
            dt: Delta time in seconds since last frame
        """
        if self.current_state and self.current_state in self.states:
            self.states[self.current_state].update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the current active state.

        Args:
            screen: Pygame surface to render to
        """
        if self.current_state and self.current_state in self.states:
            self.states[self.current_state].render(screen)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Pass event to current active state for handling.

        Args:
            event: Pygame event to handle
        """
        if self.current_state and self.current_state in self.states:
            self.states[self.current_state].handle_event(event)

    def get_current_view(self) -> Optional[object]:
        """Return the currently active view, or None if no state is bound.

        PT-M: lets the main loop ask the active view whether it has a modal
        tip overlay that should consume events before pygame_gui processing.
        """
        if self.current_state and self.current_state in self.states:
            return self.states[self.current_state]
        return None
