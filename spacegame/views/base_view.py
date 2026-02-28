"""
Base class for all game views/screens.

Provides a common interface that all game screens must implement.
"""

import pygame
from abc import ABC, abstractmethod


class BaseView(ABC):
    """
    Abstract base class for all game views.

    Each view represents a different screen or state in the game
    (main menu, galaxy map, trading interface, etc.).
    """

    def __init__(self, ui_manager=None) -> None:
        """Initialize the view."""
        self.active = False
        if ui_manager is not None:
            self.ui_manager = ui_manager

    def on_enter(self) -> None:
        """
        Called when this view becomes active.

        Use this to initialize or reset view-specific state.
        """
        self.active = True

    def on_exit(self) -> None:
        """
        Called when leaving this view.

        Use this for cleanup or saving state.
        """
        self.active = False

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        Update game logic for this view.

        Args:
            dt: Delta time in seconds since last frame
        """
        pass

    @abstractmethod
    def render(self, screen: pygame.Surface) -> None:
        """
        Render this view to the screen.

        Args:
            screen: Pygame surface to draw on
        """
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle pygame events specific to this view.

        Args:
            event: Pygame event to process
        """
        pass  # Optional override
