"""
Tests for the ship upgrade system.
"""

import pytest
from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager
from spacegame.models.ship import Ship, ShipType
from spacegame.models.player import Player


class TestShipUpgrade:
    """Tests for ShipUpgrade."""

    def test_creation(self):
        upgrade = ShipUpgrade(
            id="cargo_bay",
            name="Cargo Bay Extension",
            description="+20 cargo",
            price=5000,
            slot_type="cargo",
            bonus_type="cargo_bonus",
            bonus_value=20.0,
        )
        assert upgrade.price == 5000
        assert upgrade.can_afford(5000)
        assert not upgrade.can_afford(4999)


class TestShipUpgradeManager:
    """Tests for ShipUpgradeManager."""

    def _make_upgrade(self, uid="test", price=1000, bonus_type="test", bonus_value=10.0):
        return ShipUpgrade(
            id=uid,
            name=f"Upgrade {uid}",
            description="Test",
            price=price,
            slot_type="test",
            bonus_type=bonus_type,
            bonus_value=bonus_value,
        )

    def test_initial_state(self):
        mgr = ShipUpgradeManager()
        assert mgr.max_slots == 3
        assert mgr.slots_used == 0
        assert mgr.slots_available == 3

    def test_install(self):
        mgr = ShipUpgradeManager()
        upgrade = self._make_upgrade()
        success, msg = mgr.install(upgrade)
        assert success
        assert mgr.slots_used == 1

    def test_install_full(self):
        mgr = ShipUpgradeManager(max_slots=1)
        mgr.install(self._make_upgrade("u1"))
        success, msg = mgr.install(self._make_upgrade("u2"))
        assert not success
        assert "slots" in msg.lower()

    def test_no_duplicates(self):
        mgr = ShipUpgradeManager()
        upgrade = self._make_upgrade()
        mgr.install(upgrade)
        success, msg = mgr.install(upgrade)
        assert not success

    def test_uninstall(self):
        mgr = ShipUpgradeManager()
        upgrade = self._make_upgrade()
        mgr.install(upgrade)
        success, msg = mgr.uninstall("test")
        assert success
        assert mgr.slots_used == 0

    def test_uninstall_missing(self):
        mgr = ShipUpgradeManager()
        success, msg = mgr.uninstall("nonexistent")
        assert not success

    def test_get_bonus(self):
        mgr = ShipUpgradeManager()
        mgr.install(self._make_upgrade("u1", bonus_type="cargo", bonus_value=20))
        mgr.install(self._make_upgrade("u2", bonus_type="cargo", bonus_value=10))
        assert mgr.get_bonus("cargo") == 30.0
        assert mgr.get_bonus("fuel") == 0.0

    def test_serialization(self):
        mgr = ShipUpgradeManager()
        u1 = self._make_upgrade("cargo_bay", bonus_type="cargo", bonus_value=20)
        u2 = self._make_upgrade("fuel_tank", bonus_type="fuel", bonus_value=30)
        mgr.install(u1)
        mgr.install(u2)

        data = mgr.to_dict()
        assert data["max_slots"] == 3
        assert "cargo_bay" in data["installed_ids"]
        assert "fuel_tank" in data["installed_ids"]

        # Roundtrip
        all_upgrades = {"cargo_bay": u1, "fuel_tank": u2}
        restored = ShipUpgradeManager.from_dict(data, all_upgrades)
        assert restored.slots_used == 2
        assert restored.get_bonus("cargo") == 20.0


class TestUpgradeBonusIntegration:
    """Tests that upgrade bonuses flow through to Ship and Player."""

    def _make_ship_type(self):
        return ShipType(
            id="test_ship",
            name="Test Ship",
            ship_class="starter",
            description="Test",
            cargo_capacity=50,
            fuel_capacity=100,
            fuel_efficiency=10,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=1,
            special_abilities=[],
            availability="common",
        )

    def _make_upgrade(self, uid, bonus_type, bonus_value):
        return ShipUpgrade(
            id=uid,
            name=f"Upgrade {uid}",
            description="Test",
            price=1000,
            slot_type="test",
            bonus_type=bonus_type,
            bonus_value=bonus_value,
        )

    def test_ship_max_cargo_with_upgrade(self):
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        ship.set_upgrade_manager(mgr)

        assert ship.max_cargo == 50  # Base

        cargo_upgrade = self._make_upgrade("cargo_bay", "cargo_bonus", 20.0)
        mgr.install(cargo_upgrade)
        assert ship.max_cargo == 70  # Base + upgrade

    def test_ship_max_fuel_with_upgrade(self):
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        ship.set_upgrade_manager(mgr)

        assert ship.max_fuel == 100

        fuel_upgrade = self._make_upgrade("fuel_tank", "fuel_bonus", 30.0)
        mgr.install(fuel_upgrade)
        assert ship.max_fuel == 130

    def test_ship_fuel_efficiency_with_upgrade(self):
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        ship.set_upgrade_manager(mgr)

        assert ship.effective_fuel_efficiency == 10  # Base

        engine_upgrade = self._make_upgrade("engines", "fuel_efficiency_bonus", 2.0)
        mgr.install(engine_upgrade)
        assert ship.effective_fuel_efficiency == 8  # Base - bonus

    def test_fuel_efficiency_minimum_is_1(self):
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        ship.set_upgrade_manager(mgr)

        huge_upgrade = self._make_upgrade("engines", "fuel_efficiency_bonus", 999.0)
        mgr.install(huge_upgrade)
        assert ship.effective_fuel_efficiency == 1  # Never below 1

    def test_ship_without_upgrade_manager(self):
        """Ship works normally without an upgrade manager."""
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        assert ship.max_cargo == 50
        assert ship.max_fuel == 100
        assert ship.effective_fuel_efficiency == 10

    def test_player_links_upgrade_manager_to_ship(self):
        """Player.__post_init__ links upgrade_manager to ship."""
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        cargo_upgrade = self._make_upgrade("cargo_bay", "cargo_bonus", 20.0)
        mgr.install(cargo_upgrade)

        player = Player(
            name="Test",
            credits=1000,
            current_system_id="nexus_prime",
            ship=ship,
            upgrade_manager=mgr,
        )
        # Player's __post_init__ should have linked the manager
        assert player.ship.max_cargo == 70  # 50 base + 20 upgrade

    def test_cargo_available_with_upgrade(self):
        """Available cargo accounts for upgrade bonus."""
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        cargo_upgrade = self._make_upgrade("cargo_bay", "cargo_bonus", 20.0)
        mgr.install(cargo_upgrade)
        ship.set_upgrade_manager(mgr)

        volumes = {"ore": 1}
        assert ship.get_available_cargo(volumes) == 70
        ship.add_cargo("ore", 60)
        assert ship.get_available_cargo(volumes) == 10
        assert ship.can_carry("ore", 10, volumes)
        assert not ship.can_carry("ore", 11, volumes)
