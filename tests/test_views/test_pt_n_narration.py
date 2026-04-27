"""PT-N: narration modal + phase objective strip + phase-narration firing.

Covers:
  - TutorialNarrationModal: speaker render, dismiss path, inherits
    FirstTimeTipOverlay event handling.
  - _tutorial_maybe_fire_phase_narration fires once per phase, respects
    dialogue_flags so it doesn't re-fire after save/reload.
  - _tutorial_progress_text returns meaningful progress strings.
  - Writing Bible compliance on the three phase-narration bodies.
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
    """Same helper as test_pt_n_phase_machine — minimal wired builder."""
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
    view._tutorial_narration_modal = None
    view._tutorial_last_phase_shown = ""
    for pid in bought_part_ids or []:
        view.player.dialogue_flags[f"tutorial_bought_part_{pid}"] = True
    return view


# ---------------------------------------------------------------------------
# TutorialNarrationModal component
# ---------------------------------------------------------------------------


class TestTutorialNarrationModal:
    def test_constructor_stores_speaker(self) -> None:
        from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

        m = TutorialNarrationModal("Mechanic", "Title", "Body.")
        assert m.speaker == "Mechanic"
        assert m.title == "Title"
        assert m.body == "Body."
        assert m.dismissed is False

    def test_inherits_event_handling(self) -> None:
        """Escape should dismiss, same as FirstTimeTipOverlay."""
        from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

        m = TutorialNarrationModal("Mechanic", "T", "B")
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""})
        m.handle_event(evt)
        assert m.dismissed is True

    def test_on_dismiss_callback_fires(self) -> None:
        from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

        calls = []
        m = TutorialNarrationModal("Mechanic", "T", "B", on_dismiss=lambda: calls.append("x"))
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\r"})
        m.handle_event(evt)
        assert calls == ["x"]

    def test_render_does_not_crash(self) -> None:
        from spacegame.views.tutorial_narration_modal import TutorialNarrationModal

        m = TutorialNarrationModal("Mechanic", "Phase 1 of 3", "Some narration.")
        screen = pygame.Surface((1280, 720))
        m.render(screen)  # fading in
        m.update(1.0)
        m.render(screen)  # fully visible
        m._dismiss()
        m.render(screen)  # dismissed — should no-op


# ---------------------------------------------------------------------------
# Phase-narration firing + once-per-phase guard
# ---------------------------------------------------------------------------


class TestPhaseNarrationFiring:
    def test_fires_on_first_entry_to_slots_phase(self) -> None:
        view = _make_builder_tutorial(
            bought_part_ids=[
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "scrapyard_hold",
            ]
        )
        assert view._tutorial_narration_modal is None
        view._tutorial_maybe_fire_phase_narration()
        assert view._tutorial_narration_modal is not None
        assert "Phase 1" in view._tutorial_narration_modal.title

    def test_does_not_refire_while_in_same_phase(self) -> None:
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        view._tutorial_maybe_fire_phase_narration()
        modal1 = view._tutorial_narration_modal
        assert modal1 is not None
        # Clear the modal (as if dismissed) but stay in same phase
        view._tutorial_narration_modal = None
        # _last_phase_shown still set; firing again should no-op
        view._tutorial_maybe_fire_phase_narration()
        assert view._tutorial_narration_modal is None

    def test_does_not_fire_if_flag_already_set(self) -> None:
        """Persistence: if the player has seen this phase narration before
        (reloaded from save), don't re-fire."""
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        view.player.dialogue_flags["tutorial_phase_slots_narration_seen"] = True
        view._tutorial_maybe_fire_phase_narration()
        assert view._tutorial_narration_modal is None

    def test_mark_phase_seen_persists_flag(self) -> None:
        view = _make_builder_tutorial()
        view._tutorial_mark_phase_seen("slots")
        assert view.player.dialogue_flags["tutorial_phase_slots_narration_seen"] is True

    def test_non_tutorial_mode_no_fire(self) -> None:
        view = _make_builder_tutorial()
        view._tutorial_mode = False
        view._tutorial_maybe_fire_phase_narration()
        assert view._tutorial_narration_modal is None


# ---------------------------------------------------------------------------
# Phase objective strip progress text
# ---------------------------------------------------------------------------


def _place_slot(view, slot_def_id: str) -> None:
    from spacegame.models.ship_build import PlacedSlot

    view.build.placed_slots.append(PlacedSlot(slot_def_id=slot_def_id, x=0, y=0, rotation=0))


def _paint_pixels(view, count: int) -> None:
    from spacegame.models.ship_build import PlacedPixel

    for i in range(count):
        view.build.pixels.append(PlacedPixel(x=i % 16, y=i // 16, material_id="standard_plate"))


class TestPhaseProgressText:
    def test_slots_phase_progress(self) -> None:
        view = _make_builder_tutorial(
            bought_part_ids=[
                "scrapyard_thruster",
                "scrapyard_reactor",
                "scrapyard_fuel_cell",
                "scrapyard_hold",
            ]
        )
        text = view._tutorial_progress_text()
        assert "Slots placed: 0/5" == text
        _place_slot(view, "cockpit_scout_pod")
        _place_slot(view, "engine_small")
        assert view._tutorial_progress_text() == "Slots placed: 2/5"

    def test_hull_phase_progress(self) -> None:
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        # Satisfy phase A (only need cockpit + engine)
        _place_slot(view, "cockpit_scout_pod")
        _place_slot(view, "engine_small")
        assert view._tutorial_phase() == "hull"
        assert view._tutorial_progress_text() == "Hull pixels: 0/20+"
        _paint_pixels(view, 12)
        assert view._tutorial_progress_text() == "Hull pixels: 12/20+"

    def test_complete_phase_prompt(self) -> None:
        view = _make_builder_tutorial(bought_part_ids=["scrapyard_thruster"])
        _place_slot(view, "cockpit_scout_pod")
        _place_slot(view, "engine_small")
        _paint_pixels(view, 25)
        assert view._tutorial_phase() == "complete"
        assert "CONFIRM BUILD" in view._tutorial_progress_text()


# ---------------------------------------------------------------------------
# Writing Bible compliance on narration content
# ---------------------------------------------------------------------------


class TestWeightWarnings:
    def _make_view_with_weight(self, current: float, max_weight: int = 55):
        view = _make_builder_tutorial()
        stats = MagicMock()
        stats.weight_current = current
        stats.weight_max = max_weight
        view._computed_stats = stats
        return view

    def test_no_warning_under_heavy_threshold(self) -> None:
        view = self._make_view_with_weight(current=40.0)  # 40/55 ≈ 73%
        view._tutorial_maybe_fire_weight_warning()
        assert view._tutorial_narration_modal is None

    def test_fires_heavy_warning_at_80_percent(self) -> None:
        view = self._make_view_with_weight(current=44.0)  # exactly 80%
        view._tutorial_maybe_fire_weight_warning()
        assert view._tutorial_narration_modal is not None
        assert "Weight" in view._tutorial_narration_modal.title
        assert view.player.dialogue_flags.get("tutorial_weight_heavy_seen") is True

    def test_fires_overloaded_warning_at_95_percent(self) -> None:
        view = self._make_view_with_weight(current=53.0)  # 53/55 ≈ 96%
        view._tutorial_maybe_fire_weight_warning()
        assert view._tutorial_narration_modal is not None
        assert "Overloaded" in view._tutorial_narration_modal.title
        assert view.player.dialogue_flags.get("tutorial_weight_overloaded_seen") is True

    def test_does_not_refire_after_flag_set(self) -> None:
        view = self._make_view_with_weight(current=50.0)  # 50/55 ≈ 91%, HEAVY
        view.player.dialogue_flags["tutorial_weight_heavy_seen"] = True
        view._tutorial_maybe_fire_weight_warning()
        assert view._tutorial_narration_modal is None

    def test_does_not_stack_over_existing_modal(self) -> None:
        """If a phase narration is already showing, weight warning waits."""
        view = self._make_view_with_weight(current=50.0)  # 50/55 ≈ 91%
        view._tutorial_narration_modal = MagicMock()
        view._tutorial_narration_modal.dismissed = False
        existing = view._tutorial_narration_modal
        view._tutorial_maybe_fire_weight_warning()
        # Existing modal stays; no new one stacked
        assert view._tutorial_narration_modal is existing

    def test_no_warning_in_non_tutorial_mode(self) -> None:
        view = self._make_view_with_weight(current=50.0)
        view._tutorial_mode = False
        view._tutorial_maybe_fire_weight_warning()
        assert view._tutorial_narration_modal is None

    def test_warning_content_writing_bible_clean(self) -> None:
        from spacegame.views.ship_builder_view import ShipBuilderView

        for key, (title, body) in ShipBuilderView._TUTORIAL_WEIGHT_WARNINGS.items():
            assert "\u2014" not in title, f"em-dash in weight warning title: {key}"
            assert "\u2014" not in body, f"em-dash in weight warning body: {key}"
            low = (title + " " + body).lower()
            for phrase in ["couldn't help but", "a testament to"]:
                assert phrase not in low, f"banned phrase in weight warning {key}"


class TestStatPreview:
    """Live stat preview panel — shape classifications, weight gauge,
    colorblind-aware color selection."""

    def _view_with_pixels(self, coords: list[tuple[int, int]]):
        from spacegame.models.ship_build import PlacedPixel

        view = _make_builder_tutorial()
        for x, y in coords:
            view.build.pixels.append(PlacedPixel(x=x, y=y, material_id="standard_plate"))
        return view

    def test_profile_classification_narrow(self) -> None:
        # Thin horizontal ship: canvas_w=16, filled_height small → profile < 0.3
        coords = [(x, 4) for x in range(10)]  # filled_h=1, profile_ratio=1/16≈0.06
        view = self._view_with_pixels(coords)
        tag, effect, color = view._tutorial_profile_classification()
        assert tag == "NARROW"
        assert "+10" in effect

    def test_profile_classification_wide(self) -> None:
        # Tall ship: filled_height=14 across 16-wide canvas → profile ≈ 0.875
        coords = [(5, y) for y in range(14)]
        view = self._view_with_pixels(coords)
        tag, effect, color = view._tutorial_profile_classification()
        assert tag == "WIDE"
        assert "-10" in effect

    def test_profile_classification_normal(self) -> None:
        # Medium ship: filled_height=8 across 16-wide canvas → profile = 0.5
        coords = [(5, y) for y in range(8)]
        view = self._view_with_pixels(coords)
        tag, effect, color = view._tutorial_profile_classification()
        assert tag == "NORMAL"

    def test_profile_empty_build(self) -> None:
        view = _make_builder_tutorial()
        tag, effect, color = view._tutorial_profile_classification()
        assert tag == "NORMAL"

    def test_balance_classification_empty(self) -> None:
        """Empty build defaults to BALANCED."""
        view = _make_builder_tutorial()
        tag, effect, color = view._tutorial_balance_classification()
        assert tag == "BALANCED"

    def test_palette_role_helper_fallback(self) -> None:
        from spacegame.config import Colors
        from spacegame.views.ship_builder_view import _palette_role_color

        # Valid role → real color from palette
        c = _palette_role_color("status_positive", Colors.GREEN)
        assert len(c) == 3
        # Unknown role → fallback
        c = _palette_role_color("nonexistent_role_xyz", (1, 2, 3))
        assert c == (1, 2, 3)

    def test_stat_preview_renders_without_crash(self) -> None:
        """Smoke test — preview panel should render cleanly with any build
        state (empty, partial, complete)."""
        view = _make_builder_tutorial()
        # Mock computed_stats
        stats = MagicMock()
        stats.hull = 42
        stats.armor = 5
        stats.shields = 8
        stats.speed = 8
        stats.evasion = 10
        stats.weight_current = 20.0
        stats.weight_max = 55
        view._computed_stats = stats
        # Need font attrs for rendering
        from spacegame.engine.fonts import FONT_MD, FONT_SM, FONT_XS, get_font

        view.small_font = get_font("header", FONT_MD)
        view.label_font = get_font("label", FONT_XS)
        # Needs data_loader hull_materials + ship_modules for balance calc
        # which are already present on the real DataLoader used in the helper
        screen = pygame.Surface((1280, 720))
        view._render_tutorial_stat_preview(screen)


class TestNarrationWritingCompliance:
    def test_no_em_dashes(self) -> None:
        from spacegame.views.ship_builder_view import ShipBuilderView

        narration = ShipBuilderView._TUTORIAL_NARRATION
        for phase, (title, body) in narration.items():
            assert "\u2014" not in title, f"em-dash in title: {phase}"
            assert "\u2014" not in body, f"em-dash in body: {phase}"

    def test_no_ai_tells(self) -> None:
        from spacegame.views.ship_builder_view import ShipBuilderView

        banned = ["couldn't help but", "a testament to"]
        narration = ShipBuilderView._TUTORIAL_NARRATION
        for phase, (title, body) in narration.items():
            low = (title + " " + body).lower()
            for phrase in banned:
                assert phrase not in low, f"banned phrase '{phrase}' in {phase}"

    def test_all_three_phases_present(self) -> None:
        from spacegame.views.ship_builder_view import ShipBuilderView

        phases = ShipBuilderView._TUTORIAL_NARRATION
        assert set(phases.keys()) == {"slots", "hull", "complete"}
