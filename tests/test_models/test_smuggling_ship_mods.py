"""Tests for smuggling ship modifications (Phase D).

Covers hidden compartment mechanics, cargo split logic,
hidden hold detection during inspections, and smuggling upgrade effects.
"""

import pytest

from spacegame.models.smuggling import (
    HiddenCompartment,
    calculate_hidden_scan_chance,
    resolve_inspection_with_hidden,
    FactionLaw,
    Penalty,
    InspectionResult,
)
from spacegame.models.commodity import Legality


# ============================================================================
# Hidden Compartment Model
# ============================================================================


class TestHiddenCompartment:
    """HiddenCompartment splits cargo between main and hidden holds."""

    def test_capacity_is_30_percent_of_total(self) -> None:
        """Hidden hold capacity = 30% of ship cargo, rounded down."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        assert comp.hidden_capacity == 30

    def test_capacity_rounds_down(self) -> None:
        """Fractional capacity rounds down."""
        comp = HiddenCompartment(total_cargo_capacity=50)
        assert comp.hidden_capacity == 15

    def test_minimum_capacity_is_3(self) -> None:
        """Hidden capacity cannot be less than 3."""
        comp = HiddenCompartment(total_cargo_capacity=5)
        assert comp.hidden_capacity == 3

    def test_main_hold_capacity_reduced(self) -> None:
        """Main hold capacity = total - hidden."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        assert comp.main_capacity == 70

    def test_empty_at_creation(self) -> None:
        """Both holds start empty."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        assert comp.hidden_cargo == {}
        assert comp.hidden_used == 0

    def test_add_to_hidden(self) -> None:
        """Can add cargo to hidden hold."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        success, msg = comp.add_to_hidden("stolen_data", 5)
        assert success is True
        assert comp.hidden_cargo["stolen_data"] == 5
        assert comp.hidden_used == 5

    def test_add_exceeds_hidden_capacity(self) -> None:
        """Cannot exceed hidden hold capacity."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        success, msg = comp.add_to_hidden("stolen_data", 50)
        assert success is False
        assert comp.hidden_used == 0

    def test_remove_from_hidden(self) -> None:
        """Can remove cargo from hidden hold."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        comp.add_to_hidden("stolen_data", 10)
        success, msg = comp.remove_from_hidden("stolen_data", 5)
        assert success is True
        assert comp.hidden_cargo["stolen_data"] == 5

    def test_remove_more_than_available_fails(self) -> None:
        """Cannot remove more cargo than is in the hidden hold."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        comp.add_to_hidden("stolen_data", 5)
        success, msg = comp.remove_from_hidden("stolen_data", 10)
        assert success is False

    def test_remove_nonexistent_fails(self) -> None:
        """Cannot remove cargo that isn't in hidden hold."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        success, msg = comp.remove_from_hidden("stolen_data", 1)
        assert success is False

    def test_remove_all_cleans_up(self) -> None:
        """Removing all of a commodity removes the key."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        comp.add_to_hidden("stolen_data", 5)
        comp.remove_from_hidden("stolen_data", 5)
        assert "stolen_data" not in comp.hidden_cargo
        assert comp.hidden_used == 0

    def test_multiple_commodities(self) -> None:
        """Hidden hold can contain multiple commodity types."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        comp.add_to_hidden("stolen_data", 10)
        comp.add_to_hidden("combat_stims", 5)
        assert comp.hidden_used == 15
        assert comp.hidden_cargo["stolen_data"] == 10
        assert comp.hidden_cargo["combat_stims"] == 5

    def test_serialization_round_trip(self) -> None:
        """to_dict/from_dict preserves state."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        comp.add_to_hidden("stolen_data", 10)
        comp.add_to_hidden("combat_stims", 5)

        data = comp.to_dict()
        restored = HiddenCompartment.from_dict(data)

        assert restored.total_cargo_capacity == 100
        assert restored.hidden_cargo == {"stolen_data": 10, "combat_stims": 5}
        assert restored.hidden_used == 15


# ============================================================================
# Hidden Hold Scan Detection
# ============================================================================


class TestHiddenScanChance:
    """Hidden hold has a separate, lower detection chance during inspections."""

    def test_base_scan_chance_is_30_percent(self) -> None:
        """Base hidden hold detection is 30%."""
        chance = calculate_hidden_scan_chance(
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
        )
        assert chance == pytest.approx(0.30, abs=0.01)

    def test_signal_jammer_reduces_chance(self) -> None:
        """Signal jammer reduces hidden scan chance by 5%."""
        chance = calculate_hidden_scan_chance(
            has_signal_jammer=True,
            has_false_transponder=False,
            observation_level=0,
        )
        assert chance == pytest.approx(0.25, abs=0.01)

    def test_false_transponder_reduces_chance(self) -> None:
        """False transponder reduces hidden scan chance by 8%."""
        chance = calculate_hidden_scan_chance(
            has_signal_jammer=False,
            has_false_transponder=True,
            observation_level=0,
        )
        assert chance == pytest.approx(0.22, abs=0.01)

    def test_observation_level_3_reduces_chance(self) -> None:
        """Observation level 3+ reduces hidden scan chance by 5%."""
        chance = calculate_hidden_scan_chance(
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=3,
        )
        assert chance == pytest.approx(0.25, abs=0.01)

    def test_all_modifiers_stack(self) -> None:
        """All modifiers reduce scan chance additively."""
        chance = calculate_hidden_scan_chance(
            has_signal_jammer=True,
            has_false_transponder=True,
            observation_level=4,
        )
        # 0.30 - 0.05 - 0.08 - 0.05 = 0.12
        assert chance == pytest.approx(0.12, abs=0.01)

    def test_chance_has_floor(self) -> None:
        """Scan chance cannot go below 5%."""
        chance = calculate_hidden_scan_chance(
            has_signal_jammer=True,
            has_false_transponder=True,
            observation_level=5,
        )
        assert chance >= 0.05


# ============================================================================
# Inspection with Hidden Compartment
# ============================================================================


class TestInspectionWithHidden:
    """Inspections scan main hold always; hidden hold only sometimes."""

    def _make_law(self) -> FactionLaw:
        return FactionLaw(
            faction_id="commerce_guild",
            inspection_chance=0.20,
            restricted_penalty=Penalty.FINE,
            illegal_penalty=Penalty.CONFISCATE,
            fine_multiplier=0.5,
        )

    def test_clean_main_hidden_not_scanned(self) -> None:
        """If main hold is clean and hidden isn't scanned, pass."""
        law = self._make_law()
        result = resolve_inspection_with_hidden(
            faction_law=law,
            main_cargo={"food_rations": 10},
            hidden_cargo={"stolen_data": 5},
            legality_map={"food_rations": Legality.LEGAL, "stolen_data": Legality.ILLEGAL},
            price_map={"stolen_data": 600},
            hidden_scanned=False,
        )
        assert result.passed is True

    def test_clean_main_hidden_scanned_finds_contraband(self) -> None:
        """If hidden IS scanned and has contraband, double penalties."""
        law = self._make_law()
        result = resolve_inspection_with_hidden(
            faction_law=law,
            main_cargo={"food_rations": 10},
            hidden_cargo={"stolen_data": 5},
            legality_map={"food_rations": Legality.LEGAL, "stolen_data": Legality.ILLEGAL},
            price_map={"stolen_data": 600},
            hidden_scanned=True,
        )
        assert result.passed is False
        assert result.hidden_penalty_doubled is True
        # Fine should be doubled: 5 * 600 * 0.5 = 1500, doubled = 3000
        assert result.fine_amount == 3000

    def test_main_contraband_always_found(self) -> None:
        """Contraband in main hold is always detected."""
        law = self._make_law()
        result = resolve_inspection_with_hidden(
            faction_law=law,
            main_cargo={"combat_stims": 3},
            hidden_cargo={},
            legality_map={"combat_stims": Legality.ILLEGAL},
            price_map={"combat_stims": 350},
            hidden_scanned=False,
        )
        assert result.passed is False
        assert result.hidden_penalty_doubled is False

    def test_both_holds_scanned_combines_contraband(self) -> None:
        """When both holds have contraband and hidden is scanned, combine."""
        law = self._make_law()
        result = resolve_inspection_with_hidden(
            faction_law=law,
            main_cargo={"combat_stims": 3},
            hidden_cargo={"stolen_data": 5},
            legality_map={
                "combat_stims": Legality.ILLEGAL,
                "stolen_data": Legality.ILLEGAL,
            },
            price_map={"combat_stims": 350, "stolen_data": 600},
            hidden_scanned=True,
        )
        assert result.passed is False
        assert "combat_stims" in result.contraband_found
        assert "stolen_data" in result.contraband_found

    def test_hidden_scanned_but_clean_passes(self) -> None:
        """If hidden is scanned but has only legal goods, pass."""
        law = self._make_law()
        result = resolve_inspection_with_hidden(
            faction_law=law,
            main_cargo={"food_rations": 10},
            hidden_cargo={"water": 5},
            legality_map={"food_rations": Legality.LEGAL, "water": Legality.LEGAL},
            price_map={},
            hidden_scanned=True,
        )
        assert result.passed is True

    def test_hidden_doubled_heat(self) -> None:
        """Hidden contraband found doubles heat gain."""
        law = self._make_law()
        result = resolve_inspection_with_hidden(
            faction_law=law,
            main_cargo={},
            hidden_cargo={"stolen_data": 5},
            legality_map={"stolen_data": Legality.ILLEGAL},
            price_map={"stolen_data": 600},
            hidden_scanned=True,
        )
        # Normal illegal heat = 15, doubled = 30
        assert result.heat_gain == 30
        assert result.hidden_penalty_doubled is True


# ============================================================================
# Hidden Compartment Serialization on Player
# ============================================================================


class TestHiddenCompartmentSerialization:
    """Hidden compartment state serializes through Player."""

    def test_empty_compartment_serializes(self) -> None:
        """Empty hidden compartment serializes cleanly."""
        comp = HiddenCompartment(total_cargo_capacity=100)
        data = comp.to_dict()
        assert data["total_cargo_capacity"] == 100
        assert data["hidden_cargo"] == {}

    def test_default_no_compartment(self) -> None:
        """from_dict with empty dict returns None (no compartment)."""
        result = HiddenCompartment.from_dict({})
        assert result.total_cargo_capacity == 0
        assert result.hidden_capacity == 0
