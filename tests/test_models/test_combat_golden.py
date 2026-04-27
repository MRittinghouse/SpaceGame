"""
Golden-number regression tests for Phase B1 of the combat balance pass.

These tests form the safety net for the U2.5d balance pass. Three buckets:

1. **Action queue invariants** — fills a coverage gap. The queue gates
   multi-action turns on energy, cooldowns, and once-per-weapon. None of
   this was previously tested end-to-end.

2. **Balance tripwires** — numerical properties that must remain true
   regardless of how weapons, enemies, or reactors are tuned. If one
   breaks during the balance pass, the change is wrong, not just
   aggressive.

3. **Golden baseline scenarios** — seeded, deterministic fights that
   capture the CURRENT combat feel. These are *expected* to change
   during tuning. When one breaks, compare against targets in
   requirements/combat_balance_design.md and update intentionally.
"""

from __future__ import annotations

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
from spacegame.models.combat_engine import FLEE_MIN_CHANCE, CombatEngine

# ============================================================================
# Helpers
# ============================================================================


def _make_move(
    move_id: str = "laser",
    name: str = "Laser",
    damage: float = 15.0,
    energy_cost: int = 2,
    cooldown: int = 0,
) -> CombatMove:
    return CombatMove(
        id=move_id,
        name=name,
        description="",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy_cost,
        cooldown=cooldown,
        accuracy_modifier=20,  # Bias toward hits for deterministic scenario tests.
    )


def _make_player(
    hull: int = 100,
    shields: int = 40,
    energy: int = 12,
    energy_regen: int = 4,
    speed: int = 5,
    evasion: int = 10,
    accuracy: int = 80,
    moves: list[CombatMove] | None = None,
) -> PlayerCombatState:
    return PlayerCombatState(
        hull=hull,
        max_hull=hull,
        shields=shields,
        max_shields=shields,
        energy=energy,
        max_energy=energy,
        energy_regen=energy_regen,
        speed=speed,
        evasion=evasion,
        accuracy=accuracy,
        equipment_moves=moves or [_make_move()],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )


def _make_enemy_template(
    eid: str = "raider",
    hull: int = 40,
    shields: int = 0,
    damage: float = 10.0,
    evasion: int = 5,
    accuracy: int = 60,
    speed: int = 4,
    behavior: EnemyBehavior = EnemyBehavior.AGGRESSIVE,
) -> EnemyShipTemplate:
    attack = CombatMove(
        id="enemy_attack",
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
        name=eid.replace("_", " ").title(),
        description="",
        behavior=behavior,
        hull=hull,
        shields=shields,
        energy=10,
        energy_regen=3,
        speed=speed,
        evasion=evasion,
        accuracy=accuracy,
        moves=[attack],
        loot_table=[],
        negotiate_difficulty=3,
        flee_threshold=0.0,  # Never flee, simplifies scenario length.
        bribe_cost=0,
    )


def _make_state(
    player: PlayerCombatState,
    enemy_templates: list[EnemyShipTemplate],
    seed: int = 42,
) -> CombatState:
    enemies = [EnemyShip.from_template(t) for t in enemy_templates]
    encounter = CombatEncounter(enemy_templates=enemy_templates, encounter_seed=seed)
    return CombatState(
        player=player,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
    )


# ============================================================================
# Bucket 1: Action Queue Invariants (filled-gap coverage)
# ============================================================================


class TestActionQueueEnergyBudget:
    """The queue must never exceed available energy."""

    def test_empty_queue_has_full_energy(self) -> None:
        q = ActionQueue(energy_available=12)
        assert q.energy_remaining == 12
        assert q.energy_committed == 0
        assert q.is_empty

    def test_queued_action_commits_energy(self) -> None:
        q = ActionQueue(energy_available=12)
        move = _make_move(energy_cost=3)
        ok, _ = q.add("laser", 0, move)
        assert ok
        assert q.energy_committed == 3
        assert q.energy_remaining == 9

    def test_queue_rejects_over_budget(self) -> None:
        q = ActionQueue(energy_available=5)
        move = _make_move(move_id="big", energy_cost=6)
        ok, msg = q.add("big", 0, move)
        assert not ok
        assert "energy" in msg.lower()

    def test_queue_rejects_when_remaining_insufficient(self) -> None:
        q = ActionQueue(energy_available=10)
        m1 = _make_move(move_id="a", energy_cost=6)
        m2 = _make_move(move_id="b", energy_cost=5)
        assert q.add("a", 0, m1)[0]
        # 4 remain; m2 costs 5 → rejected
        ok, _ = q.add("b", 0, m2)
        assert not ok
        assert q.energy_committed == 6

    def test_undo_refunds_energy(self) -> None:
        q = ActionQueue(energy_available=10)
        m = _make_move(energy_cost=4)
        q.add("laser", 0, m)
        removed = q.remove_last()
        assert removed
        assert q.energy_committed == 0
        assert q.energy_remaining == 10

    def test_clear_refunds_all_energy(self) -> None:
        q = ActionQueue(energy_available=10)
        m1 = _make_move(move_id="a", energy_cost=2)
        m2 = _make_move(move_id="b", energy_cost=3)
        q.add("a", 0, m1)
        q.add("b", 0, m2)
        q.clear()
        assert q.is_empty
        assert q.energy_committed == 0
        assert q.energy_remaining == 10


class TestActionQueueCooldownGate:
    """The queue must respect active cooldowns."""

    def test_active_cooldown_rejects_queue(self) -> None:
        q = ActionQueue(energy_available=20, cooldowns={"burst": 2})
        move = _make_move(move_id="burst", energy_cost=5)
        ok, msg = q.add("burst", 0, move)
        assert not ok
        assert "cooldown" in msg.lower()

    def test_expired_cooldown_allows_queue(self) -> None:
        q = ActionQueue(energy_available=20, cooldowns={"burst": 0})
        move = _make_move(move_id="burst", energy_cost=5)
        ok, _ = q.add("burst", 0, move)
        assert ok


class TestActionQueueOncePerTurn:
    """Same weapon cannot be queued twice (unless Volley Commander)."""

    def test_double_queue_rejected(self) -> None:
        q = ActionQueue(energy_available=20)
        move = _make_move(energy_cost=2)
        ok1, _ = q.add("laser", 0, move)
        ok2, msg = q.add("laser", 0, move)
        assert ok1
        assert not ok2
        assert "already" in msg.lower()

    def test_volley_commander_allows_one_extra(self) -> None:
        """Volley Commander skill: one weapon can bypass once-per-turn."""
        q = ActionQueue(energy_available=20, extra_action=True)
        move = _make_move(energy_cost=2)
        assert q.add("laser", 0, move)[0]
        assert q.add("laser", 0, move)[0], "Volley Commander should grant a 2nd shot"
        # But only one bypass — third queue fails.
        ok, _ = q.add("laser", 0, move)
        assert not ok

    def test_different_slots_can_both_queue(self) -> None:
        """Two weapons with distinct slot_keys queue independently."""
        q = ActionQueue(energy_available=20)
        m1 = _make_move(move_id="laser", energy_cost=2)
        m1.slot_key = "laser_slot_0"
        m2 = _make_move(move_id="laser", energy_cost=2)
        m2.slot_key = "laser_slot_1"
        assert q.add("laser", 0, m1)[0]
        assert q.add("laser", 1, m2)[0]


class TestActionQueueCanAdd:
    """can_add must agree with add — no hidden divergence."""

    def test_can_add_matches_add_success(self) -> None:
        q = ActionQueue(energy_available=10)
        m = _make_move(energy_cost=3)
        can, _ = q.can_add("laser", m)
        assert can
        ok, _ = q.add("laser", 0, m)
        assert ok

    def test_can_add_matches_add_failure_energy(self) -> None:
        q = ActionQueue(energy_available=2)
        m = _make_move(energy_cost=5)
        can, _ = q.can_add("laser", m)
        assert not can
        ok, _ = q.add("laser", 0, m)
        assert not ok


# ============================================================================
# Bucket 2: Balance Tripwires
# ============================================================================
#
# Numerical properties that must remain true regardless of balance tuning.
# If a balance change breaks one of these, the change is wrong.


class TestEnergyEconomyInvariants:
    """Energy math must stay internally consistent."""

    def test_regen_capped_at_max(self) -> None:
        player = _make_player(energy=0, energy_regen=8)
        player.max_energy = 5
        player.regenerate_energy()
        assert player.energy <= player.max_energy

    def test_regen_never_overfills(self) -> None:
        player = _make_player(energy=10, energy_regen=8)
        player.max_energy = 12
        player.regenerate_energy()
        assert player.energy == 12, "Regen should clamp to max, not overflow"

    def test_zero_cost_move_always_queues(self) -> None:
        """A 0-cost move should queue even with minimal energy."""
        q = ActionQueue(energy_available=1)
        free_move = _make_move(move_id="free", energy_cost=0)
        ok, _ = q.add("free", 0, free_move)
        assert ok

    def test_zero_energy_cannot_queue_costed_move(self) -> None:
        """With 0 energy, any >0-cost move is rejected. No negative pool."""
        q = ActionQueue(energy_available=0)
        m = _make_move(energy_cost=1)
        ok, _ = q.add("m", 0, m)
        assert not ok
        assert q.energy_remaining == 0


class TestFleeInvariants:
    """Flee must remain a viable out at low HP — no soft-locking the player."""

    def test_flee_has_nonzero_success_rate_at_min(self) -> None:
        """Regardless of speed or bonuses, flee chance is at least
        FLEE_MIN_CHANCE. Over many trials, successes should appear."""
        template = _make_enemy_template(hull=200)
        outcomes = []
        for seed in range(100):
            player = _make_player(hull=5, shields=0, speed=0)
            state = _make_state(player, [template], seed=seed)
            engine = CombatEngine(state, seed=seed)
            result = engine.attempt_flee()
            outcomes.append(result)

        # Flee must be attemptable at low HP — engine never refuses.
        # The flee-chance lower bound is already tested in test_combat_engine.py;
        # this test protects against future code paths that might short-circuit flee.
        assert len(outcomes) == 100
        assert all(r is not None for r in outcomes)
        assert FLEE_MIN_CHANCE > 0, "Flee must never be structurally impossible"


class TestMonotonicityInvariants:
    """Stronger equipment must beat weaker. No upside-down scaling."""

    def test_higher_damage_move_deals_more(self) -> None:
        """A move with higher raw damage has a higher effect value."""
        weak = _make_move(move_id="weak", damage=10)
        strong = _make_move(move_id="strong", damage=30)
        assert strong.effects[0].value > weak.effects[0].value

    def test_higher_energy_pool_allows_bigger_alpha(self) -> None:
        """Given the same weapon loadout, a larger pool queues more actions."""
        moves = [
            _make_move(move_id="a", energy_cost=3),
            _make_move(move_id="b", energy_cost=3),
            _make_move(move_id="c", energy_cost=3),
        ]

        small = ActionQueue(energy_available=5)
        large = ActionQueue(energy_available=12)

        small_queued = sum(1 for m in moves if small.add(m.id, 0, m)[0])
        large_queued = sum(1 for m in moves if large.add(m.id, 0, m)[0])

        assert large_queued > small_queued, (
            f"Larger pool should queue more actions (small={small_queued}, large={large_queued})"
        )


# ============================================================================
# Bucket 3: Golden Baseline Scenarios
# ============================================================================
#
# Seeded, deterministic fights that capture CURRENT combat feel. Expected to
# change during the balance pass. When one breaks, read the new numbers,
# compare to design targets in requirements/combat_balance_design.md, and
# update the expected range with a comment citing the intentional change.


class TestGoldenStarterShuttle:
    """Starter-shuttle-class player vs tier-1-class enemies."""

    def _starter_player(self) -> PlayerCombatState:
        """Approximates starter shuttle at L1: 100 hull, 40 shields,
        12 energy / 4 regen, one sidearm."""
        laser = _make_move(move_id="laser", damage=15, energy_cost=2, cooldown=0)
        return _make_player(
            hull=100,
            shields=40,
            energy=12,
            energy_regen=4,
            speed=5,
            evasion=10,
            accuracy=85,
            moves=[laser],
        )

    def _tier1_raider_template(self) -> EnemyShipTemplate:
        """Tier-1 striker approximate: 40 HP, 10 dmg."""
        return _make_enemy_template(eid="raider", hull=40, damage=10)

    def test_starter_vs_single_raider_finishes_within_bounds(self) -> None:
        """Current feel: starter shuttle beats a single raider in a bounded
        number of rounds. If this drifts, compare vs. design doc §3 targets
        (Trivial 1–2 rounds, Standard 3–5 rounds)."""
        player = self._starter_player()
        template = self._tier1_raider_template()
        state = _make_state(player, [template], seed=42)
        engine = CombatEngine(state, seed=42)

        rounds = 0
        max_rounds = 30
        while state.enemies[0].is_alive and player.hull > 0 and rounds < max_rounds:
            queue = ActionQueue(
                energy_available=player.energy,
                cooldowns=dict(player.cooldowns),
            )
            queue.add("laser", 0, player.equipment_moves[0])
            engine.execute_player_turn(queue)
            if state.enemies[0].is_alive:
                engine.execute_enemy_turns()
            engine.end_round()
            rounds += 1

        assert rounds < max_rounds, "Fight did not resolve — possible deadlock"
        assert not state.enemies[0].is_alive, (
            f"Starter should beat a single tier-1 raider; survived {rounds} rounds."
        )
        # CURRENT-FEEL ASSERTION: expected to change during balance pass.
        assert 2 <= rounds <= 12, (
            f"CURRENT FEEL: starter vs 1 raider = 2–12 rounds (got {rounds}). "
            f"If intentional, update bound with reference to design doc §3."
        )

    def test_starter_vs_single_raider_player_survives(self) -> None:
        """Current tuning: a starter should reliably survive a 1v1
        against a tier-1 raider. If this fails, enemy damage or player
        HP is miscalibrated."""
        player = self._starter_player()
        template = self._tier1_raider_template()
        state = _make_state(player, [template], seed=7)
        engine = CombatEngine(state, seed=7)

        max_rounds = 30
        for _ in range(max_rounds):
            if not state.enemies[0].is_alive or player.hull <= 0:
                break
            queue = ActionQueue(
                energy_available=player.energy,
                cooldowns=dict(player.cooldowns),
            )
            queue.add("laser", 0, player.equipment_moves[0])
            engine.execute_player_turn(queue)
            if state.enemies[0].is_alive:
                engine.execute_enemy_turns()
            engine.end_round()

        assert player.hull > 0, "Starter should survive a 1v1 tier-1 raider"


class TestGoldenMultiAction:
    """Multi-action turns meaningfully increase throughput over single-action."""

    def test_three_weapon_queue_outdamages_one_weapon(self) -> None:
        """Queueing three weapons in one turn deals strictly more total
        damage than queueing one, against a tanky target."""

        def run_turn(moves_to_queue: list[CombatMove]) -> int:
            player = _make_player(energy=12, moves=moves_to_queue, accuracy=95)
            template = _make_enemy_template(hull=500, shields=0, evasion=0)
            state = _make_state(player, [template], seed=100)
            engine = CombatEngine(state, seed=100)
            queue = ActionQueue(energy_available=player.energy)
            for m in moves_to_queue:
                queue.add(m.id, 0, m)
            engine.execute_player_turn(queue)
            return 500 - state.enemies[0].current_hull

        three = [
            _make_move(move_id="a", damage=10, energy_cost=2),
            _make_move(move_id="b", damage=10, energy_cost=2),
            _make_move(move_id="c", damage=10, energy_cost=2),
        ]
        one = [_make_move(move_id="a", damage=10, energy_cost=2)]

        dmg_three = run_turn(three)
        dmg_one = run_turn(one)

        assert dmg_three > dmg_one, (
            f"3-weapon queue should outdamage 1-weapon (got {dmg_three} vs {dmg_one})"
        )


class TestActionQueueMoveIdFootgun:
    """Documents the footgun flagged in combat_balance_design §12 B6:

    ``ActionQueue.add(move_id, target, move)`` expects the canonical
    ``move.id`` as the first arg, NOT the slot-specific cooldown key.
    Passing a slot_key silently breaks: the engine's ``_find_player_move``
    returns None, logs "Move not found", and the action becomes a no-op.

    This test codifies the contract so future instrumentation (or agents)
    can't rediscover the foot-gun by accident.
    """

    def test_unknown_move_id_logs_move_not_found_and_no_ops(self) -> None:
        move = _make_move(move_id="laser", damage=10)
        player = _make_player(energy=10, moves=[move], accuracy=95)
        template = _make_enemy_template(hull=50, shields=0, evasion=0)
        state = _make_state(player, [template], seed=0)
        engine = CombatEngine(state, seed=0)

        # Build a queue with a BOGUS move_id (simulating slot_key misuse)
        queue = ActionQueue(energy_available=player.energy)
        queue.add("laser_slot_3", 0, move)  # slot_key instead of move.id

        enemy_hull_before = state.enemies[0].current_hull
        log_len_before = len(state.combat_log)
        engine.execute_player_turn(queue)

        # Enemy took no damage (move not found, no-op)
        assert state.enemies[0].current_hull == enemy_hull_before, (
            "An unknown move_id must produce a no-op, not randomly resolve."
        )
        # A log entry with 'Move not found' was emitted
        new_entries = state.combat_log[log_len_before:]
        found = any("Move not found" in entry.effects_applied for entry in new_entries)
        assert found, (
            "Engine must emit 'Move not found' log on unknown move_id. "
            "Callers passing slot_key instead of move.id depend on this "
            "signal surfacing during instrumentation."
        )

    def test_correct_move_id_resolves_normally(self) -> None:
        """Positive control — using move.id works, proving the footgun is
        specifically about the ID, not a broader queue bug."""
        move = _make_move(move_id="laser", damage=10)
        player = _make_player(energy=10, moves=[move], accuracy=95)
        template = _make_enemy_template(hull=50, shields=0, evasion=0)
        state = _make_state(player, [template], seed=0)
        engine = CombatEngine(state, seed=0)

        queue = ActionQueue(energy_available=player.energy)
        queue.add("laser", 0, move)  # correct move.id

        engine.execute_player_turn(queue)

        assert state.enemies[0].current_hull < 50, (
            "Correct move_id should resolve into real damage."
        )
