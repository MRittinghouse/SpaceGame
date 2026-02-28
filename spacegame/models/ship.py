"""
Ship and fleet models.

Defines ship types, their capabilities, and player ship instances.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ShipType:
    """
    Template/blueprint for a ship class.

    Defines the base statistics and properties of a ship type.
    """

    id: str
    name: str
    ship_class: str  # starter, early_game, mid_game, late_game
    description: str
    cargo_capacity: int
    fuel_capacity: int
    fuel_efficiency: int  # Fuel consumed per jump
    speed_multiplier: float  # For turn-based: affects travel time
    purchase_price: int
    resale_value: int
    crew_slots: int
    special_abilities: List[str]
    availability: str  # common, uncommon, rare

    def can_afford(self, credits: int) -> bool:
        """
        Check if player can afford this ship.

        Args:
            credits: Player's current credits

        Returns:
            True if affordable
        """
        return credits >= self.purchase_price


@dataclass
class Ship:
    """
    Player's actual ship instance.

    Tracks current state including cargo, fuel, and damage.
    """

    ship_type: ShipType
    current_fuel: int
    current_cargo: Dict[str, int] = field(default_factory=dict)  # commodity_id -> quantity
    cargo_purchase_prices: Dict[str, int] = field(
        default_factory=dict
    )  # commodity_id -> total_cost_paid
    damage_level: int = 0  # 0-100, future feature

    def __post_init__(self) -> None:
        """Initialize ship with full fuel if not specified."""
        # Optional references to bonus sources (set by Player/Game after init)
        if not hasattr(self, "_upgrade_manager"):
            self._upgrade_manager = None
        if not hasattr(self, "_crew_roster"):
            self._crew_roster = None
        if self.current_fuel == 0:
            self.current_fuel = self.ship_type.fuel_capacity

    def set_upgrade_manager(self, manager) -> None:
        """Link an upgrade manager for bonus calculations."""
        self._upgrade_manager = manager

    def set_crew_roster(self, roster) -> None:
        """Link a crew roster for bonus calculations."""
        self._crew_roster = roster

    def get_crew_bonus(self, bonus_type: str) -> float:
        """Get a crew bonus by type, or 0.0 if no crew roster linked."""
        if self._crew_roster:
            return self._crew_roster.get_bonus(bonus_type)
        return 0.0

    @property
    def name(self) -> str:
        """Get ship type name."""
        return self.ship_type.name

    @property
    def max_cargo(self) -> int:
        """Get maximum cargo capacity including upgrade and crew bonuses."""
        base = self.ship_type.cargo_capacity
        if self._upgrade_manager:
            base += int(self._upgrade_manager.get_bonus("cargo_bonus"))
        if self._crew_roster:
            base += int(self._crew_roster.get_bonus("cargo_bonus"))
        return base

    @property
    def max_fuel(self) -> int:
        """Get maximum fuel capacity including upgrade and crew bonuses."""
        base = self.ship_type.fuel_capacity
        if self._upgrade_manager:
            base += int(self._upgrade_manager.get_bonus("fuel_bonus"))
        if self._crew_roster:
            base += int(self._crew_roster.get_bonus("fuel_bonus"))
        return base

    @property
    def effective_fuel_efficiency(self) -> int:
        """Get fuel efficiency (per-jump cost) accounting for upgrade and crew bonuses."""
        base = self.ship_type.fuel_efficiency
        if self._upgrade_manager:
            base = max(1, base - int(self._upgrade_manager.get_bonus("fuel_efficiency_bonus")))
        if self._crew_roster:
            base = max(1, base - int(self._crew_roster.get_bonus("fuel_efficiency_bonus")))
        return base

    def get_used_cargo(self, commodity_volumes: Dict[str, int]) -> int:
        """
        Calculate total cargo space currently used.

        Args:
            commodity_volumes: Dict mapping commodity_id to volume_per_unit

        Returns:
            Total cargo space used
        """
        total = 0
        for commodity_id, quantity in self.current_cargo.items():
            volume_per_unit = commodity_volumes.get(commodity_id, 1)
            total += quantity * volume_per_unit
        return total

    def get_available_cargo(self, commodity_volumes: Dict[str, int]) -> int:
        """
        Calculate available cargo space.

        Args:
            commodity_volumes: Dict mapping commodity_id to volume_per_unit

        Returns:
            Available cargo space
        """
        return self.max_cargo - self.get_used_cargo(commodity_volumes)

    def can_carry(
        self, commodity_id: str, quantity: int, commodity_volumes: Dict[str, int]
    ) -> bool:
        """
        Check if ship can carry additional cargo.

        Args:
            commodity_id: ID of commodity to add
            quantity: Number of units to add
            commodity_volumes: Dict mapping commodity_id to volume_per_unit

        Returns:
            True if cargo fits
        """
        volume_needed = quantity * commodity_volumes.get(commodity_id, 1)
        return volume_needed <= self.get_available_cargo(commodity_volumes)

    def add_cargo(self, commodity_id: str, quantity: int, price_per_unit: int = 0) -> None:
        """
        Add commodity to cargo hold and track purchase price.

        Args:
            commodity_id: Commodity to add
            quantity: Amount to add
            price_per_unit: Price paid per unit (for tracking average cost)
        """
        current_amount = self.current_cargo.get(commodity_id, 0)
        self.current_cargo[commodity_id] = current_amount + quantity

        # Track total cost paid for this commodity
        if price_per_unit > 0:
            current_total_cost = self.cargo_purchase_prices.get(commodity_id, 0)
            self.cargo_purchase_prices[commodity_id] = current_total_cost + (
                price_per_unit * quantity
            )

    def remove_cargo(self, commodity_id: str, quantity: int) -> bool:
        """
        Remove commodity from cargo hold and update purchase price tracking.

        Args:
            commodity_id: Commodity to remove
            quantity: Amount to remove

        Returns:
            True if successful, False if insufficient quantity
        """
        current_amount = self.current_cargo.get(commodity_id, 0)
        if current_amount < quantity:
            return False

        new_amount = current_amount - quantity
        if new_amount == 0:
            del self.current_cargo[commodity_id]
            # Remove purchase price tracking when all cargo sold
            if commodity_id in self.cargo_purchase_prices:
                del self.cargo_purchase_prices[commodity_id]
        else:
            self.current_cargo[commodity_id] = new_amount
            # Proportionally reduce the total cost paid
            if commodity_id in self.cargo_purchase_prices:
                proportion_sold = quantity / current_amount
                self.cargo_purchase_prices[commodity_id] = int(
                    self.cargo_purchase_prices[commodity_id] * (1 - proportion_sold)
                )
        return True

    def get_cargo_quantity(self, commodity_id: str) -> int:
        """
        Get quantity of specific commodity in cargo.

        Args:
            commodity_id: Commodity to check

        Returns:
            Quantity in cargo
        """
        return self.current_cargo.get(commodity_id, 0)

    def get_average_purchase_price(self, commodity_id: str) -> int:
        """
        Get average price paid per unit for a commodity in cargo.

        Args:
            commodity_id: Commodity to check

        Returns:
            Average price per unit, or 0 if not tracked
        """
        quantity = self.get_cargo_quantity(commodity_id)
        if quantity == 0:
            return 0

        total_cost = self.cargo_purchase_prices.get(commodity_id, 0)
        return total_cost // quantity  # Integer division for CR

    def has_fuel_for_jump(self, fuel_cost: int) -> bool:
        """
        Check if ship has enough fuel for a jump.

        Args:
            fuel_cost: Fuel required

        Returns:
            True if sufficient fuel
        """
        return self.current_fuel >= fuel_cost

    def consume_fuel(self, amount: int) -> bool:
        """
        Consume fuel for travel.

        Args:
            amount: Fuel to consume

        Returns:
            True if successful, False if insufficient fuel
        """
        if not self.has_fuel_for_jump(amount):
            return False
        self.current_fuel -= amount
        return True

    def refuel(self, amount: int) -> int:
        """
        Add fuel to ship's tanks.

        Args:
            amount: Fuel to add

        Returns:
            Actual amount added (limited by tank capacity)
        """
        space_available = self.max_fuel - self.current_fuel
        actual_amount = min(amount, space_available)
        self.current_fuel += actual_amount
        return actual_amount

    def get_fuel_percentage(self) -> float:
        """
        Get fuel level as percentage.

        Returns:
            Fuel percentage (0.0 to 1.0)
        """
        return self.current_fuel / self.max_fuel if self.max_fuel > 0 else 0.0
