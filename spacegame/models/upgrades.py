"""
Ship upgrade system.

Purchasable component upgrades with slot limits and bonus application.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ShipUpgrade:
    """A ship component upgrade."""

    id: str
    name: str
    description: str
    price: int
    slot_type: str  # e.g., "cargo", "fuel", "engine", "mining", "scanner", "weapon", "defense"
    bonus_type: str  # Key for applying bonus
    bonus_value: float  # Value of the bonus
    combat_move: Optional[dict[str, Any]] = None  # Raw dict, parsed to CombatMove by data_loader
    requires_black_market: bool = False  # Only visible at black market locations

    def can_afford(self, credits: int) -> bool:
        return credits >= self.price


# Maps slot_type values to slot categories
SLOT_CATEGORIES: dict[str, str] = {
    "cargo": "utility",
    "fuel": "utility",
    "engine": "utility",
    "mining": "utility",
    "scanner": "utility",
    "smuggling": "utility",
    "weapon": "weapon",
    "defense": "defense",
}


class ShipUpgradeManager:
    """Manages installed ship upgrades with per-category slot limits.

    Ships have separate slot pools for weapons, defenses, and utility upgrades.
    """

    def __init__(
        self,
        weapon_slots: int = 0,
        defense_slots: int = 0,
        utility_slots: int = 3,
        *,
        max_slots: Optional[int] = None,
    ):
        if max_slots is not None:
            # Backward compat: max_slots maps to utility_slots
            utility_slots = max_slots
            weapon_slots = 0
            defense_slots = 0
        self._weapon_slots = weapon_slots
        self._defense_slots = defense_slots
        self._utility_slots = utility_slots
        self.installed: List[ShipUpgrade] = []

    @property
    def max_slots(self) -> int:
        """Total slots across all categories."""
        return self._weapon_slots + self._defense_slots + self._utility_slots

    @property
    def slots_used(self) -> int:
        return len(self.installed)

    @property
    def slots_available(self) -> int:
        return self.max_slots - self.slots_used

    def get_category(self, slot_type: str) -> str:
        """Map a slot_type to its category (weapon/defense/utility)."""
        return SLOT_CATEGORIES.get(slot_type, "utility")

    def get_category_limit(self, category: str) -> int:
        """Get the slot limit for a category."""
        if category == "weapon":
            return self._weapon_slots
        elif category == "defense":
            return self._defense_slots
        return self._utility_slots

    def get_category_used(self, category: str) -> int:
        """Get slots used in a category."""
        return sum(
            1 for u in self.installed if self.get_category(u.slot_type) == category
        )

    def get_category_available(self, category: str) -> int:
        """Get available slots in a category."""
        return self.get_category_limit(category) - self.get_category_used(category)

    def can_install(self, upgrade: ShipUpgrade) -> bool:
        """Check if upgrade can be installed (has category slot space, not duplicate)."""
        category = self.get_category(upgrade.slot_type)
        if self.get_category_available(category) <= 0:
            return False
        if any(u.id == upgrade.id for u in self.installed):
            return False
        return True

    def install(
        self, upgrade: ShipUpgrade, force: bool = False
    ) -> Tuple[bool, str]:
        """Install an upgrade.

        Args:
            upgrade: The upgrade to install.
            force: If True, bypass slot checks (used for save loading).

        Returns:
            Tuple of (success, message).
        """
        if not force:
            if any(u.id == upgrade.id for u in self.installed):
                return (False, "Upgrade already installed")
            category = self.get_category(upgrade.slot_type)
            if self.get_category_available(category) <= 0:
                return (False, f"No {category} slots available")

        self.installed.append(upgrade)
        return (True, f"Installed: {upgrade.name}")

    def uninstall(self, upgrade_id: str) -> Tuple[bool, str]:
        """Remove an installed upgrade.

        Returns:
            Tuple of (success, message).
        """
        for i, upgrade in enumerate(self.installed):
            if upgrade.id == upgrade_id:
                self.installed.pop(i)
                return (True, f"Removed: {upgrade.name}")
        return (False, "Upgrade not installed")

    def get_bonus(self, bonus_type: str) -> float:
        """Get total bonus of a given type from all installed upgrades."""
        return sum(u.bonus_value for u in self.installed if u.bonus_type == bonus_type)

    def get_combat_moves(self) -> list:
        """Get CombatMove objects for all installed upgrades with combat moves.

        Returns:
            List of CombatMove instances parsed from upgrade combat_move dicts.
        """
        from spacegame.models.combat import CombatMove

        moves = []
        for u in self.installed:
            if u.combat_move:
                moves.append(CombatMove.from_dict(u.combat_move))
        return moves

    def has_upgrade(self, upgrade_id: str) -> bool:
        """Check if a specific upgrade is installed.

        Args:
            upgrade_id: ID of the upgrade to check.

        Returns:
            True if the upgrade is currently installed.
        """
        return any(u.id == upgrade_id for u in self.installed)

    def get_installed_ids(self) -> List[str]:
        """Get list of installed upgrade IDs for serialization."""
        return [u.id for u in self.installed]

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "max_slots": self.max_slots,
            "weapon_slots": self._weapon_slots,
            "defense_slots": self._defense_slots,
            "utility_slots": self._utility_slots,
            "installed_ids": self.get_installed_ids(),
        }

    @classmethod
    def from_dict(cls, data: dict, all_upgrades: Dict[str, ShipUpgrade]) -> "ShipUpgradeManager":
        """Deserialize from dict.

        Supports both old format (max_slots only) and new format
        (weapon_slots/defense_slots/utility_slots).
        """
        if "weapon_slots" in data:
            manager = cls(
                weapon_slots=data.get("weapon_slots", 0),
                defense_slots=data.get("defense_slots", 0),
                utility_slots=data.get("utility_slots", 3),
            )
        else:
            # Old format: max_slots maps to utility_slots
            manager = cls(max_slots=data.get("max_slots", 3))
        for upgrade_id in data.get("installed_ids", []):
            if upgrade_id in all_upgrades:
                manager.installed.append(all_upgrades[upgrade_id])
        return manager
