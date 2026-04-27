"""Scenario: combat victory — the win path of a fight.

SI-2 Stream 1. Counterpart to ``test_scenario_death_respawn`` (the loss
path). Every successful combat in the game runs this code.

Two halves under test:

  1. **Engine victory detection** — when all enemies are dead/fled,
     ``CombatEngine._check_combat_end`` (called from ``end_round``) sets
     ``state.result = CombatResult.VICTORY`` and ``is_combat_over()``
     returns True.

  2. **Reward dispatch** — game.py mirrors the
     ``CombatResult.VICTORY`` branch in ``Game._on_combat_complete``
     (see ``spacegame/engine/game.py:3039``): credits the
     ``combats_won`` counter, awards summed ``xp_reward`` via
     ``progression.add_xp``, rolls ``loot_table`` + ``rare_loot`` into
     cargo, and adds ``credit_reward`` to credits. This scenario inlines
     the same block so a regression in any reward primitive surfaces
     here. **If you refactor the game.py block (e.g. into a
     ``Player.apply_combat_victory`` method, mirroring
     ``apply_combat_defeat``), update the inlined block in
     ``_apply_victory_rewards`` below to call it instead.**

A defeat-path crash class shipped to a playtester before
``test_scenario_death_respawn`` existed (the ``add_reputation`` →
``modify_reputation`` typo). The same class of crash on the victory
path would silently break every successful fight; this scenario is the
defense.
"""

from __future__ import annotations

import pytest

from spacegame.models.action_queue import ActionQueue
from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatMove,
    CombatResult,
    CombatState,
    EffectType,
    build_player_combat_state,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.upgrades import ShipUpgradeManager
from spacegame.views.combat_view import _roll_loot
from tests.test_scenarios._helpers import fresh_player, real_enemy

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def _make_engine(player, enemies, *, seed: int = 42):
    """Build a CombatEngine on real models — same construction as game.py."""
    upgrade_mgr = ShipUpgradeManager()
    player_state = build_player_combat_state(
        ship=player.ship,
        upgrade_manager=upgrade_mgr,
        crew_roster=None,
        crew_combat_moves={},
        player_level=5,
        progression=player.progression,
        dialogue_flags=player.dialogue_flags,
    )
    encounter = CombatEncounter(
        enemy_templates=[e.template for e in enemies],
        encounter_seed=seed,
    )
    state = CombatState(
        player=player_state,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
        progression=player.progression,
    )
    return CombatEngine(state, seed=seed)


def _apply_victory_rewards(player, state: CombatState) -> dict[str, int]:
    """Mirror ``Game._on_combat_complete`` VICTORY branch (game.py:3039).

    Kept inline so a regression in any reward primitive surfaces in this
    test. Returns a totals dict for assertions.
    """
    assert state.result == CombatResult.VICTORY, "rewards only valid post-victory"

    player.combats_won += 1
    total_xp = sum(e.template.xp_reward for e in state.enemies)
    player.progression.add_xp(total_xp)

    loot_added: dict[str, int] = {}
    for enemy in state.enemies:
        if enemy.is_alive:
            continue
        if enemy.template.loot_table:
            for cid, qty in _roll_loot(
                enemy.template.loot_table,
                seed=state.encounter.encounter_seed + hash(enemy.template.id),
            ).items():
                player.ship.add_cargo(cid, qty)
                loot_added[cid] = loot_added.get(cid, 0) + qty
        if enemy.template.rare_loot:
            for cid, qty in _roll_loot(
                enemy.template.rare_loot,
                seed=state.encounter.encounter_seed + hash(enemy.template.id) + 7919,
            ).items():
                player.ship.add_cargo(cid, qty)
                loot_added[cid] = loot_added.get(cid, 0) + qty

    total_credits = sum(e.template.credit_reward for e in state.enemies if not e.is_alive)
    if total_credits > 0:
        player.add_credits(total_credits)

    return {"xp": total_xp, "credits": total_credits, "loot_units": sum(loot_added.values())}


# ---------------------------------------------------------------------------
# 1. Engine victory detection
# ---------------------------------------------------------------------------


class TestEngineRecognizesVictory:
    def test_killing_only_enemy_sets_victory_on_round_end(self) -> None:
        """All enemies dead → end_round flips result to VICTORY."""
        player = fresh_player()
        enemy = real_enemy("pirate_scout")
        engine = _make_engine(player, [enemy])

        # Pre-condition: combat is live.
        assert engine.is_combat_over() is False
        assert engine.get_state().result == CombatResult.IN_PROGRESS

        # Simulate the killing blow without depending on weapon balance.
        enemy.current_hull = 0
        assert not enemy.is_alive

        # end_round runs the post-turn check — this is the canonical path.
        engine.end_round()

        assert engine.is_combat_over() is True
        assert engine.get_state().result == CombatResult.VICTORY

    def test_one_alive_one_dead_does_not_trigger_victory(self) -> None:
        """all_enemies_defeated requires every enemy dead/fled — partial doesn't count."""
        player = fresh_player()
        enemies = [real_enemy("pirate_scout"), real_enemy("pirate_scout")]
        engine = _make_engine(player, enemies)

        enemies[0].current_hull = 0
        engine.end_round()

        assert engine.is_combat_over() is False
        assert engine.get_state().result == CombatResult.IN_PROGRESS

    def test_all_fled_also_counts_as_victory(self) -> None:
        """A pirate_scout that flees still ends combat — fled counts as 'defeated'
        for purposes of all_enemies_defeated."""
        player = fresh_player()
        enemy = real_enemy("pirate_scout")
        engine = _make_engine(player, [enemy])

        enemy.is_fled = True
        engine.end_round()

        assert engine.is_combat_over() is True
        assert engine.get_state().result == CombatResult.VICTORY


# ---------------------------------------------------------------------------
# 2. Reward dispatch (mirrors game.py:3039)
# ---------------------------------------------------------------------------


class TestVictoryRewardsApply:
    def test_xp_credits_and_loot_flow_to_player(self) -> None:
        """XP, credits, loot, and combats_won counter all update."""
        player = fresh_player(credits=1000)
        starting_credits = player.credits
        starting_xp = player.progression.xp
        starting_combats_won = player.combats_won
        starting_cargo_units = sum(player.ship.current_cargo.values())

        enemy = real_enemy("pirate_scout")  # xp=15, credits=10, has loot_table
        engine = _make_engine(player, [enemy])
        enemy.current_hull = 0
        engine.end_round()

        rewards = _apply_victory_rewards(player, engine.get_state())

        assert player.combats_won == starting_combats_won + 1
        assert rewards["xp"] == enemy.template.xp_reward == 15
        assert player.progression.xp == starting_xp + 15
        assert player.credits == starting_credits + enemy.template.credit_reward
        # loot is rolled with chance < 1.0 — exact count varies, but units and
        # cargo state must increase if the seeded roll lands at all.
        new_cargo_units = sum(player.ship.current_cargo.values())
        assert new_cargo_units >= starting_cargo_units, "cargo can only grow on victory"

    def test_xp_award_sums_across_multiple_enemies(self) -> None:
        """Two pirate_scouts → 2× xp_reward."""
        player = fresh_player()
        starting_xp = player.progression.xp
        enemies = [real_enemy("pirate_scout"), real_enemy("pirate_scout")]
        engine = _make_engine(player, enemies)
        for e in enemies:
            e.current_hull = 0
        engine.end_round()

        rewards = _apply_victory_rewards(player, engine.get_state())

        assert rewards["xp"] == 30  # 15 × 2
        assert player.progression.xp == starting_xp + 30

    def test_fled_enemies_grant_xp_but_no_credits_or_loot(self) -> None:
        """An enemy that fled is not 'defeated' — credits/loot only roll on
        truly dead enemies (game.py checks ``not enemy.is_alive``)."""
        player = fresh_player()
        starting_credits = player.credits
        enemy = real_enemy("pirate_scout")
        engine = _make_engine(player, [enemy])
        enemy.is_fled = True  # alive but fled
        engine.end_round()

        rewards = _apply_victory_rewards(player, engine.get_state())

        # XP awards for every enemy in the encounter regardless of state
        # (matches game.py: ``sum(e.template.xp_reward for e in state.enemies)``)
        assert rewards["xp"] == 15
        # Credits guard on ``not enemy.is_alive`` — fled scout is still alive
        assert player.credits == starting_credits
        assert rewards["credits"] == 0
        assert rewards["loot_units"] == 0


# ---------------------------------------------------------------------------
# 3. Full journey — actual player attack drives the loop
# ---------------------------------------------------------------------------


class TestVictoryHappyPath:
    """One end-to-end test that drives the engine via real player actions
    until victory. Damage variance is real, so we cap rounds and skip if
    the player can't reliably one-shot — but the canonical 'queued action
    + end_round' loop must execute without crashing."""

    def test_player_attack_loop_reaches_victory(self) -> None:
        player = fresh_player()
        enemy = real_enemy("pirate_scout")
        engine = _make_engine(player, [enemy])
        state = engine.get_state()

        # Starter shuttle has no native weapons. Inject a synthetic
        # high-damage move so the loop drives deterministically — what
        # we're testing is the engine plumbing (queue → execute → enemy
        # turn → end_round → victory check), not weapon balance.
        move = CombatMove(
            id="scenario_test_blaster",
            name="Test Blaster",
            description="Synthetic weapon for the victory scenario.",
            effects=[CombatEffect(type=EffectType.DAMAGE, value=50.0)],
            energy_cost=0,
            accuracy_modifier=999,  # never miss
            category="weapon",
            slot_key="scenario_test_blaster",
        )
        state.player.equipment_moves.append(move)

        # Drive up to 20 rounds. pirate_scout has 37 hull; the loop almost
        # always resolves in single digits but we cap to stay deterministic.
        for _round in range(20):
            queue = ActionQueue(
                energy_available=state.player.energy,
                cooldowns=state.player.cooldowns,
            )
            queue.add(move_id=move.id, target_idx=0, move=move)
            engine.execute_player_turn(queue)
            engine.execute_enemy_turns()
            engine.end_round()
            if engine.is_combat_over():
                break
            # Refill energy so the loop doesn't stall on accumulated cost.
            state.player.energy = state.player.max_energy
            # Keep the player alive — this scenario tests the win path,
            # not survivability.
            state.player.hull = state.player.max_hull
            state.player.shields = state.player.max_shields

        if not engine.is_combat_over():
            # If a real loop can't kill a pirate_scout in 20 rounds with
            # full-energy refill, that's a separate balance bug — fail
            # loudly so it gets investigated, don't silently pass.
            pytest.fail(
                "pirate_scout survived 20 player turns with energy refilled — "
                "either the starter ship has no offensive moves or balance "
                "drifted hard. Investigate."
            )

        assert state.result == CombatResult.VICTORY
        # Reward dispatch is exercised separately in TestVictoryRewardsApply;
        # here we only prove the engine loop reaches victory under real input.
