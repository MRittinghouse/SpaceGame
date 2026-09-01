"""Tests for CapstoneView lifecycle and narration voice compliance (A2-20).

AC9: on_enter creates the Continue button; on_exit tears it down; handle_event
on button press sets dismissed=True and calls the acknowledge callback;
get_next_state returns None.

AC12: the module-level _TEMPLATE constant contains no em-dashes, no banned
phrases, no parallel-negation construction, and no banned NPC names.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pygame_gui

from spacegame.models.capstone import Capstone
from spacegame.models.lens import Lens
from spacegame.views.capstone_view import _TEMPLATE, CapstoneView


def _setup_pygame() -> pygame_gui.UIManager:
    from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH

    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _make_capstone() -> Capstone:
    return Capstone(
        capstone_id="wealth_capstone",
        lens_id="wealth",
        capstone_threshold=95,
        cutscene_ref=None,
    )


def _make_lens() -> Lens:
    return Lens(
        lens_id="wealth",
        name="Wealth",
        core_fantasy="Build an interstellar commercial empire from a position of nothing.",
        question="After growing up with nothing, how much is finally enough?",
        sees="A supply gap, a price event forming, or a route nobody is running yet.",
        wants="Margin, leverage, and the next position before the current one closes.",
        trades="Time, loyalty, and the comfort of operating only within legal channels.",
        investment_from=("sold_cargo", "trade_profit_large"),
        minigame_shape="Optimisation under scarcity: routes, margins, leverage",
        voice="Optimized, additive; converts everything to margin and window.",
        tier_unlocks=("access to black-market financiers",),
    )


class TestCapstoneViewLifecycle:
    """AC9 — view lifecycle: enter creates UI, exit tears it down, button dismisses."""

    def test_on_enter_creates_continue_button(self) -> None:
        ui = _setup_pygame()
        acknowledged: list[bool] = []
        view = CapstoneView(
            ui, _make_capstone(), _make_lens(), on_acknowledge=lambda: acknowledged.append(True)
        )
        assert view._continue_button is None

        view.on_enter()

        assert view._continue_button is not None
        view.on_exit()

    def test_on_exit_destroys_continue_button(self) -> None:
        ui = _setup_pygame()
        view = CapstoneView(ui, _make_capstone(), _make_lens(), on_acknowledge=lambda: None)
        view.on_enter()
        assert view._continue_button is not None

        view.on_exit()

        assert view._continue_button is None

    def test_handle_event_button_press_sets_dismissed(self) -> None:
        ui = _setup_pygame()
        acknowledged: list[bool] = []
        view = CapstoneView(
            ui, _make_capstone(), _make_lens(), on_acknowledge=lambda: acknowledged.append(True)
        )
        view.on_enter()

        assert not view.dismissed

        # Simulate pygame_gui button-pressed event
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": view._continue_button},
        )
        view.handle_event(event)

        assert view.dismissed is True
        assert acknowledged == [True], "on_acknowledge callback must have been called"

        view.on_exit()

    def test_handle_event_non_button_event_does_not_dismiss(self) -> None:
        ui = _setup_pygame()
        view = CapstoneView(ui, _make_capstone(), _make_lens(), on_acknowledge=lambda: None)
        view.on_enter()

        # A random non-button event should not dismiss
        other_event = pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": "", "scancode": 0}
        )
        view.handle_event(other_event)

        assert not view.dismissed

        view.on_exit()

    def test_get_next_state_returns_none(self) -> None:
        ui = _setup_pygame()
        view = CapstoneView(ui, _make_capstone(), _make_lens(), on_acknowledge=lambda: None)
        assert view.get_next_state() is None

    def test_is_dismissed_initially_false(self) -> None:
        ui = _setup_pygame()
        view = CapstoneView(ui, _make_capstone(), _make_lens(), on_acknowledge=lambda: None)
        assert view.is_dismissed() is False


class TestCapstoneNarrationVoice:
    """AC12 — placeholder narration template passes Writing Bible compliance."""

    def test_no_em_dashes_in_template(self) -> None:
        for em_dash in ("—", "–", "―"):
            assert em_dash not in _TEMPLATE, (
                f"Template contains em-dash character U+{ord(em_dash):04X}: {_TEMPLATE!r}"
            )

    def test_no_banned_phrase_testament_to(self) -> None:
        assert "a testament to" not in _TEMPLATE.lower(), (
            f"Template contains banned phrase 'a testament to': {_TEMPLATE!r}"
        )

    def test_no_banned_phrase_couldnt_help_but(self) -> None:
        assert "couldn't help but" not in _TEMPLATE.lower(), (
            f"Template contains banned phrase 'couldn't help but': {_TEMPLATE!r}"
        )

    def test_no_parallel_negation_construction(self) -> None:
        # "no X, no Y" construction is a GenAI tell per Writing Bible.
        import re

        pattern = re.compile(r"\bno\b[^,]+,\s*no\b", re.IGNORECASE)
        assert not pattern.search(_TEMPLATE), (
            f"Template contains 'no X, no Y' construction: {_TEMPLATE!r}"
        )

    def test_no_banned_npc_names(self) -> None:
        banned = {"Yara", "Elara", "Kael", "Mara", "Lydia", "Clive", "Magnus", "Ambrose"}
        for name in banned:
            assert name not in _TEMPLATE, (
                f"Template contains banned NPC name {name!r}: {_TEMPLATE!r}"
            )

    def test_template_mentions_lens_and_core_fantasy_placeholders(self) -> None:
        assert "{lens_name}" in _TEMPLATE, "Template must contain {lens_name} placeholder"
        assert "{core_fantasy}" in _TEMPLATE, "Template must contain {core_fantasy} placeholder"
