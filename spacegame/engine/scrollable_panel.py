"""Reusable scrollable panel for content that exceeds visible area.

Handles scroll offset tracking, mouse wheel events, clamping, and
scrollbar geometry. Views provide the rendering; this module handles
the scroll math.

Usage:
    self.panel = ScrollablePanel(
        rect=pygame.Rect(50, 100, 400, 300),
        content_height=800,
    )

    # In handle_event():
    if self.panel.handle_event(event, mouse_pos):
        return  # Event consumed by scroll

    # In render():
    for item in items:
        if self.panel.is_item_visible(item.y, item.height):
            screen_y = self.panel.get_screen_y(item.y)
            # ... draw item at screen_y
"""

from typing import Optional

import pygame


class ScrollablePanel:
    """Tracks scroll state for a rectangular content area.

    Args:
        rect: Visible area on screen (position and size).
        content_height: Total height of scrollable content in pixels.
        scroll_speed: Pixels per mouse wheel notch.
    """

    SCROLLBAR_WIDTH = 6

    def __init__(
        self,
        rect: pygame.Rect,
        content_height: int,
        scroll_speed: int = 30,
    ) -> None:
        self._rect = rect
        self._content_height = max(content_height, 0)
        self._scroll_speed = scroll_speed
        self._offset = 0

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def rect(self) -> pygame.Rect:
        """Visible area rectangle."""
        return self._rect

    @property
    def content_height(self) -> int:
        """Total height of scrollable content."""
        return self._content_height

    @property
    def scroll_offset(self) -> int:
        """Current scroll offset in pixels from top."""
        return self._offset

    @property
    def max_scroll(self) -> int:
        """Maximum allowed scroll offset."""
        return max(0, self._content_height - self._rect.height)

    @property
    def can_scroll(self) -> bool:
        """Whether content exceeds visible area."""
        return self._content_height > self._rect.height

    @property
    def scroll_fraction(self) -> float:
        """Scroll position as 0.0 (top) to 1.0 (bottom)."""
        ms = self.max_scroll
        if ms <= 0:
            return 0.0
        return self._offset / ms

    # -----------------------------------------------------------------------
    # Scrolling
    # -----------------------------------------------------------------------

    def scroll(self, delta: int) -> None:
        """Scroll by mouse wheel delta (positive = up, negative = down).

        Args:
            delta: Wheel delta (pygame MOUSEWHEEL event.y).
        """
        self._offset = self._clamp(self._offset - delta * self._scroll_speed)

    def scroll_to(self, offset: int) -> None:
        """Set scroll offset to an exact value, clamped to bounds.

        Args:
            offset: Target offset in pixels.
        """
        self._offset = self._clamp(offset)

    def scroll_to_top(self) -> None:
        """Scroll to the top of the content."""
        self._offset = 0

    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the content."""
        self._offset = self.max_scroll

    def set_content_height(self, height: int) -> None:
        """Update content height and re-clamp offset.

        Args:
            height: New total content height.
        """
        self._content_height = max(height, 0)
        self._offset = self._clamp(self._offset)

    # -----------------------------------------------------------------------
    # Event handling
    # -----------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> bool:
        """Handle a pygame event, consuming mouse wheel if inside rect.

        Args:
            event: The pygame event.
            mouse_pos: Current mouse position.

        Returns:
            True if the event was consumed (scrolled).
        """
        if event.type != pygame.MOUSEWHEEL:
            return False
        if not self._rect.collidepoint(mouse_pos):
            return False
        if not self.can_scroll:
            return False
        self.scroll(event.y)
        return True

    # -----------------------------------------------------------------------
    # Visibility helpers
    # -----------------------------------------------------------------------

    def is_item_visible(self, item_y: int, item_height: int) -> bool:
        """Check if a content item overlaps the visible viewport.

        Args:
            item_y: Item top position in content coordinates.
            item_height: Item height in pixels.

        Returns:
            True if any part of the item is visible.
        """
        item_bottom = item_y + item_height
        viewport_top = self._offset
        viewport_bottom = self._offset + self._rect.height
        return item_bottom > viewport_top and item_y < viewport_bottom

    def get_screen_y(self, content_y: int) -> int:
        """Convert content y-coordinate to screen y-coordinate.

        Args:
            content_y: Position in content coordinates.

        Returns:
            Position in screen coordinates.
        """
        return content_y - self._offset + self._rect.top

    # -----------------------------------------------------------------------
    # Scrollbar geometry
    # -----------------------------------------------------------------------

    @property
    def scrollbar_rect(self) -> Optional[pygame.Rect]:
        """Scrollbar thumb rectangle, or None if scrolling is not needed.

        Returns a small rect on the right edge of the panel for views
        to render as a scroll indicator.
        """
        if not self.can_scroll:
            return None

        track_height = self._rect.height
        thumb_height = int(track_height * (self._rect.height / self._content_height))
        thumb_height = max(thumb_height, 20)  # Minimum thumb size

        scrollable_track = track_height - thumb_height
        thumb_y = int(self.scroll_fraction * scrollable_track)

        return pygame.Rect(
            self._rect.right - self.SCROLLBAR_WIDTH,
            self._rect.top + thumb_y,
            self.SCROLLBAR_WIDTH,
            thumb_height,
        )

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _clamp(self, offset: int) -> int:
        """Clamp offset to valid range."""
        return max(0, min(offset, self.max_scroll))
