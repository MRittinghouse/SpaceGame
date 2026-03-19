"""Tests for the R5 skill tree expansion — new skills, multi-rank, capstones, positions."""

from spacegame.models.progression import (
    PlayerProgression,
    SkillNode,
    SkillTreeType,
    create_default_skills,
    get_xp_threshold,
)


# === Tree Size & Structure ===


class TestTreeSizes:
    """Each tree should have the expected number of skills after expansion."""

    def test_trading_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.TRADING)) == 10

    def test_gathering_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.GATHERING)) == 8

    def test_mining_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.MINING)) == 11

    def test_leadership_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.LEADERSHIP)) == 10

    def test_social_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.SOCIAL)) == 10

    def test_ground_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.GROUND)) == 11

    def test_combat_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.COMBAT)) == 10

    def test_exploration_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.EXPLORATION)) == 10

    def test_smuggling_tree_size(self) -> None:
        prog = PlayerProgression()
        assert len(prog.get_skill_tree(SkillTreeType.SMUGGLING)) == 9

    def test_total_skill_count(self) -> None:
        skills = create_default_skills()
        assert len(skills) == 89

    def test_total_skill_points(self) -> None:
        """Total cost to max every skill should be 175."""
        skills = create_default_skills()
        total = sum(s.max_level * s.cost_per_level for s in skills.values())
        assert total == 175


# === Capstone Skills ===


CAPSTONES = [
    "trade_magnate",
    "master_prospector",
    "strip_miner",
    "legendary_captain",
    "voice_of_the_expanse",
    "battle_hardened",
    "ace_pilot",
    "trailblazer",
    "phantom",
]


class TestCapstoneSkills:
    """Every tree should have a capstone skill that's rank 1 with a prerequisite."""

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

    def test_capstones_are_leaf_nodes(self) -> None:
        """No skill should depend on a capstone."""
        skills = create_default_skills()
        capstone_set = set(CAPSTONES)
        for skill_id, skill in skills.items():
            if skill.prerequisite_id and skill.prerequisite_id in capstone_set:
                assert False, (
                    f"{skill_id} depends on capstone {skill.prerequisite_id}"
                )


# === Ground Combat Multi-Rank ===


class TestGroundMultiRank:
    """Ground Combat skills should have correct multi-rank values."""

    def test_scrapper_max_level_3(self) -> None:
        skills = create_default_skills()
        assert skills["scrapper"].max_level == 3

    def test_tough_hide_max_level_3(self) -> None:
        skills = create_default_skills()
        assert skills["tough_hide"].max_level == 3

    def test_quick_reflexes_max_level_2(self) -> None:
        skills = create_default_skills()
        assert skills["quick_reflexes"].max_level == 2

    def test_intimidating_presence_max_level_2(self) -> None:
        skills = create_default_skills()
        assert skills["intimidating_presence"].max_level == 2

    def test_last_stand_max_level_2(self) -> None:
        skills = create_default_skills()
        assert skills["last_stand"].max_level == 2

    def test_scrapper_bonus_stacks(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("scrapper")
        prog.level_up_skill("scrapper")
        prog.level_up_skill("scrapper")
        assert prog.get_bonus("ground_attack_bonus") == 3.0

    def test_tough_hide_bonus_stacks(self) -> None:
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        prog.level_up_skill("tough_hide")
        prog.level_up_skill("tough_hide")
        assert prog.get_bonus("ground_hp_bonus") == 4.0


# === Prerequisite Chain Integrity ===


class TestPrerequisiteChains:
    """All prerequisite references should be valid with no cycles."""

    def test_all_prerequisites_exist(self) -> None:
        skills = create_default_skills()
        for skill_id, skill in skills.items():
            if skill.prerequisite_id:
                assert skill.prerequisite_id in skills, (
                    f"{skill_id} references nonexistent prerequisite "
                    f"'{skill.prerequisite_id}'"
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


# === New Skill Spot Checks ===


class TestNewSkillsExist:
    """Verify each new skill from the expansion exists with correct attributes."""

    def test_supply_chain_mastery(self) -> None:
        skills = create_default_skills()
        s = skills["supply_chain_mastery"]
        assert s.tree == SkillTreeType.TRADING
        assert s.prerequisite_id == "commodity_specialist"
        assert s.max_level == 2

    def test_efficient_refining(self) -> None:
        skills = create_default_skills()
        s = skills["efficient_refining"]
        assert s.tree == SkillTreeType.GATHERING
        assert s.prerequisite_id == "refining_knowledge"

    def test_yield_mastery(self) -> None:
        skills = create_default_skills()
        s = skills["yield_mastery"]
        assert s.tree == SkillTreeType.GATHERING
        assert s.prerequisite_id == "rich_veins"

    def test_chain_reaction(self) -> None:
        skills = create_default_skills()
        s = skills["chain_reaction"]
        assert s.tree == SkillTreeType.MINING
        assert s.prerequisite_id == "deep_scan"

    def test_pressure_venting(self) -> None:
        skills = create_default_skills()
        s = skills["pressure_venting"]
        assert s.tree == SkillTreeType.MINING
        assert s.prerequisite_id == "passive_drill"

    def test_morale_officer(self) -> None:
        skills = create_default_skills()
        s = skills["morale_officer"]
        assert s.tree == SkillTreeType.LEADERSHIP
        assert s.prerequisite_id == "inspiring_leader"

    def test_cultural_savant(self) -> None:
        skills = create_default_skills()
        s = skills["cultural_savant"]
        assert s.tree == SkillTreeType.SOCIAL
        assert s.prerequisite_id == "empathic_read"

    def test_field_medic(self) -> None:
        skills = create_default_skills()
        s = skills["field_medic"]
        assert s.tree == SkillTreeType.GROUND
        assert s.prerequisite_id == "tough_hide"
        assert s.max_level == 2

    def test_terrain_reader(self) -> None:
        skills = create_default_skills()
        s = skills["terrain_reader"]
        assert s.tree == SkillTreeType.GROUND
        assert s.prerequisite_id == "quick_reflexes"

    def test_adaptive_fighter(self) -> None:
        skills = create_default_skills()
        s = skills["adaptive_fighter"]
        assert s.tree == SkillTreeType.GROUND
        assert s.prerequisite_id == "intimidating_presence"

    def test_combat_scavenger(self) -> None:
        skills = create_default_skills()
        s = skills["combat_scavenger"]
        assert s.tree == SkillTreeType.GROUND
        assert s.prerequisite_id == "field_medic"

    def test_rapid_fire(self) -> None:
        skills = create_default_skills()
        s = skills["rapid_fire"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id == "precision_targeting"

    def test_hull_reinforcement(self) -> None:
        skills = create_default_skills()
        s = skills["hull_reinforcement"]
        assert s.tree == SkillTreeType.COMBAT
        assert s.prerequisite_id == "shield_mastery"
        assert s.max_level == 3

    def test_anomaly_detector(self) -> None:
        skills = create_default_skills()
        s = skills["anomaly_detector"]
        assert s.tree == SkillTreeType.EXPLORATION
        assert s.prerequisite_id == "hazard_scanner"

    def test_field_repairs(self) -> None:
        skills = create_default_skills()
        s = skills["field_repairs"]
        assert s.tree == SkillTreeType.EXPLORATION
        assert s.prerequisite_id == "efficient_routing"

    def test_false_manifest(self) -> None:
        skills = create_default_skills()
        s = skills["false_manifest"]
        assert s.tree == SkillTreeType.SMUGGLING
        assert s.prerequisite_id == "scan_jamming"

    def test_underworld_rep(self) -> None:
        skills = create_default_skills()
        s = skills["underworld_rep"]
        assert s.tree == SkillTreeType.SMUGGLING
        assert s.prerequisite_id == "black_market_access"
