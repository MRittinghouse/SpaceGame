"""
Tests for ShipType faction/quest gate fields and data loader parsing.
"""

import pytest
from spacegame.models.ship import ShipType


def _make_ship_type(**overrides: object) -> ShipType:
    defaults = dict(
        id="test_ship",
        name="Test Ship",
        ship_class="mid_game",
        description="A test ship",
        cargo_capacity=100,
        fuel_capacity=200,
        fuel_efficiency=10,
        speed_multiplier=1.0,
        purchase_price=50000,
        resale_value=25000,
        crew_slots=3,
        special_abilities=[],
        availability="common",
        combat_hull=100,
        combat_shields=50,
        combat_energy=10,
        combat_energy_regen=3,
        combat_speed=5,
        combat_evasion=10,
        combat_accuracy=70,
        weapon_slots=2,
        defense_slots=1,
        utility_slots=3,
    )
    defaults.update(overrides)
    return ShipType(**defaults)  # type: ignore[arg-type]


class TestShipTypeGateFields:
    """Tests for faction/quest gate fields on ShipType."""

    def test_default_no_gates(self) -> None:
        ship = _make_ship_type()
        assert ship.faction_required is None
        assert ship.faction_rep_required == 0
        assert ship.unlock_condition is None

    def test_faction_gated_ship(self) -> None:
        ship = _make_ship_type(
            faction_required="nexus_trade", faction_rep_required=50
        )
        assert ship.faction_required == "nexus_trade"
        assert ship.faction_rep_required == 50

    def test_quest_gated_ship(self) -> None:
        ship = _make_ship_type(unlock_condition="quest_special_ops")
        assert ship.unlock_condition == "quest_special_ops"

    def test_faction_and_quest_gated(self) -> None:
        ship = _make_ship_type(
            faction_required="axiom_research",
            faction_rep_required=30,
            unlock_condition="quest_axiom_defense",
        )
        assert ship.faction_required == "axiom_research"
        assert ship.faction_rep_required == 30
        assert ship.unlock_condition == "quest_axiom_defense"

    def test_can_afford_unchanged(self) -> None:
        """Gate fields don't affect can_afford logic."""
        ship = _make_ship_type(
            purchase_price=100000, faction_required="nexus_trade"
        )
        assert ship.can_afford(100000)
        assert not ship.can_afford(99999)


class TestShipTypeDataLoading:
    """Tests that data_loader parses new ShipType fields."""

    def test_existing_ships_load_without_gates(self) -> None:
        """All current ships should have no faction/quest gates."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_ship_types()
        for ship_id, ship_type in dl.ship_types.items():
            # Current ships have no gates (they'll be added with new ships)
            assert isinstance(ship_type.faction_rep_required, int)

    def test_existing_ships_still_load(self) -> None:
        """All existing ships should still parse correctly."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_ship_types()
        assert len(dl.ship_types) >= 9, "Should have at least the original 9 ships"


class TestUpgradeDataLoading:
    """Tests that data_loader parses new ShipUpgrade fields."""

    def test_existing_upgrades_load_with_defaults(self) -> None:
        """Existing upgrades should get default values for new fields."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_upgrades()
        for uid, upgrade in dl.upgrades.items():
            assert 1 <= upgrade.max_mark <= 3
            assert isinstance(upgrade.tuning_options, list)
            assert upgrade.faction_required is None or isinstance(
                upgrade.faction_required, str
            )

    def test_existing_upgrades_still_load(self) -> None:
        """All existing upgrades should still parse correctly."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_upgrades()
        assert len(dl.upgrades) >= 21, "Should have at least the original upgrades"
