"""
Ship and fleet models.

Defines ship types, their capabilities, and player ship instances.
"""

from dataclasses import dataclass, field
from typing import Dict, List


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
    # Ship class category for momentum ultimates
    ship_class_category: str = ""
    # Defensive identity (Phase 12A)
    defensive_identity: str = ""  # "juggernaut", "sentinel", "ghost", or ""
    combat_armor: int = 0
    combat_shield_regen: int = 0
    # Combat stats (default 0 for backward compat)
    combat_hull: int = 0
    combat_shields: int = 0
    combat_energy: int = 0
    combat_energy_regen: int = 0
    combat_speed: int = 0
    combat_evasion: int = 0
    combat_accuracy: int = 0
    weapon_slots: int = 0
    defense_slots: int = 0
    utility_slots: int = 3
    # Per-frame slot requirements (min/max/min_size per slot type)
    frame_requirements: dict[str, dict[str, int | str]] = field(default_factory=dict)
    # Faction/quest gating (optional)
    faction_required: str | None = None
    faction_rep_required: int = 0
    unlock_condition: str | None = None

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
    current_hull: int = 0
    current_shields: int = 0

    def __post_init__(self) -> None:
        """Initialize ship with full fuel and combat stats if not specified."""
        # Optional references to bonus sources (set by Player/Game after init)
        if not hasattr(self, "_upgrade_manager"):
            self._upgrade_manager = None
        if not hasattr(self, "_crew_roster"):
            self._crew_roster = None
        if not hasattr(self, "_progression"):
            self._progression = None
        # Ship builder references (Phase A2)
        if not hasattr(self, "_build"):
            self._build = None
        if not hasattr(self, "_computed_stats"):
            self._computed_stats = None
        if self.current_fuel == 0:
            self.current_fuel = self.ship_type.fuel_capacity
        # Auto-init hull/shields from ship type if not explicitly set
        if self.current_hull == 0 and self.ship_type.combat_hull > 0:
            self.current_hull = self.ship_type.combat_hull
        if self.current_shields == 0 and self.ship_type.combat_shields > 0:
            self.current_shields = self.ship_type.combat_shields

    def set_upgrade_manager(self, manager) -> None:
        """Link an upgrade manager for bonus calculations."""
        self._upgrade_manager = manager

    def set_crew_roster(self, roster) -> None:
        """Link a crew roster for bonus calculations."""
        self._crew_roster = roster

    def set_progression(self, progression) -> None:
        """Link a progression for skill bonus calculations."""
        self._progression = progression

    def get_crew_bonus(self, bonus_type: str) -> float:
        """Get a crew bonus by type, or 0.0 if no crew roster linked."""
        if self._crew_roster:
            return self._crew_roster.get_bonus(bonus_type)
        return 0.0

    def set_build(self, build: "ShipBuild", full_heal: bool = False) -> None:
        """Attach a ShipBuild and recompute stats.

        Args:
            build: The ship build configuration.
            full_heal: If True, set hull/shields to the new computed max.
                       Used for new game and builder confirm, not save/load.
        """
        self._build = build
        self._recompute_stats()
        if full_heal and self._computed_stats:
            self.current_hull = self._computed_stats.hull
            self.current_shields = self._computed_stats.shields

    def _recompute_stats(self) -> None:
        """Derive ComputedShipStats from the build. Called when build changes."""
        if self._build:
            from spacegame.data_loader import get_data_loader
            from spacegame.models.ship_build import ShipStatsComputer

            dl = get_data_loader()
            materials = getattr(dl, "hull_materials", {})
            equipment = getattr(dl, "upgrades", {})
            module_catalog = getattr(dl, "ship_modules", {})
            slot_defs = getattr(dl, "slot_definitions", {})
            parts_catalog = getattr(dl, "ship_parts", {})
            self._computed_stats = ShipStatsComputer.compute(
                self._build,
                materials,
                equipment,
                module_catalog=module_catalog,
                slot_definitions=slot_defs,
                parts_catalog=parts_catalog,
                ship_type=self.ship_type,
            )
            # Create or update the composite renderer.
            # Uses the rebuilt 7-phase pipeline per
            # requirements/overhaul/94_ship_composite_api.md. The constructor
            # takes only the build — materials and module catalog are
            # resolved internally via the data loader.
            try:
                from spacegame.engine.ship_composite import ShipComposite

                if not hasattr(self, "_composite") or self._composite is None:
                    self._composite = ShipComposite(self._build)
                else:
                    self._composite.invalidate()
            except ImportError:
                pass  # Composite not available in test environments

    @property
    def build(self) -> "Optional[ShipBuild]":
        """The ship's build configuration, if set."""
        return self._build

    @property
    def computed_stats(self) -> "Optional[ComputedShipStats]":
        """Computed stats from the build, if available."""
        return self._computed_stats

    @property
    def composite(self) -> "Optional[object]":
        """Ship composite renderer (set by view layer)."""
        return getattr(self, "_composite", None)

    def has_module_in_slot(self, equipment_id: str) -> bool:
        """Check if any slot has the given equipment installed.

        Works with ShipBuild slots. Falls back to upgrade_manager
        for ships without a build.

        Args:
            equipment_id: The equipment/upgrade ID to check for.

        Returns:
            True if the equipment is installed in any slot.
        """
        if self._build:
            return any(ps.equipped_part_id == equipment_id for ps in self._build.placed_slots)
        # Fallback: check upgrade manager
        if self._upgrade_manager:
            return self._upgrade_manager.has_upgrade(equipment_id)
        return False

    def has_module_type_in_slot(self, slot_type: str) -> bool:
        """Check if a slot of the given type has equipment installed.

        Args:
            slot_type: Slot type ("weapon", "defense", "engine", "utility", "core").

        Returns:
            True if any slot of this type has equipment.
        """
        if self._build:
            # Need slot definitions to map slot_def_id -> slot_type
            try:
                from spacegame.data_loader import get_data_loader

                slot_defs = getattr(get_data_loader(), "slot_definitions", {})
                return any(
                    slot_defs.get(ps.slot_def_id) is not None
                    and slot_defs[ps.slot_def_id].slot_type == slot_type
                    and ps.equipped_part_id is not None
                    for ps in self._build.placed_slots
                )
            except Exception:
                pass
        return False

    @property
    def display_ship_name(self) -> str:
        """Display name: preset name if available, else ship type name."""
        if self._build and self._build.preset_name:
            return self._build.preset_name
        return self.ship_type.name

    @property
    def name(self) -> str:
        """Get ship type name."""
        return self.ship_type.name

    @property
    def max_cargo(self) -> int:
        """Get maximum cargo capacity including upgrade and crew bonuses.

        Falls back to ShipType base cargo if computed cargo is 0.
        """
        if self._computed_stats and self._computed_stats.cargo_capacity > 0:
            base = self._computed_stats.cargo_capacity
        else:
            base = self.ship_type.cargo_capacity
            if self._upgrade_manager:
                base += int(self._upgrade_manager.get_bonus("cargo_bonus"))
        if self._crew_roster:
            base += int(self._crew_roster.get_bonus("cargo_bonus"))
        # Commerce skill: cargo_capacity_bonus is a percentage increase
        if self._progression:
            cargo_pct = self._progression.get_bonus("cargo_capacity_bonus")
            if cargo_pct > 0:
                base = int(base * (1.0 + cargo_pct))
        return base

    @property
    def max_fuel(self) -> int:
        """Get maximum fuel capacity including upgrade and crew bonuses.

        Uses computed stats from the ship build if available. Falls back
        to ShipType base fuel if computed fuel is 0 (e.g. preset builds
        without fuel tank modules). Guarantees a minimum of 10 fuel so
        the player can always travel at least one hop.
        """
        if self._computed_stats and self._computed_stats.fuel_capacity > 0:
            base = self._computed_stats.fuel_capacity
        else:
            base = self.ship_type.fuel_capacity
            if self._upgrade_manager:
                base += int(self._upgrade_manager.get_bonus("fuel_bonus"))
        if self._crew_roster:
            base += int(self._crew_roster.get_bonus("fuel_bonus"))
        return max(base, 10)

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

    def repair_hull(self, amount: int) -> int:
        """Repair hull damage, capped at max hull.

        Args:
            amount: Hull points to repair.

        Returns:
            Actual amount repaired.
        """
        if self._computed_stats and self._computed_stats.hull > 0:
            max_hull = self._computed_stats.hull
        else:
            max_hull = self.ship_type.combat_hull
        space = max_hull - self.current_hull
        actual = min(amount, space)
        self.current_hull += actual
        return actual

    def restore_shields(self) -> None:
        """Restore shields to maximum (e.g., on docking)."""
        if self._computed_stats and self._computed_stats.shields > 0:
            self.current_shields = self._computed_stats.shields
        else:
            self.current_shields = self.ship_type.combat_shields

    def get_fuel_percentage(self) -> float:
        """
        Get fuel level as percentage.

        Returns:
            Fuel percentage (0.0 to 1.0)
        """
        return self.current_fuel / self.max_fuel if self.max_fuel > 0 else 0.0
