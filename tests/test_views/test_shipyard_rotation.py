"""Regression test for shipyard loadout rotation handling.

Playtest finding 2026-04-22: an engine rotated in the drydock was
rendering in its default orientation in the Loadout view. Root cause:
``ShipyardView._slot_screen_rect`` used ``slot_def.footprint_w`` /
``footprint_h`` directly and ignored ``placed_slot.rotation``. Fix: go
through ``slot_def.get_rotated(rotation)`` so the dimensions swap at 90°
and 270°.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _make_shipyard():
    """Construct a minimal ShipyardView instance sufficient to call the
    rotation-sensitive geometry method."""
    from spacegame.views.shipyard_view import ShipyardView

    view = ShipyardView.__new__(ShipyardView)
    return view


def _slot_def_1x2():
    """Slot def with a 1x2 vertical footprint (tall). Rotating 90° → 2x1."""
    sd = MagicMock()
    sd.footprint_w = 1
    sd.footprint_h = 2
    sd.get_rotated = lambda r: ((1, 2, None), (2, 1, None), (1, 2, None), (2, 1, None))[r % 4]
    return sd


class TestSlotScreenRectRotation:
    """_slot_screen_rect honors placed_slot.rotation."""

    def test_rotation_zero_keeps_original_dimensions(self) -> None:
        view = _make_shipyard()
        ps = MagicMock(x=0, y=0, rotation=0)
        sd = _slot_def_1x2()
        gp = {"grid_x": 100, "grid_y": 50, "cell_size": 10}
        r = view._slot_screen_rect(ps, sd, gp)
        assert (r.width, r.height) == (10, 20)  # 1x2 cells at 10px

    def test_rotation_one_swaps_dimensions(self) -> None:
        """90° rotation → footprint swaps to 2x1."""
        view = _make_shipyard()
        ps = MagicMock(x=0, y=0, rotation=1)
        sd = _slot_def_1x2()
        gp = {"grid_x": 100, "grid_y": 50, "cell_size": 10}
        r = view._slot_screen_rect(ps, sd, gp)
        assert (r.width, r.height) == (20, 10)  # 2x1 cells

    def test_rotation_two_keeps_original_dimensions(self) -> None:
        """180° rotation → same footprint dimensions as unrotated."""
        view = _make_shipyard()
        ps = MagicMock(x=0, y=0, rotation=2)
        sd = _slot_def_1x2()
        gp = {"grid_x": 100, "grid_y": 50, "cell_size": 10}
        r = view._slot_screen_rect(ps, sd, gp)
        assert (r.width, r.height) == (10, 20)

    def test_rotation_three_swaps_dimensions(self) -> None:
        """270° rotation → footprint swaps (like 90°)."""
        view = _make_shipyard()
        ps = MagicMock(x=0, y=0, rotation=3)
        sd = _slot_def_1x2()
        gp = {"grid_x": 100, "grid_y": 50, "cell_size": 10}
        r = view._slot_screen_rect(ps, sd, gp)
        assert (r.width, r.height) == (20, 10)

    def test_rotation_missing_defaults_to_zero(self) -> None:
        """Placed slots without a rotation attribute default to 0° behavior."""
        view = _make_shipyard()
        # MagicMock without a rotation attribute — getattr fallback should be 0.
        ps = MagicMock(spec=["x", "y"])
        ps.x = 0
        ps.y = 0
        sd = _slot_def_1x2()
        gp = {"grid_x": 100, "grid_y": 50, "cell_size": 10}
        r = view._slot_screen_rect(ps, sd, gp)
        assert (r.width, r.height) == (10, 20)
