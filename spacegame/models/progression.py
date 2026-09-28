"""
Player progression system.

XP, leveling, and skill trees for trading and resource gathering.
"""

import functools
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from spacegame.config import PROJECT_ROOT

SKILLS_PATH: Path = PROJECT_ROOT / "data" / "progression" / "skills.json"


class SkillTreeType(Enum):
    """Types of skill trees.

    6-tree structure: Commerce, Combat, Exploration, Leadership, Social, Industry.
    Each tree defines a captain identity — every skill investment is felt.
    """

    COMMERCE = "commerce"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    LEADERSHIP = "leadership"
    SOCIAL = "social"
    INDUSTRY = "industry"


@dataclass
class SkillNode:
    """A single skill in a skill tree."""

    id: str
    name: str
    description: str
    tree: SkillTreeType
    max_level: int = 1
    current_level: int = 0
    cost_per_level: int = 1  # Skill points per level
    prerequisite_id: Optional[str] = None
    bonus_type: str = ""  # Key used for applying bonuses
    bonus_per_level: float = 0.0  # Bonus value per level

    @property
    def is_unlocked(self) -> bool:
        return self.current_level > 0

    @property
    def is_maxed(self) -> bool:
        return self.current_level >= self.max_level

    def get_bonus(self) -> float:
        """Get the total bonus from this skill."""
        return self.bonus_per_level * self.current_level

    def can_level_up(self, available_points: int, unlocked_skills: Dict[str, "SkillNode"]) -> bool:
        """Check if this skill can be leveled up."""
        if self.is_maxed:
            return False
        if available_points < self.cost_per_level:
            return False
        if self.prerequisite_id and self.prerequisite_id not in unlocked_skills:
            return False
        return True


# Respec cost: credits per player level
RESPEC_COST_PER_LEVEL = 100

# Migration map: old 9-tree skill IDs -> new 6-tree equivalents.
# Skills that kept the same ID don't need entries here.
# Old skills with no equivalent are silently dropped (points refunded via respec).
_SKILL_MIGRATION_MAP: Dict[str, str] = {
    # Trading -> Commerce (many IDs kept)
    "bulk_trader": "cargo_mastery",
    "commodity_specialist": "trade_instinct",
    "market_manipulation": "price_memory",
    "smuggler_contacts": "black_market_connections",
    "supply_chain_mastery": "trade_instinct",  # folded
    "trade_magnate": "insurance",  # capstone -> capstone
    # Gathering -> Industry
    "efficient_drills": "passive_drill",
    "keen_scanner": "click_power",
    "master_extractor": "passive_drill",
    "refining_knowledge": "material_science",
    "yield_mastery": "forge_mastery",
    "master_prospector": "ore_sense",
    # Mining -> Industry (many IDs kept)
    "deep_scan": "rich_veins",
    "drone_bay_1": "drone_fleet",
    "drone_bay_2": "drone_fleet",
    "drone_bay_3": "drone_fleet",
    "drone_efficiency": "drone_fleet",
    "ore_targeting": "drone_fleet",
    "chain_reaction": "seismic_charge",
    "pressure_venting": "passive_drill",
    "strip_miner": "ore_sense",
    # Ground -> Combat (absorbed)
    "scrapper": "weapon_specialization",
    "tough_hide": "battle_hardened",
    "quick_reflexes": "ground_veteran",
    "intimidating_presence": "ground_veteran",
    "last_stand": "battle_hardened",
    "field_medic": "battle_hardened",
    "terrain_reader": "battle_awareness",
    "adaptive_fighter": "ground_veteran",
    "veteran": "ground_veteran",
    # Combat (renamed/merged)
    "weapons_training": "weapon_specialization",
    "precision_targeting": "precision_strike",
    "broadside": "weapon_specialization",
    "combat_veteran": "weapon_specialization",
    "rapid_fire": "volley_commander",
    "hull_reinforcement": "hull_reinforcement",  # kept
    "ace_pilot": "ghost_capstone",
    "last_stand_mastery": "juggernaut_capstone",
    "combat_field_repairs": "armor_expertise",
    "endurance": "armor_expertise",
    "shield_regen_skill": "shield_regen",
    "overcharge": "energy_shields",
    "shield_discipline": "shield_mastery",
    "counterstrike_mastery": "counterstrike",
    "slippery": "afterburner",
    # Elemental combat (merged into elemental_affinity)
    "burn_specialist": "elemental_affinity",
    "ion_overcharge": "elemental_affinity",
    "deep_freeze": "elemental_affinity",
    "suppression_expert": "elemental_affinity",
    "elemental_versatility": "elemental_affinity",
    # Social (renamed)
    "streetwise": "underworld_contacts",
    "silver_lining": "faction_ambassador",
    "faction_diplomat": "faction_ambassador",
    "voice_of_the_expanse": "peacemaker",
    # Leadership (renamed)
    "fleet_coordinator": "battle_commander",
    "crisis_management": "battle_commander",
    "veteran_command": "shared_experience",
    "morale_officer": "unbreakable_bonds",
    "legendary_captain": "legend_of_the_expanse",
    # Exploration (renamed)
    "stellar_cartography": "system_intel",
    "hazard_scanner": "safe_passage",
    "long_range_scanner": "route_planner",
    "efficient_routing": "fuel_efficiency",
    "explorer_reputation": "frontier_reputation",
    "trailblazer": "anomaly_sense",
    # Smuggling -> Commerce
    "hidden_compartments": "hidden_compartments",  # kept
    "bribe_mastery": "black_market_connections",
    "scan_jamming": "smugglers_eye",
    "black_market_access": "black_market_connections",
    "heat_management": "hidden_compartments",
    "ghost_runner": "insurance",
    "false_manifest": "smugglers_eye",
    "underworld_rep": "black_market_connections",
    "phantom": "insurance",
}

# Legacy fixed thresholds (kept for reference/migration)
LEVEL_XP_THRESHOLDS = [
    0,  # Level 1 (starting)
    100,  # Level 2
    240,  # Level 3
    420,  # Level 4
    640,  # Level 5
    900,  # Level 6
    1200,  # Level 7
    1540,  # Level 8
    1920,  # Level 9
    2340,  # Level 10
]


def get_xp_threshold(level: int) -> int:
    """Get cumulative XP needed to reach a given level.

    Uses a quadratic formula with no cap.
    Level 1 = 0 XP (starting), Level 2 = 500 XP.

    Args:
        level: Target level (1-based).

    Returns:
        Cumulative XP required.
    """
    if level <= 1:
        return 0
    n = level - 1  # number of level-ups completed
    return 350 * n + 75 * n * (n + 1)


@dataclass
class PlayerProgression:
    """
    Tracks player XP, level, and skill investments.
    """

    xp: int = 0
    level: int = 1
    skill_points: int = 0
    skill_points_spent: int = 0
    skills: Dict[str, SkillNode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.skills:
            self.skills = create_default_skills()

    def add_xp(self, amount: int) -> List[str]:
        """Add XP and check for level ups.

        No level cap — XP thresholds scale via formula.
        Awards exactly 1 skill point per level, always.

        Args:
            amount: XP to add

        Returns:
            List of messages about level ups
        """
        self.xp += amount
        messages = []

        # Check for level ups (no cap, 1 point per level always)
        while True:
            next_threshold = get_xp_threshold(self.level + 1)
            if self.xp >= next_threshold:
                self.level += 1
                self.skill_points += 1
                messages.append(f"Level up! Now level {self.level}. +1 skill point!")
            else:
                break

        return messages

    def get_xp_for_next_level(self) -> int:
        """Get cumulative XP needed for next level.

        Returns:
            XP threshold for next level (always has a next level).
        """
        return get_xp_threshold(self.level + 1)

    def get_xp_progress(self) -> float:
        """Get progress to next level as 0.0-1.0."""
        next_xp = get_xp_threshold(self.level + 1)
        prev_xp = get_xp_threshold(self.level)
        if next_xp == prev_xp:
            return 1.0
        return (self.xp - prev_xp) / (next_xp - prev_xp)

    def get_available_skill_points(self) -> int:
        """Get unspent skill points."""
        return self.skill_points - self.skill_points_spent

    def level_up_skill(self, skill_id: str) -> tuple[bool, str]:
        """
        Invest a skill point into a skill.

        Args:
            skill_id: ID of skill to level up

        Returns:
            Tuple of (success, message)
        """
        if skill_id not in self.skills:
            return (False, "Unknown skill")

        skill = self.skills[skill_id]
        available = self.get_available_skill_points()

        # Get dict of unlocked skills for prerequisite checking
        unlocked = {sid: s for sid, s in self.skills.items() if s.is_unlocked}

        if not skill.can_level_up(available, unlocked):
            if skill.is_maxed:
                return (False, "Skill is already maxed")
            if available < skill.cost_per_level:
                return (False, "Not enough skill points")
            if skill.prerequisite_id and skill.prerequisite_id not in unlocked:
                prereq = self.skills.get(skill.prerequisite_id)
                prereq_name = prereq.name if prereq else skill.prerequisite_id
                return (False, f"Requires: {prereq_name}")
            return (False, "Cannot level up this skill")

        skill.current_level += 1
        self.skill_points_spent += skill.cost_per_level
        return (True, f"{skill.name} leveled to {skill.current_level}!")

    def respec_skills(
        self,
        player_level: int = 1,
        player_credits: int = 0,
    ) -> tuple[bool, str]:
        """Reset all skill investments, refunding all spent points.

        Costs RESPEC_COST_PER_LEVEL * player_level credits. The caller
        is responsible for deducting the returned cost from the player.

        Args:
            player_level: Player's current level (scales cost).
            player_credits: Player's available credits.

        Returns:
            Tuple of (success, message). On success, message includes cost.
        """
        if self.skill_points_spent == 0:
            return (False, "No skills invested to reset")

        cost = RESPEC_COST_PER_LEVEL * player_level
        if player_credits < cost:
            return (False, f"Insufficient credits. Need {cost:,} CR to respec.")

        for skill in self.skills.values():
            skill.current_level = 0
        self.skill_points_spent = 0
        return (True, f"Skills reset for {cost:,} CR. All points refunded.")

    def get_bonus(self, bonus_type: str) -> float:
        """
        Get total bonus of a given type from all skills.

        Args:
            bonus_type: The bonus key to look up

        Returns:
            Total bonus value
        """
        total = 0.0
        for skill in self.skills.values():
            if skill.bonus_type == bonus_type and skill.is_unlocked:
                total += skill.get_bonus()
        return total

    def get_skill_tree(self, tree: SkillTreeType) -> List[SkillNode]:
        """Get all skills in a given tree."""
        return [s for s in self.skills.values() if s.tree == tree]

    def to_dict(self) -> dict:
        """Serialize progression to dict."""
        skills_data = {}
        for skill_id, skill in self.skills.items():
            skills_data[skill_id] = skill.current_level
        return {
            "xp": self.xp,
            "level": self.level,
            "skill_points": self.skill_points,
            "skill_points_spent": self.skill_points_spent,
            "skills": skills_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerProgression":
        """Deserialize progression from dict."""
        prog = cls(
            xp=data.get("xp", 0),
            level=data.get("level", 1),
            skill_points=data.get("skill_points", 0),
            skill_points_spent=data.get("skill_points_spent", 0),
        )
        # Restore skill levels (with migration from old 9-tree skill IDs)
        skills_data = data.get("skills", {})
        for skill_id, level in skills_data.items():
            mapped_id = _SKILL_MIGRATION_MAP.get(skill_id, skill_id)
            if mapped_id in prog.skills:
                # Take the higher value if multiple old skills map to same new one
                prog.skills[mapped_id].current_level = max(
                    prog.skills[mapped_id].current_level, level
                )
        return prog


@functools.cache
def load_skill_definitions() -> tuple[dict[str, object], ...]:
    """Read the skill definitions once per process.

    Returns:
        One raw row per skill, in file order.
    """
    with open(SKILLS_PATH, encoding="utf-8") as handle:
        return tuple(json.load(handle)["skills"])


def _node_from_row(row: dict[str, object]) -> SkillNode:
    """Build a fresh SkillNode (current_level 0) from one JSON row."""
    return SkillNode(
        id=str(row["id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        tree=SkillTreeType(row["tree"]),
        max_level=row["max_level"],  # type: ignore[arg-type]
        cost_per_level=row["cost_per_level"],  # type: ignore[arg-type]
        prerequisite_id=row["prerequisite_id"],  # type: ignore[arg-type]
        bonus_type=str(row["bonus_type"]),
        bonus_per_level=row["bonus_per_level"],  # type: ignore[arg-type]
    )


def create_default_skills() -> Dict[str, SkillNode]:
    """Create fresh skill tree nodes from ``data/progression/skills.json``.

    6 trees, 89 skills. Organized: Tier 1 (entry), Tier 2 (specialization),
    Tier 3 and capstones (identity). Each call returns new nodes, since
    ``current_level`` is per-player state.
    """
    return {str(row["id"]): _node_from_row(row) for row in load_skill_definitions()}
