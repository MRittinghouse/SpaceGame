"""
Phase B8.2 — End-to-end execution tests for the 4 newly-wired dual techs.

Verifies that Power Drift, Fire at Will, Daring Gambit, and Crew Sync
activate correctly when queued through the combat engine:

- Power Drift adds 6 energy and shaves 2 from every active cooldown.
- Fire at Will halves energy cost on subsequent weapons in the same
  turn AND prevents those weapons from entering cooldown.
- Daring Gambit grants +40 evasion for 2 turns via the active-effect
  pipeline (counter-on-dodge is B8.3).
- Crew Sync heals 40% of max hull, grants self-buffs, and blocks
  re-activation for the rest of combat.

Total Commitment execution is deferred to B8.3 — not tested here.
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
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.dual_tech import (
    build_crew_sync_move,
    build_daring_gambit_move,
    build_fire_at_will_move,
    build_power_drift_move,
)

# ============================================================================
# Helpers
# ============================================================================


def _weapon(
    wid: str = "laser",
    damage: float = 20.0,
    energy: int = 4,
    cooldown: int = 2,
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
    equipment_moves: list[CombatMove] | None = None,
    hull: int = 200,
    max_hull: int = 200,
    energy: int = 30,
    max_energy: int = 30,
    cooldowns: dict[str, int] | None = None,
) -> PlayerCombatState:
    return PlayerCombatState(
        hull=hull,
        max_hull=max_hull,
        shields=40,
        max_shields=40,
        energy=energy,
        max_energy=max_energy,
        energy_regen=5,
        speed=6,
        evasion=10,
        accuracy=95,
        equipment_moves=equipment_moves or [],
        crew_moves=[],
        active_effects=[],
        cooldowns=cooldowns or {},
    )


def _sponge_enemy() -> tuple[list[EnemyShip], list[EnemyShipTemplate]]:
    attack = CombatMove(
        id="bite",
        name="Bite",
        description="",
        effects=[
            CombatEffect(
                type=EffectType.DAMAGE,
                value=5.0,
                target=EffectTarget.ENEMY,
            )
        ],
        energy_cost=0,
    )
    t = EnemyShipTemplate(
        id="sponge",
        name="Sponge",
        description="",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=10_000,
        shields=0,
        energy=10,
        energy_regen=3,
        speed=1,
        evasion=0,
        accuracy=50,
        moves=[attack],
        loot_table=[],
        flee_threshold=0.0,
    )
    return [EnemyShip.from_template(t)], [t]


def _run_move(
    engine: CombatEngine,
    move: CombatMove,
    target_idx: int = 0,
) -> list:
    """Add a single move to the player's equipment_moves (so it's findable
    by _find_player_move), then invoke the engine."""
    player = engine._state.player
    if move not in player.equipment_moves:
        player.equipment_moves.append(move)
    return engine.execute_player_move(move.id, target_idx)


def _new_engine(
    player: PlayerCombatState,
    seed: int = 0,
) -> CombatEngine:
    enemies, templates = _sponge_enemy()
    encounter = CombatEncounter(enemy_templates=templates, encounter_seed=seed)
    state = CombatState(player=player, enemies=enemies, encounter=encounter, combat_log=[])
    return CombatEngine(state, seed=seed)


# ============================================================================
# Power Drift — +6 energy, -2 on all cooldowns
# ============================================================================


class TestPowerDriftExecution:
    def test_power_drift_adds_six_energy(self) -> None:
        player = _player(energy=8, max_energy=30)
        engine = _new_engine(player)
        move = build_power_drift_move()
        _run_move(engine, move)
        # Spent 4E (cost), gained 6E (activation) → net +2.
        assert player.energy == 8 - 4 + 6 == 10

    def test_power_drift_caps_energy_at_max(self) -> None:
        player = _player(energy=28, max_energy=30)
        engine = _new_engine(player)
        move = build_power_drift_move()
        _run_move(engine, move)
        # Spent 4E → 24. +6 → would be 30 (max). Clamp check.
        assert player.energy == 30

    def test_power_drift_reduces_all_cooldowns_by_2(self) -> None:
        player = _player(cooldowns={"weapon_a": 3, "weapon_b": 2, "weapon_c": 1})
        engine = _new_engine(player)
        move = build_power_drift_move()
        _run_move(engine, move)
        # Weapon cooldowns reduced by 2 (excluding Power Drift's own entry,
        # which is 4 by design).
        assert player.cooldowns["weapon_a"] == 1
        assert player.cooldowns["weapon_b"] == 0
        assert player.cooldowns["weapon_c"] == 0
        assert player.cooldowns["power_drift"] == 4

    def test_power_drift_does_not_drive_cooldowns_negative(self) -> None:
        player = _player(cooldowns={"x": 1})
        engine = _new_engine(player)
        _run_move(engine, build_power_drift_move())
        assert player.cooldowns["x"] == 0

    def test_power_drift_sets_its_own_cooldown(self) -> None:
        player = _player()
        engine = _new_engine(player)
        move = build_power_drift_move()
        _run_move(engine, move)
        # Power Drift itself gets a 4-round cooldown.
        assert player.cooldowns.get("power_drift") == 4


# ============================================================================
# Fire at Will — half-energy weapons this turn, no cooldown aftermath
# ============================================================================


class TestFireAtWillExecution:
    def test_fire_at_will_sets_flag_on_activation(self) -> None:
        player = _player()
        engine = _new_engine(player)
        _run_move(engine, build_fire_at_will_move())
        assert player.fire_at_will_active is True

    def test_fire_at_will_halves_weapon_energy_cost(self) -> None:
        laser = _weapon("laser", damage=20, energy=4, cooldown=2)
        player = _player(equipment_moves=[laser], energy=20)
        engine = _new_engine(player)
        _run_move(engine, build_fire_at_will_move())
        # Flag now active. Fire weapon — cost should halve (4 → 2).
        pre_energy = player.energy
        _run_move(engine, laser)
        assert player.energy == pre_energy - 2, (
            f"Weapon energy cost should halve under Fire at Will "
            f"(expected {pre_energy - 2}, got {player.energy})"
        )

    def test_fire_at_will_skips_weapon_cooldown(self) -> None:
        """Weapons fired while FAW is active don't go on cooldown."""
        laser = _weapon("laser", damage=20, energy=4, cooldown=3)
        player = _player(equipment_moves=[laser])
        engine = _new_engine(player)
        _run_move(engine, build_fire_at_will_move())
        _run_move(engine, laser)
        # Laser cooldown should NOT be set.
        assert "laser" not in player.cooldowns

    def test_fire_at_will_flag_clears_after_turn(self) -> None:
        """execute_player_turn clears the flag after the action queue
        resolves so the discount doesn't leak into the next turn."""
        laser = _weapon("laser", damage=20, energy=4, cooldown=2)
        player = _player(equipment_moves=[laser], energy=20)
        engine = _new_engine(player)

        queue = ActionQueue(energy_available=player.energy)
        faw = build_fire_at_will_move()
        player.equipment_moves.append(faw)
        queue.add(faw.id, 0, faw)
        queue.add(laser.id, 0, laser)
        engine.execute_player_turn(queue)
        assert player.fire_at_will_active is False

    def test_fire_at_will_does_not_discount_non_weapon_moves(self) -> None:
        """A shield_restore (non-damage) move should pay full cost."""
        shield = CombatMove(
            id="shield",
            name="Shield",
            description="",
            effects=[
                CombatEffect(
                    type=EffectType.SHIELD_RESTORE,
                    value=10.0,
                    target=EffectTarget.SELF,
                )
            ],
            energy_cost=4,
            cooldown=1,
        )
        player = _player(equipment_moves=[shield], energy=20)
        engine = _new_engine(player)
        _run_move(engine, build_fire_at_will_move())
        pre_energy = player.energy
        _run_move(engine, shield)
        # Full cost (4) should be paid.
        assert player.energy == pre_energy - 4


# ============================================================================
# Daring Gambit — +40 evasion for 2 turns
# ============================================================================


class TestDaringGambitExecution:
    def test_daring_gambit_grants_two_turn_evasion_buff(self) -> None:
        player = _player()
        engine = _new_engine(player)
        _run_move(engine, build_daring_gambit_move())
        # Evasion buff should be in active_effects with duration 2.
        evasion_effects = [
            (eff, dur)
            for (eff, dur) in player.active_effects
            if eff.type == EffectType.EVASION_MOD and eff.value == 40.0
        ]
        assert len(evasion_effects) == 1, f"Expected one EVASION_MOD +40; got {evasion_effects}"
        _eff, duration = evasion_effects[0]
        assert duration == 2

    def test_daring_gambit_evasion_adds_to_effective_evasion(self) -> None:
        player = _player()
        engine = _new_engine(player)
        baseline = player.get_effective_evasion()
        _run_move(engine, build_daring_gambit_move())
        buffed = player.get_effective_evasion()
        assert buffed == baseline + 40


# ============================================================================
# Crew Sync — once per combat, heals, self-buffs
# ============================================================================


class TestCrewSyncExecution:
    def test_crew_sync_heals_forty_percent_of_max_hull(self) -> None:
        player = _player(hull=50, max_hull=200)
        engine = _new_engine(player)
        _run_move(engine, build_crew_sync_move())
        # +40% of 200 = 80 hull restored.
        assert player.hull == 50 + 80

    def test_crew_sync_hull_restore_does_not_exceed_max(self) -> None:
        player = _player(hull=180, max_hull=200)
        engine = _new_engine(player)
        _run_move(engine, build_crew_sync_move())
        assert player.hull == 200

    def test_crew_sync_sets_used_flag(self) -> None:
        player = _player()
        engine = _new_engine(player)
        _run_move(engine, build_crew_sync_move())
        assert player.crew_sync_used is True

    def test_crew_sync_cannot_fire_twice_in_one_combat(self) -> None:
        player = _player(energy=30, max_energy=30)
        engine = _new_engine(player)
        move = build_crew_sync_move()
        _run_move(engine, move)

        energy_before_second = player.energy
        logs = _run_move(engine, move)
        # Second activation rejected — energy unchanged.
        assert player.energy == energy_before_second
        assert any("already used" in "".join(e.effects_applied).lower() for e in logs)

    def test_crew_sync_applies_evasion_and_damage_boost(self) -> None:
        player = _player()
        engine = _new_engine(player)
        _run_move(engine, build_crew_sync_move())
        eff_types = [(eff.type, eff.value) for (eff, _dur) in player.active_effects]
        assert (EffectType.EVASION_MOD, 4.0) in eff_types
        assert (EffectType.DAMAGE_BOOST, 100.0) in eff_types
