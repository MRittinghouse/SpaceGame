"""A2-20: Capstone engine scenario tests.

Covers AC1-AC4 (threshold, session continues, closed-lens guard, no double-fire),
AC7 (no modal stacking with dilemma), AC8 (multiple eligible capstones fire
one at a time in insertion order), and AC10 (writes deferred to acknowledge).

The harness mirrors test_scenario_dilemma_thresholds.py: a partial Game with
patched __init__, a MagicMock state manager (for pure guard tests) or a real
StateManager + real UIManager (for push behavior tests).
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock, patch

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.data_loader import get_data_loader
from spacegame.engine.state_manager import StateManager
from spacegame.models.capstone import Capstone
from spacegame.models.dilemma import Dilemma, DilemmaOutcome, DilemmaRuntimeState
from spacegame.models.lens_investment import LensInvestment
from spacegame.views.base_view import BaseView

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _ensure_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _real_ui_manager() -> pygame_gui.UIManager:
    _ensure_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _mock_game():
    """Minimal Game for _after_player_action with a MagicMock state manager.

    Tests that only need to assert whether push_state was called use this.
    Tests that need real push behavior use _real_game_with_state_manager().
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
    game.ui_manager = None
    game.state_manager = MagicMock(current_state=None)
    game.dilemma_resolution_view = None
    game._pending_dilemma = None
    game.capstone_view = None
    game._pending_capstone = None
    return game


def _real_game(prior_state: GameState = GameState.TRADING) -> tuple:
    """Build a Game with real StateManager and real UIManager.

    Returns (game, state_manager, ui_manager). The prior_state is pushed
    as the starting state so pop_state() can return to it.
    """
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()

    ui = _real_ui_manager()
    sm = StateManager()

    class _MockView(BaseView):
        def update(self, dt: float) -> None:
            pass

        def render(self, screen: pygame.Surface) -> None:
            pass

        def handle_event(self, event: pygame.event.Event) -> None:
            pass

    mock_view = _MockView()
    sm.register_state(prior_state, mock_view)
    sm.change_state(prior_state)

    game._player = MagicMock()
    game.player.lens_investment = LensInvestment()
    game.player.dilemma_state = DilemmaRuntimeState()
    game.player.capstones_reached = set()
    game.player.dialogue_flags = {}
    game.crew_roster = None
    game.ambient_dialogue = None
    game._mission_notifications = []
    game.ui_manager = ui
    game.state_manager = sm
    game.dilemma_resolution_view = None
    game._pending_dilemma = None
    game.capstone_view = None
    game._pending_capstone = None
    return game, sm, ui


@pytest.fixture(autouse=True)
def capstone_registry():
    """Inject the real capstone registry for the duration of each test.

    Saves and restores so tests don't bleed into each other via the singleton.
    """
    dl = get_data_loader()
    dl.load_all()
    saved_capstones = dict(dl.capstones)
    saved_lenses = dict(dl.lenses)
    try:
        yield dl
    finally:
        dl.capstones = saved_capstones
        dl.lenses = saved_lenses


def _minimal_capstone(lens_id: str = "wealth") -> Capstone:
    return Capstone(
        capstone_id=f"{lens_id}_capstone",
        lens_id=lens_id,
        capstone_threshold=95,
        cutscene_ref=None,
    )


# ---------------------------------------------------------------------------
# AC1: Threshold fires; one point short does not
# ---------------------------------------------------------------------------


class TestCapstoneThresholdFires:
    """AC1: investment at 94 does not push; at 95 pushes CAPSTONE."""

    def test_one_below_threshold_does_not_push(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game = _mock_game()
        game.player.lens_investment.add_investment("wealth", 94, source="test")

        game._after_player_action("test")

        assert game.state_manager.push_state.call_count == 0, (
            "94 investment must not fire the capstone (threshold is 95)"
        )
        assert game.capstone_view is None

    def test_at_threshold_pushes_capstone_state(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game, sm, _ = _real_game()
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        game._after_player_action("test")

        assert sm.current_state == GameState.CAPSTONE, (
            f"Expected CAPSTONE state, got {sm.current_state}"
        )
        assert game.capstone_view is not None
        assert game._pending_capstone is capstone

    def test_above_threshold_also_pushes(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game, sm, _ = _real_game()
        game.player.lens_investment.add_investment("wealth", 100, source="test")

        game._after_player_action("test")

        assert sm.current_state == GameState.CAPSTONE


# ---------------------------------------------------------------------------
# AC2: Session continues after acknowledge
# ---------------------------------------------------------------------------


class TestCapstoneSessionContinues:
    """AC2: after the acknowledge path, pop returns to prior state;
    a subsequent action runs without error; capstones_reached is populated."""

    def test_pop_returns_to_prior_state_and_action_succeeds(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game, sm, _ = _real_game(prior_state=GameState.TRADING)
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire the capstone
        game._after_player_action("test")
        assert sm.current_state == GameState.CAPSTONE

        # Simulate the acknowledge callback (engine side-effect)
        game._on_capstone_acknowledge()

        # Simulate _handle_capstone_acknowledge: check dismissed and pop
        assert game.capstone_view is not None
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()

        # State is restored to TRADING
        assert sm.current_state == GameState.TRADING, (
            f"Expected TRADING after pop, got {sm.current_state}"
        )
        assert game.capstone_view is None
        assert game._pending_capstone is None

        # A subsequent action must not crash
        game._after_player_action("trade_profit_large")

        # capstones_reached must contain the wealth capstone
        assert "wealth_capstone" in game.player.capstones_reached, (
            "capstones_reached must contain wealth_capstone after acknowledge"
        )
        # Dialogue flag must be set
        assert game.player.dialogue_flags.get("wealth_capstone_reached") is True


# ---------------------------------------------------------------------------
# AC3: Closed lens never fires its capstone
# ---------------------------------------------------------------------------


class TestClosedLensSuppressesCapstone:
    """AC3: if a lens is in closed_lenses, its capstone never fires."""

    def test_closed_lens_blocks_capstone(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game = _mock_game()
        game.player.dilemma_state.closed_lenses.add("wealth")
        game.player.lens_investment.add_investment("wealth", 100, source="test")

        game._after_player_action("test")

        assert game.state_manager.push_state.call_count == 0, (
            "Closed lens must never fire its capstone"
        )
        assert game.player.capstones_reached == set()


# ---------------------------------------------------------------------------
# AC4: Same capstone does not fire twice
# ---------------------------------------------------------------------------


class TestCapstoneDoesNotDoubleFire:
    """AC4: once a capstone is in capstones_reached, it never fires again."""

    def test_capstone_does_not_fire_a_second_time(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game, sm, _ = _real_game()
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # First fire
        game._after_player_action("test")
        assert sm.current_state == GameState.CAPSTONE

        # Acknowledge
        game._on_capstone_acknowledge()
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()
        assert sm.current_state == GameState.TRADING

        # Second tick — capstones_reached blocks re-fire
        game._after_player_action("test")
        assert sm.current_state == GameState.TRADING, (
            "Second _after_player_action must not re-push CAPSTONE"
        )


# ---------------------------------------------------------------------------
# AC7: Dilemma modal and capstone modal do not stack
# ---------------------------------------------------------------------------


def _wealth_dilemma() -> Dilemma:
    return Dilemma(
        id="d_stacking_test",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=10,  # Low so it collides immediately
        telegraph_npc_id="priya_osei",
        telegraph_lines=["stacking test"],
        outcomes=[
            DilemmaOutcome(
                winning_lens_id="wealth",
                closes=["community"],
                tier_unlocks=[],
                outcome_flag="outcome_stack_wealth",
                narration_summary="Stack test wealth.",
            ),
            DilemmaOutcome(
                winning_lens_id="community",
                closes=["wealth"],
                tier_unlocks=[],
                outcome_flag="outcome_stack_community",
                narration_summary="Stack test community.",
            ),
        ],
    )


class TestCapstoneAndDilemmaModalStacking:
    """AC7: only one modal fires per tick; dilemma takes priority per Locked decision 6."""

    def test_dilemma_fires_first_when_both_eligible(self, capstone_registry) -> None:
        """When both a dilemma AND a capstone are eligible on the same tick,
        only the dilemma modal is pushed (dilemma tick runs first)."""
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        dilemma = _wealth_dilemma()
        capstone_registry.dilemmas = {dilemma.id: dilemma}

        game, sm, _ = _real_game()
        # Wealth is above capstone threshold AND above dilemma collision_threshold
        game.player.lens_investment.add_investment("wealth", 95, source="test")
        game.player.lens_investment.add_investment("community", 95, source="test")

        game._after_player_action("test")

        # Dilemma fires first (tick order: dilemma then capstone)
        assert sm.current_state == GameState.DILEMMA_RESOLUTION, (
            f"Expected DILEMMA_RESOLUTION to fire first, got {sm.current_state}"
        )
        assert game.capstone_view is None, "Capstone must not stack over dilemma"

    def test_capstone_fires_after_dilemma_resolved_non_closing(self, capstone_registry) -> None:
        """After a dilemma resolves with the capstone's lens still open,
        the next _after_player_action tick pushes the capstone."""
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        dilemma = _wealth_dilemma()
        capstone_registry.dilemmas = {dilemma.id: dilemma}

        game, sm, _ = _real_game()
        game.player.lens_investment.add_investment("wealth", 95, source="test")
        game.player.lens_investment.add_investment("community", 95, source="test")

        # First tick: dilemma fires
        game._after_player_action("test")
        assert sm.current_state == GameState.DILEMMA_RESOLUTION

        # Resolve dilemma with community winning (closes wealth)
        # Actually let's resolve with wealth winning (keeps wealth open)
        from spacegame.models.dilemma import resolve

        resolve(dilemma, "wealth", game.player)
        game.dilemma_resolution_view = MagicMock()
        game.dilemma_resolution_view.is_dismissed.return_value = True
        game._handle_dilemma_resolution()

        # wealth is still in open lenses (community was closed, not wealth)
        assert "wealth" not in game.player.dilemma_state.closed_lenses, (
            "wealth lens must remain open after winning-pole resolution"
        )

        # Next tick: capstone fires
        game._after_player_action("test")
        assert sm.current_state == GameState.CAPSTONE, (
            "Capstone must fire on the next tick after dilemma is resolved non-closing"
        )

    def test_capstone_does_not_fire_after_dilemma_closed_its_lens(self, capstone_registry) -> None:
        """If the dilemma resolution closes the capstone's lens, the capstone never fires."""
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        dilemma = _wealth_dilemma()
        capstone_registry.dilemmas = {dilemma.id: dilemma}

        game, sm, _ = _real_game()
        game.player.lens_investment.add_investment("wealth", 95, source="test")
        game.player.lens_investment.add_investment("community", 95, source="test")

        # First tick: dilemma fires
        game._after_player_action("test")
        assert sm.current_state == GameState.DILEMMA_RESOLUTION

        # Resolve with community winning (closes wealth)
        from spacegame.models.dilemma import resolve

        resolve(dilemma, "community", game.player)
        game.dilemma_resolution_view = MagicMock()
        game.dilemma_resolution_view.is_dismissed.return_value = True
        game._handle_dilemma_resolution()

        assert "wealth" in game.player.dilemma_state.closed_lenses, (
            "wealth must be closed after community wins"
        )

        # Next tick: capstone must NOT fire (wealth is closed)
        game._after_player_action("test")
        assert sm.current_state == GameState.TRADING, (
            "Capstone must not fire when its lens is closed"
        )
        assert game.player.capstones_reached == set()


# ---------------------------------------------------------------------------
# AC8: Multiple eligible capstones fire one at a time in insertion order
# ---------------------------------------------------------------------------


class TestMultipleEligibleCapstonesFireOneAtATime:
    """AC8: two eligible capstones fire sequentially, one per tick, in
    DataLoader insertion order (capstones.json ordering)."""

    def test_two_eligible_fire_in_insertion_order(self, capstone_registry) -> None:
        # Use the first two lens_ids from the real DataLoader insertion order
        dl = get_data_loader()
        dl.load_all()
        all_lens_ids = list(dl.lenses.keys())  # Insertion order
        first_lens = all_lens_ids[0]
        second_lens = all_lens_ids[1]

        first_capstone = _minimal_capstone(first_lens)
        second_capstone = _minimal_capstone(second_lens)
        capstone_registry.capstones = {
            first_capstone.capstone_id: first_capstone,
            second_capstone.capstone_id: second_capstone,
        }

        game, sm, _ = _real_game()
        # Set both lenses above threshold
        game.player.lens_investment.add_investment(first_lens, 95, source="test")
        game.player.lens_investment.add_investment(second_lens, 95, source="test")

        # First tick: first capstone fires
        game._after_player_action("test")
        assert sm.current_state == GameState.CAPSTONE
        assert game._pending_capstone is first_capstone, (
            f"Expected first capstone ({first_capstone.capstone_id}), got {game._pending_capstone}"
        )

        # Acknowledge first capstone
        game._on_capstone_acknowledge()
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()
        assert sm.current_state == GameState.TRADING

        # Second tick: second capstone fires
        game._after_player_action("test")
        assert sm.current_state == GameState.CAPSTONE
        assert game._pending_capstone is second_capstone, (
            f"Expected second capstone ({second_capstone.capstone_id}), "
            f"got {game._pending_capstone}"
        )

        # Acknowledge second capstone
        game._on_capstone_acknowledge()
        game.capstone_view.dismissed = True
        game._handle_capstone_acknowledge()

        # Both capstones must be in capstones_reached
        assert first_capstone.capstone_id in game.player.capstones_reached
        assert second_capstone.capstone_id in game.player.capstones_reached


# ---------------------------------------------------------------------------
# AC10: Firing writes are deferred to acknowledge
# ---------------------------------------------------------------------------


class TestFiringDefersWritesToAcknowledge:
    """AC10: between push_state(CAPSTONE) and the acknowledge callback,
    capstones_reached is still empty and the dialogue flag is unset."""

    def test_writes_deferred_until_acknowledge(self, capstone_registry) -> None:
        capstone = _minimal_capstone("wealth")
        capstone_registry.capstones = {"wealth_capstone": capstone}
        game, sm, _ = _real_game()
        game.player.lens_investment.add_investment("wealth", 95, source="test")

        # Fire the capstone
        game._after_player_action("test")
        assert sm.current_state == GameState.CAPSTONE

        # Before acknowledge: writes must NOT have happened
        assert "wealth_capstone" not in game.player.capstones_reached, (
            "capstones_reached must be empty before the player acknowledges"
        )
        assert not game.player.dialogue_flags.get("wealth_capstone_reached", False), (
            "dialogue flag must not be set before acknowledge"
        )

        # Acknowledge
        game._on_capstone_acknowledge()

        # After acknowledge: writes must have happened
        assert "wealth_capstone" in game.player.capstones_reached, (
            "capstones_reached must be populated after acknowledge"
        )
        assert game.player.dialogue_flags.get("wealth_capstone_reached") is True, (
            "dialogue flag must be set after acknowledge"
        )

    def test_modal_suppresses_further_ticks_while_active(self, capstone_registry) -> None:
        """While GameState.CAPSTONE is active, _after_player_action is a no-op."""
        capstone = _minimal_capstone("wealth")
        second_capstone = _minimal_capstone("exploration")
        capstone_registry.capstones = {
            "wealth_capstone": capstone,
            "exploration_capstone": second_capstone,
        }
        game = _mock_game()
        game.player.lens_investment.add_investment("wealth", 95, source="test")
        game.player.lens_investment.add_investment("exploration", 95, source="test")
        # Simulate CAPSTONE already active
        game.state_manager.current_state = GameState.CAPSTONE

        game._after_player_action("test")

        # While CAPSTONE is active, push_state must NOT be called
        assert game.state_manager.push_state.call_count == 0, (
            "While CAPSTONE is active, _after_player_action must be suppressed"
        )
