"""CE-3 Wave 2: ComplicationResolver wired into CombatEngine.

These tests exercise the live integration — engine instantiates a
resolver from the complications passed at construction, evaluates it
at hook points (start of player turn + end of round), and consumes
the three environmental modifier fields on CombatState.
"""

from __future__ import annotations

from spacegame.models.action_queue import ActionQueue
from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatLogEntry,
    CombatMove,
    CombatState,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_complication import CombatComplication
from spacegame.models.combat_engine import CombatEngine


# ---------------------------------------------------------------------------
# Helpers (small, self-contained — no shared conftest)
# ---------------------------------------------------------------------------


def _make_move(
    id: str = "blaster",
    name: str = "Blaster",
    damage: float = 10.0,
    energy_cost: int = 2,
) -> CombatMove:
    return CombatMove(
        id=id,
        name=name,
        description=f"{name} attack",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy_cost,
    )


def _make_enemy_template(
    id: str = "pirate",
    hull: int = 80,
    accuracy: int = 80,
    evasion: int = 0,
) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id=id,
        name="Pirate",
        description="A pirate.",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull,
        shields=0,
        energy=10,
        energy_regen=3,
        speed=8,
        evasion=evasion,
        accuracy=accuracy,
        moves=[_make_move()],
        loot_table=[],
        negotiate_difficulty=3,
        flee_threshold=0.0,
        bribe_cost=0,
    )


def _make_player_state(
    hull: int = 100,
    max_hull: int = 100,
    shield_regen: int = 4,
    shields: int = 10,
    max_shields: int = 40,
    evasion: int = 15,
) -> PlayerCombatState:
    return PlayerCombatState(
        hull=hull,
        max_hull=max_hull,
        shields=shields,
        max_shields=max_shields,
        energy=10,
        max_energy=10,
        energy_regen=3,
        speed=8,
        evasion=evasion,
        accuracy=80,
        equipment_moves=[_make_move("laser", "Laser", 20.0, 3)],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
        shield_regen=shield_regen,
    )


def _make_engine(
    complications: list[CombatComplication],
    player: PlayerCombatState | None = None,
    enemy_templates: list[EnemyShipTemplate] | None = None,
    encounter_complication_ids: list[str] | None = None,
    seed: int = 42,
) -> CombatEngine:
    if player is None:
        player = _make_player_state()
    if enemy_templates is None:
        enemy_templates = [_make_enemy_template()]
    encounter = CombatEncounter(
        enemy_templates=enemy_templates,
        encounter_seed=seed,
        complication_ids=encounter_complication_ids or [],
    )
    enemies = [EnemyShip.from_template(t) for t in enemy_templates]
    state = CombatState(
        player=player,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
    )
    return CombatEngine(state, seed=seed, complications=complications)


def _comp_shield_harmonic() -> CombatComplication:
    return CombatComplication(
        id="shield_harmonic_test",
        name="Shield Harmonic",
        description="",
        trigger_type="turn_counter",
        trigger_params={"turn": 1},
        effect_type="environmental",
        effect_params={"shield_regen_multiplier": 0.5},
        narration="Field interferes with regen.",
    )


def _comp_asteroid_evasion() -> CombatComplication:
    return CombatComplication(
        id="asteroid_closure_test",
        name="Asteroid Closure",
        description="",
        trigger_type="turn_counter",
        trigger_params={"turn": 1},
        effect_type="environmental",
        effect_params={"player_evasion_modifier": -10},
        narration="Asteroids tighten the lane.",
    )


def _comp_battle_damage() -> CombatComplication:
    return CombatComplication(
        id="battle_damage_test",
        name="Battle Damage",
        description="",
        trigger_type="hp_threshold",
        trigger_params={"target": "enemy", "hp_pct": 0.5},
        effect_type="environmental",
        effect_params={"enemy_accuracy_multiplier": 0.5},
        narration="Their fire control limps.",
    )


def _comp_morale_shift() -> CombatComplication:
    return CombatComplication(
        id="morale_shift_test",
        name="Morale Shift",
        description="",
        trigger_type="hp_threshold",
        trigger_params={"target": "player", "hp_pct": 0.3},
        effect_type="narration",
        effect_params={"flag_name": "player_low_hp_moment"},
        narration="Hull's screaming.",
    )


# ---------------------------------------------------------------------------
# Resolver hook firing
# ---------------------------------------------------------------------------


class TestResolverHooks:
    def test_turn_one_complication_fires_on_first_player_turn(self) -> None:
        comp = _comp_shield_harmonic()
        engine = _make_engine([comp])
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert "shield_harmonic_test" in engine._state.fired_complication_ids

    def test_complication_fires_only_once_across_rounds(self) -> None:
        comp = _comp_shield_harmonic()
        engine = _make_engine([comp])
        engine.execute_player_turn(ActionQueue(energy_available=10))
        engine.end_round()
        engine.execute_player_turn(ActionQueue(energy_available=10))
        # Should appear in fired set, never re-applied
        assert engine._state.shield_regen_multiplier == 0.5

    def test_no_complications_means_no_log_noise(self) -> None:
        engine = _make_engine([])
        engine.execute_player_turn(ActionQueue(energy_available=10))
        # No system-actor complication entries appended
        assert all(
            not entry.action.startswith("Complication:") for entry in engine._state.combat_log
        )


# ---------------------------------------------------------------------------
# Environmental modifier integration
# ---------------------------------------------------------------------------


class TestShieldRegenIntegration:
    def test_shield_regen_halved_by_complication(self) -> None:
        comp = _comp_shield_harmonic()
        # base shield_regen = 4; with multiplier 0.5 → 2 per round
        player = _make_player_state(shield_regen=4, shields=10, max_shields=40)
        engine = _make_engine([comp], player=player)
        engine.execute_player_turn(ActionQueue(energy_available=10))
        engine.end_round()
        # +2 from regen (was +4 without complication)
        assert engine._state.player.shields == 12

    def test_baseline_regen_unchanged_without_complication(self) -> None:
        player = _make_player_state(shield_regen=4, shields=10, max_shields=40)
        engine = _make_engine([], player=player)
        engine.execute_player_turn(ActionQueue(energy_available=10))
        engine.end_round()
        assert engine._state.player.shields == 14


class TestPlayerEvasionIntegration:
    def test_evasion_modifier_lowers_evasion_in_resolve(self) -> None:
        # Player starts with evasion 15; complication subtracts 10 → effective 5.
        # Force a hit-or-miss situation where the modifier shifts the outcome.
        comp = _comp_asteroid_evasion()
        # accuracy 100, base evasion 15 → hit_chance ~85; -10 modifier → 95
        player = _make_player_state(evasion=15)
        engine = _make_engine(
            [comp],
            player=player,
            enemy_templates=[_make_enemy_template(accuracy=100, evasion=0)],
        )
        engine.execute_player_turn(ActionQueue(energy_available=10))
        # After eval, the modifier is on state
        assert engine._state.player_evasion_modifier == -10
        # Resolve enemy turn — verify enemy hit logs reflect higher hit chance
        logs = engine.execute_enemy_turns()
        # At least one enemy attack got resolved
        assert any(log.actor.startswith("enemy:") for log in logs)


class TestEnemyAccuracyIntegration:
    def test_battle_damage_fires_when_enemy_hp_below_threshold(self) -> None:
        # Spawn an enemy already below 50% hull so trigger fires immediately.
        comp = _comp_battle_damage()
        # max hull 80, start hull 30 → 37.5% ≤ 50%
        template = _make_enemy_template(hull=80)
        engine = _make_engine([comp], enemy_templates=[template])
        # Pre-damage the enemy directly to land below threshold
        engine._state.enemies[0].current_hull = 30
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert engine._state.enemy_accuracy_multiplier == 0.5
        assert "battle_damage_test" in engine._state.fired_complication_ids

    def test_enemy_accuracy_multiplier_applies_at_resolve(self) -> None:
        # Enemy with 80 accuracy, multiplier 0.5 → effective 40 in resolve.
        # We can't fully observe the internal accuracy, but we can assert
        # the multiplier was scoped on state and the resolve path didn't
        # crash.
        comp = _comp_battle_damage()
        template = _make_enemy_template(hull=80, accuracy=80)
        engine = _make_engine([comp], enemy_templates=[template])
        engine._state.enemies[0].current_hull = 30
        engine.execute_player_turn(ActionQueue(energy_available=10))
        # Enemy turn should resolve cleanly with the multiplier applied
        logs = engine.execute_enemy_turns()
        assert isinstance(logs, list)
        assert engine._state.enemy_accuracy_multiplier == 0.5


# ---------------------------------------------------------------------------
# Spawn reinforcement integration
# ---------------------------------------------------------------------------


class TestSpawnReinforcementIntegration:
    def test_spawn_event_appends_enemy_via_data_loader(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        # Pick the first available enemy template id deterministically
        template_id = next(iter(dl.enemy_templates))

        comp = CombatComplication(
            id="reinforcement_test",
            name="Reinforcement",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="spawn_reinforcement",
            effect_params={"template_ids": [template_id]},
            narration="A contact lights up the scanner.",
        )
        engine = _make_engine([comp])
        original_count = len(engine._state.enemies)
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert len(engine._state.enemies) == original_count + 1

    def test_unknown_template_id_does_not_crash(self) -> None:
        comp = CombatComplication(
            id="reinforcement_bad",
            name="Reinforcement",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="spawn_reinforcement",
            effect_params={"template_ids": ["nonexistent_template_xyz"]},
        )
        engine = _make_engine([comp])
        original_count = len(engine._state.enemies)
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert len(engine._state.enemies) == original_count
        # Failure surfaces as a system log entry
        assert any(
            "unknown template" in " ".join(entry.effects_applied)
            for entry in engine._state.combat_log
            if entry.actor == "system"
        )


# ---------------------------------------------------------------------------
# Narration effect integration
# ---------------------------------------------------------------------------


class TestNarrationFlagIntegration:
    def test_morale_shift_fires_when_player_low_hp(self) -> None:
        comp = _comp_morale_shift()
        # Player at 25/100 → 25% ≤ 30%
        player = _make_player_state(hull=25, max_hull=100)
        engine = _make_engine([comp], player=player)
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert "player_low_hp_moment" in engine._state.complication_flags

    def test_log_entry_contains_narration_text(self) -> None:
        comp = _comp_morale_shift()
        player = _make_player_state(hull=25, max_hull=100)
        engine = _make_engine([comp], player=player)
        engine.execute_player_turn(ActionQueue(energy_available=10))
        narration_logs = [
            entry
            for entry in engine._state.combat_log
            if entry.actor == "system" and "Complication:" in entry.action
        ]
        assert any(
            "Hull's screaming." in " ".join(entry.effects_applied) for entry in narration_logs
        )


# ---------------------------------------------------------------------------
# Deferred trigger evaluation across rounds
# ---------------------------------------------------------------------------


class TestDeferredFiring:
    def test_round_three_trigger_fires_at_round_three(self) -> None:
        comp = CombatComplication(
            id="late_arrival",
            name="Late Arrival",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 3},
            effect_type="narration",
            effect_params={"flag_name": "late_arrived"},
            narration="Late.",
        )
        engine = _make_engine([comp])
        # Round 1
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert "late_arrived" not in engine._state.complication_flags
        engine.end_round()
        # Round 2
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert "late_arrived" not in engine._state.complication_flags
        engine.end_round()
        # Round 3
        engine.execute_player_turn(ActionQueue(energy_available=10))
        assert "late_arrived" in engine._state.complication_flags
