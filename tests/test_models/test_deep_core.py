"""Tests for Deep Core upgrade system — mining-specific persistent upgrades."""

import pytest

from spacegame.models.deep_core import (
    DeepCoreUpgrade,
    DeepCoreUpgradeState,
    calculate_strata_earned,
)


class TestStrataCalculation:
    """Tests for strata token earning formulas."""

    def test_depth_1_earns_1(self) -> None:
        # max(1, floor(1 * 0.15)) = max(1, 0) = 1
        assert calculate_strata_earned(1) == 1

    def test_depth_50_earns_7(self) -> None:
        # max(1, floor(50 * 0.15)) = 7
        assert calculate_strata_earned(50) == 7

    def test_depth_100_earns_22(self) -> None:
        # base=max(1, floor(100*0.15))=15, depth_mult=1.5 (Deep Core) -> 22
        assert calculate_strata_earned(100) == 22

    def test_depth_150_earns_44(self) -> None:
        # base=max(1, floor(150*0.15))=22, depth_mult=2.0 (Abyssal) -> 44
        assert calculate_strata_earned(150) == 44

    def test_depth_200_earns_60(self) -> None:
        # base=max(1, floor(200*0.15))=30, depth_mult=2.0 (Abyssal) -> 60
        assert calculate_strata_earned(200) == 60

    def test_shallow_depth_no_multiplier(self) -> None:
        # base=max(1, floor(50*0.15))=7, depth_mult=1.0 -> 7
        assert calculate_strata_earned(50) == 7

    def test_full_clear_bonus(self) -> None:
        base = calculate_strata_earned(100)
        with_bonus = calculate_strata_earned(100, full_clear=True)
        # base=15, bonus=floor(100*0.05)=5, subtotal=20, depth_mult=1.5 -> 30
        assert with_bonus == 30
        assert with_bonus > base

    def test_prestige_multiplier(self) -> None:
        base = calculate_strata_earned(100)
        with_prestige = calculate_strata_earned(100, prestige_level=5)
        # base=15, depth_mult=1.5 -> 22 (no prestige)
        # With prestige: 15 * 1.5 * 1.5 = 33
        assert with_prestige == 33

    def test_full_clear_and_prestige_stack(self) -> None:
        result = calculate_strata_earned(100, full_clear=True, prestige_level=2)
        # base=15, bonus=5, subtotal=20, depth_mult=1.5, prestige=1.2
        # 20 * 1.5 * 1.2 = 36
        assert result == 36


class TestDeepCoreUpgrade:
    """Tests for upgrade definition dataclass."""

    def _make_upgrade(self) -> DeepCoreUpgrade:
        return DeepCoreUpgrade(
            id="core_resonance",
            name="Core Resonance",
            description="+8% click power per level",
            max_level=5,
            costs=[5, 10, 18, 28, 42],
            effect_type="click_power_bonus",
            effect_per_level=0.08,
        )

    def test_cost_for_level(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.get_cost(1) == 5
        assert upgrade.get_cost(2) == 10
        assert upgrade.get_cost(5) == 42

    def test_cost_beyond_max_returns_none(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.get_cost(6) is None

    def test_effect_at_level(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.get_effect(0) == 0.0
        assert upgrade.get_effect(1) == pytest.approx(0.08)
        assert upgrade.get_effect(3) == pytest.approx(0.24)

    def test_costs_length_must_match_max_level(self) -> None:
        with pytest.raises(ValueError):
            DeepCoreUpgrade(
                id="bad",
                name="Bad",
                description="Mismatched",
                max_level=3,
                costs=[5, 10],  # Only 2 costs for 3 levels
                effect_type="test",
                effect_per_level=1.0,
            )


class TestDeepCoreUpgradeState:
    """Tests for player's upgrade state tracking."""

    def _make_upgrades(self) -> dict[str, DeepCoreUpgrade]:
        return {
            "core_resonance": DeepCoreUpgrade(
                id="core_resonance",
                name="Core Resonance",
                description="+8% click power per level",
                max_level=5,
                costs=[5, 10, 18, 28, 42],
                effect_type="click_power_bonus",
                effect_per_level=0.08,
            ),
            "energy_conduit": DeepCoreUpgrade(
                id="energy_conduit",
                name="Energy Conduit",
                description="+3 max energy per level",
                max_level=5,
                costs=[6, 12, 20, 32, 48],
                effect_type="max_energy_bonus",
                effect_per_level=3.0,
            ),
            "silo_expansion": DeepCoreUpgrade(
                id="silo_expansion",
                name="Silo Expansion",
                description="+50 silo capacity per level",
                max_level=5,
                costs=[8, 15, 25, 40, 60],
                effect_type="silo_capacity_bonus",
                effect_per_level=50.0,
            ),
        }

    def test_initial_levels_are_zero(self) -> None:
        state = DeepCoreUpgradeState()
        assert state.get_level("core_resonance") == 0

    def test_purchase_upgrade(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        success, msg, cost = state.purchase("core_resonance", upgrades, strata_available=100)
        assert success, msg
        assert cost == 5
        assert state.get_level("core_resonance") == 1

    def test_purchase_deducts_correct_cost(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        # Buy level 1
        state.purchase("core_resonance", upgrades, strata_available=100)
        # Buy level 2 should cost 10
        success, msg, cost = state.purchase("core_resonance", upgrades, strata_available=100)
        assert success
        assert cost == 10
        assert state.get_level("core_resonance") == 2

    def test_purchase_fails_insufficient_strata(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        success, msg, cost = state.purchase("core_resonance", upgrades, strata_available=3)
        assert not success
        assert cost == 0

    def test_purchase_fails_at_max_level(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        # Force to max
        state._levels["core_resonance"] = 5
        success, msg, cost = state.purchase("core_resonance", upgrades, strata_available=1000)
        assert not success

    def test_purchase_fails_unknown_upgrade(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        success, msg, cost = state.purchase("nonexistent", upgrades, strata_available=100)
        assert not success

    def test_get_effect(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        state._levels["core_resonance"] = 3
        effect = state.get_effect("core_resonance", upgrades)
        assert effect == pytest.approx(0.24)

    def test_get_effect_zero_for_unpurchased(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        assert state.get_effect("core_resonance", upgrades) == 0.0

    def test_reset_clears_all_levels(self) -> None:
        state = DeepCoreUpgradeState()
        state._levels["core_resonance"] = 3
        state._levels["energy_conduit"] = 2
        state.reset()
        assert state.get_level("core_resonance") == 0
        assert state.get_level("energy_conduit") == 0

    def test_get_total_invested(self) -> None:
        state = DeepCoreUpgradeState()
        upgrades = self._make_upgrades()
        state.purchase("core_resonance", upgrades, strata_available=100)
        state.purchase("core_resonance", upgrades, strata_available=100)
        # Level 1 cost 5, level 2 cost 10 = 15 total
        assert state.get_total_invested(upgrades) == 15

    def test_to_dict_round_trip(self) -> None:
        state = DeepCoreUpgradeState()
        state._levels["core_resonance"] = 3
        state._levels["energy_conduit"] = 1
        data = state.to_dict()
        restored = DeepCoreUpgradeState.from_dict(data)
        assert restored.get_level("core_resonance") == 3
        assert restored.get_level("energy_conduit") == 1

    def test_empty_state_to_dict(self) -> None:
        state = DeepCoreUpgradeState()
        data = state.to_dict()
        restored = DeepCoreUpgradeState.from_dict(data)
        assert len(restored._levels) == 0
