"""
Player progression system.

XP, leveling, and skill trees for trading and resource gathering.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


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

    def __post_init__(self):
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


def create_default_skills() -> Dict[str, SkillNode]:
    """Create the default skill tree nodes.

    6 trees, ~85 skills. Every skill passes the "would I notice?" test.
    Organized: Tier 1 (entry) -> Tier 2 (specialization) -> Tier 3/Capstone (identity).
    """
    skills: Dict[str, SkillNode] = {}

    # ================================================================
    # === COMMERCE TREE (merged Trading + Smuggling) ===
    # Identity: The shrewd merchant who always finds the angle.
    # ================================================================

    # --- Tier 1: Entry ---
    skills["negotiator"] = SkillNode(
        id="negotiator",
        name="Negotiator",
        description="-5% purchase price per level",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        bonus_type="buy_price_reduction",
        bonus_per_level=0.05,
    )
    skills["trade_network"] = SkillNode(
        id="trade_network",
        name="Trade Network",
        description="+5% sell price per level",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        bonus_type="sell_price_bonus",
        bonus_per_level=0.05,
    )

    # --- Tier 2: Specialization ---
    skills["market_eye"] = SkillNode(
        id="market_eye",
        name="Market Eye",
        description="See price trend details at current system",
        tree=SkillTreeType.COMMERCE,
        max_level=1,
        prerequisite_id="negotiator",
        bonus_type="trend_visibility",
        bonus_per_level=1.0,
    )
    # SA-C2: Auction-system specialization (SA-B3/B4 consumer)
    skills["lot_appraiser"] = SkillNode(
        id="lot_appraiser",
        name="Lot Appraiser",
        description="+5% post-auction valuation accuracy per level",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        prerequisite_id="market_eye",
        bonus_type="auction_lot_appraisal_bonus",
        bonus_per_level=0.05,
    )
    skills["market_insider"] = SkillNode(
        id="market_insider",
        name="Market Insider",
        description="See price info for remote systems on the galaxy map",
        tree=SkillTreeType.COMMERCE,
        max_level=1,
        prerequisite_id="market_eye",
        bonus_type="remote_prices",
        bonus_per_level=1.0,
    )
    skills["cargo_mastery"] = SkillNode(
        id="cargo_mastery",
        name="Cargo Mastery",
        description="+10% cargo capacity per level",
        tree=SkillTreeType.COMMERCE,
        max_level=3,
        prerequisite_id="trade_network",
        bonus_type="cargo_capacity_bonus",
        bonus_per_level=0.10,
    )
    skills["trade_instinct"] = SkillNode(
        id="trade_instinct",
        name="Trade Instinct",
        description="Specialty indicators show estimated profit margins",
        tree=SkillTreeType.COMMERCE,
        max_level=1,
        prerequisite_id="market_insider",
        bonus_type="trade_instinct",
        bonus_per_level=1.0,
    )
    skills["price_memory"] = SkillNode(
        id="price_memory",
        name="Price Memory",
        description="Galaxy map shows last-known prices for visited systems",
        tree=SkillTreeType.COMMERCE,
        max_level=1,
        prerequisite_id="market_insider",
        bonus_type="price_memory",
        bonus_per_level=1.0,
    )
    skills["tariff_negotiation"] = SkillNode(
        id="tariff_negotiation",
        name="Tariff Negotiation",
        description="-10% faction tariff per level",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        prerequisite_id="negotiator",
        bonus_type="tariff_reduction",
        bonus_per_level=0.10,
    )
    # SA-C2: Futures-market specialization (SA-F2/F3 consumer)
    skills["spread_trader"] = SkillNode(
        id="spread_trader",
        name="Spread Trader",
        description="+5% futures contract spread reduction per level on entry",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        prerequisite_id="tariff_negotiation",
        bonus_type="speculator_premium_reduction",
        bonus_per_level=0.05,
    )

    # --- Smuggling Branch ---
    skills["smugglers_eye"] = SkillNode(
        id="smugglers_eye",
        name="Smuggler's Eye",
        description="See legality status of all goods at a glance",
        tree=SkillTreeType.COMMERCE,
        max_level=1,
        prerequisite_id="trade_network",
        bonus_type="smugglers_eye",
        bonus_per_level=1.0,
    )
    skills["black_market_connections"] = SkillNode(
        id="black_market_connections",
        name="Black Market Connections",
        description="+15% black market sell prices per level",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        prerequisite_id="smugglers_eye",
        bonus_type="black_market_sell_bonus",
        bonus_per_level=0.15,
    )

    skills["hidden_compartments"] = SkillNode(
        id="hidden_compartments",
        name="Hidden Compartments",
        description="+2 contraband cargo slots per level",
        tree=SkillTreeType.COMMERCE,
        max_level=2,
        prerequisite_id="smugglers_eye",
        bonus_type="contraband_slots",
        bonus_per_level=2.0,
    )

    # --- Tier 3: Capstone ---
    skills["insurance"] = SkillNode(
        id="insurance",
        name="Insurance",
        description="On combat defeat, keep 50% of cargo instead of losing all",
        tree=SkillTreeType.COMMERCE,
        max_level=1,
        prerequisite_id="cargo_mastery",
        bonus_type="insurance",
        bonus_per_level=1.0,
    )

    # ================================================================
    # === COMBAT TREE (streamlined, absorbed Ground Combat) ===
    # Identity: The feared captain who dominates every engagement.
    # ================================================================

    # --- Tier 1: Entry ---
    skills["weapon_specialization"] = SkillNode(
        id="weapon_specialization",
        name="Weapon Specialization",
        description="+10% damage with all weapons per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        bonus_type="weapon_damage",
        bonus_per_level=0.10,
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
        max_level=3,
        bonus_type="shield_bonus",
        bonus_per_level=0.10,
    )

    # --- Tier 2: Specialization ---
    skills["precision_strike"] = SkillNode(
        id="precision_strike",
        name="Precision Strike",
        description="+10% critical hit chance per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="weapon_specialization",
        bonus_type="crit_chance",
        bonus_per_level=0.10,
    )
    skills["elemental_affinity"] = SkillNode(
        id="elemental_affinity",
        name="Elemental Affinity",
        description="All elemental status effects last 1 additional turn",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="weapon_specialization",
        bonus_type="elemental_duration_bonus",
        bonus_per_level=1.0,
    )
    skills["momentum_surge"] = SkillNode(
        id="momentum_surge",
        name="Momentum Surge",
        description="Start combat with +10 momentum per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="weapon_specialization",
        bonus_type="starting_momentum",
        bonus_per_level=10.0,
    )
    skills["tactical_retreat"] = SkillNode(
        id="tactical_retreat",
        name="Tactical Retreat",
        description="+15% flee chance per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="evasive_maneuvers",
        bonus_type="flee_bonus",
        bonus_per_level=0.15,
    )
    skills["shield_regen"] = SkillNode(
        id="shield_regen",
        name="Shield Regeneration",
        description="+2 shield regen per turn per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="shield_mastery",
        bonus_type="shield_regen_bonus",
        bonus_per_level=2.0,
    )
    skills["armor_expertise"] = SkillNode(
        id="armor_expertise",
        name="Armor Expertise",
        description="+1 armor per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        prerequisite_id="shield_mastery",
        bonus_type="armor_bonus",
        bonus_per_level=1.0,
    )
    skills["battle_awareness"] = SkillNode(
        id="battle_awareness",
        name="Battle Awareness",
        description="See enemy intended action before choosing yours",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="evasive_maneuvers",
        bonus_type="battle_awareness",
        bonus_per_level=1.0,
    )

    skills["hull_reinforcement"] = SkillNode(
        id="hull_reinforcement",
        name="Hull Reinforcement",
        description="+5% max hull HP per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        prerequisite_id="armor_expertise",
        bonus_type="hull_hp_bonus",
        bonus_per_level=0.05,
    )
    skills["afterburner"] = SkillNode(
        id="afterburner",
        name="Afterburner",
        description="+5 evasion per level",
        tree=SkillTreeType.COMBAT,
        max_level=3,
        prerequisite_id="evasive_maneuvers",
        bonus_type="afterburner_bonus",
        bonus_per_level=5.0,
    )
    skills["light_foot"] = SkillNode(
        id="light_foot",
        name="Light Foot",
        description="Lv1: no evasion decay after hit. Lv2: graze damage halved",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="afterburner",
        bonus_type="light_foot",
        bonus_per_level=1.0,
    )
    skills["counterstrike"] = SkillNode(
        id="counterstrike",
        name="Counterstrike Mastery",
        description="Counterstrike bonus +5% per level, max stacks +1",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="afterburner",
        bonus_type="counterstrike_bonus",
        bonus_per_level=0.05,
    )
    skills["energy_shields"] = SkillNode(
        id="energy_shields",
        name="Energy Shields",
        description="Shield restore costs 1 less energy per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="shield_regen",
        bonus_type="shield_energy_discount",
        bonus_per_level=1.0,
    )

    # --- Volley Commander (game-changer) ---
    skills["volley_commander"] = SkillNode(
        id="volley_commander",
        name="Volley Commander",
        description="Queue one extra action per combat turn",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="precision_strike",
        bonus_type="extra_combat_action",
        bonus_per_level=1.0,
    )

    # --- Ground Combat Sub-Branch ---
    skills["ground_veteran"] = SkillNode(
        id="ground_veteran",
        name="Ground Veteran",
        description="+1 ground combat reroll per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="weapon_specialization",
        bonus_type="ground_reroll",
        bonus_per_level=1.0,
    )
    skills["battle_hardened"] = SkillNode(
        id="battle_hardened",
        name="Battle-Hardened",
        description="+20% ground HP",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="ground_veteran",
        bonus_type="ground_hp_bonus",
        bonus_per_level=0.20,
    )
    skills["combat_scavenger"] = SkillNode(
        id="combat_scavenger",
        name="Combat Scavenger",
        description="+15% ground loot quality per level",
        tree=SkillTreeType.COMBAT,
        max_level=2,
        prerequisite_id="ground_veteran",
        bonus_type="ground_loot_bonus",
        bonus_per_level=0.15,
    )

    # --- Tier 3: Capstone Paths ---
    skills["juggernaut_capstone"] = SkillNode(
        id="juggernaut_capstone",
        name="Juggernaut",
        description="Hull > 75%: immune to crits. Hull < 25%: +25% damage",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="armor_expertise",
        bonus_type="juggernaut_capstone",
        bonus_per_level=1.0,
    )
    skills["sentinel_capstone"] = SkillNode(
        id="sentinel_capstone",
        name="Sentinel",
        description="Shields > 50%: double regen. Shield break: restore 20%",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="shield_regen",
        bonus_type="sentinel_capstone",
        bonus_per_level=1.0,
    )
    skills["ghost_capstone"] = SkillNode(
        id="ghost_capstone",
        name="Ghost",
        description="First turn: +30 evasion. Consecutive unhit: guaranteed crit",
        tree=SkillTreeType.COMBAT,
        max_level=1,
        prerequisite_id="battle_awareness",
        bonus_type="ghost_capstone",
        bonus_per_level=1.0,
    )

    # ================================================================
    # === EXPLORATION TREE (merged Exploration + some Gathering) ===
    # Identity: The navigator who knows every corridor and hidden route.
    # ================================================================

    # --- Tier 1: Entry ---
    skills["fuel_efficiency"] = SkillNode(
        id="fuel_efficiency",
        name="Fuel Efficiency",
        description="-10% fuel cost per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=3,
        bonus_type="fuel_reduction",
        bonus_per_level=0.10,
    )
    skills["salvage_instinct"] = SkillNode(
        id="salvage_instinct",
        name="Salvage Instinct",
        description="+15% salvage yield per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        bonus_type="salvage_yield",
        bonus_per_level=0.15,
    )
    # NV-6.5: Piloting base — entry into the Piloting skill-check axis.
    skills["steady_stick"] = SkillNode(
        id="steady_stick",
        name="Steady Stick",
        description="+1 Piloting level per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        bonus_type="piloting_bonus",
        bonus_per_level=1.0,
    )

    # --- Tier 2: Specialization ---
    skills["system_intel"] = SkillNode(
        id="system_intel",
        name="System Intel",
        description="Lv1: see danger for unvisited systems. Lv2: see faction and economy",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="fuel_efficiency",
        bonus_type="system_intel",
        bonus_per_level=1.0,
    )
    skills["safe_passage"] = SkillNode(
        id="safe_passage",
        name="Safe Passage",
        description="-15% encounter chance per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="fuel_efficiency",
        bonus_type="encounter_reduction",
        bonus_per_level=0.15,
    )
    skills["route_planner"] = SkillNode(
        id="route_planner",
        name="Route Planner",
        description="See fuel cost for all systems on galaxy map",
        tree=SkillTreeType.EXPLORATION,
        max_level=1,
        prerequisite_id="system_intel",
        bonus_type="route_planner",
        bonus_per_level=1.0,
    )
    skills["frontier_reputation"] = SkillNode(
        id="frontier_reputation",
        name="Frontier Reputation",
        description="+5 starting rep with Frontier Alliance per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="system_intel",
        bonus_type="frontier_rep_bonus",
        bonus_per_level=5.0,
    )
    skills["field_repairs"] = SkillNode(
        id="field_repairs",
        name="Field Repairs",
        description="Restore 5% hull on system arrival per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="fuel_efficiency",
        bonus_type="jump_hull_restore",
        bonus_per_level=0.05,
    )
    skills["salvage_efficiency"] = SkillNode(
        id="salvage_efficiency",
        name="Salvage Efficiency",
        description="+1 extraction charge per level in salvage",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="salvage_instinct",
        bonus_type="salvage_extra_charges",
        bonus_per_level=1.0,
    )

    skills["anomaly_detector"] = SkillNode(
        id="anomaly_detector",
        name="Anomaly Detector",
        description="+10% chance to discover hidden events per level",
        tree=SkillTreeType.EXPLORATION,
        max_level=2,
        prerequisite_id="safe_passage",
        bonus_type="anomaly_chance",
        bonus_per_level=0.10,
    )

    # --- Tier 3: Capstone ---
    skills["emergency_reserves"] = SkillNode(
        id="emergency_reserves",
        name="Emergency Reserves",
        description="Can never be fully stranded; minimum 1 fuel after any jump",
        tree=SkillTreeType.EXPLORATION,
        max_level=1,
        prerequisite_id="field_repairs",
        bonus_type="emergency_reserves",
        bonus_per_level=1.0,
    )
    skills["anomaly_sense"] = SkillNode(
        id="anomaly_sense",
        name="Anomaly Sense",
        description="Non-hostile encounter rate increased by 15%",
        tree=SkillTreeType.EXPLORATION,
        max_level=1,
        prerequisite_id="anomaly_detector",
        bonus_type="anomaly_sense",
        bonus_per_level=0.15,
    )

    # ================================================================
    # === LEADERSHIP TREE (refined) ===
    # Identity: The captain who inspires loyalty and commands respect.
    # ================================================================

    # --- Tier 1: Entry ---
    skills["crew_manager"] = SkillNode(
        id="crew_manager",
        name="Crew Manager",
        description="+1 crew slot per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        bonus_type="crew_slot_bonus",
        bonus_per_level=1.0,
    )
    skills["diplomatic_relations"] = SkillNode(
        id="diplomatic_relations",
        name="Diplomatic Relations",
        description="+1 faction rep per trade per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        bonus_type="reputation_gain_bonus",
        bonus_per_level=1.0,
    )
    # SA-C2: Research-institution specialization (SA-R1/R2 consumer)
    skills["research_oversight"] = SkillNode(
        id="research_oversight",
        name="Research Oversight",
        description="+5% project failure odds reduction per level at the Okafor Institute",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="diplomatic_relations",
        bonus_type="research_risk_reduction",
        bonus_per_level=0.05,
    )
    # NV-6.5: Leadership base — entry into the Leadership skill-check axis.
    skills["give_the_word"] = SkillNode(
        id="give_the_word",
        name="Give the Word",
        description="+1 Leadership level per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        bonus_type="leadership_bonus",
        bonus_per_level=1.0,
    )
    # SA-C2: Politics-system specialization (SA-P3/P4 consumer)
    skills["delegate_reach"] = SkillNode(
        id="delegate_reach",
        name="Delegate Reach",
        description="+0.5 to delegate pre-commitment cap per level before a Politics vote",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="give_the_word",
        bonus_type="coalition_size_bonus",
        bonus_per_level=0.5,
    )

    # --- Tier 2: Specialization ---
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
    skills["battle_commander"] = SkillNode(
        id="battle_commander",
        name="Battle Commander",
        description="Crew combat abilities deal +15% damage per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="crew_manager",
        bonus_type="crew_combat_damage",
        bonus_per_level=0.15,
    )
    # NV-6.5 variant: command-presence check bonus when 2+ crew aboard.
    skills["command_presence"] = SkillNode(
        id="command_presence",
        name="Command Presence",
        description="+1 Leadership per level when 2+ crew are aboard",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="give_the_word",
        bonus_type="leadership_crew_bonus",
        bonus_per_level=1.0,
    )
    skills["unbreakable_bonds"] = SkillNode(
        id="unbreakable_bonds",
        name="Unbreakable Bonds",
        description="Crew loyalty never drops below 30",
        tree=SkillTreeType.LEADERSHIP,
        max_level=1,
        prerequisite_id="inspiring_leader",
        bonus_type="loyalty_floor",
        bonus_per_level=30.0,
    )
    skills["shared_experience"] = SkillNode(
        id="shared_experience",
        name="Shared Experience",
        description="+10% XP from crew quest completions per level",
        tree=SkillTreeType.LEADERSHIP,
        max_level=2,
        prerequisite_id="crew_mentor",
        bonus_type="crew_quest_xp_bonus",
        bonus_per_level=0.10,
    )
    skills["captains_presence"] = SkillNode(
        id="captains_presence",
        name="Captain's Presence",
        description="Docking at a station gives +1 faction rep (once per visit)",
        tree=SkillTreeType.LEADERSHIP,
        max_level=1,
        prerequisite_id="diplomatic_relations",
        bonus_type="dock_rep_bonus",
        bonus_per_level=1.0,
    )

    # --- Tier 3: Capstone ---
    skills["legend_of_the_expanse"] = SkillNode(
        id="legend_of_the_expanse",
        name="Legend of the Expanse",
        description="+2 crew slots; crew quests unlock 10 loyalty earlier",
        tree=SkillTreeType.LEADERSHIP,
        max_level=1,
        prerequisite_id="shared_experience",
        bonus_type="legendary_captain",
        bonus_per_level=1.0,
    )

    # ================================================================
    # === SOCIAL TREE (refined, ensure wired) ===
    # Identity: The diplomat who reads people and shapes conversations.
    # ================================================================

    # --- Tier 1: Entry ---
    skills["silver_tongue"] = SkillNode(
        id="silver_tongue",
        name="Silver Tongue",
        description="+1 Persuasion level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        bonus_type="persuasion_bonus",
        bonus_per_level=1.0,
    )
    # SA-C2: Politics persuasion specialization (SA-P3/P4 consumer)
    skills["coalition_sway"] = SkillNode(
        id="coalition_sway",
        name="Coalition Sway",
        description="+10% delegate persuasion modifier per level in Politics disputes",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="silver_tongue",
        bonus_type="coalition_sway_bonus",
        bonus_per_level=0.10,
    )
    skills["commanding_presence"] = SkillNode(
        id="commanding_presence",
        name="Commanding Presence",
        description="+1 Intimidation level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        bonus_type="intimidation_bonus",
        bonus_per_level=1.0,
    )
    skills["keen_insight"] = SkillNode(
        id="keen_insight",
        name="Keen Insight",
        description="+1 Observation level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        bonus_type="observation_bonus",
        bonus_per_level=1.0,
    )
    # NV-6.5: Deception base skill — social-tree entry.
    skills["poker_face"] = SkillNode(
        id="poker_face",
        name="Poker Face",
        description="+1 Deception level per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        bonus_type="deception_bonus",
        bonus_per_level=1.0,
    )

    # --- Tier 2: Specialization ---
    skills["empathic_read"] = SkillNode(
        id="empathic_read",
        name="Empathic Read",
        description="See NPC disposition and subtext during dialogue",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="keen_insight",
        bonus_type="npc_disposition_visible",
        bonus_per_level=1.0,
    )
    # SA-C2: Mediation specialization (SA-P5 consumer)
    skills["mediation_instinct"] = SkillNode(
        id="mediation_instinct",
        name="Mediation Instinct",
        description="+10% partial-win odds in mediation resolutions per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="empathic_read",
        bonus_type="arbitration_neutrality_bonus",
        bonus_per_level=0.10,
    )
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
    skills["cultural_savant"] = SkillNode(
        id="cultural_savant",
        name="Cultural Savant",
        description="+1 to all social checks in faction-aligned systems per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="empathic_read",
        bonus_type="faction_social_bonus",
        bonus_per_level=1.0,
    )
    skills["read_the_room"] = SkillNode(
        id="read_the_room",
        name="Read the Room",
        description="See disposition change on dialogue responses before choosing",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="empathic_read",
        bonus_type="read_the_room",
        bonus_per_level=1.0,
    )
    skills["faction_ambassador"] = SkillNode(
        id="faction_ambassador",
        name="Faction Ambassador",
        description="All faction rep gains doubled per level",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="master_negotiator",
        bonus_type="faction_rep_multiplier",
        bonus_per_level=1.0,
    )
    # NV-6.5 variant: context-narrow Deception bonus for contraband-aware
    # checks. Stacks with the base deception_bonus but only when the
    # encounter flag contraband_present is active.
    skills["ghost_protocol"] = SkillNode(
        id="ghost_protocol",
        name="Ghost Protocol",
        description="+1 Deception per level when carrying contraband",
        tree=SkillTreeType.SOCIAL,
        max_level=2,
        prerequisite_id="poker_face",
        bonus_type="deception_contraband_bonus",
        bonus_per_level=1.0,
    )
    skills["underworld_contacts"] = SkillNode(
        id="underworld_contacts",
        name="Underworld Contacts",
        description="Black market prices visible; access at all stations",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="keen_insight",
        bonus_type="underworld_contacts",
        bonus_per_level=1.0,
    )
    skills["crew_whisperer"] = SkillNode(
        id="crew_whisperer",
        name="Crew Whisperer",
        description="Crew loyalty changes from dialogue are +50%",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="cultural_savant",
        bonus_type="crew_whisperer",
        bonus_per_level=0.50,
    )

    # --- Tier 3: Capstone ---
    skills["peacemaker"] = SkillNode(
        id="peacemaker",
        name="Peacemaker",
        description="Non-hostile option always available; talk out of any fight",
        tree=SkillTreeType.SOCIAL,
        max_level=1,
        prerequisite_id="faction_ambassador",
        bonus_type="peaceful_resolution",
        bonus_per_level=1.0,
    )

    # ================================================================
    # === INDUSTRY TREE (merged Mining + Gathering/Refining) ===
    # Identity: The industrialist who turns raw materials into wealth.
    # ================================================================

    # --- Tier 1: Entry ---
    skills["click_power"] = SkillNode(
        id="click_power",
        name="Click Power",
        description="+25% click drill power per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=3,
        bonus_type="click_drill_power",
        bonus_per_level=0.25,
    )
    skills["passive_drill"] = SkillNode(
        id="passive_drill",
        name="Passive Drill",
        description="+10% passive drill speed per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        bonus_type="passive_drill_speed",
        bonus_per_level=0.10,
    )
    skills["efficient_refining"] = SkillNode(
        id="efficient_refining",
        name="Efficient Refining",
        description="+15% refining speed per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        bonus_type="refining_speed",
        bonus_per_level=0.15,
    )
    # SA-C2: Research-patronage specialization (SA-R1/R2 consumer)
    skills["research_yield"] = SkillNode(
        id="research_yield",
        name="Research Yield",
        description="+5% project return at the Okafor Institute per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        prerequisite_id="efficient_refining",
        bonus_type="research_yield_bonus",
        bonus_per_level=0.05,
    )
    # NV-6.5: Technical base — entry into the Technical skill-check axis.
    skills["tool_sense"] = SkillNode(
        id="tool_sense",
        name="Tool Sense",
        description="+1 Technical level per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        bonus_type="technical_bonus",
        bonus_per_level=1.0,
    )

    # --- Tier 2: Specialization ---
    skills["rich_veins"] = SkillNode(
        id="rich_veins",
        name="Rich Veins",
        description="+25% rare ore chance per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        prerequisite_id="click_power",
        bonus_type="rare_ore_chance",
        bonus_per_level=0.25,
    )
    # NV-6.5 variant: Technical bonus specifically for refining/inspection
    # contexts. Stacks with the base technical_bonus at those moments.
    skills["engineer_insight"] = SkillNode(
        id="engineer_insight",
        name="Engineer's Insight",
        description="+1 Technical per level during refining or inspection",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        prerequisite_id="tool_sense",
        bonus_type="technical_refining_bonus",
        bonus_per_level=1.0,
    )
    skills["drone_fleet"] = SkillNode(
        id="drone_fleet",
        name="Drone Fleet",
        description="Lv1: basic drone. Lv2: drone mines faster. Lv3: two drones active",
        tree=SkillTreeType.INDUSTRY,
        max_level=3,
        prerequisite_id="click_power",
        bonus_type="drone_slot",
        bonus_per_level=1.0,
    )
    skills["seismic_charge"] = SkillNode(
        id="seismic_charge",
        name="Seismic Charge",
        description="Breaking a rock has 20% chance to crack adjacent rocks",
        tree=SkillTreeType.INDUSTRY,
        max_level=1,
        prerequisite_id="rich_veins",
        bonus_type="chain_break_chance",
        bonus_per_level=0.20,
    )
    skills["forge_mastery"] = SkillNode(
        id="forge_mastery",
        name="Forge Mastery",
        description="Refining yields +1 extra unit per batch per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        prerequisite_id="efficient_refining",
        bonus_type="refining_yield_bonus",
        bonus_per_level=1.0,
    )
    skills["salvage_efficiency_industry"] = SkillNode(
        id="salvage_efficiency_industry",
        name="Salvage Savant",
        description="+1 extraction charge per salvage session per level",
        tree=SkillTreeType.INDUSTRY,
        max_level=2,
        prerequisite_id="passive_drill",
        bonus_type="salvage_extra_charges",
        bonus_per_level=1.0,
    )

    # --- Tier 3: Capstone ---
    skills["ore_sense"] = SkillNode(
        id="ore_sense",
        name="Ore Sense",
        description="First rock each mining session is guaranteed rare quality",
        tree=SkillTreeType.INDUSTRY,
        max_level=1,
        prerequisite_id="seismic_charge",
        bonus_type="guaranteed_rare",
        bonus_per_level=1.0,
    )
    skills["material_science"] = SkillNode(
        id="material_science",
        name="Material Science",
        description="Unlock advanced refining recipes without finding schematics",
        tree=SkillTreeType.INDUSTRY,
        max_level=1,
        prerequisite_id="forge_mastery",
        bonus_type="advanced_recipes",
        bonus_per_level=1.0,
    )

    return skills
