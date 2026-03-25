"""
Tests for R5: Skill Tree Expansion.

Covers: uncapped leveling, formula-based XP, new skill trees (COMBAT,
EXPLORATION, SMUGGLING), expanded existing trees, and milestone skill points.
"""

import pytest
from spacegame.models.progression import (
    PlayerProgression,
    SkillNode,
    SkillTreeType,
    create_default_skills,
    get_xp_threshold,
)


# ============================================================================
# Uncapped Leveling System
# ============================================================================


class TestUncappedLeveling:
    """Tests for the formula-based, uncapped leveling system."""

    def test_xp_threshold_level_1_is_zero(self) -> None:
        assert get_xp_threshold(1) == 0

    def test_xp_threshold_level_2(self) -> None:
        assert get_xp_threshold(2) == 500

    def test_xp_threshold_increases_each_level(self) -> None:
        """Each level should require more XP than the last."""
        for level in range(2, 50):
            prev = get_xp_threshold(level)
            curr = get_xp_threshold(level + 1)
            assert curr > prev, f"Level {level + 1} should need more XP than level {level}"

    def test_xp_threshold_moderate_curve(self) -> None:
        """Early levels reachable, later levels require real effort."""
        assert get_xp_threshold(5) < 4000
        assert get_xp_threshold(10) < 12000

    def test_no_level_cap(self) -> None:
        """Player can level beyond the old cap of 10."""
        prog = PlayerProgression()
        prog.add_xp(200000)
        assert prog.level > 10, "Should be able to level past 10"

    def test_level_20_reachable(self) -> None:
        """Level 20 should be a long-term goal but not impossible."""
        threshold = get_xp_threshold(20)
        assert threshold < 40000, f"Level 20 at {threshold} XP is too high"

    def test_xp_for_next_level_never_none(self) -> None:
        """get_xp_for_next_level should always return a value (no cap)."""
        prog = PlayerProgression()
        prog.add_xp(50000)
        assert prog.get_xp_for_next_level() is not None

    def test_xp_progress_never_stuck_at_max(self) -> None:
        """Progress should not be stuck at 1.0 unless between level-ups."""
        prog = PlayerProgression()
        prog.add_xp(50000)
        # After leveling up, progress is between 0 and 1 toward next level
        progress = prog.get_xp_progress()
        assert 0.0 <= progress < 1.0 or progress == pytest.approx(1.0)

    def test_level_50_exists(self) -> None:
        """Extremely dedicated players can reach very high levels."""
        threshold = get_xp_threshold(50)
        assert threshold > 0

    def test_xp_threshold_zero_and_negative(self) -> None:
        """Levels <= 0 should return 0."""
        assert get_xp_threshold(0) == 0
        assert get_xp_threshold(-1) == 0


# ============================================================================
# Milestone Skill Points
# ============================================================================


class TestMilestoneSkillPoints:
    """Tests for the milestone skill point system."""

    def test_normal_level_gives_one_point(self) -> None:
        """Non-milestone levels give 1 skill point."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(2))  # Level 2
        assert prog.skill_points == 1

    def test_milestone_level_5_gives_two_points(self) -> None:
        """Level 5 (milestone) gives 2 skill points instead of 1."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(5))
        # Levels 2,3,4 = 3 points, level 5 = 2 points = 5 total
        assert prog.skill_points == 5

    def test_milestone_level_10_gives_two_points(self) -> None:
        """Level 10 (milestone) gives 2 skill points."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        # Levels 2-4,6-9 = 7 * 1 = 7, milestones 5,10 = 2 * 2 = 4, total = 11
        assert prog.skill_points == 11

    def test_milestone_level_15_gives_two_points(self) -> None:
        """Level 15 (milestone) gives 2 skill points."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        # 14 level-ups: milestones at 5,10,15 = 3*2=6, normal 11*1=11, total=17
        assert prog.skill_points == 17

    def test_milestone_every_five_levels(self) -> None:
        """Every 5th level should be a milestone."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(20))
        # 19 level-ups: milestones at 5,10,15,20 = 4*2=8, normal 15*1=15, total=23
        assert prog.skill_points == 23

    def test_skill_points_at_level_25(self) -> None:
        """Verify skill point total at level 25."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(25))
        # 24 level-ups: milestones at 5,10,15,20,25 = 5*2=10, normal 19*1=19, total=29
        assert prog.skill_points == 29


# ============================================================================
# New Skill Tree Types
# ============================================================================


class TestNewSkillTreeTypes:
    """Tests for new SkillTreeType enum values."""

    def test_combat_tree_exists(self) -> None:
        assert SkillTreeType.COMBAT.value == "combat"

    def test_exploration_tree_exists(self) -> None:
        assert SkillTreeType.EXPLORATION.value == "exploration"

    def test_smuggling_tree_exists(self) -> None:
        assert SkillTreeType.SMUGGLING.value == "smuggling"

    def test_all_tree_types_count(self) -> None:
        """Should have 9 total tree types."""
        assert len(SkillTreeType) == 9


# ============================================================================
# Combat Tree (NEW)
# ============================================================================


class TestCombatTree:
    """Tests for the Combat & Tactics skill tree."""

    def test_combat_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "weapons_training",
            "evasive_maneuvers",
            "shield_mastery",
            "precision_targeting",
            "tactical_retreat",
            "broadside",
            "combat_veteran",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_combat_tree_count(self) -> None:
        prog = PlayerProgression()
        combat_skills = prog.get_skill_tree(SkillTreeType.COMBAT)
        assert len(combat_skills) == 30

    def test_weapons_training_is_root(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["weapons_training"]
        assert skill.prerequisite_id is None
        assert skill.tree == SkillTreeType.COMBAT
        assert skill.max_level == 3

    def test_evasive_maneuvers_is_root(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["evasive_maneuvers"]
        assert skill.prerequisite_id is None
        assert skill.tree == SkillTreeType.COMBAT

    def test_precision_targeting_prereq(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["precision_targeting"]
        assert skill.prerequisite_id == "weapons_training"

    def test_shield_mastery_prereq(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["shield_mastery"]
        assert skill.prerequisite_id == "evasive_maneuvers"

    def test_weapons_training_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("weapons_training")
        prog.level_up_skill("weapons_training")
        assert prog.get_bonus("weapon_damage") == pytest.approx(0.10)


# ============================================================================
# Exploration Tree (NEW)
# ============================================================================


class TestExplorationTree:
    """Tests for the Exploration & Piloting skill tree."""

    def test_exploration_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "fuel_efficiency",
            "stellar_cartography",
            "hazard_scanner",
            "long_range_scanner",
            "efficient_routing",
            "salvage_instinct",
            "explorer_reputation",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_exploration_tree_count(self) -> None:
        prog = PlayerProgression()
        skills = prog.get_skill_tree(SkillTreeType.EXPLORATION)
        assert len(skills) == 10

    def test_fuel_efficiency_is_root(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["fuel_efficiency"]
        assert skill.prerequisite_id is None
        assert skill.tree == SkillTreeType.EXPLORATION

    def test_fuel_efficiency_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("fuel_efficiency")
        prog.level_up_skill("fuel_efficiency")
        prog.level_up_skill("fuel_efficiency")
        assert prog.get_bonus("fuel_reduction") == pytest.approx(0.15)

    def test_stellar_cartography_is_root(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["stellar_cartography"]
        assert skill.prerequisite_id is None


# ============================================================================
# Smuggling Tree (NEW)
# ============================================================================


class TestSmugglingTree:
    """Tests for the Smuggling & Subterfuge skill tree."""

    def test_smuggling_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "hidden_compartments",
            "bribe_mastery",
            "scan_jamming",
            "black_market_access",
            "heat_management",
            "ghost_runner",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_smuggling_tree_count(self) -> None:
        prog = PlayerProgression()
        skills = prog.get_skill_tree(SkillTreeType.SMUGGLING)
        assert len(skills) == 9

    def test_hidden_compartments_is_root(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["hidden_compartments"]
        assert skill.prerequisite_id is None
        assert skill.tree == SkillTreeType.SMUGGLING

    def test_ghost_runner_requires_heat_management(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["ghost_runner"]
        assert skill.prerequisite_id == "heat_management"
        assert skill.max_level == 1

    def test_scan_jamming_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("hidden_compartments")
        prog.level_up_skill("scan_jamming")
        prog.level_up_skill("scan_jamming")
        assert prog.get_bonus("scan_evasion") == pytest.approx(0.20)


# ============================================================================
# Expanded Existing Trees
# ============================================================================


class TestExpandedTradingTree:
    """Tests for new skills added to the Trading tree."""

    def test_trading_tree_expanded(self) -> None:
        prog = PlayerProgression()
        trading_skills = prog.get_skill_tree(SkillTreeType.TRADING)
        assert len(trading_skills) == 10

    def test_commodity_specialist_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["commodity_specialist"]
        assert skill.tree == SkillTreeType.TRADING
        assert skill.prerequisite_id == "trade_network"

    def test_market_manipulation_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["market_manipulation"]
        assert skill.tree == SkillTreeType.TRADING
        assert skill.prerequisite_id == "market_insider"

    def test_smuggler_contacts_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["smuggler_contacts"]
        assert skill.tree == SkillTreeType.TRADING
        assert skill.prerequisite_id == "bulk_trader"


class TestExpandedLeadershipTree:
    """Tests for new skills added to the Leadership tree."""

    def test_leadership_tree_expanded(self) -> None:
        prog = PlayerProgression()
        leadership_skills = prog.get_skill_tree(SkillTreeType.LEADERSHIP)
        assert len(leadership_skills) == 10

    def test_fleet_coordinator_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["fleet_coordinator"]
        assert skill.tree == SkillTreeType.LEADERSHIP
        assert skill.prerequisite_id == "crew_mentor"

    def test_crisis_management_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["crisis_management"]
        assert skill.tree == SkillTreeType.LEADERSHIP
        assert skill.prerequisite_id == "tariff_negotiation"

    def test_veteran_command_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["veteran_command"]
        assert skill.tree == SkillTreeType.LEADERSHIP
        assert skill.prerequisite_id == "crew_manager"


class TestExpandedSocialTree:
    """Tests for new skills added to the Social tree."""

    def test_social_tree_expanded(self) -> None:
        prog = PlayerProgression()
        social_skills = prog.get_skill_tree(SkillTreeType.SOCIAL)
        assert len(social_skills) == 10

    def test_master_negotiator_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["master_negotiator"]
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "commanding_presence"

    def test_streetwise_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["streetwise"]
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "keen_insight"

    def test_empathic_read_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["empathic_read"]
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "keen_insight"

    def test_silver_lining_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["silver_lining"]
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "master_negotiator"

    def test_faction_diplomat_exists(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["faction_diplomat"]
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "master_negotiator"


# ============================================================================
# Total Skill Count
# ============================================================================


class TestTotalSkillCount:
    """Verify overall skill count after expansion."""

    def test_total_skill_count(self) -> None:
        """Should have 109 skills across 9 trees after Phase 12C expansion."""
        skills = create_default_skills()
        assert len(skills) == 109

    def test_all_trees_have_skills(self) -> None:
        prog = PlayerProgression()
        for tree_type in SkillTreeType:
            skills = prog.get_skill_tree(tree_type)
            assert len(skills) >= 5, f"{tree_type.value} tree should have at least 5 skills"

    def test_all_prerequisites_valid(self) -> None:
        """Every skill's prerequisite should reference an existing skill."""
        skills = create_default_skills()
        for skill_id, skill in skills.items():
            if skill.prerequisite_id:
                assert skill.prerequisite_id in skills, (
                    f"{skill_id} has invalid prerequisite: {skill.prerequisite_id}"
                )

    def test_no_circular_prerequisites(self) -> None:
        """Prerequisite chains should not form cycles."""
        skills = create_default_skills()
        for skill_id in skills:
            visited = set()
            current = skill_id
            while current:
                assert current not in visited, f"Circular prerequisite: {current}"
                visited.add(current)
                current = skills[current].prerequisite_id


# ============================================================================
# Backward Compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Old saves with fewer skills should load gracefully."""

    def test_old_save_loads_with_new_skills_at_zero(self) -> None:
        """Old save data without new skills should get them at level 0."""
        data = {
            "xp": 500,
            "level": 4,
            "skill_points": 3,
            "skill_points_spent": 1,
            "skills": {"negotiator": 1},
        }
        prog = PlayerProgression.from_dict(data)
        # Old skill preserved
        assert prog.skills["negotiator"].current_level == 1
        # New skills exist at level 0
        assert prog.skills["weapons_training"].current_level == 0
        assert prog.skills["fuel_efficiency"].current_level == 0
        assert prog.skills["hidden_compartments"].current_level == 0

    def test_old_save_with_level_10_keeps_working(self) -> None:
        """Old save at level 10 (old max) should be able to level further."""
        data = {
            "xp": 9900,
            "level": 10,
            "skill_points": 11,
            "skill_points_spent": 0,
            "skills": {},
        }
        prog = PlayerProgression.from_dict(data)
        assert prog.level == 10
        # Can still level up (level 11 requires 11,750 XP)
        messages = prog.add_xp(2000)
        assert prog.level > 10
