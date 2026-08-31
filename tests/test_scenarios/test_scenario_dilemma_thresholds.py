"""A2-8 scenario coverage: engine-level dilemma threshold behavior.

Covers acceptance criteria that require the full Game wiring:

AC4  — one pole at 90 and the other at 0 does not collide; both at 90
       transitions to DILEMMA_RESOLUTION; no further telegraph fires
       while the modal is on top.

AC5  — the telegraph is delivered on the first qualifying action after
       crossing telegraph_threshold, with no player-initiated dialogue.

AC6  — a three-pole dilemma with ``collision_requires=2`` opens the
       resolution modal when exactly two of three poles cross the
       collision threshold; the below-threshold pole appears as a
       resolution button (D3 escape-valve rule).

AC8  — repeated qualifying actions cycle through ``telegraph_lines`` in
       order (round-robin), rather than parroting ``telegraph_lines[0]``.

Tests inject synthetic ``Dilemma`` fixtures into
``DataLoader.dilemmas`` via a try/finally so the singleton loader
stays clean across tests.
"""

from __future__ import annotations

import os

# Headless SDL before importing pygame anywhere else -- the modal view
# constructor calls ``get_font`` which requires ``pygame.font.init()``.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock, patch

import pygame
import pygame_gui
import pytest

pygame.init()
pygame.display.init()
_screen = pygame.display.set_mode((1280, 720))
_ui_manager_singleton = pygame_gui.UIManager((1280, 720))

from spacegame.config import GameState  # noqa: E402
from spacegame.constants import flags  # noqa: E402
from spacegame.data_loader import get_data_loader  # noqa: E402
from spacegame.engine.state_manager import StateManager  # noqa: E402
from spacegame.models.dilemma import Dilemma, DilemmaOutcome  # noqa: E402
from spacegame.models.lens_investment import LensInvestment  # noqa: E402
from tests.test_scenarios._helpers import fresh_player  # noqa: E402


def _outcome(winning_lens: str) -> DilemmaOutcome:
    return DilemmaOutcome(
        winning_lens_id=winning_lens,
        closes=[winning_lens],
        tier_unlocks=[],
        outcome_flag=f"outcome_{winning_lens}",
        narration_summary=f"Chose {winning_lens}.",
    )


def _pair_dilemma() -> Dilemma:
    return Dilemma(
        id="d_scenario_pair",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["alpha line", "beta line", "gamma line"],
        outcomes=[_outcome("wealth"), _outcome("community")],
    )


def _triangle_dilemma() -> Dilemma:
    return Dilemma(
        id="d_scenario_triangle",
        poles=["order", "freedom", "faith"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["triangle line"],
        outcomes=[_outcome("order"), _outcome("freedom"), _outcome("faith")],
    )


def _make_bare_game(player, ui_manager=None):
    """Build a bare-bones Game object that exposes just what _after_player_action needs.

    Uses the same ``__init__``-suppression trick as
    ``tests/test_engine/test_mission_notifications.py`` so we do not
    have to pygame-init a real display for a model-layer scenario.
    """
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()

    game._player = player  # type: ignore[attr-defined]
    game._mission_notifications = []
    game.state_manager = StateManager()
    # Give the state manager a placeholder current_state so
    # push/pop mechanics work. A stub view is fine -- the scenario
    # never renders.
    stub_state = GameState.GALAXY_MAP
    game.state_manager.states[stub_state] = MagicMock()
    game.state_manager.current_state = stub_state
    game.ambient_dialogue = None
    game.crew_roster = None
    game.ui_manager = ui_manager if ui_manager is not None else _ui_manager_singleton
    game._dilemma_resolution_view = None
    return game


@pytest.fixture
def dilemmas_registry_isolation():
    """Save + restore ``data_loader.dilemmas`` across a test.

    Tests inject synthetic ``Dilemma`` fixtures for the duration of the
    test; the loader singleton persists across tests, so we must
    restore the prior state on teardown to avoid cross-test pollution.

    IMPORTANT ordering gotcha: ``fresh_player`` from ``_helpers``
    triggers ``dl.load_all()`` which wipes ``dl.dilemmas`` back to the
    on-disk state (empty in A2-8). Tests must build their player
    FIRST, then inject the fixture -- or use ``_seed_registry`` below.
    """
    dl = get_data_loader()
    dl.load_all()
    saved = dict(dl.dilemmas)
    try:
        yield dl
    finally:
        dl.dilemmas = saved


def _prepare_player_and_registry(dl, dilemmas: list[Dilemma], investment: dict[str, int]):
    """Build a fresh player + inject the dilemmas in the correct order.

    Handles the ``fresh_player`` / ``load_all`` re-clearing gotcha
    documented on the fixture: the player must be built before
    ``dl.dilemmas`` is populated.
    """
    player = fresh_player()
    dl.dilemmas = {d.id: d for d in dilemmas}
    player.lens_investment = LensInvestment(_values=dict(investment))
    return player


class TestScenarioAC4NoCollisionAndSuppression:
    """AC4: one-sided investment does not collide; both sides do; and
    the modal blocks any further telegraph fire."""

    def test_one_pole_alone_does_not_collide(self, dilemmas_registry_isolation) -> None:
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation,
            [_pair_dilemma()],
            {"wealth": 90, "community": 0},
        )
        game = _make_bare_game(player)

        game._after_player_action("combat_victory")

        assert game.state_manager.current_state != GameState.DILEMMA_RESOLUTION
        assert game._dilemma_resolution_view is None
        # No telegraph either -- one pole above telegraph_threshold does
        # not meet collision_requires=2.
        assert not any("priya" in m.lower() for m in game._mission_notifications)

    def test_both_poles_at_collision_transitions_and_suppresses_further(
        self, dilemmas_registry_isolation
    ) -> None:
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation,
            [_pair_dilemma()],
            {"wealth": 90, "community": 90},
        )
        game = _make_bare_game(player)

        game._after_player_action("combat_victory")

        assert game.state_manager.current_state == GameState.DILEMMA_RESOLUTION, (
            "Both poles above collision_threshold must push DILEMMA_RESOLUTION"
        )
        assert game._dilemma_resolution_view is not None

        # A subsequent action while the modal is active must be a no-op:
        # no additional telegraph notifications, no double-modal push.
        notifications_before = len(game._mission_notifications)
        game._after_player_action("mission_completed")
        assert len(game._mission_notifications) == notifications_before, (
            "Modal-active suppression must block further notifications"
        )


class TestScenarioAC5TelegraphWithoutDialogue:
    """AC5: the telegraph fires from the qualifying player action alone,
    with no player-initiated dialogue call."""

    def test_telegraph_appears_in_notification_queue_on_first_qualifying_action(
        self, dilemmas_registry_isolation
    ) -> None:
        dilemma = _pair_dilemma()
        # Both poles at 60 -- above telegraph (55), below collision (80).
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation, [dilemma], {"wealth": 60, "community": 60}
        )
        game = _make_bare_game(player)

        game._after_player_action("combat_victory")

        # Telegraph fired -- the first line, prefixed by NPC display name.
        assert any("alpha line" in m for m in game._mission_notifications), (
            f"Expected telegraph line in notifications, got: {game._mission_notifications}"
        )
        # The dilemma is marked as telegraphed on the player's runtime state.
        assert dilemma.id in player.dilemma_state.telegraphed
        # And a corresponding flag is set in dialogue_flags.
        assert player.dialogue_flags.get(flags.dilemma_telegraphed(dilemma.id)) is True
        # No collision yet.
        assert game.state_manager.current_state != GameState.DILEMMA_RESOLUTION


class TestScenarioAC6TrianglePole:
    """AC6: three-pole dilemma with collision_requires=2 fires on two of
    three; the below-threshold pole is offered as a button."""

    def test_two_of_three_poles_collide_and_third_pole_is_eligible(
        self, dilemmas_registry_isolation
    ) -> None:
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation,
            [_triangle_dilemma()],
            {"order": 90, "freedom": 90, "faith": 0},
        )
        game = _make_bare_game(player)

        game._after_player_action("combat_victory")

        assert game.state_manager.current_state == GameState.DILEMMA_RESOLUTION
        view = game._dilemma_resolution_view
        assert view is not None
        # The D3 rule: len(poles) > collision_requires, so the
        # below-threshold pole (faith) MUST appear as an option.
        eligible = set(view._eligible_poles())
        assert eligible == {"order", "freedom", "faith"}


class TestScenarioAC8RoundRobinTelegraphs:
    """AC8: three back-to-back qualifying actions cycle through
    ``telegraph_lines`` in order, not repeat line[0]."""

    def test_three_actions_cycle_all_three_lines_in_order(
        self, dilemmas_registry_isolation
    ) -> None:
        # telegraph_lines = ['alpha line', 'beta line', 'gamma line'];
        # keep values above telegraph, below collision so telegraph re-fires.
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation, [_pair_dilemma()], {"wealth": 60, "community": 60}
        )
        game = _make_bare_game(player)

        # Three qualifying actions in a row.
        game._after_player_action("combat_victory")
        game._after_player_action("mission_completed")
        game._after_player_action("sold_cargo")

        joined = "\n".join(game._mission_notifications)
        # Assert order: alpha, beta, gamma.
        alpha_idx = joined.find("alpha line")
        beta_idx = joined.find("beta line")
        gamma_idx = joined.find("gamma line")
        assert alpha_idx != -1, f"first line missing: {game._mission_notifications}"
        assert beta_idx != -1 and beta_idx > alpha_idx, (
            f"second line missing or out of order: {game._mission_notifications}"
        )
        assert gamma_idx != -1 and gamma_idx > beta_idx, (
            f"third line missing or out of order: {game._mission_notifications}"
        )

    def test_repeat_delivery_wraps_around_line_pool(self, dilemmas_registry_isolation) -> None:
        """A fourth action wraps back to line[0] -- cursor uses mod arithmetic."""
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation, [_pair_dilemma()], {"wealth": 60, "community": 60}
        )
        game = _make_bare_game(player)

        for _ in range(4):
            game._after_player_action("combat_victory")

        # After 4 fires and 3 unique lines, alpha line appears twice.
        alpha_count = sum(1 for m in game._mission_notifications if "alpha line" in m)
        assert alpha_count == 2, (
            f"Round-robin must wrap after cycling all lines: {game._mission_notifications}"
        )


class TestScenarioResolveDilemma:
    """Once the player picks a pole, the resolved flag + runtime state
    are recorded and the modal pops. A subsequent qualifying action must
    NOT re-fire the resolved dilemma (coordinator skips resolved)."""

    def test_resolve_records_state_and_pops_modal(self, dilemmas_registry_isolation) -> None:
        dilemma = _pair_dilemma()
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation, [dilemma], {"wealth": 90, "community": 90}
        )
        game = _make_bare_game(player)

        game._after_player_action("combat_victory")
        assert game.state_manager.current_state == GameState.DILEMMA_RESOLUTION

        # Simulate the player pressing the wealth button.
        view = game._dilemma_resolution_view
        assert view is not None
        view.on_resolve("wealth")
        view.dismissed = True

        # Frame handler pops the modal.
        game._handle_dilemma_resolution()

        assert game.state_manager.current_state != GameState.DILEMMA_RESOLUTION
        assert game._dilemma_resolution_view is None
        assert player.dilemma_state.resolved.get(dilemma.id) == "wealth"
        assert player.dialogue_flags.get(flags.dilemma_resolved(dilemma.id)) is True

    def test_resolved_dilemma_does_not_refire_on_next_action(
        self, dilemmas_registry_isolation
    ) -> None:
        dilemma = _pair_dilemma()
        player = _prepare_player_and_registry(
            dilemmas_registry_isolation, [dilemma], {"wealth": 90, "community": 90}
        )
        player.dilemma_state.resolved[dilemma.id] = "wealth"
        game = _make_bare_game(player)

        game._after_player_action("combat_victory")

        # No modal, no telegraph -- a resolved dilemma is skipped entirely.
        assert game.state_manager.current_state != GameState.DILEMMA_RESOLUTION
        assert game._dilemma_resolution_view is None
