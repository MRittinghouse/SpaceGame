"""A2-10 AC7: DilemmaResolutionView pop-state returns to prior state.

Proves that StateManager.pop_state() restores the state that was active
before the resolution modal was pushed. Uses a minimal headless pygame
setup with a MockBaseView for the TRADING slot.

The engine's _handle_dilemma_resolution calls pop_state() after the view
sets dismissed=True; this test verifies that pattern returns control to
the original state, not a hardcoded default.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pygame_gui

from spacegame.config import GameState
from spacegame.engine.state_manager import StateManager
from spacegame.models.dilemma import Dilemma, DilemmaOutcome
from spacegame.views.base_view import BaseView
from spacegame.views.dilemma_resolution_view import DilemmaResolutionView
from tests.test_scenarios._view_harness import ensure_pygame, fresh_ui_manager


class _MockView(BaseView):
    """Minimal BaseView stub for the TRADING slot."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = False
        self.exited = False

    def on_enter(self) -> None:
        super().on_enter()
        self.entered = True

    def on_exit(self) -> None:
        self.exited = True
        super().on_exit()

    def update(self, dt: float) -> None:
        pass

    def render(self, screen: pygame.Surface) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass


def _minimal_dilemma() -> Dilemma:
    return Dilemma(
        id="d_pop_test",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=10,  # Low so both buttons are eligible
        telegraph_npc_id="priya_osei",
        telegraph_lines=["test_line"],
        outcomes=[
            DilemmaOutcome(
                winning_lens_id="wealth",
                closes=["community"],
                tier_unlocks=[],
                outcome_flag="outcome_pop_wealth",
                narration_summary="Pop test wealth.",
            ),
            DilemmaOutcome(
                winning_lens_id="community",
                closes=["wealth"],
                tier_unlocks=[],
                outcome_flag="outcome_pop_community",
                narration_summary="Pop test community.",
            ),
        ],
    )


class TestDilemmaViewPopState:
    """AC7: modal dismissal returns to the state that was active before the push."""

    def test_pop_returns_to_trading(self) -> None:
        """Pushing DILEMMA_RESOLUTION over TRADING, then popping, gives TRADING."""
        ensure_pygame()
        ui_manager = fresh_ui_manager()

        state_manager = StateManager()
        mock_trading = _MockView()
        state_manager.register_state(GameState.TRADING, mock_trading)
        state_manager.change_state(GameState.TRADING)

        assert state_manager.current_state == GameState.TRADING

        resolved_lens: list[str] = []
        dilemma = _minimal_dilemma()
        resolution_view = DilemmaResolutionView(
            ui_manager,
            dilemma,
            on_resolve=lambda lens_id: resolved_lens.append(lens_id),
            current_investment={"wealth": 90, "community": 90},
        )
        state_manager.register_state(GameState.DILEMMA_RESOLUTION, resolution_view)
        state_manager.push_state(GameState.DILEMMA_RESOLUTION)

        assert state_manager.current_state == GameState.DILEMMA_RESOLUTION

        # Simulate button press for the first eligible pole.
        first_pole = dilemma.poles[0]
        button = resolution_view.pole_buttons.get(first_pole)
        assert button is not None, f"Expected button for pole '{first_pole}'"
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": button, "ui_object_id": str(button.object_ids)},
        )
        resolution_view.handle_event(event)

        assert resolution_view.is_dismissed(), "View must be dismissed after button press"

        # Simulate _handle_dilemma_resolution: pop state when dismissed.
        if resolution_view.is_dismissed():
            state_manager.pop_state()

        assert state_manager.current_state == GameState.TRADING, (
            f"Expected TRADING after pop, got {state_manager.current_state}"
        )

    def test_pop_returns_to_any_prior_state(self) -> None:
        """Pushing over GALAXY_MAP then popping returns to GALAXY_MAP, not a hardcoded default."""
        ensure_pygame()
        ui_manager = fresh_ui_manager()

        state_manager = StateManager()
        mock_galaxy = _MockView()
        state_manager.register_state(GameState.GALAXY_MAP, mock_galaxy)
        state_manager.change_state(GameState.GALAXY_MAP)

        dilemma = _minimal_dilemma()
        resolution_view = DilemmaResolutionView(
            ui_manager,
            dilemma,
            on_resolve=lambda _: None,
            current_investment={"wealth": 90, "community": 90},
        )
        state_manager.register_state(GameState.DILEMMA_RESOLUTION, resolution_view)
        state_manager.push_state(GameState.DILEMMA_RESOLUTION)

        first_pole = dilemma.poles[0]
        button = resolution_view.pole_buttons[first_pole]
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": button, "ui_object_id": str(button.object_ids)},
        )
        resolution_view.handle_event(event)

        if resolution_view.is_dismissed():
            state_manager.pop_state()

        assert state_manager.current_state == GameState.GALAXY_MAP
