"""
Tests for R5: Skill Tree Expansion.

Covers: uncapped leveling, formula-based XP, 6-tree structure,
milestone skill points, and backward compatibility.
"""

import pytest

from spacegame.models.progression import (
    PlayerProgression,
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


class TestCleanSkillPoints:
    """Tests for the clean 1-point-per-level system (S3)."""

    def test_level_up_gives_one_point(self) -> None:
        """Every level gives exactly 1 skill point."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(2))  # Level 2
        assert prog.skill_points == 1

    def test_level_5_gives_4_points(self) -> None:
        """4 level-ups to reach level 5 = 4 points (no milestones)."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(5))
        assert prog.skill_points == 4

    def test_level_10_gives_9_points(self) -> None:
        """9 level-ups to reach level 10 = 9 points."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        assert prog.skill_points == 9

    def test_level_20_gives_19_points(self) -> None:
        """19 level-ups to reach level 20 = 19 points."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(20))
        assert prog.skill_points == 19


# ============================================================================
# Six-Tree Structure
# ============================================================================


class TestSixTreeStructure:
    """Tests for the 6-tree skill system."""

    def test_commerce_tree_exists(self) -> None:
        assert SkillTreeType.COMMERCE.value == "commerce"

    def test_combat_tree_exists(self) -> None:
        assert SkillTreeType.COMBAT.value == "combat"

    def test_exploration_tree_exists(self) -> None:
        assert SkillTreeType.EXPLORATION.value == "exploration"

    def test_leadership_tree_exists(self) -> None:
        assert SkillTreeType.LEADERSHIP.value == "leadership"

    def test_social_tree_exists(self) -> None:
        assert SkillTreeType.SOCIAL.value == "social"

    def test_industry_tree_exists(self) -> None:
        assert SkillTreeType.INDUSTRY.value == "industry"

    def test_all_tree_types_count(self) -> None:
        """Should have 6 total tree types."""
        assert len(SkillTreeType) == 6

    def test_total_skill_count(self) -> None:
        """Should have 89 skills after SA-C2 (82 from NV-6.5 + 7 SA-C2 SA-arc nodes)."""
        skills = create_default_skills()
        assert len(skills) == 89

    def test_all_trees_have_skills(self) -> None:
        prog = PlayerProgression()
        for tree_type in SkillTreeType:
            skills = prog.get_skill_tree(tree_type)
            assert len(skills) >= 5, f"{tree_type.value} tree should have at least 5 skills"


# ============================================================================
# Combat Tree
# ============================================================================


class TestCombatTree:
    """Tests for the Combat skill tree (streamlined, absorbed Ground Combat)."""

    def test_combat_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "weapon_specialization",
            "evasive_maneuvers",
            "shield_mastery",
            "precision_strike",
            "tactical_retreat",
            "armor_expertise",
            "ground_veteran",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_combat_tree_count(self) -> None:
        prog = PlayerProgression()
        combat_skills = prog.get_skill_tree(SkillTreeType.COMBAT)
        assert len(combat_skills) == 22

    def test_weapon_specialization_is_root(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["weapon_specialization"]
        assert skill.prerequisite_id is None
        assert skill.tree == SkillTreeType.COMBAT
        assert skill.max_level == 3

    def test_weapon_specialization_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("weapon_specialization")
        prog.level_up_skill("weapon_specialization")
        assert prog.get_bonus("weapon_damage") == pytest.approx(0.20)

    def test_capstone_paths_exist(self) -> None:
        """All three combat capstones should exist."""
        prog = PlayerProgression()
        for cap in ["juggernaut_capstone", "sentinel_capstone", "ghost_capstone"]:
            assert cap in prog.skills, f"{cap} missing"
            assert prog.skills[cap].max_level == 1


# ============================================================================
# Commerce Tree
# ============================================================================


class TestCommerceTree:
    """Tests for the Commerce skill tree (merged Trading + Smuggling)."""

    def test_commerce_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "negotiator",
            "trade_network",
            "market_eye",
            "market_insider",
            "cargo_mastery",
            "smugglers_eye",
            "black_market_connections",
            "insurance",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_negotiator_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("negotiator")
        prog.level_up_skill("negotiator")
        assert prog.get_bonus("buy_price_reduction") == pytest.approx(0.10)


# ============================================================================
# Exploration Tree
# ============================================================================


class TestExplorationTree:
    """Tests for the Exploration skill tree."""

    def test_exploration_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "fuel_efficiency",
            "salvage_instinct",
            "system_intel",
            "safe_passage",
            "route_planner",
            "field_repairs",
            "emergency_reserves",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_fuel_efficiency_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("fuel_efficiency")
        prog.level_up_skill("fuel_efficiency")
        prog.level_up_skill("fuel_efficiency")
        assert prog.get_bonus("fuel_reduction") == pytest.approx(0.30)


# ============================================================================
# Industry Tree
# ============================================================================


class TestIndustryTree:
    """Tests for the Industry skill tree (merged Mining + Gathering)."""

    def test_industry_skills_exist(self) -> None:
        prog = PlayerProgression()
        expected = [
            "click_power",
            "passive_drill",
            "efficient_refining",
            "rich_veins",
            "drone_fleet",
            "forge_mastery",
            "ore_sense",
            "material_science",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing"

    def test_click_power_bonus(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("click_power")
        prog.level_up_skill("click_power")
        prog.level_up_skill("click_power")
        assert prog.get_bonus("click_drill_power") == pytest.approx(0.75)


# ============================================================================
# Backward Compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Old saves with old 9-tree skills should load via migration map."""

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
        # Old skill preserved (negotiator still exists)
        assert prog.skills["negotiator"].current_level == 1
        # New skills exist at level 0
        assert prog.skills["weapon_specialization"].current_level == 0
        assert prog.skills["fuel_efficiency"].current_level == 0

    def test_old_save_migrates_renamed_skills(self) -> None:
        """Old skill IDs should migrate to new equivalents."""
        data = {
            "xp": 500,
            "level": 4,
            "skill_points": 10,
            "skill_points_spent": 3,
            "skills": {
                "weapons_training": 2,  # -> weapon_specialization
                "stellar_cartography": 1,  # -> system_intel
                "hidden_compartments": 1,  # kept as-is
            },
        }
        prog = PlayerProgression.from_dict(data)
        assert prog.skills["weapon_specialization"].current_level == 2
        assert prog.skills["system_intel"].current_level == 1
        assert prog.skills["hidden_compartments"].current_level == 1

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
        messages = prog.add_xp(2000)
        assert prog.level > 10
