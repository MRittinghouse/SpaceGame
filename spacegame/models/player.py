"""
Player state and progression models.

Tracks player credits, location, ship, and game progress.
"""

from dataclasses import dataclass, field
from typing import Optional
from spacegame.models.ship import Ship, ShipType
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

    # Black market access permits (earned through narrative events)
    black_market_access: set[str] = field(default_factory=set)

    # Mission system
    mission_state: dict = field(default_factory=dict)

    # Crew system
    crew_state: dict = field(default_factory=dict)

    # Social skill system
    social_state: dict = field(default_factory=dict)

    # Attribute system
    attribute_state: dict = field(default_factory=dict)

    # Journal system
    journal_state: dict = field(default_factory=dict)

    # Hidden compartment (installed via upgrade)
    hidden_compartment: Optional["HiddenCompartment"] = None

    # Ground equipment inventory (equipment IDs owned)
    ground_equipment: list[str] = field(default_factory=list)

    # Smuggling contract manager state
    smuggling_contract_state: dict = field(default_factory=dict)

    # Ground contract manager state
    ground_contract_state: dict = field(default_factory=dict)

    # Political system state
    political_state: dict = field(default_factory=dict)

    # Smuggling system
    criminal_heat: int = 0
    goods_smuggled: int = 0
    smuggling_contracts_completed: int = 0
    times_caught_smuggling: int = 0
    inspections_passed_with_contraband: int = 0
    max_criminal_heat_reached: int = 0

    # Ground exploration statistics
    ground_missions_completed: int = 0
    ground_missions_failed: int = 0
    ground_enemies_defeated: int = 0
    ground_enemies_talked: int = 0
    ground_tiles_explored: int = 0
    ground_undetected_completions: int = 0
    ground_campaign_missions_completed: int = 0

    # Combat statistics
    combats_won: int = 0
    combats_fled: int = 0

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

    # Minigame statistics for achievements
    max_mining_depth: int = 0
    total_chains_triggered: int = 0
    rare_ores_mined: int = 0
    salvage_sessions_completed: int = 0
    corrupted_items_extracted: int = 0
    refining_jobs_completed: int = 0
    batch_jobs_queued: int = 0
    recipes_crafted: set[str] = field(default_factory=set)

    # Investment + rating stats
    investments_owned: int = 0
    s_ranks_earned: int = 0

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
        self.total_profit += profit
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
        self.decay_criminal_heat(1)
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
        self.decay_criminal_heat(1)

        return (True, f"Rested for {rest_cost:,} CR. Day {self.game_day}. Markets have changed!")

    def repair_at_station(self, cost_per_hp: int) -> tuple[bool, str]:
        """Repair ship hull to full at a station repair bay.

        Args:
            cost_per_hp: Credits charged per hull point repaired.

        Returns:
            Tuple of (success, message).
        """
        max_hull = self.ship.ship_type.combat_hull
        damage = max_hull - self.ship.current_hull
        if damage <= 0:
            return (False, "Hull is already at full integrity.")
        total_cost = damage * cost_per_hp
        if total_cost > 0 and not self.can_afford(total_cost):
            return (
                False,
                f"Insufficient credits. Repair costs {total_cost:,} CR, "
                f"have {self.credits:,} CR.",
            )
        self.deduct_credits(total_cost)
        repaired = self.ship.repair_hull(damage)
        return (True, f"Repaired {repaired} hull points for {total_cost:,} CR.")

    def swap_ship(self, new_type: ShipType) -> tuple[bool, str]:
        """Purchase a new ship, trading in the current one.

        The current ship is sold at its resale value. Cargo is transferred
        up to the new ship's capacity; excess is lost. The new ship starts
        with full fuel and full hull/shields.

        Args:
            new_type: The ShipType to purchase.

        Returns:
            Tuple of (success, message).
        """
        if new_type.id == self.ship.ship_type.id:
            return (False, "You already own this ship type.")

        resale = self.ship.ship_type.resale_value
        net_cost = new_type.purchase_price - resale
        if net_cost > self.credits:
            return (
                False,
                f"Cannot afford. Need {net_cost:,} CR after trade-in, "
                f"have {self.credits:,} CR.",
            )

        # Save references to transfer
        old_cargo = dict(self.ship.current_cargo)
        old_prices = dict(self.ship.cargo_purchase_prices)
        upgrade_mgr = getattr(self.ship, "_upgrade_manager", None)
        crew_roster = getattr(self.ship, "_crew_roster", None)

        # Create new ship
        new_ship = Ship(
            ship_type=new_type,
            current_fuel=new_type.fuel_capacity,
        )

        # Transfer cargo up to new capacity
        cargo_lost = 0
        for commodity_id, quantity in old_cargo.items():
            transferable = min(quantity, new_type.cargo_capacity)
            if transferable > 0:
                new_ship.add_cargo(commodity_id, transferable)
                if commodity_id in old_prices and quantity > 0:
                    proportion = transferable / quantity
                    new_ship.cargo_purchase_prices[commodity_id] = int(
                        old_prices.get(commodity_id, 0) * proportion
                    )
            if transferable < quantity:
                cargo_lost += quantity - transferable

        # Re-link bonus sources
        if upgrade_mgr:
            new_ship.set_upgrade_manager(upgrade_mgr)
        if crew_roster:
            new_ship.set_crew_roster(crew_roster)

        # Commit transaction
        self.credits = self.credits + resale - new_type.purchase_price
        self.ship = new_ship

        msg = f"Purchased {new_type.name}!"
        if cargo_lost > 0:
            msg += f" Warning: {cargo_lost} units of cargo could not fit."
        return (True, msg)

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

    def apply_combat_defeat(self, safe_system_id: str) -> None:
        """Apply consequences of losing combat.

        Loses 30% of each cargo type (min 1 per type), sets hull to 25%
        of max, shields to 0, and moves player to a safe system.
        Credits are not affected.

        Args:
            safe_system_id: System to retreat to.
        """
        from spacegame.config import (
            COMBAT_DEFEAT_CARGO_LOSS_PERCENT,
            COMBAT_DEFEAT_HULL_REMAINING_PERCENT,
        )

        # Lose cargo
        for commodity_id, quantity in list(self.ship.current_cargo.items()):
            loss = max(1, int(quantity * COMBAT_DEFEAT_CARGO_LOSS_PERCENT / 100))
            self.ship.remove_cargo(commodity_id, loss)

        # Set hull to 25% of max
        max_hull = self.ship.ship_type.combat_hull
        self.ship.current_hull = max(1, int(max_hull * COMBAT_DEFEAT_HULL_REMAINING_PERCENT / 100))

        # Shields to 0
        self.ship.current_shields = 0

        # Move to safe system
        self.current_system_id = safe_system_id

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
            "ground_missions_completed": self.ground_missions_completed,
            "ground_missions_failed": self.ground_missions_failed,
            "ground_enemies_defeated": self.ground_enemies_defeated,
            "ground_enemies_talked": self.ground_enemies_talked,
            "ground_tiles_explored": self.ground_tiles_explored,
            "ground_undetected_completions": self.ground_undetected_completions,
            "criminal_heat": self.criminal_heat,
            "goods_smuggled": self.goods_smuggled,
            "smuggling_contracts_completed": self.smuggling_contracts_completed,
            "times_caught_smuggling": self.times_caught_smuggling,
        }

    def add_criminal_heat(self, amount: int) -> None:
        """Add criminal heat, capped at 100.

        Args:
            amount: Heat points to add.
        """
        self.criminal_heat = min(100, self.criminal_heat + amount)
        if self.criminal_heat > self.max_criminal_heat_reached:
            self.max_criminal_heat_reached = self.criminal_heat

    def decay_criminal_heat(self, amount: int) -> None:
        """Decay criminal heat, floored at 0.

        Args:
            amount: Heat points to remove.
        """
        self.criminal_heat = max(0, self.criminal_heat - amount)

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

    def has_black_market_access(self, system_id: str) -> bool:
        """Check if player has black market access for a system.

        Args:
            system_id: System to check.

        Returns:
            True if player has earned access to this system's black market.
        """
        return system_id in self.black_market_access

    def grant_black_market_access(self, system_id: str) -> None:
        """Grant black market access for a system.

        Args:
            system_id: System to grant access for.
        """
        self.black_market_access.add(system_id)

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
