"""Tests for SceneCamera — shared camera primitive.

See requirements/overhaul/91_scene_camera_api.md for the full spec.
Unit tests cover transitions, shake composition, parallax layers,
immediate reset, world-to-screen transform, and state queries.
"""

import pytest

from spacegame.engine.easing import ease_out_cubic, linear
from spacegame.engine.scene_camera import SceneCamera, ShakeSource


class TestSceneCameraConstruction:
    """Default construction and field initialization."""

    def test_default_offset_is_origin(self) -> None:
        c = SceneCamera()
        assert c.offset == (0.0, 0.0)

    def test_default_zoom_is_one(self) -> None:
        c = SceneCamera()
        assert c.zoom == pytest.approx(1.0)

    def test_custom_initial_state(self) -> None:
        c = SceneCamera(offset=(50.0, 25.0), zoom=1.5)
        assert c.offset == (50.0, 25.0)
        assert c.zoom == pytest.approx(1.5)

    def test_not_transitioning_at_start(self) -> None:
        c = SceneCamera()
        assert not c.is_transitioning
        # With no transition, progress is 1.0 (arrived)
        assert c.transition_progress == pytest.approx(1.0)

    def test_no_active_shakes_at_start(self) -> None:
        c = SceneCamera()
        assert not c.has_active_shakes


class TestSceneCameraTransitions:
    """transition_to moves toward targets over time with easing."""

    def test_transition_completes_in_duration(self) -> None:
        c = SceneCamera()
        c.transition_to(offset=(100.0, 0.0), duration=1.0)
        c.update(1.0)
        assert c.get_offset() == pytest.approx((100.0, 0.0))
        assert not c.is_transitioning

    def test_transition_zoom_completes(self) -> None:
        c = SceneCamera()
        c.transition_to(zoom=2.0, duration=0.5)
        c.update(0.5)
        assert c.get_zoom() == pytest.approx(2.0)

    def test_linear_curve_at_midpoint(self) -> None:
        c = SceneCamera()
        c.transition_to(offset=(100.0, 0.0), duration=1.0, ease=linear)
        c.update(0.5)
        x, _ = c.get_offset()
        assert x == pytest.approx(50.0, abs=1.0)

    def test_ease_out_cubic_front_loads_progress(self) -> None:
        """Ease-out cubic should cover more than half the distance at t=0.5."""
        c = SceneCamera()
        c.transition_to(offset=(100.0, 0.0), duration=1.0, ease=ease_out_cubic)
        c.update(0.5)
        x, _ = c.get_offset()
        assert x > 50.0

    def test_replace_in_flight_transition(self) -> None:
        """A new transition from partial state reaches the new target."""
        c = SceneCamera()
        c.transition_to(offset=(100.0, 0.0), duration=1.0)
        c.update(0.5)  # Partway along first transition
        c.transition_to(offset=(200.0, 0.0), duration=1.0)  # Replace
        c.update(1.0)
        assert c.get_offset()[0] == pytest.approx(200.0)

    def test_transition_only_offset_preserves_zoom(self) -> None:
        c = SceneCamera(offset=(0.0, 0.0), zoom=1.5)
        c.transition_to(offset=(50.0, 0.0), duration=1.0)
        c.update(1.0)
        assert c.get_zoom() == pytest.approx(1.5)

    def test_transition_only_zoom_preserves_offset(self) -> None:
        c = SceneCamera(offset=(30.0, 40.0))
        c.transition_to(zoom=2.0, duration=1.0)
        c.update(1.0)
        x, y = c.get_offset()
        assert x == pytest.approx(30.0)
        assert y == pytest.approx(40.0)

    def test_is_transitioning_during_transition(self) -> None:
        c = SceneCamera()
        c.transition_to(offset=(100.0, 0.0), duration=1.0)
        assert c.is_transitioning
        c.update(0.5)
        assert c.is_transitioning
        c.update(0.6)  # past duration
        assert not c.is_transitioning

    def test_transition_progress_scales(self) -> None:
        c = SceneCamera()
        c.transition_to(offset=(100.0, 0.0), duration=1.0, ease=linear)
        c.update(0.3)
        assert c.transition_progress == pytest.approx(0.3)


class TestSceneCameraImmediateReset:
    """reset_immediate snaps without animation."""

    def test_reset_clears_transition(self) -> None:
        c = SceneCamera()
        c.transition_to(offset=(500.0, 0.0), duration=5.0)
        c.reset_immediate(offset=(10.0, 20.0), zoom=2.0)
        assert c.get_offset() == pytest.approx((10.0, 20.0))
        assert c.get_zoom() == pytest.approx(2.0)
        assert not c.is_transitioning

    def test_reset_default_values(self) -> None:
        c = SceneCamera(offset=(100.0, 100.0), zoom=3.0)
        c.reset_immediate()
        assert c.get_offset() == pytest.approx((0.0, 0.0))
        assert c.get_zoom() == pytest.approx(1.0)


class TestSceneCameraShake:
    """add_shake / clear_shakes / shake composition."""

    def test_single_shake_contributes_offset(self) -> None:
        c = SceneCamera()
        c.add_shake(amplitude=10.0, duration=0.5)
        c.update(0.1)
        dx, dy = c.get_offset()
        # Some shake should be applied; at least one axis non-zero
        assert abs(dx) > 0.0 or abs(dy) > 0.0

    def test_has_active_shakes_while_alive(self) -> None:
        c = SceneCamera()
        c.add_shake(amplitude=5.0, duration=0.3)
        assert c.has_active_shakes

    def test_shake_expires_after_duration(self) -> None:
        c = SceneCamera()
        c.add_shake(amplitude=10.0, duration=0.2)
        c.update(0.3)  # past duration
        assert not c.has_active_shakes
        assert c.get_offset() == pytest.approx((0.0, 0.0))

    def test_multiple_shakes_compose(self) -> None:
        c = SceneCamera()
        c.add_shake(amplitude=5.0, duration=0.5)
        c.add_shake(amplitude=3.0, duration=0.5)
        assert c.has_active_shakes
        # Can't test exact offset values without mocking math.sin;
        # test that the structure supports multiple shakes by confirming
        # both are tracked internally.
        assert len(c._shakes) == 2

    def test_clear_shakes_removes_all(self) -> None:
        c = SceneCamera()
        c.add_shake(amplitude=10.0, duration=1.0)
        c.add_shake(amplitude=5.0, duration=1.0)
        c.clear_shakes()
        assert not c.has_active_shakes
        assert c.get_offset() == pytest.approx((0.0, 0.0))

    def test_shake_decays_over_time(self) -> None:
        """Default linear decay: amplitude at t=0 > amplitude at t=0.5."""
        s = ShakeSource(amplitude=10.0, duration=1.0, frequency=30.0)
        # Max-ish offset near start (phase-dependent, but can sample many)
        samples_early = []
        for i in range(10):
            s.elapsed = 0.001 * i
            dx, dy = s.current_offset()
            samples_early.append(max(abs(dx), abs(dy)))
        max_early = max(samples_early)

        samples_late = []
        for i in range(10):
            s.elapsed = 0.9 + 0.001 * i
            dx, dy = s.current_offset()
            samples_late.append(max(abs(dx), abs(dy)))
        max_late = max(samples_late)

        assert max_late < max_early


class TestSceneCameraParallax:
    """Per-layer parallax factors scale camera offset."""

    def test_unregistered_layer_is_full_parallax(self) -> None:
        """Default factor = 1.0 for unregistered layers."""
        c = SceneCamera(offset=(100.0, 50.0))
        assert c.get_layer_offset(999) == pytest.approx((100.0, 50.0))

    def test_registered_layer_scales_offset(self) -> None:
        c = SceneCamera(offset=(100.0, 50.0))
        c.set_parallax_factor(1, 0.1)
        assert c.get_layer_offset(1) == pytest.approx((10.0, 5.0))

    def test_zero_factor_static_layer(self) -> None:
        c = SceneCamera(offset=(500.0, 200.0))
        c.set_parallax_factor(0, 0.0)
        assert c.get_layer_offset(0) == pytest.approx((0.0, 0.0))

    def test_get_parallax_factor_registered(self) -> None:
        c = SceneCamera()
        c.set_parallax_factor(2, 0.3)
        assert c.get_parallax_factor(2) == pytest.approx(0.3)

    def test_get_parallax_factor_unregistered_default(self) -> None:
        c = SceneCamera()
        assert c.get_parallax_factor(42) == pytest.approx(1.0)


class TestSceneCameraTransform:
    """world_to_screen helper applies offset + zoom + parallax."""

    def test_identity_transform(self) -> None:
        c = SceneCamera()
        # No offset, zoom=1.0, layer=1 (full parallax by default)
        result = c.world_to_screen((50.0, 30.0), screen_center=(400.0, 300.0), layer=1)
        # (50 - 0) * 1.0 + 400, (30 - 0) * 1.0 + 300
        assert result == pytest.approx((450.0, 330.0))

    def test_offset_applied(self) -> None:
        c = SceneCamera(offset=(10.0, 0.0))
        result = c.world_to_screen((50.0, 0.0), screen_center=(400.0, 300.0), layer=1)
        # With full parallax, camera offset subtracts from world: (50 - 10) + 400 = 440
        assert result[0] == pytest.approx(440.0)

    def test_zoom_applied(self) -> None:
        c = SceneCamera(zoom=2.0)
        # World (50, 0) at zoom 2.0: (50 * 2) + 400 = 500
        result = c.world_to_screen((50.0, 0.0), screen_center=(400.0, 300.0), layer=1)
        assert result[0] == pytest.approx(500.0)

    def test_layer_parallax_in_transform(self) -> None:
        c = SceneCamera(offset=(100.0, 0.0))
        c.set_parallax_factor(1, 0.1)  # far background
        result = c.world_to_screen((0.0, 0.0), screen_center=(400.0, 300.0), layer=1)
        # Layer-1 offset is 100 * 0.1 = 10; world (0,0) - 10 = -10; + 400 = 390
        assert result[0] == pytest.approx(390.0)


class TestSceneCameraShakeOnly:
    """get_shake_offset returns shake contribution without pan.

    Used by views that want UI elements to shake with impacts while
    staying anchored (not panning with camera).
    """

    def test_no_shake_returns_zero(self) -> None:
        c = SceneCamera(offset=(100.0, 50.0))  # pan exists
        # No shake; shake-only offset is zero
        assert c.get_shake_offset() == pytest.approx((0.0, 0.0))

    def test_shake_only_excludes_pan(self) -> None:
        c = SceneCamera(offset=(100.0, 50.0))  # pan exists
        c.add_shake(amplitude=10.0, duration=0.5)
        c.update(0.1)
        shake_ox, shake_oy = c.get_shake_offset()
        full_ox, full_oy = c.get_offset()
        # Full includes the 100/50 pan; shake-only does not
        assert abs(full_ox - 100.0 - shake_ox) == pytest.approx(0.0, abs=0.001)
        assert abs(full_oy - 50.0 - shake_oy) == pytest.approx(0.0, abs=0.001)


class TestSceneCameraGetTransform:
    """get_transform convenience returns (offset, zoom)."""

    def test_returns_current_state(self) -> None:
        c = SceneCamera(offset=(5.0, 10.0), zoom=1.5)
        offset, zoom = c.get_transform()
        assert offset == pytest.approx((5.0, 10.0))
        assert zoom == pytest.approx(1.5)

    def test_includes_shake_offset(self) -> None:
        """get_offset includes shake; get_transform uses get_offset."""
        c = SceneCamera(offset=(0.0, 0.0))
        c.add_shake(amplitude=5.0, duration=0.5)
        c.update(0.1)
        offset, _ = c.get_transform()
        # Shake should have contributed some offset
        dx, dy = offset
        assert abs(dx) > 0.0 or abs(dy) > 0.0


class TestShakeSource:
    """ShakeSource is the individual shake event."""

    def test_alive_while_within_duration(self) -> None:
        s = ShakeSource(amplitude=10.0, duration=1.0)
        assert s.alive
        s.elapsed = 0.5
        assert s.alive

    def test_not_alive_at_duration(self) -> None:
        s = ShakeSource(amplitude=10.0, duration=1.0)
        s.elapsed = 1.0
        assert not s.alive

    def test_dead_shake_returns_zero_offset(self) -> None:
        s = ShakeSource(amplitude=10.0, duration=1.0)
        s.elapsed = 2.0  # well past duration
        assert s.current_offset() == (0.0, 0.0)

    def test_amplitude_peak_scales_with_amplitude(self) -> None:
        """Higher amplitude produces larger peak offset."""
        s_small = ShakeSource(amplitude=2.0, duration=1.0, frequency=30.0)
        s_large = ShakeSource(amplitude=20.0, duration=1.0, frequency=30.0)
        # Sample at the same phase (just past zero)
        s_small.elapsed = 0.01
        s_large.elapsed = 0.01
        _, dy_small = s_small.current_offset()
        _, dy_large = s_large.current_offset()
        assert abs(dy_large) > abs(dy_small)


class TestSceneCameraIntegration:
    """Scenario tests matching real combat usage patterns."""

    def test_combat_focus_pattern(self) -> None:
        """Simulate: DEFAULT → FOCUS_PLAYER → DEFAULT pacing-beat relax."""
        c = SceneCamera()
        # Register combat's canonical parallax layers
        c.set_parallax_factor(1, 0.1)  # far starfield
        c.set_parallax_factor(4, 1.0)  # foreground ships

        # Action committed: FOCUS_PLAYER (offset -80, zoom 1.25, 300ms)
        c.transition_to(offset=(-80.0, 0.0), zoom=1.25, duration=0.3)
        c.update(0.3)
        assert c.get_offset()[0] == pytest.approx(-80.0)
        assert c.get_zoom() == pytest.approx(1.25)

        # Impact shake
        c.add_shake(amplitude=4.0, duration=0.15)

        # Pacing beat: relax to DEFAULT over 250ms
        c.transition_to(offset=(0.0, 0.0), zoom=1.0, duration=0.25)
        # Partway through relax — shake still contributing
        c.update(0.1)
        assert c.is_transitioning

        # Past relax duration and past shake
        c.update(0.3)
        assert not c.is_transitioning
        assert not c.has_active_shakes
        assert c.get_offset() == pytest.approx((0.0, 0.0))
        assert c.get_zoom() == pytest.approx(1.0)

    def test_parallax_layer_offsets_differ(self) -> None:
        """Far background and foreground receive different offsets."""
        c = SceneCamera(offset=(100.0, 0.0))
        c.set_parallax_factor(1, 0.1)
        c.set_parallax_factor(4, 1.0)

        far_offset = c.get_layer_offset(1)
        near_offset = c.get_layer_offset(4)

        # Far layer drifts less (10px vs 100px at full parallax)
        assert far_offset[0] == pytest.approx(10.0)
        assert near_offset[0] == pytest.approx(100.0)
