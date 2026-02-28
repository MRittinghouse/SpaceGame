"""
Ship upgrade system.

Purchasable component upgrades with slot limits and bonus application.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ShipUpgrade:
    """A ship component upgrade."""

    id: str
    name: str
    description: str
    price: int
    slot_type: str  # e.g., "cargo", "fuel", "engine", "mining", "scanner"
    bonus_type: str  # Key for applying bonus
    bonus_value: float  # Value of the bonus

    def can_afford(self, credits: int) -> bool:
        return credits >= self.price


class ShipUpgradeManager:
    """
    Manages installed ship upgrades.

    Ships have a limited number of upgrade slots (default 3).
    """

    def __init__(self, max_slots: int = 3):
        self.max_slots = max_slots
        self.installed: List[ShipUpgrade] = []

    @property
    def slots_used(self) -> int:
        return len(self.installed)

    @property
    def slots_available(self) -> int:
        return self.max_slots - self.slots_used

    def can_install(self, upgrade: ShipUpgrade) -> bool:
        """Check if upgrade can be installed (has slot space, not duplicate)."""
        if self.slots_available <= 0:
            return False
        # Prevent duplicate upgrades
        if any(u.id == upgrade.id for u in self.installed):
            return False
        return True

    def install(self, upgrade: ShipUpgrade) -> Tuple[bool, str]:
        """
        Install an upgrade.

        Returns:
            Tuple of (success, message)
        """
        if not self.can_install(upgrade):
            if self.slots_available <= 0:
                return (False, "No upgrade slots available")
            if any(u.id == upgrade.id for u in self.installed):
                return (False, "Upgrade already installed")
            return (False, "Cannot install upgrade")

        self.installed.append(upgrade)
        return (True, f"Installed: {upgrade.name}")

    def uninstall(self, upgrade_id: str) -> Tuple[bool, str]:
        """
        Remove an installed upgrade.

        Returns:
            Tuple of (success, message)
        """
        for i, upgrade in enumerate(self.installed):
            if upgrade.id == upgrade_id:
                self.installed.pop(i)
                return (True, f"Removed: {upgrade.name}")
        return (False, "Upgrade not installed")

    def get_bonus(self, bonus_type: str) -> float:
        """Get total bonus of a given type from all installed upgrades."""
        return sum(u.bonus_value for u in self.installed if u.bonus_type == bonus_type)

    def get_installed_ids(self) -> List[str]:
        """Get list of installed upgrade IDs for serialization."""
        return [u.id for u in self.installed]

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "max_slots": self.max_slots,
            "installed_ids": self.get_installed_ids(),
        }

    @classmethod
    def from_dict(cls, data: dict, all_upgrades: Dict[str, ShipUpgrade]) -> "ShipUpgradeManager":
        """Deserialize from dict."""
        manager = cls(max_slots=data.get("max_slots", 3))
        for upgrade_id in data.get("installed_ids", []):
            if upgrade_id in all_upgrades:
                manager.installed.append(all_upgrades[upgrade_id])
        return manager
