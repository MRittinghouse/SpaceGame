"""
Player progression system.

XP, leveling, and skill trees for trading and resource gathering.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class SkillTreeType(Enum):
    """Types of skill trees."""

    TRADING = "trading"
    GATHERING = "gathering"
    MINING = "mining"
    LEADERSHIP = "leadership"


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


# XP thresholds for each level (cumulative)
LEVEL_XP_THRESHOLDS = [
    0,  # Level 1 (starting)
    100,  # Level 2
    250,  # Level 3
    500,  # Level 4
    850,  # Level 5
    1300,  # Level 6
    1900,  # Level 7
    2700,  # Level 8
    3800,  # Level 9
    5200,  # Level 10
]


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

    def __post_init__(self):
        if not self.skills:
            self.skills = create_default_skills()

    def add_xp(self, amount: int) -> List[str]:
        """
        Add XP and check for level ups.

        Args:
            amount: XP to add

        Returns:
            List of messages about level ups
        """
        self.xp += amount
        messages = []

        # Check for level ups
        while self.level < len(LEVEL_XP_THRESHOLDS):
            next_threshold = LEVEL_XP_THRESHOLDS[
                self.level
            ]  # level is 1-indexed, threshold list is 0-indexed
            if self.xp >= next_threshold:
                self.level += 1
                self.skill_points += 1
                messages.append(f"Level up! Now level {self.level}. +1 skill point!")
            else:
                break

        return messages

    def get_xp_for_next_level(self) -> Optional[int]:
        """Get XP needed for next level, or None if max."""
        if self.level >= len(LEVEL_XP_THRESHOLDS):
            return None
        return LEVEL_XP_THRESHOLDS[self.level]

    def get_xp_progress(self) -> float:
        """Get progress to next level as 0.0-1.0."""
        next_xp = self.get_xp_for_next_level()
        if next_xp is None:
            return 1.0
        prev_xp = LEVEL_XP_THRESHOLDS[self.level - 1] if self.level > 1 else 0
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
        # Restore skill levels
        skills_data = data.get("skills", {})
        for skill_id, level in skills_data.items():
            if skill_id in prog.skills:
                prog.skills[skill_id].current_level = level
        return prog


def create_default_skills() -> Dict[str, SkillNode]:
    """Create the default skill tree nodes."""
    skills = {}

    # === TRADING MASTERY TREE ===
    skills["negotiator"] = SkillNode(
        id="negotiator",
        name="Negotiator",
        description="-2% purchase price per level",
        tree=SkillTreeType.TRADING,
        max_level=3,
        bonus_type="buy_price_reduction",
        bonus_per_level=0.02,
    )
    skills["market_eye"] = SkillNode(
        id="market_eye",
        name="Market Eye",
        description="See price trend details at current system",
        tree=SkillTreeType.TRADING,
        max_level=1,
        prerequisite_id="negotiator",
        bonus_type="trend_visibility",
        bonus_per_level=1.0,
    )
    skills["bulk_trader"] = SkillNode(
        id="bulk_trader",
        name="Bulk Trader",
        description="-5% price when buying 10+ units per level",
        tree=SkillTreeType.TRADING,
        max_level=2,
        prerequisite_id="negotiator",
        bonus_type="bulk_discount",
        bonus_per_level=0.05,
    )
    skills["trade_network"] = SkillNode(
        id="trade_network",
        name="Trade Network",
        description="+10% sell price at high-rep systems per level",
        tree=SkillTreeType.TRADING,
        max_level=2,
        prerequisite_id="market_eye",
        bonus_type="sell_price_bonus",
        bonus_per_level=0.10,
    )
    skills["market_insider"] = SkillNode(
        id="market_insider",
        name="Market Insider",
        description="See price info for remote systems",
        tree=SkillTreeType.TRADING,
        max_level=1,
        prerequisite_id="trade_network",
        bonus_type="remote_prices",
        bonus_per_level=1.0,
    )

    # === RESOURCE GATHERING TREE ===
    skills["efficient_drills"] = SkillNode(
        id="efficient_drills",
        name="Efficient Drills",
        description="-15% drill time per level",
        tree=SkillTreeType.GATHERING,
        max_level=3,
        bonus_type="drill_speed",
        bonus_per_level=0.15,
    )
    skills["keen_scanner"] = SkillNode(
        id="keen_scanner",
        name="Keen Scanner",
        description="+1 scan charge per level",
        tree=SkillTreeType.GATHERING,
        max_level=3,
        prerequisite_id="efficient_drills",
        bonus_type="extra_scan_charges",
        bonus_per_level=1.0,
    )
    skills["rich_veins"] = SkillNode(
        id="rich_veins",
        name="Rich Veins",
        description="+25% rare ore chance per level",
        tree=SkillTreeType.GATHERING,
        max_level=2,
        prerequisite_id="efficient_drills",
        bonus_type="rare_ore_chance",
        bonus_per_level=0.25,
    )
    skills["master_extractor"] = SkillNode(
        id="master_extractor",
        name="Master Extractor",
        description="-20% extraction time per level",
        tree=SkillTreeType.GATHERING,
        max_level=3,
        prerequisite_id="keen_scanner",
        bonus_type="extract_speed",
        bonus_per_level=0.20,
    )
    skills["refining_knowledge"] = SkillNode(
        id="refining_knowledge",
        name="Refining Knowledge",
        description="Unlocks advanced refining recipes",
        tree=SkillTreeType.GATHERING,
        max_level=1,
        prerequisite_id="master_extractor",
        bonus_type="advanced_recipes",
        bonus_per_level=1.0,
    )

    # === MINING MASTERY TREE ===
    skills["click_power"] = SkillNode(
        id="click_power",
        name="Click Power",
        description="+25% click drill power per level",
        tree=SkillTreeType.MINING,
        max_level=3,
        bonus_type="click_drill_power",
        bonus_per_level=0.25,
    )
    skills["passive_drill"] = SkillNode(
        id="passive_drill",
        name="Passive Drill",
        description="+10% passive drill speed per level",
        tree=SkillTreeType.MINING,
        max_level=2,
        prerequisite_id="click_power",
        bonus_type="passive_drill_speed",
        bonus_per_level=0.10,
    )
    skills["deep_scan"] = SkillNode(
        id="deep_scan",
        name="Deep Scan",
        description="+50% rare ore chance in mining fields per level",
        tree=SkillTreeType.MINING,
        max_level=2,
        prerequisite_id="passive_drill",
        bonus_type="mining_rare_chance",
        bonus_per_level=0.50,
    )
    skills["drone_bay_1"] = SkillNode(
        id="drone_bay_1",
        name="Drone Bay I",
        description="Unlocks 1 drone slot and grants a Tier 1 drone",
        tree=SkillTreeType.MINING,
        max_level=1,
        prerequisite_id="click_power",
        bonus_type="drone_slot",
        bonus_per_level=1.0,
    )
    skills["drone_bay_2"] = SkillNode(
        id="drone_bay_2",
        name="Drone Bay II",
        description="Unlocks 2nd drone slot and grants a Tier 2 drone",
        tree=SkillTreeType.MINING,
        max_level=1,
        prerequisite_id="drone_bay_1",
        bonus_type="drone_slot",
        bonus_per_level=1.0,
    )
    skills["drone_bay_3"] = SkillNode(
        id="drone_bay_3",
        name="Drone Bay III",
        description="Unlocks 3rd drone slot and grants a Tier 3 drone",
        tree=SkillTreeType.MINING,
        max_level=1,
        prerequisite_id="drone_bay_2",
        bonus_type="drone_slot",
        bonus_per_level=1.0,
    )
    skills["drone_efficiency"] = SkillNode(
        id="drone_efficiency",
        name="Drone Efficiency",
        description="+20% drone mining speed per level",
        tree=SkillTreeType.MINING,
        max_level=3,
        prerequisite_id="drone_bay_1",
        bonus_type="drone_mining_speed",
        bonus_per_level=0.20,
    )
    skills["ore_targeting"] = SkillNode(
        id="ore_targeting",
        name="Ore Targeting",
        description="Drones can be set to prefer specific ore types",
        tree=SkillTreeType.MINING,
        max_level=1,
        prerequisite_id="drone_efficiency",
        bonus_type="drone_targeting",
        bonus_per_level=1.0,
    )

    # === LEADERSHIP & OPERATIONS TREE ===
    skills["crew_manager"] = SkillNode(
        id="crew_manager",
        name="Crew Manager",
        description="+1 crew slot",
        tree=SkillTreeType.LEADERSHIP,
        max_level=1,
        bonus_type="crew_slot_bonus",
        bonus_per_level=1.0,
    )
    skills["diplomatic_relations"] = SkillNode(
        id="diplomatic_relations",
        name="Diplomatic Relations",
        description="+1 reputation per trade per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="crew_manager",
        bonus_type="reputation_gain_bonus",
        bonus_per_level=1.0,
    )
    skills["inspiring_leader"] = SkillNode(
        id="inspiring_leader",
        name="Inspiring Leader",
        description="+1 crew loyalty per trade per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="crew_manager",
        bonus_type="crew_loyalty_bonus",
        bonus_per_level=1.0,
    )
    skills["tariff_negotiation"] = SkillNode(
        id="tariff_negotiation",
        name="Tariff Negotiation",
        description="-5% faction tariff per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="diplomatic_relations",
        bonus_type="tariff_reduction",
        bonus_per_level=0.05,
    )
    skills["crew_mentor"] = SkillNode(
        id="crew_mentor",
        name="Crew Mentor",
        description="+2 crew XP per event per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="inspiring_leader",
        bonus_type="crew_xp_bonus",
        bonus_per_level=2.0,
    )

    return skills
