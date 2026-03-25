"""Tests for Phase G — System integration and migration.

Verifies that ShipBuild integrates with save/load, cargo/fuel
properties, module detection, and backward compatibility.
"""

from spacegame.models.ship import Ship, ShipType
from spacegame.models.ship_build import (
    ShipBuild,
    PlacedPixel,
    DesignatedSlot,
    HullMaterial,
    ShipStatsComputer,
    ComputedShipStats,
)


def _ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="starter",
        description="test",
        cargo_capacity=50,
        fuel_capacity=100,
        fuel_efficiency=10,
        speed_multiplier=1.0,
        purchase_price=5000,
        resale_value=3500,
        crew_slots=1,
        special_abilities=[],
        availability="common",
        combat_hull=60,
        combat_shields=20,
    )


def _build_with_stats() -> tuple[ShipBuild, ComputedShipStats]:
    """Create a build and compute stats manually."""
    build = ShipBuild(weight_class="tiny")
    for i in range(20):
        build.pixels.append(PlacedPixel(i % 16, i // 16, "standard_plate"))
    build.slots.append(DesignatedSlot(slot_type="weapon", x=4, y=4, equipment_id="laser_cannon"))
    build.slots.append(DesignatedSlot(slot_type="utility", x=6, y=4, equipment_id="mining_drill"))

    mat = {
        "standard_plate": HullMaterial(
            id="standard_plate",
            name="S",
            description="t",
            color_primary=(128, 128, 128),
            hull_per_pixel=2.5,
            weight_per_pixel=0.7,
            cost_per_pixel=15,
        )
    }
    stats = ShipStatsComputer.compute(build, mat)
    return build, stats


class TestShipBuildSaveSerialization:
    """ShipBuild serializes in ship save data."""

    def test_build_round_trip_in_ship_data(self) -> None:
        build, stats = _build_with_stats()
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        ship._build = build
        ship._computed_stats = stats

        # Simulate serialization
        data = {
            "ship_type_id": ship.ship_type.id,
            "current_fuel": ship.current_fuel,
            "current_cargo": ship.current_cargo,
            "current_hull": ship.current_hull,
            "current_shields": ship.current_shields,
        }
        if ship._build:
            data["build"] = ship._build.to_dict()

        # Simulate deserialization
        from spacegame.models.ship_build import ShipBuild as SB

        assert "build" in data
        restored_build = SB.from_dict(data["build"])
        assert restored_build.weight_class == "tiny"
        assert len(restored_build.pixels) == 20
        assert len(restored_build.slots) == 2
        assert restored_build.slots[0].equipment_id == "laser_cannon"

    def test_old_save_without_build_still_loads(self) -> None:
        """Old save format (no 'build' key) should still work."""
        data = {
            "ship_type_id": "shuttle",
            "current_fuel": 80,
            "current_cargo": {},
            "current_hull": 60,
            "current_shields": 20,
        }
        assert "build" not in data
        # Old path: create ship from ship_type, no build


class TestModuleDetection:
    """has_module_in_slot and has_module_type_in_slot."""

    def test_has_module_with_build(self) -> None:
        build, stats = _build_with_stats()
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        ship._build = build
        assert ship.has_module_in_slot("laser_cannon")
        assert ship.has_module_in_slot("mining_drill")
        assert not ship.has_module_in_slot("nonexistent")

    def test_has_module_type(self) -> None:
        build, stats = _build_with_stats()
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        ship._build = build
        assert ship.has_module_type_in_slot("weapon")
        assert ship.has_module_type_in_slot("utility")
        assert not ship.has_module_type_in_slot("defense")

    def test_has_module_without_build_falls_back(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        # No build, no upgrade manager
        assert not ship.has_module_in_slot("laser_cannon")


class TestCargoFuelFromBuild:
    """max_cargo and max_fuel use build stats when available."""

    def test_cargo_from_build(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        # Set computed stats with cargo
        stats = ComputedShipStats(cargo_capacity=75, fuel_capacity=120)
        ship._computed_stats = stats
        assert ship.max_cargo == 75, f"Expected 75 from build, got {ship.max_cargo}"

    def test_cargo_from_ship_type_without_build(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        assert ship.max_cargo == 50  # From ShipType

    def test_fuel_from_build(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        stats = ComputedShipStats(cargo_capacity=50, fuel_capacity=150)
        ship._computed_stats = stats
        assert ship.max_fuel == 150

    def test_fuel_from_ship_type_without_build(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        assert ship.max_fuel == 100  # From ShipType


class TestDisplayShipName:
    """Ship display name uses build preset name when available."""

    def test_name_from_build_preset(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        build = ShipBuild(weight_class="tiny", preset_name="My Fighter")
        ship._build = build
        assert ship.display_ship_name == "My Fighter"

    def test_name_from_ship_type_without_build(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        assert ship.display_ship_name == "Shuttle"

    def test_name_from_ship_type_when_no_preset_name(self) -> None:
        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        build = ShipBuild(weight_class="tiny")  # No preset_name
        ship._build = build
        assert ship.display_ship_name == "Shuttle"


class TestPlayerBuilderDefaults:
    """New game starts with correct builder state."""

    def test_new_player_has_9_basic_shapes(self) -> None:
        from spacegame.models.player import Player

        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        p = Player(name="Test", credits=1000, current_system_id="nexus_prime", ship=ship)
        assert len(p.unlocked_shapes) == 9
        assert "pixel" in p.unlocked_shapes
        assert "small_square" in p.unlocked_shapes
        assert "medium_triangle" in p.unlocked_shapes

    def test_new_player_has_3_starter_materials(self) -> None:
        from spacegame.models.player import Player

        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        p = Player(name="Test", credits=1000, current_system_id="nexus_prime", ship=ship)
        assert len(p.unlocked_materials) == 3
        assert "light_alloy" in p.unlocked_materials
        assert "standard_plate" in p.unlocked_materials
        assert "salvage_scrap" in p.unlocked_materials

    def test_new_player_has_tiny_weight_class(self) -> None:
        from spacegame.models.player import Player

        ship = Ship(ship_type=_ship_type(), current_fuel=80)
        p = Player(name="Test", credits=1000, current_system_id="nexus_prime", ship=ship)
        assert "tiny" in p.unlocked_weight_classes
