"""End-to-end scenarios for the A2-8 dilemma engine.

Covers AC4, AC5, AC6, AC8 by driving ``_after_player_action`` on a
minimally-mocked :class:`~spacegame.engine.game.Game` against a
hand-built dilemma injected into the :class:`~spacegame.data_loader.DataLoader`
singleton. The engine reads investment via
:func:`~spacegame.models.dilemma.check_dilemmas` in the model layer,
so we drive investment on the real ``player.lens_investment`` store
(tests are allowed to touch it — the compliance guard is scoped to
``spacegame/views/`` and ``spacegame/engine/``).

Each test uses a ``try / finally`` to restore ``dl.dilemmas`` because
the singleton persists across the whole session.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from spacegame.config import GameState
from spacegame.constants import flags as flag_registry
from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import Dilemma, DilemmaOutcome, DilemmaRuntimeState
from spacegame.models.lens_investment import LensInvestment


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
        id="d_scenario_pair",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["one", "two", "three"],
        outcomes=[_outcome("wealth"), _outcome("community")],
    )


def _triangle_dilemma() -> Dilemma:
    return Dilemma(
        id="d_scenario_triangle",
        poles=["order", "freedom", "faith"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="marcus_jin",
        telegraph_lines=["alpha"],
        outcomes=[_outcome("order"), _outcome("freedom"), _outcome("faith")],
    )


def _mock_game():
    """Construct a Game with just enough state for _after_player_action.

    Mocks ``crew_roster`` and ``ambient_dialogue`` off so
    ``_trigger_crew_reaction`` returns early — the dilemma engine tick
    is what the scenarios exercise, not crew banter.
    """
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = MagicMock()
    game.player.lens_investment = LensInvestment()
    game.player.dilemma_state = DilemmaRuntimeState()
    game.player.dialogue_flags = {}
    game.crew_roster = None
    game.ambient_dialogue = None
    game._mission_notifications = []
    game.ui_manager = None
    game.state_manager = MagicMock(current_state=None)
    game.dilemma_resolution_view = None
    game._pending_dilemma = None
    return game


@pytest.fixture
def dilemma_registry():
    """Inject a fresh dilemma registry for the duration of a test."""
    dl = get_data_loader()
    dl.load_all()
    saved = dict(dl.dilemmas)
    try:
        yield dl
    finally:
        dl.dilemmas = saved


class TestSingleHotPoleDoesNotCollide:
    """AC4 first half: one pole hot in isolation does not fire the modal."""

    def test_one_pole_at_90_never_pushes_modal(self, dilemma_registry) -> None:
        dilemma = _pair_dilemma()
        dilemma_registry.dilemmas = {dilemma.id: dilemma}
        game = _mock_game()
        game.player.lens_investment.add_investment("wealth", 90, source="test")

        game._after_player_action("test_action")

        assert game.state_manager.push_state.call_count == 0
        assert game.player.dilemma_state.resolved == {}
        # Telegraph must not fire — only one pole is above telegraph threshold.
        assert not any("priya" in n.lower() or '"' in n for n in game._mission_notifications), (
            f"Unexpected telegraph fired for a one-pole state: {game._mission_notifications!r}"
        )


class TestBothPolesHotFiresCollision:
    """AC4 second half: both poles above threshold pushes the modal AND
    suppresses further telegraph re-delivery while resolution is active.
    """

    def test_both_poles_at_90_pushes_modal(self, dilemma_registry) -> None:
        dilemma = _pair_dilemma()
        dilemma_registry.dilemmas = {dilemma.id: dilemma}
        game = _mock_game()
        game.ui_manager = _real_ui_manager()
        game.player.lens_investment.add_investment("wealth", 90, source="test")
        game.player.lens_investment.add_investment("community", 90, source="test")

        game._after_player_action("test_action")

        game.state_manager.push_state.assert_called_once_with(GameState.DILEMMA_RESOLUTION)
        assert game.dilemma_resolution_view is not None
        assert game._pending_dilemma is dilemma

    def test_no_further_telegraph_after_modal_pushed(self, dilemma_registry) -> None:
        """AC4: once ``DILEMMA_RESOLUTION`` is active, ``_after_player_action``
        is a no-op — no additional telegraph line lands in the queue."""
        dilemma = _pair_dilemma()
        dilemma_registry.dilemmas = {dilemma.id: dilemma}
        game = _mock_game()
        game.ui_manager = _real_ui_manager()
        game.player.lens_investment.add_investment("wealth", 90, source="test")
        game.player.lens_investment.add_investment("community", 90, source="test")
        game._after_player_action("test_action")
        notifications_before = list(game._mission_notifications)

        # Simulate the state manager reflecting the pushed modal.
        game.state_manager.current_state = GameState.DILEMMA_RESOLUTION
        game._after_player_action("test_action_again")

        assert game._mission_notifications == notifications_before, (
            "Once the resolution modal is active, no further telegraph lines should land — AC4."
        )


class TestTelegraphFiresWithoutPlayerDialogue:
    """AC5: telegraph delivery happens on the qualifying action, without
    the player initiating a dialogue with ``telegraph_npc_id``.
    """

    def test_telegraph_appears_after_qualifying_action(self, dilemma_registry) -> None:
        dilemma = _pair_dilemma()
        dilemma_registry.dilemmas = {dilemma.id: dilemma}
        game = _mock_game()
        game.player.lens_investment.add_investment("wealth", 60, source="test")
        game.player.lens_investment.add_investment("community", 60, source="test")

        game._after_player_action("test_action")

        assert any('"one"' in n for n in game._mission_notifications), (
            f"Expected first telegraph line 'one' in notifications, got "
            f"{game._mission_notifications!r}"
        )
        # Telegraph flag is set on first delivery so downstream systems can gate.
        assert game.player.dialogue_flags.get(flag_registry.dilemma_telegraphed(dilemma.id)) is True
        assert dilemma.id in game.player.dilemma_state.telegraphed


class TestTriangleDilemma:
    """AC6: 3-pole synthetic fixture collides when 2 of 3 cross threshold."""

    def test_two_of_three_hot_fires_collision(self, dilemma_registry) -> None:
        dilemma = _triangle_dilemma()
        dilemma_registry.dilemmas = {dilemma.id: dilemma}
        game = _mock_game()
        game.ui_manager = _real_ui_manager()
        game.player.lens_investment.add_investment("order", 90, source="test")
        game.player.lens_investment.add_investment("freedom", 90, source="test")
        # 'faith' left at 0

        game._after_player_action("test_action")

        game.state_manager.push_state.assert_called_once_with(GameState.DILEMMA_RESOLUTION)
        # The mocked state_manager doesn't invoke on_enter automatically —
        # call it here so we can assert on the created buttons.
        game.dilemma_resolution_view.on_enter()
        # The below-threshold third pole must still get a button — D3 rule.
        assert set(game.dilemma_resolution_view.pole_buttons.keys()) == {
            "order",
            "freedom",
            "faith",
        }
        game.dilemma_resolution_view.on_exit()


class TestTelegraphRoundRobinCycles:
    """AC8: telegraph re-delivery cycles through ``telegraph_lines`` in order
    rather than parroting line[0] on every qualifying action.
    """

    def test_three_qualifying_actions_yield_three_distinct_lines(self, dilemma_registry) -> None:
        dilemma = _pair_dilemma()  # telegraph_lines = ["one", "two", "three"]
        dilemma_registry.dilemmas = {dilemma.id: dilemma}
        game = _mock_game()
        game.player.lens_investment.add_investment("wealth", 60, source="test")
        game.player.lens_investment.add_investment("community", 60, source="test")

        game._after_player_action("action_1")
        game._after_player_action("action_2")
        game._after_player_action("action_3")

        text = " || ".join(game._mission_notifications)
        assert '"one"' in text, f"Missing 'one' in {text!r}"
        assert '"two"' in text, f"Missing 'two' in {text!r}"
        assert '"three"' in text, f"Missing 'three' in {text!r}"
        # Assert order-preservation: 'one' appears before 'two' before 'three'.
        one_idx = text.index('"one"')
        two_idx = text.index('"two"')
        three_idx = text.index('"three"')
        assert one_idx < two_idx < three_idx, (
            f"Round-robin cycle out of order: got '{text}' (indices "
            f"one={one_idx} two={two_idx} three={three_idx})"
        )


def _real_ui_manager():
    """Build a real pygame_gui.UIManager so DilemmaResolutionView.__init__ works.

    Kept in a helper so scenarios that only need to assert on
    ``state_manager.push_state`` don't pay the pygame initialization
    cost.
    """
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    import pygame_gui

    from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH

    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
