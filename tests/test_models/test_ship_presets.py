"""Tests for Phase A3 — Ship preset generation and migration.

Verifies that generated presets approximate legacy ShipType stats
and that player builder fields serialize correctly.
"""

from spacegame.models.ship_presets import (
    generate_preset_from_ship_type,
    get_preset_for_ship_type,
    _PRESET_MATERIALS,
)
from spacegame.models.ship_build import ShipBuild, ShipStatsComputer, WEIGHT_CLASSES
from spacegame.data_loader import get_data_loader


def _load_ship_types() -> dict:
    dl = get_data_loader()
    dl.load_ship_types()
    return dl.ship_types


class TestPresetGeneration:
    """Verify preset builds approximate legacy stats."""

    def test_generates_build_for_shuttle(self) -> None:
        ship_types = _load_ship_types()
        build = generate_preset_from_ship_type(ship_types["shuttle"])
        assert build is not None
        assert build.weight_class in WEIGHT_CLASSES
        assert len(build.pixels) > 0
        assert build.preset_name == "Shuttle"

    def test_generates_build_for_war_frigate(self) -> None:
        ship_types = _load_ship_types()
        build = generate_preset_from_ship_type(ship_types["war_frigate"])
        assert build is not None
        assert len(build.pixels) > 20
        assert build.preset_name == "War Frigate"

    def test_all_24_ships_generate_presets(self) -> None:
        ship_types = _load_ship_types()
        for ship_id, st in ship_types.items():
            build = generate_preset_from_ship_type(st)
            assert build is not None, f"Failed to generate preset for {ship_id}"
            assert len(build.pixels) >= 10, (
                f"{ship_id} preset has too few pixels: {len(build.pixels)}"
            )

    def test_preset_hull_within_tolerance(self) -> None:
        """Preset hull should be in a reasonable range vs original.

        We use a wide tolerance because the preset generator
        approximates stats — materials contribute hull as a side effect
        of shields/evasion pixels. The goal is a playable ship, not
        an exact stat match.
        """
        ship_types = _load_ship_types()
        for ship_id, st in ship_types.items():
            build = generate_preset_from_ship_type(st)
            stats = ShipStatsComputer.compute(build, _PRESET_MATERIALS)
            target = st.combat_hull
            if target <= 0:
                continue
            # Hull should be at least 30% of target and no more than 3x
            # (shield/evasion materials add hull as a bonus)
            assert stats.hull >= target * 0.3, (
                f"{ship_id}: hull {stats.hull} too low vs target {target}"
            )
            assert stats.hull <= target * 3.0, (
                f"{ship_id}: hull {stats.hull} too high vs target {target}"
            )

    def test_preset_weight_under_limit(self) -> None:
        """All presets should be within weight limit."""
        ship_types = _load_ship_types()
        for ship_id, st in ship_types.items():
            build = generate_preset_from_ship_type(st)
            stats = ShipStatsComputer.compute(build, _PRESET_MATERIALS)
            assert stats.weight_ratio <= 1.0, (
                f"{ship_id}: weight {stats.weight_current:.1f}/{stats.weight_max} "
                f"({stats.weight_ratio:.1%}) exceeds limit"
            )

    def test_preset_has_slots(self) -> None:
        """Presets should have at least a core slot."""
        ship_types = _load_ship_types()
        for ship_id, st in ship_types.items():
            build = generate_preset_from_ship_type(st)
            # Ships with weapon or defense slots should have some slots
            if st.weapon_slots > 0 or st.defense_slots > 0:
                assert len(build.slots) > 0, f"{ship_id} has no slots"

    def test_preset_serialization_round_trip(self) -> None:
        ship_types = _load_ship_types()
        build = generate_preset_from_ship_type(ship_types["shuttle"])
        data = build.to_dict()
        restored = ShipBuild.from_dict(data)
        assert restored.weight_class == build.weight_class
        assert len(restored.pixels) == len(build.pixels)
        assert restored.preset_name == build.preset_name


class TestGetPreset:
    """Test the convenience preset lookup."""

    def test_get_preset_for_known_ship(self) -> None:
        build = get_preset_for_ship_type("shuttle")
        assert build is not None
        assert build.preset_name == "Shuttle"

    def test_get_preset_for_unknown_ship(self) -> None:
        build = get_preset_for_ship_type("nonexistent_ship_xyz")
        assert build is None


class TestPlayerBuilderFields:
    """Verify player model has builder fields."""

    def test_default_unlocked_shapes(self) -> None:
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        st = ShipType(
            id="shuttle", name="Shuttle", ship_class="starter",
            description="test", cargo_capacity=50, fuel_capacity=100,
            fuel_efficiency=10, speed_multiplier=1.0, purchase_price=5000,
            resale_value=3500, crew_slots=1, special_abilities=[],
            availability="common",
        )
        ship = Ship(ship_type=st, current_fuel=100)
        p = Player(
            name="Test", credits=1000, current_system_id="nexus_prime",
            ship=ship,
        )
        assert len(p.unlocked_shapes) == 9
        assert "pixel" in p.unlocked_shapes
        assert "small_square" in p.unlocked_shapes

    def test_default_unlocked_materials(self) -> None:
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        st = ShipType(
            id="shuttle", name="Shuttle", ship_class="starter",
            description="test", cargo_capacity=50, fuel_capacity=100,
            fuel_efficiency=10, speed_multiplier=1.0, purchase_price=5000,
            resale_value=3500, crew_slots=1, special_abilities=[],
            availability="common",
        )
        ship = Ship(ship_type=st, current_fuel=100)
        p = Player(
            name="Test", credits=1000, current_system_id="nexus_prime",
            ship=ship,
        )
        assert len(p.unlocked_materials) == 3
        assert "light_alloy" in p.unlocked_materials

    def test_default_weight_class(self) -> None:
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        st = ShipType(
            id="shuttle", name="Shuttle", ship_class="starter",
            description="test", cargo_capacity=50, fuel_capacity=100,
            fuel_efficiency=10, speed_multiplier=1.0, purchase_price=5000,
            resale_value=3500, crew_slots=1, special_abilities=[],
            availability="common",
        )
        ship = Ship(ship_type=st, current_fuel=100)
        p = Player(
            name="Test", credits=1000, current_system_id="nexus_prime",
            ship=ship,
        )
        assert "tiny" in p.unlocked_weight_classes
