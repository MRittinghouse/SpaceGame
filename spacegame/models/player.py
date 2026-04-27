"""
Player state and progression models.

Tracks player credits, location, ship, and game progress.
"""

from dataclasses import dataclass, field
from typing import Optional

from spacegame.models.captain_memory import CaptainMemory
from spacegame.models.deep_core import DeepCoreUpgradeState
from spacegame.models.deep_shafts import DeepShaftsState
from spacegame.models.drone import MiningDroneFleet
from spacegame.models.faction import ReputationTier, get_reputation_tier
from spacegame.models.forge_buffer import ForgeBufferManager
from spacegame.models.forge_upgrade import ForgeUpgradeState
from spacegame.models.ore_silo import OreSiloManager
from spacegame.models.player_identity import (
    get_all_titles,
    get_playstyle,
    get_playstyle_label,
    get_primary_title,
)
from spacegame.models.progression import PlayerProgression
from spacegame.models.recipe_mastery import RecipeMasteryTracker
from spacegame.models.salvage_hold import SalvageHoldManager
from spacegame.models.ship import Ship, ShipType
from spacegame.models.sub_reputation import (
    OrganizationConfig,
    OrganizationTier,
    SubReputationDelta,
    get_tier_for_rep,
    is_at_least,
)
from spacegame.models.timed_thread import TimedThreadState
from spacegame.models.trade_route import PriceMemory, TradeRouteTracker
from spacegame.models.upgrades import ShipUpgradeManager
from spacegame.models.wreck_upgrade import WreckUpgradeState
from spacegame.models.wreckers_guild import WreckersGuildState


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
    ship_name: str = ""  # Player-chosen ship name (empty = use ship type name)
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

    # Sub-reputation system (SA-B-EXT-1): per-organization standing layered
    # under faction reputation.  Keyed by organization ID (e.g. "wreckers_guild").
    # Notification queue lives on _pending_sub_rep_deltas (non-serialized).
    sub_reputation: dict[str, int] = field(default_factory=dict)

    # SA-1: Wreckers' Guild Hall runtime state. None for unenrolled players;
    # the first conversation with Malia at the Hall flips it on. The
    # standing value lives separately on ``sub_reputation["wreckers_guild"]``
    # per the SA-B-EXT-1 contract — *enrolled* and *standing* are
    # intentionally orthogonal.
    wreckers_guild_state: Optional[WreckersGuildState] = None

    # SA-2: Deep Shafts memorial pilgrimage state. None until the player
    # first enters the venue. Faction-rep value lives separately on
    # ``faction_reputation["miners_union"]`` via the existing API; this
    # state tracks the cap and cooldown bookkeeping.
    deep_shafts_state: Optional[DeepShaftsState] = None

    # Dialogue system
    dialogue_flags: dict[str, bool] = field(default_factory=dict)

    # RC: per-captain memory (encounter count, last outcome, resolution
    # status). Persists across saves so recurring captains can remember
    # the player and rivalries can resolve into terminal states. Empty
    # dict = no captains met yet. See ``models/captain_memory.py``.
    captain_memory: dict[str, "CaptainMemory"] = field(default_factory=dict)

    # TW: per-thread runtime state (last touched day + entered drift
    # states). Keyed by thread_id. Empty = no thread has had its clock
    # started. See ``models/timed_thread.py``.
    timed_thread_state: dict[str, "TimedThreadState"] = field(default_factory=dict)
    # TW (QA-F-1 fix): most-recent game_day each interaction key was
    # recorded. Powers touch semantics for TimedThreads — both one-time
    # and recurring. Populated via record_interaction() at action
    # points (dialogue end, mission accept). The evaluator consults
    # this instead of sniffing dialogue_flags so touches can be
    # distinguished from "flag set long ago and still True".
    last_interaction_day: dict[str, int] = field(default_factory=dict)

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

    # Ship parts inventory (part_id -> count owned but not equipped)
    parts_inventory: dict[str, int] = field(default_factory=dict)

    # Smuggling contract manager state
    smuggling_contract_state: dict = field(default_factory=dict)

    # Ground contract manager state
    ground_contract_state: dict = field(default_factory=dict)

    # Political system state
    political_state: dict = field(default_factory=dict)

    # SA-P2 venue dispute system state. Distinct keyspace from
    # ``political_state`` so the two managers serialize independently
    # (per SA-P1 §11 decision 1: coexist, not merge).
    politics_dispute_state: dict = field(default_factory=dict)

    # Trade route tracking
    trade_route_tracker: TradeRouteTracker = field(default_factory=TradeRouteTracker)
    # Per-system price snapshots — gated behind the ``price_memory`` skill
    # (QA Pass 5 Tier 3.F). Recorded on system arrival; displayed on the
    # galaxy map.
    price_memory: PriceMemory = field(default_factory=PriceMemory)
    previous_system_id: str = ""

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
    combats_negotiated: int = 0
    combats_bribed: int = 0

    # Mission statistics
    side_missions_completed: int = 0
    crew_quests_completed: int = 0
    encounters_survived: int = 0

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

    # Personal records (high-water marks)
    best_mining_session_ore: int = 0
    best_mining_depth: int = 0  # Distinct from max_mining_depth (session vs career)
    best_trade_profit: int = 0  # Single transaction
    best_salvage_haul: int = 0  # Single session
    best_refining_output: int = 0  # Single session
    max_credits_held: int = 0

    # Deep Core mining progression
    strata_tokens: int = 0
    mining_prestige_level: int = 0
    deep_core_upgrades: DeepCoreUpgradeState = field(default_factory=DeepCoreUpgradeState)
    ore_silo_manager: OreSiloManager = field(default_factory=OreSiloManager)
    mining_depth_per_system: dict[str, int] = field(default_factory=dict)
    prestige_hint_shown: bool = False

    # Deep Salvage progression
    salvage_intel: int = 0
    salvage_prestige_level: int = 0
    wreck_upgrades: WreckUpgradeState = field(default_factory=WreckUpgradeState)
    salvage_hold_manager: SalvageHoldManager = field(default_factory=SalvageHoldManager)
    max_salvage_deck: int = 0

    # Forge (Catalyst Protocol) progression
    forge_tokens: int = 0
    forge_upgrades: ForgeUpgradeState = field(default_factory=ForgeUpgradeState)
    forge_buffer_manager: ForgeBufferManager = field(default_factory=ForgeBufferManager)
    recipe_mastery: RecipeMasteryTracker = field(default_factory=RecipeMasteryTracker)
    discovered_recipes: set[str] = field(default_factory=set)
    discovered_combos: set[str] = field(default_factory=set)
    # Ship builder (Shipyard Overhaul Phase A3)
    unlocked_shapes: set[str] = field(
        default_factory=lambda: {
            "pixel",
            "small_bar",
            "bar",
            "long_bar",
            "small_square",
            "small_rect",
            "small_triangle",
            "medium_triangle",
            "nose_point",
        }
    )
    unlocked_materials: set[str] = field(
        default_factory=lambda: {
            "light_alloy",
            "standard_plate",
            "salvage_scrap",
        }
    )
    unlocked_weight_classes: set[str] = field(default_factory=lambda: {"tiny"})
    unlocked_modules: set[str] = field(
        default_factory=lambda: {
            "scout_pod_rk",
            "salvage_cockpit_sr",
            "light_thruster_rk",
            "micro_thruster_rk",
            "salvage_engine_sr",
            "light_hardpoint_rk",
            "salvage_gun_sr",
            "basic_emitter_rk",
            "salvage_shield_sr",
            "small_hold_rk",
            "bunk_room_rk",
            "salvage_bunk_sr",
            "small_fuel_tank_rk",
            "life_support_rk",
            "hull_connector_2x2",
            "hull_beam_6x2",
            "small_rect_3x2",
            "medium_rect_4x3",
            "small_square_3x3",
            "l_shape_3x3",
            "plus_shape_3x3",
            "nose_point_3x3",
            "tail_fin_3x4",
            "connector_2x3",
        }
    )
    player_presets: list[dict] = field(default_factory=list)
    build_drafts: list[dict] = field(default_factory=list)  # Saved ship drafts (max 20)
    trade_profit_total: int = 0

    def __post_init__(self) -> None:
        """Initialize visited systems with starting location."""
        self.systems_visited.add(self.current_system_id)
        # Link upgrade manager to ship for bonus calculations
        self.ship.set_upgrade_manager(self.upgrade_manager)
        # Link progression to ship for skill bonus calculations
        self.ship.set_progression(self.progression)
        # Link progression to hidden compartment for contraband_slots bonus
        if self.hidden_compartment:
            self.hidden_compartment.set_progression(self.progression)

    def can_afford(self, cost: int) -> bool:
        """
        Check if player can afford a purchase.

        Args:
            cost: Amount in credits

        Returns:
            True if player has enough credits
        """
        return self.credits >= cost

    # ------------------------------------------------------------------
    # Parts inventory management
    # ------------------------------------------------------------------

    def add_part(self, part_id: str, count: int = 1) -> None:
        """Add ship parts to inventory.

        Args:
            part_id: The ShipPart ID.
            count: Number to add (default 1).
        """
        self.parts_inventory[part_id] = self.parts_inventory.get(part_id, 0) + count

    def remove_part(self, part_id: str, count: int = 1) -> tuple[bool, str]:
        """Remove ship parts from inventory.

        Args:
            part_id: The ShipPart ID.
            count: Number to remove.

        Returns:
            (success, message) tuple.
        """
        current = self.parts_inventory.get(part_id, 0)
        if current < count:
            return False, f"Not enough {part_id} in inventory ({current} < {count})"
        self.parts_inventory[part_id] = current - count
        if self.parts_inventory[part_id] == 0:
            del self.parts_inventory[part_id]
        return True, f"Removed {count}x {part_id}"

    def get_part_count(self, part_id: str) -> int:
        """Get count of a specific part in inventory."""
        return self.parts_inventory.get(part_id, 0)

    # ------------------------------------------------------------------
    # Credit management
    # ------------------------------------------------------------------

    def add_credits(self, amount: int) -> None:
        """
        Add credits to player's account.

        Args:
            amount: Credits to add
        """
        self.credits += amount
        if self.credits > self.max_credits_held:
            self.max_credits_held = self.credits

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
                f"Insufficient credits. Repair costs {total_cost:,} CR, have {self.credits:,} CR.",
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
                f"Cannot afford. Need {net_cost:,} CR after trade-in, have {self.credits:,} CR.",
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
        new_ship.set_progression(self.progression)

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

        Consequences: cargo loss, credit loss, hull/shield damage,
        fuel reduction, faction reputation hit, and retreat to safety.
        Painful but not permadeath — the player keeps their ship and parts.

        Args:
            safe_system_id: System to retreat to.
        """
        from spacegame.config import (
            COMBAT_DEFEAT_CARGO_LOSS_PERCENT,
            COMBAT_DEFEAT_CREDIT_LOSS_PERCENT,
            COMBAT_DEFEAT_FUEL_REMAINING,
            COMBAT_DEFEAT_HULL_REMAINING_PERCENT,
            COMBAT_DEFEAT_REPUTATION_PENALTY,
        )

        # Lose cargo (30% of each type, halved with insurance skill)
        has_insurance = self.progression.get_bonus("insurance") > 0
        cargo_loss_pct = COMBAT_DEFEAT_CARGO_LOSS_PERCENT
        if has_insurance:
            cargo_loss_pct = cargo_loss_pct / 2  # Keep 50% more cargo
        for commodity_id, quantity in list(self.ship.current_cargo.items()):
            loss = max(1, int(quantity * cargo_loss_pct / 100))
            self.ship.remove_cargo(commodity_id, loss)

        # Lose credits (10% — repair and salvage costs)
        credit_loss = int(self.credits * COMBAT_DEFEAT_CREDIT_LOSS_PERCENT / 100)
        if credit_loss > 0:
            self.credits -= credit_loss

        # Set hull to 25% of max
        max_hull = self.ship.ship_type.combat_hull
        self.ship.current_hull = max(1, int(max_hull * COMBAT_DEFEAT_HULL_REMAINING_PERCENT / 100))

        # Shields to 0
        self.ship.current_shields = 0

        # Fuel reduced (enough for 1 short jump)
        self.ship.current_fuel = min(self.ship.current_fuel, COMBAT_DEFEAT_FUEL_REMAINING)

        # Reputation hit with local faction (you needed rescuing)
        faction_id = self.get_faction_for_system(safe_system_id)
        if faction_id and COMBAT_DEFEAT_REPUTATION_PENALTY > 0:
            self.modify_reputation(faction_id, -COMBAT_DEFEAT_REPUTATION_PENALTY)

        # Move to safe system
        self.current_system_id = safe_system_id

    def get_net_worth(self) -> int:
        """
        Calculate player's total net worth.

        Returns:
            Total net worth (credits + ship value + cargo value estimate)
        """
        # Credits + ship resale value. Cargo value excluded because market
        # prices are system-dependent and would require a system context parameter.
        return self.credits + self.ship.ship_type.resale_value

    @property
    def display_ship_name(self) -> str:
        """Get the display name for the player's ship."""
        return self.ship_name if self.ship_name else self.ship.name

    def _identity_stats(self) -> dict[str, int]:
        """Get stats used for identity calculations."""
        return {
            "ore_mined": self.ore_mined,
            "trades_completed": self.trades_completed,
            "combats_won": self.combats_won,
            "items_salvaged": self.items_salvaged,
            "items_refined": self.items_refined,
            "systems_visited": len(self.systems_visited),
        }

    @property
    def title(self) -> str:
        """Get the player's primary reputation title."""
        return get_primary_title(**self._identity_stats())

    @property
    def all_titles(self) -> dict[str, str]:
        """Get all earned titles by domain."""
        return get_all_titles(**self._identity_stats())

    @property
    def playstyle(self) -> str:
        """Get the player's dominant playstyle key."""
        return get_playstyle(**self._identity_stats())

    @property
    def playstyle_label(self) -> str:
        """Get the player's playstyle as a human-readable label."""
        return get_playstyle_label(**self._identity_stats())

    # ------------------------------------------------------------------
    # RC: captain memory helpers
    # ------------------------------------------------------------------

    def get_captain_memory(self, captain_id: str) -> CaptainMemory:
        """Get the player's memory for a captain, creating it if absent.

        Returns a ``CaptainMemory`` with default state for never-met
        captains. Mutating the returned object updates the player's
        records in place.
        """
        if captain_id not in self.captain_memory:
            self.captain_memory[captain_id] = CaptainMemory(captain_id=captain_id)
        return self.captain_memory[captain_id]

    def record_interaction(self, key: str, game_day: Optional[int] = None) -> None:
        """TW: mark an interaction-key as happening on the given day.

        Used by the TimedThread evaluator to reset drift clocks on
        threads that watch this key. Callers invoke this at action
        points — dialogue end, mission accept, etc. — so touches are
        distinguishable from flags that merely stay True over time.

        Args:
            key: Interaction identifier — frequently a flag built via the
                helpers in ``spacegame.constants.flags`` (e.g.
                ``talked_to_npc("marcus_jin")``), or a free-form mission
                interaction key (e.g. ``"the_scholars_errand_accepted"``,
                ``"any_mission_accepted"``).
            game_day: Day the interaction happened. Defaults to
                ``self.game_day``.
        """
        day = game_day if game_day is not None else self.game_day
        self.last_interaction_day[key] = day

    def record_captain_encounter(self, captain_id: str, outcome: str) -> CaptainMemory:
        """Record a meeting with a captain and apply resolution rules.

        Increments encounter_count, sets last_outcome, updates day stamps,
        and transitions status if the outcome triggers resolution. Returns
        the (possibly newly-created) memory for the caller to inspect.

        Args:
            captain_id: The captain's id.
            outcome: One of ``OUTCOME_*`` strings from captain_memory.
        """
        mem = self.get_captain_memory(captain_id)
        mem.record_encounter(outcome, self.game_day)
        return mem

    def make_news_context(
        self, detail: str = "", commodity: str = "", amount: str = ""
    ) -> dict[str, str]:
        """Create a context dict for player action news templates.

        Args:
            detail: Action-specific detail (e.g., mining depth, recipe name).
            commodity: Commodity involved.
            amount: Amount or value string.

        Returns:
            Dict suitable for news ticker player_action context.
        """
        return {
            "player_name": self.name,
            "ship_name": self.display_ship_name,
            "system": self.current_system_id,
            "detail": detail,
            "commodity": commodity,
            "amount": amount,
        }

    def get_statistics(self) -> dict[str, any]:
        """
        Get player statistics for display.

        Returns:
            Dict of statistics
        """
        return {
            "name": self.name,
            "title": self.title,
            "playstyle": self.playstyle_label,
            "credits": self.credits,
            "day": self.game_day,
            "ship": self.display_ship_name,
            "ship_name": self.ship_name,
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
            # Personal records
            "best_mining_session_ore": self.best_mining_session_ore,
            "best_mining_depth": self.best_mining_depth,
            "best_trade_profit": self.best_trade_profit,
            "best_salvage_haul": self.best_salvage_haul,
            "best_refining_output": self.best_refining_output,
            "max_credits_held": self.max_credits_held,
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

        Also sets the ``black_market_access`` dialogue flag so narrative
        content (encounters, dialogues) can gate on "has the player made
        black-market contacts anywhere" without walking the per-system set.

        Args:
            system_id: System to grant access for.
        """
        self.black_market_access.add(system_id)
        self.dialogue_flags["black_market_access"] = True

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
        # Compute the effective delta (honors clamping). PT-K: surface faction
        # standing shifts to the player via a notification. Store as plain
        # attribute so it's not serialized — the list is ephemeral UI state
        # drained each frame by the game loop.
        effective_delta = new_rep - current
        self.faction_reputation[faction_id] = new_rep
        if effective_delta != 0:
            if not hasattr(self, "_pending_faction_deltas"):
                self._pending_faction_deltas: list[tuple[str, int]] = []
            self._pending_faction_deltas.append((faction_id, effective_delta))
        sign = "+" if amount >= 0 else ""
        return (True, f"{sign}{amount} reputation with {faction_id}")

    def get_reputation(self, faction_id: str) -> int:
        """Get current reputation value with a faction.

        Args:
            faction_id: Faction to check.

        Returns:
            Reputation value (-100 to +100), defaults to 0.
        """
        base = self.faction_reputation.get(faction_id, 0)
        # Exploration skill: frontier_rep_bonus adds starting rep with Frontier Alliance
        if faction_id == "frontier_alliance":
            bonus = int(self.progression.get_bonus("frontier_rep_bonus"))
            base = min(100, base + bonus)
        return base

    def get_reputation_tier(self, faction_id: str) -> ReputationTier:
        """Get the reputation tier with a faction.

        Args:
            faction_id: Faction to check.

        Returns:
            The ReputationTier enum value.
        """
        return get_reputation_tier(self.get_reputation(faction_id))

    # ------------------------------------------------------------------
    # Sub-reputation helpers (SA-B-EXT-1)
    # ------------------------------------------------------------------

    def modify_sub_reputation(
        self, org_id: str, amount: int, config: OrganizationConfig
    ) -> tuple[bool, str]:
        """Modify sub-reputation with an organization, clamped to config range.

        Queues a SubReputationDelta on _pending_sub_rep_deltas when the
        modification crosses a tier threshold.  The queue is ephemeral
        (not serialized) and should be drained each frame by consumer views.

        Args:
            org_id: Organization identifier.
            amount: Amount to add (positive or negative).
            config: OrganizationConfig defining range and tiers.

        Returns:
            Tuple of (success, message).
        """
        current = self.sub_reputation.get(org_id, 0)
        old_tier = get_tier_for_rep(config, current)
        new_val = max(config.min_rep, min(config.max_rep, current + amount))
        effective_delta = new_val - current
        self.sub_reputation[org_id] = new_val
        new_tier = get_tier_for_rep(config, new_val)
        if new_tier != old_tier:
            if not hasattr(self, "_pending_sub_rep_deltas"):
                self._pending_sub_rep_deltas: list[SubReputationDelta] = []
            self._pending_sub_rep_deltas.append(
                SubReputationDelta(
                    org_id=org_id,
                    effective_amount=effective_delta,
                    old_tier=old_tier,
                    new_tier=new_tier,
                )
            )
        sign = "+" if amount >= 0 else ""
        return (True, f"{sign}{amount} standing with {org_id}")

    def get_sub_reputation(self, org_id: str) -> int:
        """Get current sub-reputation with an organization.

        Args:
            org_id: Organization identifier.

        Returns:
            Current value, or 0 if the organization is not yet tracked.
        """
        return self.sub_reputation.get(org_id, 0)

    def get_sub_reputation_tier(self, org_id: str, config: OrganizationConfig) -> OrganizationTier:
        """Get the current tier with an organization.

        Returns the lowest tier when the organization is absent from
        sub_reputation (defaults to 0 rep, so the lowest-ranked tier).

        Args:
            org_id: Organization identifier.
            config: OrganizationConfig defining the tier thresholds.

        Returns:
            The matching OrganizationTier.
        """
        value = self.sub_reputation.get(org_id, 0)
        return get_tier_for_rep(config, value)

    def is_at_least_tier(self, org_id: str, tier_id: str, config: OrganizationConfig) -> bool:
        """Check whether the player meets or exceeds a given tier.

        Returns False (not raises) when tier_id is unknown to the config.

        Args:
            org_id: Organization identifier.
            tier_id: Target tier ID to test against.
            config: OrganizationConfig to use for resolution.

        Returns:
            True if current tier rank >= target tier rank.
        """
        value = self.sub_reputation.get(org_id, 0)
        return is_at_least(config, value, tier_id)

    def add_strata_tokens(self, amount: int) -> None:
        """Add strata tokens to player balance.

        Args:
            amount: Tokens to add.
        """
        self.strata_tokens += amount

    def spend_strata_tokens(self, amount: int) -> bool:
        """Spend strata tokens if sufficient balance.

        Args:
            amount: Tokens to spend.

        Returns:
            True if successful, False if insufficient.
        """
        if self.strata_tokens < amount:
            return False
        self.strata_tokens -= amount
        return True

    def add_salvage_intel(self, amount: int) -> None:
        """Add salvage intel to player balance.

        Args:
            amount: Intel to add.
        """
        self.salvage_intel += amount

    def spend_salvage_intel(self, amount: int) -> bool:
        """Spend salvage intel if sufficient balance.

        Args:
            amount: Intel to spend.

        Returns:
            True if successful, False if insufficient.
        """
        if self.salvage_intel < amount:
            return False
        self.salvage_intel -= amount
        return True

    def add_forge_tokens(self, amount: int) -> None:
        """Add forge tokens to player balance.

        Args:
            amount: Tokens to add.
        """
        self.forge_tokens += amount

    def spend_forge_tokens(self, amount: int) -> bool:
        """Spend forge tokens if sufficient balance.

        Args:
            amount: Tokens to spend.

        Returns:
            True if successful, False if insufficient.
        """
        if self.forge_tokens < amount:
            return False
        self.forge_tokens -= amount
        return True

    def discover_recipe(self, recipe_id: str) -> None:
        """Mark a recipe as discovered.

        Args:
            recipe_id: ID of the recipe to discover.
        """
        self.discovered_recipes.add(recipe_id)

    def is_recipe_discovered(self, recipe_id: str) -> bool:
        """Check if a recipe has been discovered.

        Args:
            recipe_id: ID of the recipe to check.

        Returns:
            True if discovered.
        """
        return recipe_id in self.discovered_recipes

    def initialize_discovered_recipes(self, recipes: list) -> None:
        """Populate discovered_recipes with all non-discoverable recipes.

        Called on new game or when loading a save that has no discoveries yet.

        Args:
            recipes: All recipes from DataLoader.
        """
        for recipe in recipes:
            if not recipe.discoverable:
                self.discovered_recipes.add(recipe.id)
