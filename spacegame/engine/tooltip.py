"""Reusable tooltip state tracker.

Manages hover timing, fade-in, positioning, and content for tooltips
across all views. Views provide the rendering; this module handles the logic.

Usage:
    self.tooltip = TooltipState(delay=0.3, fade_in=0.15)

    # In update():
    hovered_item = self._get_hovered_item(mouse_pos)
    if hovered_item:
        self.tooltip.set_hover(hovered_item.id, mouse_pos)
    else:
        self.tooltip.clear()
    self.tooltip.update(dt)

    # In render():
    if self.tooltip.visible:
        alpha = int(255 * self.tooltip.alpha)
        x, y = self.tooltip.get_screen_position(w, h, WINDOW_WIDTH, WINDOW_HEIGHT)
        # ... draw tooltip at (x, y) with alpha
"""

from typing import Any, Optional


class TooltipState:
    """Tracks tooltip hover timing, content, and positioning.

    Args:
        delay: Seconds to hover before tooltip appears.
        fade_in: Seconds for alpha to ramp from 0 to 1 after delay.
    """

    def __init__(self, delay: float = 0.3, fade_in: float = 0.15) -> None:
        self._delay = max(delay, 0.0)
        self._fade_in = max(fade_in, 0.0)
        self._hover_timer = 0.0
        self._fade_timer = 0.0
        self._content: Optional[Any] = None
        self._anchor: tuple[int, int] = (0, 0)
        self._visible = False

    @property
    def visible(self) -> bool:
        """Whether the tooltip should be rendered."""
        return self._visible

    @property
    def content(self) -> Optional[Any]:
        """Current tooltip content key (set by the view)."""
        return self._content

    @property
    def anchor(self) -> tuple[int, int]:
        """Mouse position when hover started."""
        return self._anchor

    @property
    def alpha(self) -> float:
        """Current opacity from 0.0 to 1.0 (for fade-in)."""
        if not self._visible:
            return 0.0
        if self._fade_in <= 0.0:
            return 1.0
        return min(self._fade_timer / self._fade_in, 1.0)

    def set_hover(self, content: Any, position: tuple[int, int]) -> None:
        """Signal that the mouse is hovering over a tooltippable element.

        Args:
            content: Identifier for what's being hovered (e.g., item ID).
            position: Current mouse (x, y) position.
        """
        if content != self._content:
            # New target — reset timer
            self._content = content
            self._hover_timer = 0.0
            self._fade_timer = 0.0
            self._visible = False
        self._anchor = position

    def clear(self) -> None:
        """Signal that the mouse is no longer hovering over anything."""
        self._content = None
        self._hover_timer = 0.0
        self._fade_timer = 0.0
        self._visible = False

    def update(self, dt: float) -> None:
        """Advance timers.

        Args:
            dt: Delta time in seconds.
        """
        if self._content is None:
            return
        if not self._visible:
            self._hover_timer += dt
            if self._hover_timer >= self._delay:
                self._visible = True
                self._fade_timer = 0.0
        else:
            self._fade_timer += dt

    def get_screen_position(
        self,
        tooltip_w: int,
        tooltip_h: int,
        screen_w: int,
        screen_h: int,
        offset_x: int = 15,
        offset_y: int = 15,
    ) -> tuple[int, int]:
        """Compute tooltip position clamped to screen bounds.

        Args:
            tooltip_w: Width of the tooltip surface.
            tooltip_h: Height of the tooltip surface.
            screen_w: Screen width.
            screen_h: Screen height.
            offset_x: Horizontal offset from anchor.
            offset_y: Vertical offset from anchor.

        Returns:
            Tuple of (x, y) for top-left corner of tooltip.
        """
        x = self._anchor[0] + offset_x
        y = self._anchor[1] + offset_y
        # Clamp to screen edges
        if x + tooltip_w > screen_w:
            x = screen_w - tooltip_w
        if y + tooltip_h > screen_h:
            y = screen_h - tooltip_h
        return (x, y)
