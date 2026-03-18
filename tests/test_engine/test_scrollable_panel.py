"""Tests for reusable scrollable panel widget."""

import pygame
import pytest

from spacegame.engine.scrollable_panel import ScrollablePanel


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    pygame.init()


@pytest.fixture()
def screen() -> pygame.Surface:
    return pygame.Surface((800, 600))


def _make_panel(
    visible_height: int = 200,
    content_height: int = 500,
    scroll_speed: int = 30,
) -> ScrollablePanel:
    """Create a panel with the given dimensions."""
    return ScrollablePanel(
        rect=pygame.Rect(50, 50, 300, visible_height),
        content_height=content_height,
        scroll_speed=scroll_speed,
    )


# ============================================================================
# Basic state
# ============================================================================


class TestScrollablePanelInit:
    """Initial state and configuration."""

    def test_initial_offset_is_zero(self) -> None:
        panel = _make_panel()
        assert panel.scroll_offset == 0

    def test_stores_rect(self) -> None:
        panel = _make_panel()
        assert panel.rect == pygame.Rect(50, 50, 300, 200)

    def test_stores_content_height(self) -> None:
        panel = _make_panel(content_height=500)
        assert panel.content_height == 500

    def test_max_scroll_is_content_minus_visible(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        assert panel.max_scroll == 300

    def test_max_scroll_zero_when_content_fits(self) -> None:
        panel = _make_panel(visible_height=200, content_height=100)
        assert panel.max_scroll == 0

    def test_can_scroll_when_content_exceeds_visible(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        assert panel.can_scroll is True

    def test_cannot_scroll_when_content_fits(self) -> None:
        panel = _make_panel(visible_height=200, content_height=150)
        assert panel.can_scroll is False


# ============================================================================
# Scrolling behavior
# ============================================================================


class TestScrolling:
    """Mouse wheel and programmatic scrolling."""

    def test_scroll_down_increases_offset(self) -> None:
        panel = _make_panel(scroll_speed=30)
        panel.scroll(delta=-1)  # Wheel down = negative delta
        assert panel.scroll_offset == 30

    def test_scroll_up_decreases_offset(self) -> None:
        panel = _make_panel(scroll_speed=30)
        panel.scroll(delta=-3)  # Scroll down first
        panel.scroll(delta=1)  # Scroll up
        assert panel.scroll_offset == 60  # 90 - 30

    def test_scroll_clamps_to_zero(self) -> None:
        panel = _make_panel()
        panel.scroll(delta=5)  # Try to scroll up past top
        assert panel.scroll_offset == 0

    def test_scroll_clamps_to_max(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500, scroll_speed=30)
        panel.scroll(delta=-100)  # Way past bottom
        assert panel.scroll_offset == 300  # max_scroll

    def test_scroll_noop_when_content_fits(self) -> None:
        panel = _make_panel(visible_height=200, content_height=100)
        panel.scroll(delta=-5)
        assert panel.scroll_offset == 0

    def test_scroll_to_sets_exact_offset(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to(150)
        assert panel.scroll_offset == 150

    def test_scroll_to_clamps_to_bounds(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to(-50)
        assert panel.scroll_offset == 0
        panel.scroll_to(999)
        assert panel.scroll_offset == 300

    def test_scroll_to_top(self) -> None:
        panel = _make_panel()
        panel.scroll(delta=-5)
        panel.scroll_to_top()
        assert panel.scroll_offset == 0

    def test_scroll_to_bottom(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to_bottom()
        assert panel.scroll_offset == 300


# ============================================================================
# Event handling
# ============================================================================


class TestEventHandling:
    """MOUSEWHEEL event integration."""

    def _make_wheel_event(self, y: int, pos: tuple[int, int]) -> pygame.event.Event:
        """Create a MOUSEWHEEL event."""
        return pygame.event.Event(pygame.MOUSEWHEEL, y=y, x=0, pos=pos)

    def test_handle_mousewheel_inside_rect(self) -> None:
        panel = _make_panel(scroll_speed=30)
        event = self._make_wheel_event(y=-1, pos=(100, 100))  # Inside rect
        handled = panel.handle_event(event, mouse_pos=(100, 100))
        assert handled is True
        assert panel.scroll_offset == 30

    def test_ignores_mousewheel_outside_rect(self) -> None:
        panel = _make_panel()
        event = self._make_wheel_event(y=-1, pos=(400, 400))  # Outside rect
        handled = panel.handle_event(event, mouse_pos=(400, 400))
        assert handled is False
        assert panel.scroll_offset == 0

    def test_ignores_non_mousewheel_events(self) -> None:
        panel = _make_panel()
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 100))
        handled = panel.handle_event(event, mouse_pos=(100, 100))
        assert handled is False


# ============================================================================
# Content height updates
# ============================================================================


class TestContentHeightUpdate:
    """Dynamic content height changes."""

    def test_update_content_height(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.set_content_height(800)
        assert panel.content_height == 800
        assert panel.max_scroll == 600

    def test_shrinking_content_clamps_offset(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to(250)
        panel.set_content_height(300)  # max_scroll = 100
        assert panel.scroll_offset == 100

    def test_shrinking_below_visible_resets_offset(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to(200)
        panel.set_content_height(100)  # Fits entirely
        assert panel.scroll_offset == 0


# ============================================================================
# Visibility helpers
# ============================================================================


class TestVisibilityHelpers:
    """Item visibility checks for render culling."""

    def test_is_item_visible_fully_inside(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        assert panel.is_item_visible(item_y=50, item_height=30) is True

    def test_is_item_visible_above_viewport(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to(100)
        # Item at y=20, height=30 → bottom at 50, viewport starts at 100
        assert panel.is_item_visible(item_y=20, item_height=30) is False

    def test_is_item_visible_below_viewport(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        # Item at y=250, height=30 → starts below viewport (200)
        assert panel.is_item_visible(item_y=250, item_height=30) is False

    def test_is_item_visible_partially_overlapping(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        # Item at y=180, height=40 → overlaps bottom of viewport
        assert panel.is_item_visible(item_y=180, item_height=40) is True

    def test_visible_y_offset(self) -> None:
        """Item y in screen coords = item_y - scroll_offset + rect.top."""
        panel = _make_panel(visible_height=200, content_height=500)
        panel.scroll_to(50)
        # Item at content y=100 → screen y = 100 - 50 + 50(rect.top) = 100
        assert panel.get_screen_y(content_y=100) == 100

    def test_scroll_fraction(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        assert panel.scroll_fraction == pytest.approx(0.0)
        panel.scroll_to(150)
        assert panel.scroll_fraction == pytest.approx(0.5)
        panel.scroll_to_bottom()
        assert panel.scroll_fraction == pytest.approx(1.0)

    def test_scroll_fraction_zero_when_no_scroll(self) -> None:
        panel = _make_panel(visible_height=200, content_height=100)
        assert panel.scroll_fraction == pytest.approx(0.0)


# ============================================================================
# Scrollbar rendering
# ============================================================================


class TestScrollbarRendering:
    """Scrollbar visual properties."""

    def test_scrollbar_rect_at_top(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        sb = panel.scrollbar_rect
        assert sb is not None
        assert sb.top == panel.rect.top

    def test_scrollbar_rect_moves_with_scroll(self) -> None:
        panel = _make_panel(visible_height=200, content_height=500)
        sb_top = panel.scrollbar_rect
        panel.scroll_to_bottom()
        sb_bottom = panel.scrollbar_rect
        assert sb_bottom is not None
        assert sb_top is not None
        assert sb_bottom.top > sb_top.top

    def test_no_scrollbar_when_content_fits(self) -> None:
        panel = _make_panel(visible_height=200, content_height=100)
        assert panel.scrollbar_rect is None

    def test_scrollbar_height_proportional(self) -> None:
        """Scrollbar height = visible/content * track_height."""
        panel = _make_panel(visible_height=200, content_height=500)
        sb = panel.scrollbar_rect
        assert sb is not None
        expected_height = int(200 * (200 / 500))
        assert sb.height == expected_height
