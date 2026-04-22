"""
Tests for the ship upgrade system.

Post-U5 (Legacy Retirement): ShipUpgradeManager no longer enforces slot
caps. Modules on the ship build determine installable capacity; the
manager is now a pure inventory + bonus aggregator. These tests pin
down the new contract and guard against regressions.
"""

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
    """Tests for ShipUpgradeManager inventory + bonus contract."""

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

    def test_initial_state_is_empty(self):
        mgr = ShipUpgradeManager()
        assert mgr.installed == []

    def test_install_single(self):
        mgr = ShipUpgradeManager()
        success, _ = mgr.install(self._make_upgrade())
        assert success
        assert len(mgr.installed) == 1

    def test_install_never_rejects_for_capacity(self):
        """U5: slot caps removed. Installing many upgrades always succeeds
        (duplicate check still applies — see test_no_duplicates)."""
        mgr = ShipUpgradeManager()
        for i in range(20):
            success, _ = mgr.install(self._make_upgrade(uid=f"u{i}"))
            assert success, f"Install #{i} should not be rejected for slot capacity"
        assert len(mgr.installed) == 20

    def test_no_duplicates(self):
        mgr = ShipUpgradeManager()
        upgrade = self._make_upgrade()
        mgr.install(upgrade)
        success, msg = mgr.install(upgrade)
        assert not success
        assert "already" in msg.lower()

    def test_can_install_rejects_only_duplicates(self):
        mgr = ShipUpgradeManager()
        u1 = self._make_upgrade("u1")
        u2 = self._make_upgrade("u2")
        assert mgr.can_install(u1) is True
        mgr.install(u1)
        assert mgr.can_install(u1) is False, "Duplicate should be blocked"
        assert mgr.can_install(u2) is True, "New upgrade should install freely"

    def test_uninstall(self):
        mgr = ShipUpgradeManager()
        upgrade = self._make_upgrade()
        mgr.install(upgrade)
        success, _ = mgr.uninstall("test")
        assert success
        assert mgr.installed == []

    def test_uninstall_missing(self):
        mgr = ShipUpgradeManager()
        success, _ = mgr.uninstall("nonexistent")
        assert not success

    def test_get_bonus_aggregates(self):
        mgr = ShipUpgradeManager()
        mgr.install(self._make_upgrade("u1", bonus_type="cargo", bonus_value=20))
        mgr.install(self._make_upgrade("u2", bonus_type="cargo", bonus_value=10))
        assert mgr.get_bonus("cargo") == 30.0
        assert mgr.get_bonus("fuel") == 0.0

    def test_has_upgrade(self):
        mgr = ShipUpgradeManager()
        mgr.install(self._make_upgrade("u1"))
        assert mgr.has_upgrade("u1") is True
        assert mgr.has_upgrade("u2") is False

    def test_get_category_still_maps_slot_types(self):
        """get_category is kept for UI grouping; it is NOT a capacity check."""
        mgr = ShipUpgradeManager()
        assert mgr.get_category("weapon") == "weapon"
        assert mgr.get_category("defense") == "defense"
        assert mgr.get_category("cargo") == "utility"
        assert mgr.get_category("fuel") == "utility"
        assert mgr.get_category("unknown_type") == "utility"  # default

    def test_serialization_roundtrip(self):
        mgr = ShipUpgradeManager()
        u1 = self._make_upgrade("cargo_bay", bonus_type="cargo", bonus_value=20)
        u2 = self._make_upgrade("fuel_tank", bonus_type="fuel", bonus_value=30)
        mgr.install(u1)
        mgr.install(u2)

        data = mgr.to_dict()
        assert "cargo_bay" in data["installed_ids"]
        assert "fuel_tank" in data["installed_ids"]

        all_upgrades = {"cargo_bay": u1, "fuel_tank": u2}
        restored = ShipUpgradeManager.from_dict(data, all_upgrades)
        assert len(restored.installed) == 2
        assert restored.get_bonus("cargo") == 20.0
        assert restored.get_bonus("fuel") == 30.0

    def test_to_dict_omits_slot_fields(self):
        """U5: to_dict must no longer emit slot-counting fields."""
        mgr = ShipUpgradeManager()
        mgr.install(self._make_upgrade())
        data = mgr.to_dict()
        assert "max_slots" not in data, "legacy field must not be re-emitted"
        assert "weapon_slots" not in data
        assert "defense_slots" not in data
        assert "utility_slots" not in data

    def test_from_dict_ignores_legacy_slot_fields(self):
        """Old saves contain weapon_slots/defense_slots/utility_slots/max_slots.
        These must be silently ignored, not crash the load."""
        u1 = ShipUpgrade(
            id="u1",
            name="U1",
            description="",
            price=0,
            slot_type="cargo",
            bonus_type="cargo",
            bonus_value=5.0,
        )
        legacy_data = {
            "max_slots": 3,
            "weapon_slots": 2,
            "defense_slots": 1,
            "utility_slots": 3,
            "installed_ids": ["u1"],
            "installed": [{"upgrade_id": "u1", "mark": 1, "tuning": None}],
        }
        restored = ShipUpgradeManager.from_dict(legacy_data, {"u1": u1})
        assert len(restored.installed) == 1
        assert restored.has_upgrade("u1")

    def test_from_dict_very_old_save_with_only_installed_ids(self):
        """Oldest save format: only installed_ids, no per-upgrade mark/tuning."""
        u1 = ShipUpgrade(
            id="u1",
            name="U1",
            description="",
            price=0,
            slot_type="cargo",
            bonus_type="cargo",
            bonus_value=5.0,
        )
        ancient_data = {"max_slots": 3, "installed_ids": ["u1"]}
        restored = ShipUpgradeManager.from_dict(ancient_data, {"u1": u1})
        assert restored.has_upgrade("u1")
        inst = restored.get_installed("u1")
        assert inst is not None and inst.mark == 1


class TestUpgradeBonusIntegration:
    """Tests that upgrade bonuses flow through to Ship and Player.

    These tests protect the non-combat bonus consumers (cargo, fuel,
    fuel_efficiency) that still read from ShipUpgradeManager.get_bonus().
    """

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

        assert ship.max_cargo == 50

        cargo_upgrade = self._make_upgrade("cargo_bay", "cargo_bonus", 20.0)
        mgr.install(cargo_upgrade)
        assert ship.max_cargo == 70

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

        assert ship.effective_fuel_efficiency == 10

        engine_upgrade = self._make_upgrade("engines", "fuel_efficiency_bonus", 2.0)
        mgr.install(engine_upgrade)
        assert ship.effective_fuel_efficiency == 8

    def test_fuel_efficiency_minimum_is_1(self):
        ship_type = self._make_ship_type()
        ship = Ship(ship_type=ship_type, current_fuel=100)
        mgr = ShipUpgradeManager()
        ship.set_upgrade_manager(mgr)

        huge_upgrade = self._make_upgrade("engines", "fuel_efficiency_bonus", 999.0)
        mgr.install(huge_upgrade)
        assert ship.effective_fuel_efficiency == 1

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
        assert player.ship.max_cargo == 70

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
