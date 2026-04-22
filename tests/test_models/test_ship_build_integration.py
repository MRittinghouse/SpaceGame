"""Tests for Phase A2 — Ship model transition.

Verifies that ShipBuild integrates with the existing Ship model,
combat state initialization, and data loading.
"""

from unittest.mock import MagicMock
from spacegame.models.ship import Ship, ShipType
from spacegame.models.ship_build import (
    ShipBuild,
    PlacedPixel,
    HullMaterial,
    ShipStatsComputer,
    ComputedShipStats,
)


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="starter",
        description="A basic ship.",
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
        combat_energy=8,
        combat_energy_regen=3,
        combat_speed=12,
        combat_evasion=25,
        combat_accuracy=65,
    )


def _make_build() -> ShipBuild:
    """Create a simple test build with some pixels."""
    build = ShipBuild(weight_class="tiny")
    for i in range(20):
        build.pixels.append(PlacedPixel(i % 16, i // 16, "standard_plate"))
    return build


def _make_materials() -> dict[str, HullMaterial]:
    return {
        "standard_plate": HullMaterial(
            id="standard_plate",
            name="Standard",
            description="test",
            shade_band="steel",
            hull_per_pixel=2.5,
            weight_per_pixel=0.7,
            cost_per_pixel=15,
        ),
    }


class TestShipBuildOnShipModel:
    """Verify ShipBuild integrates with Ship."""

    def test_ship_without_build_uses_ship_type(self) -> None:
        """No build → old path: stats from ShipType."""
        st = _make_ship_type()
        ship = Ship(ship_type=st, current_fuel=100)
        assert ship.computed_stats is None
        assert ship.max_cargo == 50  # From ShipType

    def test_ship_with_build_has_computed_stats(self) -> None:
        """With build set → computed stats available."""
        st = _make_ship_type()
        ship = Ship(ship_type=st, current_fuel=100)
        build = _make_build()

        # Manually set computed stats (bypass data loader dependency)
        stats = ShipStatsComputer.compute(build, _make_materials())
        ship._build = build
        ship._computed_stats = stats

        assert ship.computed_stats is not None
        assert ship.computed_stats.hull == 50  # 20 pixels * 2.5 hull

    def test_build_property_accessible(self) -> None:
        st = _make_ship_type()
        ship = Ship(ship_type=st, current_fuel=100)
        assert ship.build is None
        ship._build = _make_build()
        assert ship.build is not None
        assert ship.build.weight_class == "tiny"


class TestBuildCombatStatePath:
    """Verify build_player_combat_state uses build stats when available."""

    def test_combat_state_from_build(self) -> None:
        from spacegame.models.combat import build_player_combat_state

        st = _make_ship_type()
        ship = Ship(ship_type=st, current_fuel=100)
        build = _make_build()
        stats = ShipStatsComputer.compute(build, _make_materials())
        ship._build = build
        ship._computed_stats = stats
        ship.current_hull = stats.hull
        ship.current_shields = stats.shields

        um = MagicMock()
        um.get_combat_moves.return_value = []
        um.get_bonus.return_value = 0.0

        state = build_player_combat_state(ship, um, None, {})
        # Should use computed stats (50 hull from build, not 60 from ShipType)
        assert state.max_hull == 50, f"Expected 50 from build, got {state.max_hull}"

    def test_combat_state_falls_back_to_ship_type(self) -> None:
        from spacegame.models.combat import build_player_combat_state

        st = _make_ship_type()
        ship = Ship(ship_type=st, current_fuel=100)
        # No build set → should use ShipType

        um = MagicMock()
        um.get_combat_moves.return_value = []
        um.get_bonus.return_value = 0.0

        state = build_player_combat_state(ship, um, None, {})
        assert state.max_hull == 60, f"Expected 60 from ShipType, got {state.max_hull}"


class TestDataLoaderShapes:
    """Verify shapes and materials load from JSON."""

    def test_load_shapes(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_hull_shapes()
        assert len(dl.hull_shapes) == 56, f"Expected 56 shapes, got {len(dl.hull_shapes)}"
        assert "pixel" in dl.hull_shapes
        assert "small_square" in dl.hull_shapes
        assert dl.hull_shapes["bar"].pixel_count == 3

    def test_load_materials(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_hull_materials()
        assert len(dl.hull_materials) == 16, f"Expected 16 materials, got {len(dl.hull_materials)}"
        assert "light_alloy" in dl.hull_materials
        assert "standard_plate" in dl.hull_materials
        assert "salvage_scrap" in dl.hull_materials
        mat = dl.hull_materials["standard_plate"]
        assert mat.hull_per_pixel == 2.5
        assert mat.weight_per_pixel == 0.25  # Reduced for builder freedom
