"""Smoke tests for :class:`spacegame.views.dilemma_resolution_view.DilemmaResolutionView`.

Sprint A2-8, Task 6. Verifies:

- Headless construction (no crash on init / on_enter / on_exit / render).
- 2-pole vs 3-pole button counts (D3 rule: below-threshold third pole
  gets a button iff ``len(poles) > collision_requires``).
- ``on_resolve(lens_id)`` callback receives the id of the pressed button.
- View file contains no ``LensInvestment`` / ``lens_investment`` tokens
  (compliance guard; the snapshot dict pattern keeps the view green).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.dilemma import Dilemma, DilemmaOutcome
from spacegame.views.dilemma_resolution_view import DilemmaResolutionView


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield


def _outcome(lens_id: str) -> DilemmaOutcome:
    return DilemmaOutcome(
        winning_lens_id=lens_id,
        closes=[lens_id],
        tier_unlocks=[],
        outcome_flag=f"outcome_{lens_id}",
        narration_summary=f"Chose {lens_id}.",
    )


def _pair_dilemma() -> Dilemma:
    return Dilemma(
        id="d_pair",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["one"],
        outcomes=[_outcome("wealth"), _outcome("community")],
    )


def _triangle_dilemma() -> Dilemma:
    return Dilemma(
        id="d_triangle",
        poles=["order", "freedom", "faith"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["one"],
        outcomes=[_outcome("order"), _outcome("freedom"), _outcome("faith")],
    )


class TestDilemmaResolutionViewSmoke:
    def test_construct_and_enter_exit_pair(self) -> None:
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        dilemma = _pair_dilemma()

        view = DilemmaResolutionView(
            manager,
            dilemma,
            on_resolve=lambda _: None,
            current_investment={"wealth": 90, "community": 90},
        )
        view.on_enter()
        assert view.active is True
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.update(0.016)
        view.on_exit()
        assert view.active is False

    def test_pair_dilemma_has_two_buttons(self) -> None:
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        dilemma = _pair_dilemma()

        view = DilemmaResolutionView(
            manager,
            dilemma,
            on_resolve=lambda _: None,
            current_investment={"wealth": 90, "community": 90},
        )
        view.on_enter()
        assert len(view.pole_buttons) == 2
        assert set(view.pole_buttons.keys()) == {"wealth", "community"}
        view.on_exit()

    def test_triangle_below_threshold_pole_gets_button(self) -> None:
        """D3 rule: three-pole dilemma with two poles hot, one at 0,
        the third pole still gets a button because ``len(poles) >
        collision_requires``.
        """
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        dilemma = _triangle_dilemma()

        view = DilemmaResolutionView(
            manager,
            dilemma,
            on_resolve=lambda _: None,
            current_investment={"order": 90, "freedom": 90, "faith": 0},
        )
        view.on_enter()
        assert len(view.pole_buttons) == 3
        assert set(view.pole_buttons.keys()) == {"order", "freedom", "faith"}
        view.on_exit()


class TestDilemmaResolutionViewCallback:
    def test_button_press_invokes_callback_with_correct_lens(self) -> None:
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        dilemma = _pair_dilemma()
        captured: dict[str, Optional[str]] = {"lens_id": None}

        def _resolve(lens_id: str) -> None:
            captured["lens_id"] = lens_id

        view = DilemmaResolutionView(
            manager,
            dilemma,
            on_resolve=_resolve,
            current_investment={"wealth": 90, "community": 90},
        )
        view.on_enter()

        community_btn = view.pole_buttons["community"]
        press_event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED, {"ui_element": community_btn}
        )
        view.handle_event(press_event)

        assert captured["lens_id"] == "community"
        assert view.dismissed is True
        view.on_exit()

    def test_dismiss_flag_defaults_to_false_before_press(self) -> None:
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        dilemma = _pair_dilemma()

        view = DilemmaResolutionView(
            manager,
            dilemma,
            on_resolve=lambda _: None,
            current_investment={"wealth": 90, "community": 90},
        )
        view.on_enter()
        assert view.dismissed is False
        view.on_exit()


class TestDilemmaResolutionViewComplianceScan:
    """Structural guard: the view file itself must never touch
    ``LensInvestment`` / ``lens_investment`` — the compliance scan under
    ``tests/test_compliance/test_lens_investment_never_rendered.py``
    already enforces this across ``spacegame/views/``; this class is a
    view-scoped sanity check the review can eyeball independently.
    """

    def test_view_source_has_no_forbidden_tokens(self) -> None:
        view_path = (
            Path(__file__).resolve().parent.parent.parent
            / "spacegame"
            / "views"
            / "dilemma_resolution_view.py"
        )
        source = view_path.read_text(encoding="utf-8")
        for token in ("LensInvestment", "lens_investment"):
            assert token not in source, (
                f"DilemmaResolutionView must not reference '{token}' — the "
                f"snapshot dict pattern keeps this compliance scan green."
            )
