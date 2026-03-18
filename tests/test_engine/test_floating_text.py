"""Tests for generalized floating text/icon animation system."""

import pytest

from spacegame.engine.floating_text import FloatingItem, FloatingItemManager


class TestFloatingItem:
    """FloatingItem moves from origin to target over duration with easing."""

    def test_initial_position_at_origin(self) -> None:
        fi = FloatingItem(
            text="Hello",
            origin=(100.0, 200.0),
            duration=1.0,
        )
        assert fi.x == pytest.approx(100.0)
        assert fi.y == pytest.approx(200.0)

    def test_default_target_is_rise(self) -> None:
        """With no target, text rises upward from origin."""
        fi = FloatingItem(
            text="+5 ore",
            origin=(100.0, 200.0),
            duration=1.0,
            rise=30.0,
        )
        fi.update(1.0)
        assert fi.y == pytest.approx(170.0)
        assert fi.x == pytest.approx(100.0)

    def test_moves_to_target(self) -> None:
        fi = FloatingItem(
            text="item",
            origin=(0.0, 0.0),
            target=(100.0, 50.0),
            duration=1.0,
        )
        fi.update(1.0)
        assert fi.x == pytest.approx(100.0)
        assert fi.y == pytest.approx(50.0)

    def test_alpha_fades_out(self) -> None:
        fi = FloatingItem(text="fade", origin=(0.0, 0.0), duration=1.0)
        assert fi.alpha == pytest.approx(1.0)
        fi.update(0.5)
        # Alpha should still be high at midpoint (fades toward end)
        assert fi.alpha > 0.3
        fi.update(0.5)
        assert fi.alpha == pytest.approx(0.0)

    def test_finished_after_duration(self) -> None:
        fi = FloatingItem(text="done", origin=(0.0, 0.0), duration=0.5)
        assert not fi.finished
        fi.update(0.5)
        assert fi.finished

    def test_scale_shrinks_on_target_travel(self) -> None:
        fi = FloatingItem(
            text="shrink",
            origin=(0.0, 0.0),
            target=(100.0, 100.0),
            duration=1.0,
            scale_start=1.0,
            scale_end=0.3,
        )
        fi.update(1.0)
        assert fi.scale == pytest.approx(0.3)

    def test_scale_default_is_constant(self) -> None:
        fi = FloatingItem(text="no scale", origin=(0.0, 0.0), duration=1.0)
        fi.update(0.5)
        assert fi.scale == pytest.approx(1.0)

    def test_callback_on_finish(self) -> None:
        results = []
        fi = FloatingItem(
            text="cb",
            origin=(0.0, 0.0),
            duration=0.5,
            on_complete=lambda: results.append("done"),
        )
        fi.update(0.5)
        assert results == ["done"]

    def test_callback_fires_only_once(self) -> None:
        results = []
        fi = FloatingItem(
            text="cb",
            origin=(0.0, 0.0),
            duration=0.5,
            on_complete=lambda: results.append("done"),
        )
        fi.update(1.0)
        fi.update(1.0)
        assert results == ["done"]

    def test_color_stored(self) -> None:
        fi = FloatingItem(
            text="+10",
            origin=(0.0, 0.0),
            duration=1.0,
            color=(255, 200, 50),
        )
        assert fi.color == (255, 200, 50)


class TestFloatingItemManager:
    """Manages a collection of floating items."""

    def test_add_text(self) -> None:
        mgr = FloatingItemManager()
        mgr.add_text("+5", x=100, y=200, color=(255, 255, 255))
        assert len(mgr) == 1

    def test_add_icon_float(self) -> None:
        mgr = FloatingItemManager()
        mgr.add_icon_float(
            text="ore",
            origin=(100, 200),
            target=(50, 10),
            icon_key="raw_ore",
        )
        assert len(mgr) == 1
        assert mgr.items[0].icon_key == "raw_ore"

    def test_update_removes_finished(self) -> None:
        mgr = FloatingItemManager()
        mgr.add_text("+5", x=100, y=200, duration=0.5)
        mgr.add_text("+10", x=100, y=250, duration=2.0)
        assert len(mgr) == 2
        mgr.update(1.0)
        assert len(mgr) == 1

    def test_clear(self) -> None:
        mgr = FloatingItemManager()
        mgr.add_text("+5", x=100, y=200)
        mgr.add_text("+10", x=100, y=250)
        mgr.clear()
        assert len(mgr) == 0

    def test_stacks_vertically(self) -> None:
        """Multiple texts at same position should offset to avoid overlap."""
        mgr = FloatingItemManager()
        mgr.add_text("+5", x=100, y=200, stack_offset=20)
        mgr.add_text("+10", x=100, y=200, stack_offset=20)
        # Second item should be offset upward
        assert mgr.items[1].y < mgr.items[0].y

    def test_items_property(self) -> None:
        mgr = FloatingItemManager()
        mgr.add_text("a", x=0, y=0)
        assert len(mgr.items) == 1
        assert mgr.items[0].text == "a"
