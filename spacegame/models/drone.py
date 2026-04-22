"""
Mining drone models.

Persistent drone fleet for automated asteroid mining during sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

from spacegame.models.mining import RockType

if TYPE_CHECKING:
    from spacegame.models.player import Player


class DroneTier(IntEnum):
    """Drone quality tiers with increasing capabilities."""

    BASIC = 1
    ADVANCED = 2
    ELITE = 3


DRONE_TIER_CONFIGS: dict[DroneTier, dict] = {
    DroneTier.BASIC: {
        "mining_speed": 0.3,
        "yield_bonus": 0.0,
        "can_target": False,
    },
    DroneTier.ADVANCED: {
        "mining_speed": 0.6,
        "yield_bonus": 0.0,
        "can_target": True,
    },
    DroneTier.ELITE: {
        "mining_speed": 1.0,
        "yield_bonus": 0.25,
        "can_target": True,
    },
}


@dataclass
class MiningDrone:
    """A single mining drone owned by the player."""

    tier: DroneTier
    target_preference: Optional[RockType] = None

    @property
    def config(self) -> dict:
        """Get tier configuration."""
        return DRONE_TIER_CONFIGS[self.tier]

    @property
    def mining_speed(self) -> float:
        """Base mining speed (drill progress per second on hardness=1.0)."""
        return self.config["mining_speed"]

    @property
    def yield_bonus(self) -> float:
        """Yield multiplier bonus (0.0 = no bonus)."""
        return self.config["yield_bonus"]

    @property
    def can_target(self) -> bool:
        """Whether this drone supports ore type targeting."""
        return self.config["can_target"]

    def set_target_preference(self, rock_type: Optional[RockType]) -> tuple[bool, str]:
        """Set ore targeting preference.

        Args:
            rock_type: Preferred rock type, or None to clear.

        Returns:
            Tuple of (success, message).
        """
        if rock_type is not None and not self.can_target:
            return (False, "This drone tier does not support ore targeting")
        self.target_preference = rock_type
        if rock_type:
            return (True, f"Drone now targeting {rock_type.value} rocks")
        return (True, "Drone targeting cleared")

    def to_dict(self) -> dict:
        """Serialize drone to dict."""
        return {
            "tier": self.tier.value,
            "target_preference": (self.target_preference.value if self.target_preference else None),
        }

    @classmethod
    def from_dict(cls, data: dict) -> MiningDrone:
        """Deserialize drone from dict."""
        tier = DroneTier(data["tier"])
        pref = RockType(data["target_preference"]) if data.get("target_preference") else None
        return cls(tier=tier, target_preference=pref)


@dataclass
class MiningDroneFleet:
    """Collection of player's mining drones.

    Manages drone slots and fleet-wide operations. Drone slots
    are unlocked via the MINING skill tree, not purchased with credits.
    """

    drones: list[MiningDrone] = field(default_factory=list)
    max_slots: int = 0

    @property
    def slot_count(self) -> int:
        """Number of drones currently owned."""
        return len(self.drones)

    @property
    def available_slots(self) -> int:
        """Number of empty drone slots."""
        return max(0, self.max_slots - len(self.drones))

    def add_drone(self, drone: MiningDrone) -> tuple[bool, str]:
        """Add a drone to the fleet.

        Args:
            drone: Drone to add.

        Returns:
            Tuple of (success, message).
        """
        if len(self.drones) >= self.max_slots:
            return (False, "No available drone slots")
        self.drones.append(drone)
        return (True, f"Tier {drone.tier.value} drone added to fleet")

    def remove_drone(self, index: int) -> tuple[bool, str]:
        """Remove a drone by index.

        Args:
            index: Index in drones list.

        Returns:
            Tuple of (success, message).
        """
        if index < 0 or index >= len(self.drones):
            return (False, "Invalid drone index")
        removed = self.drones.pop(index)
        return (True, f"Tier {removed.tier.value} drone removed")

    def get_active_drones(self) -> list[MiningDrone]:
        """Get all drones in the fleet (returns a copy)."""
        return list(self.drones)

    def to_dict(self) -> dict:
        """Serialize fleet to dict."""
        return {
            "drones": [d.to_dict() for d in self.drones],
            "max_slots": self.max_slots,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MiningDroneFleet:
        """Deserialize fleet from dict."""
        drones = [MiningDrone.from_dict(d) for d in data.get("drones", [])]
        return cls(
            drones=drones,
            max_slots=data.get("max_slots", 0),
        )


def apply_drone_skill_effects(player: Player) -> None:
    """Sync drone fleet state with skill tree.

    Reads the ``drone_fleet`` skill level and grants drones of
    increasing tier (BASIC at lv1, ADVANCED at lv2, ELITE at lv3).
    Idempotent — safe to call on load and after every skill-up.

    Args:
        player: Player whose fleet to update.
    """
    prog = player.progression
    fleet = player.drone_fleet

    # drone_fleet is a single skill with max_level=3
    level_tiers: list[DroneTier] = [
        DroneTier.BASIC,
        DroneTier.ADVANCED,
        DroneTier.ELITE,
    ]

    skill = prog.skills.get("drone_fleet")
    level = skill.current_level if skill else 0

    # Each level grants one additional drone slot
    expected_drones: list[DroneTier] = level_tiers[:level]
    fleet.max_slots = len(expected_drones)

    # Grant drones that haven't been granted yet
    while len(fleet.drones) < len(expected_drones):
        next_tier = expected_drones[len(fleet.drones)]
        fleet.drones.append(MiningDrone(tier=next_tier))
