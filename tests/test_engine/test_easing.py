"""Tests for easing/tween utility module."""

import pytest

from spacegame.engine.easing import (
    linear,
    ease_in_quad,
    ease_out_quad,
    ease_in_out_quad,
    ease_out_cubic,
    ease_in_out_cubic,
    ease_out_back,
    ease_out_elastic,
    Tween,
    TweenGroup,
)


class TestEasingFunctions:
    """Each easing function maps t in [0,1] to a value, with f(0)=0 and f(1)=1."""

    @pytest.mark.parametrize(
        "fn",
        [
            linear,
            ease_in_quad,
            ease_out_quad,
            ease_in_out_quad,
            ease_out_cubic,
            ease_in_out_cubic,
        ],
    )
    def test_boundaries(self, fn) -> None:
        assert fn(0.0) == pytest.approx(0.0)
        assert fn(1.0) == pytest.approx(1.0)

    def test_linear_midpoint(self) -> None:
        assert linear(0.5) == pytest.approx(0.5)

    def test_ease_out_quad_is_decelerating(self) -> None:
        """First half should cover more distance than linear."""
        assert ease_out_quad(0.5) > 0.5

    def test_ease_in_quad_is_accelerating(self) -> None:
        """First half should cover less distance than linear."""
        assert ease_in_quad(0.5) < 0.5

    def test_ease_in_out_quad_midpoint(self) -> None:
        assert ease_in_out_quad(0.5) == pytest.approx(0.5)

    def test_ease_out_cubic_faster_start(self) -> None:
        assert ease_out_cubic(0.25) > ease_out_quad(0.25)

    def test_ease_out_back_overshoots(self) -> None:
        """ease_out_back should exceed 1.0 briefly before settling."""
        assert ease_out_back(0.5) > 0.5
        assert ease_out_back(1.0) == pytest.approx(1.0)

    def test_ease_out_elastic_boundaries(self) -> None:
        assert ease_out_elastic(0.0) == pytest.approx(0.0)
        assert ease_out_elastic(1.0) == pytest.approx(1.0)

    def test_clamps_below_zero(self) -> None:
        """Passing t < 0 should clamp to 0."""
        assert linear(-0.5) == pytest.approx(0.0)

    def test_clamps_above_one(self) -> None:
        """Passing t > 1 should clamp to 1."""
        assert linear(1.5) == pytest.approx(1.0)


class TestTween:
    """Tween interpolates a value from start to end over duration."""

    def test_initial_value(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=1.0)
        assert tw.value == pytest.approx(0.0)

    def test_value_at_half(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=1.0, easing=linear)
        tw.update(0.5)
        assert tw.value == pytest.approx(50.0)

    def test_value_at_end(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=1.0, easing=linear)
        tw.update(1.0)
        assert tw.value == pytest.approx(100.0)
        assert tw.finished

    def test_overshooting_duration_clamps(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=0.5, easing=linear)
        tw.update(1.0)
        assert tw.value == pytest.approx(100.0)
        assert tw.finished

    def test_negative_range(self) -> None:
        tw = Tween(start=100.0, end=0.0, duration=1.0, easing=linear)
        tw.update(0.5)
        assert tw.value == pytest.approx(50.0)

    def test_with_easing(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=1.0, easing=ease_out_quad)
        tw.update(0.5)
        assert tw.value > 50.0  # ease_out is ahead of linear at midpoint

    def test_callback_on_finish(self) -> None:
        results = []
        tw = Tween(
            start=0.0, end=1.0, duration=0.5, easing=linear,
            on_complete=lambda: results.append("done"),
        )
        tw.update(0.25)
        assert results == []
        tw.update(0.30)
        assert results == ["done"]

    def test_callback_fires_only_once(self) -> None:
        results = []
        tw = Tween(
            start=0.0, end=1.0, duration=0.5, easing=linear,
            on_complete=lambda: results.append("done"),
        )
        tw.update(1.0)
        tw.update(1.0)
        assert results == ["done"]

    def test_not_started_until_update(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=1.0)
        assert not tw.finished
        assert tw.value == pytest.approx(0.0)

    def test_zero_duration_finishes_immediately(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=0.0, easing=linear)
        tw.update(0.0)
        assert tw.finished
        assert tw.value == pytest.approx(100.0)

    def test_reset(self) -> None:
        tw = Tween(start=0.0, end=100.0, duration=1.0, easing=linear)
        tw.update(1.0)
        assert tw.finished
        tw.reset()
        assert not tw.finished
        assert tw.value == pytest.approx(0.0)


class TestTweenGroup:
    """TweenGroup manages multiple tweens and removes finished ones."""

    def test_add_and_update(self) -> None:
        group = TweenGroup()
        tw = Tween(start=0.0, end=1.0, duration=1.0, easing=linear)
        group.add(tw)
        group.update(0.5)
        assert tw.value == pytest.approx(0.5)

    def test_finished_tweens_removed(self) -> None:
        group = TweenGroup()
        tw = Tween(start=0.0, end=1.0, duration=0.5, easing=linear)
        group.add(tw)
        assert len(group) == 1
        group.update(1.0)
        assert len(group) == 0

    def test_active_tweens_kept(self) -> None:
        group = TweenGroup()
        tw1 = Tween(start=0.0, end=1.0, duration=0.5, easing=linear)
        tw2 = Tween(start=0.0, end=1.0, duration=2.0, easing=linear)
        group.add(tw1)
        group.add(tw2)
        group.update(1.0)
        assert len(group) == 1

    def test_clear(self) -> None:
        group = TweenGroup()
        group.add(Tween(start=0.0, end=1.0, duration=1.0))
        group.add(Tween(start=0.0, end=1.0, duration=1.0))
        group.clear()
        assert len(group) == 0

    def test_is_empty(self) -> None:
        group = TweenGroup()
        assert group.is_empty()
        group.add(Tween(start=0.0, end=1.0, duration=1.0))
        assert not group.is_empty()
