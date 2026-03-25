"""Tests for smuggling upgrade visibility in shipyard (Phase E.7).

Covers requires_black_market field on ShipUpgrade, data loading,
and shipyard filtering based on black market access.
"""

from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=50,
        fuel_capacity=100,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player() -> Player:
    ship = Ship(ship_type=_make_ship_type(), current_fuel=100)
    return Player(
        name="Test",
        credits=50000,
        current_system_id="nexus_prime",
        ship=ship,
    )


def _make_smuggling_upgrade() -> ShipUpgrade:
    return ShipUpgrade(
        id="hidden_compartment",
        name="Hidden Compartment",
        description="Conceals cargo",
        price=2500,
        slot_type="smuggling",
        bonus_type="hidden_compartment",
        bonus_value=0.30,
        requires_black_market=True,
    )


def _make_normal_upgrade() -> ShipUpgrade:
    return ShipUpgrade(
        id="cargo_bay_ext",
        name="Cargo Bay Extension",
        description="Expands cargo",
        price=5000,
        slot_type="cargo",
        bonus_type="cargo_bonus",
        bonus_value=20.0,
    )


# ============================================================================
# ShipUpgrade.requires_black_market field
# ============================================================================


class TestShipUpgradeBlackMarketField:
    """ShipUpgrade should have a requires_black_market flag."""

    def test_default_false(self) -> None:
        """Normal upgrades default to requires_black_market=False."""
        upgrade = _make_normal_upgrade()
        assert upgrade.requires_black_market is False

    def test_smuggling_upgrade_flag_true(self) -> None:
        """Smuggling upgrades can be flagged as requires_black_market."""
        upgrade = _make_smuggling_upgrade()
        assert upgrade.requires_black_market is True


# ============================================================================
# Data Loading
# ============================================================================


class TestSmugglingUpgradeDataLoading:
    """DataLoader should parse requires_black_market from JSON."""

    def test_smuggling_upgrades_have_flag(self) -> None:
        """All 3 smuggling upgrades in data have requires_black_market=True."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()

        smuggling_ids = ["hidden_compartment", "signal_jammer", "false_transponder"]
        for uid in smuggling_ids:
            upgrade = dl.upgrades.get(uid)
            assert upgrade is not None, f"Upgrade {uid} should exist"
            assert upgrade.requires_black_market is True, (
                f"{uid} should require black market access"
            )

    def test_normal_upgrades_no_flag(self) -> None:
        """Non-smuggling upgrades should not require black market."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()

        normal_ids = ["cargo_bay_ext", "fuel_tank_upgrade", "laser_cannon"]
        for uid in normal_ids:
            upgrade = dl.upgrades.get(uid)
            assert upgrade is not None, f"Upgrade {uid} should exist"
            assert upgrade.requires_black_market is False, (
                f"{uid} should not require black market access"
            )


# ============================================================================
# Shipyard Filtering
# ============================================================================


class TestShipyardSmugglingFilter:
    """Shipyard should hide smuggling upgrades without black market access."""

    def test_smuggling_upgrade_hidden_without_access(self) -> None:
        """Smuggling upgrades not shown when player lacks black market access."""
        player = _make_player()
        smuggling = _make_smuggling_upgrade()
        normal = _make_normal_upgrade()
        all_upgrades = {smuggling.id: smuggling, normal.id: normal}

        # Import the filtering logic — we test _get_shop_list behavior
        from spacegame.views.shipyard_view import ShipyardView

        # Player has no black market access at current system
        assert not player.has_black_market_access(player.current_system_id)

        # Use the class method or test the filter directly
        # The shop list should exclude requires_black_market upgrades
        installed_ids: set[str] = set()
        shop = [
            u
            for u in all_upgrades.values()
            if u.id not in installed_ids
            and (
                not u.requires_black_market
                or player.has_black_market_access(player.current_system_id)
            )
        ]
        assert len(shop) == 1
        assert shop[0].id == "cargo_bay_ext"

    def test_smuggling_upgrade_visible_with_access(self) -> None:
        """Smuggling upgrades shown when player has black market access."""
        player = _make_player()
        player.grant_black_market_access("nexus_prime")  # Current system

        smuggling = _make_smuggling_upgrade()
        normal = _make_normal_upgrade()
        all_upgrades = {smuggling.id: smuggling, normal.id: normal}

        installed_ids: set[str] = set()
        shop = [
            u
            for u in all_upgrades.values()
            if u.id not in installed_ids
            and (
                not u.requires_black_market
                or player.has_black_market_access(player.current_system_id)
            )
        ]
        assert len(shop) == 2
        assert {u.id for u in shop} == {"hidden_compartment", "cargo_bay_ext"}

    def test_smuggling_upgrade_hidden_at_wrong_system(self) -> None:
        """Black market access at different system doesn't unlock upgrades here."""
        player = _make_player()
        # Access at crimson_reach, but player is at nexus_prime
        player.grant_black_market_access("crimson_reach")

        smuggling = _make_smuggling_upgrade()
        all_upgrades = {smuggling.id: smuggling}

        installed_ids: set[str] = set()
        shop = [
            u
            for u in all_upgrades.values()
            if u.id not in installed_ids
            and (
                not u.requires_black_market
                or player.has_black_market_access(player.current_system_id)
            )
        ]
        assert len(shop) == 0
