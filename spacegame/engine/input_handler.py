"""
Input handling system.

Processes keyboard and mouse input events and dispatches them to the
appropriate game components.
"""

from typing import Callable, Dict

import pygame

from spacegame.utils.logger import logger


class InputHandler:
    """
    Centralized input handling for the game.

    Processes pygame events and provides a clean interface for responding
    to user input.
    """

    def __init__(self) -> None:
        """Initialize the input handler."""
        self.quit_requested = False
        self.mouse_pos = (0, 0)
        self.keys_pressed: Dict[int, bool] = {}

        # Callbacks for custom handling (can be used by different states)
        self.key_callbacks: Dict[int, Callable] = {}
        self.mouse_callbacks: Dict[str, Callable] = {}

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        """
        Process all pygame events for this frame.

        Args:
            events: List of pygame events from pygame.event.get()
        """
        for event in events:
            if event.type == pygame.QUIT:
                logger.info("Quit event received")
                self.quit_requested = True

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            elif event.type == pygame.KEYUP:
                self._handle_keyup(event)

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)

            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_up(event)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle key press events."""
        key = event.key
        self.keys_pressed[key] = True

        # Check for ESC (common for pause/menu)
        if key == pygame.K_ESCAPE:
            logger.debug("ESC pressed")

        # Execute registered callback if exists
        if key in self.key_callbacks:
            self.key_callbacks[key]()

    def _handle_keyup(self, event: pygame.event.Event) -> None:
        """Handle key release events."""
        key = event.key
        self.keys_pressed[key] = False

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        """Handle mouse button press."""
        button = event.button
        pos = event.pos

        logger.debug(f"Mouse button {button} pressed at {pos}")

        if "click" in self.mouse_callbacks:
            self.mouse_callbacks["click"](pos, button)

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        """Handle mouse button release."""
        # Can implement if needed

    def is_key_pressed(self, key: int) -> bool:
        """
        Check if a specific key is currently pressed.

        Args:
            key: pygame key constant (e.g., pygame.K_SPACE)

        Returns:
            True if key is pressed, False otherwise
        """
        return self.keys_pressed.get(key, False)

    def register_key_callback(self, key: int, callback: Callable) -> None:
        """
        Register a callback for a specific key press.

        Args:
            key: pygame key constant
            callback: Function to call when key is pressed
        """
        self.key_callbacks[key] = callback

    def register_mouse_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback for mouse events.

        Args:
            event_type: Type of mouse event ("click", etc.)
            callback: Function to call on event
        """
        self.mouse_callbacks[event_type] = callback

    def clear_callbacks(self) -> None:
        """Clear all registered callbacks (useful when changing states)."""
        self.key_callbacks.clear()
        self.mouse_callbacks.clear()
