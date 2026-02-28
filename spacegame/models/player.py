"""
Player state and progression models.

Tracks player credits, location, ship, and game progress.
"""

from dataclasses import dataclass, field
from typing import Optional
from spacegame.models.ship import Ship
from spacegame.models.progression import PlayerProgression
from spacegame.models.upgrades import ShipUpgradeManager
from spacegame.models.drone import MiningDroneFleet
from spacegame.models.faction import ReputationTier, get_reputation_tier


@dataclass
class Player:
    """
    Represents the player's current state in the game.

    Tracks credits, location, ship, and progression metrics.
    """

    name: str
    credits: int
    current_system_id: str
    ship: Ship
    game_day: int = 1  # Turn counter for turn-based travel
    total_profit: int = 0  # Career profit tracking
    trades_completed: int = 0
    systems_visited: set[str] = field(default_factory=set)
    progression: PlayerProgression = field(default_factory=PlayerProgression)
    upgrade_manager: ShipUpgradeManager = field(default_factory=ShipUpgradeManager)
    drone_fleet: MiningDroneFleet = field(default_factory=MiningDroneFleet)

    # Faction reputation system
    faction_reputation: dict[str, int] = field(default_factory=dict)
    faction_assignments: dict[str, str] = field(default_factory=dict)

    # Dialogue system
    dialogue_flags: dict[str, bool] = field(default_factory=dict)

    # Trade permit system (bills of landing)
    trade_permits: set[str] = field(default_factory=set)

    # Mission system
    mission_state: dict = field(default_factory=dict)

    # Crew system
    crew_state: dict = field(default_factory=dict)

    # Lifetime statistics for achievements
    credits_earned_lifetime: int = 0
    credits_spent_lifetime: int = 0
    largest_single_profit: int = 0
    jumps_traveled: int = 0
    fuel_consumed: int = 0
    ore_mined: int = 0
    items_salvaged: int = 0
    items_refined: int = 0
    unlocked_achievements: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize visited systems with starting location."""
        self.systems_visited.add(self.current_system_id)
        # Link upgrade manager to ship for bonus calculations
        self.ship.set_upgrade_manager(self.upgrade_manager)

    def can_afford(self, cost: int) -> bool:
        """
        Check if player can afford a purchase.

        Args:
            cost: Amount in credits

        Returns:
            True if player has enough credits
        """
        return self.credits >= cost

    def add_credits(self, amount: int) -> None:
        """
        Add credits to player's account.

        Args:
            amount: Credits to add
        """
        self.credits += amount

    def deduct_credits(self, amount: int) -> bool:
        """
        Deduct credits from player's account.

        Args:
            amount: Credits to deduct

        Returns:
            True if successful, False if insufficient funds
        """
        if not self.can_afford(amount):
            return False
        self.credits -= amount
        return True

    def buy_commodity(
        self,
        commodity_id: str,
        quantity: int,
        price_per_unit: int,
        commodity_volumes: dict[str, int],
    ) -> tuple[bool, str]:
        """
        Purchase commodity and add to ship cargo.

        Args:
            commodity_id: ID of commodity to buy
            quantity: Amount to purchase
            price_per_unit: Current market price
            commodity_volumes: Dict of commodity volumes

        Returns:
            Tuple of (success: bool, message: str)
        """
        total_cost = price_per_unit * quantity

        # Check funds
        if not self.can_afford(total_cost):
            return (False, f"Insufficient funds. Need {total_cost:,} CR, have {self.credits:,} CR")

        # Check cargo space
        if not self.ship.can_carry(commodity_id, quantity, commodity_volumes):
            return (False, "Insufficient cargo space")

        # Execute transaction
        self.deduct_credits(total_cost)
        self.ship.add_cargo(commodity_id, quantity, price_per_unit)
        self.trades_completed += 1
        self.credits_spent_lifetime += total_cost

        return (True, f"Purchased {quantity} units for {total_cost:,} CR")

    def sell_commodity(
        self, commodity_id: str, quantity: int, price_per_unit: int
    ) -> tuple[bool, str]:
        """
        Sell commodity from ship cargo.

        Args:
            commodity_id: ID of commodity to sell
            quantity: Amount to sell
            price_per_unit: Current market price

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check cargo
        if self.ship.get_cargo_quantity(commodity_id) < quantity:
            return (False, "Insufficient quantity in cargo")

        # Execute transaction
        total_revenue = price_per_unit * quantity
        avg_cost = self.ship.get_average_purchase_price(commodity_id)
        profit = (price_per_unit - avg_cost) * quantity
        self.ship.remove_cargo(commodity_id, quantity)
        self.add_credits(total_revenue)
        self.trades_completed += 1
        self.total_profit += total_revenue  # Simplified - doesn't track buy price
        self.credits_earned_lifetime += total_revenue
        if profit > self.largest_single_profit:
            self.largest_single_profit = profit

        return (True, f"Sold {quantity} units for {total_revenue:,} CR")

    def travel_to_system(self, system_id: str, fuel_cost: int) -> tuple[bool, str]:
        """
        Travel to a new system (turn-based).

        Args:
            system_id: Target system ID
            fuel_cost: Fuel required for jump

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check fuel
        if not self.ship.has_fuel_for_jump(fuel_cost):
            return (False, f"Insufficient fuel. Need {fuel_cost}, have {self.ship.current_fuel}")

        # Execute travel
        self.ship.consume_fuel(fuel_cost)
        self.current_system_id = system_id
        self.systems_visited.add(system_id)
        self.game_day += 1  # Turn-based: each jump is one day
        self.jumps_traveled += 1
        self.fuel_consumed += fuel_cost

        return (True, f"Arrived at {system_id}. Day {self.game_day}")

    def rest_at_system(self, rest_cost: int) -> tuple[bool, str]:
        """
        Rest at current system for one day (advances time, triggers market changes).

        Args:
            rest_cost: Cost to stay at this system for one day

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check funds
        if not self.can_afford(rest_cost):
            return (False, f"Insufficient funds. Need {rest_cost:,} CR, have {self.credits:,} CR")

        # Execute rest
        self.deduct_credits(rest_cost)
        self.game_day += 1  # Advance time (triggers market changes)

        return (True, f"Rested for {rest_cost:,} CR. Day {self.game_day}. Markets have changed!")

    def refuel_ship(self, fuel_quantity: int, price_per_unit: int) -> tuple[bool, str]:
        """
        Purchase and add fuel to ship.

        Args:
            fuel_quantity: Amount of fuel to buy
            price_per_unit: Price per fuel unit

        Returns:
            Tuple of (success: bool, message: str)
        """
        total_cost = fuel_quantity * price_per_unit

        # Check funds
        if not self.can_afford(total_cost):
            return (False, f"Insufficient funds. Need {total_cost:,} CR")

        # Check tank capacity
        actual_added = self.ship.refuel(fuel_quantity)
        actual_cost = actual_added * price_per_unit

        # Deduct only for actual fuel added
        self.deduct_credits(actual_cost)

        if actual_added < fuel_quantity:
            return (True, f"Added {actual_added} fuel (tank full) for {actual_cost:,} CR")
        else:
            return (True, f"Added {actual_added} fuel for {actual_cost:,} CR")

    def get_net_worth(self) -> int:
        """
        Calculate player's total net worth.

        Returns:
            Total net worth (credits + ship value + cargo value estimate)
        """
        # Simplified: credits + ship resale value
        # TODO: Add cargo value calculation when market prices available
        return self.credits + self.ship.ship_type.resale_value

    def get_statistics(self) -> dict[str, any]:
        """
        Get player statistics for display.

        Returns:
            Dict of statistics
        """
        return {
            "name": self.name,
            "credits": self.credits,
            "day": self.game_day,
            "ship": self.ship.name,
            "location": self.current_system_id,
            "fuel": f"{self.ship.current_fuel}/{self.ship.max_fuel}",
            "fuel_percent": self.ship.get_fuel_percentage(),
            "trades": self.trades_completed,
            "systems_visited": len(self.systems_visited),
            "net_worth": self.get_net_worth(),
            "credits_earned_lifetime": self.credits_earned_lifetime,
            "credits_spent_lifetime": self.credits_spent_lifetime,
            "largest_single_profit": self.largest_single_profit,
            "jumps_traveled": self.jumps_traveled,
            "fuel_consumed": self.fuel_consumed,
            "ore_mined": self.ore_mined,
            "items_salvaged": self.items_salvaged,
            "items_refined": self.items_refined,
            "level": self.progression.level,
            "xp": self.progression.xp,
            "skill_points_spent": self.progression.skill_points_spent,
        }

    def has_trade_permit(self, faction_id: str) -> bool:
        """Check if player has a trade permit for a faction.

        Args:
            faction_id: Faction to check.

        Returns:
            True if player holds a permit for this faction.
        """
        return faction_id in self.trade_permits

    def grant_trade_permit(self, faction_id: str) -> None:
        """Grant a trade permit (bill of landing) for a faction.

        Args:
            faction_id: Faction to grant permit for.
        """
        self.trade_permits.add(faction_id)

    def get_faction_for_system(self, system_id: str) -> Optional[str]:
        """Get the faction ID controlling a system.

        Args:
            system_id: System to look up.

        Returns:
            Faction ID, or None if system has no assignment.
        """
        return self.faction_assignments.get(system_id)

    def modify_reputation(self, faction_id: str, amount: int) -> tuple[bool, str]:
        """Modify reputation with a faction, clamped to [-100, +100].

        Args:
            faction_id: Faction to modify reputation with.
            amount: Amount to add (positive or negative).

        Returns:
            Tuple of (success, message).
        """
        current = self.faction_reputation.get(faction_id, 0)
        new_rep = max(-100, min(100, current + amount))
        self.faction_reputation[faction_id] = new_rep
        sign = "+" if amount >= 0 else ""
        return (True, f"{sign}{amount} reputation with {faction_id}")

    def get_reputation(self, faction_id: str) -> int:
        """Get current reputation value with a faction.

        Args:
            faction_id: Faction to check.

        Returns:
            Reputation value (-100 to +100), defaults to 0.
        """
        return self.faction_reputation.get(faction_id, 0)

    def get_reputation_tier(self, faction_id: str) -> ReputationTier:
        """Get the reputation tier with a faction.

        Args:
            faction_id: Faction to check.

        Returns:
            The ReputationTier enum value.
        """
        return get_reputation_tier(self.get_reputation(faction_id))
