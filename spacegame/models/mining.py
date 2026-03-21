"""
Mining system models.

Asteroid field mini-game with click-to-mine, passive drilling,
drone automation, and skill-driven progression.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from spacegame.models.drone import MiningDrone


class RockType(Enum):
    """Types of minable rocks with different properties."""

    COMMON = "common"
    IRON = "iron"
    CRYSTAL = "crystal"
    RARE = "rare"
    DENSE = "dense"
    VOLATILE = "volatile"
    MONOLITH = "monolith"


class HazardType(Enum):
    """Types of environmental hazards in the mining field."""

    UNSTABLE_CELL = "unstable_cell"
    PRESSURE_VENT = "pressure_vent"


@dataclass
class HazardCell:
    """An environmental hazard occupying a grid cell."""

    hazard_type: HazardType
    grid_x: int
    grid_y: int
    pulse_timer: float = 0.0  # Used by pressure vents


# Hazard depth thresholds
HAZARD_UNSTABLE_DEPTH = 10
HAZARD_VENT_DEPTH = 15
UNSTABLE_ENERGY_COST = 3
UNSTABLE_PROGRESS_AMOUNT = 0.30
VENT_PULSE_INTERVAL = 8.0
VENT_PROGRESS_AMOUNT = 0.10


@dataclass
class RockTypeConfig:
    """Configuration for a rock type."""

    rock_type: RockType
    hardness: float  # Drill time in seconds
    min_yield: int
    max_yield: int
    commodity_id: str  # What commodity this yields
    color: tuple  # RGB color for rendering
    chain_immune: bool = False  # If True, cannot be chain-detonated
    volatile_splash: bool = False  # If True, applies 50% progress to neighbors on break
    drone_immune: bool = False  # If True, drones cannot target this rock


# Default rock type configurations
ROCK_TYPE_CONFIGS = {
    RockType.COMMON: RockTypeConfig(
        rock_type=RockType.COMMON,
        hardness=0.5,
        min_yield=2,
        max_yield=4,
        commodity_id="raw_ore",
        color=(120, 110, 100),
    ),
    RockType.IRON: RockTypeConfig(
        rock_type=RockType.IRON,
        hardness=1.0,
        min_yield=1,
        max_yield=4,
        commodity_id="iron_ore",
        color=(160, 80, 60),
    ),
    RockType.CRYSTAL: RockTypeConfig(
        rock_type=RockType.CRYSTAL,
        hardness=2.0,
        min_yield=1,
        max_yield=3,
        commodity_id="crystal_ore",
        color=(100, 180, 220),
    ),
    RockType.RARE: RockTypeConfig(
        rock_type=RockType.RARE,
        hardness=3.0,
        min_yield=1,
        max_yield=3,
        commodity_id="rare_ore",
        color=(200, 100, 255),
    ),
    RockType.DENSE: RockTypeConfig(
        rock_type=RockType.DENSE,
        hardness=4.0,
        min_yield=3,
        max_yield=6,
        commodity_id="iron_ore",
        color=(90, 70, 50),
        chain_immune=True,
    ),
    RockType.VOLATILE: RockTypeConfig(
        rock_type=RockType.VOLATILE,
        hardness=1.5,
        min_yield=2,
        max_yield=4,
        commodity_id="raw_ore",
        color=(255, 120, 40),
        volatile_splash=True,
    ),
    RockType.MONOLITH: RockTypeConfig(
        rock_type=RockType.MONOLITH,
        hardness=10.0,  # Base; actual is 10.0 + depth * 0.5
        min_yield=5,
        max_yield=5,  # Base; actual is 5 + depth
        commodity_id="iron_ore",  # Overridden per-system
        color=(40, 40, 60),
        chain_immune=True,
        drone_immune=True,
    ),
}

# Depth thresholds for new rock types
DEPTH_ROCK_THRESHOLDS: dict[str, int] = {
    "iron": 3,
    "crystal": 6,
    "rare": 9,
    "dense": 5,
    "volatile": 12,
}

# Ore types that are removed from the base distribution and only appear via depth gating
DEPTH_GATED_ORES: set[str] = {"iron", "crystal", "rare"}


@dataclass
class AsteroidRock:
    """A single minable rock in the asteroid field."""

    rock_type: RockType
    grid_x: int
    grid_y: int
    depleted: bool = False
    drill_progress: float = 0.0  # 0.0 to 1.0
    drilling: bool = False
    # Overrides for special rocks (Monolith)
    hardness_override: Optional[float] = None
    yield_override: Optional[int] = None
    commodity_override: Optional[str] = None
    strata_reward: int = 0  # Strata tokens awarded on break (Monolith)

    @property
    def config(self) -> RockTypeConfig:
        """Get configuration for this rock type."""
        return ROCK_TYPE_CONFIGS[self.rock_type]

    @property
    def hardness(self) -> float:
        """Get drill time in seconds."""
        if self.hardness_override is not None:
            return self.hardness_override
        return self.config.hardness

    @property
    def commodity_id(self) -> str:
        """Get the commodity this rock yields."""
        if self.commodity_override is not None:
            return self.commodity_override
        return self.config.commodity_id

    def get_yield(self) -> int:
        """Get random yield amount when rock breaks."""
        if self.yield_override is not None:
            return self.yield_override
        cfg = self.config
        return random.randint(cfg.min_yield, cfg.max_yield)

    def start_drilling(self) -> bool:
        """Start drilling this rock. Returns False if already depleted."""
        if self.depleted or self.drilling:
            return False
        self.drilling = True
        self.drill_progress = 0.0
        return True

    def update_drill(self, dt: float, speed_bonus: float = 1.0) -> Optional[int]:
        """
        Update drill progress. Returns yield amount if rock breaks, None otherwise.

        Args:
            dt: Delta time in seconds
            speed_bonus: Multiplier for drill speed (skill bonus)

        Returns:
            Yield amount if rock is broken, None if still drilling
        """
        if not self.drilling or self.depleted:
            return None

        drill_rate = (1.0 / self.hardness) * speed_bonus
        self.drill_progress += drill_rate * dt

        if self.drill_progress >= 1.0:
            self.drill_progress = 1.0
            self.drilling = False
            self.depleted = True
            return self.get_yield()

        return None

    def apply_click(self, click_power: float) -> Optional[int]:
        """Apply a click to this rock.

        Adds click_power / hardness to drill_progress. Sets drilling=True
        for visual state. Returns yield if rock breaks, None otherwise.

        Args:
            click_power: Raw click power before hardness scaling.

        Returns:
            Yield amount if rock broke, None otherwise.
        """
        if self.depleted:
            return None

        self.drilling = True
        self.drill_progress += click_power / self.hardness

        if self.drill_progress >= 1.0:
            self.drill_progress = 1.0
            self.drilling = False
            self.depleted = True
            return self.get_yield()

        return None

    def cancel_drill(self) -> None:
        """Cancel current drilling operation."""
        self.drilling = False
        self.drill_progress = 0.0


@dataclass
class MiningConfig:
    """Configuration for mining at a specific system."""

    system_id: str
    grid_width: int = 6
    grid_height: int = 4
    max_energy: int = 20
    energy_regen_seconds: float = 3.0
    base_click_power: float = 0.12
    base_passive_rate: float = 0.05
    rock_distribution: Dict[str, float] = field(default_factory=dict)
    # Distribution is a dict of rock_type_name -> probability (0.0-1.0)
    danger_level: str = "safe"  # System danger level for yield scaling
    perk_yield_bonus: float = 0.0  # Faction perk yield bonus (stacks with danger)
    perk_wholesale_bonus: float = 0.0  # Faction perk wholesale sell price bonus

    def __post_init__(self):
        if not self.rock_distribution:
            self.rock_distribution = {
                "common": 0.50,
                "iron": 0.30,
                "crystal": 0.15,
                "rare": 0.05,
            }


@dataclass
class DepthModifiers:
    """Modifiers for the current mining depth level."""

    rare_weight_bonus: float
    energy_cost_multiplier: int
    yield_bonus: float


# Chain detonation constants
CHAIN_BASE_CHANCE = 0.15
CHAIN_PROGRESS_AMOUNT = 1.0
CHAIN_MAX_DEPTH = 3


@dataclass
class ChainBreak:
    """A rock broken by chain detonation."""

    grid_x: int
    grid_y: int
    rock_type: RockType
    commodity_id: str
    quantity: int
    chain_depth: int
    ingredient_drops: dict[str, int] = field(default_factory=dict)


@dataclass
class MiningMilestone:
    """A session milestone with progress tracking and rewards."""

    id: str
    description: str
    category: str  # "rocks_mined", "rare_ores", "depth_reached", "chains_triggered"
    threshold: int
    reward_xp: int = 0
    reward_credits: int = 0
    completed: bool = False


MILESTONE_POOL: list[dict] = [
    {
        "id": "rocks_10",
        "description": "Mine 10 rocks",
        "category": "rocks_mined",
        "threshold": 10,
        "reward_xp": 25,
    },
    {
        "id": "rocks_20",
        "description": "Mine 20 rocks",
        "category": "rocks_mined",
        "threshold": 20,
        "reward_xp": 50,
    },
    {
        "id": "rare_3",
        "description": "Find 3 rare ores",
        "category": "rare_ores",
        "threshold": 3,
        "reward_xp": 40,
    },
    {
        "id": "rare_5",
        "description": "Find 5 rare ores",
        "category": "rare_ores",
        "threshold": 5,
        "reward_credits": 100,
    },
    {
        "id": "depth_3",
        "description": "Reach depth 3",
        "category": "depth_reached",
        "threshold": 3,
        "reward_xp": 30,
    },
    {
        "id": "depth_5",
        "description": "Reach depth 5",
        "category": "depth_reached",
        "threshold": 5,
        "reward_xp": 60,
    },
    {
        "id": "depth_10",
        "description": "Reach depth 10",
        "category": "depth_reached",
        "threshold": 10,
        "reward_credits": 200,
    },
    {
        "id": "chains_3",
        "description": "Trigger 3 chain detonations",
        "category": "chains_triggered",
        "threshold": 3,
        "reward_xp": 35,
    },
    {
        "id": "chains_10",
        "description": "Trigger 10 chain detonations",
        "category": "chains_triggered",
        "threshold": 10,
        "reward_credits": 150,
    },
]


@dataclass
class MiningResult:
    """Result of a single mining action."""

    commodity_id: str
    quantity: int
    rock_type: RockType
    ingredient_drops: dict[str, int] = field(default_factory=dict)


@dataclass
class DepthAdvanceResult:
    """Result of advancing to the next depth level."""

    new_depth: int
    strata_earned: int
    was_full_clear: bool


class MiningSession:
    """
    Active mining session with click-to-mine, passive drilling, and drones.

    Manages the asteroid grid, player click input, passive drill progress,
    and drone auto-mining.
    """

    def __init__(
        self,
        config: MiningConfig,
        drill_speed_bonus: float = 1.0,
        click_power_bonus: float = 0.0,
        passive_drill_bonus: float = 0.0,
        drone_speed_bonus: float = 0.0,
        rare_chance_bonus: float = 0.0,
        chain_chance_bonus: float = 0.0,
        max_chain_depth_bonus: int = 0,
        starting_depth: int = 1,
        drones: Optional[list[MiningDrone]] = None,
        milestones: Optional[list[MiningMilestone]] = None,
        prestige_level: int = 0,
        auto_drill_level: int = 0,
        ore_scanner_level: int = 0,
    ):
        """
        Initialize mining session.

        Args:
            config: Mining configuration for the current system.
            drill_speed_bonus: Legacy drill speed multiplier (used by start_drill compat).
            click_power_bonus: Fractional bonus to click power (0.0 = no bonus).
            passive_drill_bonus: Fractional bonus to passive drill rate.
            drone_speed_bonus: Fractional bonus to drone mining speed.
            rare_chance_bonus: Fractional bonus to rare ore chance.
            chain_chance_bonus: Fractional bonus to chain detonation chance.
            max_chain_depth_bonus: Extra chain recursion depth (from Seismic Pulse).
            auto_drill_level: Auto-drill upgrade level (0=off, 1=8s, 2=5s, 3=3s).
            ore_scanner_level: Ore scanner upgrade level (0=off, 1-3=increasing detail).
            starting_depth: Initial depth (from Depth Scanner).
            drones: List of active MiningDrone instances.
        """
        self.config = config
        self.drill_speed_bonus = drill_speed_bonus
        self.click_power_bonus = click_power_bonus
        self.passive_drill_bonus = passive_drill_bonus
        self.drone_speed_bonus = drone_speed_bonus
        self.rare_chance_bonus = rare_chance_bonus
        self.chain_chance_bonus = chain_chance_bonus
        self.max_chain_depth: int = CHAIN_MAX_DEPTH + max_chain_depth_bonus
        self.drones: list[MiningDrone] = drones or []
        self.prestige_level: int = prestige_level
        self.auto_drill_level: int = auto_drill_level
        self.ore_scanner_level: int = ore_scanner_level
        self._auto_drill_timer: float = 0.0

        # Energy state
        self.energy: int = config.max_energy
        self.max_energy: int = config.max_energy
        self._energy_regen_timer: float = 0.0

        # Depth state
        self.depth: int = max(1, starting_depth)

        # Chain detonation state
        self.chain_results: list[ChainBreak] = []
        self.total_chains: int = 0

        # Milestone tracking
        self.rocks_broken: int = 0
        self.rare_ores_found: int = 0
        self.milestones: list[MiningMilestone] = milestones if milestones is not None else self._select_milestones()
        self.newly_completed_milestones: list[MiningMilestone] = []

        self.rocks: List[AsteroidRock] = []
        self.hazards: List[HazardCell] = []
        self.active_rock: Optional[AsteroidRock] = None
        self.total_mined: Dict[str, int] = {}  # commodity_id -> quantity
        self.total_clicks: int = 0
        self.drone_targets: Dict[int, AsteroidRock] = {}  # drone_index -> rock

        self._generate_field()

    def _get_depth_rock_distribution(self) -> Dict[str, float]:
        """Get rock distribution adjusted for current depth.

        Removes ore types below their depth threshold and adds depth-gated
        types as the player pushes deeper.
        """
        dist = dict(self.config.rock_distribution)

        # Remove depth-gated ores below their threshold
        for type_name in DEPTH_GATED_ORES:
            threshold = DEPTH_ROCK_THRESHOLDS.get(type_name, 0)
            if self.depth < threshold and type_name in dist:
                del dist[type_name]

        # Add depth-gated types that are now unlocked (only if not already in dist)
        for type_name, threshold in DEPTH_ROCK_THRESHOLDS.items():
            if self.depth >= threshold and type_name not in dist:
                if type_name in DEPTH_GATED_ORES:
                    base_weight = self.config.rock_distribution.get(type_name, 0.10)
                    depth_bonus = 0.02 * (self.depth - threshold)
                    dist[type_name] = min(base_weight + depth_bonus, 0.35)
                else:
                    weight = 0.10 + 0.02 * (self.depth - threshold)
                    dist[type_name] = min(weight, 0.25)
                if "common" in dist:
                    dist["common"] = max(0.10, dist["common"] - 0.02)

        return dist

    def _generate_field(self) -> None:
        """Generate asteroid field based on config and depth."""
        self.rocks.clear()
        distribution = self._get_depth_rock_distribution()

        # Build weighted list
        rock_types = []
        weights = []
        for type_name, weight in distribution.items():
            try:
                rock_types.append(RockType(type_name))
                weights.append(weight)
            except ValueError:
                continue

        if not rock_types:
            rock_types = [RockType.COMMON]
            weights = [1.0]

        # Boost crystal and rare weights based on combined rare bonuses
        depth_mods = self.get_depth_modifiers()
        effective_rare = min(
            self.rare_chance_bonus + depth_mods.rare_weight_bonus,
            2.0,  # Cap at 3x weight multiplier to preserve common rock distribution
        )
        if effective_rare > 0:
            for i, rt in enumerate(rock_types):
                if rt in (RockType.CRYSTAL, RockType.RARE):
                    weights[i] *= 1 + effective_rare

        # Reserve one cell for monolith at every 5 depths
        monolith_cell = None
        if self.depth > 1 and self.depth % 5 == 0:
            monolith_cell = (
                random.randint(0, self.config.grid_width - 1),
                random.randint(0, self.config.grid_height - 1),
            )

        for y in range(self.config.grid_height):
            for x in range(self.config.grid_width):
                if monolith_cell and (x, y) == monolith_cell:
                    self.rocks.append(
                        AsteroidRock(
                            rock_type=RockType.MONOLITH,
                            grid_x=x,
                            grid_y=y,
                            hardness_override=10.0 + self.depth * 0.5,
                            yield_override=5 + self.depth,
                            strata_reward=self.depth * 2,
                        )
                    )
                else:
                    rock_type = random.choices(rock_types, weights=weights, k=1)[0]
                    self.rocks.append(
                        AsteroidRock(
                            rock_type=rock_type,
                            grid_x=x,
                            grid_y=y,
                        )
                    )

        self._generate_hazards()

    def _generate_hazards(self) -> None:
        """Spawn environmental hazards based on current depth."""
        self.hazards.clear()
        if self.depth < HAZARD_UNSTABLE_DEPTH:
            return

        # Determine how many hazard cells to place (1-2 at threshold, scaling)
        hazard_types: list[HazardType] = []
        if self.depth >= HAZARD_UNSTABLE_DEPTH:
            count = 1 + (self.depth - HAZARD_UNSTABLE_DEPTH) // 5
            hazard_types.extend([HazardType.UNSTABLE_CELL] * min(count, 3))
        if self.depth >= HAZARD_VENT_DEPTH:
            count = 1 + (self.depth - HAZARD_VENT_DEPTH) // 5
            hazard_types.extend([HazardType.PRESSURE_VENT] * min(count, 2))

        if not hazard_types:
            return

        # Pick random non-monolith rocks to replace with hazards
        candidates = [
            r for r in self.rocks if r.rock_type != RockType.MONOLITH
        ]
        random.shuffle(candidates)
        for i, htype in enumerate(hazard_types):
            if i >= len(candidates):
                break
            rock = candidates[i]
            self.rocks.remove(rock)
            self.hazards.append(
                HazardCell(hazard_type=htype, grid_x=rock.grid_x, grid_y=rock.grid_y)
            )

    def get_rock_at(self, grid_x: int, grid_y: int) -> Optional[AsteroidRock]:
        """Get rock at grid position."""
        for rock in self.rocks:
            if rock.grid_x == grid_x and rock.grid_y == grid_y:
                return rock
        return None

    def get_depth_modifiers(self) -> DepthModifiers:
        """Get modifiers for the current mining depth."""
        d = self.depth
        if d <= 3:
            return DepthModifiers(0.0, 1, 0.0)
        elif d <= 6:
            return DepthModifiers((d - 3) * 0.10, 1, 0.10)
        elif d <= 9:
            return DepthModifiers(0.30 + (d - 6) * 0.20, 2, 0.20)
        else:
            return DepthModifiers(0.90 + (d - 9) * 0.30, 2, 0.30)

    def get_click_energy_cost(self) -> int:
        """Get energy cost per click at current depth."""
        return self.get_depth_modifiers().energy_cost_multiplier

    def _apply_yield_bonus(self, base_yield: int) -> int:
        """Apply depth yield bonus, danger multiplier, and perk bonus to yield."""
        from spacegame.config import DANGER_YIELD_MULTIPLIERS

        bonus = self.get_depth_modifiers().yield_bonus
        result = base_yield
        if bonus > 0:
            result = base_yield + math.floor(base_yield * bonus)
        # Danger + perk multipliers stack additively
        total_mult = DANGER_YIELD_MULTIPLIERS.get(self.config.danger_level, 1.0)
        total_mult += self.config.perk_yield_bonus
        if total_mult != 1.0:
            result = math.floor(result * total_mult)
        return max(1, result)

    def _roll_ingredient_drops(self) -> dict[str, int]:
        """Roll for depth-gated ingredient drops on rock break.

        Returns:
            Dict of ingredient_id -> quantity (empty if nothing dropped).
        """
        drops: dict[str, int] = {}
        # Resonance core: 5% at depth 15+ (checked first — rarer, higher priority)
        if self.depth >= 15 and random.random() < 0.05:
            drops["resonance_core"] = 1
        # Flux catalyst: 10% at depth 8+
        if self.depth >= 8 and random.random() < 0.10:
            drops["flux_catalyst"] = 1
        return drops

    def click_rock(
        self, grid_x: int, grid_y: int, empowered: bool = False
    ) -> tuple[bool, str, Optional[MiningResult]]:
        """Click a rock to mine it.

        Normal clicks are free and unlimited. Empowered clicks cost energy
        but deal triple damage.

        Args:
            grid_x: Grid X coordinate.
            grid_y: Grid Y coordinate.
            empowered: If True, spend energy for 3x click power.

        Returns:
            Tuple of (success, message, result_if_rock_broke).
        """
        self.chain_results.clear()
        self.newly_completed_milestones.clear()

        rock = self.get_rock_at(grid_x, grid_y)
        if rock is None:
            return (False, "No rock at that position", None)

        if rock.depleted:
            return (False, "Rock is already depleted", None)

        # Empowered clicks require energy
        if empowered:
            energy_cost = self.get_click_energy_cost()
            if self.energy < energy_cost:
                return (False, "Not enough energy for empowered click!", None)
            self.energy -= energy_cost

        # Switch active rock (old rock keeps progress)
        self.active_rock = rock
        self.total_clicks += 1

        # Apply click — empowered clicks deal 3x damage
        power_multiplier = 3.0 if empowered else 1.0
        effective_power = self.config.base_click_power * (1 + self.click_power_bonus) * power_multiplier
        yield_amount = rock.apply_click(effective_power)

        if yield_amount is not None:
            final_yield = self._apply_yield_bonus(yield_amount)
            result = MiningResult(
                commodity_id=rock.commodity_id,
                quantity=final_yield,
                rock_type=rock.rock_type,
                ingredient_drops=self._roll_ingredient_drops(),
            )
            self.total_mined[rock.commodity_id] = (
                self.total_mined.get(rock.commodity_id, 0) + final_yield
            )
            self.active_rock = None
            self._on_rock_broken(rock)
            self._apply_volatile_splash(rock)
            self._check_chain_detonation(rock)
            self._check_unstable_detonation(rock)
            self._check_milestones()
            return (True, f"Mined {final_yield} {rock.commodity_id}!", result)

        return (True, f"Drilling {rock.rock_type.value} rock...", None)

    def start_drill(self, grid_x: int, grid_y: int) -> tuple[bool, str]:
        """Start drilling a rock (backward-compat wrapper for click_rock).

        Args:
            grid_x: Grid X coordinate.
            grid_y: Grid Y coordinate.

        Returns:
            Tuple of (success, message).
        """
        success, msg, _ = self.click_rock(grid_x, grid_y)
        return (success, msg)

    def update(self, dt: float, cargo_full: bool = False) -> list[MiningResult]:
        """Update mining session: passive drill and drone mining.

        Args:
            dt: Delta time in seconds.
            cargo_full: If True, skip passive drill and drone mining (cargo hold full).

        Returns:
            List of MiningResult for rocks broken this frame.
        """
        self.chain_results.clear()
        self.newly_completed_milestones.clear()
        results: list[MiningResult] = []

        # Energy regeneration
        if self.energy < self.max_energy:
            self._energy_regen_timer += dt
            while (
                self._energy_regen_timer >= self.config.energy_regen_seconds
                and self.energy < self.max_energy
            ):
                self.energy += 1
                self._energy_regen_timer -= self.config.energy_regen_seconds

        # Skip auto-mining when cargo is full
        if cargo_full:
            self._check_milestones()
            return results

        # Passive drill on active rock
        if self.active_rock and not self.active_rock.depleted:
            passive_rate = self.config.base_passive_rate * (1 + self.passive_drill_bonus)
            # Use update_drill with the passive rate as the speed_bonus
            self.active_rock.drilling = True
            drill_rate = passive_rate / self.active_rock.hardness
            self.active_rock.drill_progress += drill_rate * dt

            if self.active_rock.drill_progress >= 1.0:
                self.active_rock.drill_progress = 1.0
                self.active_rock.drilling = False
                self.active_rock.depleted = True
                yield_amount = self._apply_yield_bonus(self.active_rock.get_yield())
                result = MiningResult(
                    commodity_id=self.active_rock.commodity_id,
                    quantity=yield_amount,
                    rock_type=self.active_rock.rock_type,
                    ingredient_drops=self._roll_ingredient_drops(),
                )
                self.total_mined[self.active_rock.commodity_id] = (
                    self.total_mined.get(self.active_rock.commodity_id, 0) + yield_amount
                )
                results.append(result)
                broken_rock = self.active_rock
                self.active_rock = None
                self._on_rock_broken(broken_rock)
                self._apply_volatile_splash(broken_rock)
                self._check_chain_detonation(broken_rock)
                self._check_unstable_detonation(broken_rock)

        # Auto-drill: passively breaks the weakest rock on a timer
        if self.auto_drill_level > 0:
            intervals = {1: 8.0, 2: 5.0, 3: 3.0}
            interval = intervals.get(self.auto_drill_level, 8.0)
            self._auto_drill_timer += dt
            while self._auto_drill_timer >= interval:
                self._auto_drill_timer -= interval
                auto_result = self._auto_drill_break()
                if auto_result:
                    results.append(auto_result)

        # Drone mining
        drone_results = self._update_drones(dt)
        results.extend(drone_results)

        # Environmental hazards
        vent_results = self._update_pressure_vents(dt)
        results.extend(vent_results)

        self._check_milestones()
        return results

    def _update_drones(self, dt: float) -> list[MiningResult]:
        """Update drone auto-mining.

        Each drone picks an undepleted rock (respecting preference),
        avoids active_rock, and applies mining progress.

        Args:
            dt: Delta time in seconds.

        Returns:
            List of MiningResult for rocks broken by drones.
        """
        results: list[MiningResult] = []

        for i, drone in enumerate(self.drones):
            # Get or assign target
            target = self.drone_targets.get(i)
            if target is None or target.depleted:
                target = self._pick_drone_target(drone, i)
                if target is None:
                    self.drone_targets.pop(i, None)
                    continue
                self.drone_targets[i] = target

            # Apply drone mining
            effective_speed = drone.mining_speed * (1 + self.drone_speed_bonus)
            progress = effective_speed / target.hardness * dt
            target.drilling = True
            target.drill_progress += progress

            if target.drill_progress >= 1.0:
                target.drill_progress = 1.0
                target.drilling = False
                target.depleted = True
                base_yield = target.get_yield()
                # Apply drone yield bonus + depth yield bonus
                bonus_yield = math.floor(base_yield * drone.yield_bonus)
                final_yield = self._apply_yield_bonus(base_yield + bonus_yield)
                result = MiningResult(
                    commodity_id=target.commodity_id,
                    quantity=final_yield,
                    rock_type=target.rock_type,
                    ingredient_drops=self._roll_ingredient_drops(),
                )
                self.total_mined[target.commodity_id] = (
                    self.total_mined.get(target.commodity_id, 0) + final_yield
                )
                results.append(result)
                self.drone_targets.pop(i, None)
                self._on_rock_broken(target)
                self._apply_volatile_splash(target)
                self._check_chain_detonation(target)
                self._check_unstable_detonation(target)

        return results

    def _pick_drone_target(self, drone: MiningDrone, drone_index: int) -> Optional[AsteroidRock]:
        """Pick a target rock for a drone.

        Respects preference, avoids active_rock and other drones' targets.

        Args:
            drone: The drone needing a target.
            drone_index: Index of the drone in the list.

        Returns:
            A suitable rock, or None if none available.
        """
        # Rocks already claimed by other drones or the player
        claimed = set()
        if self.active_rock is not None:
            claimed.add(id(self.active_rock))
        for idx, rock in self.drone_targets.items():
            if idx != drone_index:
                claimed.add(id(rock))

        available = [
            r for r in self.rocks
            if not r.depleted and id(r) not in claimed and not r.config.drone_immune
        ]

        if not available:
            return None

        # Try preferred type first
        if drone.target_preference is not None:
            preferred = [r for r in available if r.rock_type == drone.target_preference]
            if preferred:
                return random.choice(preferred)

        # Fall back to any available rock
        return random.choice(available)

    def _select_milestones(self) -> list[MiningMilestone]:
        """Select 3 random milestones (one per category, then sample 3)."""
        by_category: dict[str, list[dict]] = {}
        for m in MILESTONE_POOL:
            by_category.setdefault(m["category"], []).append(m)
        candidates = [random.choice(v) for v in by_category.values()]
        selected = random.sample(candidates, min(3, len(candidates)))
        return [MiningMilestone(**m) for m in selected]

    def _on_rock_broken(self, rock: AsteroidRock) -> None:
        """Track stats when any rock breaks (click, passive, drone, chain)."""
        self.rocks_broken += 1
        if rock.rock_type in (RockType.CRYSTAL, RockType.RARE):
            self.rare_ores_found += 1

    def _check_milestones(self) -> None:
        """Check and complete any milestones that have reached their threshold."""
        for ms in self.milestones:
            if ms.completed:
                continue
            value = self._get_milestone_value(ms.category)
            if value >= ms.threshold:
                ms.completed = True
                self.newly_completed_milestones.append(ms)

    def _get_milestone_value(self, category: str) -> int:
        """Get current value for a milestone category."""
        if category == "rocks_mined":
            return self.rocks_broken
        if category == "rare_ores":
            return self.rare_ores_found
        if category == "depth_reached":
            return self.depth
        if category == "chains_triggered":
            return self.total_chains
        return 0

    def _get_neighbors(self, gx: int, gy: int) -> list[AsteroidRock]:
        """Get adjacent rocks (8 directions)."""
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                rock = self.get_rock_at(gx + dx, gy + dy)
                if rock is not None:
                    neighbors.append(rock)
        return neighbors

    def _check_chain_detonation(self, broken_rock: AsteroidRock, depth: int = 1) -> None:
        """Check for chain detonation from a broken rock.

        Same-type undepleted neighbors have a chance to receive progress.
        If that pushes them past 1.0, they break and cascade.

        Args:
            broken_rock: The rock that just broke.
            depth: Current chain depth (stops at CHAIN_MAX_DEPTH).
        """
        if depth > self.max_chain_depth:
            return
        # Chain-immune rocks cannot trigger chains
        if broken_rock.config.chain_immune:
            return
        chain_chance = CHAIN_BASE_CHANCE + self.chain_chance_bonus
        neighbors = self._get_neighbors(broken_rock.grid_x, broken_rock.grid_y)
        for neighbor in neighbors:
            if neighbor.depleted or neighbor.rock_type != broken_rock.rock_type:
                continue
            # Chain-immune rocks cannot be chain targets
            if neighbor.config.chain_immune:
                continue
            if random.random() < chain_chance:
                neighbor.drill_progress += CHAIN_PROGRESS_AMOUNT
                if neighbor.drill_progress >= 1.0:
                    neighbor.drill_progress = 1.0
                    neighbor.depleted = True
                    neighbor.drilling = False
                    yield_amount = self._apply_yield_bonus(neighbor.get_yield())
                    commodity = ROCK_TYPE_CONFIGS[neighbor.rock_type].commodity_id
                    self.total_mined[commodity] = (
                        self.total_mined.get(commodity, 0) + yield_amount
                    )
                    self._on_rock_broken(neighbor)
                    self.chain_results.append(
                        ChainBreak(
                            grid_x=neighbor.grid_x,
                            grid_y=neighbor.grid_y,
                            rock_type=neighbor.rock_type,
                            commodity_id=commodity,
                            quantity=yield_amount,
                            chain_depth=depth,
                            ingredient_drops=self._roll_ingredient_drops(),
                        )
                    )
                    self.total_chains += 1
                    self._check_chain_detonation(neighbor, depth + 1)

    def _apply_volatile_splash(self, broken_rock: AsteroidRock) -> None:
        """Apply volatile rock splash damage: 50% drill progress to all adjacent rocks."""
        if not broken_rock.config.volatile_splash:
            return
        neighbors = self._get_neighbors(broken_rock.grid_x, broken_rock.grid_y)
        for neighbor in neighbors:
            if neighbor.depleted:
                continue
            neighbor.drill_progress = min(1.0, neighbor.drill_progress + 0.5)
            if neighbor.drill_progress >= 1.0:
                neighbor.drill_progress = 1.0
                neighbor.depleted = True
                neighbor.drilling = False
                yield_amount = self._apply_yield_bonus(neighbor.get_yield())
                commodity = neighbor.commodity_id
                self.total_mined[commodity] = (
                    self.total_mined.get(commodity, 0) + yield_amount
                )
                self._on_rock_broken(neighbor)
                self.chain_results.append(
                    ChainBreak(
                        grid_x=neighbor.grid_x,
                        grid_y=neighbor.grid_y,
                        rock_type=neighbor.rock_type,
                        commodity_id=commodity,
                        quantity=yield_amount,
                        chain_depth=0,
                    )
                )

    def _get_hazard_neighbors(self, gx: int, gy: int) -> list[AsteroidRock]:
        """Get rocks adjacent to a hazard cell (8 directions)."""
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                rock = self.get_rock_at(gx + dx, gy + dy)
                if rock is not None:
                    neighbors.append(rock)
        return neighbors

    def _is_adjacent_to_hazard(self, rock: AsteroidRock, hazard: HazardCell) -> bool:
        """Check if a rock is adjacent (8 directions) to a hazard cell."""
        return abs(rock.grid_x - hazard.grid_x) <= 1 and abs(rock.grid_y - hazard.grid_y) <= 1

    def _check_unstable_detonation(self, broken_rock: AsteroidRock) -> list[MiningResult]:
        """Check if breaking a rock triggers any adjacent unstable cells.

        Unstable cells detonate when an adjacent rock breaks, applying 30% progress
        to all their neighbors. Costs 3 energy. Consumed after detonation.

        Returns:
            List of MiningResult for any rocks broken by detonation.
        """
        results: list[MiningResult] = []
        to_remove: list[HazardCell] = []
        for hazard in self.hazards:
            if hazard.hazard_type != HazardType.UNSTABLE_CELL:
                continue
            if not self._is_adjacent_to_hazard(broken_rock, hazard):
                continue
            if self.energy < UNSTABLE_ENERGY_COST:
                continue
            # Detonate
            self.energy -= UNSTABLE_ENERGY_COST
            neighbors = self._get_hazard_neighbors(hazard.grid_x, hazard.grid_y)
            for neighbor in neighbors:
                if neighbor.depleted:
                    continue
                neighbor.drill_progress = min(1.0, neighbor.drill_progress + UNSTABLE_PROGRESS_AMOUNT)
                if neighbor.drill_progress >= 1.0:
                    neighbor.drill_progress = 1.0
                    neighbor.depleted = True
                    neighbor.drilling = False
                    yield_amount = self._apply_yield_bonus(neighbor.get_yield())
                    commodity = neighbor.commodity_id
                    self.total_mined[commodity] = (
                        self.total_mined.get(commodity, 0) + yield_amount
                    )
                    self._on_rock_broken(neighbor)
                    results.append(MiningResult(
                        commodity_id=commodity,
                        quantity=yield_amount,
                        rock_type=neighbor.rock_type,
                    ))
            to_remove.append(hazard)
        for hazard in to_remove:
            self.hazards.remove(hazard)
        return results

    def _auto_drill_break(self) -> Optional[MiningResult]:
        """Break the weakest undepleted rock for the auto-drill upgrade.

        Returns:
            MiningResult if a rock was broken, None if no valid target.
        """
        # Find the weakest (lowest hardness) undepleted rock
        candidates = [r for r in self.rocks if not r.depleted]
        if not candidates:
            return None
        target = min(candidates, key=lambda r: r.hardness)
        target.depleted = True
        target.drill_progress = 1.0
        yield_amount = self._apply_yield_bonus(target.get_yield())
        result = MiningResult(
            commodity_id=target.commodity_id,
            quantity=yield_amount,
            rock_type=target.rock_type,
            ingredient_drops=self._roll_ingredient_drops(),
        )
        self.total_mined[target.commodity_id] = (
            self.total_mined.get(target.commodity_id, 0) + yield_amount
        )
        self._on_rock_broken(target)
        self._apply_volatile_splash(target)
        self._check_chain_detonation(target)
        self._check_unstable_detonation(target)
        return result

    def _update_pressure_vents(self, dt: float) -> list[MiningResult]:
        """Update pressure vent timers and pulse when ready.

        Pressure vents pulse every 8 seconds, applying 10% progress to adjacent rocks.

        Returns:
            List of MiningResult for any rocks broken by vent pulses.
        """
        results: list[MiningResult] = []
        for hazard in self.hazards:
            if hazard.hazard_type != HazardType.PRESSURE_VENT:
                continue
            hazard.pulse_timer += dt
            if hazard.pulse_timer >= VENT_PULSE_INTERVAL:
                hazard.pulse_timer -= VENT_PULSE_INTERVAL
                neighbors = self._get_hazard_neighbors(hazard.grid_x, hazard.grid_y)
                for neighbor in neighbors:
                    if neighbor.depleted:
                        continue
                    neighbor.drill_progress = min(1.0, neighbor.drill_progress + VENT_PROGRESS_AMOUNT)
                    if neighbor.drill_progress >= 1.0:
                        neighbor.drill_progress = 1.0
                        neighbor.depleted = True
                        neighbor.drilling = False
                        yield_amount = self._apply_yield_bonus(neighbor.get_yield())
                        commodity = neighbor.commodity_id
                        self.total_mined[commodity] = (
                            self.total_mined.get(commodity, 0) + yield_amount
                        )
                        self._on_rock_broken(neighbor)
                        results.append(MiningResult(
                            commodity_id=commodity,
                            quantity=yield_amount,
                            rock_type=neighbor.rock_type,
                        ))
        return results

    def regenerate_field(self) -> DepthAdvanceResult:
        """Regenerate the asteroid field and advance to next depth.

        Returns:
            DepthAdvanceResult with strata earned and full clear status.
        """
        from spacegame.models.deep_core import calculate_strata_earned

        was_full_clear = self.get_undepleted_count() == 0
        cleared_depth = self.depth
        strata = calculate_strata_earned(
            cleared_depth,
            full_clear=was_full_clear,
            prestige_level=self.prestige_level,
        )

        self.depth += 1
        self.energy = self.max_energy
        self._energy_regen_timer = 0.0
        self._generate_field()
        self.active_rock = None
        self.drone_targets.clear()

        return DepthAdvanceResult(
            new_depth=self.depth,
            strata_earned=strata,
            was_full_clear=was_full_clear,
        )

    def get_undepleted_count(self) -> int:
        """Get count of rocks that haven't been mined yet."""
        return sum(1 for r in self.rocks if not r.depleted)

    def get_total_rocks(self) -> int:
        """Get total number of rocks in the field."""
        return len(self.rocks)
