"""Tests for enemy subsystem palette + damage routing (Combat C4 §11.2)."""

from __future__ import annotations

from spacegame.models.combat import (
    CombatMove,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
)
from spacegame.models.enemy_subsystems import (
    CANONICAL_TAGS,
    SUBSYSTEM_PALETTE,
    SubsystemTag,
    apply_subsystem_damage,
    apply_subsystem_destruction,
    consume_engine_tempo_skip,
    get_effect,
    is_valid_tag,
    subsystem_max_hp,
)


def _template(
    hull: int = 100,
    subsystems: list[str] | None = None,
    behavior: EnemyBehavior = EnemyBehavior.AGGRESSIVE,
    flee_threshold: float = 0.4,
) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id="test",
        name="Test",
        description="",
        behavior=behavior,
        hull=hull,
        shields=0,
        energy=5,
        energy_regen=1,
        speed=10,
        evasion=20,
        accuracy=60,
        moves=[CombatMove(id="shot", name="Shot", description="", effects=[])],
        loot_table=[],
        flee_threshold=flee_threshold,
        targetable_subsystems=subsystems or [],
    )


class TestPalette:
    def test_six_canonical_tags(self) -> None:
        assert len(CANONICAL_TAGS) == 6
        assert set(CANONICAL_TAGS) == {t.value for t in SubsystemTag}

    def test_every_tag_has_palette_entry(self) -> None:
        for tag in CANONICAL_TAGS:
            assert tag in SUBSYSTEM_PALETTE
            assert SUBSYSTEM_PALETTE[tag].tag == tag

    def test_weapon_array_reduces_damage(self) -> None:
        assert SUBSYSTEM_PALETTE["weapon_array"].damage_multiplier == 0.60

    def test_engine_triggers_tempo_skip_and_disables_flee(self) -> None:
        eff = SUBSYSTEM_PALETTE["engine"]
        assert eff.trigger_tempo_skip
        assert eff.disable_flee
        assert eff.evasion_override == 0

    def test_cockpit_instant_kills(self) -> None:
        assert SUBSYSTEM_PALETTE["cockpit"].instant_kill

    def test_shield_generator_strips_and_disables_regen(self) -> None:
        eff = SUBSYSTEM_PALETTE["shield_generator"]
        assert eff.strip_current_shields
        assert eff.disable_shield_regen

    def test_sensor_array_cuts_accuracy(self) -> None:
        assert SUBSYSTEM_PALETTE["sensor_array"].accuracy_delta == -30

    def test_reactor_disables_energy_regen(self) -> None:
        assert SUBSYSTEM_PALETTE["reactor"].disable_energy_regen


class TestValidation:
    def test_is_valid_tag_known(self) -> None:
        assert is_valid_tag("engine")

    def test_is_valid_tag_unknown(self) -> None:
        assert not is_valid_tag("warp_drive")

    def test_get_effect_returns_descriptor(self) -> None:
        eff = get_effect("engine")
        assert eff is not None
        assert eff.tag == "engine"

    def test_get_effect_unknown_returns_none(self) -> None:
        assert get_effect("not_a_tag") is None


class TestSubsystemHPInit:
    def test_baseline_hp_is_25_percent_of_hull(self) -> None:
        assert subsystem_max_hp("engine", 100) == 25

    def test_cockpit_hp_is_lower_than_baseline(self) -> None:
        """Cockpit is a risk target — lower HP than a normal subsystem."""
        cockpit_hp = subsystem_max_hp("cockpit", 100)
        engine_hp = subsystem_max_hp("engine", 100)
        assert cockpit_hp < engine_hp

    def test_unknown_tag_defaults_to_baseline(self) -> None:
        assert subsystem_max_hp("unknown", 100) == 25

    def test_minimum_hp_is_one(self) -> None:
        """Even tiny enemies get at least 1 HP per subsystem."""
        assert subsystem_max_hp("engine", 1) >= 1


class TestEnemyShipRuntimeState:
    def test_from_template_initializes_subsystem_hp(self) -> None:
        tpl = _template(hull=100, subsystems=["engine", "weapon_array"])
        enemy = EnemyShip.from_template(tpl)
        assert "engine" in enemy.subsystem_hp
        assert "weapon_array" in enemy.subsystem_hp
        assert enemy.subsystem_hp["engine"] == 25

    def test_from_template_empty_subsystems_yields_empty_hp_dict(self) -> None:
        tpl = _template(hull=100, subsystems=[])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.subsystem_hp == {}

    def test_subsystems_destroyed_starts_empty(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.subsystems_destroyed == set()

    def test_engines_just_destroyed_starts_false(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert not enemy.engines_just_destroyed

    def test_focused_subsystem_starts_none(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.focused_subsystem is None


class TestDamageRouting:
    def test_damage_chips_subsystem_hp(self) -> None:
        tpl = _template(hull=100, subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        effect = apply_subsystem_damage(enemy, 10, "engine")
        assert effect is None  # not destroyed yet
        assert enemy.subsystem_hp["engine"] == 15  # 25 - 10

    def test_zero_or_negative_damage_is_noop(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert apply_subsystem_damage(enemy, 0, "engine") is None
        assert apply_subsystem_damage(enemy, -5, "engine") is None
        assert enemy.subsystem_hp["engine"] == 25

    def test_damage_to_unknown_subsystem_is_noop(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert apply_subsystem_damage(enemy, 100, "warp_drive") is None

    def test_damage_to_already_destroyed_subsystem_is_noop(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        enemy.subsystems_destroyed.add("engine")
        assert apply_subsystem_damage(enemy, 100, "engine") is None

    def test_destruction_returns_effect_descriptor(self) -> None:
        tpl = _template(hull=100, subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        effect = apply_subsystem_damage(enemy, 100, "engine")
        assert effect is not None
        assert effect.tag == "engine"
        assert "engine" in enemy.subsystems_destroyed
        assert enemy.subsystem_hp["engine"] == 0


class TestDestructionEffects:
    def test_engine_destruction_sets_tempo_skip(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        effect = SUBSYSTEM_PALETTE["engine"]
        apply_subsystem_destruction(enemy, effect)
        assert enemy.engines_just_destroyed

    def test_shield_destruction_strips_current_shields(self) -> None:
        tpl = _template(subsystems=["shield_generator"])
        enemy = EnemyShip.from_template(tpl)
        enemy.current_shields = 40
        apply_subsystem_destruction(enemy, SUBSYSTEM_PALETTE["shield_generator"])
        assert enemy.current_shields == 0

    def test_cockpit_destruction_kills(self) -> None:
        tpl = _template(hull=100, subsystems=["cockpit"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.current_hull == 100
        apply_subsystem_destruction(enemy, SUBSYSTEM_PALETTE["cockpit"])
        assert enemy.current_hull == 0
        assert not enemy.is_alive


class TestEffectiveStats:
    def test_evasion_unchanged_without_engine_destruction(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.effective_evasion == 20

    def test_evasion_zeroed_on_engine_destruction(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        enemy.subsystems_destroyed.add("engine")
        assert enemy.effective_evasion == 0

    def test_accuracy_cut_on_sensor_destruction(self) -> None:
        tpl = _template(subsystems=["sensor_array"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.effective_accuracy == 60
        enemy.subsystems_destroyed.add("sensor_array")
        assert enemy.effective_accuracy == 30

    def test_damage_multiplier_reduced_on_weapon_destruction(self) -> None:
        tpl = _template(subsystems=["weapon_array"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.damage_multiplier == 1.0
        enemy.subsystems_destroyed.add("weapon_array")
        assert enemy.damage_multiplier == 0.60

    def test_can_flee_reflects_engine(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.can_flee
        enemy.subsystems_destroyed.add("engine")
        assert not enemy.can_flee

    def test_can_regen_shields_reflects_shield_generator(self) -> None:
        tpl = _template(subsystems=["shield_generator"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.can_regen_shields
        enemy.subsystems_destroyed.add("shield_generator")
        assert not enemy.can_regen_shields

    def test_can_regen_energy_reflects_reactor(self) -> None:
        tpl = _template(subsystems=["reactor"])
        enemy = EnemyShip.from_template(tpl)
        assert enemy.can_regen_energy
        enemy.subsystems_destroyed.add("reactor")
        assert not enemy.can_regen_energy


class TestTempoSkip:
    def test_consume_returns_true_when_engines_just_destroyed(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        enemy.engines_just_destroyed = True
        assert consume_engine_tempo_skip(enemy)
        # Flag cleared after consumption.
        assert not enemy.engines_just_destroyed

    def test_consume_returns_false_when_flag_clear(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        assert not consume_engine_tempo_skip(enemy)

    def test_consume_is_one_shot(self) -> None:
        tpl = _template(subsystems=["engine"])
        enemy = EnemyShip.from_template(tpl)
        enemy.engines_just_destroyed = True
        assert consume_engine_tempo_skip(enemy)
        # Second call returns False — tempo skip is one-shot per destruction.
        assert not consume_engine_tempo_skip(enemy)
