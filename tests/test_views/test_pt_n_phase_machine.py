"""PT-N: tutorial builder phase state machine tests.

Covers:
  - Phase detection helpers (_tutorial_required_slot_types,
    _is_tutorial_phase_a_complete, _is_tutorial_phase_b_complete,
    _tutorial_phase).
  - Tutorial charge amount math (placement 50% + hull full cost).
  - Auto-equip maps bought parts to slots by slot_type.
  - CONFIRM gating: _can_confirm is False whenever tutorial phase is not
    "complete" (structural Arna-interruption fix).
  - HULL mode lock during Phase A.
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


def _make_builder_tutorial(bought_part_ids: list[str] | None = None):
    """Build a minimally-wired ShipBuilderView in tutorial mode with a
    mock data_loader populated from the real one (so slot_definitions and
    ship_parts resolve correctly)."""
    from spacegame.data_loader import get_data_loader
    from spacegame.models.ship_build import ShipBuild
    from spacegame.views.ship_builder_view import ShipBuilderView

    dl = get_data_loader()
    dl.load_all()
    view = ShipBuilderView.__new__(ShipBuilderView)
    view._tutorial_mode = True
    view.data_loader = dl
    view.build = ShipBuild(weight_class="tiny")
    view.player = MagicMock()
    view.player.dialogue_flags = {}
    view.player.parts_inventory = {}
    view.player.credits = 5500
    for pid in bought_part_ids or []:
        view.player.dialogue_flags[f"tutorial_bought_part_{pid}"] = True
        view.player.parts_inventory[pid] = 1
    return view


def _place_slot(view, slot_def_id: str, x: int = 0, y: int = 0) -> None:
    """Append a PlacedSlot entry by ID directly — bypasses the builder's
    placement logic, which isn't needed for phase-gate tests."""
    from spacegame.models.ship_build import PlacedSlot

    view.build.placed_slots.append(
        PlacedSlot(slot_def_id=slot_def_id, x=x, y=y, rotation=0)
    )


def _paint_pixels(view, count: int, material_id: str = "standard_plate") -> None:
    from spacegame.models.ship_build import PlacedPixel

    for i in range(count):
        view.build.pixels.append(PlacedPixel(x=i % 16, y=i // 16, material_id=material_id))


# ---------------------------------------------------------------------------
# _tutorial_required_slot_types
# ---------------------------------------------------------------------------


class TestRequiredSlotTypes:
    def test_cockpit_always_required(self) -> None:
        view = _make_builder_tutorial()
        assert "cockpit" in view._tutorial_required_slot_types()

    def test_infers_from_bought_parts(self) -> None:
        view = _make_builder_tutorial(
            bought_part_ids=[
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "scrapyard_hold",
            ]
        )
        required = view._tutorial_required_slot_types()
        # cockpit + the slot_types of the four bought parts
        assert "cockpit" in required
        assert "engine" in required
        assert "reactor" in required
        assert "fuel" in required
        assert "cargo" in required

    def test_weapon_choice(self) -> None:
        view = _make_builder_tutorial(
            bought_part_ids=[
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "salvaged_pulse_emitter",
            ]
        )
        required = view._tutorial_required_slot_types()
        assert "weapon" in required
        assert "cargo" not in required


# ---------------------------------------------------------------------------
# Phase completion gates
# ---------------------------------------------------------------------------


class TestPhaseGates:
    def test_phase_a_incomplete_with_no_slots(self) -> None:
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        assert view._is_tutorial_phase_a_complete() is False
        assert view._tutorial_phase() == "slots"

    def test_phase_a_complete_when_required_placed(self) -> None:
        view = _make_builder_tutorial(
            bought_part_ids=[
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "scrapyard_hold",
            ]
        )
        _place_slot(view, "cockpit_scout_pod")
        _place_slot(view, "engine_small")
        _place_slot(view, "reactor_small")
        _place_slot(view, "fuel_small")
        _place_slot(view, "cargo_small")
        assert view._is_tutorial_phase_a_complete() is True

    def test_phase_b_needs_minimum_pixels(self) -> None:
        view = _make_builder_tutorial()
        assert view._is_tutorial_phase_b_complete() is False
        _paint_pixels(view, view._MIN_TUTORIAL_HULL_PIXELS - 1)
        assert view._is_tutorial_phase_b_complete() is False
        _paint_pixels(view, 1)
        assert view._is_tutorial_phase_b_complete() is True

    def test_phase_transitions(self) -> None:
        view = _make_builder_tutorial(
            bought_part_ids=[
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "scrapyard_hold",
            ]
        )
        assert view._tutorial_phase() == "slots"
        _place_slot(view, "cockpit_scout_pod")
        _place_slot(view, "engine_small")
        _place_slot(view, "reactor_small")
        _place_slot(view, "fuel_small")
        _place_slot(view, "cargo_small")
        assert view._tutorial_phase() == "hull"
        _paint_pixels(view, 25)
        assert view._tutorial_phase() == "complete"


# ---------------------------------------------------------------------------
# Tutorial charge math
# ---------------------------------------------------------------------------


class TestTutorialCharge:
    def test_empty_build_costs_zero(self) -> None:
        view = _make_builder_tutorial()
        assert view._tutorial_charge_amount() == 0

    def test_placement_half_off(self) -> None:
        """Single slot with placement_cost 300 charges 150 (50% discount)."""
        view = _make_builder_tutorial()
        _place_slot(view, "cockpit_scout_pod")
        # cockpit_scout_pod.placement_cost is 300 per earlier audit
        assert view._tutorial_charge_amount() == 150

    def test_hull_at_full_cost(self) -> None:
        """Hull pixels cost cost_per_pixel, no discount."""
        view = _make_builder_tutorial()
        _paint_pixels(view, 10, material_id="standard_plate")
        # standard_plate.cost_per_pixel = 15 per audit; 10 pixels * 15 = 150
        assert view._tutorial_charge_amount() == 150

    def test_combined_formula(self) -> None:
        view = _make_builder_tutorial()
        _place_slot(view, "cockpit_scout_pod")  # 300 * 0.5 = 150
        _place_slot(view, "engine_small")  # 600 * 0.5 = 300
        _paint_pixels(view, 20, material_id="standard_plate")  # 20 * 15 = 300
        # 150 + 300 + 300 = 750
        assert view._tutorial_charge_amount() == 750


# ---------------------------------------------------------------------------
# Auto-equip on confirm
# ---------------------------------------------------------------------------


class TestAutoEquip:
    def test_equips_part_matching_slot_type(self) -> None:
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        view.player.remove_part = MagicMock()
        _place_slot(view, "engine_small")
        view._tutorial_auto_equip()
        slot = view.build.placed_slots[0]
        assert slot.equipped_part_id == "scrapyard_thruster"
        view.player.remove_part.assert_called_once_with("scrapyard_thruster")

    def test_skips_cockpit_slots(self) -> None:
        """Cockpit slots are self-fulfilling; auto-equip shouldn't touch them."""
        view = _make_builder_tutorial()
        _place_slot(view, "cockpit_scout_pod")
        view._tutorial_auto_equip()
        assert view.build.placed_slots[0].equipped_part_id is None

    def test_skips_already_equipped(self) -> None:
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        view.player.remove_part = MagicMock()
        _place_slot(view, "engine_small")
        view.build.placed_slots[0].equipped_part_id = "light_thruster_rk"  # pre-equipped
        view._tutorial_auto_equip()
        # Pre-equipped stays; scrapyard not touched
        assert view.build.placed_slots[0].equipped_part_id == "light_thruster_rk"
        view.player.remove_part.assert_not_called()

    def test_mismatched_slot_and_part_no_equip(self) -> None:
        """A bought engine part shouldn't equip into a cargo slot."""
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        view.player.remove_part = MagicMock()
        _place_slot(view, "cargo_small")
        view._tutorial_auto_equip()
        assert view.build.placed_slots[0].equipped_part_id is None


# ---------------------------------------------------------------------------
# CONFIRM gating (Arna-interruption structural fix)
# ---------------------------------------------------------------------------


class TestConfirmGate:
    def test_recompute_forces_can_confirm_false_during_tutorial_phases(self) -> None:
        """Source-level guard: _recompute_stats sets _can_confirm = False
        whenever tutorial phase is not complete."""
        from pathlib import Path

        src = Path("spacegame/views/ship_builder_view.py").read_text(encoding="utf-8")
        # The gating block must be present, referencing both the tutorial
        # mode flag and the phase check.
        assert "self._tutorial_mode and self._tutorial_phase() != \"complete\"" in src
        assert "self._can_confirm = False" in src

    def test_confirm_build_bails_if_phase_not_complete(self) -> None:
        """Defensive check: even if _can_confirm got set True somehow, the
        tutorial branch of _confirm_build re-verifies phase before running."""
        from pathlib import Path

        src = Path("spacegame/views/ship_builder_view.py").read_text(encoding="utf-8")
        assert 'self._tutorial_phase() != "complete"' in src


# ---------------------------------------------------------------------------
# HULL mode lock during Phase A
# ---------------------------------------------------------------------------


class TestModeLock:
    def test_hull_mode_blocked_during_phase_a(self) -> None:
        """Source-level guard: click handler rejects mode='hull' while
        tutorial phase is 'slots'."""
        from pathlib import Path

        src = Path("spacegame/views/ship_builder_view.py").read_text(encoding="utf-8")
        # The block must check all three conditions in sequence
        assert "self._tutorial_mode" in src
        assert 'mode_id == "hull"' in src
        assert 'self._tutorial_phase() == "slots"' in src

    def test_tab_key_blocked_during_phase_a(self) -> None:
        """PT-N audit: keyboard shortcut cycling must respect the Phase A
        mode lock, not just mouse clicks."""
        from pathlib import Path

        src = Path("spacegame/views/ship_builder_view.py").read_text(encoding="utf-8")
        # The Tab-key block must guard on tutorial phase
        tab_block_idx = src.index("if event.key == pygame.K_TAB")
        # Look in the next ~500 chars for the guard
        tab_region = src[tab_block_idx : tab_block_idx + 500]
        assert "self._tutorial_mode" in tab_region
        assert 'self._tutorial_phase() == "slots"' in tab_region

    def test_escape_blocked_in_tutorial(self) -> None:
        """PT-N audit: Escape must not exit to SHIPYARD mid-tutorial.
        CONFIRM (gated on phase complete) is the only legitimate exit."""
        from pathlib import Path

        src = Path("spacegame/views/ship_builder_view.py").read_text(encoding="utf-8")
        esc_idx = src.index("elif event.key == pygame.K_ESCAPE")
        esc_region = src[esc_idx : esc_idx + 500]
        assert "self._tutorial_mode" in esc_region


class TestStatDeltas:
    """Delta tracking for the tutorial stat preview."""

    def _view_with_snapshot(self, snapshot: dict[str, float]):
        view = _make_builder_tutorial()
        view._tutorial_stat_snapshot = dict(snapshot)
        view._tutorial_stat_deltas = {}
        return view

    def test_delta_recorded_on_stat_increase(self) -> None:
        view = self._view_with_snapshot({"hull": 10, "armor": 0, "shields": 0, "speed": 8, "evasion": 10})
        stats = MagicMock()
        stats.hull = 15
        stats.armor = 0
        stats.shields = 0
        stats.speed = 8
        stats.evasion = 10
        view._computed_stats = stats
        view._tutorial_record_stat_deltas()
        assert "hull" in view._tutorial_stat_deltas
        delta, timer = view._tutorial_stat_deltas["hull"]
        assert delta == 5
        assert timer == 1.8

    def test_delta_recorded_on_stat_decrease(self) -> None:
        view = self._view_with_snapshot({"hull": 20, "armor": 0, "shields": 0, "speed": 8, "evasion": 10})
        stats = MagicMock()
        stats.hull = 15
        stats.armor = 0
        stats.shields = 0
        stats.speed = 8
        stats.evasion = 10
        view._computed_stats = stats
        view._tutorial_record_stat_deltas()
        delta, timer = view._tutorial_stat_deltas["hull"]
        assert delta == -5

    def test_sub_integer_float_noise_ignored(self) -> None:
        view = self._view_with_snapshot({"hull": 10.0, "armor": 0, "shields": 0, "speed": 8, "evasion": 10})
        stats = MagicMock()
        stats.hull = 10.3  # <0.5 difference, should be ignored
        stats.armor = 0
        stats.shields = 0
        stats.speed = 8
        stats.evasion = 10
        view._computed_stats = stats
        view._tutorial_record_stat_deltas()
        assert "hull" not in view._tutorial_stat_deltas

    def test_first_snapshot_records_nothing(self) -> None:
        """Empty snapshot means the view just entered; no delta should fire."""
        view = _make_builder_tutorial()
        view._tutorial_stat_snapshot = {}
        view._tutorial_stat_deltas = {}
        stats = MagicMock()
        stats.hull = 42
        stats.armor = 5
        stats.shields = 0
        stats.speed = 8
        stats.evasion = 10
        view._computed_stats = stats
        view._tutorial_record_stat_deltas()
        assert view._tutorial_stat_deltas == {}
        # Snapshot was updated for next comparison
        assert view._tutorial_stat_snapshot["hull"] == 42

    def test_tick_expires_delta(self) -> None:
        view = _make_builder_tutorial()
        view._tutorial_stat_deltas = {"hull": (5.0, 0.3)}
        view._tutorial_tick_stat_deltas(0.5)  # more than timer remaining
        assert "hull" not in view._tutorial_stat_deltas

    def test_tick_reduces_timer(self) -> None:
        view = _make_builder_tutorial()
        view._tutorial_stat_deltas = {"hull": (5.0, 1.0)}
        view._tutorial_tick_stat_deltas(0.3)
        assert view._tutorial_stat_deltas["hull"][1] == pytest.approx(0.7)
