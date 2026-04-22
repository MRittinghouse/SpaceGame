"""
Phase B8.3 — Engine integration tests for the remaining dual tech hooks.

Covers the three pieces that need combat-engine plumbing beyond what
B8.2 shipped:

1. Total Commitment — next 3 incoming hull hits convert to armor
   (capped at +8), then the tech disarms.
2. Daring Gambit counter-on-dodge — when the player dodges an enemy
   attack during the 2-turn window, 25 damage returns to the attacker.
3. Crew Sync armor-pierce — for the activation turn, the player's
   attacks bypass defender armor.

Also verifies the end-of-round cleanup: armor_pierce_active clears,
daring_gambit_turns counter decrements.
"""

from __future__ import annotations

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
from spacegame.models.dual_tech import (
    TOTAL_COMMITMENT_ARMOR_CAP,
    TOTAL_COMMITMENT_ARMOR_PER_HIT,
    TOTAL_COMMITMENT_HITS,
    build_crew_sync_move,
    build_daring_gambit_move,
    build_total_commitment_move,
)

# ============================================================================
# Helpers
# ============================================================================


def _weapon(
    wid: str = "laser",
    damage: float = 20.0,
    energy: int = 2,
    cooldown: int = 0,
) -> CombatMove:
    return CombatMove(
        id=wid,
        name=wid.title(),
        description="",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy,
        cooldown=cooldown,
        accuracy_modifier=50,
    )


def _player(
    *,
    hull: int = 200,
    max_hull: int = 200,
    shields: int = 0,
    armor: int = 0,
    energy: int = 30,
    evasion: int = 0,
    accuracy: int = 95,
    equipment_moves: list[CombatMove] | None = None,
) -> PlayerCombatState:
    return PlayerCombatState(
        hull=hull,
        max_hull=max_hull,
        shields=shields,
        max_shields=shields,
        energy=energy,
        max_energy=energy,
        energy_regen=5,
        speed=6,
        evasion=evasion,
        accuracy=accuracy,
        equipment_moves=equipment_moves or [],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
        armor=armor,
    )


def _enemy_template(
    eid: str = "dummy",
    hull: int = 500,
    armor: int = 5,
    damage: float = 20.0,
    accuracy: int = 95,
) -> EnemyShipTemplate:
    attack = CombatMove(
        id="bite",
        name="Bite",
        description="",
        effects=[
            CombatEffect(
                type=EffectType.DAMAGE,
                value=damage,
                target=EffectTarget.ENEMY,
            )
        ],
        energy_cost=0,
        accuracy_modifier=50,
    )
    return EnemyShipTemplate(
        id=eid,
        name=eid.title(),
        description="",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull,
        shields=0,
        energy=10,
        energy_regen=3,
        speed=4,
        evasion=0,
        accuracy=accuracy,
        moves=[attack],
        loot_table=[],
        flee_threshold=0.0,
        combat_armor=armor,
    )


def _build(
    player: PlayerCombatState, templates: list[EnemyShipTemplate], seed: int = 0
) -> tuple[CombatState, CombatEngine]:
    enemies = [EnemyShip.from_template(t) for t in templates]
    encounter = CombatEncounter(enemy_templates=templates, encounter_seed=seed)
    state = CombatState(
        player=player, enemies=enemies, encounter=encounter, combat_log=[]
    )
    return state, CombatEngine(state, seed=seed)


def _fire(engine: CombatEngine, move: CombatMove, target_idx: int = 0) -> list:
    player = engine._state.player
    if move not in player.equipment_moves:
        player.equipment_moves.append(move)
    return engine.execute_player_move(move.id, target_idx)


# ============================================================================
# Total Commitment — hull-hit interception
# ============================================================================


class TestTotalCommitmentExecution:
    def test_activation_primes_three_hits(self) -> None:
        player = _player()
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_total_commitment_move())
        assert player.total_commitment_hits_remaining == TOTAL_COMMITMENT_HITS
        assert player.total_commitment_armor_gained == 0

    def test_first_hull_hit_converts_to_armor(self) -> None:
        player = _player(hull=200, armor=2)  # Small starting armor
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_total_commitment_move())

        armor_before = player.armor
        hull_before = player.hull
        # Enemy takes a swing.
        engine.execute_enemy_turns()
        # Hit should be absorbed — hull unchanged, armor increased.
        assert player.hull == hull_before, "hull should not decrease during TC absorb"
        assert player.armor > armor_before, "armor should increase from the absorb"
        assert player.total_commitment_hits_remaining == TOTAL_COMMITMENT_HITS - 1

    def test_absorbs_exactly_three_hits(self) -> None:
        player = _player(hull=500, armor=0)
        _state, engine = _build(player, [_enemy_template(hull=1000, damage=10)])
        _fire(engine, build_total_commitment_move())

        hull_before = player.hull
        # Four enemy rounds → three absorbs + one real hit.
        for _ in range(4):
            engine.execute_enemy_turns()

        assert player.total_commitment_hits_remaining == 0
        # Three hits absorbed, fourth landed — some hull damage should
        # have taken through by the 4th hit.
        assert player.hull < hull_before, (
            "Hit #4 should land normally after the tech disarms"
        )

    def test_armor_gained_caps_at_eight(self) -> None:
        """Per-hit armor gain is {TOTAL_COMMITMENT_ARMOR_PER_HIT}, cap {cap}.
        Across 3 hits, total cannot exceed the cap."""
        player = _player(hull=500, armor=0)
        _state, engine = _build(player, [_enemy_template(damage=5)])
        _fire(engine, build_total_commitment_move())
        for _ in range(TOTAL_COMMITMENT_HITS):
            engine.execute_enemy_turns()
        # Armor gain should reflect 3 × per_hit, capped at cap.
        expected = min(
            TOTAL_COMMITMENT_HITS * TOTAL_COMMITMENT_ARMOR_PER_HIT,
            TOTAL_COMMITMENT_ARMOR_CAP,
        )
        assert player.total_commitment_armor_gained == expected


# ============================================================================
# Daring Gambit — counter-on-dodge
# ============================================================================


class TestDaringGambitCounter:
    def test_activation_arms_counter_window(self) -> None:
        player = _player()
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_daring_gambit_move())
        assert player.daring_gambit_turns == 2

    def test_counter_fires_on_clean_miss(self) -> None:
        """High player evasion + enemy attack → clean miss. Counter
        should return 25 damage to the attacker."""
        # Player with very high evasion guarantees misses.
        player = _player(evasion=200)
        _state, engine = _build(player, [_enemy_template(hull=300, armor=0)])
        _fire(engine, build_daring_gambit_move())

        enemy = _state.enemies[0]
        hull_before = enemy.current_hull
        engine.execute_enemy_turns()
        # At minimum one miss should occur across the tries; counter
        # should have fired.
        assert enemy.current_hull <= hull_before - 20, (
            f"Expected counter to deal ≥20 dmg; enemy hull went "
            f"{hull_before} → {enemy.current_hull}"
        )

    def test_counter_does_not_fire_when_window_expired(self) -> None:
        """After 2 end_round ticks, daring_gambit_turns == 0. Counter
        should not fire on subsequent dodges."""
        player = _player(evasion=200)
        _state, engine = _build(player, [_enemy_template(hull=300, armor=0)])
        _fire(engine, build_daring_gambit_move())

        # Tick 2 rounds to expire the window.
        engine.end_round()
        engine.end_round()
        assert player.daring_gambit_turns == 0

        enemy = _state.enemies[0]
        hull_before = enemy.current_hull
        # Enemy attacks, player dodges, NO counter should fire.
        engine.execute_enemy_turns()
        assert enemy.current_hull == hull_before, (
            f"Counter should not fire after window expired; "
            f"enemy hull went {hull_before} → {enemy.current_hull}"
        )


# ============================================================================
# Crew Sync — armor-pierce on player attacks
# ============================================================================


class TestCrewSyncArmorPierce:
    def test_activation_sets_armor_pierce_flag(self) -> None:
        player = _player(max_hull=200)
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_crew_sync_move())
        assert player.armor_pierce_active is True

    def test_player_attack_bypasses_enemy_armor(self) -> None:
        """With armor_pierce active, a player weapon hit against an
        armored enemy should deal its full raw damage (minus shield
        absorption, but no armor reduction)."""
        laser = _weapon("laser", damage=20, energy=2, cooldown=0)
        player = _player(equipment_moves=[laser], energy=30)
        _state, engine = _build(player, [_enemy_template(hull=500, armor=10)])
        _fire(engine, build_crew_sync_move())

        enemy = _state.enemies[0]
        hull_before = enemy.current_hull
        _fire(engine, laser)
        # Without armor pierce: 20 - 10 armor = 10 damage.
        # With armor pierce: full 20 damage.
        damage_dealt = hull_before - enemy.current_hull
        assert damage_dealt >= 18, (
            f"Armor pierce should let ≥18 of 20 damage through; got {damage_dealt}"
        )

    def test_armor_pierce_clears_at_end_of_round(self) -> None:
        player = _player(max_hull=200)
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_crew_sync_move())
        assert player.armor_pierce_active is True
        engine.end_round()
        assert player.armor_pierce_active is False

    def test_subsequent_turns_do_not_pierce(self) -> None:
        """After armor_pierce clears, subsequent player weapons hit
        normal armor."""
        laser = _weapon("laser", damage=20, energy=2, cooldown=0)
        player = _player(equipment_moves=[laser], energy=30, max_hull=200)
        _state, engine = _build(player, [_enemy_template(hull=500, armor=10)])
        _fire(engine, build_crew_sync_move())
        engine.end_round()  # Clears armor_pierce_active.

        enemy = _state.enemies[0]
        hull_before = enemy.current_hull
        _fire(engine, laser)
        # Back to normal: 20 - 10 armor = 10 damage.
        damage_dealt = hull_before - enemy.current_hull
        assert damage_dealt <= 11, (
            f"After pierce expires, armor should reduce damage; got {damage_dealt}"
        )


# ============================================================================
# End-of-round cleanup
# ============================================================================


class TestEndOfRoundCleanup:
    def test_daring_gambit_turns_decrements_each_round(self) -> None:
        player = _player()
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_daring_gambit_move())
        assert player.daring_gambit_turns == 2
        engine.end_round()
        assert player.daring_gambit_turns == 1
        engine.end_round()
        assert player.daring_gambit_turns == 0

    def test_daring_gambit_turns_does_not_go_negative(self) -> None:
        player = _player()
        _state, engine = _build(player, [_enemy_template()])
        _fire(engine, build_daring_gambit_move())
        for _ in range(5):
            engine.end_round()
        assert player.daring_gambit_turns == 0
