"""A2-20: CapstoneView lifecycle and narration voice tests.

Covers AC9 (lifecycle: on_enter creates button, on_exit tears down, handle_event
sets dismissed, get_next_state returns None) and AC12 (voice: no em-dashes,
no banned phrases, no parallel-negation in the placeholder template).
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.capstone import Capstone
from spacegame.models.lens import Lens
from spacegame.views.capstone_view import _TEMPLATE, CapstoneView


def _ensure_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _fresh_ui() -> pygame_gui.UIManager:
    _ensure_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _wealth_capstone() -> Capstone:
    return Capstone(
        capstone_id="wealth_capstone",
        lens_id="wealth",
        capstone_threshold=95,
        cutscene_ref=None,
    )


def _wealth_lens() -> Lens:
    return Lens(
        lens_id="wealth",
        name="Wealth",
        core_fantasy="Build an interstellar commercial empire from a position of nothing.",
        question="After growing up with nothing, how much is finally enough?",
        sees="A supply gap.",
        wants="Margin.",
        trades="Time.",
        investment_from=("sold_cargo",),
        minigame_shape="Optimisation.",
        voice="Optimized.",
        tier_unlocks=("access to financiers",),
    )


class TestCapstoneViewLifecycle:
    """AC9: on_enter creates button; on_exit tears down; handle_event sets dismissed;
    get_next_state returns None."""

    def test_on_enter_creates_continue_button(self) -> None:
        ui = _fresh_ui()
        acknowledged: list[bool] = []
        view = CapstoneView(
            ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: acknowledged.append(True)
        )
        view.on_enter()
        assert view._continue_button is not None, "on_enter must create the Continue button"
        view.on_exit()

    def test_on_exit_tears_down_button(self) -> None:
        ui = _fresh_ui()
        view = CapstoneView(ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: None)
        view.on_enter()
        assert view._continue_button is not None
        view.on_exit()
        assert view._continue_button is None, "on_exit must kill and null the Continue button"

    def test_handle_event_sets_dismissed_and_calls_acknowledge(self) -> None:
        ui = _fresh_ui()
        acknowledged: list[bool] = []
        view = CapstoneView(
            ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: acknowledged.append(True)
        )
        view.on_enter()

        assert not view.dismissed, "dismissed must start False"
        button = view._continue_button
        assert button is not None

        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": button, "ui_object_id": str(button.object_ids)},
        )
        view.handle_event(event)

        assert view.dismissed, "dismissed must be True after button press"
        assert acknowledged == [True], "on_acknowledge must be called exactly once"
        view.on_exit()

    def test_get_next_state_returns_none(self) -> None:
        ui = _fresh_ui()
        view = CapstoneView(ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: None)
        view.on_enter()
        assert view.get_next_state() is None, "Modal views must return None from get_next_state"
        view.on_exit()

    def test_is_dismissed_reflects_dismissed_flag(self) -> None:
        ui = _fresh_ui()
        view = CapstoneView(ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: None)
        view.on_enter()
        assert not view.is_dismissed()
        view.dismissed = True
        assert view.is_dismissed()
        view.on_exit()

    def test_unrelated_button_press_does_not_dismiss(self) -> None:
        ui = _fresh_ui()
        other_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, 50, 30),
            text="OTHER",
            manager=ui,
        )
        view = CapstoneView(ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: None)
        view.on_enter()

        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": other_button, "ui_object_id": str(other_button.object_ids)},
        )
        view.handle_event(event)
        assert not view.dismissed, "An unrelated button press must not dismiss the view"
        view.on_exit()
        other_button.kill()


class TestCapstoneNarrationVoice:
    """AC12: placeholder narration passes the Writing Bible smoke checks."""

    def test_no_em_dashes(self) -> None:
        em_dashes = ("—", "–", "―")
        for dash in em_dashes:
            assert dash not in _TEMPLATE, (
                f"_TEMPLATE contains em-dash {dash!r} -- banned by Writing Bible"
            )

    def test_no_banned_phrases(self) -> None:
        banned = ["a testament to", "couldn't help but"]
        for phrase in banned:
            assert phrase.lower() not in _TEMPLATE.lower(), (
                f"_TEMPLATE contains banned phrase {phrase!r}"
            )

    def test_no_parallel_negation(self) -> None:
        import re

        # Pattern: "no X, no Y" constructions
        pattern = re.compile(r"\bno\b[^,.!?]{1,40},\s*no\b", re.IGNORECASE)
        assert not pattern.search(_TEMPLATE), (
            "Writing Bible forbids 'no X, no Y' parallel-negation in _TEMPLATE"
        )

    def test_no_banned_npc_names(self) -> None:
        banned_names = ["Yara", "Elara", "Kael", "Mara", "Lydia", "Clive", "Magnus", "Ambrose"]
        for name in banned_names:
            assert name not in _TEMPLATE, f"_TEMPLATE contains banned NPC name {name!r}"

    def test_template_contains_expected_placeholders(self) -> None:
        assert "{lens_name}" in _TEMPLATE, "_TEMPLATE must contain {lens_name} placeholder"
        assert "{core_fantasy_lowercased_no_trailing_period}" in _TEMPLATE, (
            "_TEMPLATE must contain {core_fantasy_lowercased_no_trailing_period} placeholder"
        )

    def test_narration_renders_correctly_for_wealth_lens(self) -> None:
        ui = _fresh_ui()
        view = CapstoneView(ui, _wealth_capstone(), _wealth_lens(), on_acknowledge=lambda: None)
        narration = view._narration()
        assert "Wealth" in narration, "Lens name must appear in rendered narration"
        assert "build an interstellar" in narration.lower(), (
            "core_fantasy (lowercased) must appear in narration"
        )
        assert narration.endswith("Play continues."), "Template must end with 'Play continues.'"
