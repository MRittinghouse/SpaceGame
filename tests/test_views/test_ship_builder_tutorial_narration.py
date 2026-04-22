"""PT-007 playtest response: ship builder tutorial narration state machine.

Four-priority selection:
  1. Welcome — no parts placed, nothing selected
  2. Rotation tip — non-square slot selected, R not yet pressed
  3. Per-part prompt — next bought-but-unplaced part
  4. Completion — all bought parts placed; points to CONFIRM BUILD

Each priority is tested in isolation + priority ordering is verified.
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


def _make_builder():
    """Minimal ShipBuilderView with just enough state for narration logic."""
    from spacegame.views.ship_builder_view import ShipBuilderView

    view = ShipBuilderView.__new__(ShipBuilderView)
    view.player = MagicMock()
    view.player.dialogue_flags = {}
    view._selected_slot_def_id = None
    view._shown_rotation_tip = False
    view.data_loader = MagicMock()
    view.data_loader.slot_definitions = {}
    return view


def _tutorial_parts():
    return [
        {"slot_def_id": "cockpit_scout_pod"},
        {"slot_def_id": "engine_small"},
        {"slot_def_id": "reactor_small"},
        {"slot_def_id": "fuel_small"},
        {"slot_def_id": "cargo_small"},
    ]


def _part_narration():
    return {
        "cockpit_scout_pod": "Cockpit first. Select it on the left, place it on the grid.",
        "engine_small": "Engine next. Nothing leaves this bay without thrust.",
        "reactor_small": "Reactor in the core. Powers everything you've got.",
        "fuel_small": "Fuel tank. No fuel, no jumps. Simple.",
        "cargo_small": "Cargo bay. Somewhere to stash whatever pays the bills.",
    }


class TestNarrationPriorities:
    """Each narration priority fires in the right state."""

    def test_welcome_when_nothing_placed_or_selected(self) -> None:
        view = _make_builder()
        # Mark all parts bought but none placed; nothing selected.
        for p in _tutorial_parts():
            view.player.dialogue_flags[f"tutorial_bought_{p['slot_def_id']}"] = True
        narration = view._pick_tutorial_narration(
            placed_ids=set(), part_narration=_part_narration(), tutorial_parts=_tutorial_parts()
        )
        assert "pick a part" in narration.lower()

    def test_rotation_tip_when_tall_module_selected_and_not_rotated(self) -> None:
        view = _make_builder()
        for p in _tutorial_parts():
            view.player.dialogue_flags[f"tutorial_bought_{p['slot_def_id']}"] = True
        # Select a 1x2 (tall) slot, rotation tip not yet shown
        sd = MagicMock(footprint_w=1, footprint_h=2)
        view.data_loader.slot_definitions = {"engine_small": sd}
        view._selected_slot_def_id = "engine_small"
        view._shown_rotation_tip = False
        narration = view._pick_tutorial_narration(
            placed_ids=set(), part_narration=_part_narration(), tutorial_parts=_tutorial_parts()
        )
        assert "rotate" in narration.lower()
        assert "r " in narration.lower() or " r" in narration.lower()

    def test_rotation_tip_suppressed_after_player_rotates(self) -> None:
        view = _make_builder()
        for p in _tutorial_parts():
            view.player.dialogue_flags[f"tutorial_bought_{p['slot_def_id']}"] = True
        sd = MagicMock(footprint_w=1, footprint_h=2)
        view.data_loader.slot_definitions = {"engine_small": sd}
        view._selected_slot_def_id = "engine_small"
        view._shown_rotation_tip = True  # Already rotated
        narration = view._pick_tutorial_narration(
            placed_ids=set(), part_narration=_part_narration(), tutorial_parts=_tutorial_parts()
        )
        assert "rotate" not in narration.lower()

    def test_rotation_tip_not_fired_for_square_modules(self) -> None:
        view = _make_builder()
        for p in _tutorial_parts():
            view.player.dialogue_flags[f"tutorial_bought_{p['slot_def_id']}"] = True
        sd = MagicMock(footprint_w=2, footprint_h=2)  # square
        view.data_loader.slot_definitions = {"reactor_small": sd}
        view._selected_slot_def_id = "reactor_small"
        narration = view._pick_tutorial_narration(
            placed_ids=set(), part_narration=_part_narration(), tutorial_parts=_tutorial_parts()
        )
        assert "rotate" not in narration.lower()

    def test_per_part_prompt_fires_for_first_bought_unplaced(self) -> None:
        view = _make_builder()
        # Bought cockpit + engine, placed cockpit; engine prompt should fire
        view.player.dialogue_flags["tutorial_bought_cockpit_scout_pod"] = True
        view.player.dialogue_flags["tutorial_bought_engine_small"] = True
        narration = view._pick_tutorial_narration(
            placed_ids={"cockpit_scout_pod"},
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "engine" in narration.lower()

    def test_completion_fires_when_all_placed(self) -> None:
        view = _make_builder()
        for p in _tutorial_parts():
            view.player.dialogue_flags[f"tutorial_bought_{p['slot_def_id']}"] = True
        placed = {p["slot_def_id"] for p in _tutorial_parts()}
        narration = view._pick_tutorial_narration(
            placed_ids=placed,
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        # PT-006 response: completion points at CONFIRM BUILD explicitly.
        assert "confirm build" in narration.lower()


class TestPriorityOrdering:
    """Higher-priority narration wins when multiple conditions are met."""

    def test_rotation_tip_beats_per_part_prompt(self) -> None:
        """When a tall module is selected AND bought-unplaced parts exist,
        the rotation tip takes priority (it's the more actionable hint)."""
        view = _make_builder()
        view.player.dialogue_flags["tutorial_bought_engine_small"] = True
        sd = MagicMock(footprint_w=1, footprint_h=2)
        view.data_loader.slot_definitions = {"engine_small": sd}
        view._selected_slot_def_id = "engine_small"
        view._shown_rotation_tip = False
        narration = view._pick_tutorial_narration(
            placed_ids=set(), part_narration=_part_narration(), tutorial_parts=_tutorial_parts()
        )
        assert "rotate" in narration.lower()
