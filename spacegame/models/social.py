"""Social skill system models.

Tracks use-based social skills (Persuasion, Intimidation, Observation) and
per-NPC disposition for dialogue skill checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

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
    "deception": "Deception",
    "technical": "Technical",
    "piloting": "Piloting",
    "leadership": "Leadership",
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

# Specialization bonus: soft modifier that rewards focusing on a skill
# relative to your other skills. Measured from base_level only —
# tree/synergy/disposition contribute to effective_level orthogonally.
#
# Ratio = skill_X.base_level / mean(all_skill_base_levels)
# Bonus = int((ratio - 1.0) * SPEC_BONUS_SCALE), clamped to [SPEC_BONUS_MIN,
# SPEC_BONUS_MAX]. Truncation (not rounding) means you have to earn a full
# point — a ratio of 1.25 is not a specialist.
SPEC_BONUS_SCALE: float = 2.0
SPEC_BONUS_MAX: int = 2
SPEC_BONUS_MIN: int = -2

# Which attribute contributes synergy bonus to each skill. Socials share
# Synergy (SYN); Technical draws on Ingenuity (ING, "technical creativity");
# Piloting draws on Acuity (ACU, "analytical precision").
SKILL_TO_ATTRIBUTE: dict[str, str] = {
    "persuasion": "syn",
    "intimidation": "syn",
    "observation": "syn",
    "deception": "syn",
    "leadership": "syn",
    "technical": "ing",
    "piloting": "acu",
}

# Skills whose effective level is influenced by NPC disposition. Social-
# interaction skills respond to NPC mood; expertise skills (Technical,
# Piloting) don't — the NPC's opinion of you doesn't change whether you
# can read a circuit or thread a nebula.
SKILLS_USING_DISPOSITION: set[str] = {
    "persuasion",
    "intimidation",
    "observation",
    "deception",
    "leadership",
}

# XP grants outside of dialogue — keep Technical and Piloting from stagnating
# when they're rarely exercised in conversation.
XP_ON_REFINE_SUCCESS: int = 2  # Technical growth from successful refines
XP_ON_COMBAT_WIN: int = 2  # Piloting growth from combat victories


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

    def add_xp(self, amount: int, max_level: int, xp_thresholds: list[int]) -> list[str]:
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
                messages.append(f"{self.name} increased to level {self.level}!")
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
            sid: SocialSkill(id=sid, name=name) for sid, name in SOCIAL_SKILL_DEFINITIONS.items()
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
        self._npc_disposition[npc_id] = max(DISPOSITION_MIN, min(DISPOSITION_MAX, current + amount))

    # --- Specialization (soft modifier) ---

    def get_specialization_ratio(self, skill_id: str) -> float:
        """Ratio of this skill's base level vs the mean across all social skills.

        Ratio 1.0 = balanced (skill matches average). Ratio > 1.0 = specialized.
        Ratio < 1.0 = neglected relative to others.

        Uses base_level only (the use-based component) — the player's
        dialogue-path choices, not their stat allocations.

        Args:
            skill_id: Social skill to measure.

        Returns:
            Float ratio. Returns 1.0 if no skills are leveled (edge case).
        """
        levels = [s.level for s in self._skills.values()]
        if not levels:
            return 1.0
        avg = sum(levels) / len(levels)
        if avg <= 0:
            return 1.0
        return self.get_skill_level(skill_id) / avg

    def get_specialization_bonus(self, skill_id: str) -> int:
        """Integer bonus (or penalty) to effective level from specialization.

        Formula: int((ratio - 1.0) * SPEC_BONUS_SCALE), clamped to
        [SPEC_BONUS_MIN, SPEC_BONUS_MAX]. Truncation (not rounding) means a
        specialist must earn a full point — a ratio of 1.25 doesn't cross
        the threshold.

        Args:
            skill_id: Social skill to measure.

        Returns:
            Integer bonus, typically -2 to +2.
        """
        ratio = self.get_specialization_ratio(skill_id)
        raw = (ratio - 1.0) * SPEC_BONUS_SCALE
        if raw >= 0:
            return min(SPEC_BONUS_MAX, int(raw))
        return max(SPEC_BONUS_MIN, int(raw))

    # --- Effective level & check resolution ---

    def get_effective_level(self, skill_id: str, npc_id: str) -> int:
        """Get skill level adjusted by disposition, tree, attributes, and spec.

        Formula: base + disposition_modifier + tree_bonus + synergy_bonus
        + specialization_bonus.

        - Disposition modifier only applies to social-interaction skills
          (Persuasion, Intimidation, Deception, Observation, Leadership).
          Expertise skills (Technical, Piloting) ignore NPC mood.
        - Synergy bonus draws from the skill's matching attribute per
          ``SKILL_TO_ATTRIBUTE``.
        - Specialization rewards focusing on a skill relative to peers
          (NV-0 soft modifier).

        Args:
            skill_id: Skill to check.
            npc_id: NPC whose disposition modifies the check (if applicable).

        Returns:
            Effective level (minimum 0).
        """
        base_level = self.get_skill_level(skill_id)

        disp_modifier = 0
        if skill_id in SKILLS_USING_DISPOSITION:
            disposition = self.get_disposition(npc_id)
            disp_modifier = (disposition - DISPOSITION_DEFAULT) // 10

        tree_bonus = 0
        if self._progression is not None:
            tree_bonus = int(self._progression.get_bonus(f"{skill_id}_bonus"))
            # Cultural Savant: +1 per level in faction-aligned systems — only
            # relevant to social-interaction skills.
            if skill_id in SKILLS_USING_DISPOSITION:
                tree_bonus += int(self._progression.get_bonus("faction_social_bonus"))

        synergy_bonus = 0
        if self._attribute_sheet is not None:
            attr = SKILL_TO_ATTRIBUTE.get(skill_id)
            if attr is not None:
                synergy_bonus = self._attribute_sheet.get_attribute_check_bonus(attr)

        spec_bonus = self.get_specialization_bonus(skill_id)

        return max(0, base_level + disp_modifier + tree_bonus + synergy_bonus + spec_bonus)

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

    def resolve_check(self, skill_id: str, difficulty: int, npc_id: str) -> tuple[bool, str]:
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
            skill.add_xp(XP_ON_SUCCESS, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
            self.modify_disposition(npc_id, DISPOSITION_ON_CHECK_SUCCESS)
            msg = f"{skill.name} check passed!"
        else:
            skill.add_xp(XP_ON_FAILURE, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
            self.modify_disposition(npc_id, DISPOSITION_ON_CHECK_FAILURE)
            msg = f"{skill.name} check failed."

        return success, msg

    # --- Serialization ---

    def get_state(self) -> dict[str, Any]:
        """Serialize social state for saving."""
        return {
            "skills": {sid: skill.to_dict() for sid, skill in self._skills.items()},
            "disposition": dict(self._npc_disposition),
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore social state from saved data.

        Args:
            data: Serialized state from get_state(). Empty dict resets to defaults.
        """
        # Reset to defaults
        self._skills = {
            sid: SocialSkill(id=sid, name=name) for sid, name in SOCIAL_SKILL_DEFINITIONS.items()
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
