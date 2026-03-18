"""Generalized floating text and icon animation system.

Replaces per-view floating text implementations with a shared manager.
Supports rising text, A-to-B icon travel, fade-out, scaling, and callbacks.

Usage:
    self.floats = FloatingItemManager()

    # Add rising text feedback:
    self.floats.add_text("+5 ore", x=200, y=300, color=Colors.GREEN)

    # Add icon traveling from source to UI bar:
    self.floats.add_icon_float("ore", origin=(200, 300), target=(50, 10),
                               icon_key="raw_ore")

    # In update():
    self.floats.update(dt)

    # In render():
    for item in self.floats.items:
        alpha = int(255 * item.alpha)
        # render item.text or item.icon_key at (item.x, item.y)
"""

from typing import Callable, Optional

from spacegame.engine.easing import ease_out_cubic, EasingFn


class FloatingItem:
    """A single floating text or icon with position, alpha, and scale animation.

    Args:
        text: Display text.
        origin: Starting (x, y) position.
        target: Optional destination (x, y). If None, text rises from origin.
        duration: Lifetime in seconds.
        rise: Pixels to rise upward (only used when target is None).
        color: RGB tuple for text rendering.
        icon_key: Optional sprite key for icon rendering.
        scale_start: Initial scale factor.
        scale_end: Final scale factor.
        easing: Easing function for position interpolation.
        on_complete: Optional callback when animation finishes.
    """

    def __init__(
        self,
        text: str,
        origin: tuple[float, float],
        target: Optional[tuple[float, float]] = None,
        duration: float = 1.0,
        rise: float = 30.0,
        color: tuple[int, int, int] = (255, 255, 255),
        icon_key: Optional[str] = None,
        scale_start: float = 1.0,
        scale_end: float = 1.0,
        easing: EasingFn = ease_out_cubic,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self.text = text
        self.color = color
        self.icon_key = icon_key
        self._origin = origin
        self._easing = easing
        self._on_complete = on_complete
        self._callback_fired = False
        self._duration = max(duration, 0.0)
        self._elapsed = 0.0
        self._scale_start = scale_start
        self._scale_end = scale_end

        # Compute target: explicit or rise upward
        if target is not None:
            self._target = target
        else:
            self._target = (origin[0], origin[1] - rise)

        # Current state
        self.x = origin[0]
        self.y = origin[1]

    @property
    def finished(self) -> bool:
        """Whether this item has completed its animation."""
        return self._elapsed >= self._duration

    @property
    def alpha(self) -> float:
        """Current opacity from 0.0 to 1.0. Fades out in the last 40%."""
        if self._duration <= 0.0:
            return 0.0
        progress = self._elapsed / self._duration
        # Full alpha for first 60%, then fade out
        if progress < 0.6:
            return 1.0
        return max(0.0, 1.0 - (progress - 0.6) / 0.4)

    @property
    def scale(self) -> float:
        """Current scale factor (interpolated from start to end)."""
        if self._duration <= 0.0:
            return self._scale_end
        t = min(self._elapsed / self._duration, 1.0)
        eased = self._easing(t)
        return self._scale_start + (self._scale_end - self._scale_start) * eased

    def update(self, dt: float) -> None:
        """Advance the animation by dt seconds.

        Args:
            dt: Delta time in seconds.
        """
        self._elapsed = min(self._elapsed + dt, self._duration)
        if self._duration > 0.0:
            t = self._elapsed / self._duration
            eased = self._easing(t)
            self.x = self._origin[0] + (self._target[0] - self._origin[0]) * eased
            self.y = self._origin[1] + (self._target[1] - self._origin[1]) * eased

        if self.finished and self._on_complete and not self._callback_fired:
            self._callback_fired = True
            self._on_complete()


class FloatingItemManager:
    """Manages a collection of floating items with automatic cleanup.

    Provides convenience methods for common patterns (rising text,
    icon travel) and handles vertical stacking to prevent overlap.
    """

    def __init__(self) -> None:
        self._items: list[FloatingItem] = []

    @property
    def items(self) -> list[FloatingItem]:
        """Active floating items (read-only access for rendering)."""
        return self._items

    def add(self, item: FloatingItem) -> None:
        """Add a pre-configured FloatingItem."""
        self._items.append(item)

    def add_text(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[int, int, int] = (255, 255, 255),
        duration: float = 1.0,
        rise: float = 30.0,
        stack_offset: float = 0.0,
    ) -> None:
        """Add rising text feedback at a position.

        Args:
            text: Display text.
            x: X position.
            y: Y position.
            color: Text color.
            duration: Lifetime in seconds.
            rise: Pixels to float upward.
            stack_offset: If > 0, offset Y for items near same position.
        """
        if stack_offset > 0.0:
            y = self._stack_y(x, y, stack_offset)
        self._items.append(
            FloatingItem(text=text, origin=(x, y), duration=duration, rise=rise, color=color)
        )

    def add_icon_float(
        self,
        text: str,
        origin: tuple[float, float],
        target: tuple[float, float],
        icon_key: Optional[str] = None,
        duration: float = 0.8,
        scale_end: float = 0.3,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        """Add an icon/text that travels from origin to target (e.g., ore to silo).

        Args:
            text: Label text.
            origin: Start position.
            target: Destination position.
            icon_key: Sprite key for icon rendering.
            duration: Travel time in seconds.
            scale_end: Final scale factor (shrink as it arrives).
            on_complete: Callback when travel completes.
        """
        self._items.append(
            FloatingItem(
                text=text,
                origin=origin,
                target=target,
                duration=duration,
                icon_key=icon_key,
                scale_start=1.0,
                scale_end=scale_end,
                on_complete=on_complete,
            )
        )

    def update(self, dt: float) -> None:
        """Update all items and remove finished ones.

        Args:
            dt: Delta time in seconds.
        """
        for item in self._items:
            item.update(dt)
        self._items = [item for item in self._items if not item.finished]

    def clear(self) -> None:
        """Remove all floating items."""
        self._items.clear()

    def _stack_y(self, x: float, y: float, offset: float) -> float:
        """Find a Y position that avoids overlapping nearby active items."""
        for existing in self._items:
            if abs(existing.x - x) < 30 and abs(existing.y - y) < offset:
                y -= offset
        return y

    def __len__(self) -> int:
        return len(self._items)
