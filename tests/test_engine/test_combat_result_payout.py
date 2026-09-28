"""End-to-end coverage of Game._apply_combat_result's VICTORY/NEGOTIATED payouts.

Task 6 fixed the model layer (``Player.apply_combat_victory`` /
``apply_combat_negotiated``) and rewired ``game.py`` to call it, but no
committed test drove ``_apply_combat_result`` itself through either branch.
That left a game-level regression invisible: a wrong seed argument or a
dropped ``negotiate_partial_loot`` check would pass every committed test
(the model tests call ``Player`` directly; they never see what ``game.py``
passes it). These tests close that gap by driving the real method with a
mocked ``combat_view`` (only the collaborators ``_apply_combat_result``
reaches: ``ambient_dialogue``, ``social_manager``, ``audio_manager``,
``_after_player_action``) and asserting the loot lands in the real
player's real cargo hold.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from spacegame.engine.game import Game
from spacegame.models.combat import CombatResult, EnemyShip
from spacegame.models.combat_rewards import loot_rng, roll_loot
from tests.test_scenarios._helpers import fresh_player, real_enemy

SEED = 1234


def _make_game() -> Game:
    """A ``Game`` with just enough wiring for ``_apply_combat_result`` to run."""
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = fresh_player(credits=0)
    game.ambient_dialogue = None
    game.social_manager = None
    game.politics_manager = None
    game.audio_manager = MagicMock()
    game._mission_notifications = []
    game._after_player_action = MagicMock()
    game.combat_view = MagicMock()
    return game


def _make_state(
    *,
    result: CombatResult,
    enemies: list[EnemyShip],
    negotiate_partial_loot: bool = False,
) -> MagicMock:
    """A combat-engine state stub carrying only what ``_apply_combat_result`` reads."""
    state = MagicMock()
    state.result = result
    state.enemies = enemies
    state.encounter.encounter_seed = SEED
    state.negotiate_partial_loot = negotiate_partial_loot
    state.negotiate_rival_rep = False
    state.player.hull = 80
    state.player.shields = 20
    return state


class TestVictoryPayout:
    def test_destroyed_enemy_pays_loot_credits_xp_and_fires_the_hook(self) -> None:
        """VICTORY: the destroyed enemy's loot lands in cargo, credits and XP pay out."""
        game = _make_game()
        enemy = real_enemy("pirate_raider")
        enemy.current_hull = 0  # destroyed, not fled

        common = roll_loot(enemy.template.loot_table, loot_rng(SEED, enemy.template.id, rare=False))
        rare = roll_loot(enemy.template.rare_loot, loot_rng(SEED, enemy.template.id, rare=True))
        expected: dict[str, int] = dict(common)
        for commodity_id, qty in rare.items():
            expected[commodity_id] = expected.get(commodity_id, 0) + qty
        assert expected, "seed 1234 must roll pirate_raider loot, or this test proves nothing"

        state = _make_state(result=CombatResult.VICTORY, enemies=[enemy])
        game.combat_view.engine.get_state.return_value = state

        game._apply_combat_result()

        for commodity_id, qty in expected.items():
            assert game.player.ship.get_cargo_quantity(commodity_id) == qty, (
                f"expected {qty} {commodity_id} in cargo after victory"
            )
        assert game.player.credits == enemy.template.credit_reward
        assert game.player.combats_won == 1
        game._after_player_action.assert_called_once_with("combat_victory")


class TestNegotiatedPayout:
    def test_partial_loot_true_pays_half_of_each_common_roll(self) -> None:
        """NEGOTIATED with partial_loot=True: cargo gets max(1, qty // 2) per commodity."""
        game = _make_game()
        enemy = real_enemy("pirate_raider")

        common = roll_loot(enemy.template.loot_table, loot_rng(SEED, enemy.template.id, rare=False))
        assert common, "seed 1234 must roll pirate_raider loot, or the halving check proves nothing"
        expected = {commodity_id: max(1, qty // 2) for commodity_id, qty in common.items()}

        state = _make_state(
            result=CombatResult.NEGOTIATED, enemies=[enemy], negotiate_partial_loot=True
        )
        game.combat_view.engine.get_state.return_value = state

        game._apply_combat_result()

        for commodity_id, qty in expected.items():
            assert game.player.ship.get_cargo_quantity(commodity_id) == qty, (
                f"expected {qty} {commodity_id} in cargo after negotiated partial loot"
            )
        assert (game.player.combats_won, game.player.combats_negotiated) == (1, 1)

    def test_partial_loot_false_counts_the_negotiation_but_pays_nothing(self) -> None:
        """NEGOTIATED with partial_loot=False: counters update, no cargo moves."""
        game = _make_game()
        enemy = real_enemy("pirate_raider")

        common = roll_loot(enemy.template.loot_table, loot_rng(SEED, enemy.template.id, rare=False))
        assert common, (
            "seed 1234 must roll pirate_raider loot, or the empty-payout check proves nothing"
        )

        state = _make_state(
            result=CombatResult.NEGOTIATED, enemies=[enemy], negotiate_partial_loot=False
        )
        game.combat_view.engine.get_state.return_value = state

        game._apply_combat_result()

        for commodity_id in common:
            assert game.player.ship.get_cargo_quantity(commodity_id) == 0, (
                f"expected no {commodity_id} in cargo when partial_loot is False"
            )
        assert (game.player.combats_won, game.player.combats_negotiated) == (1, 1)
