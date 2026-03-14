"""
Crew system models.

Defines crew abilities, templates, and the CrewRoster manager that tracks
recruitment, leveling, loyalty, and passive bonuses.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


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
    combat_move: Optional[dict[str, Any]] = None  # Raw dict, parsed to CombatMove by data_loader

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

    def recruit(self, template_id: str, crew_slots: int) -> tuple[bool, str]:
        """Recruit a crew member.

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

        self._recruited.append(template_id)
        template = self._templates[template_id]
        self._state[template_id] = {
            "level": 1,
            "xp": 0,
            "loyalty": 30,
            "attributes": dict(template.base_attributes),
            "attribute_points": 0,
        }
        return (True, template.name)

    def dismiss(self, template_id: str) -> tuple[bool, str]:
        """Dismiss a crew member.

        Args:
            template_id: Template ID of crew member to dismiss.

        Returns:
            Tuple of (success, message).
        """
        if template_id not in self._recruited:
            return (False, f"Crew member not in roster: {template_id}")

        name = self._templates[template_id].name
        self._recruited.remove(template_id)
        del self._state[template_id]
        return (True, f"{name} has been dismissed")

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

    def get_bonus(self, bonus_type: str) -> float:
        """Get total bonus of a given type from all recruited crew.

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
                total += template.get_bonus_at_level(bonus_type, state["level"])
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

    def adjust_loyalty(self, template_id: str, amount: int) -> None:
        """Adjust loyalty for a specific crew member.

        Args:
            template_id: Crew member to adjust.
            amount: Amount to add (positive) or subtract (negative).
        """
        state = self._state.get(template_id)
        if state:
            state["loyalty"] = max(0, min(100, state["loyalty"] + amount))

    def adjust_loyalty_all(self, amount: int) -> None:
        """Adjust loyalty for all recruited crew members.

        Args:
            amount: Amount to add (positive) or subtract (negative).
        """
        for tid in self._recruited:
            self.adjust_loyalty(tid, amount)

    def get_state(self) -> dict[str, Any]:
        """Serialize all crew runtime state for saving."""
        return {
            "recruited": list(self._recruited),
            "members": {tid: dict(s) for tid, s in self._state.items()},
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore crew runtime state from saved data.

        Args:
            data: Dict from get_state().
        """
        self._recruited.clear()
        self._state.clear()

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
                self._state[tid] = state
