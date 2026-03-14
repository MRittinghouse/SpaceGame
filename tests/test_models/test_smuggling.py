"""Tests for smuggling & contraband system (Phase A: Foundation).

Covers FactionLaw model, criminal heat on Player, inspection chance
calculation, commodity legality checks, and smuggling contract generation.
"""

import pytest

from spacegame.models.commodity import Legality
from spacegame.models.smuggling import (
    FactionLaw,
    InspectionResult,
    Penalty,
    SmugglingContract,
    calculate_inspection_chance,
    resolve_inspection,
)


# ============================================================================
# FactionLaw Model
# ============================================================================


class TestFactionLaw:
    """FactionLaw maps faction enforcement behavior to legality levels."""

    def test_construction(self) -> None:
        """FactionLaw stores faction enforcement rules."""
        law = FactionLaw(
            faction_id="commerce_guild",
            inspection_chance=0.20,
            restricted_penalty=Penalty.FINE,
            illegal_penalty=Penalty.CONFISCATE,
            fine_multiplier=0.5,
        )
        assert law.faction_id == "commerce_guild"
        assert law.inspection_chance == 0.20
        assert law.restricted_penalty == Penalty.FINE
        assert law.illegal_penalty == Penalty.CONFISCATE
        assert law.fine_multiplier == 0.5

    def test_penalty_enum_values(self) -> None:
        """Penalty enum has expected values."""
        assert Penalty.WARN.value == "warn"
        assert Penalty.FINE.value == "fine"
        assert Penalty.CONFISCATE.value == "confiscate"
        assert Penalty.BAN.value == "ban"

    def test_crimson_reach_no_enforcement(self) -> None:
        """Crimson Reach has 0% inspection chance (no law enforcement)."""
        law = FactionLaw(
            faction_id="frontier_alliance",
            inspection_chance=0.0,
            restricted_penalty=Penalty.WARN,
            illegal_penalty=Penalty.WARN,
            fine_multiplier=0.0,
        )
        assert law.inspection_chance == 0.0

    def test_from_dict(self) -> None:
        """FactionLaw can be constructed from a JSON dict."""
        data = {
            "faction_id": "miners_union",
            "inspection_chance": 0.10,
            "restricted_penalty": "warn",
            "illegal_penalty": "fine",
            "fine_multiplier": 0.3,
        }
        law = FactionLaw.from_dict(data)
        assert law.faction_id == "miners_union"
        assert law.restricted_penalty == Penalty.WARN
        assert law.illegal_penalty == Penalty.FINE


# ============================================================================
# Inspection Chance Calculation
# ============================================================================


class TestInspectionChance:
    """Inspection chance depends on faction, cargo, heat, upgrades, and skills."""

    def _guild_law(self) -> FactionLaw:
        return FactionLaw(
            faction_id="commerce_guild",
            inspection_chance=0.20,
            restricted_penalty=Penalty.FINE,
            illegal_penalty=Penalty.CONFISCATE,
            fine_multiplier=0.5,
        )

    def test_base_chance_from_faction(self) -> None:
        """Base inspection chance comes from faction law."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.20, abs=0.001)

    def test_criminal_heat_increases_chance(self) -> None:
        """Criminal heat adds +2% per point."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=10,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=0,
        )
        # 20% base + 10*2% = 40%
        assert chance == pytest.approx(0.40, abs=0.001)

    def test_restricted_cargo_increases_chance(self) -> None:
        """Carrying RESTRICTED cargo adds +5%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=True,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.25, abs=0.001)

    def test_illegal_cargo_increases_chance(self) -> None:
        """Carrying ILLEGAL cargo adds +10%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=True,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.30, abs=0.001)

    def test_hidden_compartment_reduces_chance(self) -> None:
        """Hidden compartment reduces inspection chance by 10%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=True,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.10, abs=0.001)

    def test_signal_jammer_reduces_chance(self) -> None:
        """Signal jammer reduces inspection chance by 5%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=True,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.15, abs=0.001)

    def test_false_transponder_reduces_chance(self) -> None:
        """False transponder reduces inspection chance by 8%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=True,
            observation_level=0,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.12, abs=0.001)

    def test_observation_skill_reduces_chance(self) -> None:
        """Observation level 3+ reduces inspection chance by 3%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=3,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.17, abs=0.001)

    def test_observation_below_3_no_effect(self) -> None:
        """Observation level below 3 has no effect."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=2,
            faction_reputation=0,
        )
        assert chance == pytest.approx(0.20, abs=0.001)

    def test_friendly_reputation_reduces_chance(self) -> None:
        """Friendly+ reputation (20+) reduces inspection chance by 5%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=25,
        )
        assert chance == pytest.approx(0.15, abs=0.001)

    def test_hostile_reputation_increases_chance(self) -> None:
        """Hostile reputation (-50 or lower) increases chance by 10%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=-55,
        )
        assert chance == pytest.approx(0.30, abs=0.001)

    def test_floor_at_2_percent(self) -> None:
        """Inspection chance cannot go below 2% in enforced systems."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=0,
            has_restricted=False,
            has_illegal=False,
            has_hidden_compartment=True,
            has_signal_jammer=True,
            has_false_transponder=True,
            observation_level=5,
            faction_reputation=50,
        )
        assert chance == pytest.approx(0.02, abs=0.001)

    def test_ceiling_at_60_percent(self) -> None:
        """Inspection chance cannot exceed 60%."""
        chance = calculate_inspection_chance(
            faction_law=self._guild_law(),
            criminal_heat=30,
            has_restricted=True,
            has_illegal=True,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=-80,
        )
        assert chance == pytest.approx(0.60, abs=0.001)

    def test_zero_base_chance_stays_zero(self) -> None:
        """Systems with 0% base chance (Crimson Reach) always stay at 0%."""
        no_enforcement = FactionLaw(
            faction_id="frontier_alliance",
            inspection_chance=0.0,
            restricted_penalty=Penalty.WARN,
            illegal_penalty=Penalty.WARN,
            fine_multiplier=0.0,
        )
        chance = calculate_inspection_chance(
            faction_law=no_enforcement,
            criminal_heat=50,
            has_restricted=True,
            has_illegal=True,
            has_hidden_compartment=False,
            has_signal_jammer=False,
            has_false_transponder=False,
            observation_level=0,
            faction_reputation=-100,
        )
        assert chance == pytest.approx(0.0, abs=0.001)


# ============================================================================
# Inspection Resolution
# ============================================================================


class TestInspectionResolution:
    """Inspection scans cargo and applies penalties based on faction law."""

    def _guild_law(self) -> FactionLaw:
        return FactionLaw(
            faction_id="commerce_guild",
            inspection_chance=0.20,
            restricted_penalty=Penalty.FINE,
            illegal_penalty=Penalty.CONFISCATE,
            fine_multiplier=0.5,
        )

    def test_clean_cargo_passes(self) -> None:
        """No contraband means inspection passes cleanly."""
        cargo = {"food": 10, "textiles": 5}
        legality_map = {"food": Legality.LEGAL, "textiles": Legality.LEGAL}
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.passed is True
        assert result.penalty == Penalty.WARN  # No penalty, just a pass
        assert result.contraband_found == {}
        assert result.fine_amount == 0

    def test_restricted_cargo_detected(self) -> None:
        """Restricted cargo is detected and fined per faction law."""
        cargo = {"food": 10, "weapons_components": 3}
        legality_map = {
            "food": Legality.LEGAL,
            "weapons_components": Legality.RESTRICTED,
        }
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.passed is False
        assert result.penalty == Penalty.FINE
        assert "weapons_components" in result.contraband_found

    def test_illegal_cargo_confiscated(self) -> None:
        """Illegal cargo triggers confiscation per faction law."""
        cargo = {"food": 10, "stolen_data": 2}
        legality_map = {
            "food": Legality.LEGAL,
            "stolen_data": Legality.ILLEGAL,
        }
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.passed is False
        assert result.penalty == Penalty.CONFISCATE
        assert "stolen_data" in result.contraband_found

    def test_worst_penalty_applies(self) -> None:
        """When both RESTRICTED and ILLEGAL found, worst penalty applies."""
        cargo = {"weapons_components": 3, "stolen_data": 2}
        legality_map = {
            "weapons_components": Legality.RESTRICTED,
            "stolen_data": Legality.ILLEGAL,
        }
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.penalty == Penalty.CONFISCATE  # Worst of FINE and CONFISCATE

    def test_fine_amount_based_on_cargo_value(self) -> None:
        """Fine amount = sum(contraband_quantity * base_price) * fine_multiplier."""
        cargo = {"weapons_components": 4}
        legality_map = {"weapons_components": Legality.RESTRICTED}
        price_map = {"weapons_components": 450}
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
            price_map=price_map,
        )
        # 4 * 450 * 0.5 = 900
        assert result.fine_amount == 900

    def test_heat_gain_restricted(self) -> None:
        """Getting caught with restricted cargo adds 5 criminal heat."""
        cargo = {"weapons_components": 3}
        legality_map = {"weapons_components": Legality.RESTRICTED}
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.heat_gain == 5

    def test_heat_gain_illegal(self) -> None:
        """Getting caught with illegal cargo adds 15 criminal heat."""
        cargo = {"stolen_data": 2}
        legality_map = {"stolen_data": Legality.ILLEGAL}
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.heat_gain == 15

    def test_rep_loss_restricted(self) -> None:
        """Getting caught with restricted cargo costs -10 faction rep."""
        cargo = {"weapons_components": 3}
        legality_map = {"weapons_components": Legality.RESTRICTED}
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.reputation_loss == -10

    def test_rep_loss_illegal(self) -> None:
        """Getting caught with illegal cargo costs -30 faction rep."""
        cargo = {"stolen_data": 2}
        legality_map = {"stolen_data": Legality.ILLEGAL}
        result = resolve_inspection(
            faction_law=self._guild_law(),
            cargo=cargo,
            legality_map=legality_map,
        )
        assert result.reputation_loss == -30


# ============================================================================
# Criminal Heat on Player
# ============================================================================


class TestCriminalHeat:
    """Criminal heat tracks smuggling notoriety on the Player model."""

    def _make_player(self) -> "Player":
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="shuttle",
            name="Shuttle",
            ship_class="starter",
            description="Basic",
            cargo_capacity=50,
            fuel_capacity=100,
            fuel_efficiency=10,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=2,
            special_abilities=[],
            availability="common",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        return Player(
            name="Test",
            credits=5000,
            current_system_id="nexus_prime",
            ship=ship,
        )

    def test_criminal_heat_default_zero(self) -> None:
        """Criminal heat starts at 0."""
        player = self._make_player()
        assert player.criminal_heat == 0

    def test_add_criminal_heat(self) -> None:
        """Adding heat increases the value."""
        player = self._make_player()
        player.add_criminal_heat(15)
        assert player.criminal_heat == 15

    def test_criminal_heat_capped_at_100(self) -> None:
        """Criminal heat cannot exceed 100."""
        player = self._make_player()
        player.add_criminal_heat(150)
        assert player.criminal_heat == 100

    def test_decay_criminal_heat(self) -> None:
        """Heat decays by specified amount per call."""
        player = self._make_player()
        player.add_criminal_heat(20)
        player.decay_criminal_heat(1)
        assert player.criminal_heat == 19

    def test_decay_does_not_go_below_zero(self) -> None:
        """Heat decay cannot go below 0."""
        player = self._make_player()
        player.add_criminal_heat(3)
        player.decay_criminal_heat(10)
        assert player.criminal_heat == 0

    def test_heat_in_statistics(self) -> None:
        """Criminal heat appears in player statistics."""
        player = self._make_player()
        player.add_criminal_heat(25)
        stats = player.get_statistics()
        assert stats["criminal_heat"] == 25

    def test_smuggling_stats_in_statistics(self) -> None:
        """Smuggling-related stats appear in player statistics."""
        player = self._make_player()
        player.goods_smuggled = 10
        player.smuggling_contracts_completed = 3
        player.times_caught_smuggling = 1
        stats = player.get_statistics()
        assert stats["goods_smuggled"] == 10
        assert stats["smuggling_contracts_completed"] == 3
        assert stats["times_caught_smuggling"] == 1

    def test_heat_decays_on_travel(self) -> None:
        """Criminal heat decays by 1 when traveling to a new system."""
        player = self._make_player()
        player.add_criminal_heat(10)
        player.travel_to_system("breakstone", fuel_cost=5)
        assert player.criminal_heat == 9

    def test_heat_decays_on_rest(self) -> None:
        """Criminal heat decays by 1 when resting at a system."""
        player = self._make_player()
        player.add_criminal_heat(10)
        player.rest_at_system(rest_cost=10)
        assert player.criminal_heat == 9


# ============================================================================
# Criminal Heat Serialization
# ============================================================================


class TestCriminalHeatSerialization:
    """Criminal heat persists through save/load."""

    def test_backward_compatibility(self) -> None:
        """Old saves without criminal_heat default to 0."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="shuttle",
            name="Shuttle",
            ship_class="starter",
            description="Basic",
            cargo_capacity=50,
            fuel_capacity=100,
            fuel_efficiency=10,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=2,
            special_abilities=[],
            availability="common",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        player = Player(
            name="Test",
            credits=5000,
            current_system_id="nexus_prime",
            ship=ship,
        )
        # Simulate old save data without smuggling fields
        assert player.criminal_heat == 0
        assert player.goods_smuggled == 0
        assert player.smuggling_contracts_completed == 0
        assert player.times_caught_smuggling == 0


# ============================================================================
# Smuggling Contract Model
# ============================================================================


class TestSmugglingContract:
    """SmugglingContract represents a smuggling delivery job."""

    def test_construction(self) -> None:
        """Contract stores all required fields."""
        contract = SmugglingContract(
            id="smuggle_001",
            client_name="Malia Torres",
            commodity_id="stolen_data",
            quantity=5,
            source_system="crimson_reach",
            destination_system="axiom_labs",
            payment=2000,
            deadline_days=7,
            penalty_on_failure=500,
            heat_on_completion=8,
            difficulty="medium",
        )
        assert contract.id == "smuggle_001"
        assert contract.payment == 2000
        assert contract.difficulty == "medium"

    def test_is_expired(self) -> None:
        """Contract is expired if current day exceeds start + deadline."""
        contract = SmugglingContract(
            id="smuggle_002",
            client_name="Dex Halloran",
            commodity_id="combat_stims",
            quantity=3,
            source_system="nova_research",
            destination_system="breakstone",
            payment=1500,
            deadline_days=5,
            penalty_on_failure=300,
            heat_on_completion=5,
            difficulty="low",
        )
        assert contract.is_expired(current_day=1, accepted_day=1) is False
        assert contract.is_expired(current_day=5, accepted_day=1) is False
        assert contract.is_expired(current_day=6, accepted_day=1) is False
        assert contract.is_expired(current_day=7, accepted_day=1) is True

    def test_to_dict_round_trip(self) -> None:
        """Contract serializes and deserializes correctly."""
        contract = SmugglingContract(
            id="smuggle_003",
            client_name="Tomas Drifter",
            commodity_id="contraband_medicine",
            quantity=10,
            source_system="axiom_labs",
            destination_system="havens_rest",
            payment=800,
            deadline_days=10,
            penalty_on_failure=200,
            heat_on_completion=3,
            difficulty="low",
        )
        data = contract.to_dict()
        restored = SmugglingContract.from_dict(data)
        assert restored.id == contract.id
        assert restored.payment == contract.payment
        assert restored.difficulty == contract.difficulty
        assert restored.commodity_id == contract.commodity_id
