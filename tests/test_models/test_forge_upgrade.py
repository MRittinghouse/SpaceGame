"""Tests for Forge upgrade system — refining-specific persistent upgrades."""

import pytest

from spacegame.models.forge_upgrade import (
    ForgeUpgrade,
    ForgeUpgradeState,
    calculate_forge_tokens,
)


class TestForgeTokenCalculation:
    """Tests for forge token earning formulas."""

    def test_basic_recipe(self) -> None:
        # 5s time, 1 input, mastery 0 -> base=max(1, floor(5/5))=1, complexity=0, total=1
        assert calculate_forge_tokens(5.0, 1) == 1

    def test_complex_recipe(self) -> None:
        # 30s time, 3 inputs, mastery 0
        # base=max(1, floor(30/5))=6, complexity=max(0, 3-1)=2, total=8
        assert calculate_forge_tokens(30.0, 3) == 8

    def test_mastery_bonus(self) -> None:
        # mastery_level=3 adds +1
        without = calculate_forge_tokens(5.0, 1, mastery_level=0)
        with_mastery = calculate_forge_tokens(5.0, 1, mastery_level=3)
        assert with_mastery == without + 1

    def test_token_earn_bonus(self) -> None:
        # 30s, 3 inputs -> base 8, with 0.30 bonus -> floor(8 * 1.3) = 10
        assert calculate_forge_tokens(30.0, 3, token_earn_bonus=0.30) == 10


class TestForgeUpgrade:
    """Tests for forge upgrade definition dataclass."""

    def _make_upgrade(self) -> ForgeUpgrade:
        return ForgeUpgrade(
            id="flux_capacitor",
            name="Flux Capacitor",
            description="+10% refine speed per level",
            max_level=5,
            costs=[3, 7, 12, 20, 30],
            effect_type="refine_speed_bonus",
            effect_per_level=0.10,
        )

    def test_create_upgrade(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.id == "flux_capacitor"
        assert upgrade.name == "Flux Capacitor"
        assert upgrade.max_level == 5
        assert upgrade.effect_type == "refine_speed_bonus"
        assert upgrade.effect_per_level == 0.10

    def test_costs_length_validation(self) -> None:
        with pytest.raises(ValueError):
            ForgeUpgrade(
                id="bad",
                name="Bad",
                description="Mismatched",
                max_level=3,
                costs=[5, 10],  # Only 2 costs for 3 levels
                effect_type="test",
                effect_per_level=1.0,
            )

    def test_get_cost_valid(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.get_cost(1) == 3
        assert upgrade.get_cost(2) == 7
        assert upgrade.get_cost(5) == 30

    def test_get_cost_beyond_max(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.get_cost(6) is None

    def test_get_effect(self) -> None:
        upgrade = self._make_upgrade()
        assert upgrade.get_effect(0) == 0.0
        assert upgrade.get_effect(1) == pytest.approx(0.10)
        assert upgrade.get_effect(3) == pytest.approx(0.30)


class TestForgeUpgradeState:
    """Tests for player's forge upgrade state tracking."""

    def _make_upgrades(self) -> dict[str, ForgeUpgrade]:
        return {
            "flux_capacitor": ForgeUpgrade(
                id="flux_capacitor",
                name="Flux Capacitor",
                description="+10% refine speed per level",
                max_level=5,
                costs=[3, 7, 12, 20, 30],
                effect_type="refine_speed_bonus",
                effect_per_level=0.10,
            ),
            "yield_amplifier": ForgeUpgrade(
                id="yield_amplifier",
                name="Yield Amplifier",
                description="+5% output yield per level",
                max_level=5,
                costs=[4, 9, 16, 25, 38],
                effect_type="output_yield_bonus",
                effect_per_level=0.05,
            ),
        }

    def test_purchase_success(self) -> None:
        state = ForgeUpgradeState()
        upgrades = self._make_upgrades()
        success, msg, cost = state.purchase("flux_capacitor", upgrades, forge_tokens_available=100)
        assert success, msg
        assert cost == 3
        assert state.get_level("flux_capacitor") == 1

    def test_purchase_insufficient(self) -> None:
        state = ForgeUpgradeState()
        upgrades = self._make_upgrades()
        success, msg, cost = state.purchase("flux_capacitor", upgrades, forge_tokens_available=1)
        assert not success
        assert cost == 0

    def test_purchase_max_level(self) -> None:
        state = ForgeUpgradeState()
        upgrades = self._make_upgrades()
        state._levels["flux_capacitor"] = 5
        success, msg, cost = state.purchase(
            "flux_capacitor", upgrades, forge_tokens_available=1000
        )
        assert not success
        assert cost == 0

    def test_serialization_round_trip(self) -> None:
        state = ForgeUpgradeState()
        state._levels["flux_capacitor"] = 3
        state._levels["yield_amplifier"] = 1
        data = state.to_dict()
        restored = ForgeUpgradeState.from_dict(data)
        assert restored.get_level("flux_capacitor") == 3
        assert restored.get_level("yield_amplifier") == 1
