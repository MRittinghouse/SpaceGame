"""
Tests for mining drone models.
"""

import pytest
from spacegame.models.drone import (
    DroneTier,
    DRONE_TIER_CONFIGS,
    MiningDrone,
    MiningDroneFleet,
    apply_drone_skill_effects,
)
from spacegame.models.mining import RockType

# === MiningDrone Tests ===


class TestMiningDrone:
    """Tests for MiningDrone dataclass."""

    def test_creation_basic(self) -> None:
        drone = MiningDrone(tier=DroneTier.BASIC)
        assert drone.tier == DroneTier.BASIC
        assert drone.target_preference is None

    def test_tier_basic_properties(self) -> None:
        drone = MiningDrone(tier=DroneTier.BASIC)
        assert drone.mining_speed == 0.3
        assert drone.yield_bonus == 0.0
        assert drone.can_target is False

    def test_tier_advanced_properties(self) -> None:
        drone = MiningDrone(tier=DroneTier.ADVANCED)
        assert drone.mining_speed == 0.6
        assert drone.yield_bonus == 0.0
        assert drone.can_target is True

    def test_tier_elite_properties(self) -> None:
        drone = MiningDrone(tier=DroneTier.ELITE)
        assert drone.mining_speed == 1.0
        assert drone.yield_bonus == 0.25
        assert drone.can_target is True

    def test_set_target_preference_advanced(self) -> None:
        drone = MiningDrone(tier=DroneTier.ADVANCED)
        success, msg = drone.set_target_preference(RockType.IRON)
        assert success
        assert drone.target_preference == RockType.IRON

    def test_set_target_basic_fails(self) -> None:
        drone = MiningDrone(tier=DroneTier.BASIC)
        success, msg = drone.set_target_preference(RockType.IRON)
        assert not success
        assert drone.target_preference is None

    def test_clear_target(self) -> None:
        drone = MiningDrone(tier=DroneTier.ADVANCED)
        drone.set_target_preference(RockType.CRYSTAL)
        success, msg = drone.set_target_preference(None)
        assert success
        assert drone.target_preference is None

    def test_to_dict(self) -> None:
        drone = MiningDrone(tier=DroneTier.ELITE, target_preference=RockType.RARE)
        data = drone.to_dict()
        assert data["tier"] == 3
        assert data["target_preference"] == "rare"

    def test_to_dict_no_preference(self) -> None:
        drone = MiningDrone(tier=DroneTier.BASIC)
        data = drone.to_dict()
        assert data["target_preference"] is None

    def test_from_dict(self) -> None:
        data = {"tier": 2, "target_preference": "iron"}
        drone = MiningDrone.from_dict(data)
        assert drone.tier == DroneTier.ADVANCED
        assert drone.target_preference == RockType.IRON

    def test_from_dict_no_preference(self) -> None:
        data = {"tier": 1, "target_preference": None}
        drone = MiningDrone.from_dict(data)
        assert drone.tier == DroneTier.BASIC
        assert drone.target_preference is None

    def test_round_trip(self) -> None:
        original = MiningDrone(tier=DroneTier.ELITE, target_preference=RockType.CRYSTAL)
        restored = MiningDrone.from_dict(original.to_dict())
        assert restored.tier == original.tier
        assert restored.target_preference == original.target_preference


# === MiningDroneFleet Tests ===


class TestMiningDroneFleet:
    """Tests for MiningDroneFleet."""

    def test_empty_fleet(self) -> None:
        fleet = MiningDroneFleet()
        assert fleet.slot_count == 0
        assert fleet.max_slots == 0
        assert fleet.available_slots == 0

    def test_add_drone_success(self) -> None:
        fleet = MiningDroneFleet(max_slots=2)
        drone = MiningDrone(tier=DroneTier.BASIC)
        success, msg = fleet.add_drone(drone)
        assert success
        assert fleet.slot_count == 1
        assert fleet.available_slots == 1

    def test_add_drone_no_slots(self) -> None:
        fleet = MiningDroneFleet(max_slots=0)
        drone = MiningDrone(tier=DroneTier.BASIC)
        success, msg = fleet.add_drone(drone)
        assert not success
        assert fleet.slot_count == 0

    def test_add_drone_full(self) -> None:
        fleet = MiningDroneFleet(max_slots=1)
        fleet.add_drone(MiningDrone(tier=DroneTier.BASIC))
        success, msg = fleet.add_drone(MiningDrone(tier=DroneTier.ADVANCED))
        assert not success
        assert fleet.slot_count == 1

    def test_remove_drone(self) -> None:
        fleet = MiningDroneFleet(max_slots=2)
        fleet.add_drone(MiningDrone(tier=DroneTier.BASIC))
        fleet.add_drone(MiningDrone(tier=DroneTier.ADVANCED))
        success, msg = fleet.remove_drone(0)
        assert success
        assert fleet.slot_count == 1
        assert fleet.drones[0].tier == DroneTier.ADVANCED

    def test_remove_invalid_index(self) -> None:
        fleet = MiningDroneFleet(max_slots=1)
        success, msg = fleet.remove_drone(0)
        assert not success

    def test_get_active_drones(self) -> None:
        fleet = MiningDroneFleet(max_slots=2)
        fleet.add_drone(MiningDrone(tier=DroneTier.BASIC))
        fleet.add_drone(MiningDrone(tier=DroneTier.ELITE))
        drones = fleet.get_active_drones()
        assert len(drones) == 2
        # Returns a copy, not the original list
        drones.pop()
        assert fleet.slot_count == 2

    def test_to_dict(self) -> None:
        fleet = MiningDroneFleet(max_slots=2)
        fleet.add_drone(MiningDrone(tier=DroneTier.BASIC))
        data = fleet.to_dict()
        assert data["max_slots"] == 2
        assert len(data["drones"]) == 1

    def test_from_dict(self) -> None:
        data = {
            "max_slots": 3,
            "drones": [
                {"tier": 1, "target_preference": None},
                {"tier": 2, "target_preference": "iron"},
            ],
        }
        fleet = MiningDroneFleet.from_dict(data)
        assert fleet.max_slots == 3
        assert fleet.slot_count == 2
        assert fleet.drones[0].tier == DroneTier.BASIC
        assert fleet.drones[1].target_preference == RockType.IRON

    def test_from_dict_empty(self) -> None:
        fleet = MiningDroneFleet.from_dict({})
        assert fleet.max_slots == 0
        assert fleet.slot_count == 0

    def test_round_trip(self) -> None:
        fleet = MiningDroneFleet(max_slots=3)
        fleet.add_drone(MiningDrone(tier=DroneTier.BASIC))
        fleet.add_drone(MiningDrone(tier=DroneTier.ELITE, target_preference=RockType.RARE))
        restored = MiningDroneFleet.from_dict(fleet.to_dict())
        assert restored.max_slots == fleet.max_slots
        assert restored.slot_count == fleet.slot_count
        assert restored.drones[1].target_preference == RockType.RARE


# === apply_drone_skill_effects Tests ===


class TestApplyDroneSkillEffects:
    """Tests for skill-driven drone granting."""

    def _make_player(self):
        """Create a minimal player for testing."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="test_ship",
            name="Test Ship",
            ship_class="starter",
            description="Test",
            cargo_capacity=100,
            fuel_capacity=100,
            fuel_efficiency=1,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=0,
            special_abilities=[],
            availability="common",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        return Player(
            name="Test",
            credits=1000,
            current_system_id="test",
            ship=ship,
        )

    def test_no_skills_no_drones(self) -> None:
        player = self._make_player()
        apply_drone_skill_effects(player)
        assert player.drone_fleet.max_slots == 0
        assert player.drone_fleet.slot_count == 0

    def test_drone_fleet_lv1_grants_basic(self) -> None:
        player = self._make_player()
        player.progression.skills["drone_fleet"].current_level = 1
        apply_drone_skill_effects(player)
        assert player.drone_fleet.max_slots == 1
        assert player.drone_fleet.slot_count == 1
        assert player.drone_fleet.drones[0].tier == DroneTier.BASIC

    def test_drone_fleet_lv2_grants_advanced(self) -> None:
        player = self._make_player()
        player.progression.skills["drone_fleet"].current_level = 2
        apply_drone_skill_effects(player)
        assert player.drone_fleet.max_slots == 2
        assert player.drone_fleet.slot_count == 2
        assert player.drone_fleet.drones[0].tier == DroneTier.BASIC
        assert player.drone_fleet.drones[1].tier == DroneTier.ADVANCED

    def test_drone_fleet_lv3_grants_all(self) -> None:
        player = self._make_player()
        player.progression.skills["drone_fleet"].current_level = 3
        apply_drone_skill_effects(player)
        assert player.drone_fleet.max_slots == 3
        assert player.drone_fleet.slot_count == 3
        assert player.drone_fleet.drones[0].tier == DroneTier.BASIC
        assert player.drone_fleet.drones[1].tier == DroneTier.ADVANCED
        assert player.drone_fleet.drones[2].tier == DroneTier.ELITE

    def test_idempotent(self) -> None:
        player = self._make_player()
        player.progression.skills["drone_fleet"].current_level = 1
        apply_drone_skill_effects(player)
        apply_drone_skill_effects(player)
        assert player.drone_fleet.slot_count == 1, "Should not duplicate drones"

    def test_from_loaded_state(self) -> None:
        """Works correctly when fleet was already loaded from save."""
        player = self._make_player()
        # Simulate loaded state: fleet already has a drone
        player.drone_fleet.max_slots = 1
        player.drone_fleet.drones.append(MiningDrone(tier=DroneTier.BASIC))
        player.progression.skills["drone_fleet"].current_level = 1
        apply_drone_skill_effects(player)
        assert player.drone_fleet.slot_count == 1, "Should not add duplicate"
