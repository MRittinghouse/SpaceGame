"""Scenario B: Subsystem focus → damage → destruction → effect applies.

End-to-end verification of Impl 4 (Combat §11.2). Drives damage through the
full ``apply_subsystem_damage`` + ``apply_subsystem_destruction`` pipeline
and asserts each destruction effect lands on the enemy's runtime state.

This is the integration test that would have caught the "do enemies even
try to flee right now?" design gap that the user flagged during Impl 4.
"""

from __future__ import annotations

from spacegame.models.enemy_subsystems import (
    apply_subsystem_damage,
    apply_subsystem_destruction,
    consume_engine_tempo_skip,
)
from tests.test_scenarios._helpers import real_enemy


class TestEngineDestructionChain:
    """Engine destruction is the most complex effect — it sets multiple
    flags (tempo skip, evasion override, flee disable). Verify each."""

    def test_engine_destruction_full_effect_chain(self) -> None:
        # pirate_raider has ["weapon_array", "engine"]
        enemy = real_enemy("pirate_raider")
        assert "engine" in enemy.subsystem_hp
        initial_evasion = enemy.effective_evasion
        assert initial_evasion > 0, "Fresh enemy should have non-zero evasion"
        assert enemy.can_flee is True  # True until engines destroyed (regardless of AI)

        # Hit engine until destroyed. Subsystem HP is 25% of hull.
        starting_hp = enemy.subsystem_hp["engine"]
        effect = apply_subsystem_damage(enemy, starting_hp, "engine")

        assert effect is not None, "Destruction should return effect descriptor"
        assert effect.tag == "engine"
        assert "engine" in enemy.subsystems_destroyed
        assert enemy.subsystem_hp["engine"] == 0

        # Apply the effect — this is the game step after damage routing
        messages = apply_subsystem_destruction(enemy, effect)
        assert len(messages) >= 1
        assert "engine" in messages[0].lower() or "cripple" in messages[0].lower()

        # Effective stats reflect destruction
        assert enemy.effective_evasion == 0, "Evasion must zero out post-destruction"
        assert enemy.engines_just_destroyed is True, "Tempo skip flag must be set"

        # can_flee now False (engine was destroyed)
        assert enemy.can_flee is False, "Engine destruction must disable flee"

        # Consume tempo skip — this is what combat_engine does on enemy turn
        assert consume_engine_tempo_skip(enemy) is True
        assert enemy.engines_just_destroyed is False, "Tempo flag clears after consumption"

        # One-shot: subsequent attempts return False
        assert consume_engine_tempo_skip(enemy) is False

    def test_engine_destruction_disables_flee_on_cowardly(self) -> None:
        """Cowardly enemies normally flee at low health — engine destruction
        must disable that behaviour."""
        enemy = real_enemy("pirate_scout")  # cowardly
        assert enemy.can_flee, "pirate_scout starts with flee capability"

        # Destroy engine
        hp = enemy.subsystem_hp["engine"]
        effect = apply_subsystem_damage(enemy, hp, "engine")
        assert effect is not None
        apply_subsystem_destruction(enemy, effect)

        assert enemy.can_flee is False, (
            "Cowardly enemy must not flee once engines are destroyed"
        )


class TestShieldGeneratorDestruction:
    def test_shields_strip_and_regen_disable(self) -> None:
        # Defensive enemy with shield_generator in palette
        enemy = real_enemy("guild_enforcer")  # defensive, subs=[shield_generator, reactor]
        assert "shield_generator" in enemy.subsystem_hp

        # Put shields at max so strip effect is visible
        enemy.current_shields = enemy.template.shields
        assert enemy.current_shields > 0

        hp = enemy.subsystem_hp["shield_generator"]
        effect = apply_subsystem_damage(enemy, hp, "shield_generator")
        assert effect is not None

        apply_subsystem_destruction(enemy, effect)

        assert enemy.current_shields == 0, "Shield destruction must strip current shields"
        assert enemy.can_regen_shields is False, "Regen must be disabled post-destruction"


class TestCockpitDestruction:
    """Cockpit is the instant-kill risk target — lower HP, full kill on destruction."""

    def test_cockpit_instant_kills_enemy(self) -> None:
        enemy = real_enemy("pirate_lord")  # legendary, has cockpit
        assert "cockpit" in enemy.subsystem_hp
        assert enemy.is_alive

        hp = enemy.subsystem_hp["cockpit"]
        effect = apply_subsystem_damage(enemy, hp, "cockpit")
        assert effect is not None
        assert effect.instant_kill is True

        apply_subsystem_destruction(enemy, effect)

        assert enemy.current_hull == 0, "Cockpit shot must zero hull"
        assert not enemy.is_alive

    def test_cockpit_hp_is_lower_than_engine(self) -> None:
        """Cockpit risk comes from lower HP — confirm on a real enemy."""
        enemy = real_enemy("pirate_lord")
        assert enemy.subsystem_hp["cockpit"] < enemy.subsystem_hp["engine"]


class TestWeaponAndSensorAndReactor:
    def test_weapon_destruction_reduces_damage_multiplier(self) -> None:
        enemy = real_enemy("pirate_raider")  # has weapon_array
        assert enemy.damage_multiplier == 1.0

        hp = enemy.subsystem_hp["weapon_array"]
        effect = apply_subsystem_damage(enemy, hp, "weapon_array")
        assert effect is not None

        apply_subsystem_destruction(enemy, effect)

        assert enemy.damage_multiplier == 0.60, "40% damage reduction per palette"

    def test_sensor_destruction_cuts_accuracy(self) -> None:
        enemy = real_enemy("pirate_scout")  # cowardly, has sensor_array
        baseline_accuracy = enemy.effective_accuracy

        hp = enemy.subsystem_hp["sensor_array"]
        effect = apply_subsystem_damage(enemy, hp, "sensor_array")
        assert effect is not None

        apply_subsystem_destruction(enemy, effect)

        assert enemy.effective_accuracy == baseline_accuracy - 30

    def test_reactor_destruction_disables_energy_regen(self) -> None:
        enemy = real_enemy("guild_enforcer")  # defensive, has reactor
        assert enemy.can_regen_energy

        hp = enemy.subsystem_hp["reactor"]
        effect = apply_subsystem_damage(enemy, hp, "reactor")
        assert effect is not None

        apply_subsystem_destruction(enemy, effect)

        assert enemy.can_regen_energy is False


class TestMultiSubsystemDestruction:
    """Destroying multiple subsystems compounds — no effect interferes with another."""

    def test_engine_plus_weapons_both_apply(self) -> None:
        enemy = real_enemy("pirate_raider")

        # Destroy weapon_array first
        wa_hp = enemy.subsystem_hp["weapon_array"]
        wa_effect = apply_subsystem_damage(enemy, wa_hp, "weapon_array")
        apply_subsystem_destruction(enemy, wa_effect)
        assert enemy.damage_multiplier == 0.60

        # Then engine
        e_hp = enemy.subsystem_hp["engine"]
        e_effect = apply_subsystem_damage(enemy, e_hp, "engine")
        apply_subsystem_destruction(enemy, e_effect)
        assert enemy.effective_evasion == 0

        # Both effects still reflected
        assert enemy.damage_multiplier == 0.60, "Weapon destruction persists"
        assert enemy.effective_evasion == 0, "Engine destruction persists"
        assert len(enemy.subsystems_destroyed) == 2


class TestDamageRoutingEdgeCases:
    """Guard rails — damage to dead enemies, destroyed subsystems, unknown tags."""

    def test_damage_to_destroyed_subsystem_is_noop(self) -> None:
        enemy = real_enemy("pirate_raider")
        hp = enemy.subsystem_hp["engine"]
        apply_subsystem_damage(enemy, hp, "engine")  # destroy it

        # Second hit shouldn't crash or reset HP
        effect = apply_subsystem_damage(enemy, 50, "engine")
        assert effect is None
        assert enemy.subsystem_hp["engine"] == 0

    def test_damage_to_untargeted_subsystem_noop(self) -> None:
        """pirate_scout doesn't have cockpit in its palette."""
        enemy = real_enemy("pirate_scout")
        assert "cockpit" not in enemy.subsystem_hp

        effect = apply_subsystem_damage(enemy, 100, "cockpit")
        assert effect is None
        assert enemy.is_alive  # Must not accidentally kill
