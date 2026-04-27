"""Tests for the 6-tree skill structure after S1 overhaul.

Covers: tree sizes, capstones, prerequisite integrity, new skill spot checks.
"""

from spacegame.models.progression import (
    PlayerProgression,
    SkillTreeType,
    create_default_skills,
)

# === Tree Size & Structure ===


class TestTreeSizes:
    """Each tree should have the expected number of skills."""

    def test_commerce_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.COMMERCE)) == 14  # +2 SA-C2

    def test_combat_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.COMBAT)) == 22

    def test_exploration_tree_size(self) -> None:
        prog = PlayerProgression()
        # +1 (steady_stick, NV-6.5 Piloting base)
        assert len(prog.get_skill_tree(SkillTreeType.EXPLORATION)) == 12

    def test_leadership_tree_size(self) -> None:
        prog = PlayerProgression()
        # +2 (give_the_word + command_presence, NV-6.5 Leadership axis) + 2 SA-C2
        assert len(prog.get_skill_tree(SkillTreeType.LEADERSHIP)) == 13

    def test_social_tree_size(self) -> None:
        prog = PlayerProgression()
        # +2 (poker_face + ghost_protocol, NV-6.5 Deception axis) + 2 SA-C2
        assert len(prog.get_skill_tree(SkillTreeType.SOCIAL)) == 15

    def test_industry_tree_size(self) -> None:
        prog = PlayerProgression()
        # +2 (tool_sense + engineer_insight, NV-6.5 Technical axis) + 1 SA-C2
        assert len(prog.get_skill_tree(SkillTreeType.INDUSTRY)) == 13

    def test_total_skill_count(self) -> None:
        skills = create_default_skills()
        # NV-6.5: 75 + 7 new skill-check axis skills + 7 SA-C2
        assert len(skills) == 89

    def test_total_max_levels(self) -> None:
        """Total cost to max every skill should be 160."""
        skills = create_default_skills()
        total = sum(s.max_level * s.cost_per_level for s in skills.values())
        # NV-6.5: 132 + (7 NV skills × max_level 2) + (7 SA-C2 skills × max_level 2) = 160
        assert total == 160

    def test_six_trees_only(self) -> None:
        """Exactly 6 tree types should exist."""
        assert len(list(SkillTreeType)) == 6


# === Capstone Skills ===


CAPSTONES = [
    "insurance",  # Commerce
    "juggernaut_capstone",  # Combat — Hull path
    "sentinel_capstone",  # Combat — Shield path
    "ghost_capstone",  # Combat — Evasion path
    "volley_commander",  # Combat — Offense path
    "emergency_reserves",  # Exploration
    "anomaly_sense",  # Exploration
    "legend_of_the_expanse",  # Leadership
    "peacemaker",  # Social
    "ore_sense",  # Industry
    "material_science",  # Industry
]


class TestCapstoneSkills:
    """Every tree should have capstone skills that are rank 1 with prerequisites."""

    def test_all_capstones_exist(self) -> None:
        skills = create_default_skills()
        for cap_id in CAPSTONES:
            assert cap_id in skills, f"Capstone {cap_id} missing"

    def test_capstones_are_rank_1(self) -> None:
        skills = create_default_skills()
        for cap_id in CAPSTONES:
            assert skills[cap_id].max_level == 1, (
                f"{cap_id} should be max_level=1, got {skills[cap_id].max_level}"
            )

    def test_capstones_have_prerequisites(self) -> None:
        skills = create_default_skills()
        for cap_id in CAPSTONES:
            assert skills[cap_id].prerequisite_id is not None, (
                f"{cap_id} should have a prerequisite"
            )


# === Prerequisite Chain Integrity ===


class TestPrerequisiteChains:
    """All prerequisite references should be valid with no cycles."""

    def test_all_prerequisites_exist(self) -> None:
        skills = create_default_skills()
        for skill_id, skill in skills.items():
            if skill.prerequisite_id:
                assert skill.prerequisite_id in skills, (
                    f"{skill_id} references nonexistent prerequisite '{skill.prerequisite_id}'"
                )

    def test_prerequisites_in_same_tree(self) -> None:
        skills = create_default_skills()
        for skill_id, skill in skills.items():
            if skill.prerequisite_id:
                prereq = skills[skill.prerequisite_id]
                assert skill.tree == prereq.tree, (
                    f"{skill_id} ({skill.tree.value}) has cross-tree prerequisite "
                    f"'{skill.prerequisite_id}' ({prereq.tree.value})"
                )

    def test_no_circular_prerequisites(self) -> None:
        skills = create_default_skills()
        for skill_id in skills:
            visited: set[str] = set()
            current = skill_id
            while current and current not in visited:
                visited.add(current)
                current = skills[current].prerequisite_id
            if current is not None:
                assert False, f"Circular prerequisite chain involving {skill_id}"

    def test_every_tree_has_root_skills(self) -> None:
        """Each tree should have at least one root skill (no prerequisite)."""
        skills = create_default_skills()
        for tree_type in SkillTreeType:
            tree_skills = [s for s in skills.values() if s.tree == tree_type]
            roots = [s for s in tree_skills if s.prerequisite_id is None]
            assert len(roots) >= 1, f"{tree_type.value} has no root skills"


# === New Skill Spot Checks ===


class TestNewSkillsExist:
    """Verify key new skills from the 6-tree overhaul exist with correct attributes."""

    def test_cargo_mastery(self) -> None:
        skills = create_default_skills()
        s = skills["cargo_mastery"]
        assert s.tree == SkillTreeType.COMMERCE
        assert s.prerequisite_id == "trade_network"
        assert s.max_level == 3

    def test_price_memory(self) -> None:
        skills = create_default_skills()
        s = skills["price_memory"]
        assert s.tree == SkillTreeType.COMMERCE
        assert s.prerequisite_id == "market_insider"

    def test_weapon_specialization(self) -> None:
        skills = create_default_skills()
        s = skills["weapon_specialization"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id is None
        assert s.max_level == 3

    def test_precision_strike(self) -> None:
        skills = create_default_skills()
        s = skills["precision_strike"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id == "weapon_specialization"
        assert s.max_level == 2

    def test_elemental_affinity(self) -> None:
        skills = create_default_skills()
        s = skills["elemental_affinity"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.max_level == 1

    def test_momentum_surge(self) -> None:
        skills = create_default_skills()
        s = skills["momentum_surge"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.bonus_type == "starting_momentum"

    def test_battle_awareness(self) -> None:
        skills = create_default_skills()
        s = skills["battle_awareness"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.max_level == 1

    def test_ground_veteran(self) -> None:
        skills = create_default_skills()
        s = skills["ground_veteran"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id == "weapon_specialization"

    def test_combat_scavenger(self) -> None:
        skills = create_default_skills()
        s = skills["combat_scavenger"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id == "ground_veteran"

    def test_system_intel(self) -> None:
        skills = create_default_skills()
        s = skills["system_intel"]
        assert s.tree == SkillTreeType.EXPLORATION
        assert s.prerequisite_id == "fuel_efficiency"
        assert s.max_level == 2

    def test_safe_passage(self) -> None:
        skills = create_default_skills()
        s = skills["safe_passage"]
        assert s.tree == SkillTreeType.EXPLORATION
        assert s.bonus_type == "encounter_reduction"

    def test_field_repairs(self) -> None:
        skills = create_default_skills()
        s = skills["field_repairs"]
        assert s.tree == SkillTreeType.EXPLORATION
        assert s.prerequisite_id == "fuel_efficiency"

    def test_battle_commander(self) -> None:
        skills = create_default_skills()
        s = skills["battle_commander"]
        assert s.tree == SkillTreeType.LEADERSHIP
        assert s.prerequisite_id == "crew_manager"

    def test_unbreakable_bonds(self) -> None:
        skills = create_default_skills()
        s = skills["unbreakable_bonds"]
        assert s.tree == SkillTreeType.LEADERSHIP
        assert s.bonus_type == "loyalty_floor"

    def test_read_the_room(self) -> None:
        skills = create_default_skills()
        s = skills["read_the_room"]
        assert s.tree == SkillTreeType.SOCIAL
        assert s.prerequisite_id == "empathic_read"

    def test_crew_whisperer(self) -> None:
        skills = create_default_skills()
        s = skills["crew_whisperer"]
        assert s.tree == SkillTreeType.SOCIAL
        assert s.bonus_type == "crew_whisperer"

    def test_drone_fleet(self) -> None:
        skills = create_default_skills()
        s = skills["drone_fleet"]
        assert s.tree == SkillTreeType.INDUSTRY
        assert s.max_level == 3

    def test_seismic_charge(self) -> None:
        skills = create_default_skills()
        s = skills["seismic_charge"]
        assert s.tree == SkillTreeType.INDUSTRY
        assert s.prerequisite_id == "rich_veins"

    def test_forge_mastery(self) -> None:
        skills = create_default_skills()
        s = skills["forge_mastery"]
        assert s.tree == SkillTreeType.INDUSTRY
        assert s.bonus_type == "refining_yield_bonus"

    def test_efficient_refining(self) -> None:
        skills = create_default_skills()
        s = skills["efficient_refining"]
        assert s.tree == SkillTreeType.INDUSTRY
        assert s.prerequisite_id is None  # Root skill

    def test_hull_reinforcement(self) -> None:
        skills = create_default_skills()
        s = skills["hull_reinforcement"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id == "armor_expertise"
        assert s.max_level == 3

    def test_cultural_savant(self) -> None:
        skills = create_default_skills()
        s = skills["cultural_savant"]
        assert s.tree == SkillTreeType.SOCIAL
        assert s.prerequisite_id == "empathic_read"

    def test_anomaly_detector(self) -> None:
        skills = create_default_skills()
        s = skills["anomaly_detector"]
        assert s.tree == SkillTreeType.EXPLORATION
        assert s.prerequisite_id == "safe_passage"
