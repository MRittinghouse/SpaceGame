"""PT-M "Training wheels" regression tests.

Covers the first-time tip overlay component and its integration across the
six priority views (mission log, galaxy map, trading, shipyard, skill tree,
character sheet).
"""

from __future__ import annotations

import os
from pathlib import Path
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


# ---------------------------------------------------------------------------
# FirstTimeTipOverlay — component unit tests
# ---------------------------------------------------------------------------


class TestFirstTimeTipOverlay:
    def _make(self, on_dismiss=None):
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        return FirstTimeTipOverlay(
            title="Test Title", body="Test body content.", on_dismiss=on_dismiss
        )

    def test_initial_state(self) -> None:
        o = self._make()
        assert o.dismissed is False
        assert o.title == "Test Title"
        assert o.body == "Test body content."

    def test_update_advances_fade_timer(self) -> None:
        o = self._make()
        start = o._fade_timer
        o.update(0.1)
        assert o._fade_timer < start
        assert o._fade_timer >= 0

    def test_fade_timer_clamps_to_zero(self) -> None:
        o = self._make()
        o.update(100.0)  # way more than fade duration
        assert o._fade_timer == 0.0

    def test_escape_dismisses(self) -> None:
        calls = []
        o = self._make(on_dismiss=lambda: calls.append("x"))
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""})
        consumed = o.handle_event(evt)
        assert consumed is True
        assert o.dismissed is True
        assert calls == ["x"]

    def test_enter_dismisses(self) -> None:
        o = self._make()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\r"})
        o.handle_event(evt)
        assert o.dismissed is True

    def test_space_dismisses(self) -> None:
        o = self._make()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE, "unicode": " "})
        o.handle_event(evt)
        assert o.dismissed is True

    def test_numpad_enter_dismisses(self) -> None:
        o = self._make()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_KP_ENTER, "unicode": "\r"})
        o.handle_event(evt)
        assert o.dismissed is True

    def test_button_click_dismisses(self) -> None:
        o = self._make()
        click = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": o._btn_rect.center},
        )
        consumed = o.handle_event(click)
        assert consumed is True
        assert o.dismissed is True

    def test_click_outside_button_consumed_but_not_dismissed(self) -> None:
        """Modal semantics: clicks anywhere on screen are consumed so the
        view behind doesn't process them, but only the button dismisses."""
        o = self._make()
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})
        consumed = o.handle_event(click)
        assert consumed is True
        assert o.dismissed is False

    def test_callback_fires_exactly_once(self) -> None:
        calls = []
        o = self._make(on_dismiss=lambda: calls.append("x"))
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""})
        o.handle_event(evt)
        o.handle_event(evt)  # second dismiss shouldn't re-fire callback
        assert calls == ["x"]

    def test_events_pass_through_after_dismiss(self) -> None:
        o = self._make()
        o._dismiss()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE, "unicode": " "})
        assert o.handle_event(evt) is False

    def test_hover_doesnt_consume(self) -> None:
        o = self._make()
        evt = pygame.event.Event(
            pygame.MOUSEMOTION, {"pos": (100, 100), "rel": (0, 0), "buttons": (0, 0, 0)}
        )
        consumed = o.handle_event(evt)
        assert consumed is False

    def test_render_does_not_crash(self) -> None:
        o = self._make()
        screen = pygame.Surface((1280, 720))
        o.render(screen)  # fade-in state
        o.update(1.0)
        o.render(screen)  # post-fade state
        o._dismiss()
        o.render(screen)  # dismissed state should no-op cleanly


# ---------------------------------------------------------------------------
# Voice compliance on all 6 tip bodies
# ---------------------------------------------------------------------------


_TIP_SOURCE_FILES = [
    "spacegame/views/mission_log_view.py",
    "spacegame/views/galaxy_map_view.py",
    "spacegame/views/trading_view.py",
    "spacegame/views/shipyard_view.py",
    "spacegame/views/skill_tree_view.py",
    "spacegame/views/character_view.py",
    "spacegame/views/encounter_view.py",
]


class TestTipBodyWritingCompliance:
    def _tip_bodies_raw(self) -> list[str]:
        """Extract the body string passed to FirstTimeTipOverlay in each view."""
        import re

        bodies: list[str] = []
        pat = re.compile(
            r"FirstTimeTipOverlay\s*\(\s*title=.*?body=\((.*?)\)\s*,",
            re.DOTALL,
        )
        for fn in _TIP_SOURCE_FILES:
            text = Path(fn).read_text(encoding="utf-8")
            for m in pat.finditer(text):
                # Collapse the concatenated string literals into one body.
                body = "".join(s.strip().strip('"').strip("'") for s in m.group(1).split("\n"))
                bodies.append(body)
        return bodies

    def test_all_six_tips_registered(self) -> None:
        # Six primary view tips + three smuggling sub-feature tips
        # (hidden_compartment in shipyard_view, black_market in trading_view,
        # customs_inspection in encounter_view).
        bodies = self._tip_bodies_raw()
        assert len(bodies) == 9, f"expected 9 tip bodies, found {len(bodies)}"

    def test_no_em_dashes(self) -> None:
        for body in self._tip_bodies_raw():
            assert "\u2014" not in body, f"em-dash in tip body: {body!r}"

    def test_no_ai_tells(self) -> None:
        banned = ["couldn't help but", "a testament to"]
        for body in self._tip_bodies_raw():
            low = body.lower()
            for phrase in banned:
                assert phrase not in low, f"banned phrase '{phrase}' in: {body!r}"

    def test_bodies_are_concise(self) -> None:
        """Design doc says 1-3 sentences. Allow up to 4 for complex screens."""
        for body in self._tip_bodies_raw():
            sentences = [
                s for s in body.replace("!", ".").replace("?", ".").split(".") if s.strip()
            ]
            assert 1 <= len(sentences) <= 4, (
                f"tip body has {len(sentences)} sentences (expected 1-4): {body!r}"
            )


# ---------------------------------------------------------------------------
# Per-view integration — each view registers the tip on first entry
# ---------------------------------------------------------------------------


class TestViewIntegration:
    """Source-level check: each view has the expected flag literals and the
    FirstTimeTipOverlay wiring. Avoids per-view test harnesses which would
    require significant construction boilerplate for each."""

    EXPECTED = {
        "spacegame/views/mission_log_view.py": "seen_tip_mission_log",
        "spacegame/views/galaxy_map_view.py": "seen_tip_galaxy_map",
        "spacegame/views/trading_view.py": "seen_tip_trading",
        "spacegame/views/shipyard_view.py": "seen_tip_shipyard",
        "spacegame/views/skill_tree_view.py": "seen_tip_skill_tree",
        "spacegame/views/character_view.py": "seen_tip_character",
    }

    def test_all_views_instantiate_overlay(self) -> None:
        for path in _TIP_SOURCE_FILES:
            src = Path(path).read_text(encoding="utf-8")
            assert "FirstTimeTipOverlay(" in src, f"view missing tip overlay instantiation: {path}"

    def test_all_views_call_maybe_show_tip(self) -> None:
        for path in _TIP_SOURCE_FILES:
            src = Path(path).read_text(encoding="utf-8")
            assert "_maybe_show_tip" in src, f"view missing _maybe_show_tip hook: {path}"

    def test_all_views_override_render_top(self) -> None:
        for path in _TIP_SOURCE_FILES:
            src = Path(path).read_text(encoding="utf-8")
            assert "def render_top" in src, (
                f"view missing render_top override (tip would sit below UI): {path}"
            )

    def test_all_views_drain_dismissed_tip(self) -> None:
        """Views should null out _first_time_tip once dismissed so subsequent
        on_enter re-entries work from a clean state."""
        for path in _TIP_SOURCE_FILES:
            src = Path(path).read_text(encoding="utf-8")
            assert "self._first_time_tip = None" in src, (
                f"view missing tip-cleanup on dismiss: {path}"
            )

    def test_each_view_reads_and_writes_its_flag(self) -> None:
        """Scanner-critical: both the flag read (dialogue_flags.get) and the
        write (dialogue_flags[...]) must be in the view's source with literal
        strings so the dialogue-integrity scanner detects them."""
        for path, flag in self.EXPECTED.items():
            src = Path(path).read_text(encoding="utf-8")
            assert f'"{flag}"' in src, f"flag literal '{flag}' missing in {path}"
            # Read pattern
            assert f'dialogue_flags.get("{flag}"' in src, (
                f"flag read for '{flag}' missing in {path}"
            )
            # Write pattern
            assert f'dialogue_flags["{flag}"]' in src, f"flag write for '{flag}' missing in {path}"


# ---------------------------------------------------------------------------
# Mission log runtime integration — tests actual behavior
# ---------------------------------------------------------------------------


class TestMissionLogViewTipRuntime:
    """Exercise the on_enter → overlay creation path end-to-end for one view.
    Rest rely on source-level integration checks above since each view follows
    the same pattern."""

    def _make_view(self, player_flags: dict[str, bool]):
        import pygame_gui
        from spacegame.models.mission import MissionManager
        from spacegame.views.mission_log_view import MissionLogView

        manager = pygame_gui.UIManager((1280, 720))
        mgr = MissionManager([])
        player = MagicMock()
        player.dialogue_flags = dict(player_flags)
        view = MissionLogView(manager, mgr, data_loader=MagicMock(), player=player)
        view.on_enter()
        return view, player

    def test_tip_shown_on_first_entry(self) -> None:
        view, _ = self._make_view(player_flags={})
        assert view._first_time_tip is not None
        assert "Mission Log" == view._first_time_tip.title

    def test_tip_suppressed_if_already_seen(self) -> None:
        view, _ = self._make_view(player_flags={"seen_tip_mission_log": True})
        assert view._first_time_tip is None

    def test_dismiss_sets_flag(self) -> None:
        view, player = self._make_view(player_flags={})
        assert view._first_time_tip is not None
        # Simulate Escape dismiss
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""})
        view._first_time_tip.handle_event(evt)
        assert player.dialogue_flags.get("seen_tip_mission_log") is True

    def test_tip_consumes_events_before_view(self) -> None:
        """The view's handle_event should return early when the tip consumes."""
        view, _ = self._make_view(player_flags={})
        # Send a random keydown; tip should eat it and the view should not
        # attempt to change next_state or similar.
        original_next_state = view.next_state
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "unicode": "a"})
        view.handle_event(evt)
        # Tip remains active (not dismissed by 'a'), no state change happened
        assert view.next_state == original_next_state
        assert view._first_time_tip is not None

    def test_tip_cleared_on_update_after_dismiss(self) -> None:
        view, _ = self._make_view(player_flags={})
        assert view._first_time_tip is not None
        view._first_time_tip._dismiss()
        view.update(0.1)
        assert view._first_time_tip is None


# ---------------------------------------------------------------------------
# Main loop modal event consumption — source-level guard
# ---------------------------------------------------------------------------


class TestMainLoopModalConsumption:
    def test_game_loop_routes_events_to_tip_first(self) -> None:
        """Before pygame_gui processes events, the active view's tip gets
        first crack. Verifies the guard block exists in game.py."""
        src = Path("spacegame/engine/game.py").read_text(encoding="utf-8")
        assert "get_current_view()" in src, (
            "game.py must query state_manager.get_current_view() to route to tip"
        )
        assert "_first_time_tip" in src, "game.py must check for active tip"

    def test_state_manager_exposes_current_view(self) -> None:
        from spacegame.engine.state_manager import StateManager

        sm = StateManager()
        assert sm.get_current_view() is None  # no state bound yet
