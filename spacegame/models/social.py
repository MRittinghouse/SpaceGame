"""Social skill system models.

Tracks use-based social skills (Persuasion, Intimidation, Observation) and
per-NPC disposition for dialogue skill checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from spacegame.models.attributes import AttributeSheet
    from spacegame.models.progression import PlayerProgression


# ============================================================================
# Constants
# ============================================================================

SOCIAL_SKILL_DEFINITIONS: dict[str, str] = {
    "persuasion": "Persuasion",
    "intimidation": "Intimidation",
    "observation": "Observation",
}

SOCIAL_XP_THRESHOLDS: list[int] = [0, 8, 25, 55, 100]
MAX_SOCIAL_LEVEL: int = 5
XP_ON_SUCCESS: int = 2
XP_ON_FAILURE: int = 1
DISPOSITION_DEFAULT: int = 50
DISPOSITION_MIN: int = 0
DISPOSITION_MAX: int = 100
DISPOSITION_ON_CHECK_SUCCESS: int = 3
DISPOSITION_ON_CHECK_FAILURE: int = -2


# ============================================================================
# SocialSkill
# ============================================================================


@dataclass
class SocialSkill:
    """A use-based social skill that grows through dialogue checks."""

    id: str
    name: str
    level: int = 1
    xp: int = 0

    def add_xp(
        self, amount: int, max_level: int, xp_thresholds: list[int]
    ) -> list[str]:
        """Add XP and check for level ups.

        Args:
            amount: XP to add.
            max_level: Maximum skill level.
            xp_thresholds: Cumulative XP thresholds per level.

        Returns:
            List of level-up messages (empty if no level change).
        """
        self.xp += amount
        messages: list[str] = []

        while self.level < max_level:
            next_threshold_index = self.level  # level 1 -> index 1
            if next_threshold_index >= len(xp_thresholds):
                break
            if self.xp >= xp_thresholds[next_threshold_index]:
                self.level += 1
                messages.append(
                    f"{self.name} increased to level {self.level}!"
                )
            else:
                break

        return messages

    def to_dict(self) -> dict[str, Any]:
        """Serialize skill state."""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "xp": self.xp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SocialSkill":
        """Restore skill from serialized data."""
        return cls(
            id=data["id"],
            name=data["name"],
            level=data.get("level", 1),
            xp=data.get("xp", 0),
        )


# ============================================================================
# SocialManager
# ============================================================================


class SocialManager:
    """Manages social skills, NPC disposition, and skill check resolution."""

    def __init__(self) -> None:
        self._skills: dict[str, SocialSkill] = {
            sid: SocialSkill(id=sid, name=name)
            for sid, name in SOCIAL_SKILL_DEFINITIONS.items()
        }
        self._npc_disposition: dict[str, int] = {}
        self._progression: Optional[PlayerProgression] = None
        self._attribute_sheet: Optional[AttributeSheet] = None

    def set_progression(self, progression: PlayerProgression) -> None:
        """Set a progression reference for skill tree bonuses.

        Args:
            progression: Player progression with social tree skills.
        """
        self._progression = progression

    def set_attribute_sheet(self, sheet: AttributeSheet) -> None:
        """Set an attribute sheet reference for synergy bonuses.

        Args:
            sheet: Attribute sheet with Synergy value.
        """
        self._attribute_sheet = sheet

    # --- Skill access ---

    def get_skill(self, skill_id: str) -> Optional[SocialSkill]:
        """Get a social skill by ID, or None if not found."""
        return self._skills.get(skill_id)

    def get_skill_level(self, skill_id: str) -> int:
        """Get a skill's current level, or 0 if unknown."""
        skill = self._skills.get(skill_id)
        return skill.level if skill else 0

    def get_all_skills(self) -> list[SocialSkill]:
        """Get all social skills."""
        return list(self._skills.values())

    # --- NPC disposition ---

    def get_disposition(self, npc_id: str) -> int:
        """Get disposition with an NPC, defaulting to 50 (neutral)."""
        return self._npc_disposition.get(npc_id, DISPOSITION_DEFAULT)

    def modify_disposition(self, npc_id: str, amount: int) -> None:
        """Adjust NPC disposition, clamped 0-100."""
        current = self.get_disposition(npc_id)
        self._npc_disposition[npc_id] = max(
            DISPOSITION_MIN, min(DISPOSITION_MAX, current + amount)
        )

    # --- Effective level & check resolution ---

    def get_effective_level(self, skill_id: str, npc_id: str) -> int:
        """Get skill level adjusted by disposition, tree bonuses, and attributes.

        Formula: use_level + disposition_modifier + tree_bonus + synergy_bonus

        Args:
            skill_id: Social skill to check.
            npc_id: NPC whose disposition modifies the check.

        Returns:
            Effective level (minimum 0).
        """
        base_level = self.get_skill_level(skill_id)
        disposition = self.get_disposition(npc_id)
        disp_modifier = (disposition - DISPOSITION_DEFAULT) // 10

        tree_bonus = 0
        if self._progression is not None:
            tree_bonus = int(self._progression.get_bonus(f"{skill_id}_bonus"))

        synergy_bonus = 0
        if self._attribute_sheet is not None:
            synergy_bonus = self._attribute_sheet.get_synergy_social_bonus()

        return max(0, base_level + disp_modifier + tree_bonus + synergy_bonus)

    def can_pass_check(self, skill_id: str, difficulty: int, npc_id: str) -> bool:
        """Check if the player can pass a skill check (for display purposes).

        Args:
            skill_id: Social skill to check.
            difficulty: Check difficulty (1-5).
            npc_id: NPC whose disposition modifies the check.

        Returns:
            True if effective level >= difficulty.
        """
        return self.get_effective_level(skill_id, npc_id) >= difficulty

    def resolve_check(
        self, skill_id: str, difficulty: int, npc_id: str
    ) -> tuple[bool, str]:
        """Resolve a skill check, awarding XP and adjusting disposition.

        Args:
            skill_id: Social skill to check.
            difficulty: Check difficulty (1-5).
            npc_id: NPC whose disposition modifies the check.

        Returns:
            Tuple of (success, message).
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return False, f"Unknown skill: {skill_id}"

        effective = self.get_effective_level(skill_id, npc_id)
        success = effective >= difficulty

        if success:
            messages = skill.add_xp(
                XP_ON_SUCCESS, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS
            )
            self.modify_disposition(npc_id, DISPOSITION_ON_CHECK_SUCCESS)
            msg = f"{skill.name} check passed!"
        else:
            messages = skill.add_xp(
                XP_ON_FAILURE, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS
            )
            self.modify_disposition(npc_id, DISPOSITION_ON_CHECK_FAILURE)
            msg = f"{skill.name} check failed."

        return success, msg

    # --- Serialization ---

    def get_state(self) -> dict[str, Any]:
        """Serialize social state for saving."""
        return {
            "skills": {
                sid: skill.to_dict() for sid, skill in self._skills.items()
            },
            "disposition": dict(self._npc_disposition),
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore social state from saved data.

        Args:
            data: Serialized state from get_state(). Empty dict resets to defaults.
        """
        # Reset to defaults
        self._skills = {
            sid: SocialSkill(id=sid, name=name)
            for sid, name in SOCIAL_SKILL_DEFINITIONS.items()
        }
        self._npc_disposition = {}

        if not data:
            return

        # Restore skills
        saved_skills = data.get("skills", {})
        for sid, skill_data in saved_skills.items():
            if sid in self._skills:
                self._skills[sid] = SocialSkill.from_dict(skill_data)

        # Restore disposition
        self._npc_disposition = dict(data.get("disposition", {}))
