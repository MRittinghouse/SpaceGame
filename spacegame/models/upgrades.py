"""
Ship upgrade system.

Post-U5 (Legacy Retirement): installable capacity is determined by
modules/slots on the ShipBuild, not by per-category slot pools on
this manager. ShipUpgradeManager is now a pure inventory + bonus
aggregator. It still tracks per-upgrade enhancement state (mark and
tuning) and still produces combat moves for the legacy ShipType
combat path.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Mark multipliers applied to base bonus_value
MARK_MULTIPLIERS: dict[int, float] = {1: 1.0, 2: 1.25, 3: 1.50}


@dataclass
class InstalledUpgrade:
    """Per-instance enhancement state for an installed upgrade."""

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
    bonus_type: str
    bonus_value: float
    combat_move: Optional[dict[str, Any]] = None
    requires_black_market: bool = False
    max_mark: int = 3
    tuning_options: list[dict[str, Any]] = field(default_factory=list)
    faction_required: Optional[str] = None
    faction_rep_required: int = 0
    unlock_condition: Optional[str] = None
    tier: int = 1
    available_systems: list[str] = field(default_factory=list)

    def can_afford(self, credits: int) -> bool:
        return credits >= self.price

    def get_tuning_option(self, tuning_id: str) -> Optional[dict[str, Any]]:
        for opt in self.tuning_options:
            if opt["id"] == tuning_id:
                return opt
        return None


# Maps slot_type values to display categories. Used for UI grouping only —
# capacity gating has moved to ShipBuild modules.
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
    """Tracks installed upgrades, their enhancement state, and aggregate bonuses.

    Capacity is NOT enforced here — the ShipBuild's placed modules/slots
    determine how many weapons, defenses, and utilities a ship can support.
    This manager only prevents duplicate installations of the same upgrade.
    """

    def __init__(self) -> None:
        self.installed: List[ShipUpgrade] = []
        self._enhancement: dict[str, InstalledUpgrade] = {}

    def get_category(self, slot_type: str) -> str:
        """Map a slot_type to its display category (weapon/defense/utility)."""
        return SLOT_CATEGORIES.get(slot_type, "utility")

    def can_install(self, upgrade: ShipUpgrade) -> bool:
        """True unless this exact upgrade is already installed."""
        return not any(u.id == upgrade.id for u in self.installed)

    def install(self, upgrade: ShipUpgrade) -> Tuple[bool, str]:
        """Install an upgrade.

        Args:
            upgrade: The upgrade to install.

        Returns:
            Tuple of (success, message). Fails only on duplicate install.
        """
        if any(u.id == upgrade.id for u in self.installed):
            return (False, "Upgrade already installed")
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

        if mark <= inst.mark:
            return (False, f"Already at Mk{inst.mark} or higher")
        if mark != inst.mark + 1:
            return (False, f"Must enhance to Mk{inst.mark + 1} first")
        if mark > upgrade.max_mark:
            return (False, f"Maximum mark for this upgrade is Mk{upgrade.max_mark}")

        if tuning is not None:
            if upgrade.get_tuning_option(tuning) is None:
                return (False, f"Invalid tuning option: {tuning}")

        inst.mark = mark
        if tuning is not None:
            inst.tuning = tuning

        return (True, f"Enhanced {upgrade.name} to Mk{mark}")

    def get_installed(self, upgrade_id: str) -> Optional[InstalledUpgrade]:
        """Get the InstalledUpgrade state for an upgrade, or None if not installed."""
        return self._enhancement.get(upgrade_id)

    def get_bonus(self, bonus_type: str) -> float:
        """Total bonus of a given type from all installed upgrades.

        Applies mark multipliers and tuning bonuses.
        """
        total = 0.0
        for u in self.installed:
            inst = self._enhancement.get(u.id)
            mark = inst.mark if inst else 1
            multiplier = MARK_MULTIPLIERS.get(mark, 1.0)

            if u.bonus_type == bonus_type:
                total += u.bonus_value * multiplier

            if inst and inst.tuning:
                tuning_opt = u.get_tuning_option(inst.tuning)
                if tuning_opt and tuning_opt["bonus_type"] == bonus_type:
                    tuning_value = tuning_opt["bonus_value"]
                    if mark >= 3:
                        tuning_value *= 2.0
                    total += tuning_value

        return total

    def get_combat_moves(self) -> list:
        """CombatMove objects for all installed upgrades with combat moves."""
        from spacegame.models.combat import CombatMove

        moves = []
        for u in self.installed:
            if u.combat_move:
                moves.append(CombatMove.from_dict(u.combat_move))
        return moves

    def has_upgrade(self, upgrade_id: str) -> bool:
        return any(u.id == upgrade_id for u in self.installed)

    def get_installed_ids(self) -> List[str]:
        return [u.id for u in self.installed]

    def to_dict(self) -> dict:
        """Serialize. Slot-count fields from pre-U5 saves are intentionally omitted."""
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
            "installed_ids": self.get_installed_ids(),
            "installed": installed_list,
        }

    @classmethod
    def from_dict(cls, data: dict, all_upgrades: Dict[str, ShipUpgrade]) -> "ShipUpgradeManager":
        """Deserialize from dict.

        Silently ignores legacy slot-count fields (``max_slots``,
        ``weapon_slots``, ``defense_slots``, ``utility_slots``) for
        backward compat with pre-U5 saves.
        """
        manager = cls()

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
            # Ancient save format: installed_ids only, all at Mk1
            for upgrade_id in data.get("installed_ids", []):
                if upgrade_id in all_upgrades:
                    upgrade = all_upgrades[upgrade_id]
                    manager.installed.append(upgrade)
                    manager._enhancement[upgrade_id] = InstalledUpgrade(
                        upgrade_id=upgrade_id,
                    )

        return manager
