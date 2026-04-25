"""PT-007 playtest response: ship builder tutorial narration state machine.

Four-priority selection:
  1. Welcome — no parts placed, nothing selected
  2. Rotation tip — non-square slot selected, R not yet pressed
  3. Per-part prompt — next bought-but-unplaced part
  4. Completion — all bought parts placed; points to CONFIRM BUILD

Each priority is tested in isolation + priority ordering is verified.

Rewritten 2026-04-24: the previous test stubs used fake ``slot_def_id``
keys that matched the production bug, so the tests protected the bug
instead of catching it. New fixtures use the real ``part_id`` schema +
real flag names + real ship_parts -> slot_type mapping.
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
    """ShipBuilderView with just enough state to exercise narration logic."""
    from spacegame.views.ship_builder_view import ShipBuilderView

    view = ShipBuilderView.__new__(ShipBuilderView)
    view.player = MagicMock()
    view.player.dialogue_flags = {}
    view._selected_slot_def_id = None
    view._shown_rotation_tip = False
    view.data_loader = MagicMock()
    # slot_definitions: tutorial slot_def_ids with slot_type + footprint
    view.data_loader.slot_definitions = {
        "cockpit_scout_pod": MagicMock(
            slot_type="cockpit", footprint_w=2, footprint_h=2
        ),
        "engine_small": MagicMock(
            slot_type="engine", footprint_w=1, footprint_h=2
        ),
        "reactor_small": MagicMock(
            slot_type="reactor", footprint_w=2, footprint_h=2
        ),
        "fuel_small": MagicMock(
            slot_type="fuel", footprint_w=1, footprint_h=1
        ),
        "cargo_small": MagicMock(
            slot_type="cargo", footprint_w=1, footprint_h=2
        ),
        "weapon_small": MagicMock(
            slot_type="weapon", footprint_w=1, footprint_h=1
        ),
    }
    # ship_parts: real tutorial part_ids with their slot_types
    view.data_loader.ship_parts = {
        "scrapyard_thruster": MagicMock(slot_type="engine"),
        "scrapyard_reactor": MagicMock(slot_type="reactor"),
        "scrapyard_fuel_cell": MagicMock(slot_type="fuel"),
        "scrapyard_hold": MagicMock(slot_type="cargo"),
        "salvaged_pulse_emitter": MagicMock(slot_type="weapon"),
    }
    return view


def _tutorial_parts():
    """Real TUTORIAL_PARTS schema: ``TutorialPart`` dataclass instances."""
    from spacegame.views.tutorial_shop_view import TutorialPart

    return [
        TutorialPart(
            part_id="scrapyard_thruster",
            name="Scrapyard Thruster",
            description="",
            cost=0,
            narration="",
            tag="REQUIRED",
        ),
        TutorialPart(
            part_id="scrapyard_reactor",
            name="Scrapyard Reactor",
            description="",
            cost=0,
            narration="",
            tag="REQUIRED",
        ),
        TutorialPart(
            part_id="scrapyard_fuel_cell",
            name="Scrapyard Fuel Cell",
            description="",
            cost=0,
            narration="",
            tag="REQUIRED",
        ),
        TutorialPart(
            part_id="scrapyard_hold",
            name="Scrapyard Hold",
            description="",
            cost=0,
            narration="",
            tag="CHOOSE ONE",
        ),
    ]


def _part_narration():
    return {
        "cockpit_scout_pod": "Cockpit first. Select it on the left, place it on the grid.",
        "engine_small": "Engine next. Nothing leaves this bay without thrust.",
        "reactor_small": "Reactor in the core. Powers everything you've got.",
        "fuel_small": "Fuel tank. No fuel, no jumps. Simple.",
        "cargo_small": "Cargo bay. Somewhere to stash whatever pays the bills.",
    }


def _buy_all(view, parts):
    """Use the REAL flag name the tutorial shop sets (via the registry helper)."""
    from spacegame.constants.flags import tutorial_bought_part

    for p in parts:
        view.player.dialogue_flags[tutorial_bought_part(p.part_id)] = True


class TestNarrationPriorities:
    """Each narration priority fires in the right state."""

    def test_welcome_when_nothing_placed_or_selected(self) -> None:
        view = _make_builder()
        _buy_all(view, _tutorial_parts())
        narration = view._pick_tutorial_narration(
            placed_ids=set(),
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "pick a part" in narration.lower()

    def test_rotation_tip_when_tall_module_selected_and_not_rotated(self) -> None:
        view = _make_builder()
        _buy_all(view, _tutorial_parts())
        view._selected_slot_def_id = "engine_small"  # 1x2 (tall)
        view._shown_rotation_tip = False
        narration = view._pick_tutorial_narration(
            placed_ids=set(),
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "rotate" in narration.lower()

    def test_rotation_tip_suppressed_after_player_rotates(self) -> None:
        view = _make_builder()
        _buy_all(view, _tutorial_parts())
        view._selected_slot_def_id = "engine_small"
        view._shown_rotation_tip = True  # Already rotated
        narration = view._pick_tutorial_narration(
            placed_ids=set(),
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "rotate" not in narration.lower()

    def test_rotation_tip_not_fired_for_square_modules(self) -> None:
        view = _make_builder()
        _buy_all(view, _tutorial_parts())
        view._selected_slot_def_id = "reactor_small"  # 2x2 square
        narration = view._pick_tutorial_narration(
            placed_ids=set(),
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "rotate" not in narration.lower()

    def test_per_part_prompt_fires_for_first_bought_unplaced(self) -> None:
        """Bought thruster (engine slot_type) + reactor; placed cockpit but
        not engine; narration points to engine next."""
        view = _make_builder()
        view.player.dialogue_flags[
            "tutorial_bought_part_scrapyard_thruster"
        ] = True
        view.player.dialogue_flags[
            "tutorial_bought_part_scrapyard_reactor"
        ] = True
        narration = view._pick_tutorial_narration(
            placed_ids={"cockpit_scout_pod"},  # cockpit placed, engine not
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "engine" in narration.lower()

    def test_completion_fires_when_all_placed(self) -> None:
        view = _make_builder()
        _buy_all(view, _tutorial_parts())
        # Place a slot_def for every slot_type the bought parts use
        placed = {
            "cockpit_scout_pod",  # cockpit (always)
            "engine_small",       # scrapyard_thruster slot_type
            "reactor_small",      # scrapyard_reactor slot_type
            "fuel_small",         # scrapyard_fuel_cell slot_type
            "cargo_small",        # scrapyard_hold slot_type
        }
        narration = view._pick_tutorial_narration(
            placed_ids=placed,
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "confirm build" in narration.lower()


class TestPriorityOrdering:
    """Higher-priority narration wins when multiple conditions are met."""

    def test_rotation_tip_beats_per_part_prompt(self) -> None:
        """Tall module selected AND bought-unplaced parts exist:
        rotation tip wins (more actionable in the moment)."""
        view = _make_builder()
        view.player.dialogue_flags[
            "tutorial_bought_part_scrapyard_thruster"
        ] = True
        view._selected_slot_def_id = "engine_small"  # 1x2
        view._shown_rotation_tip = False
        narration = view._pick_tutorial_narration(
            placed_ids=set(),
            part_narration=_part_narration(),
            tutorial_parts=_tutorial_parts(),
        )
        assert "rotate" in narration.lower()
