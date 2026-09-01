"""End-to-end scenarios for the A2-20 capstone engine.

Covers AC1-AC4, AC7, AC8, AC10 by driving ``_after_player_action`` on a
minimally-mocked :class:`~spacegame.engine.game.Game` against real capstones
loaded from the data layer. The engine reads investment via the model-layer
coordinator :func:`~spacegame.models.capstone.check_capstones`, so tests drive
investment on the real ``player.lens_investment`` store.

The ``_mock_game`` helper mirrors the pattern used by the dilemma scenario
tests — ``__init__`` is patched out and the game is configured by hand with
real model instances.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock, patch

import pygame
import pygame_gui

from spacegame.config import GameState
from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import DilemmaRuntimeState
from spacegame.models.lens_investment import LensInvestment


def _real_ui_manager() -> pygame_gui.UIManager:
    from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH

    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _mock_game(*, with_ui: bool = False):
    """Construct a Game with just enough state for _after_player_action.

    Sets ``capstones_reached`` as a real ``set`` so
    ``_tick_capstone_engine``'s partial-Game guard passes.
    """
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()

    game._player = MagicMock()
    game.player.lens_investment = LensInvestment()
    game.player.dilemma_state = DilemmaRuntimeState()
    game.player.capstones_reached = set()
    game.player.dialogue_flags = {}
    game.crew_roster = None
    game.ambient_dialogue = None
    game._mission_notifications = []
    game.ui_manager = _real_ui_manager() if with_ui else None
    game.state_manager = MagicMock(current_state=None)
    game.dilemma_resolution_view = None
    game._pending_dilemma = None
    game.capstone_view = None
    game._pending_capstone = None
    return game


@property
def _player_prop(self):
    return self._player


class TestCapstoneThresholdFires:
    """AC1 — threshold fires; one point short does not."""

    def test_below_threshold_does_not_push_capstone(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        # wealth_capstone threshold is 95
        game.player.lens_investment.add_investment("wealth", 94, source="test")

        game._after_player_action("test")

        game.state_manager.push_state.assert_not_called()
        assert game.capstone_view is None

    def test_at_threshold_pushes_capstone(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        game._after_player_action("test")

        game.state_manager.push_state.assert_called_once_with(GameState.CAPSTONE)
        assert game.capstone_view is not None
        assert game._pending_capstone is not None
        assert game._pending_capstone.capstone_id == "wealth_capstone"


class TestCapstoneSessionContinues:
    """AC2 — session continues after acknowledge (spec Success Criterion 8)."""

    def test_acknowledge_writes_reached_and_flag(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire the capstone
        game._after_player_action("test")
        assert game._pending_capstone is not None

        # Acknowledge
        game._on_capstone_acknowledge()
        assert "wealth_capstone" in game.player.capstones_reached
        assert game.player.dialogue_flags.get("wealth_capstone_reached") is True

    def test_handle_acknowledge_polls_dismissed_and_pops(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire the capstone
        game._after_player_action("test")
        assert game.capstone_view is not None
        game._on_capstone_acknowledge()

        # Simulate state manager reflecting the pushed modal
        game.state_manager.current_state = GameState.CAPSTONE
        game.capstone_view.dismissed = True

        game._handle_capstone_acknowledge()

        game.state_manager.pop_state.assert_called_once()
        assert game.capstone_view is None
        assert game._pending_capstone is None

    def test_subsequent_action_completes_without_error(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire and acknowledge
        game._after_player_action("test")
        game._on_capstone_acknowledge()
        game.state_manager.current_state = GameState.CAPSTONE
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()

        # Reset mock state
        game.state_manager.current_state = None

        # Subsequent action should complete without error
        game._after_player_action("trade_profit_large")

        # Only the first push_state should have been called (for wealth_capstone).
        # After acknowledge, wealth_capstone is in capstones_reached so it won't re-fire.
        assert game.player.capstones_reached == {"wealth_capstone"}


class TestClosedLensSuppressesCapstone:
    """AC3 — a closed lens can never fire its capstone."""

    def test_closed_lens_at_100_does_not_push_capstone(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.dilemma_state.closed_lenses.add("wealth")
        game.player.lens_investment.add_investment("wealth", 100, source="test")

        game._after_player_action("test")

        game.state_manager.push_state.assert_not_called()
        assert game.player.capstones_reached == set()


class TestCapstoneDoesNotDoubleFire:
    """AC4 — same capstone does not fire twice."""

    def test_second_tick_suppressed_after_acknowledge(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # First fire + acknowledge
        game._after_player_action("test")
        game._on_capstone_acknowledge()
        game.state_manager.current_state = GameState.CAPSTONE
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()

        # Reset mock state and do second tick
        game.state_manager.current_state = None
        game.state_manager.push_state.reset_mock()

        game._after_player_action("test")

        game.state_manager.push_state.assert_not_called()


class TestCapstoneAndDilemmaModalStacking:
    """AC7 — capstone modal cannot stack a dilemma modal beneath it."""

    def test_capstone_state_suppresses_after_player_action(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # First fire
        game._after_player_action("test")
        game.state_manager.push_state.assert_called_once_with(GameState.CAPSTONE)

        # Simulate capstone modal active
        game.state_manager.current_state = GameState.CAPSTONE
        game.state_manager.push_state.reset_mock()

        # Second action while modal is active — suppressed
        game._after_player_action("test_again")

        game.state_manager.push_state.assert_not_called()

    def test_dilemma_state_suppresses_capstone_tick(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Simulate dilemma modal already active
        game.state_manager.current_state = GameState.DILEMMA_RESOLUTION

        game._after_player_action("test")

        # Neither capstone nor dilemma tick should push while DILEMMA_RESOLUTION is active
        game.state_manager.push_state.assert_not_called()


class TestMultipleEligibleCapstonesFireOneAtATime:
    """AC8 — multiple simultaneously-eligible capstones fire one at a time."""

    def test_first_eligible_fires_first(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)

        # Get the first two lens IDs from the capstone registry (insertion order)
        capstone_ids = list(dl.capstones.keys())
        first_cid = capstone_ids[0]
        second_cid = capstone_ids[1]
        first_capstone = dl.capstones[first_cid]
        second_capstone = dl.capstones[second_cid]

        # Both at threshold
        game.player.lens_investment.add_investment(first_capstone.lens_id, 95, source="test")
        game.player.lens_investment.add_investment(second_capstone.lens_id, 95, source="test")

        # First tick — only the first eligible fires
        game._after_player_action("test")
        game.state_manager.push_state.assert_called_once_with(GameState.CAPSTONE)
        assert game._pending_capstone.capstone_id == first_cid

    def test_second_fires_after_first_acknowledged(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)

        capstone_ids = list(dl.capstones.keys())
        first_cid = capstone_ids[0]
        second_cid = capstone_ids[1]
        first_capstone = dl.capstones[first_cid]
        second_capstone = dl.capstones[second_cid]

        game.player.lens_investment.add_investment(first_capstone.lens_id, 95, source="test")
        game.player.lens_investment.add_investment(second_capstone.lens_id, 95, source="test")

        # First tick
        game._after_player_action("test")
        game._on_capstone_acknowledge()
        game.state_manager.current_state = GameState.CAPSTONE
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()

        # Reset and second tick
        game.state_manager.current_state = None
        game.state_manager.push_state.reset_mock()

        game._after_player_action("test")
        game.state_manager.push_state.assert_called_once_with(GameState.CAPSTONE)
        assert game._pending_capstone.capstone_id == second_cid

        # Both should be in capstones_reached after full acknowledge cycle
        game._on_capstone_acknowledge()
        assert first_cid in game.player.capstones_reached
        assert second_cid in game.player.capstones_reached


class TestFiringDefersWritesToAcknowledge:
    """AC10 — writes are deferred to acknowledge, not fire."""

    def test_capstones_reached_empty_immediately_after_push(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire the capstone (push state)
        game._after_player_action("test")
        assert game._pending_capstone is not None

        # Before acknowledge: capstones_reached must still be empty
        assert game.player.capstones_reached == set()
        assert game.player.dialogue_flags.get("wealth_capstone_reached") is None

    def test_writes_happen_on_acknowledge_not_fire(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        game = _mock_game(with_ui=True)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire
        game._after_player_action("test")
        assert game.player.capstones_reached == set()

        # Acknowledge
        game._on_capstone_acknowledge()
        assert "wealth_capstone" in game.player.capstones_reached
        assert game.player.dialogue_flags.get("wealth_capstone_reached") is True
