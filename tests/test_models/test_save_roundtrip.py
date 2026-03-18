"""Comprehensive save/load round-trip tests.

Verifies that all serialized subsystems survive a save/load cycle.
"""

import json
import tempfile
from pathlib import Path

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.progression import PlayerProgression
from spacegame.save_manager import SaveManager


def _get_real_ship_type() -> ShipType:
    """Get a real ship type from DataLoader (shuttle — starter ship)."""
    dl = get_data_loader()
    return dl.ship_types["shuttle"]


def _make_loaded_player() -> Player:
    """Create a fully-loaded player with state across all subsystems."""
    ship_type = _get_real_ship_type()
    ship = Ship(ship_type=ship_type, current_fuel=40)
    ship.current_cargo = {"metals": 10, "luxury_goods": 5}
    ship.cargo_purchase_prices = {"metals": 800, "luxury_goods": 2500}
    ship.current_hull = 80
    ship.current_shields = 30

    player = Player(
        name="TestPilot",
        credits=15000,
        current_system_id="nexus_prime",
        ship=ship,
    )

    # Lifetime stats
    player.game_day = 42
    player.total_profit = 25000
    player.trades_completed = 18
    player.systems_visited = {"nexus_prime", "breakstone", "stellaris_port"}
    player.credits_earned_lifetime = 100000
    player.credits_spent_lifetime = 75000
    player.largest_single_profit = 5000
    player.jumps_traveled = 30
    player.fuel_consumed = 60
    player.ore_mined = 200
    player.items_salvaged = 15
    player.items_refined = 8

    # Achievement state
    player.unlocked_achievements = ["first_trade", "deep_miner"]

    # Minigame stats
    player.max_mining_depth = 7
    player.total_chains_triggered = 12
    player.rare_ores_mined = 3
    player.salvage_sessions_completed = 5
    player.corrupted_items_extracted = 2
    player.refining_jobs_completed = 4
    player.batch_jobs_queued = 6
    player.recipes_crafted = {"alloy_plating", "refined_crystal"}
    player.investments_owned = 2
    player.s_ranks_earned = 1

    # Faction reputation
    player.faction_reputation = {
        "commerce_guild": 45,
        "miners_union": 20,
        "frontier_alliance": -10,
    }
    player.faction_assignments = {"commerce_guild": "trader"}

    # Dialogue flags
    player.dialogue_flags = {"met_elena": True, "intro_complete": True}

    # Trade permits
    player.trade_permits = {"commerce_guild", "miners_union"}
    player.black_market_access = {"crimson_reach"}

    # Mission state (opaque dict)
    player.mission_state = {
        "active": ["rescue_miners"],
        "completed": ["first_delivery"],
    }

    # Crew state (opaque dict)
    player.crew_state = {"elena_reeves": {"loyalty": 65, "level": 2}}

    # Social state
    player.social_state = {"haggle_level": 2}

    # Attribute state
    player.attribute_state = {"charisma": 3, "perception": 2}

    # Journal state
    player.journal_state = {"entries": ["Day 1: Arrived at Nexus Prime"]}

    # Ground equipment
    player.ground_equipment = ["light_armor", "scanner"]

    # Smuggling stats
    player.criminal_heat = 15
    player.goods_smuggled = 8
    player.smuggling_contracts_completed = 3
    player.times_caught_smuggling = 1
    player.inspections_passed_with_contraband = 4
    player.max_criminal_heat_reached = 25
    player.smuggling_contract_state = {"active": ["run_spice"]}

    # Ground contract state
    player.ground_contract_state = {"active": ["salvage_op"]}

    # Political state
    player.political_state = {"last_election_day": 30}

    # Ground exploration stats
    player.ground_missions_completed = 5
    player.ground_missions_failed = 1
    player.ground_enemies_defeated = 12
    player.ground_enemies_talked = 3
    player.ground_tiles_explored = 45
    player.ground_undetected_completions = 2
    player.ground_campaign_missions_completed = 3

    # Combat stats
    player.combats_won = 7
    player.combats_fled = 2
    player.combats_negotiated = 1
    player.combats_bribed = 1

    # Mission stats
    player.side_missions_completed = 4
    player.crew_quests_completed = 1
    player.encounters_survived = 10

    # Previous system
    player.previous_system_id = "breakstone"

    return player


class TestPlayerSerializationRoundTrip:
    """Test that _serialize_player -> _deserialize_player preserves all fields."""

    def _round_trip(self, player: Player) -> Player:
        """Serialize and deserialize a player through SaveManager."""
        mgr = SaveManager()
        data = mgr._serialize_player(player)
        # Ensure JSON-serializable (catches set/tuple issues)
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        return mgr._deserialize_player(restored_data)

    def test_basic_fields(self) -> None:
        """Name, credits, system, game_day survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.name == "TestPilot"
        assert restored.credits == 15000
        assert restored.current_system_id == "nexus_prime"
        assert restored.game_day == 42

    def test_ship_state(self) -> None:
        """Ship fuel, cargo, hull, shields survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.ship.current_fuel == 40
        assert restored.ship.current_cargo == {"metals": 10, "luxury_goods": 5}
        assert restored.ship.cargo_purchase_prices == {"metals": 800, "luxury_goods": 2500}
        assert restored.ship.current_hull == 80
        assert restored.ship.current_shields == 30

    def test_trade_stats(self) -> None:
        """Trading statistics survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.total_profit == 25000
        assert restored.trades_completed == 18
        assert restored.credits_earned_lifetime == 100000
        assert restored.credits_spent_lifetime == 75000
        assert restored.largest_single_profit == 5000

    def test_systems_visited(self) -> None:
        """Visited systems set survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.systems_visited == {"nexus_prime", "breakstone", "stellaris_port"}

    def test_travel_stats(self) -> None:
        """Jump and fuel stats survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.jumps_traveled == 30
        assert restored.fuel_consumed == 60

    def test_minigame_stats(self) -> None:
        """Mining, salvage, refining stats survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.ore_mined == 200
        assert restored.items_salvaged == 15
        assert restored.items_refined == 8
        assert restored.max_mining_depth == 7
        assert restored.total_chains_triggered == 12
        assert restored.rare_ores_mined == 3
        assert restored.salvage_sessions_completed == 5
        assert restored.corrupted_items_extracted == 2
        assert restored.refining_jobs_completed == 4
        assert restored.batch_jobs_queued == 6
        assert restored.recipes_crafted == {"alloy_plating", "refined_crystal"}
        assert restored.investments_owned == 2
        assert restored.s_ranks_earned == 1

    def test_achievement_state(self) -> None:
        """Unlocked achievements survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.unlocked_achievements == ["first_trade", "deep_miner"]

    def test_faction_reputation(self) -> None:
        """Faction rep and assignments survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.faction_reputation == {
            "commerce_guild": 45,
            "miners_union": 20,
            "frontier_alliance": -10,
        }
        assert restored.faction_assignments == {"commerce_guild": "trader"}

    def test_dialogue_flags(self) -> None:
        """Dialogue flags survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.dialogue_flags == {"met_elena": True, "intro_complete": True}

    def test_trade_permits(self) -> None:
        """Trade permits and black market access survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.trade_permits == {"commerce_guild", "miners_union"}
        assert restored.black_market_access == {"crimson_reach"}

    def test_mission_state(self) -> None:
        """Mission state dict survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.mission_state == {
            "active": ["rescue_miners"],
            "completed": ["first_delivery"],
        }

    def test_crew_state(self) -> None:
        """Crew state dict survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.crew_state == {"elena_reeves": {"loyalty": 65, "level": 2}}

    def test_social_and_attribute_state(self) -> None:
        """Social and attribute state dicts survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.social_state == {"haggle_level": 2}
        assert restored.attribute_state == {"charisma": 3, "perception": 2}

    def test_journal_state(self) -> None:
        """Journal state survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.journal_state == {"entries": ["Day 1: Arrived at Nexus Prime"]}

    def test_ground_equipment(self) -> None:
        """Ground equipment inventory survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.ground_equipment == ["light_armor", "scanner"]

    def test_smuggling_stats(self) -> None:
        """All smuggling stats survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.criminal_heat == 15
        assert restored.goods_smuggled == 8
        assert restored.smuggling_contracts_completed == 3
        assert restored.times_caught_smuggling == 1
        assert restored.inspections_passed_with_contraband == 4
        assert restored.max_criminal_heat_reached == 25
        assert restored.smuggling_contract_state == {"active": ["run_spice"]}

    def test_ground_contract_state(self) -> None:
        """Ground contract state survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.ground_contract_state == {"active": ["salvage_op"]}

    def test_political_state(self) -> None:
        """Political state survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.political_state == {"last_election_day": 30}

    def test_ground_exploration_stats(self) -> None:
        """All ground exploration stats survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.ground_missions_completed == 5
        assert restored.ground_missions_failed == 1
        assert restored.ground_enemies_defeated == 12
        assert restored.ground_enemies_talked == 3
        assert restored.ground_tiles_explored == 45
        assert restored.ground_undetected_completions == 2
        assert restored.ground_campaign_missions_completed == 3

    def test_combat_stats(self) -> None:
        """Combat stats survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.combats_won == 7
        assert restored.combats_fled == 2
        assert restored.combats_negotiated == 1
        assert restored.combats_bribed == 1

    def test_mission_stats(self) -> None:
        """Mission completion stats survive round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.side_missions_completed == 4
        assert restored.crew_quests_completed == 1
        assert restored.encounters_survived == 10

    def test_previous_system_id(self) -> None:
        """Previous system ID survives round-trip."""
        player = _make_loaded_player()
        restored = self._round_trip(player)
        assert restored.previous_system_id == "breakstone"

    def test_empty_player_defaults(self) -> None:
        """A minimal player round-trips with correct defaults."""
        ship = Ship(ship_type=_get_real_ship_type(), current_fuel=50)
        player = Player(name="Blank", credits=0, current_system_id="nexus_prime", ship=ship)
        restored = self._round_trip(player)
        assert restored.name == "Blank"
        assert restored.credits == 0
        assert restored.trades_completed == 0
        assert restored.faction_reputation == {}
        assert restored.dialogue_flags == {}
        assert restored.crew_state == {}
        assert restored.ground_missions_completed == 0
        assert restored.combats_won == 0

    def test_json_serializable(self) -> None:
        """Fully loaded player serializes to valid JSON without errors."""
        player = _make_loaded_player()
        mgr = SaveManager()
        data = mgr._serialize_player(player)
        # Should not raise
        json_str = json.dumps(data)
        assert len(json_str) > 100, "JSON should contain substantial data"
        parsed = json.loads(json_str)
        assert parsed["name"] == "TestPilot"


class TestShipSerializationRoundTrip:
    """Test ship serialization specifically."""

    def test_ship_type_preserved(self) -> None:
        """Ship type ID is preserved through round-trip."""
        ship = Ship(ship_type=_get_real_ship_type(), current_fuel=40)
        mgr = SaveManager()
        data = mgr._serialize_ship(ship)
        assert data["ship_type_id"] == "shuttle"

    def test_cargo_preserved(self) -> None:
        """Cargo and purchase prices survive serialization."""
        ship = Ship(ship_type=_get_real_ship_type(), current_fuel=40)
        ship.current_cargo = {"metals": 10}
        ship.cargo_purchase_prices = {"metals": 500}
        mgr = SaveManager()
        data = mgr._serialize_ship(ship)
        assert data["current_cargo"] == {"metals": 10}
        assert data["cargo_purchase_prices"] == {"metals": 500}

    def test_combat_state_preserved(self) -> None:
        """Hull and shields are serialized."""
        ship = Ship(ship_type=_get_real_ship_type(), current_fuel=40)
        ship.current_hull = 75
        ship.current_shields = 25
        mgr = SaveManager()
        data = mgr._serialize_ship(ship)
        assert data["current_hull"] == 75
        assert data["current_shields"] == 25
