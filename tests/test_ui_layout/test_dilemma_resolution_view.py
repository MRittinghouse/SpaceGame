"""Smoke tests for DilemmaResolutionView (A2-8).

Covers:
- Construction with 2-pole and 3-pole dilemmas
- on_enter / on_exit lifecycle and UI cleanup
- One button per eligible pole for a 2-pole collision
- Three buttons for a 3-pole D3 collision including one below-threshold
  pole (the D3 rule: ``len(poles) > collision_requires`` opens the
  below-threshold pole as an escape valve)
- Button press invokes ``on_resolve`` with the selected lens id
- Compliance: the view file never mentions ``LensInvestment`` or
  ``lens_investment`` (the compliance scanner enforces this globally,
  but this test catches accidental drift early)
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.dilemma import Dilemma, DilemmaOutcome
from spacegame.views.dilemma_resolution_view import DilemmaResolutionView


def _outcome(winning_lens: str) -> DilemmaOutcome:
    return DilemmaOutcome(
        winning_lens_id=winning_lens,
        closes=[winning_lens],
        tier_unlocks=[],
        outcome_flag=f"outcome_{winning_lens}",
        narration_summary=f"Test summary for {winning_lens}.",
    )


def _pair_dilemma() -> Dilemma:
    return Dilemma(
        id="d_test_pair",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["Test telegraph."],
        outcomes=[_outcome("wealth"), _outcome("community")],
    )


def _triangle_dilemma() -> Dilemma:
    return Dilemma(
        id="d_test_triangle",
        poles=["order", "freedom", "faith"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["Test triangle."],
        outcomes=[_outcome("order"), _outcome("freedom"), _outcome("faith")],
    )


def _make_manager() -> pygame_gui.UIManager:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


class TestConstruction:
    def test_construct_pair_dilemma(self) -> None:
        manager = _make_manager()
        view = DilemmaResolutionView(
            ui_manager=manager,
            dilemma=_pair_dilemma(),
            on_resolve=lambda _lens_id: None,
            current_investment={"wealth": 85, "community": 85},
        )
        assert view is not None
        assert view.dismissed is False

    def test_on_enter_sets_active(self) -> None:
        manager = _make_manager()
        view = DilemmaResolutionView(
            ui_manager=manager,
            dilemma=_pair_dilemma(),
            on_resolve=lambda _lens_id: None,
            current_investment={"wealth": 85, "community": 85},
        )
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_destroys_ui(self) -> None:
        manager = _make_manager()
        view = DilemmaResolutionView(
            ui_manager=manager,
            dilemma=_pair_dilemma(),
            on_resolve=lambda _lens_id: None,
            current_investment={"wealth": 85, "community": 85},
        )
        view.on_enter()
        assert len(view.pole_buttons) == 2
        view.on_exit()
        assert view.pole_buttons == {}
        assert not view.active


class TestPoleButtons:
    """AC6 (view side): the D3 case opens the third below-threshold pole."""

    def test_pair_dilemma_has_two_buttons(self) -> None:
        manager = _make_manager()
        view = DilemmaResolutionView(
            ui_manager=manager,
            dilemma=_pair_dilemma(),
            on_resolve=lambda _lens_id: None,
            current_investment={"wealth": 85, "community": 85},
        )
        view.on_enter()
        try:
            assert set(view.pole_buttons.keys()) == {"wealth", "community"}
        finally:
            view.on_exit()

    def test_triangle_with_two_above_threshold_has_three_buttons(self) -> None:
        """D3 rule: ``len(poles) > collision_requires`` (3 > 2), so the
        below-threshold pole (faith) MUST appear as an eligible option."""
        manager = _make_manager()
        view = DilemmaResolutionView(
            ui_manager=manager,
            dilemma=_triangle_dilemma(),
            on_resolve=lambda _lens_id: None,
            current_investment={"order": 90, "freedom": 90, "faith": 0},
        )
        view.on_enter()
        try:
            assert set(view.pole_buttons.keys()) == {"order", "freedom", "faith"}
        finally:
            view.on_exit()


class TestOnResolveCallback:
    def test_press_button_invokes_callback_with_lens_id(self) -> None:
        manager = _make_manager()
        captured: list[str] = []

        view = DilemmaResolutionView(
            ui_manager=manager,
            dilemma=_pair_dilemma(),
            on_resolve=lambda lens_id: captured.append(lens_id),
            current_investment={"wealth": 85, "community": 85},
        )
        view.on_enter()
        try:
            # Simulate a pygame_gui button press event on the wealth button.
            evt = pygame.event.Event(
                pygame_gui.UI_BUTTON_PRESSED,
                {"ui_element": view.pole_buttons["wealth"]},
            )
            view.handle_event(evt)
            assert captured == ["wealth"]
            assert view.dismissed is True
        finally:
            view.on_exit()


class TestNoLensInvestmentToken:
    """Compliance guardrail — the view file must not mention the
    forbidden tokens. The global scanner in
    tests/test_compliance/test_lens_investment_never_rendered.py already
    enforces this, but this per-file check gives faster feedback when
    the view is being edited."""

    def test_view_module_has_no_lens_investment_token(self) -> None:
        from pathlib import Path

        here = Path(__file__).resolve().parent.parent.parent
        view_file = here / "spacegame" / "views" / "dilemma_resolution_view.py"
        text = view_file.read_text(encoding="utf-8")
        for token in ("LensInvestment", "lens_investment"):
            assert token not in text, (
                f"DilemmaResolutionView must not mention {token!r}. "
                "Pass a dict[str, int] snapshot in through current_investment "
                "so the compliance scan stays green."
            )
