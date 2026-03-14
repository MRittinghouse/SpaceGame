"""Tests for ship purchasing system.

Verifies that players can buy new ships, trade in their current ship,
and that cargo/upgrade transfer works correctly.
"""

from spacegame.models.ship import Ship, ShipType
from spacegame.models.player import Player


def _make_ship_type(
    ship_id: str = "shuttle",
    name: str = "Shuttle",
    cargo: int = 50,
    fuel: int = 100,
    price: int = 5000,
    resale: int = 3500,
    weapon_slots: int = 1,
    defense_slots: int = 0,
    utility_slots: int = 2,
    combat_hull: int = 60,
    combat_shields: int = 20,
) -> ShipType:
    return ShipType(
        id=ship_id,
        name=name,
        ship_class="starter",
        description="Test ship",
        cargo_capacity=cargo,
        fuel_capacity=fuel,
        fuel_efficiency=10,
        speed_multiplier=1.0,
        purchase_price=price,
        resale_value=resale,
        crew_slots=2,
        special_abilities=[],
        availability="common",
        combat_hull=combat_hull,
        combat_shields=combat_shields,
        weapon_slots=weapon_slots,
        defense_slots=defense_slots,
        utility_slots=utility_slots,
    )


def _make_player(
    credits: int = 10000,
    ship_type: ShipType | None = None,
) -> Player:
    st = ship_type or _make_ship_type()
    ship = Ship(ship_type=st, current_fuel=st.fuel_capacity)
    return Player(
        name="Test",
        credits=credits,
        current_system_id="nexus_prime",
        ship=ship,
    )


class TestShipPurchase:
    """Test Player.swap_ship() functionality."""

    def test_swap_ship_basic(self) -> None:
        """Player can swap to a new ship type."""
        old_type = _make_ship_type("shuttle", price=5000, resale=3500, cargo=50)
        new_type = _make_ship_type("freighter", name="Freighter", price=25000, resale=17500, cargo=150)

        player = _make_player(credits=30000, ship_type=old_type)
        success, msg = player.swap_ship(new_type)

        assert success, f"Swap should succeed: {msg}"
        assert player.ship.ship_type.id == "freighter"
        # Credits: 30000 + 3500 (resale) - 25000 (purchase) = 8500
        assert player.credits == 8500

    def test_swap_ship_insufficient_credits(self) -> None:
        """Cannot swap if can't afford even with trade-in."""
        old_type = _make_ship_type("shuttle", price=5000, resale=3500)
        new_type = _make_ship_type("expensive", price=100000, resale=70000)

        player = _make_player(credits=1000, ship_type=old_type)
        success, msg = player.swap_ship(new_type)

        assert not success
        assert player.ship.ship_type.id == "shuttle"
        assert player.credits == 1000  # Unchanged

    def test_swap_ship_transfers_cargo(self) -> None:
        """Cargo that fits in the new ship is transferred."""
        old_type = _make_ship_type("old", cargo=100, resale=5000)
        new_type = _make_ship_type("new", cargo=200, price=10000)

        player = _make_player(credits=20000, ship_type=old_type)
        player.ship.add_cargo("iron_ore", 10)

        success, _ = player.swap_ship(new_type)
        assert success
        assert player.ship.get_cargo_quantity("iron_ore") == 10

    def test_swap_ship_cargo_overflow_dropped(self) -> None:
        """Cargo that doesn't fit in new ship is lost (warned in message)."""
        old_type = _make_ship_type("old", cargo=200, resale=5000)
        new_type = _make_ship_type("new", cargo=20, price=10000)

        player = _make_player(credits=20000, ship_type=old_type)
        player.ship.add_cargo("iron_ore", 100)

        success, msg = player.swap_ship(new_type)
        assert success
        # New ship has 20 cargo, so only 20 units fit
        assert player.ship.get_cargo_quantity("iron_ore") == 20
        assert "cargo" in msg.lower()

    def test_swap_ship_full_fuel(self) -> None:
        """New ship starts with full fuel."""
        old_type = _make_ship_type("old", fuel=100, resale=5000)
        new_type = _make_ship_type("new", fuel=200, price=10000)

        player = _make_player(credits=20000, ship_type=old_type)
        player.ship.current_fuel = 50  # Half fuel on old

        success, _ = player.swap_ship(new_type)
        assert success
        assert player.ship.current_fuel == 200  # Full fuel on new

    def test_swap_ship_same_type(self) -> None:
        """Cannot swap to the same ship type."""
        ship_type = _make_ship_type("shuttle")
        player = _make_player(credits=20000, ship_type=ship_type)

        success, msg = player.swap_ship(ship_type)
        assert not success

    def test_swap_ship_net_cost_calculation(self) -> None:
        """Net cost = purchase_price - current resale_value."""
        old_type = _make_ship_type("old", price=5000, resale=4000)
        new_type = _make_ship_type("new", price=20000, resale=14000)

        player = _make_player(credits=16000, ship_type=old_type)
        # Net cost: 20000 - 4000 = 16000, exactly affordable
        success, _ = player.swap_ship(new_type)
        assert success
        assert player.credits == 0

    def test_swap_preserves_upgrade_manager_link(self) -> None:
        """New ship gets the upgrade manager link."""
        old_type = _make_ship_type("old", resale=5000)
        new_type = _make_ship_type("new", price=10000)

        player = _make_player(credits=20000, ship_type=old_type)
        # Set a mock upgrade manager
        player.ship.set_upgrade_manager("mock_mgr")

        success, _ = player.swap_ship(new_type)
        assert success
        assert player.ship._upgrade_manager == "mock_mgr"
