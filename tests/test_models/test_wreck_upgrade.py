"""Tests for Wreck Upgrade system — salvage intel and upgrade progression."""

import pytest

from spacegame.models.wreck_upgrade import (
    calculate_intel_earned,
    WreckUpgrade,
    WreckUpgradeState,
)


def _make_upgrades() -> dict[str, WreckUpgrade]:
    """Create test upgrade definitions."""
    return {
        "signal_amplifier": WreckUpgrade(
            id="signal_amplifier",
            name="Signal Amplifier",
            description="+1 scan charge per level",
            max_level=5,
            costs=[5, 10, 18, 28, 42],
            effect_type="extra_charges_bonus",
            effect_per_level=1.0,
        ),
        "quick_extract": WreckUpgrade(
            id="quick_extract",
            name="Quick Extract",
            description="+8% extraction speed per level",
            max_level=5,
            costs=[6, 12, 20, 32, 48],
            effect_type="extract_speed_bonus",
            effect_per_level=0.08,
        ),
    }


class TestCalculateIntelEarned:
    """Tests for intel earning formula."""

    def test_deck_1_base(self) -> None:
        # floor(1 * 1.2) = 1
        assert calculate_intel_earned(1) == 1

    def test_deck_5_base(self) -> None:
        # floor(5 * 1.2) = 6
        assert calculate_intel_earned(5) == 6

    def test_deck_10_base(self) -> None:
        # floor(10 * 1.2) = 12
        assert calculate_intel_earned(10) == 12

    def test_clear_bonus_at_80_percent(self) -> None:
        # deck 5: base=6, bonus=floor(5*0.8)=4, total=10
        assert calculate_intel_earned(5, extraction_ratio=0.80) == 10

    def test_no_bonus_below_80_percent(self) -> None:
        # deck 5: base=6, no bonus
        assert calculate_intel_earned(5, extraction_ratio=0.79) == 6

    def test_prestige_multiplier(self) -> None:
        # deck 5: base=6, mult=1.5 (prestige 5), total=9
        assert calculate_intel_earned(5, prestige_level=5) == 9

    def test_bonus_and_prestige_combined(self) -> None:
        # deck 5: base=6, bonus=4, subtotal=10, mult=1.2 (prestige 2), total=12
        assert calculate_intel_earned(5, extraction_ratio=0.90, prestige_level=2) == 12

    def test_deck_1_clear_bonus(self) -> None:
        # deck 1: base=1, bonus=floor(1*0.8)=0, total=1
        assert calculate_intel_earned(1, extraction_ratio=1.0) == 1

    def test_deck_3_clear_bonus(self) -> None:
        # deck 3: base=floor(3*1.2)=3, bonus=floor(3*0.8)=2, total=5
        assert calculate_intel_earned(3, extraction_ratio=0.85) == 5


class TestWreckUpgrade:
    """Tests for WreckUpgrade definition."""

    def test_create_upgrade(self) -> None:
        u = WreckUpgrade(
            id="test",
            name="Test",
            description="Test",
            max_level=3,
            costs=[5, 10, 20],
            effect_type="test_bonus",
            effect_per_level=0.1,
        )
        assert u.id == "test"
        assert u.max_level == 3

    def test_costs_length_validation(self) -> None:
        with pytest.raises(ValueError, match="costs length"):
            WreckUpgrade(
                id="bad",
                name="Bad",
                description="Bad",
                max_level=3,
                costs=[5, 10],
                effect_type="test",
                effect_per_level=0.1,
            )

    def test_get_cost_level_1(self) -> None:
        upgrades = _make_upgrades()
        assert upgrades["signal_amplifier"].get_cost(1) == 5

    def test_get_cost_level_5(self) -> None:
        upgrades = _make_upgrades()
        assert upgrades["signal_amplifier"].get_cost(5) == 42

    def test_get_cost_beyond_max(self) -> None:
        upgrades = _make_upgrades()
        assert upgrades["signal_amplifier"].get_cost(6) is None

    def test_get_cost_level_0(self) -> None:
        upgrades = _make_upgrades()
        assert upgrades["signal_amplifier"].get_cost(0) is None

    def test_get_effect_at_level(self) -> None:
        upgrades = _make_upgrades()
        assert upgrades["quick_extract"].get_effect(3) == pytest.approx(0.24)

    def test_get_effect_at_zero(self) -> None:
        upgrades = _make_upgrades()
        assert upgrades["quick_extract"].get_effect(0) == 0.0


class TestWreckUpgradeState:
    """Tests for player upgrade state tracking."""

    def test_default_level_is_zero(self) -> None:
        state = WreckUpgradeState()
        assert state.get_level("signal_amplifier") == 0

    def test_purchase_success(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        success, msg, cost = state.purchase("signal_amplifier", upgrades, 100)
        assert success
        assert cost == 5
        assert state.get_level("signal_amplifier") == 1

    def test_purchase_insufficient_intel(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        success, msg, cost = state.purchase("signal_amplifier", upgrades, 3)
        assert not success
        assert cost == 0
        assert "Need 5" in msg

    def test_purchase_max_level(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        for _ in range(5):
            state.purchase("signal_amplifier", upgrades, 100)
        success, msg, cost = state.purchase("signal_amplifier", upgrades, 100)
        assert not success
        assert "max level" in msg

    def test_purchase_unknown_upgrade(self) -> None:
        state = WreckUpgradeState()
        success, msg, cost = state.purchase("nonexistent", {}, 100)
        assert not success

    def test_get_effect(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        state.purchase("quick_extract", upgrades, 100)
        state.purchase("quick_extract", upgrades, 100)
        effect = state.get_effect("quick_extract", upgrades)
        assert effect == pytest.approx(0.16)

    def test_get_effect_unknown(self) -> None:
        state = WreckUpgradeState()
        assert state.get_effect("nonexistent", {}) == 0.0

    def test_total_invested(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        state.purchase("signal_amplifier", upgrades, 100)  # 5
        state.purchase("signal_amplifier", upgrades, 100)  # 10
        state.purchase("quick_extract", upgrades, 100)  # 6
        assert state.get_total_invested(upgrades) == 21

    def test_reset(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        state.purchase("signal_amplifier", upgrades, 100)
        state.reset()
        assert state.get_level("signal_amplifier") == 0

    def test_serialization_round_trip(self) -> None:
        state = WreckUpgradeState()
        upgrades = _make_upgrades()
        state.purchase("signal_amplifier", upgrades, 100)
        state.purchase("signal_amplifier", upgrades, 100)
        data = state.to_dict()
        restored = WreckUpgradeState.from_dict(data)
        assert restored.get_level("signal_amplifier") == 2

    def test_from_dict_empty(self) -> None:
        state = WreckUpgradeState.from_dict({})
        assert state.get_level("anything") == 0
