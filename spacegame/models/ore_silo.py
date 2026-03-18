"""Ore Silo model — per-system ore storage buffer for extended mining sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


BASE_SILO_CAPACITY = 100


@dataclass
class OreSilo:
    """Per-system ore storage buffer that decouples mining from ship cargo.

    Ore mined goes into the silo first. On exiting the mining view,
    the player transfers silo contents into ship cargo (limited by
    available cargo space). Remainder stays for next visit.
    """

    system_id: str
    capacity: int = BASE_SILO_CAPACITY
    contents: dict[str, int] = field(default_factory=dict)

    def get_total_stored(self) -> int:
        """Get total units of ore stored across all types."""
        return sum(self.contents.values())

    def get_available_space(self) -> int:
        """Get remaining capacity."""
        return max(0, self.capacity - self.get_total_stored())

    def is_full(self) -> bool:
        """Check if the silo has no remaining capacity."""
        return self.get_total_stored() >= self.capacity

    def add_ore(self, commodity_id: str, quantity: int) -> int:
        """Add ore to the silo, capped at capacity.

        Args:
            commodity_id: Type of ore to add.
            quantity: Amount to add.

        Returns:
            Actual amount added (may be less if silo is nearly full).
        """
        space = self.get_available_space()
        actual = min(quantity, space)
        if actual > 0:
            self.contents[commodity_id] = self.contents.get(commodity_id, 0) + actual
        return actual

    def remove_ore(self, commodity_id: str, quantity: int) -> int:
        """Remove ore from the silo.

        Args:
            commodity_id: Type of ore to remove.
            quantity: Amount to remove.

        Returns:
            Actual amount removed (may be less if not enough stored).
        """
        stored = self.contents.get(commodity_id, 0)
        actual = min(quantity, stored)
        if actual > 0:
            remaining = stored - actual
            if remaining > 0:
                self.contents[commodity_id] = remaining
            else:
                self.contents.pop(commodity_id, None)
        return actual

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "system_id": self.system_id,
            "capacity": self.capacity,
            "contents": dict(self.contents),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OreSilo:
        """Deserialize from dictionary."""
        return cls(
            system_id=data["system_id"],
            capacity=data.get("capacity", BASE_SILO_CAPACITY),
            contents=dict(data.get("contents", {})),
        )


class OreSiloManager:
    """Manages ore silos across all mining systems.

    Tracks per-system silos and global capacity upgrades.
    """

    def __init__(self) -> None:
        self._silos: dict[str, OreSilo] = {}
        self.capacity_bonus: int = 0

    def get_silo(self, system_id: str) -> OreSilo:
        """Get or create the silo for a system.

        Args:
            system_id: Mining system ID.

        Returns:
            The OreSilo for this system.
        """
        if system_id not in self._silos:
            self._silos[system_id] = OreSilo(
                system_id=system_id,
                capacity=BASE_SILO_CAPACITY + self.capacity_bonus,
            )
        return self._silos[system_id]

    def upgrade_all_capacity(self, additional: int) -> None:
        """Increase capacity for all silos (existing and future).

        Args:
            additional: Extra capacity to add on top of current bonus.
        """
        self.capacity_bonus += additional
        for silo in self._silos.values():
            silo.capacity = BASE_SILO_CAPACITY + self.capacity_bonus

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "capacity_bonus": self.capacity_bonus,
            "silos": {sid: silo.to_dict() for sid, silo in self._silos.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OreSiloManager:
        """Deserialize from dictionary."""
        mgr = cls()
        mgr.capacity_bonus = data.get("capacity_bonus", 0)
        for sid, silo_data in data.get("silos", {}).items():
            mgr._silos[sid] = OreSilo.from_dict(silo_data)
        return mgr
