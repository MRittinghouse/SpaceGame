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


@dataclass
class RockTypeConfig:
    """Configuration for a rock type."""

    rock_type: RockType
    hardness: float  # Drill time in seconds (0.5 - 3.0)
    min_yield: int
    max_yield: int
    commodity_id: str  # What commodity this yields
    color: tuple  # RGB color for rendering


# Default rock type configurations
ROCK_TYPE_CONFIGS = {
    RockType.COMMON: RockTypeConfig(
        rock_type=RockType.COMMON,
        hardness=0.5,
        min_yield=1,
        max_yield=3,
        commodity_id="raw_ore",
        color=(120, 110, 100),
    ),
    RockType.IRON: RockTypeConfig(
        rock_type=RockType.IRON,
        hardness=1.0,
        min_yield=1,
        max_yield=3,
        commodity_id="iron_ore",
        color=(160, 80, 60),
    ),
    RockType.CRYSTAL: RockTypeConfig(
        rock_type=RockType.CRYSTAL,
        hardness=2.0,
        min_yield=1,
        max_yield=2,
        commodity_id="crystal_ore",
        color=(100, 180, 220),
    ),
    RockType.RARE: RockTypeConfig(
        rock_type=RockType.RARE,
        hardness=3.0,
        min_yield=1,
        max_yield=2,
        commodity_id="rare_ore",
        color=(200, 100, 255),
    ),
}


@dataclass
class AsteroidRock:
    """A single minable rock in the asteroid field."""

    rock_type: RockType
    grid_x: int
    grid_y: int
    depleted: bool = False
    drill_progress: float = 0.0  # 0.0 to 1.0
    drilling: bool = False

    @property
    def config(self) -> RockTypeConfig:
        """Get configuration for this rock type."""
        return ROCK_TYPE_CONFIGS[self.rock_type]

    @property
    def hardness(self) -> float:
        """Get drill time in seconds."""
        return self.config.hardness

    @property
    def commodity_id(self) -> str:
        """Get the commodity this rock yields."""
        return self.config.commodity_id

    def get_yield(self) -> int:
        """Get random yield amount when rock breaks."""
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

    def __post_init__(self):
        if not self.rock_distribution:
            self.rock_distribution = {
                "common": 0.50,
                "iron": 0.30,
                "crystal": 0.15,
                "rare": 0.05,
            }


@dataclass
class MiningResult:
    """Result of a single mining action."""

    commodity_id: str
    quantity: int
    rock_type: RockType


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
        drones: Optional[list[MiningDrone]] = None,
    ):
        """
        Initialize mining session.

        Args:
            config: Mining configuration for the current system.
            drill_speed_bonus: Legacy drill speed multiplier (used by start_drill compat).
            click_power_bonus: Fractional bonus to click power (0.0 = no bonus).
            passive_drill_bonus: Fractional bonus to passive drill rate.
            drone_speed_bonus: Fractional bonus to drone mining speed.
            rare_chance_bonus: Fractional bonus to rare ore chance (future use).
            drones: List of active MiningDrone instances.
        """
        self.config = config
        self.drill_speed_bonus = drill_speed_bonus
        self.click_power_bonus = click_power_bonus
        self.passive_drill_bonus = passive_drill_bonus
        self.drone_speed_bonus = drone_speed_bonus
        self.rare_chance_bonus = rare_chance_bonus
        self.drones: list[MiningDrone] = drones or []

        self.rocks: List[AsteroidRock] = []
        self.active_rock: Optional[AsteroidRock] = None
        self.total_mined: Dict[str, int] = {}  # commodity_id -> quantity
        self.total_clicks: int = 0
        self.drone_targets: Dict[int, AsteroidRock] = {}  # drone_index -> rock

        self._generate_field()

    def _generate_field(self) -> None:
        """Generate asteroid field based on config."""
        self.rocks.clear()
        distribution = self.config.rock_distribution

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

        for y in range(self.config.grid_height):
            for x in range(self.config.grid_width):
                rock_type = random.choices(rock_types, weights=weights, k=1)[0]
                self.rocks.append(
                    AsteroidRock(
                        rock_type=rock_type,
                        grid_x=x,
                        grid_y=y,
                    )
                )

    def get_rock_at(self, grid_x: int, grid_y: int) -> Optional[AsteroidRock]:
        """Get rock at grid position."""
        for rock in self.rocks:
            if rock.grid_x == grid_x and rock.grid_y == grid_y:
                return rock
        return None

    def click_rock(self, grid_x: int, grid_y: int) -> tuple[bool, str, Optional[MiningResult]]:
        """Click a rock to mine it.

        Applies click power to the rock. Switches active_rock if clicking
        a different rock (no lock-out). Increments total_clicks.

        Args:
            grid_x: Grid X coordinate.
            grid_y: Grid Y coordinate.

        Returns:
            Tuple of (success, message, result_if_rock_broke).
        """
        rock = self.get_rock_at(grid_x, grid_y)
        if rock is None:
            return (False, "No rock at that position", None)

        if rock.depleted:
            return (False, "Rock is already depleted", None)

        # Switch active rock (old rock keeps progress)
        self.active_rock = rock
        self.total_clicks += 1

        # Apply click
        effective_power = self.config.base_click_power * (1 + self.click_power_bonus)
        yield_amount = rock.apply_click(effective_power)

        if yield_amount is not None:
            result = MiningResult(
                commodity_id=rock.commodity_id,
                quantity=yield_amount,
                rock_type=rock.rock_type,
            )
            self.total_mined[rock.commodity_id] = (
                self.total_mined.get(rock.commodity_id, 0) + yield_amount
            )
            self.active_rock = None
            return (True, f"Mined {yield_amount} {rock.commodity_id}!", result)

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

    def update(self, dt: float) -> list[MiningResult]:
        """Update mining session: passive drill and drone mining.

        Args:
            dt: Delta time in seconds.

        Returns:
            List of MiningResult for rocks broken this frame.
        """
        results: list[MiningResult] = []

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
                yield_amount = self.active_rock.get_yield()
                result = MiningResult(
                    commodity_id=self.active_rock.commodity_id,
                    quantity=yield_amount,
                    rock_type=self.active_rock.rock_type,
                )
                self.total_mined[self.active_rock.commodity_id] = (
                    self.total_mined.get(self.active_rock.commodity_id, 0) + yield_amount
                )
                results.append(result)
                self.active_rock = None

        # Drone mining
        drone_results = self._update_drones(dt)
        results.extend(drone_results)

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
                # Apply drone yield bonus
                bonus_yield = math.floor(base_yield * drone.yield_bonus)
                final_yield = base_yield + bonus_yield
                result = MiningResult(
                    commodity_id=target.commodity_id,
                    quantity=final_yield,
                    rock_type=target.rock_type,
                )
                self.total_mined[target.commodity_id] = (
                    self.total_mined.get(target.commodity_id, 0) + final_yield
                )
                results.append(result)
                self.drone_targets.pop(i, None)

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

        available = [r for r in self.rocks if not r.depleted and id(r) not in claimed]

        if not available:
            return None

        # Try preferred type first
        if drone.target_preference is not None:
            preferred = [r for r in available if r.rock_type == drone.target_preference]
            if preferred:
                return random.choice(preferred)

        # Fall back to any available rock
        return random.choice(available)

    def regenerate_field(self) -> None:
        """Regenerate the asteroid field (between sessions)."""
        self._generate_field()
        self.active_rock = None
        self.drone_targets.clear()

    def get_undepleted_count(self) -> int:
        """Get count of rocks that haven't been mined yet."""
        return sum(1 for r in self.rocks if not r.depleted)

    def get_total_rocks(self) -> int:
        """Get total number of rocks in the field."""
        return len(self.rocks)
