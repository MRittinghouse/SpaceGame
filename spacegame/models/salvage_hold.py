"""Salvage Hold model — per-system salvage storage buffer for extended salvage sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


BASE_HOLD_CAPACITY = 100


@dataclass
class SalvageHold:
    """Per-system salvage storage buffer that decouples salvage from ship cargo.

    Salvaged items go into the hold first. On exiting the salvage view,
    the player transfers hold contents into ship cargo (limited by
    available cargo space). Remainder stays for next visit.
    """

    system_id: str
    capacity: int = BASE_HOLD_CAPACITY
    contents: dict[str, int] = field(default_factory=dict)

    def get_total_stored(self) -> int:
        """Get total units stored across all types."""
        return sum(self.contents.values())

    def get_available_space(self) -> int:
        """Get remaining capacity."""
        return max(0, self.capacity - self.get_total_stored())

    def is_full(self) -> bool:
        """Check if the hold has no remaining capacity."""
        return self.get_total_stored() >= self.capacity

    def add_salvage(self, commodity_id: str, quantity: int) -> int:
        """Add salvage to the hold, capped at capacity.

        Args:
            commodity_id: Type of salvage to add.
            quantity: Amount to add.

        Returns:
            Actual amount added (may be less if hold is nearly full).
        """
        space = self.get_available_space()
        actual = min(quantity, space)
        if actual > 0:
            self.contents[commodity_id] = self.contents.get(commodity_id, 0) + actual
        return actual

    def remove_salvage(self, commodity_id: str, quantity: int) -> int:
        """Remove salvage from the hold.

        Args:
            commodity_id: Type of salvage to remove.
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
    def from_dict(cls, data: dict[str, Any]) -> SalvageHold:
        """Deserialize from dictionary."""
        return cls(
            system_id=data["system_id"],
            capacity=data.get("capacity", BASE_HOLD_CAPACITY),
            contents=dict(data.get("contents", {})),
        )


class SalvageHoldManager:
    """Manages salvage holds across all systems.

    Tracks per-system holds and global capacity upgrades.
    """

    def __init__(self) -> None:
        self._holds: dict[str, SalvageHold] = {}
        self.capacity_bonus: int = 0

    def get_hold(self, system_id: str) -> SalvageHold:
        """Get or create the hold for a system.

        Args:
            system_id: System ID.

        Returns:
            The SalvageHold for this system.
        """
        if system_id not in self._holds:
            self._holds[system_id] = SalvageHold(
                system_id=system_id,
                capacity=BASE_HOLD_CAPACITY + self.capacity_bonus,
            )
        return self._holds[system_id]

    def upgrade_all_capacity(self, additional: int) -> None:
        """Increase capacity for all holds (existing and future).

        Args:
            additional: Extra capacity to add on top of current bonus.
        """
        self.capacity_bonus += additional
        for hold in self._holds.values():
            hold.capacity = BASE_HOLD_CAPACITY + self.capacity_bonus

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "capacity_bonus": self.capacity_bonus,
            "holds": {sid: hold.to_dict() for sid, hold in self._holds.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SalvageHoldManager:
        """Deserialize from dictionary."""
        mgr = cls()
        mgr.capacity_bonus = data.get("capacity_bonus", 0)
        for sid, hold_data in data.get("holds", {}).items():
            mgr._holds[sid] = SalvageHold.from_dict(hold_data)
        return mgr
