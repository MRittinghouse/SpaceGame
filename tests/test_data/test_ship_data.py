"""
Tests for the complete ship roster (24 ships).

Validates stats, tier distribution, faction gates, and design invariants.
"""

import pytest
from spacegame.data_loader import get_data_loader


@pytest.fixture()
def ships() -> dict:
    dl = get_data_loader()
    dl.load_ship_types()
    return dl.ship_types


class TestShipCount:
    def test_total_ship_count(self, ships: dict) -> None:
        assert len(ships) == 24

    def test_starter_count(self, ships: dict) -> None:
        starters = [s for s in ships.values() if s.ship_class == "starter"]
        assert len(starters) == 1

    def test_early_game_count(self, ships: dict) -> None:
        early = [s for s in ships.values() if s.ship_class == "early_game"]
        assert len(early) == 3

    def test_mid_game_count(self, ships: dict) -> None:
        mid = [s for s in ships.values() if s.ship_class == "mid_game"]
        assert len(mid) == 8

    def test_late_game_count(self, ships: dict) -> None:
        late = [s for s in ships.values() if s.ship_class == "late_game"]
        assert len(late) == 8

    def test_faction_count(self, ships: dict) -> None:
        faction = [s for s in ships.values() if s.ship_class == "faction"]
        assert len(faction) == 4


class TestShipIdentities:
    """Verify key ships exist with expected IDs."""

    EXPECTED_IDS = [
        "shuttle",
        "light_freighter",
        "prospector",
        "patrol_cutter",
        "medium_freighter",
        "fast_courier",
        "armed_trader",
        "scout_vessel",
        "corsair",
        "mining_barge",
        "smugglers_sloop",
        "salvage_rig",
        "bulk_hauler",
        "luxury_yacht",
        "clipper",
        "war_frigate",
        "deep_explorer",
        "phantom",
        "industrial_titan",
        "diplomatic_cruiser",
        "consortium_merchantman",
        "syndicate_enforcer",
        "frontier_runner",
        "institute_vessel",
    ]

    def test_all_expected_ships_exist(self, ships: dict) -> None:
        for ship_id in self.EXPECTED_IDS:
            assert ship_id in ships, f"Missing ship: {ship_id}"


class TestShipStats:
    """Validate stat ranges and design invariants."""

    def test_all_ships_have_positive_cargo(self, ships: dict) -> None:
        for sid, s in ships.items():
            assert s.cargo_capacity > 0, f"{sid} should have positive cargo"

    def test_all_ships_have_positive_fuel(self, ships: dict) -> None:
        for sid, s in ships.items():
            assert s.fuel_capacity > 0, f"{sid} should have positive fuel"

    def test_all_ships_have_positive_hull(self, ships: dict) -> None:
        for sid, s in ships.items():
            assert s.combat_hull > 0, f"{sid} should have positive hull"

    def test_all_ships_have_positive_price(self, ships: dict) -> None:
        for sid, s in ships.items():
            assert s.purchase_price > 0, f"{sid} needs a purchase price"

    def test_resale_less_than_purchase(self, ships: dict) -> None:
        for sid, s in ships.items():
            assert s.resale_value < s.purchase_price, f"{sid} resale >= purchase"

    def test_total_slots_reasonable(self, ships: dict) -> None:
        for sid, s in ships.items():
            total = s.weapon_slots + s.defense_slots + s.utility_slots
            assert 3 <= total <= 12, f"{sid} has {total} total slots"

    def test_speed_multiplier_range(self, ships: dict) -> None:
        for sid, s in ships.items():
            assert 0.3 <= s.speed_multiplier <= 3.0, f"{sid} speed out of range"


class TestFactionShips:
    """Validate faction ship gating."""

    def test_faction_ships_have_faction_required(self, ships: dict) -> None:
        faction_ships = [s for s in ships.values() if s.ship_class == "faction"]
        for s in faction_ships:
            assert s.faction_required is not None, f"{s.id} missing faction_required"
            assert s.faction_rep_required >= 50, f"{s.id} rep too low"

    def test_non_faction_ships_no_gate(self, ships: dict) -> None:
        non_faction = [s for s in ships.values() if s.ship_class != "faction"]
        for s in non_faction:
            assert s.faction_required is None, f"{s.id} shouldn't have faction gate"

    def test_consortium_merchantman(self, ships: dict) -> None:
        s = ships["consortium_merchantman"]
        assert s.faction_required == "nexus_trade"
        assert "tariff_immunity" in s.special_abilities

    def test_syndicate_enforcer(self, ships: dict) -> None:
        s = ships["syndicate_enforcer"]
        assert s.faction_required == "forgeworks_industrial"
        assert "hull_regen" in s.special_abilities

    def test_frontier_runner(self, ships: dict) -> None:
        s = ships["frontier_runner"]
        assert s.faction_required == "free_salvagers"
        assert "salvage_mastery" in s.special_abilities

    def test_institute_vessel(self, ships: dict) -> None:
        s = ships["institute_vessel"]
        assert s.faction_required == "axiom_research"
        assert "quantum_sensors" in s.special_abilities


class TestDesignTradeoffs:
    """Verify no ship is strictly better than all others at its tier."""

    def test_corsair_high_weapons_low_cargo(self, ships: dict) -> None:
        s = ships["corsair"]
        assert s.weapon_slots == 4  # +1 from slot expansion
        assert s.cargo_capacity <= 150  # 3x balanced for mid-game frame

    def test_mining_barge_low_weapons(self, ships: dict) -> None:
        s = ships["mining_barge"]
        assert s.weapon_slots == 1  # +1 from slot expansion (was 0)
        assert s.utility_slots == 6  # +1 from slot expansion

    def test_phantom_fastest_but_fragile(self, ships: dict) -> None:
        s = ships["phantom"]
        assert s.speed_multiplier >= 2.0
        assert s.combat_hull <= 80

    def test_industrial_titan_slowest_most_utility(self, ships: dict) -> None:
        s = ships["industrial_titan"]
        assert s.speed_multiplier <= 0.6
        assert s.utility_slots == 7  # +1 from slot expansion
        assert s.weapon_slots == 1  # +1 from slot expansion (was 0)

    def test_war_frigate_most_combat_slots(self, ships: dict) -> None:
        s = ships["war_frigate"]
        assert s.weapon_slots == 5  # +1 from slot expansion
        assert s.defense_slots == 4  # +1 from slot expansion

    def test_deep_explorer_max_fuel(self, ships: dict) -> None:
        s = ships["deep_explorer"]
        assert s.fuel_capacity == 500
