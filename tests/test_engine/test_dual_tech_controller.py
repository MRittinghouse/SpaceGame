"""Tests for DualTechController (Combat C5 Session 3).

Covers:
  - Factory construction wires element roles through to trail config
  - Lifecycle: update advances timeline, is_complete tracks total duration
  - on_impact fires exactly once at IMPACT phase boundary
  - Per-phase rendering gates (darken, trail, portraits, tech name)
  - Tech name renders in dominant role with void_deep stroke
  - Camera + shake factor passthroughs
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.dual_tech_cinematic import (
    STANDARD_TOTAL,
    DualTechPhase,
)
from spacegame.engine.dual_tech_controller import DualTechController
from spacegame.engine.dual_tech_element_trail import TrailConfig
from spacegame.engine.dual_tech_portraits import PortraitConfig
from spacegame.engine.material_palette import get_role


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _portrait(fill: tuple[int, int, int] = (160, 160, 200)) -> PortraitConfig:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    surf.fill((*fill, 255))
    return PortraitConfig(surface=surf)


def _controller(
    *,
    tech_name: str = "FROST LANCE",
    dominant_element: str = "ion",
    secondary_element: str = "cryo",
    is_ultimate: bool = False,
    on_impact=None,  # type: ignore[no-untyped-def]
) -> DualTechController:
    return DualTechController.from_inputs(
        tech_name=tech_name,
        dominant_element=dominant_element,
        secondary_element=secondary_element,
        left_portrait=_portrait(),
        right_portrait=_portrait(),
        trail_start=(40.0, 200.0),
        trail_end=(600.0, 200.0),
        is_ultimate=is_ultimate,
        on_impact=on_impact,
    )


def _screen(w: int = 800, h: int = 400) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


def _any_opaque(surf: pygame.Surface) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            if surf.get_at((x, y)).a > 0:
                return True
    return False


def _contains_color(surf: pygame.Surface, rgb: tuple[int, int, int]) -> bool:
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            px = surf.get_at((x, y))
            if px.a > 0 and (px.r, px.g, px.b) == rgb:
                return True
    return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFromInputs:
    def test_factory_resolves_element_roles(self) -> None:
        c = _controller(dominant_element="plasma", secondary_element="voltaic")
        assert c.timeline.dominant_role == "plasma_core"
        assert c.timeline.secondary_role == "voltaic_strike"

    def test_trail_config_inherits_timeline_roles(self) -> None:
        c = _controller(dominant_element="ion", secondary_element="cryo")
        # Trail head uses dominant; trail tail uses the timeline's trail
        # role (which picks up the secondary element).
        assert c.trail_config.dominant_role == c.timeline.dominant_role
        assert c.trail_config.trail_role == c.timeline.trail_role

    def test_ultimate_flag_passes_through(self) -> None:
        c = _controller(is_ultimate=True)
        assert c.timeline.is_ultimate
        assert c.timeline.total_duration > STANDARD_TOTAL


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_not_complete_at_start(self) -> None:
        c = _controller()
        assert not c.is_complete

    def test_complete_after_total_duration(self) -> None:
        c = _controller()
        c.update(STANDARD_TOTAL + 0.1)
        assert c.is_complete

    def test_update_advances_timeline(self) -> None:
        c = _controller()
        c.update(0.5)
        assert c.timeline.elapsed == pytest.approx(0.5)

    def test_phase_passthrough_reflects_timeline(self) -> None:
        c = _controller()
        assert c.phase == DualTechPhase.CAMERA_ZOOM
        c.update(0.9)
        assert c.phase == DualTechPhase.NAME_HOLD

    def test_camera_zoom_factor_passthrough(self) -> None:
        c = _controller()
        c.update(0.3)
        assert c.camera_zoom_factor == pytest.approx(0.5, abs=0.02)

    def test_impact_shake_factor_zero_outside_impact(self) -> None:
        c = _controller()
        c.update(1.0)
        assert c.impact_shake_factor == 0.0

    def test_impact_shake_factor_nonzero_during_impact(self) -> None:
        c = _controller()
        c.update(2.7 + 0.1)
        assert c.impact_shake_factor > 0.0


# ---------------------------------------------------------------------------
# on_impact callback
# ---------------------------------------------------------------------------


class TestImpactCallback:
    def test_impact_fires_once_at_impact_phase(self) -> None:
        fired: list[int] = []

        def _cb() -> None:
            fired.append(1)

        c = _controller(on_impact=_cb)
        c.update(2.7)  # enter IMPACT
        assert len(fired) == 1

    def test_impact_does_not_fire_before_impact_phase(self) -> None:
        fired: list[int] = []

        def _cb() -> None:
            fired.append(1)

        c = _controller(on_impact=_cb)
        c.update(2.0)  # still in COMBINED_RESOLVE
        assert fired == []

    def test_impact_does_not_fire_twice(self) -> None:
        fired: list[int] = []

        def _cb() -> None:
            fired.append(1)

        c = _controller(on_impact=_cb)
        c.update(2.7)
        c.update(0.2)
        c.update(0.2)
        assert len(fired) == 1

    def test_no_callback_does_not_crash(self) -> None:
        """on_impact=None must still work — controller doesn't require a callback."""
        c = _controller(on_impact=None)
        c.update(STANDARD_TOTAL + 0.1)  # sweep through impact
        assert c.is_complete

    def test_ultimate_impact_fires_at_later_time(self) -> None:
        fired: list[int] = []

        def _cb() -> None:
            fired.append(1)

        c = _controller(is_ultimate=True, on_impact=_cb)
        # Ultimate impact starts at 3.0
        c.update(2.7)  # still in CHARGE for ultimate
        assert fired == []
        c.update(0.4)  # now at 3.1 — IMPACT
        assert len(fired) == 1


# ---------------------------------------------------------------------------
# Rendering gates per phase
# ---------------------------------------------------------------------------


class TestRenderingGates:
    def test_camera_zoom_phase_renders_nothing(self) -> None:
        """During CAMERA_ZOOM the darken hasn't started, portraits are
        off-screen, trail hasn't started, tech name hasn't appeared."""
        c = _controller()
        c.update(0.3)  # mid CAMERA_ZOOM
        screen = _screen()
        c.render(screen)
        assert not _any_opaque(screen)

    def test_darken_phase_renders_overlay_only(self) -> None:
        """During DARKEN_PORTRAITS the darken overlay ramps + portraits slide."""
        c = _controller()
        c.update(0.7)  # mid DARKEN_PORTRAITS
        screen = _screen()
        c.render(screen)
        assert _any_opaque(screen)

    def test_name_hold_renders_tech_name(self) -> None:
        """During NAME_HOLD the tech name should be on-screen in the dominant role."""
        c = _controller(
            tech_name="FROST LANCE", dominant_element="cryo", secondary_element="ion"
        )
        c.update(1.1)  # mid NAME_HOLD
        screen = _screen()
        c.render(screen)
        cryo = get_role("cryo_fractal")
        assert _contains_color(screen, cryo)

    def test_name_hold_uses_void_deep_stroke(self) -> None:
        c = _controller()
        c.update(1.1)
        screen = _screen()
        c.render(screen)
        void_deep = get_role("void_deep")
        assert _contains_color(screen, void_deep)

    def test_combined_resolve_renders_trail(self) -> None:
        c = _controller(dominant_element="plasma", secondary_element="voltaic")
        c.update(2.0)  # mid COMBINED_RESOLVE
        screen = _screen()
        c.render(screen)
        # Head at dominant role; trail at timeline's trail role.
        plasma_core = get_role("plasma_core")
        assert _contains_color(screen, plasma_core)

    def test_complete_phase_renders_nothing(self) -> None:
        c = _controller()
        c.update(STANDARD_TOTAL + 0.1)
        screen = _screen()
        c.render(screen)
        assert not _any_opaque(screen)

    def test_rendering_is_safe_to_call_repeatedly(self) -> None:
        """Multiple render calls at the same timeline state produce the
        same frame — pure rendering."""
        c = _controller()
        c.update(1.0)
        screen_a = _screen()
        screen_b = _screen()
        c.render(screen_a)
        c.render(screen_b)
        # Compare a handful of opaque pixels.
        for y in (100, 200, 300):
            for x in (100, 400, 700):
                assert screen_a.get_at((x, y)) == screen_b.get_at((x, y))


# ---------------------------------------------------------------------------
# Tech name positioning
# ---------------------------------------------------------------------------


class TestTechNameCentered:
    def test_tech_name_renders_near_screen_center(self) -> None:
        """Tech name lands near screen center; opaque pixels cluster
        around the middle of the screen during NAME_HOLD."""
        c = _controller(tech_name="ICE SPEAR", dominant_element="cryo")
        c.update(1.1)
        screen = _screen(800, 400)
        c.render(screen)
        # Find opaque pixels that are NOT from the darken overlay — the
        # darken is uniform so we need to find pixels whose color
        # differs from pure dark. Tech name uses cryo (bright cyan)
        # which will dominate in terms of color distinctness.
        cryo = get_role("cryo_fractal")
        cryo_xs = []
        cryo_ys = []
        for y in range(400):
            for x in range(800):
                px = screen.get_at((x, y))
                if px.a > 0 and (px.r, px.g, px.b) == cryo:
                    cryo_xs.append(x)
                    cryo_ys.append(y)
        assert cryo_xs, "Expected at least one cryo_fractal pixel for tech name"
        # Center of mass should be near screen center (400, 200).
        cx = sum(cryo_xs) / len(cryo_xs)
        cy = sum(cryo_ys) / len(cryo_ys)
        assert 350 < cx < 450, f"tech name x-center {cx} should be near 400"
        assert 170 < cy < 230, f"tech name y-center {cy} should be near 200"
