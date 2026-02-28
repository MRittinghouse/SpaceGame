# Coding Principles and Standards

> **Implementation Status** (Updated 2026-02-27): ACTIVELY ENFORCED
>
> - **OOP**: @dataclass models, BaseView inheritance, composition (Player has Ship, Ship has ShipType)
> - **TDD**: pytest test suite covering models and data loading; class-based tests with helper methods
> - **Type hints**: MyPy strict mode enforced (`disallow_untyped_defs = true`)
> - **Formatting**: Black (100 char lines), pylint
> - **Docstrings**: Google style with Args/Returns/Raises sections
> - **Conventions codified**: Project CLAUDE.md and views/CLAUDE.md document all patterns for AI-assisted development
> - **Key patterns established**: tuple[bool, str] returns for failable operations, to_dict/from_dict serialization, _create_ui/_destroy_ui view lifecycle, object-pooled particles

## 1. Overview

This document defines the coding standards, design principles, and development practices for the SpaceGame project. Following these principles ensures maintainable, testable, and scalable code.

## 2. Core Development Philosophy

### 2.1 Guiding Principles

1. **Object-Oriented Programming (OOP)** - Leverage encapsulation, inheritance, and polymorphism
2. **Test-Driven Development (TDD)** - Write tests before implementation
3. **SOLID Principles** - Foundation for clean architecture
4. **Clean Code** - Readable, self-documenting, and maintainable
5. **Don't Repeat Yourself (DRY)** - Eliminate code duplication
6. **Keep It Simple, Stupid (KISS)** - Favor simplicity over complexity

### 2.2 Code Quality Goals

- **Maintainability**: Code should be easy to understand and modify
- **Testability**: All business logic should be unit testable
- **Readability**: Code should read like well-written prose
- **Modularity**: Components should be loosely coupled and highly cohesive
- **Performance**: Optimize only when necessary, after profiling

## 3. Object-Oriented Programming

### 3.1 Class Design Principles

#### Encapsulation
- Keep data private, expose behavior through methods
- Use properties for controlled access to attributes
- Hide implementation details

**Example:**
```python
class Ship:
    """Represents a trading ship with cargo and fuel management."""

    def __init__(self, ship_type: ShipType, name: str):
        self._ship_type = ship_type
        self._name = name
        self._fuel_current = ship_type.fuel_capacity
        self._cargo: Dict[str, int] = {}

    @property
    def fuel_current(self) -> int:
        """Current fuel level (read-only)."""
        return self._fuel_current

    @property
    def cargo_used(self) -> int:
        """Calculate total cargo space used."""
        return sum(
            qty * commodity.volume_per_unit
            for commodity_id, qty in self._cargo.items()
        )

    def add_cargo(self, commodity_id: str, quantity: int) -> bool:
        """
        Add cargo to the ship.

        Args:
            commodity_id: ID of the commodity to add
            quantity: Amount to add

        Returns:
            True if cargo was added, False if insufficient space
        """
        # Implementation with validation
        pass
```

#### Inheritance and Composition

**Prefer Composition Over Inheritance** when possible:

```python
# GOOD: Composition
class Ship:
    def __init__(self, cargo_hold: CargoHold, fuel_tank: FuelTank):
        self._cargo_hold = cargo_hold
        self._fuel_tank = fuel_tank

    def add_cargo(self, commodity: str, qty: int) -> bool:
        return self._cargo_hold.add(commodity, qty)

# ACCEPTABLE: Inheritance for clear "is-a" relationships
class TradingShip(Ship):
    """Base class for all trading vessels."""
    pass

class Freighter(TradingShip):
    """Standard cargo freighter."""
    pass
```

#### Polymorphism

Use polymorphism for flexible, extensible code:

```python
from abc import ABC, abstractmethod

class PricingStrategy(ABC):
    """Abstract base class for commodity pricing strategies."""

    @abstractmethod
    def calculate_price(self, base_price: int, market: Market) -> int:
        """Calculate the current price for a commodity."""
        pass

class SupplyDemandPricing(PricingStrategy):
    """Pricing based on supply and demand."""

    def calculate_price(self, base_price: int, market: Market) -> int:
        modifier = market.supply_demand_modifier
        return int(base_price * (1 + modifier))

class EventModifiedPricing(PricingStrategy):
    """Pricing that includes event modifiers."""

    def calculate_price(self, base_price: int, market: Market) -> int:
        base = SupplyDemandPricing().calculate_price(base_price, market)
        event_mod = market.event_modifier
        return int(base * (1 + event_mod))

# Usage
pricing: PricingStrategy = EventModifiedPricing()
current_price = pricing.calculate_price(commodity.base_price, market)
```

### 3.2 Class Organization

#### Class Structure Template

```python
class ExampleClass:
    """
    Brief description of class purpose.

    Longer description if needed, including usage examples.

    Attributes:
        public_attr: Description of public attribute
    """

    # 1. Class variables (constants)
    MAX_CAPACITY = 100

    # 2. Constructor
    def __init__(self, param: type):
        """Initialize the class."""
        self._private_attr = param
        self.public_attr = None

    # 3. Properties
    @property
    def private_attr(self) -> type:
        """Getter for private attribute."""
        return self._private_attr

    # 4. Public methods
    def public_method(self, arg: type) -> type:
        """Public interface method."""
        return self._private_method(arg)

    # 5. Private methods
    def _private_method(self, arg: type) -> type:
        """Internal implementation detail."""
        pass

    # 6. Special methods
    def __str__(self) -> str:
        """String representation."""
        return f"ExampleClass({self._private_attr})"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ExampleClass(param={self._private_attr!r})"
```

### 3.3 Naming Conventions

```python
# Classes: PascalCase
class TradingController:
    pass

# Functions/Methods: snake_case
def calculate_profit(buy_price: int, sell_price: int) -> int:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_CARGO_CAPACITY = 1000
DEFAULT_FUEL_CONSUMPTION = 10

# Private attributes/methods: leading underscore
class Ship:
    def __init__(self):
        self._fuel = 100  # Private attribute

    def _validate_cargo(self):  # Private method
        pass

# Protected attributes/methods: single underscore (by convention)
class BaseView:
    def _render_background(self):  # Protected, for subclass use
        pass
```

## 4. SOLID Principles

### 4.1 Single Responsibility Principle (SRP)

**Principle**: A class should have only one reason to change.

**Bad Example:**
```python
# VIOLATION: This class does too much
class Ship:
    def add_cargo(self, commodity, qty):
        pass

    def calculate_trade_profit(self, buy_price, sell_price):
        pass

    def save_to_database(self):
        pass

    def render_to_screen(self, screen):
        pass
```

**Good Example:**
```python
# GOOD: Single responsibilities separated
class Ship:
    """Manages ship state and cargo."""
    def add_cargo(self, commodity, qty):
        pass

class TradeCalculator:
    """Handles trade profit calculations."""
    def calculate_profit(self, ship, route):
        pass

class ShipRepository:
    """Handles ship persistence."""
    def save(self, ship):
        pass

class ShipRenderer:
    """Handles ship visualization."""
    def render(self, ship, screen):
        pass
```

### 4.2 Open/Closed Principle (OCP)

**Principle**: Classes should be open for extension but closed for modification.

**Bad Example:**
```python
# VIOLATION: Must modify class to add new ship types
class ShipManager:
    def get_fuel_consumption(self, ship_type: str) -> int:
        if ship_type == "shuttle":
            return 10
        elif ship_type == "freighter":
            return 15
        elif ship_type == "hauler":
            return 35
        # Must modify this method for each new ship type!
```

**Good Example:**
```python
# GOOD: Extend through inheritance/composition
class ShipType(ABC):
    @abstractmethod
    def get_fuel_consumption(self) -> int:
        pass

class Shuttle(ShipType):
    def get_fuel_consumption(self) -> int:
        return 10

class Freighter(ShipType):
    def get_fuel_consumption(self) -> int:
        return 15

class Hauler(ShipType):
    def get_fuel_consumption(self) -> int:
        return 35

# New ship types extend without modifying existing code
class Corvette(ShipType):
    def get_fuel_consumption(self) -> int:
        return 18
```

### 4.3 Liskov Substitution Principle (LSP)

**Principle**: Subtypes must be substitutable for their base types.

**Bad Example:**
```python
# VIOLATION: DroneShip violates expectations of Ship
class Ship:
    def refuel(self, amount: int):
        self._fuel += amount

class DroneShip(Ship):
    def refuel(self, amount: int):
        raise NotImplementedError("Drones use batteries, not fuel!")
        # Violates LSP - can't substitute for Ship
```

**Good Example:**
```python
# GOOD: Proper abstraction that all subtypes can honor
class Vessel(ABC):
    @abstractmethod
    def add_energy(self, amount: int):
        """Add energy to the vessel."""
        pass

class FuelPoweredShip(Vessel):
    def add_energy(self, amount: int):
        self._fuel += amount

class BatteryPoweredDrone(Vessel):
    def add_energy(self, amount: int):
        self._battery_charge += amount

# Both can be used interchangeably where Vessel is expected
def recharge_vessel(vessel: Vessel):
    vessel.add_energy(100)  # Works for both types
```

### 4.4 Interface Segregation Principle (ISP)

**Principle**: Clients should not be forced to depend on interfaces they don't use.

**Bad Example:**
```python
# VIOLATION: Fat interface forces unnecessary implementations
class TradingVessel(ABC):
    @abstractmethod
    def buy_cargo(self, commodity, qty): pass

    @abstractmethod
    def sell_cargo(self, commodity, qty): pass

    @abstractmethod
    def engage_weapons(self): pass  # Not all ships have weapons!

    @abstractmethod
    def cloak(self): pass  # Not all ships can cloak!

class BasicFreighter(TradingVessel):
    def engage_weapons(self):
        raise NotImplementedError("Freighter has no weapons")

    def cloak(self):
        raise NotImplementedError("Freighter cannot cloak")
```

**Good Example:**
```python
# GOOD: Segregated interfaces
class Trader(ABC):
    @abstractmethod
    def buy_cargo(self, commodity, qty): pass

    @abstractmethod
    def sell_cargo(self, commodity, qty): pass

class Armed(ABC):
    @abstractmethod
    def engage_weapons(self): pass

class Stealthy(ABC):
    @abstractmethod
    def cloak(self): pass

# Implement only needed interfaces
class BasicFreighter(Trader):
    def buy_cargo(self, commodity, qty): pass
    def sell_cargo(self, commodity, qty): pass

class Corvette(Trader, Armed):
    def buy_cargo(self, commodity, qty): pass
    def sell_cargo(self, commodity, qty): pass
    def engage_weapons(self): pass

class StealthShip(Trader, Armed, Stealthy):
    def buy_cargo(self, commodity, qty): pass
    def sell_cargo(self, commodity, qty): pass
    def engage_weapons(self): pass
    def cloak(self): pass
```

### 4.5 Dependency Inversion Principle (DIP)

**Principle**: Depend on abstractions, not concretions.

**Bad Example:**
```python
# VIOLATION: High-level class depends on low-level implementation
class TradingController:
    def __init__(self):
        self.repository = JSONShipRepository()  # Concrete dependency

    def save_ship(self, ship):
        self.repository.save(ship)
```

**Good Example:**
```python
# GOOD: Depend on abstraction, inject concrete implementation
class ShipRepository(ABC):
    @abstractmethod
    def save(self, ship: Ship) -> None:
        pass

    @abstractmethod
    def load(self, ship_id: str) -> Ship:
        pass

class JSONShipRepository(ShipRepository):
    def save(self, ship: Ship) -> None:
        # JSON implementation
        pass

    def load(self, ship_id: str) -> Ship:
        # JSON implementation
        pass

class SQLiteShipRepository(ShipRepository):
    def save(self, ship: Ship) -> None:
        # SQLite implementation
        pass

    def load(self, ship_id: str) -> Ship:
        # SQLite implementation
        pass

class TradingController:
    def __init__(self, repository: ShipRepository):  # Depend on abstraction
        self._repository = repository

    def save_ship(self, ship: Ship) -> None:
        self._repository.save(ship)

# Usage with dependency injection
repository = JSONShipRepository()  # Or SQLiteShipRepository()
controller = TradingController(repository)
```

## 5. Test-Driven Development (TDD)

### 5.1 TDD Cycle: Red-Green-Refactor

1. **Red**: Write a failing test
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Clean up code while keeping tests green

### 5.2 TDD Workflow Example

**Step 1: Write the test first**
```python
# tests/test_trading.py
import pytest
from spacegame.models.ship import Ship
from spacegame.models.commodity import Commodity

def test_ship_can_add_cargo_within_capacity():
    """Test that ship can add cargo if space is available."""
    # Arrange
    ship = Ship(cargo_capacity=100, name="Test Ship")
    commodity = Commodity(id="food", volume_per_unit=1)

    # Act
    result = ship.add_cargo("food", 50)

    # Assert
    assert result is True
    assert ship.cargo_used == 50

def test_ship_cannot_exceed_cargo_capacity():
    """Test that ship rejects cargo exceeding capacity."""
    # Arrange
    ship = Ship(cargo_capacity=100, name="Test Ship")

    # Act
    result = ship.add_cargo("food", 150)

    # Assert
    assert result is False
    assert ship.cargo_used == 0
```

**Step 2: Run tests (they fail - RED)**

**Step 3: Write minimal implementation**
```python
# spacegame/models/ship.py
class Ship:
    def __init__(self, cargo_capacity: int, name: str):
        self._cargo_capacity = cargo_capacity
        self._name = name
        self._cargo: Dict[str, int] = {}

    @property
    def cargo_used(self) -> int:
        return sum(self._cargo.values())

    def add_cargo(self, commodity_id: str, quantity: int) -> bool:
        if self.cargo_used + quantity > self._cargo_capacity:
            return False

        if commodity_id in self._cargo:
            self._cargo[commodity_id] += quantity
        else:
            self._cargo[commodity_id] = quantity

        return True
```

**Step 4: Run tests (they pass - GREEN)**

**Step 5: Refactor if needed**
```python
# Refactored version with better encapsulation
class Ship:
    def __init__(self, cargo_capacity: int, name: str):
        self._cargo_capacity = cargo_capacity
        self._name = name
        self._cargo: Dict[str, int] = {}

    @property
    def cargo_used(self) -> int:
        return sum(self._cargo.values())

    @property
    def cargo_available(self) -> int:
        return self._cargo_capacity - self.cargo_used

    def add_cargo(self, commodity_id: str, quantity: int) -> bool:
        if not self._has_space_for(quantity):
            return False

        self._add_to_cargo_hold(commodity_id, quantity)
        return True

    def _has_space_for(self, quantity: int) -> bool:
        return quantity <= self.cargo_available

    def _add_to_cargo_hold(self, commodity_id: str, quantity: int) -> None:
        current_qty = self._cargo.get(commodity_id, 0)
        self._cargo[commodity_id] = current_qty + quantity
```

### 5.3 Test Structure and Organization

**Test File Structure:**
```
tests/
├── __init__.py
├── test_models/
│   ├── test_ship.py
│   ├── test_commodity.py
│   ├── test_market.py
│   └── test_player.py
├── test_controllers/
│   ├── test_trading.py
│   ├── test_navigation.py
│   └── test_economy.py
└── test_utils/
    ├── test_pathfinding.py
    └── test_formatter.py
```

**Test Naming Convention:**
```python
def test_<unit>_<scenario>_<expected_result>():
    """Clear, descriptive test name."""
    pass

# Examples:
def test_ship_add_cargo_succeeds_when_space_available():
    pass

def test_market_calculate_price_applies_supply_demand_modifier():
    pass

def test_pathfinding_finds_shortest_route_between_systems():
    pass
```

### 5.4 Test Organization: AAA Pattern

**Arrange-Act-Assert:**
```python
def test_trade_profit_calculation():
    # Arrange: Set up test data and conditions
    buy_price = 100
    sell_price = 150
    quantity = 50
    expected_profit = 2500

    # Act: Execute the behavior being tested
    actual_profit = calculate_profit(buy_price, sell_price, quantity)

    # Assert: Verify the result
    assert actual_profit == expected_profit
```

### 5.5 Test Coverage Goals

**Coverage Targets:**
- **Models**: 90%+ coverage (critical business logic)
- **Controllers**: 80%+ coverage (orchestration logic)
- **Utils**: 85%+ coverage (helper functions)
- **Views**: 50%+ coverage (UI rendering, harder to test)

**Use pytest-cov:**
```bash
pytest --cov=spacegame --cov-report=html
```

### 5.6 Types of Tests

#### Unit Tests
Test individual components in isolation:
```python
def test_commodity_price_calculation():
    commodity = Commodity(base_price=100)
    market = Market(supply_demand_modifier=0.2)

    price = commodity.calculate_current_price(market)

    assert price == 120
```

#### Integration Tests
Test multiple components together:
```python
def test_complete_trade_transaction():
    player = Player(credits=10000)
    ship = Ship(cargo_capacity=100)
    market = Market()

    trading_controller = TradingController(player, ship, market)
    result = trading_controller.buy_commodity("food", 50)

    assert result is True
    assert player.credits == 7500  # 50 * 50 CR
    assert ship.cargo["food"] == 50
```

#### End-to-End Tests (Minimal)
Test full workflows:
```python
def test_player_can_complete_profitable_trade_route():
    game = Game.new_game()

    # Travel to system A
    game.travel_to("alpha_centauri")

    # Buy commodities
    game.buy_commodity("food", 100)

    # Travel to system B
    game.travel_to("proxima")

    # Sell commodities
    profit = game.sell_commodity("food", 100)

    assert profit > 0
    assert game.player.credits > 1000  # Starting credits
```

### 5.7 Test Fixtures and Mocking

**Use pytest fixtures:**
```python
import pytest

@pytest.fixture
def sample_ship():
    """Provide a standard test ship."""
    return Ship(
        cargo_capacity=150,
        fuel_capacity=200,
        name="Test Freighter"
    )

@pytest.fixture
def sample_market():
    """Provide a standard test market."""
    return Market(
        system_id="test_system",
        commodities={
            "food": {"price": 50, "supply": 1000},
            "metals": {"price": 100, "supply": 500}
        }
    )

def test_ship_trading(sample_ship, sample_market):
    """Use fixtures in tests."""
    assert sample_ship.cargo_capacity == 150
    assert sample_market.get_price("food") == 50
```

**Mock external dependencies:**
```python
from unittest.mock import Mock, patch

def test_save_game_writes_to_file():
    mock_file_handler = Mock()
    save_manager = SaveManager(file_handler=mock_file_handler)

    game_state = GameState(player_credits=5000)
    save_manager.save(game_state)

    mock_file_handler.write.assert_called_once()
```

## 6. Clean Code Principles

### 6.1 Meaningful Names

**Bad:**
```python
# Unclear, abbreviated names
def calc(p1, p2, q):
    return (p2 - p1) * q

x = calc(100, 150, 50)
```

**Good:**
```python
# Clear, descriptive names
def calculate_trade_profit(
    buy_price: int,
    sell_price: int,
    quantity: int
) -> int:
    """Calculate profit from a trade transaction."""
    return (sell_price - buy_price) * quantity

profit = calculate_trade_profit(
    buy_price=100,
    sell_price=150,
    quantity=50
)
```

### 6.2 Functions Should Do One Thing

**Bad:**
```python
def process_trade(player, ship, commodity, quantity, action):
    # Does too many things!
    if action == "buy":
        price = commodity.base_price * quantity
        if player.credits >= price:
            player.credits -= price
            ship.add_cargo(commodity.id, quantity)
            print(f"Bought {quantity} {commodity.name}")
            return True
    elif action == "sell":
        if commodity.id in ship.cargo:
            price = commodity.base_price * quantity
            player.credits += price
            ship.remove_cargo(commodity.id, quantity)
            print(f"Sold {quantity} {commodity.name}")
            return True
    return False
```

**Good:**
```python
def buy_commodity(
    player: Player,
    ship: Ship,
    commodity: Commodity,
    quantity: int
) -> bool:
    """Purchase commodity and add to ship cargo."""
    total_cost = commodity.base_price * quantity

    if not player.can_afford(total_cost):
        return False

    if not ship.has_cargo_space(quantity):
        return False

    player.deduct_credits(total_cost)
    ship.add_cargo(commodity.id, quantity)

    return True

def sell_commodity(
    player: Player,
    ship: Ship,
    commodity: Commodity,
    quantity: int
) -> bool:
    """Sell commodity from ship cargo."""
    if not ship.has_cargo(commodity.id, quantity):
        return False

    total_revenue = commodity.base_price * quantity

    ship.remove_cargo(commodity.id, quantity)
    player.add_credits(total_revenue)

    return True
```

### 6.3 Keep Functions Small

**Guideline**: Functions should be 5-15 lines ideally, max 20-30 lines

**Bad:**
```python
def update_market_prices(self):
    # 100+ line function doing everything
    pass
```

**Good:**
```python
def update_market_prices(self):
    """Update all commodity prices based on current conditions."""
    self._apply_supply_demand_changes()
    self._apply_random_variance()
    self._apply_event_modifiers()
    self._clamp_prices_to_valid_range()

def _apply_supply_demand_changes(self):
    """Apply supply/demand modifiers to prices."""
    for commodity_id, market_data in self._markets.items():
        modifier = self._calculate_supply_demand_modifier(market_data)
        market_data.price *= (1 + modifier)

def _apply_random_variance(self):
    """Add random price fluctuations."""
    # Implementation
    pass
```

### 6.4 Avoid Deep Nesting

**Bad:**
```python
def process_event(self, event):
    if event.type == "trade":
        if self.player.is_at_station:
            if event.commodity in self.market.commodities:
                if event.quantity > 0:
                    if self.player.credits >= event.total_cost:
                        # Finally do something!
                        self.execute_trade(event)
```

**Good:**
```python
def process_trade_event(self, event: TradeEvent) -> bool:
    """Process a trade event with early returns."""
    if not self._is_valid_trade_event(event):
        return False

    self._execute_trade(event)
    return True

def _is_valid_trade_event(self, event: TradeEvent) -> bool:
    """Validate trade event conditions."""
    if not self.player.is_at_station:
        return False

    if event.commodity not in self.market.commodities:
        return False

    if event.quantity <= 0:
        return False

    if self.player.credits < event.total_cost:
        return False

    return True
```

### 6.5 Use Type Hints

**Always use type hints for clarity and tooling support:**

```python
from typing import List, Dict, Optional, Tuple

def find_profitable_routes(
    galaxy: Galaxy,
    current_system: str,
    max_jumps: int
) -> List[TradeRoute]:
    """Find profitable trade routes within jump range."""
    routes: List[TradeRoute] = []

    for system_id in galaxy.get_systems_within_jumps(current_system, max_jumps):
        route = self._evaluate_system_for_profit(system_id)
        if route:
            routes.append(route)

    return sorted(routes, key=lambda r: r.profit, reverse=True)

def get_commodity_price(
    self,
    commodity_id: str,
    system_id: str
) -> Optional[int]:
    """
    Get current price for a commodity in a system.

    Returns:
        Price in credits, or None if commodity not available
    """
    market = self._markets.get(system_id)
    if not market:
        return None

    return market.get_price(commodity_id)
```

### 6.6 Comments and Documentation

**When to Comment:**
- **Why**, not **what** (code shows what)
- Complex algorithms
- Business rules that aren't obvious
- Workarounds or hacks (with explanation)

**Bad:**
```python
# Add quantity to cargo
self._cargo[commodity_id] += quantity
```

**Good:**
```python
# Apply 10% bulk discount for purchases over 100 units
# per requirement in Economic System Requirements doc
if quantity > 100:
    total_cost *= 0.9
```

**Use Docstrings:**
```python
def calculate_route_fuel_cost(
    self,
    start: str,
    end: str,
    ship: Ship
) -> int:
    """
    Calculate total fuel cost for a route.

    Uses Dijkstra's algorithm to find the shortest path between systems,
    then calculates fuel consumption based on ship efficiency.

    Args:
        start: Starting system ID
        end: Destination system ID
        ship: Ship object with fuel efficiency data

    Returns:
        Total fuel units required for the route

    Raises:
        NoRouteFoundError: If no path exists between systems

    Example:
        >>> ship = Ship(fuel_efficiency=15)
        >>> fuel_cost = calculator.calculate_route_fuel_cost("sol", "proxima", ship)
        >>> print(fuel_cost)
        30
    """
    path = self._find_shortest_path(start, end)
    jumps = len(path) - 1
    return jumps * ship.fuel_efficiency
```

### 6.7 Error Handling

**Use Specific Exceptions:**
```python
# Bad
def buy_cargo(self, commodity_id: str, quantity: int):
    if not self.can_afford(commodity_id, quantity):
        raise Exception("Can't buy")  # Too vague!

# Good
class InsufficientCreditsError(Exception):
    """Raised when player doesn't have enough credits."""
    pass

class InsufficientCargoSpaceError(Exception):
    """Raised when ship doesn't have enough cargo space."""
    pass

def buy_cargo(self, commodity_id: str, quantity: int):
    cost = self._calculate_cost(commodity_id, quantity)

    if self.player.credits < cost:
        raise InsufficientCreditsError(
            f"Need {cost} CR, have {self.player.credits} CR"
        )

    if not self.ship.has_space_for(quantity):
        raise InsufficientCargoSpaceError(
            f"Need {quantity} space, have {self.ship.cargo_available}"
        )

    # Proceed with purchase
```

**Fail Fast:**
```python
def process_trade(self, trade_request: TradeRequest):
    # Validate early, fail fast
    self._validate_trade_request(trade_request)

    # If we get here, we know the request is valid
    self._execute_trade(trade_request)
```

### 6.8 Constants and Magic Numbers

**Bad:**
```python
def calculate_reputation_change(self, action):
    if action == "trade":
        return 1  # What does 1 mean?
    elif action == "mission":
        return 15  # Why 15?
```

**Good:**
```python
# Constants defined at module or class level
REPUTATION_GAIN_TRADE = 1
REPUTATION_GAIN_MISSION = 15
REPUTATION_LOSS_ILLEGAL_TRADE = -20

def calculate_reputation_change(self, action: str) -> int:
    reputation_changes = {
        "trade": REPUTATION_GAIN_TRADE,
        "mission": REPUTATION_GAIN_MISSION,
        "illegal_trade": REPUTATION_LOSS_ILLEGAL_TRADE,
    }
    return reputation_changes.get(action, 0)
```

## 7. Code Organization and Structure

### 7.1 Module Cohesion

Each module should have a single, clear purpose:

```python
# spacegame/models/ship.py - Only ship-related models
class Ship:
    pass

class ShipType:
    pass

# spacegame/controllers/trading.py - Only trading logic
class TradingController:
    pass

# spacegame/utils/pathfinding.py - Only pathfinding utilities
def find_shortest_path(graph, start, end):
    pass
```

### 7.2 Dependency Direction

**Dependencies should flow inward:**
```
Views → Controllers → Models
   ↓         ↓          ↓
   └─────────→ Utils ←─┘
```

**Never:**
- Models depend on Controllers or Views
- Utils depend on anything except other Utils

### 7.3 Avoid Circular Dependencies

**Bad:**
```python
# ship.py
from market import Market

class Ship:
    def dock_at(self, market: Market):
        pass

# market.py
from ship import Ship  # CIRCULAR!

class Market:
    def accept_ship(self, ship: Ship):
        pass
```

**Good:**
```python
# Use forward references or restructure
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from market import Market

class Ship:
    def dock_at(self, market: 'Market'):  # String reference
        pass
```

## 8. Performance and Optimization

### 8.1 Premature Optimization

**Rule**: Don't optimize until you measure and identify bottlenecks.

**Process:**
1. Write clean, readable code first
2. Profile the code
3. Optimize only the bottlenecks
4. Measure improvement
5. Maintain readability

### 8.2 When to Optimize

**Profile First:**
```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your code
    game_loop()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 time consumers
```

**Optimize data structures and algorithms before micro-optimizations:**
```python
# Bad: O(n) search repeated
def find_expensive_commodities(commodities):
    expensive = []
    for c in commodities:
        if c.base_price > 1000:  # O(n)
            expensive.append(c)
    return expensive

# Good: O(1) lookup with proper indexing
class CommodityIndex:
    def __init__(self, commodities):
        self._by_price = self._index_by_price(commodities)

    def get_expensive(self):
        return self._by_price.get("expensive", [])
```

## 9. Code Review Checklist

### 9.1 Before Committing

- [ ] All tests pass
- [ ] New code has tests (TDD)
- [ ] Code follows SOLID principles
- [ ] No code duplication (DRY)
- [ ] Functions are small and focused
- [ ] Type hints are used
- [ ] Docstrings are present for public APIs
- [ ] No magic numbers or strings
- [ ] Naming is clear and descriptive
- [ ] Code is formatted with Black
- [ ] Linting passes (pylint/flake8)
- [ ] Type checking passes (mypy)

### 9.2 Automated Checks

**Use pre-commit hooks:**
```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
```

**Run before commit:**
```bash
black spacegame/
flake8 spacegame/
mypy spacegame/
pytest
```

## 10. Refactoring Guidelines

### 10.1 When to Refactor

- When adding new features (make it easy to add)
- When fixing bugs (prevent similar bugs)
- When code smells appear (duplication, complexity)
- During code review (before merging)
- **Never** without test coverage

### 10.2 Refactoring Patterns

**Extract Method:**
```python
# Before
def calculate_total_cost(self, items):
    total = 0
    for item in items:
        total += item.price * item.quantity
        total += item.price * item.quantity * 0.1  # tax
    return total

# After
def calculate_total_cost(self, items):
    subtotal = self._calculate_subtotal(items)
    tax = self._calculate_tax(subtotal)
    return subtotal + tax

def _calculate_subtotal(self, items):
    return sum(item.price * item.quantity for item in items)

def _calculate_tax(self, subtotal):
    return subtotal * 0.1
```

**Extract Class:**
```python
# Before
class Ship:
    def __init__(self):
        self.cargo_items = {}
        self.cargo_capacity = 100

    def add_cargo(self, item, qty): pass
    def remove_cargo(self, item, qty): pass
    def cargo_used(self): pass

# After
class CargoHold:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = {}

    def add(self, item, qty): pass
    def remove(self, item, qty): pass
    def used(self): pass

class Ship:
    def __init__(self):
        self.cargo_hold = CargoHold(capacity=100)
```

### 10.3 Refactoring Safety

**Always refactor with tests:**
1. Ensure tests are green
2. Make small refactoring change
3. Run tests
4. Repeat

**Never:**
- Refactor and add features simultaneously
- Refactor without test coverage
- Make large refactoring changes in one commit

## 11. Documentation Standards

### 11.1 Code-Level Documentation

**Module Docstrings:**
```python
"""
Ship management and cargo operations.

This module provides classes for managing trading vessels, including
cargo hold operations, fuel management, and ship upgrades.

Classes:
    Ship: Represents a trading vessel
    ShipType: Ship class definitions and specifications
    CargoHold: Manages commodity storage
"""
```

**Class Docstrings:**
```python
class Ship:
    """
    Represents a trading vessel in the game.

    A ship has cargo capacity, fuel capacity, and various upgrades.
    It can travel between systems and trade commodities.

    Attributes:
        name: Custom name for the ship
        ship_type: ShipType instance defining capabilities
        cargo_hold: CargoHold instance managing commodities
        fuel_current: Current fuel level

    Example:
        >>> ship_type = ShipType.get_by_id("freighter")
        >>> ship = Ship(ship_type, name="Millennium Eagle")
        >>> ship.add_cargo("food", 50)
        True
    """
```

### 11.2 README and Project Documentation

**Update README.md with:**
- Project setup instructions
- How to run tests
- Coding standards (link to this doc)
- Architecture overview

## 12. Metrics and Quality Gates

### 12.1 Code Quality Metrics

**Track these metrics:**
- **Test Coverage**: >80% overall
- **Cyclomatic Complexity**: <10 per function
- **Maintainability Index**: >65
- **Code Duplication**: <3%

**Tools:**
```bash
# Coverage
pytest --cov=spacegame --cov-report=html

# Complexity
radon cc spacegame/ -a

# Maintainability
radon mi spacegame/
```

### 12.2 Quality Gates

**Don't merge code that:**
- Has failing tests
- Reduces coverage by >2%
- Has functions with complexity >15
- Violates linting rules
- Lacks docstrings for public APIs

## 13. Open Questions and Evolution

### 13.1 Pending Decisions

- Should we use dataclasses for simple data containers?
- When to use Protocol vs ABC for interfaces?
- How strict should type checking be (mypy --strict)?

### 13.2 Future Enhancements

- Integrate with CI/CD pipeline
- Add mutation testing (mutpy)
- Implement property-based testing (Hypothesis)
- Add performance benchmarks

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Review**: All code should be reviewed against these principles before merging
