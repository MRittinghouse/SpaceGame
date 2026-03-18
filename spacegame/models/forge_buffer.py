"""Forge Buffer model — per-system output storage for refined commodities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


BASE_FORGE_BUFFER_CAPACITY = 50


@dataclass
class ForgeBuffer:
    """Per-system output buffer that stores refined commodities.

    Refined goods go into the forge buffer first. The player can then
    transfer buffer contents into ship cargo (limited by available
    cargo space). Remainder stays for next visit.
    """

    system_id: str
    capacity: int = BASE_FORGE_BUFFER_CAPACITY
    contents: dict[str, int] = field(default_factory=dict)

    def get_total_stored(self) -> int:
        """Get total units stored across all commodity types."""
        return sum(self.contents.values())

    def available_space(self) -> int:
        """Get remaining capacity."""
        return max(0, self.capacity - self.get_total_stored())

    def is_full(self) -> bool:
        """Check if the buffer has no remaining capacity."""
        return self.get_total_stored() >= self.capacity

    def add_output(self, commodity_id: str, quantity: int) -> int:
        """Add refined output to the buffer, capped at capacity.

        Args:
            commodity_id: Type of commodity to add.
            quantity: Amount to add.

        Returns:
            Actual amount added (may be less if buffer is nearly full).
        """
        space = self.available_space()
        actual = min(quantity, space)
        if actual > 0:
            self.contents[commodity_id] = self.contents.get(commodity_id, 0) + actual
        return actual

    def remove_output(self, commodity_id: str, quantity: int) -> int:
        """Remove output from the buffer.

        Args:
            commodity_id: Type of commodity to remove.
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
    def from_dict(cls, data: dict[str, Any]) -> ForgeBuffer:
        """Deserialize from dictionary."""
        return cls(
            system_id=data["system_id"],
            capacity=data.get("capacity", BASE_FORGE_BUFFER_CAPACITY),
            contents=dict(data.get("contents", {})),
        )


class ForgeBufferManager:
    """Manages forge buffers across all systems.

    Tracks per-system buffers and global capacity upgrades.
    """

    def __init__(self) -> None:
        self._buffers: dict[str, ForgeBuffer] = {}
        self.capacity_bonus: int = 0

    def get_buffer(self, system_id: str) -> ForgeBuffer:
        """Get or create the buffer for a system.

        Args:
            system_id: System ID.

        Returns:
            The ForgeBuffer for this system.
        """
        if system_id not in self._buffers:
            self._buffers[system_id] = ForgeBuffer(
                system_id=system_id,
                capacity=BASE_FORGE_BUFFER_CAPACITY + self.capacity_bonus,
            )
        return self._buffers[system_id]

    def upgrade_all_capacity(self, amount: int) -> None:
        """Increase capacity for all buffers (existing and future).

        Args:
            amount: Extra capacity to add on top of current bonus.
        """
        self.capacity_bonus += amount
        for buf in self._buffers.values():
            buf.capacity = BASE_FORGE_BUFFER_CAPACITY + self.capacity_bonus

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "capacity_bonus": self.capacity_bonus,
            "buffers": {sid: buf.to_dict() for sid, buf in self._buffers.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForgeBufferManager:
        """Deserialize from dictionary."""
        mgr = cls()
        mgr.capacity_bonus = data.get("capacity_bonus", 0)
        for sid, buf_data in data.get("buffers", {}).items():
            mgr._buffers[sid] = ForgeBuffer.from_dict(buf_data)
        return mgr
