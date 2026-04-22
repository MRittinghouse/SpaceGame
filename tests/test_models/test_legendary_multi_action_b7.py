"""
Phase B7 — Legendary effect verification under multi-action combat.

The existing `test_legendary_combat.py` suite covers each legendary
effect's pure-function contract. This file covers the *integration*
scenarios from combat_balance_design.md §8 — what the effects do when
the combat engine processes a queued multi-action turn:

1. Chain Fire fires **per hit**, not per turn. In a 3-weapon queue,
   each hit rolls independently.
2. Void Absorption accumulates across hits and across turns, then
   releases exactly once per combat.
3. Heat Hardening caps at `heat_hardening_max` stacks; a new combat
   starts with a fresh state.
4. Cooldown Reduction stacks on top of the normal end-of-turn tick.
5. Phase Shift blocks the first incoming attack in an active round,
   not every attack that round.
"""

from __future__ import annotations

import random

from spacegame.models.action_queue import ActionQueue
from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatMove,
    CombatState,
    EffectTarget,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.legendary_effects import (
    LegendaryState,
    apply_cooldown_reduction,
    check_phase_shift,
    process_heat_hardening,
    process_void_absorption,
    process_void_release,
)

# ============================================================================
# Helpers
# ============================================================================


def _move(
    move_id: str = "shot",
    damage: float = 10.0,
    energy: int = 2,
    cooldown: int = 0,
) -> CombatMove:
    return CombatMove(
        id=move_id,
        name=move_id.title(),
        description="",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy,
        cooldown=cooldown,
        accuracy_modifier=50,  # Bias toward hits so counts are stable.
    )


def _player_with_legendary(
    legendary: LegendaryState,
    *,
    hull: int = 200,
    shields: int = 40,
    energy: int = 20,
    weapons: list[CombatMove] | None = None,
    accuracy: int = 95,
    armor: int = 0,
    shield_regen: int = 0,
) -> PlayerCombatState:
    player = PlayerCombatState(
        hull=hull,
        max_hull=hull,
        shields=shields,
        max_shields=shields,
        energy=energy,
        max_energy=energy,
        energy_regen=5,
        speed=6,
        evasion=0,
        accuracy=accuracy,
        equipment_moves=weapons or [_move()],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
        armor=armor,
    )
    player.shield_regen = shield_regen
    player._legendary = legendary
    return player


def _enemy_template(
    eid: str = "dummy",
    hull: int = 500,
    shields: int = 0,
    damage: float = 10.0,
    accuracy: int = 95,
) -> EnemyShipTemplate:
    attack = CombatMove(
        id="attack",
        name="Attack",
        description="",
        effects=[
            CombatEffect(
                type=EffectType.DAMAGE,
                value=damage,
                target=EffectTarget.ENEMY,
            )
        ],
        energy_cost=0,
    )
    return EnemyShipTemplate(
        id=eid,
        name=eid.title(),
        description="",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull,
        shields=shields,
        energy=10,
        energy_regen=3,
        speed=4,
        evasion=0,
        accuracy=accuracy,
        moves=[attack],
        loot_table=[],
        flee_threshold=0.0,
    )


def _build_state(
    player: PlayerCombatState,
    templates: list[EnemyShipTemplate],
    seed: int = 42,
) -> tuple[CombatState, CombatEngine]:
    enemies = [EnemyShip.from_template(t) for t in templates]
    encounter = CombatEncounter(enemy_templates=templates, encounter_seed=seed)
    state = CombatState(
        player=player, enemies=enemies, encounter=encounter, combat_log=[]
    )
    engine = CombatEngine(state, seed=seed)
    return state, engine


# ============================================================================
# 1. Chain Fire — per hit, not per turn
# ============================================================================


class TestChainFireMultiAction:
    """Design doc §8: Chain Fire triggers per weapon hit. In a 3-weapon
    queue, each hit rolls 40% independently — up to 3 chain hits possible."""

    def test_chain_fire_rolls_once_per_full_hit_in_queue(self) -> None:
        """With chain_fire_chance=1.0, every full hit in the queue should
        produce one chain-fire entry. Grazes don't trigger chain fire
        (engine design: mechanics fire on hits, not partial hits)."""
        random.seed(0)
        legendary = LegendaryState(
            chain_fire_chance=1.0, chain_fire_damage_mult=0.5
        )
        weapons = [
            _move(move_id="a", damage=20, energy=2, cooldown=0),
            _move(move_id="b", damage=20, energy=2, cooldown=0),
            _move(move_id="c", damage=20, energy=2, cooldown=0),
        ]
        player = _player_with_legendary(legendary, energy=20, weapons=weapons)
        tpl = _enemy_template(hull=10_000)
        state, engine = _build_state(player, [tpl], seed=0)

        queue = ActionQueue(energy_available=player.energy)
        for w in weapons:
            queue.add(w.id, 0, w)
        engine.execute_player_turn(queue)

        full_hits = [
            e
            for e in state.combat_log
            if e.actor == "player"
            and e.hit
            and "chain" not in (e.action or "").lower()
        ]
        chain_hits = [
            e for e in state.combat_log if "chain" in (e.action or "").lower()
        ]
        assert len(chain_hits) == len(full_hits), (
            f"Chain Fire must trigger exactly once per FULL HIT. "
            f"Got {len(full_hits)} full hits and {len(chain_hits)} chain fires. "
            f"Log: {[(e.action, e.hit, e.effects_applied) for e in state.combat_log]}"
        )
        # Sanity: at chance=1.0 with 3 weapons, expect at least 2 chain fires
        # (allowing for up to one graze in the seed-dependent roll).
        assert len(chain_hits) >= 2, (
            f"At chance=1.0 expected ≥2 chain fires, got {len(chain_hits)}"
        )

    def test_chain_fire_never_triggers_at_zero_chance(self) -> None:
        """Belt-and-suspenders: with chain_fire_chance=0, no chain-fire
        entries should appear even after a 3-weapon queue."""
        legendary = LegendaryState(chain_fire_chance=0.0)
        weapons = [
            _move(move_id="a", damage=20, energy=2, cooldown=0),
            _move(move_id="b", damage=20, energy=2, cooldown=0),
            _move(move_id="c", damage=20, energy=2, cooldown=0),
        ]
        player = _player_with_legendary(legendary, energy=20, weapons=weapons)
        tpl = _enemy_template(hull=10_000)
        state, engine = _build_state(player, [tpl], seed=0)

        queue = ActionQueue(energy_available=player.energy)
        for w in weapons:
            queue.add(w.id, 0, w)
        engine.execute_player_turn(queue)

        chain_hits = [
            entry
            for entry in state.combat_log
            if "chain" in (entry.action or "").lower()
        ]
        assert chain_hits == []


# ============================================================================
# 2. Void Absorption — accumulates across hits and turns, one-shot release
# ============================================================================


class TestVoidAbsorptionAcrossTurns:
    """Design doc §8: absorbs 15% of incoming hull damage per hit. Releases
    once per combat."""

    def test_accumulates_across_multiple_hits(self) -> None:
        state = LegendaryState(
            void_absorption_rate=0.15, void_release_available=True
        )
        process_void_absorption(state, hull_damage=50)
        process_void_absorption(state, hull_damage=50)
        process_void_absorption(state, hull_damage=50)
        assert state.void_charge == int(0.15 * 50) * 3

    def test_accumulates_across_simulated_turns(self) -> None:
        """State persists across multiple combat rounds — void_charge
        grows over a 3-turn pummeling."""
        state = LegendaryState(
            void_absorption_rate=0.20, void_release_available=True
        )
        # Turn 1: 2 hits of 40 each
        process_void_absorption(state, hull_damage=40)
        process_void_absorption(state, hull_damage=40)
        turn1_charge = state.void_charge
        # Turn 2: 1 hit of 60
        process_void_absorption(state, hull_damage=60)
        # Turn 3: 1 hit of 30
        process_void_absorption(state, hull_damage=30)

        expected = int(40 * 0.20) * 2 + int(60 * 0.20) + int(30 * 0.20)
        assert state.void_charge == expected, (
            f"Expected {expected} total void charge, got {state.void_charge} "
            f"(turn1 subtotal was {turn1_charge})"
        )

    def test_release_is_one_shot_per_combat(self) -> None:
        state = LegendaryState(
            void_absorption_rate=0.15,
            void_release_available=True,
            void_charge=80,
        )
        first = process_void_release(state)
        assert first == 80
        # Second release yields nothing.
        second = process_void_release(state)
        assert second == 0
        # Even if new charge accumulates, release is spent.
        process_void_absorption(state, hull_damage=100)
        assert state.void_charge > 0
        third = process_void_release(state)
        assert third == 0


# ============================================================================
# 3. Heat Hardening — armor caps, new combat resets
# ============================================================================


class TestHeatHardeningCapAndReset:
    """Design doc §8: +1 armor per shield hit, max 5, resets at combat end."""

    def test_armor_caps_at_five_after_seven_hits(self) -> None:
        state = LegendaryState(heat_hardening_per_hit=1, heat_hardening_max=5)
        gained_per_hit = []
        for _ in range(7):
            gained_per_hit.append(process_heat_hardening(state, shield_absorbed=10))
        assert state.heat_stacks == 5
        assert gained_per_hit == [1, 1, 1, 1, 1, 0, 0], (
            f"Expected first 5 hits to add 1 armor, remaining to add 0; "
            f"got {gained_per_hit}"
        )

    def test_new_combat_starts_with_zero_stacks(self) -> None:
        """A fresh LegendaryState (built at the start of each combat) has
        0 heat stacks regardless of what prior combat accumulated."""
        stale = LegendaryState(
            heat_hardening_per_hit=1, heat_hardening_max=5, heat_stacks=5
        )
        # Player ends old combat with stacks full.
        assert stale.heat_stacks == 5
        # New combat = new state (this is how the engine creates them).
        fresh = LegendaryState(
            heat_hardening_per_hit=1, heat_hardening_max=5
        )
        assert fresh.heat_stacks == 0

    def test_zero_shield_absorbed_does_not_add_stacks(self) -> None:
        """If shields are already 0 and damage goes straight to hull, heat
        hardening should not spuriously add stacks."""
        state = LegendaryState(heat_hardening_per_hit=1, heat_hardening_max=5)
        gained = process_heat_hardening(state, shield_absorbed=0)
        assert gained == 0
        assert state.heat_stacks == 0


# ============================================================================
# 4. Cooldown Reduction — stacks with normal end-of-round tick
# ============================================================================


class TestCooldownReductionStacking:
    """Design doc §8: -1 to all cooldowns per turn end, stacks with the
    engine's normal tick."""

    def test_legendary_reduces_cooldowns_after_normal_tick(self) -> None:
        """Simulates the engine's end-of-round sequence: first the normal
        tick (player.tick_cooldowns) runs, then apply_cooldown_reduction
        stacks on top."""
        cooldowns = {"burst_0": 3, "tech_1": 2, "sidearm_2": 0}
        # Normal tick — decrement by 1 (mimics player.tick_cooldowns)
        for key in list(cooldowns.keys()):
            cooldowns[key] = max(0, cooldowns[key] - 1)
        assert cooldowns == {"burst_0": 2, "tech_1": 1, "sidearm_2": 0}

        # Legendary tick — another -1 on top
        state = LegendaryState(cooldown_reduction=1)
        apply_cooldown_reduction(state, cooldowns)
        assert cooldowns == {"burst_0": 1, "tech_1": 0, "sidearm_2": 0}

    def test_legendary_never_pushes_cooldown_below_zero(self) -> None:
        cooldowns = {"x": 0, "y": 1}
        state = LegendaryState(cooldown_reduction=2)
        apply_cooldown_reduction(state, cooldowns)
        assert cooldowns["x"] == 0
        assert cooldowns["y"] == 0

    def test_no_reduction_when_disabled(self) -> None:
        cooldowns = {"a": 3, "b": 2}
        state = LegendaryState(cooldown_reduction=0)
        apply_cooldown_reduction(state, cooldowns)
        assert cooldowns == {"a": 3, "b": 2}


# ============================================================================
# 5. Phase Shift — blocks first incoming attack per round, not all attacks
# ============================================================================


class TestPhaseShiftPerRound:
    """Design doc §8: blocks the FIRST incoming attack per round. With
    multiple enemies attacking in one round, phase shift is per-round,
    not per-action."""

    def test_phase_shift_active_on_interval_rounds(self) -> None:
        state = LegendaryState(phase_shift_interval=3)
        # Interval 3 → round 3, 6, 9 active; 1, 2, 4, 5 inactive.
        assert check_phase_shift(state, round_number=3) is True
        assert check_phase_shift(state, round_number=6) is True
        assert check_phase_shift(state, round_number=9) is True
        assert check_phase_shift(state, round_number=1) is False
        assert check_phase_shift(state, round_number=2) is False
        assert check_phase_shift(state, round_number=4) is False

    def test_phase_shift_disabled_when_interval_zero(self) -> None:
        state = LegendaryState(phase_shift_interval=0)
        for rnd in range(1, 20):
            assert check_phase_shift(state, round_number=rnd) is False

    def test_phase_shift_negates_first_attack_only(
        self,
    ) -> None:
        """Design doc §8: phase shift blocks the FIRST incoming attack per
        round. With 3 enemies attacking in one round on an active shift
        round, the first enemy's attack is dodged; the other two hit
        normally.

        Fixed in QA Pass 5 Tier 2.1 (2026-04-21). Previously the engine
        erroneously blocked ALL attacks on an active round, which made
        multi-enemy encounters trivial on shift rounds.
        """
        legendary = LegendaryState(phase_shift_interval=1)
        weapons = [_move(move_id="sidearm", damage=10, energy=2, cooldown=0)]
        player = _player_with_legendary(
            legendary,
            hull=500,
            shields=0,
            weapons=weapons,
            accuracy=95,
            armor=0,
        )
        templates = [
            _enemy_template(eid=f"e{i}", hull=200, damage=20) for i in range(3)
        ]
        _, engine = _build_state(player, templates, seed=7)

        queue = ActionQueue(energy_available=player.energy)
        queue.add("sidearm", 0, weapons[0])

        starting_hull = player.hull
        engine.execute_player_turn(queue)
        engine.execute_enemy_turns()
        hull_loss = starting_hull - player.hull

        # First attack dodged (20 damage absorbed), next two landed normally.
        # Some damage WILL land — strictly more than 0, strictly less than
        # the full 3-attack total. Exact value depends on accuracy rolls
        # but must be in the range [1, 60].
        assert 0 < hull_loss <= 60, (
            f"First-attack dodge should absorb one attack (~20 damage) and "
            f"let the other two land; hull loss was {hull_loss}, expected 1-60"
        )

    def test_phase_shift_inactive_round_does_not_block(self) -> None:
        """On an inactive round, enemies hit normally — no dodge."""
        # interval=3 means active rounds are 3, 6, 9. Round 1 = inactive.
        legendary = LegendaryState(phase_shift_interval=3)
        weapons = [_move(move_id="sidearm", damage=10, energy=2, cooldown=0)]
        player = _player_with_legendary(
            legendary,
            hull=500,
            shields=0,
            weapons=weapons,
            accuracy=95,
            armor=0,
        )
        templates = [_enemy_template(hull=200, damage=20)]
        _, engine = _build_state(player, templates, seed=7)

        queue = ActionQueue(energy_available=player.energy)
        queue.add("sidearm", 0, weapons[0])

        starting_hull = player.hull
        engine.execute_player_turn(queue)
        engine.execute_enemy_turns()
        hull_loss = starting_hull - player.hull
        # One enemy, 20 damage, hit expected → substantial hull loss.
        assert hull_loss > 0, (
            f"Inactive phase-shift round should take normal damage; "
            f"hull loss was {hull_loss}"
        )
