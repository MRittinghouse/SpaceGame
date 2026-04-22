"""Tests for legendary boss-drop module combat mechanics.

Covers Chain Fire, Void Absorption, Heat Hardening, Cooldown Reduction,
and Phase Shift — the 5 unique mechanics from superboss drops.
"""

import random

from spacegame.models.legendary_effects import (
    LegendaryState,
    apply_cooldown_reduction,
    check_phase_shift,
    init_legendary_state,
    process_chain_fire,
    process_heat_hardening,
    process_void_absorption,
    process_void_release,
)
from spacegame.models.ship_build import PlacedSlot, ShipBuild
from spacegame.models.ship_part import ShipPart

# ============================================================================
# Helpers
# ============================================================================


def _legendary_part(part_id: str, **provides) -> ShipPart:
    return ShipPart(
        id=part_id,
        name=part_id,
        description="",
        slot_type="weapon",
        min_size="small",
        manufacturer="salvage_rat",
        provides=provides,
        base_cost=0,
        combat_move=None,
    )


def _build_with_legendary(part_id: str, **provides) -> tuple[ShipBuild, dict]:
    catalog = {part_id: _legendary_part(part_id, **provides)}
    build = ShipBuild(
        weight_class="tiny",
        placed_slots=[PlacedSlot(slot_def_id="weapon_small", x=5, y=5, equipped_part_id=part_id)],
    )
    return build, catalog


# ============================================================================
# Legendary State Init
# ============================================================================


class TestLegendaryStateInit:
    def test_init_with_no_legendaries(self) -> None:
        build = ShipBuild(weight_class="tiny")
        state = init_legendary_state(build, {})
        assert state.chain_fire_chance == 0.0
        assert state.void_absorption_rate == 0.0
        assert state.heat_hardening_max == 0
        assert state.cooldown_reduction == 0
        assert state.phase_shift_interval == 0

    def test_init_detects_chain_fire(self) -> None:
        build, catalog = _build_with_legendary(
            "repeater",
            chain_fire_chance=0.4,
            chain_fire_damage_mult=0.5,
        )
        state = init_legendary_state(build, catalog)
        assert state.chain_fire_chance == 0.4
        assert state.chain_fire_damage_mult == 0.5

    def test_init_detects_void_absorption(self) -> None:
        build, catalog = _build_with_legendary(
            "reactor",
            void_absorption_rate=0.15,
            void_release_available=True,
        )
        state = init_legendary_state(build, catalog)
        assert state.void_absorption_rate == 0.15
        assert state.void_release_available is True
        assert state.void_charge == 0

    def test_init_detects_heat_hardening(self) -> None:
        build, catalog = _build_with_legendary(
            "bulwark",
            heat_hardening_per_hit=1,
            heat_hardening_max=5,
        )
        state = init_legendary_state(build, catalog)
        assert state.heat_hardening_per_hit == 1
        assert state.heat_hardening_max == 5
        assert state.heat_stacks == 0

    def test_init_detects_cooldown_reduction(self) -> None:
        build, catalog = _build_with_legendary(
            "engine",
            cooldown_reduction=1,
        )
        state = init_legendary_state(build, catalog)
        assert state.cooldown_reduction == 1

    def test_init_detects_phase_shift(self) -> None:
        build, catalog = _build_with_legendary(
            "shroud",
            phase_shift_interval=3,
            phase_shift_guaranteed_dodge=True,
        )
        state = init_legendary_state(build, catalog)
        assert state.phase_shift_interval == 3


# ============================================================================
# Chain Fire
# ============================================================================


class TestChainFire:
    def test_chain_fires_on_success(self) -> None:
        random.seed(1)  # Deterministic
        state = LegendaryState(chain_fire_chance=1.0, chain_fire_damage_mult=0.5)
        triggered, mult = process_chain_fire(state, base_damage=20.0)
        assert triggered is True
        assert mult == 0.5

    def test_chain_never_fires_at_zero(self) -> None:
        state = LegendaryState(chain_fire_chance=0.0)
        for _ in range(50):
            triggered, _ = process_chain_fire(state, base_damage=20.0)
            assert not triggered

    def test_chain_respects_probability(self) -> None:
        random.seed(42)
        state = LegendaryState(chain_fire_chance=0.4, chain_fire_damage_mult=0.5)
        fires = sum(1 for _ in range(1000) if process_chain_fire(state, 20.0)[0])
        # Should be roughly 400 out of 1000 (±60)
        assert 300 < fires < 500, f"Expected ~400 fires, got {fires}"


# ============================================================================
# Void Absorption
# ============================================================================


class TestVoidAbsorption:
    def test_absorbs_percentage_of_hull_damage(self) -> None:
        state = LegendaryState(void_absorption_rate=0.15, void_release_available=True)
        absorbed = process_void_absorption(state, hull_damage=100)
        assert absorbed == 15
        assert state.void_charge == 15

    def test_accumulates_over_multiple_hits(self) -> None:
        state = LegendaryState(void_absorption_rate=0.15, void_release_available=True)
        process_void_absorption(state, hull_damage=100)
        process_void_absorption(state, hull_damage=100)
        process_void_absorption(state, hull_damage=100)
        assert state.void_charge == 45

    def test_no_absorption_at_zero_rate(self) -> None:
        state = LegendaryState(void_absorption_rate=0.0)
        absorbed = process_void_absorption(state, hull_damage=100)
        assert absorbed == 0
        assert state.void_charge == 0

    def test_release_returns_accumulated_charge(self) -> None:
        state = LegendaryState(
            void_absorption_rate=0.15,
            void_release_available=True,
            void_charge=50,
        )
        damage = process_void_release(state)
        assert damage == 50
        assert state.void_charge == 0
        assert state.void_release_available is False  # One-time use

    def test_release_with_no_charge(self) -> None:
        state = LegendaryState(void_absorption_rate=0.15, void_release_available=True)
        damage = process_void_release(state)
        assert damage == 0


# ============================================================================
# Heat Hardening
# ============================================================================


class TestHeatHardening:
    def test_shield_hit_adds_stack(self) -> None:
        state = LegendaryState(heat_hardening_per_hit=1, heat_hardening_max=5)
        armor_bonus = process_heat_hardening(state, shield_absorbed=10)
        assert state.heat_stacks == 1
        assert armor_bonus == 1

    def test_stacks_accumulate(self) -> None:
        state = LegendaryState(heat_hardening_per_hit=1, heat_hardening_max=5)
        for _ in range(3):
            process_heat_hardening(state, shield_absorbed=10)
        assert state.heat_stacks == 3

    def test_stacks_cap_at_max(self) -> None:
        state = LegendaryState(heat_hardening_per_hit=1, heat_hardening_max=5)
        for _ in range(10):
            process_heat_hardening(state, shield_absorbed=10)
        assert state.heat_stacks == 5

    def test_no_stack_if_shields_not_hit(self) -> None:
        state = LegendaryState(heat_hardening_per_hit=1, heat_hardening_max=5)
        armor_bonus = process_heat_hardening(state, shield_absorbed=0)
        assert state.heat_stacks == 0
        assert armor_bonus == 0

    def test_no_stacking_without_module(self) -> None:
        state = LegendaryState()  # No heat hardening
        armor_bonus = process_heat_hardening(state, shield_absorbed=10)
        assert armor_bonus == 0


# ============================================================================
# Cooldown Reduction
# ============================================================================


class TestCooldownReduction:
    def test_reduces_all_cooldowns(self) -> None:
        cooldowns = {"move_a": 3, "move_b": 2, "move_c": 1}
        state = LegendaryState(cooldown_reduction=1)
        apply_cooldown_reduction(state, cooldowns)
        assert cooldowns["move_a"] == 2
        assert cooldowns["move_b"] == 1
        assert cooldowns["move_c"] == 0

    def test_does_not_go_negative(self) -> None:
        cooldowns = {"move_a": 0}
        state = LegendaryState(cooldown_reduction=1)
        apply_cooldown_reduction(state, cooldowns)
        assert cooldowns["move_a"] == 0

    def test_no_reduction_at_zero(self) -> None:
        cooldowns = {"move_a": 3}
        state = LegendaryState(cooldown_reduction=0)
        apply_cooldown_reduction(state, cooldowns)
        assert cooldowns["move_a"] == 3


# ============================================================================
# Phase Shift
# ============================================================================


class TestPhaseShift:
    def test_activates_on_interval(self) -> None:
        state = LegendaryState(phase_shift_interval=3)
        assert check_phase_shift(state, round_number=3) is True
        assert check_phase_shift(state, round_number=6) is True
        assert check_phase_shift(state, round_number=9) is True

    def test_does_not_activate_off_interval(self) -> None:
        state = LegendaryState(phase_shift_interval=3)
        assert check_phase_shift(state, round_number=1) is False
        assert check_phase_shift(state, round_number=2) is False
        assert check_phase_shift(state, round_number=4) is False
        assert check_phase_shift(state, round_number=5) is False

    def test_no_phase_shift_without_module(self) -> None:
        state = LegendaryState()
        assert check_phase_shift(state, round_number=3) is False

    def test_round_zero_does_not_activate(self) -> None:
        state = LegendaryState(phase_shift_interval=3)
        assert check_phase_shift(state, round_number=0) is False


class TestPhaseShiftFirstAttackOnly:
    """Spec §8: Phase Shift blocks the FIRST incoming attack per round.
    Previously (pre-Tier-2.1) it blocked all attacks in an active round —
    a 3-enemy encounter on a shift round dodged all 3 attacks. Now it
    dodges exactly one."""

    def test_consume_fires_once_then_returns_false(self) -> None:
        from spacegame.models.legendary_effects import consume_phase_shift

        state = LegendaryState(phase_shift_interval=3)

        # First attack on round 3: dodges
        assert consume_phase_shift(state, round_number=3) is True
        # Subsequent attacks in the same round: hit normally
        assert consume_phase_shift(state, round_number=3) is False
        assert consume_phase_shift(state, round_number=3) is False

    def test_check_returns_false_after_consume(self) -> None:
        """check_phase_shift (pure predicate) respects the used flag."""
        from spacegame.models.legendary_effects import consume_phase_shift

        state = LegendaryState(phase_shift_interval=3)
        assert check_phase_shift(state, round_number=3) is True
        consume_phase_shift(state, round_number=3)
        assert check_phase_shift(state, round_number=3) is False

    def test_reset_unlocks_next_round(self) -> None:
        from spacegame.models.legendary_effects import (
            consume_phase_shift,
            reset_phase_shift_for_round,
        )

        state = LegendaryState(phase_shift_interval=3)
        assert consume_phase_shift(state, round_number=3) is True
        assert consume_phase_shift(state, round_number=3) is False

        # end_round resets
        reset_phase_shift_for_round(state)
        # On next shift round (6), the dodge is available again
        assert consume_phase_shift(state, round_number=6) is True

    def test_off_interval_rounds_still_do_not_fire(self) -> None:
        """Consume on a non-interval round must not succeed, and must not
        burn the flag for the next valid round."""
        from spacegame.models.legendary_effects import consume_phase_shift

        state = LegendaryState(phase_shift_interval=3)
        assert consume_phase_shift(state, round_number=1) is False
        assert consume_phase_shift(state, round_number=2) is False
        # Round 3 still has its dodge
        assert consume_phase_shift(state, round_number=3) is True
