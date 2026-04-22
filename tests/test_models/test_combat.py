"""Tests for combat data models."""

import pytest
from spacegame.models.combat import (
    EffectType,
    EffectTarget,
    CombatEffect,
    CombatResult,
    CombatMove,
    CombatLogEntry,
    EnemyBehavior,
    EnemyShipTemplate,
    EnemyShip,
    PlayerCombatState,
    CombatEncounter,
    CombatState,
)


# ============================================================================
# CombatEffect Tests
# ============================================================================


class TestCombatEffect:
    """Tests for CombatEffect dataclass."""

    def test_create_instant_damage_effect(self) -> None:
        effect = CombatEffect(
            type=EffectType.DAMAGE,
            value=20.0,
        )
        assert effect.type == EffectType.DAMAGE
        assert effect.value == 20.0
        assert effect.duration == 0, "Instant effects have duration 0"
        assert effect.target == EffectTarget.ENEMY, "Default target is ENEMY"

    def test_create_duration_effect(self) -> None:
        effect = CombatEffect(
            type=EffectType.EVASION_MOD,
            value=15.0,
            duration=2,
            target=EffectTarget.SELF,
        )
        assert effect.type == EffectType.EVASION_MOD
        assert effect.value == 15.0
        assert effect.duration == 2
        assert effect.target == EffectTarget.SELF

    def test_to_dict(self) -> None:
        effect = CombatEffect(
            type=EffectType.SHIELD_RESTORE,
            value=25.0,
            duration=0,
            target=EffectTarget.SELF,
        )
        d = effect.to_dict()
        assert d["type"] == "shield_restore"
        assert d["value"] == 25.0
        assert d["duration"] == 0
        assert d["target"] == "self"

    def test_from_dict(self) -> None:
        data = {
            "type": "damage_reduction",
            "value": 0.15,
            "duration": 3,
            "target": "self",
        }
        effect = CombatEffect.from_dict(data)
        assert effect.type == EffectType.DAMAGE_REDUCTION
        assert effect.value == 0.15
        assert effect.duration == 3
        assert effect.target == EffectTarget.SELF

    def test_from_dict_defaults(self) -> None:
        data = {"type": "damage", "value": 10.0}
        effect = CombatEffect.from_dict(data)
        assert effect.duration == 0
        assert effect.target == EffectTarget.ENEMY

    def test_serialization_roundtrip(self) -> None:
        original = CombatEffect(
            type=EffectType.ENERGY_DRAIN,
            value=5.0,
            duration=1,
            target=EffectTarget.ENEMY,
        )
        restored = CombatEffect.from_dict(original.to_dict())
        assert restored.type == original.type
        assert restored.value == original.value
        assert restored.duration == original.duration
        assert restored.target == original.target


# ============================================================================
# EffectType Enum Tests
# ============================================================================


class TestEffectType:
    """Tests for EffectType enum values."""

    def test_all_effect_types_exist(self) -> None:
        expected = {
            "DAMAGE",
            "SHIELD_RESTORE",
            "HULL_RESTORE",
            "EVASION_MOD",
            "ACCURACY_MOD",
            "SHIELD_DRAIN",
            "DAMAGE_REDUCTION",
            "ENERGY_DRAIN",
            "ENERGY_RESTORE",
            "DAMAGE_BOOST",
            "BURN",
            "CHILL",
            "SUPPRESSED",
            "CLEANSE",
            "ABSORB",
            "SPAWN_REINFORCEMENT",  # Added Tier 3.E (2026-04-21)
        }
        actual = {e.name for e in EffectType}
        assert actual == expected


class TestEffectTarget:
    """Tests for EffectTarget enum values."""

    def test_all_targets_exist(self) -> None:
        # ALLY added Tier 3.D (2026-04-21) for Support archetype heal routing.
        expected = {"SELF", "ENEMY", "ALLY"}
        actual = {t.name for t in EffectTarget}
        assert actual == expected

    def test_ally_target_serializes(self) -> None:
        """Round-trip an ALLY effect through to_dict/from_dict."""
        from spacegame.models.combat import CombatEffect, EffectType

        effect = CombatEffect(
            type=EffectType.HULL_RESTORE,
            value=30.0,
            target=EffectTarget.ALLY,
        )
        restored = CombatEffect.from_dict(effect.to_dict())
        assert restored.target == EffectTarget.ALLY
        assert restored.type == EffectType.HULL_RESTORE
        assert restored.value == 30.0


# ============================================================================
# CombatMove Tests
# ============================================================================


class TestCombatMove:
    """Tests for CombatMove dataclass."""

    def test_create_basic_attack(self) -> None:
        move = CombatMove(
            id="laser_cannon",
            name="Laser Cannon",
            description="A focused laser beam.",
            effects=[
                CombatEffect(type=EffectType.DAMAGE, value=18.0),
            ],
            energy_cost=3,
            accuracy_modifier=10,
        )
        assert move.id == "laser_cannon"
        assert move.name == "Laser Cannon"
        assert len(move.effects) == 1
        assert move.energy_cost == 3
        assert move.cooldown == 0, "Default cooldown is 0"
        assert move.accuracy_modifier == 10

    def test_create_multi_effect_move(self) -> None:
        move = CombatMove(
            id="ion_disruptor",
            name="Ion Disruptor",
            description="Drains shields and deals damage.",
            effects=[
                CombatEffect(type=EffectType.DAMAGE, value=8.0),
                CombatEffect(type=EffectType.SHIELD_DRAIN, value=15.0),
            ],
            energy_cost=3,
            cooldown=1,
            accuracy_modifier=5,
        )
        assert len(move.effects) == 2
        assert move.cooldown == 1

    def test_create_defensive_move(self) -> None:
        move = CombatMove(
            id="armor_plating",
            name="Armor Plating",
            description="Activates armor plating.",
            effects=[
                CombatEffect(
                    type=EffectType.DAMAGE_REDUCTION,
                    value=0.15,
                    duration=2,
                    target=EffectTarget.SELF,
                ),
            ],
            energy_cost=2,
        )
        assert move.effects[0].target == EffectTarget.SELF
        assert move.effects[0].duration == 2

    def test_to_dict(self) -> None:
        move = CombatMove(
            id="basic_attack",
            name="Basic Attack",
            description="A basic attack.",
            effects=[CombatEffect(type=EffectType.DAMAGE, value=10.0)],
            energy_cost=2,
            cooldown=1,
            accuracy_modifier=-5,
        )
        d = move.to_dict()
        assert d["id"] == "basic_attack"
        assert d["name"] == "Basic Attack"
        assert d["description"] == "A basic attack."
        assert d["energy_cost"] == 2
        assert d["cooldown"] == 1
        assert d["accuracy_modifier"] == -5
        assert len(d["effects"]) == 1
        assert d["effects"][0]["type"] == "damage"

    def test_from_dict(self) -> None:
        data = {
            "id": "missile",
            "name": "Missile Launcher",
            "description": "Fires a missile.",
            "effects": [
                {"type": "damage", "value": 30.0},
            ],
            "energy_cost": 4,
            "cooldown": 2,
            "accuracy_modifier": -10,
        }
        move = CombatMove.from_dict(data)
        assert move.id == "missile"
        assert move.name == "Missile Launcher"
        assert move.energy_cost == 4
        assert move.cooldown == 2
        assert move.accuracy_modifier == -10
        assert len(move.effects) == 1
        assert move.effects[0].type == EffectType.DAMAGE

    def test_from_dict_defaults(self) -> None:
        data = {
            "id": "punch",
            "name": "Punch",
            "description": "A punch.",
            "effects": [],
        }
        move = CombatMove.from_dict(data)
        assert move.energy_cost == 0
        assert move.cooldown == 0
        assert move.accuracy_modifier == 0

    def test_serialization_roundtrip(self) -> None:
        original = CombatMove(
            id="plasma_torpedo",
            name="Plasma Torpedo",
            description="Devastating plasma charge.",
            effects=[
                CombatEffect(type=EffectType.DAMAGE, value=45.0),
            ],
            energy_cost=6,
            cooldown=3,
            accuracy_modifier=0,
        )
        restored = CombatMove.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.energy_cost == original.energy_cost
        assert restored.cooldown == original.cooldown
        assert restored.accuracy_modifier == original.accuracy_modifier
        assert len(restored.effects) == len(original.effects)
        assert restored.effects[0].type == original.effects[0].type
        assert restored.effects[0].value == original.effects[0].value


# ============================================================================
# CombatResult Enum Tests
# ============================================================================


class TestCombatResult:
    """Tests for CombatResult enum values."""

    def test_all_results_exist(self) -> None:
        expected = {"VICTORY", "DEFEAT", "FLED", "NEGOTIATED", "BRIBED", "IN_PROGRESS"}
        actual = {r.name for r in CombatResult}
        assert actual == expected


# ============================================================================
# CombatLogEntry Tests
# ============================================================================


class TestCombatLogEntry:
    """Tests for CombatLogEntry dataclass."""

    def test_create_hit_entry(self) -> None:
        entry = CombatLogEntry(
            round_number=1,
            actor="player",
            action="Laser Cannon",
            effects_applied=["Dealt 18 damage to Pirate Scout"],
            hit=True,
        )
        assert entry.round_number == 1
        assert entry.actor == "player"
        assert entry.action == "Laser Cannon"
        assert len(entry.effects_applied) == 1
        assert entry.hit is True

    def test_create_miss_entry(self) -> None:
        entry = CombatLogEntry(
            round_number=2,
            actor="enemy:0",
            action="Blaster",
            effects_applied=[],
            hit=False,
        )
        assert entry.hit is False
        assert len(entry.effects_applied) == 0

    def test_default_hit_is_true(self) -> None:
        entry = CombatLogEntry(
            round_number=1,
            actor="crew:elena_reeves",
            action="Evasive Maneuvers",
            effects_applied=["Evasion +20 for 2 turns"],
        )
        assert entry.hit is True


# ============================================================================
# Helpers for Enemy tests
# ============================================================================


def _make_combat_move(
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
    id: str = "pirate_raider",
    hull: int = 90,
    shields: int = 30,
    behavior: EnemyBehavior = EnemyBehavior.AGGRESSIVE,
    **overrides: object,
) -> EnemyShipTemplate:
    defaults: dict = {
        "id": id,
        "name": "Pirate Raider",
        "description": "A common pirate vessel.",
        "behavior": behavior,
        "hull": hull,
        "shields": shields,
        "energy": 10,
        "energy_regen": 3,
        "speed": 8,
        "evasion": 15,
        "accuracy": 70,
        "moves": [_make_combat_move()],
        "loot_table": [{"commodity_id": "metals", "min_qty": 2, "max_qty": 5, "chance": 0.8}],
        "negotiate_difficulty": 3,
        "flee_threshold": 0.4,
        "xp_reward": 20,
    }
    defaults.update(overrides)
    return EnemyShipTemplate(**defaults)


# ============================================================================
# EnemyBehavior Tests
# ============================================================================


class TestEnemyBehavior:
    """Tests for EnemyBehavior enum."""

    def test_all_behaviors_exist(self) -> None:
        expected = {"AGGRESSIVE", "DEFENSIVE", "COWARDLY", "EVASIVE"}
        actual = {b.name for b in EnemyBehavior}
        assert actual == expected


# ============================================================================
# EnemyShipTemplate Tests
# ============================================================================


class TestEnemyShipTemplate:
    """Tests for EnemyShipTemplate dataclass."""

    def test_create_template(self) -> None:
        template = _make_enemy_template()
        assert template.id == "pirate_raider"
        assert template.hull == 90
        assert template.shields == 30
        assert template.behavior == EnemyBehavior.AGGRESSIVE
        assert template.negotiate_difficulty == 3
        assert template.flee_threshold == 0.4
        assert template.xp_reward == 20
        assert len(template.moves) == 1
        assert len(template.loot_table) == 1

    def test_template_defaults(self) -> None:
        template = EnemyShipTemplate(
            id="test",
            name="Test",
            description="Test enemy",
            behavior=EnemyBehavior.AGGRESSIVE,
            hull=50,
            shields=10,
            energy=8,
            energy_regen=2,
            speed=6,
            evasion=10,
            accuracy=60,
            moves=[],
            loot_table=[],
        )
        assert template.negotiate_difficulty == 3
        assert template.flee_threshold == 0.4
        assert template.xp_reward == 20


# ============================================================================
# EnemyShip Tests
# ============================================================================


class TestEnemyShip:
    """Tests for EnemyShip runtime instance."""

    def test_from_template(self) -> None:
        template = _make_enemy_template(hull=100, shields=40)
        enemy = EnemyShip.from_template(template)
        assert enemy.template is template
        assert enemy.current_hull == 100
        assert enemy.current_shields == 40
        assert enemy.current_energy == template.energy
        assert enemy.active_effects == []
        assert enemy.cooldowns == {}
        assert enemy.is_fled is False

    def test_is_alive_true(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template(hull=100))
        assert enemy.is_alive is True

    def test_is_alive_false_when_hull_zero(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template(hull=100))
        enemy.current_hull = 0
        assert enemy.is_alive is False

    def test_is_alive_false_when_hull_negative(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template(hull=100))
        enemy.current_hull = -5
        assert enemy.is_alive is False

    def test_hull_ratio(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template(hull=100))
        assert enemy.hull_ratio == 1.0
        enemy.current_hull = 50
        assert enemy.hull_ratio == 0.5
        enemy.current_hull = 0
        assert enemy.hull_ratio == 0.0

    def test_effective_evasion_with_buff(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template(hull=100))
        assert enemy.get_effective_evasion() == 15  # base evasion
        buff = CombatEffect(
            type=EffectType.EVASION_MOD, value=10.0, duration=2, target=EffectTarget.SELF
        )
        enemy.active_effects.append((buff, 2))
        assert enemy.get_effective_evasion() == 25

    def test_effective_evasion_with_debuff(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template(hull=100))
        debuff = CombatEffect(
            type=EffectType.EVASION_MOD, value=-15.0, duration=1, target=EffectTarget.ENEMY
        )
        enemy.active_effects.append((debuff, 1))
        assert enemy.get_effective_evasion() == 0

    def test_effective_accuracy_with_modifier(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template())
        assert enemy.get_effective_accuracy() == 70  # base accuracy
        buff = CombatEffect(
            type=EffectType.ACCURACY_MOD, value=10.0, duration=1, target=EffectTarget.SELF
        )
        enemy.active_effects.append((buff, 1))
        assert enemy.get_effective_accuracy() == 80

    def test_tick_effects_decrements_and_expires(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template())
        effect_2turns = CombatEffect(
            type=EffectType.EVASION_MOD, value=10.0, duration=2, target=EffectTarget.SELF
        )
        effect_1turn = CombatEffect(
            type=EffectType.ACCURACY_MOD, value=5.0, duration=1, target=EffectTarget.SELF
        )
        enemy.active_effects = [(effect_2turns, 2), (effect_1turn, 1)]

        messages = enemy.tick_effects()
        assert len(enemy.active_effects) == 1, "1-turn effect should expire"
        assert enemy.active_effects[0][1] == 1, "2-turn effect decremented to 1"
        assert len(messages) > 0

    def test_tick_cooldowns(self) -> None:
        enemy = EnemyShip.from_template(_make_enemy_template())
        enemy.cooldowns = {"blaster": 2, "missile": 1}
        enemy.tick_cooldowns()
        assert enemy.cooldowns["blaster"] == 1
        assert "missile" not in enemy.cooldowns, "Cooldown at 0 should be removed"

    def test_regenerate_energy(self) -> None:
        template = _make_enemy_template()
        enemy = EnemyShip.from_template(template)
        enemy.current_energy = 5
        enemy.regenerate_energy()
        assert enemy.current_energy == 5 + template.energy_regen

    def test_regenerate_energy_capped(self) -> None:
        template = _make_enemy_template()
        enemy = EnemyShip.from_template(template)
        enemy.current_energy = template.energy  # already full
        enemy.regenerate_energy()
        assert enemy.current_energy == template.energy, "Energy should not exceed max"


# ============================================================================
# Helpers for PlayerCombatState
# ============================================================================


def _make_player_combat_state(**overrides: object) -> PlayerCombatState:
    defaults: dict = {
        "hull": 100,
        "max_hull": 100,
        "shields": 40,
        "max_shields": 40,
        "energy": 10,
        "max_energy": 10,
        "energy_regen": 3,
        "speed": 8,
        "evasion": 15,
        "accuracy": 70,
        "equipment_moves": [_make_combat_move("laser", "Laser", 18.0, 3)],
        "crew_moves": [_make_combat_move("evasive", "Evasive Maneuvers", 0.0, 0)],
        "active_effects": [],
        "cooldowns": {},
    }
    defaults.update(overrides)
    return PlayerCombatState(**defaults)


# ============================================================================
# PlayerCombatState Tests
# ============================================================================


class TestPlayerCombatState:
    """Tests for PlayerCombatState dataclass."""

    def test_create(self) -> None:
        state = _make_player_combat_state()
        assert state.hull == 100
        assert state.max_hull == 100
        assert state.shields == 40
        assert state.max_shields == 40
        assert state.energy == 10
        assert state.max_energy == 10
        assert state.energy_regen == 3
        assert state.speed == 8
        assert state.evasion == 15
        assert state.accuracy == 70
        assert len(state.equipment_moves) == 1
        assert len(state.crew_moves) == 1

    def test_is_alive_true(self) -> None:
        state = _make_player_combat_state(hull=50)
        assert state.is_alive is True

    def test_is_alive_false(self) -> None:
        state = _make_player_combat_state(hull=0)
        assert state.is_alive is False

    def test_hull_ratio(self) -> None:
        state = _make_player_combat_state(hull=75, max_hull=100)
        assert state.hull_ratio == 0.75

    def test_hull_ratio_zero_max(self) -> None:
        state = _make_player_combat_state(hull=0, max_hull=0)
        assert state.hull_ratio == 0.0

    def test_effective_evasion_with_buffs(self) -> None:
        state = _make_player_combat_state(evasion=20)
        assert state.get_effective_evasion() == 20
        buff = CombatEffect(
            type=EffectType.EVASION_MOD, value=15.0, duration=2, target=EffectTarget.SELF
        )
        state.active_effects.append((buff, 2))
        assert state.get_effective_evasion() == 35

    def test_effective_evasion_minimum_zero(self) -> None:
        state = _make_player_combat_state(evasion=10)
        debuff = CombatEffect(
            type=EffectType.EVASION_MOD, value=-20.0, duration=1, target=EffectTarget.ENEMY
        )
        state.active_effects.append((debuff, 1))
        assert state.get_effective_evasion() == 0

    def test_effective_accuracy(self) -> None:
        state = _make_player_combat_state(accuracy=70)
        buff = CombatEffect(
            type=EffectType.ACCURACY_MOD, value=10.0, duration=1, target=EffectTarget.SELF
        )
        state.active_effects.append((buff, 1))
        assert state.get_effective_accuracy() == 80

    def test_tick_effects(self) -> None:
        state = _make_player_combat_state()
        effect_2 = CombatEffect(
            type=EffectType.DAMAGE_REDUCTION, value=0.15, duration=2, target=EffectTarget.SELF
        )
        effect_1 = CombatEffect(
            type=EffectType.EVASION_MOD, value=10.0, duration=1, target=EffectTarget.SELF
        )
        state.active_effects = [(effect_2, 2), (effect_1, 1)]
        messages = state.tick_effects()
        assert len(state.active_effects) == 1
        assert len(messages) == 1  # one expired

    def test_tick_cooldowns(self) -> None:
        state = _make_player_combat_state()
        state.cooldowns = {"laser": 3, "missile": 1}
        state.tick_cooldowns()
        assert state.cooldowns["laser"] == 2
        assert "missile" not in state.cooldowns

    def test_regenerate_energy(self) -> None:
        state = _make_player_combat_state(energy=5, max_energy=10, energy_regen=3)
        state.regenerate_energy()
        assert state.energy == 8

    def test_regenerate_energy_capped(self) -> None:
        state = _make_player_combat_state(energy=9, max_energy=10, energy_regen=3)
        state.regenerate_energy()
        assert state.energy == 10


# ============================================================================
# CombatEncounter Tests
# ============================================================================


class TestCombatEncounter:
    """Tests for CombatEncounter dataclass."""

    def test_create(self) -> None:
        templates = [_make_enemy_template(), _make_enemy_template(id="pirate_scout")]
        encounter = CombatEncounter(enemy_templates=templates, encounter_seed=42)
        assert len(encounter.enemy_templates) == 2
        assert encounter.encounter_seed == 42


# ============================================================================
# CombatState Tests
# ============================================================================


class TestCombatState:
    """Tests for CombatState dataclass."""

    def _make_combat_state(self) -> CombatState:
        player = _make_player_combat_state()
        templates = [_make_enemy_template()]
        encounter = CombatEncounter(enemy_templates=templates, encounter_seed=42)
        enemies = [EnemyShip.from_template(t) for t in templates]
        return CombatState(
            player=player,
            enemies=enemies,
            encounter=encounter,
            combat_log=[],
        )

    def test_create_defaults(self) -> None:
        state = self._make_combat_state()
        assert state.round_number == 1
        assert state.result == CombatResult.IN_PROGRESS
        assert state.negotiate_used is False
        assert len(state.combat_log) == 0

    def test_all_enemies_defeated_false(self) -> None:
        state = self._make_combat_state()
        assert state.all_enemies_defeated is False

    def test_all_enemies_defeated_true(self) -> None:
        state = self._make_combat_state()
        state.enemies[0].current_hull = 0
        assert state.all_enemies_defeated is True

    def test_all_enemies_defeated_mixed_fled(self) -> None:
        player = _make_player_combat_state()
        templates = [_make_enemy_template(), _make_enemy_template(id="scout")]
        encounter = CombatEncounter(enemy_templates=templates, encounter_seed=1)
        enemies = [EnemyShip.from_template(t) for t in templates]
        state = CombatState(player=player, enemies=enemies, encounter=encounter, combat_log=[])
        enemies[0].current_hull = 0  # dead
        enemies[1].is_fled = True  # fled
        assert state.all_enemies_defeated is True

    def test_surviving_enemies(self) -> None:
        player = _make_player_combat_state()
        templates = [
            _make_enemy_template(id="a"),
            _make_enemy_template(id="b"),
            _make_enemy_template(id="c"),
        ]
        encounter = CombatEncounter(enemy_templates=templates, encounter_seed=1)
        enemies = [EnemyShip.from_template(t) for t in templates]
        state = CombatState(player=player, enemies=enemies, encounter=encounter, combat_log=[])
        enemies[1].current_hull = 0  # dead
        survivors = state.surviving_enemies
        assert len(survivors) == 2
        assert all(e.is_alive for e in survivors)

    def test_surviving_enemies_excludes_fled(self) -> None:
        player = _make_player_combat_state()
        templates = [_make_enemy_template(id="a"), _make_enemy_template(id="b")]
        encounter = CombatEncounter(enemy_templates=templates, encounter_seed=1)
        enemies = [EnemyShip.from_template(t) for t in templates]
        state = CombatState(player=player, enemies=enemies, encounter=encounter, combat_log=[])
        enemies[0].is_fled = True
        survivors = state.surviving_enemies
        assert len(survivors) == 1
