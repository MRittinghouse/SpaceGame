"""
Crew system models.

Defines crew abilities, templates, and the CrewRoster manager that tracks
recruitment, leveling, loyalty, and passive bonuses.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class LoyaltyTier(Enum):
    """Loyalty tier that determines gameplay effects."""

    DISCONTENTED = "discontented"  # 0-9: departure risk
    WARY = "wary"                  # 10-29: no bonuses
    NEUTRAL = "neutral"            # 30-49: starting range
    WARM = "warm"                  # 50-69: quest stage 1
    LOYAL = "loyal"                # 70-84: +25% bonuses, quest stage 2
    DEVOTED = "devoted"            # 85-100: +50% bonuses, quest stage 3


# Thresholds that generate quest-gating flags when crossed upward
_LOYALTY_FLAG_THRESHOLDS = [50, 70, 85]


def _loyalty_value_to_tier(loyalty: int) -> LoyaltyTier:
    """Convert a raw loyalty value to its tier.

    Args:
        loyalty: Loyalty value (0-100).

    Returns:
        Corresponding LoyaltyTier.
    """
    if loyalty < 10:
        return LoyaltyTier.DISCONTENTED
    if loyalty < 30:
        return LoyaltyTier.WARY
    if loyalty < 50:
        return LoyaltyTier.NEUTRAL
    if loyalty < 70:
        return LoyaltyTier.WARM
    if loyalty < 85:
        return LoyaltyTier.LOYAL
    return LoyaltyTier.DEVOTED


@dataclass
class CrewAbility:
    """A passive bonus provided by a crew member at a given level."""

    bonus_type: str
    bonus_value: float
    description: str
    unlock_level: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "bonus_type": self.bonus_type,
            "bonus_value": self.bonus_value,
            "description": self.description,
            "unlock_level": self.unlock_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrewAbility":
        """Deserialize from dict."""
        return cls(
            bonus_type=data["bonus_type"],
            bonus_value=data["bonus_value"],
            description=data["description"],
            unlock_level=data.get("unlock_level", 1),
        )


@dataclass
class CrewTemplate:
    """Immutable crew member definition loaded from JSON data."""

    id: str
    name: str
    role: str
    description: str
    portrait_color: list[int]
    abilities: list[CrewAbility] = field(default_factory=list)
    max_level: int = 5
    xp_thresholds: list[int] = field(default_factory=lambda: [0, 50, 150, 350, 700])
    base_attributes: dict[str, int] = field(
        default_factory=lambda: {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 1}
    )
    faction_id: str = ""
    home_system_id: str = ""
    combat_move: Optional[dict[str, Any]] = None  # Raw dict, parsed to CombatMove by data_loader
    combat_moves: list[dict[str, Any]] = field(default_factory=list)  # Multiple combat moves (new)
    is_companion: bool = False

    def get_abilities_at_level(self, level: int) -> list[CrewAbility]:
        """Get all abilities unlocked at or below the given level."""
        return [a for a in self.abilities if a.unlock_level <= level]

    def get_bonus_at_level(self, bonus_type: str, level: int) -> float:
        """Get total bonus of a given type at a given level."""
        return sum(
            a.bonus_value
            for a in self.abilities
            if a.bonus_type == bonus_type and a.unlock_level <= level
        )


class CrewRoster:
    """Manages recruited crew: recruitment, bonuses, XP, loyalty.

    Holds crew templates (from DataLoader) as immutable references.
    Tracks runtime state (recruited IDs, per-member level/xp/loyalty) separately.
    """

    def __init__(self, templates: dict[str, "CrewTemplate"]) -> None:
        """Initialize with crew template definitions.

        Args:
            templates: All crew templates from data loader.
        """
        self._templates: dict[str, CrewTemplate] = dict(templates)
        self._recruited: list[str] = []
        self._state: dict[str, dict[str, Any]] = {}
        self._dismissed: dict[str, dict[str, Any]] = {}
        self._pending_companions: set[str] = set()

    @property
    def recruited_ids(self) -> set[str]:
        """Get set of currently recruited crew member template IDs."""
        return set(self._recruited)

    @property
    def pending_companion_ids(self) -> set[str]:
        """Get set of companion IDs awaiting recruitment (crew was full)."""
        return set(self._pending_companions)

    def add_pending_companion(self, template_id: str) -> bool:
        """Mark a companion as pending recruitment (mission reward fired but crew was full).

        Args:
            template_id: Template ID of the companion.

        Returns:
            True if added, False if template not found or not a companion.
        """
        template = self._templates.get(template_id)
        if not template or not template.is_companion:
            return False
        self._pending_companions.add(template_id)
        return True

    def recruit(self, template_id: str, crew_slots: int) -> tuple[bool, str]:
        """Recruit a crew member, restoring preserved state if previously dismissed.

        Args:
            template_id: Template ID of crew member to recruit.
            crew_slots: Maximum crew slots on current ship.

        Returns:
            Tuple of (success, message).
        """
        if template_id not in self._templates:
            return (False, f"Crew member not found: {template_id}")
        if template_id in self._recruited:
            return (False, f"{self._templates[template_id].name} is already recruited")
        if len(self._recruited) >= crew_slots:
            return (False, "No crew slots available")

        template = self._templates[template_id]
        self._recruited.append(template_id)

        if template_id in self._dismissed:
            # Restore preserved state from dismissal
            state = dict(self._dismissed.pop(template_id))
            state.pop("departed", None)
            state.pop("location", None)
            self._state[template_id] = state
        else:
            # Fresh recruit
            self._state[template_id] = {
                "level": 1,
                "xp": 0,
                "loyalty": 30,
                "attributes": dict(template.base_attributes),
                "attribute_points": 0,
            }
        self._pending_companions.discard(template_id)
        return (True, template.name)

    def dismiss(self, template_id: str) -> tuple[bool, str]:
        """Dismiss a crew member, preserving their state for re-recruitment.

        Args:
            template_id: Template ID of crew member to dismiss.

        Returns:
            Tuple of (success, message).
        """
        if template_id not in self._recruited:
            return (False, f"Crew member not in roster: {template_id}")

        template = self._templates[template_id]
        state = dict(self._state[template_id])
        state["departed"] = False
        state["location"] = template.home_system_id
        self._dismissed[template_id] = state

        self._recruited.remove(template_id)
        del self._state[template_id]
        return (True, f"{template.name} has been dismissed")

    def get_member_state(self, template_id: str) -> Optional[dict[str, Any]]:
        """Get runtime state for a recruited crew member."""
        return self._state.get(template_id)

    def get_template(self, template_id: str) -> Optional["CrewTemplate"]:
        """Get a crew template by ID."""
        return self._templates.get(template_id)

    def get_recruited_members(self) -> list[tuple["CrewTemplate", dict[str, Any]]]:
        """Get all recruited crew as (template, state) pairs."""
        result = []
        for tid in self._recruited:
            template = self._templates.get(tid)
            state = self._state.get(tid)
            if template and state:
                result.append((template, state))
        return result

    def add_bonus_ability(
        self, template_id: str, ability: CrewAbility
    ) -> tuple[bool, str]:
        """Add a permanent bonus ability to a crew member.

        Args:
            template_id: Crew member to modify.
            ability: The ability to add.

        Returns:
            Tuple of (success, message).
        """
        state = self._state.get(template_id)
        if not state:
            return (False, "Crew member not recruited")

        bonus_abilities = state.get("bonus_abilities", [])
        # Check for duplicate by description
        for existing in bonus_abilities:
            if existing.get("description") == ability.description:
                return (False, f"Already has ability: {ability.description}")

        bonus_abilities.append(ability.to_dict())
        state["bonus_abilities"] = bonus_abilities
        template = self._templates.get(template_id)
        name = template.name if template else template_id
        return (True, f"{name} gained {ability.description}")

    def get_bonus(self, bonus_type: str) -> float:
        """Get total bonus of a given type from all recruited crew.

        Applies loyalty-based multipliers: 1.25x at Loyal tier, 1.5x at Devoted.
        Includes permanent bonus abilities.

        Args:
            bonus_type: The bonus type to sum (e.g., "fuel_efficiency_bonus").

        Returns:
            Total bonus value.
        """
        total = 0.0
        for tid in self._recruited:
            template = self._templates.get(tid)
            state = self._state.get(tid)
            if template and state:
                base = template.get_bonus_at_level(bonus_type, state["level"])
                # Add bonus abilities
                for ability_dict in state.get("bonus_abilities", []):
                    if ability_dict.get("bonus_type") == bonus_type:
                        base += ability_dict.get("bonus_value", 0.0)
                # Crew get flat bonuses; only companions scale with loyalty
                multiplier = self.get_loyalty_multiplier(tid) if template.is_companion else 1.0
                total += base * multiplier
        return total

    def get_member_attributes(self, template_id: str) -> dict[str, int]:
        """Get attribute values for a recruited crew member.

        Args:
            template_id: Crew member to query.

        Returns:
            Dict of attribute ID → value, or empty dict if not recruited.
        """
        state = self._state.get(template_id)
        if not state:
            return {}
        return dict(state.get("attributes", {}))

    def get_member_attribute_points(self, template_id: str) -> int:
        """Get unspent attribute points for a crew member.

        Args:
            template_id: Crew member to query.

        Returns:
            Unspent attribute points, or 0 if not recruited.
        """
        state = self._state.get(template_id)
        if not state:
            return 0
        return state.get("attribute_points", 0)

    def allocate_crew_attribute(
        self, template_id: str, attr_id: str
    ) -> tuple[bool, str]:
        """Allocate an attribute point for a crew member.

        Args:
            template_id: Crew member to modify.
            attr_id: Attribute to increase.

        Returns:
            Tuple of (success, message).
        """
        state = self._state.get(template_id)
        if not state:
            return (False, "Crew member not recruited")

        # Crew (non-companions) cannot allocate attribute points
        template = self._templates.get(template_id)
        if template and not template.is_companion:
            return (False, "Crew members cannot allocate attribute points")

        attrs = state.get("attributes", {})
        if attr_id not in attrs:
            return (False, f"Unknown attribute: {attr_id}")

        points = state.get("attribute_points", 0)
        if points <= 0:
            return (False, "No attribute points available")

        from spacegame.models.attributes import ATTRIBUTE_MAX

        if attrs[attr_id] >= ATTRIBUTE_MAX:
            return (False, "Attribute already at maximum")

        attrs[attr_id] += 1
        state["attribute_points"] = points - 1
        template = self._templates.get(template_id)
        name = template.name if template else template_id
        return (True, f"{name}: attribute increased")

    def add_xp_to_all(self, amount: int) -> list[str]:
        """Add XP to all recruited crew members.

        Args:
            amount: XP to add to each member.

        Returns:
            List of level-up messages.
        """
        messages: list[str] = []
        for tid in self._recruited:
            template = self._templates.get(tid)
            state = self._state.get(tid)
            if not template or not state:
                continue

            # Crew (max_level=1) don't gain XP
            if template.max_level <= 1:
                continue

            state["xp"] += amount
            # Check for level ups
            while state["level"] < template.max_level:
                next_level = state["level"]  # 0-indexed into thresholds
                if (
                    next_level < len(template.xp_thresholds)
                    and state["xp"] >= template.xp_thresholds[next_level]
                ):
                    state["level"] += 1
                    # Award +1 attribute point on level-up
                    state["attribute_points"] = state.get("attribute_points", 0) + 1
                    messages.append(f"{template.name} reached level {state['level']}!")
                else:
                    break
        return messages

    def adjust_loyalty(self, template_id: str, amount: int) -> list[str]:
        """Adjust loyalty for a specific crew member.

        Args:
            template_id: Crew member to adjust.
            amount: Amount to add (positive) or subtract (negative).

        Returns:
            List of newly crossed threshold flags (e.g., "crew_loyalty_elena_reeves_50").
            Only generated when crossing upward.
        """
        state = self._state.get(template_id)
        if not state:
            return []

        # Crew (non-companions) have fixed loyalty — no adjustments
        template = self._templates.get(template_id)
        if template and not template.is_companion:
            return []

        old_loyalty = state["loyalty"]
        new_loyalty = max(0, min(100, old_loyalty + amount))
        state["loyalty"] = new_loyalty

        # Check for upward threshold crossings
        flags: list[str] = []
        if new_loyalty > old_loyalty:
            for threshold in _LOYALTY_FLAG_THRESHOLDS:
                if old_loyalty < threshold <= new_loyalty:
                    flags.append(f"crew_loyalty_{template_id}_{threshold}")
        return flags

    def adjust_loyalty_all(self, amount: int) -> list[str]:
        """Adjust loyalty for all recruited crew members.

        Args:
            amount: Amount to add (positive) or subtract (negative).

        Returns:
            List of newly crossed threshold flags.
        """
        all_flags: list[str] = []
        for tid in self._recruited:
            flags = self.adjust_loyalty(tid, amount)
            all_flags.extend(flags)
        return all_flags

    def adjust_loyalty_for_faction(
        self, faction_id: str, amount: int
    ) -> list[str]:
        """Adjust loyalty for all recruited crew matching a faction.

        Args:
            faction_id: Faction whose crew members are affected.
            amount: Loyalty adjustment amount.

        Returns:
            List of newly crossed threshold flags.
        """
        all_flags: list[str] = []
        for tid in self._recruited:
            template = self._templates.get(tid)
            if template and template.faction_id == faction_id:
                flags = self.adjust_loyalty(tid, amount)
                all_flags.extend(flags)
        return all_flags

    def get_loyalty_tier(self, template_id: str) -> Optional[LoyaltyTier]:
        """Get the loyalty tier for a crew member.

        Args:
            template_id: Crew member to query.

        Returns:
            LoyaltyTier, or None if not recruited.
        """
        state = self._state.get(template_id)
        if not state:
            return None
        return _loyalty_value_to_tier(state["loyalty"])

    def get_loyalty_multiplier(self, template_id: str) -> float:
        """Get the ability bonus multiplier based on loyalty tier.

        Args:
            template_id: Crew member to query.

        Returns:
            1.0 for most tiers, 1.25 for Loyal, 1.5 for Devoted.
        """
        tier = self.get_loyalty_tier(template_id)
        if tier == LoyaltyTier.LOYAL:
            return 1.25
        if tier == LoyaltyTier.DEVOTED:
            return 1.5
        return 1.0

    def check_departure_warnings(self) -> list[str]:
        """Check for crew members at risk of departing.

        Returns:
            List of warning messages for crew with loyalty < 10.
        """
        warnings: list[str] = []
        for tid in self._recruited:
            state = self._state.get(tid)
            template = self._templates.get(tid)
            if state and template and state["loyalty"] < 10:
                warnings.append(
                    f"{template.name} is considering leaving the crew"
                )
        return warnings

    def process_departures(self) -> list[str]:
        """Remove crew members with loyalty 0, preserving state for re-recruitment.

        Returns:
            List of departure messages.
        """
        departures: list[str] = []
        to_remove: list[str] = []
        for tid in self._recruited:
            state = self._state.get(tid)
            template = self._templates.get(tid)
            if state and template and state["loyalty"] <= 0:
                departures.append(f"{template.name} has left the crew")
                to_remove.append(tid)

        for tid in to_remove:
            template = self._templates[tid]
            preserved = dict(self._state[tid])
            preserved["departed"] = True
            preserved["location"] = template.home_system_id
            self._dismissed[tid] = preserved
            self._recruited.remove(tid)
            del self._state[tid]

        return departures

    def is_recruited(self, template_id: str) -> bool:
        """Check if a crew member is currently recruited."""
        return template_id in self._recruited

    def is_dismissed(self, template_id: str) -> bool:
        """Check if a crew member is dismissed and awaiting re-recruitment."""
        return template_id in self._dismissed

    def get_dismissed_at_system(
        self, system_id: str
    ) -> list[tuple["CrewTemplate", dict[str, Any]]]:
        """Get dismissed crew members located at a specific system.

        Args:
            system_id: System ID to filter by.

        Returns:
            List of (template, dismissed_state) pairs at the given system.
        """
        result = []
        for tid, state in self._dismissed.items():
            if state.get("location") == system_id:
                template = self._templates.get(tid)
                if template:
                    result.append((template, state))
        return result

    def get_available_crew_at_system(
        self, system_id: str
    ) -> list["CrewTemplate"]:
        """Get hireable crew members at a system.

        Returns non-companion crew whose home_system_id matches,
        who are not currently recruited or dismissed.

        Args:
            system_id: System to check for available crew.

        Returns:
            List of CrewTemplate instances available for hire.
        """
        available = []
        for tid, template in self._templates.items():
            # Pending companions override the is_companion filter
            is_pending = tid in self._pending_companions
            if template.is_companion and not is_pending:
                continue
            if template.home_system_id != system_id:
                continue
            if tid in self._recruited or tid in self._dismissed:
                continue
            available.append(template)
        return available

    def can_dismiss(
        self, template_id: str, active_mission_ids: list[str]
    ) -> tuple[bool, str]:
        """Check if a crew member can be dismissed.

        Args:
            template_id: Crew member to check.
            active_mission_ids: List of currently active mission IDs.

        Returns:
            Tuple of (allowed, reason).
        """
        if template_id == "dr_priya_osei" and "lab_rat" in active_mission_ids:
            return (False, "Dr. Priya Osei cannot leave while the Lab Rat mission is active")
        return (True, "")

    def get_recruit_cost(self, template_id: str) -> int:
        """Get the credit cost to re-recruit a dismissed crew member.

        Args:
            template_id: Crew member to check.

        Returns:
            Credit cost. 0 for non-dismissed crew (fresh recruits).
        """
        if template_id not in self._dismissed:
            return 0

        from spacegame.config import (
            CREW_DEPARTED_SURCHARGE,
            CREW_RERECRUIT_DISCONTENTED,
            CREW_RERECRUIT_NEUTRAL,
            CREW_RERECRUIT_WARY,
        )

        state = self._dismissed[template_id]
        loyalty = state.get("loyalty", 30)
        tier = _loyalty_value_to_tier(loyalty)

        cost = 0
        if tier == LoyaltyTier.NEUTRAL:
            cost = CREW_RERECRUIT_NEUTRAL
        elif tier == LoyaltyTier.WARY:
            cost = CREW_RERECRUIT_WARY
        elif tier == LoyaltyTier.DISCONTENTED:
            cost = CREW_RERECRUIT_DISCONTENTED

        if state.get("departed", False):
            cost += CREW_DEPARTED_SURCHARGE

        return cost

    def get_state(self) -> dict[str, Any]:
        """Serialize all crew runtime state for saving."""
        return {
            "recruited": list(self._recruited),
            "members": {tid: dict(s) for tid, s in self._state.items()},
            "dismissed": {tid: dict(s) for tid, s in self._dismissed.items()},
            "pending_companions": sorted(self._pending_companions),
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore crew runtime state from saved data.

        Args:
            data: Dict from get_state().
        """
        self._recruited.clear()
        self._state.clear()
        self._dismissed.clear()

        recruited = data.get("recruited", [])
        members = data.get("members", {})

        for tid in recruited:
            if tid in self._templates and tid in members:
                self._recruited.append(tid)
                state = dict(members[tid])
                # Backward compat: ensure attributes exist
                if "attributes" not in state:
                    state["attributes"] = dict(self._templates[tid].base_attributes)
                if "attribute_points" not in state:
                    state["attribute_points"] = 0
                if "bonus_abilities" not in state:
                    state["bonus_abilities"] = []
                self._state[tid] = state

        # Load dismissed crew (backward compat: may not exist in old saves)
        dismissed = data.get("dismissed", {})
        for tid, state in dismissed.items():
            if tid in self._templates:
                self._dismissed[tid] = dict(state)

        # Load pending companions (backward compat: may not exist in old saves)
        self._pending_companions = set(data.get("pending_companions", []))
