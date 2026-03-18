"""Tests for reusable tooltip system."""

import pytest

from spacegame.engine.tooltip import TooltipState


class TestTooltipState:
    """TooltipState tracks hover timing, content, and position."""

    def test_initial_state_not_visible(self) -> None:
        ts = TooltipState(delay=0.3)
        assert not ts.visible
        assert ts.content is None

    def test_hover_shows_after_delay(self) -> None:
        ts = TooltipState(delay=0.3)
        ts.set_hover("skill_info", (100, 200))
        assert not ts.visible
        ts.update(0.2)
        assert not ts.visible
        ts.update(0.15)
        assert ts.visible
        assert ts.content == "skill_info"

    def test_hover_position_stored(self) -> None:
        ts = TooltipState(delay=0.0)
        ts.set_hover("info", (150, 250))
        ts.update(0.0)
        assert ts.visible
        assert ts.anchor == (150, 250)

    def test_clear_hides_tooltip(self) -> None:
        ts = TooltipState(delay=0.0)
        ts.set_hover("info", (100, 200))
        ts.update(0.0)
        assert ts.visible
        ts.clear()
        assert not ts.visible
        assert ts.content is None

    def test_changing_content_resets_timer(self) -> None:
        ts = TooltipState(delay=0.3)
        ts.set_hover("item_a", (100, 200))
        ts.update(0.25)
        assert not ts.visible
        # Move to different item — timer resets
        ts.set_hover("item_b", (200, 300))
        ts.update(0.25)
        assert not ts.visible
        ts.update(0.10)
        assert ts.visible
        assert ts.content == "item_b"

    def test_same_content_does_not_reset_timer(self) -> None:
        ts = TooltipState(delay=0.3)
        ts.set_hover("item_a", (100, 200))
        ts.update(0.2)
        # Same content, maybe slightly different position
        ts.set_hover("item_a", (105, 205))
        ts.update(0.15)
        assert ts.visible  # Should be visible — timer was NOT reset

    def test_zero_delay_shows_immediately(self) -> None:
        ts = TooltipState(delay=0.0)
        ts.set_hover("instant", (50, 50))
        ts.update(0.0)
        assert ts.visible

    def test_fade_alpha_ramps_up(self) -> None:
        ts = TooltipState(delay=0.1, fade_in=0.2)
        ts.set_hover("info", (100, 200))
        ts.update(0.1)  # delay elapsed
        assert ts.visible
        assert ts.alpha == pytest.approx(0.0)
        ts.update(0.1)  # half of fade_in
        assert ts.alpha == pytest.approx(0.5, abs=0.05)
        ts.update(0.1)  # full fade_in
        assert ts.alpha == pytest.approx(1.0)

    def test_fade_alpha_stays_at_one(self) -> None:
        ts = TooltipState(delay=0.0, fade_in=0.1)
        ts.set_hover("info", (100, 200))
        ts.update(0.0)
        ts.update(0.5)
        assert ts.alpha == pytest.approx(1.0)

    def test_no_fade_in_means_instant_alpha(self) -> None:
        ts = TooltipState(delay=0.0, fade_in=0.0)
        ts.set_hover("info", (100, 200))
        ts.update(0.0)
        assert ts.alpha == pytest.approx(1.0)

    def test_get_screen_position_basic(self) -> None:
        ts = TooltipState(delay=0.0)
        ts.set_hover("info", (100, 200))
        ts.update(0.0)
        x, y = ts.get_screen_position(
            tooltip_w=200, tooltip_h=80,
            screen_w=1280, screen_h=720,
            offset_x=15, offset_y=15,
        )
        assert x == 115  # anchor_x + offset
        assert y == 215  # anchor_y + offset

    def test_get_screen_position_clamps_right_edge(self) -> None:
        ts = TooltipState(delay=0.0)
        ts.set_hover("info", (1200, 200))
        ts.update(0.0)
        x, y = ts.get_screen_position(
            tooltip_w=200, tooltip_h=80,
            screen_w=1280, screen_h=720,
        )
        assert x + 200 <= 1280

    def test_get_screen_position_clamps_bottom_edge(self) -> None:
        ts = TooltipState(delay=0.0)
        ts.set_hover("info", (100, 680))
        ts.update(0.0)
        x, y = ts.get_screen_position(
            tooltip_w=200, tooltip_h=80,
            screen_w=1280, screen_h=720,
        )
        assert y + 80 <= 720

    def test_update_without_hover_does_nothing(self) -> None:
        ts = TooltipState(delay=0.3)
        ts.update(1.0)
        assert not ts.visible
