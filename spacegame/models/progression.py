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
    SOCIAL = "social"
    GROUND = "ground"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SMUGGLING = "smuggling"


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

    Uses a gentle quadratic formula with no cap.
    Level 1 = 0 XP (starting).

    Args:
        level: Target level (1-based).

    Returns:
        Cumulative XP required.
    """
    if level <= 1:
        return 0
    n = level - 1  # number of level-ups completed
    return 60 * n + 20 * n * (n + 1)


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

        No level cap — XP thresholds scale via formula.
        Every 5th level is a milestone granting 2 skill points instead of 1.

        Args:
            amount: XP to add

        Returns:
            List of messages about level ups
        """
        self.xp += amount
        messages = []

        # Check for level ups (no cap)
        while True:
            next_threshold = get_xp_threshold(self.level + 1)
            if self.xp >= next_threshold:
                self.level += 1
                points = 2 if self.level % 5 == 0 else 1
                self.skill_points += points
                sp_text = f"+{points} skill point{'s' if points > 1 else ''}!"
                messages.append(f"Level up! Now level {self.level}. {sp_text}")
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

    # --- New Trading skills ---
    skills["commodity_specialist"] = SkillNode(
        id="commodity_specialist",
        name="Commodity Specialist",
        description="+5% sell price on specialty goods per level",
        tree=SkillTreeType.TRADING,
        max_level=2,
        prerequisite_id="trade_network",
        bonus_type="specialty_sell_bonus",
        bonus_per_level=0.05,
    )
    skills["market_manipulation"] = SkillNode(
        id="market_manipulation",
        name="Market Manipulation",
        description="Player buy/sell has 50% less price impact per level",
        tree=SkillTreeType.TRADING,
        max_level=2,
        prerequisite_id="market_insider",
        bonus_type="market_impact_reduction",
        bonus_per_level=0.50,
    )
    skills["smuggler_contacts"] = SkillNode(
        id="smuggler_contacts",
        name="Smuggler Contacts",
        description="-10% off-market sell penalty per level",
        tree=SkillTreeType.TRADING,
        max_level=2,
        prerequisite_id="bulk_trader",
        bonus_type="off_market_bonus",
        bonus_per_level=0.10,
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

    # --- New Leadership skills ---
    skills["fleet_coordinator"] = SkillNode(
        id="fleet_coordinator",
        name="Fleet Coordinator",
        description="+10% crew task effectiveness per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="crew_mentor",
        bonus_type="crew_effectiveness",
        bonus_per_level=0.10,
    )
    skills["crisis_management"] = SkillNode(
        id="crisis_management",
        name="Crisis Management",
        description="-5% hull damage taken per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=3,
        prerequisite_id="tariff_negotiation",
        bonus_type="hull_damage_reduction",
        bonus_per_level=0.05,
    )
    skills["veteran_command"] = SkillNode(
        id="veteran_command",
        name="Veteran Command",
        description="+2% XP gain from all sources per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=3,
        prerequisite_id="crew_manager",
        bonus_type="xp_gain_bonus",
        bonus_per_level=0.02,
    )

    # === SOCIAL TREE ===
    skills["silver_tongue"] = SkillNode(
        id="silver_tongue",
        name="Silver Tongue",
        description="+1 Persuasion level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        bonus_type="persuasion_bonus",
        bonus_per_level=1.0,
    )
    skills["commanding_presence"] = SkillNode(
        id="commanding_presence",
        name="Commanding Presence",
        description="+1 Intimidation level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="silver_tongue",
        bonus_type="intimidation_bonus",
        bonus_per_level=1.0,
    )
    skills["keen_insight"] = SkillNode(
        id="keen_insight",
        name="Keen Insight",
        description="+1 Observation level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="silver_tongue",
        bonus_type="observation_bonus",
        bonus_per_level=1.0,
    )

    # --- New Social skills ---
    skills["master_negotiator"] = SkillNode(
        id="master_negotiator",
        name="Master Negotiator",
        description="Unlock special dialogue options in negotiations",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="commanding_presence",
        bonus_type="special_dialogue",
        bonus_per_level=1.0,
    )
    skills["streetwise"] = SkillNode(
        id="streetwise",
        name="Streetwise",
        description="+1 to black market checks per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="keen_insight",
        bonus_type="black_market_bonus",
        bonus_per_level=1.0,
    )
    skills["empathic_read"] = SkillNode(
        id="empathic_read",
        name="Empathic Read",
        description="See NPC disposition during dialogue",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="keen_insight",
        bonus_type="npc_disposition_visible",
        bonus_per_level=1.0,
    )
    skills["silver_lining"] = SkillNode(
        id="silver_lining",
        name="Silver Lining",
        description="+10% better random encounter outcomes per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="master_negotiator",
        bonus_type="encounter_outcome_bonus",
        bonus_per_level=0.10,
    )
    skills["faction_diplomat"] = SkillNode(
        id="faction_diplomat",
        name="Faction Diplomat",
        description="+1 faction rep per diplomatic action per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="master_negotiator",
        bonus_type="diplomatic_rep_bonus",
        bonus_per_level=1.0,
    )

    # === GROUND COMBAT TREE ===
    skills["scrapper"] = SkillNode(
        id="scrapper",
        name="Scrapper",
        description="+1 to ground attack rolls",
        tree=SkillTreeType.GROUND,
        max_level=1,
        bonus_type="ground_attack_bonus",
        bonus_per_level=1.0,
    )
    skills["tough_hide"] = SkillNode(
        id="tough_hide",
        name="Tough Hide",
        description="+2 max HP on ground missions",
        tree=SkillTreeType.GROUND,
        max_level=1,
        bonus_type="ground_hp_bonus",
        bonus_per_level=2.0,
    )
    skills["quick_reflexes"] = SkillNode(
        id="quick_reflexes",
        name="Quick Reflexes",
        description="Once per ground combat, re-roll any die",
        tree=SkillTreeType.GROUND,
        max_level=1,
        prerequisite_id="scrapper",
        bonus_type="ground_reroll",
        bonus_per_level=1.0,
    )
    skills["intimidating_presence"] = SkillNode(
        id="intimidating_presence",
        name="Intimidating Presence",
        description="First exchange: enemy rolls at -2",
        tree=SkillTreeType.GROUND,
        max_level=1,
        prerequisite_id="quick_reflexes",
        bonus_type="ground_intimidating_presence",
        bonus_per_level=1.0,
    )
    skills["last_stand"] = SkillNode(
        id="last_stand",
        name="Last Stand",
        description="Below 25% HP: +3 to all rolls",
        tree=SkillTreeType.GROUND,
        max_level=1,
        prerequisite_id="tough_hide",
        bonus_type="ground_last_stand",
        bonus_per_level=1.0,
    )
    skills["veteran"] = SkillNode(
        id="veteran",
        name="Veteran",
        description="+1 re-roll per combat, +1 max HP",
        tree=SkillTreeType.GROUND,
        max_level=1,
        prerequisite_id="intimidating_presence",
        bonus_type="ground_veteran",
        bonus_per_level=1.0,
    )

    # === COMBAT & TACTICS TREE ===
    skills["weapons_training"] = SkillNode(
        id="weapons_training",
        name="Weapons Training",
        description="+5% weapon damage per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        bonus_type="weapon_damage",
        bonus_per_level=0.05,
    )
    skills["evasive_maneuvers"] = SkillNode(
        id="evasive_maneuvers",
        name="Evasive Maneuvers",
        description="+5% dodge chance per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        bonus_type="dodge_chance",
        bonus_per_level=0.05,
    )
    skills["shield_mastery"] = SkillNode(
        id="shield_mastery",
        name="Shield Mastery",
        description="+10% shield effectiveness per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="evasive_maneuvers",
        bonus_type="shield_bonus",
        bonus_per_level=0.10,
    )
    skills["precision_targeting"] = SkillNode(
        id="precision_targeting",
        name="Precision Targeting",
        description="+5% critical hit chance per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="weapons_training",
        bonus_type="crit_chance",
        bonus_per_level=0.05,
    )
    skills["tactical_retreat"] = SkillNode(
        id="tactical_retreat",
        name="Tactical Retreat",
        description="+10% flee chance per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="evasive_maneuvers",
        bonus_type="flee_bonus",
        bonus_per_level=0.10,
    )
    skills["broadside"] = SkillNode(
        id="broadside",
        name="Broadside",
        description="+15% damage with heavy weapons per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="precision_targeting",
        bonus_type="heavy_weapon_damage",
        bonus_per_level=0.15,
    )
    skills["combat_veteran"] = SkillNode(
        id="combat_veteran",
        name="Combat Veteran",
        description="+10% combat XP per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        prerequisite_id="weapons_training",
        bonus_type="combat_xp_bonus",
        bonus_per_level=0.10,
    )

    # === EXPLORATION & PILOTING TREE ===
    skills["fuel_efficiency"] = SkillNode(
        id="fuel_efficiency",
        name="Fuel Efficiency",
        description="-5% fuel consumption per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=3,
        bonus_type="fuel_reduction",
        bonus_per_level=0.05,
    )
    skills["stellar_cartography"] = SkillNode(
        id="stellar_cartography",
        name="Stellar Cartography",
        description="Reveal additional map info per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        bonus_type="map_reveal",
        bonus_per_level=1.0,
    )
    skills["hazard_scanner"] = SkillNode(
        id="hazard_scanner",
        name="Hazard Scanner",
        description="-10% travel event danger per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="stellar_cartography",
        bonus_type="travel_danger_reduction",
        bonus_per_level=0.10,
    )
    skills["long_range_scanner"] = SkillNode(
        id="long_range_scanner",
        name="Long Range Scanner",
        description="+1 system scan range per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="stellar_cartography",
        bonus_type="scan_range",
        bonus_per_level=1.0,
    )
    skills["efficient_routing"] = SkillNode(
        id="efficient_routing",
        name="Efficient Routing",
        description="-5% travel time per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=3,
        prerequisite_id="fuel_efficiency",
        bonus_type="travel_speed",
        bonus_per_level=0.05,
    )
    skills["salvage_instinct"] = SkillNode(
        id="salvage_instinct",
        name="Salvage Instinct",
        description="+15% salvage yield per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="fuel_efficiency",
        bonus_type="salvage_yield",
        bonus_per_level=0.15,
    )
    skills["explorer_reputation"] = SkillNode(
        id="explorer_reputation",
        name="Explorer Reputation",
        description="+1 rep with frontier systems per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="long_range_scanner",
        bonus_type="frontier_rep_bonus",
        bonus_per_level=1.0,
    )

    # === SMUGGLING & SUBTERFUGE TREE ===
    skills["hidden_compartments"] = SkillNode(
        id="hidden_compartments",
        name="Hidden Compartments",
        description="+2 contraband cargo slots per level",
        tree=SkillTreeType.SMUGGLING,
        max_level=3,
        bonus_type="contraband_slots",
        bonus_per_level=2.0,
    )
    skills["bribe_mastery"] = SkillNode(
        id="bribe_mastery",
        name="Bribe Mastery",
        description="-15% bribe cost per level",
        tree=SkillTreeType.SMUGGLING,
        max_level=2,
        prerequisite_id="hidden_compartments",
        bonus_type="bribe_reduction",
        bonus_per_level=0.15,
    )
    skills["scan_jamming"] = SkillNode(
        id="scan_jamming",
        name="Scan Jamming",
        description="-10% detection chance per level",
        tree=SkillTreeType.SMUGGLING,
        max_level=3,
        prerequisite_id="hidden_compartments",
        bonus_type="scan_evasion",
        bonus_per_level=0.10,
    )
    skills["black_market_access"] = SkillNode(
        id="black_market_access",
        name="Black Market Access",
        description="+10% contraband sell price per level",
        tree=SkillTreeType.SMUGGLING,
        max_level=2,
        prerequisite_id="bribe_mastery",
        bonus_type="contraband_sell_bonus",
        bonus_per_level=0.10,
    )
    skills["heat_management"] = SkillNode(
        id="heat_management",
        name="Heat Management",
        description="-10% criminal heat gain per level",
        tree=SkillTreeType.SMUGGLING,
        max_level=3,
        prerequisite_id="scan_jamming",
        bonus_type="heat_reduction",
        bonus_per_level=0.10,
    )
    skills["ghost_runner"] = SkillNode(
        id="ghost_runner",
        name="Ghost Runner",
        description="Maximum evasion: -25% detection, -25% heat gain",
        tree=SkillTreeType.SMUGGLING,
        max_level=1,
        prerequisite_id="heat_management",
        bonus_type="ghost_runner",
        bonus_per_level=1.0,
    )

    return skills
