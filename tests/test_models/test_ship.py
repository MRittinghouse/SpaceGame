"""Tests for Ship and ShipType models."""

from spacegame.models.ship import Ship, ShipType


def _make_ship_type(**overrides) -> ShipType:
    """Create a ShipType with reasonable defaults."""
    defaults = dict(
        id="test_ship",
        name="Test Ship",
        ship_class="starter",
        description="A test ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=5,
        speed_multiplier=1.0,
        purchase_price=5000,
        resale_value=2500,
        crew_slots=2,
        special_abilities=[],
        availability="common",
        combat_hull=100,
        combat_shields=50,
        combat_energy=30,
    )
    defaults.update(overrides)
    return ShipType(**defaults)


def _make_ship(ship_type: ShipType | None = None, **overrides) -> Ship:
    """Create a Ship with reasonable defaults."""
    if ship_type is None:
        ship_type = _make_ship_type()
    defaults = dict(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    defaults.update(overrides)
    return Ship(**defaults)


# --- ShipType ---


class TestShipType:
    def test_can_afford_true(self) -> None:
        st = _make_ship_type(purchase_price=5000)
        assert st.can_afford(5000) is True
        assert st.can_afford(10000) is True

    def test_can_afford_false(self) -> None:
        st = _make_ship_type(purchase_price=5000)
        assert st.can_afford(4999) is False
        assert st.can_afford(0) is False

    def test_combat_stats_default_zero(self) -> None:
        st = ShipType(
            id="basic", name="Basic", ship_class="starter",
            description="", cargo_capacity=50, fuel_capacity=30,
            fuel_efficiency=3, speed_multiplier=1.0, purchase_price=1000,
            resale_value=500, crew_slots=1, special_abilities=[], availability="common",
        )
        assert st.combat_hull == 0
        assert st.combat_shields == 0
        assert st.combat_energy == 0
        assert st.weapon_slots == 0
        assert st.defense_slots == 0
        assert st.utility_slots == 3  # default is 3


# --- Ship Initialization ---


class TestShipInit:
    def test_auto_init_fuel_to_capacity(self) -> None:
        """Ship should start with full fuel if not specified."""
        st = _make_ship_type(fuel_capacity=50)
        ship = Ship(ship_type=st, current_fuel=0)
        assert ship.current_fuel == 50

    def test_explicit_fuel_preserved(self) -> None:
        """Explicit fuel value should not be overwritten."""
        st = _make_ship_type(fuel_capacity=50)
        ship = Ship(ship_type=st, current_fuel=25)
        assert ship.current_fuel == 25

    def test_auto_init_hull_from_type(self) -> None:
        """Hull should initialize from ship_type if zero."""
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=50)
        assert ship.current_hull == 100

    def test_auto_init_shields_from_type(self) -> None:
        """Shields should initialize from ship_type if zero."""
        st = _make_ship_type(combat_shields=50)
        ship = Ship(ship_type=st, current_fuel=50)
        assert ship.current_shields == 50

    def test_explicit_hull_preserved(self) -> None:
        """Explicit hull should not be overwritten."""
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=50, current_hull=30)
        assert ship.current_hull == 30

    def test_no_combat_ship_hull_stays_zero(self) -> None:
        """Ship with 0 combat_hull type should stay at 0."""
        st = _make_ship_type(combat_hull=0)
        ship = Ship(ship_type=st, current_fuel=50)
        assert ship.current_hull == 0


# --- Properties ---


class TestShipProperties:
    def test_name_from_type(self) -> None:
        st = _make_ship_type(name="Star Cruiser")
        ship = _make_ship(st)
        assert ship.name == "Star Cruiser"

    def test_max_cargo_base(self) -> None:
        """Max cargo with no upgrades/crew should equal base capacity."""
        st = _make_ship_type(cargo_capacity=150)
        ship = _make_ship(st)
        assert ship.max_cargo == 150

    def test_max_fuel_base(self) -> None:
        """Max fuel with no upgrades/crew should equal base capacity."""
        st = _make_ship_type(fuel_capacity=60)
        ship = _make_ship(st)
        assert ship.max_fuel == 60

    def test_effective_fuel_efficiency_base(self) -> None:
        """Fuel efficiency with no bonuses should equal base."""
        st = _make_ship_type(fuel_efficiency=5)
        ship = _make_ship(st)
        assert ship.effective_fuel_efficiency == 5

    def test_fuel_percentage_full(self) -> None:
        st = _make_ship_type(fuel_capacity=50)
        ship = _make_ship(st)
        assert ship.get_fuel_percentage() == 1.0

    def test_fuel_percentage_half(self) -> None:
        st = _make_ship_type(fuel_capacity=50)
        ship = Ship(ship_type=st, current_fuel=25)
        assert ship.get_fuel_percentage() == 0.5

    def test_fuel_percentage_zero_capacity(self) -> None:
        """Avoid division by zero with 0 capacity."""
        st = _make_ship_type(fuel_capacity=0)
        ship = Ship(ship_type=st, current_fuel=0)
        assert ship.get_fuel_percentage() == 0.0


# --- Cargo Operations ---


class TestCargo:
    def test_add_cargo(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=50)
        assert ship.get_cargo_quantity("iron") == 10

    def test_add_cargo_stacks(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=50)
        ship.add_cargo("iron", 5, price_per_unit=60)
        assert ship.get_cargo_quantity("iron") == 15

    def test_remove_cargo_success(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10)
        assert ship.remove_cargo("iron", 5) is True
        assert ship.get_cargo_quantity("iron") == 5

    def test_remove_cargo_all(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10)
        assert ship.remove_cargo("iron", 10) is True
        assert ship.get_cargo_quantity("iron") == 0
        assert "iron" not in ship.current_cargo

    def test_remove_cargo_insufficient(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 5)
        assert ship.remove_cargo("iron", 10) is False
        assert ship.get_cargo_quantity("iron") == 5

    def test_remove_nonexistent_cargo(self) -> None:
        ship = _make_ship()
        assert ship.remove_cargo("iron", 1) is False

    def test_get_cargo_quantity_empty(self) -> None:
        ship = _make_ship()
        assert ship.get_cargo_quantity("gold") == 0

    def test_used_cargo_space(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10)
        ship.add_cargo("gold", 5)
        volumes = {"iron": 1, "gold": 2}
        assert ship.get_used_cargo(volumes) == 20  # 10*1 + 5*2

    def test_available_cargo_space(self) -> None:
        st = _make_ship_type(cargo_capacity=100)
        ship = _make_ship(st)
        ship.add_cargo("iron", 30)
        volumes = {"iron": 1}
        assert ship.get_available_cargo(volumes) == 70

    def test_can_carry_true(self) -> None:
        st = _make_ship_type(cargo_capacity=100)
        ship = _make_ship(st)
        volumes = {"iron": 1}
        assert ship.can_carry("iron", 50, volumes) is True

    def test_can_carry_false(self) -> None:
        st = _make_ship_type(cargo_capacity=100)
        ship = _make_ship(st)
        volumes = {"iron": 1}
        assert ship.can_carry("iron", 101, volumes) is False

    def test_can_carry_with_volume(self) -> None:
        """Large volume items consume more cargo space."""
        st = _make_ship_type(cargo_capacity=100)
        ship = _make_ship(st)
        volumes = {"machinery": 5}
        assert ship.can_carry("machinery", 20, volumes) is True  # 20 * 5 = 100
        assert ship.can_carry("machinery", 21, volumes) is False  # 21 * 5 = 105

    def test_default_volume_is_one(self) -> None:
        """Unknown commodity volume defaults to 1."""
        ship = _make_ship()
        ship.add_cargo("unknown_stuff", 10)
        assert ship.get_used_cargo({}) == 10


# --- Purchase Price Tracking ---


class TestPurchasePriceTracking:
    def test_average_price_single_batch(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=50)
        assert ship.get_average_purchase_price("iron") == 50

    def test_average_price_multiple_batches(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=50)  # total cost 500
        ship.add_cargo("iron", 10, price_per_unit=70)  # total cost 700
        # Total: 1200 / 20 = 60
        assert ship.get_average_purchase_price("iron") == 60

    def test_average_price_after_partial_sell(self) -> None:
        """Selling reduces total cost proportionally."""
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=100)  # total cost 1000
        ship.remove_cargo("iron", 5)  # sell half -> cost = 500
        assert ship.get_average_purchase_price("iron") == 100  # 500 / 5

    def test_price_tracking_cleared_on_full_sell(self) -> None:
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=50)
        ship.remove_cargo("iron", 10)
        assert ship.get_average_purchase_price("iron") == 0
        assert "iron" not in ship.cargo_purchase_prices

    def test_average_price_zero_quantity(self) -> None:
        ship = _make_ship()
        assert ship.get_average_purchase_price("iron") == 0

    def test_add_cargo_no_price(self) -> None:
        """Adding cargo with price_per_unit=0 shouldn't track cost."""
        ship = _make_ship()
        ship.add_cargo("iron", 10, price_per_unit=0)
        assert ship.get_average_purchase_price("iron") == 0


# --- Fuel Operations ---


class TestFuel:
    def test_has_fuel_for_jump_true(self) -> None:
        ship = _make_ship()  # full fuel = 50
        assert ship.has_fuel_for_jump(50) is True
        assert ship.has_fuel_for_jump(1) is True

    def test_has_fuel_for_jump_false(self) -> None:
        ship = _make_ship()
        assert ship.has_fuel_for_jump(51) is False

    def test_consume_fuel_success(self) -> None:
        ship = _make_ship()  # 50 fuel
        assert ship.consume_fuel(20) is True
        assert ship.current_fuel == 30

    def test_consume_fuel_insufficient(self) -> None:
        ship = _make_ship()
        assert ship.consume_fuel(51) is False
        assert ship.current_fuel == 50  # unchanged

    def test_refuel_partial(self) -> None:
        st = _make_ship_type(fuel_capacity=50)
        ship = Ship(ship_type=st, current_fuel=30)
        added = ship.refuel(100)
        assert added == 20  # capped at capacity
        assert ship.current_fuel == 50

    def test_refuel_exact(self) -> None:
        st = _make_ship_type(fuel_capacity=50)
        ship = Ship(ship_type=st, current_fuel=30)
        added = ship.refuel(20)
        assert added == 20
        assert ship.current_fuel == 50

    def test_refuel_already_full(self) -> None:
        ship = _make_ship()  # full
        added = ship.refuel(10)
        assert added == 0
        assert ship.current_fuel == 50


# --- Hull & Shield Operations ---


class TestHullAndShields:
    def test_repair_hull(self) -> None:
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=50, current_hull=60)
        actual = ship.repair_hull(20)
        assert actual == 20
        assert ship.current_hull == 80

    def test_repair_hull_capped(self) -> None:
        """Can't repair beyond max hull."""
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=50, current_hull=90)
        actual = ship.repair_hull(50)
        assert actual == 10
        assert ship.current_hull == 100

    def test_repair_hull_at_max(self) -> None:
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=50, current_hull=100)
        actual = ship.repair_hull(10)
        assert actual == 0
        assert ship.current_hull == 100

    def test_restore_shields(self) -> None:
        st = _make_ship_type(combat_shields=50)
        ship = Ship(ship_type=st, current_fuel=50, current_shields=10)
        ship.restore_shields()
        assert ship.current_shields == 50


# --- Bonus Integration ---


class TestBonusIntegration:
    def test_get_crew_bonus_no_roster(self) -> None:
        """No crew roster should return 0."""
        ship = _make_ship()
        assert ship.get_crew_bonus("cargo_bonus") == 0.0

    def test_set_upgrade_manager(self) -> None:
        """Setting upgrade manager should affect max_cargo."""

        class FakeUpgradeManager:
            def get_bonus(self, bonus_type: str) -> float:
                if bonus_type == "cargo_bonus":
                    return 20.0
                return 0.0

        st = _make_ship_type(cargo_capacity=100)
        ship = _make_ship(st)
        ship.set_upgrade_manager(FakeUpgradeManager())
        assert ship.max_cargo == 120

    def test_set_crew_roster(self) -> None:
        """Setting crew roster should affect max_cargo."""

        class FakeRoster:
            def get_bonus(self, bonus_type: str) -> float:
                if bonus_type == "cargo_bonus":
                    return 15.0
                return 0.0

        st = _make_ship_type(cargo_capacity=100)
        ship = _make_ship(st)
        ship.set_crew_roster(FakeRoster())
        assert ship.max_cargo == 115

    def test_fuel_efficiency_bonus_capped_at_one(self) -> None:
        """Fuel efficiency should never go below 1."""

        class FakeUpgradeManager:
            def get_bonus(self, bonus_type: str) -> float:
                if bonus_type == "fuel_efficiency_bonus":
                    return 999.0
                return 0.0

        st = _make_ship_type(fuel_efficiency=5)
        ship = _make_ship(st)
        ship.set_upgrade_manager(FakeUpgradeManager())
        assert ship.effective_fuel_efficiency == 1

    def test_max_fuel_with_bonuses(self) -> None:
        class FakeUpgradeManager:
            def get_bonus(self, bonus_type: str) -> float:
                return 10.0 if bonus_type == "fuel_bonus" else 0.0

        class FakeRoster:
            def get_bonus(self, bonus_type: str) -> float:
                return 5.0 if bonus_type == "fuel_bonus" else 0.0

        st = _make_ship_type(fuel_capacity=50)
        ship = _make_ship(st)
        ship.set_upgrade_manager(FakeUpgradeManager())
        ship.set_crew_roster(FakeRoster())
        assert ship.max_fuel == 65  # 50 + 10 + 5
