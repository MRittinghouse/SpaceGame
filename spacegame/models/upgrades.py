"""
Ship upgrade system.

Purchasable component upgrades with slot limits, bonus application,
and an enhancement system (Mk1 → Mk2 → Mk3) with tuning specialization.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Mark multipliers applied to base bonus_value
MARK_MULTIPLIERS: dict[int, float] = {1: 1.0, 2: 1.25, 3: 1.50}


@dataclass
class InstalledUpgrade:
    """Per-instance enhancement state for an installed upgrade.

    Tracks the upgrade's current mark level and tuning specialization.
    """

    upgrade_id: str
    mark: int = 1
    tuning: Optional[str] = None


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
    max_mark: int = 3  # Maximum enhancement level (1-3)
    tuning_options: list[dict[str, Any]] = field(default_factory=list)
    faction_required: Optional[str] = None  # Faction ID required to purchase
    faction_rep_required: int = 0  # Minimum faction reputation required
    unlock_condition: Optional[str] = None  # Quest or condition ID required
    tier: int = 1  # 1=starter, 2=mid-game, 3=late-game/specialized
    available_systems: list[str] = field(default_factory=list)  # Empty = everywhere

    def can_afford(self, credits: int) -> bool:
        return credits >= self.price

    def get_tuning_option(self, tuning_id: str) -> Optional[dict[str, Any]]:
        """Find a tuning option by ID."""
        for opt in self.tuning_options:
            if opt["id"] == tuning_id:
                return opt
        return None


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
    Each installed upgrade tracks per-instance enhancement state (mark + tuning).
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
        self._enhancement: dict[str, InstalledUpgrade] = {}

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
        self._enhancement[upgrade.id] = InstalledUpgrade(upgrade_id=upgrade.id)
        return (True, f"Installed: {upgrade.name}")

    def uninstall(self, upgrade_id: str) -> Tuple[bool, str]:
        """Remove an installed upgrade.

        Returns:
            Tuple of (success, message).
        """
        for i, upgrade in enumerate(self.installed):
            if upgrade.id == upgrade_id:
                self.installed.pop(i)
                self._enhancement.pop(upgrade_id, None)
                return (True, f"Removed: {upgrade.name}")
        return (False, "Upgrade not installed")

    def enhance(
        self,
        upgrade_id: str,
        mark: int,
        tuning: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Enhance an installed upgrade to a higher mark level.

        Args:
            upgrade_id: ID of the installed upgrade.
            mark: Target mark level (2 or 3).
            tuning: Tuning specialization ID (required at Mk2 if options exist).

        Returns:
            Tuple of (success, message).
        """
        # Find the upgrade
        upgrade = None
        for u in self.installed:
            if u.id == upgrade_id:
                upgrade = u
                break
        if upgrade is None:
            return (False, "Upgrade not installed")

        inst = self._enhancement.get(upgrade_id)
        if inst is None:
            return (False, "Upgrade not installed")

        # Validate mark progression
        if mark <= inst.mark:
            return (False, f"Already at Mk{inst.mark} or higher")
        if mark != inst.mark + 1:
            return (False, f"Must enhance to Mk{inst.mark + 1} first")
        if mark > upgrade.max_mark:
            return (False, f"Maximum mark for this upgrade is Mk{upgrade.max_mark}")

        # Validate tuning
        if tuning is not None:
            if upgrade.get_tuning_option(tuning) is None:
                return (False, f"Invalid tuning option: {tuning}")

        # Apply enhancement
        inst.mark = mark
        if tuning is not None:
            inst.tuning = tuning

        return (True, f"Enhanced {upgrade.name} to Mk{mark}")

    def get_installed(self, upgrade_id: str) -> Optional[InstalledUpgrade]:
        """Get the InstalledUpgrade state for an upgrade.

        Args:
            upgrade_id: ID of the upgrade.

        Returns:
            InstalledUpgrade instance or None if not installed.
        """
        return self._enhancement.get(upgrade_id)

    def get_bonus(self, bonus_type: str) -> float:
        """Get total bonus of a given type from all installed upgrades.

        Applies mark multipliers and tuning bonuses.
        """
        total = 0.0
        for u in self.installed:
            inst = self._enhancement.get(u.id)
            mark = inst.mark if inst else 1
            multiplier = MARK_MULTIPLIERS.get(mark, 1.0)

            # Base bonus scaled by mark
            if u.bonus_type == bonus_type:
                total += u.bonus_value * multiplier

            # Tuning bonus
            if inst and inst.tuning:
                tuning_opt = u.get_tuning_option(inst.tuning)
                if tuning_opt and tuning_opt["bonus_type"] == bonus_type:
                    tuning_value = tuning_opt["bonus_value"]
                    # Tuning doubles at Mk3
                    if mark >= 3:
                        tuning_value *= 2.0
                    total += tuning_value

        return total

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
        installed_list = []
        for u in self.installed:
            inst = self._enhancement.get(u.id)
            entry: dict[str, Any] = {"upgrade_id": u.id}
            if inst:
                entry["mark"] = inst.mark
                entry["tuning"] = inst.tuning
            else:
                entry["mark"] = 1
                entry["tuning"] = None
            installed_list.append(entry)

        return {
            "max_slots": self.max_slots,
            "weapon_slots": self._weapon_slots,
            "defense_slots": self._defense_slots,
            "utility_slots": self._utility_slots,
            "installed_ids": self.get_installed_ids(),
            "installed": installed_list,
        }

    @classmethod
    def from_dict(cls, data: dict, all_upgrades: Dict[str, ShipUpgrade]) -> "ShipUpgradeManager":
        """Deserialize from dict.

        Supports both old format (installed_ids only) and new format
        (installed list with mark/tuning).
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

        # New format: installed list with enhancement state
        if "installed" in data:
            for entry in data["installed"]:
                upgrade_id = entry["upgrade_id"]
                if upgrade_id in all_upgrades:
                    upgrade = all_upgrades[upgrade_id]
                    manager.installed.append(upgrade)
                    manager._enhancement[upgrade_id] = InstalledUpgrade(
                        upgrade_id=upgrade_id,
                        mark=entry.get("mark", 1),
                        tuning=entry.get("tuning"),
                    )
        else:
            # Old format: installed_ids only, all at Mk1
            for upgrade_id in data.get("installed_ids", []):
                if upgrade_id in all_upgrades:
                    upgrade = all_upgrades[upgrade_id]
                    manager.installed.append(upgrade)
                    manager._enhancement[upgrade_id] = InstalledUpgrade(
                        upgrade_id=upgrade_id,
                    )

        return manager
