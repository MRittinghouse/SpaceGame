"""Tests for Phase 12C — Defensive identity and elemental mastery skill nodes.

Verifies that new skill nodes exist in the combat tree, have correct
prerequisites, and that bonus types are correctly defined.
"""

from spacegame.data_loader import get_data_loader


def _load_combat_skills() -> list[dict]:
    """Load combat skill tree skills from JSON via data loader."""
    dl = get_data_loader()
    dl.load_all()
    # Access the raw skill tree data
    import json
    with open("data/progression/skill_trees.json") as f:
        data = json.load(f)
    return data["skill_trees"]["combat"]["skills"]


class TestCombatTreeExpansion:
    """Verify combat tree has all new nodes."""

    def test_combat_tree_has_30_skills(self) -> None:
        skills = _load_combat_skills()
        assert len(skills) == 30, f"Expected 30 (10 existing + 20 new), got {len(skills)}"

    def test_hull_branch_skills_exist(self) -> None:
        skills = _load_combat_skills()
        ids = {s["id"] for s in skills}
        hull_ids = {"armor_expertise", "last_stand_mastery", "combat_field_repairs",
                    "endurance", "juggernaut_capstone"}
        missing = hull_ids - ids
        assert not missing, f"Missing hull branch skills: {missing}"

    def test_shield_branch_skills_exist(self) -> None:
        skills = _load_combat_skills()
        ids = {s["id"] for s in skills}
        shield_ids = {"shield_regen_skill", "overcharge", "shield_discipline",
                      "energy_shields", "sentinel_capstone"}
        missing = shield_ids - ids
        assert not missing, f"Missing shield branch skills: {missing}"

    def test_evasion_branch_skills_exist(self) -> None:
        skills = _load_combat_skills()
        ids = {s["id"] for s in skills}
        evasion_ids = {"afterburner", "counterstrike_mastery", "light_foot",
                       "slippery", "ghost_capstone"}
        missing = evasion_ids - ids
        assert not missing, f"Missing evasion branch skills: {missing}"

    def test_elemental_mastery_skills_exist(self) -> None:
        skills = _load_combat_skills()
        ids = {s["id"] for s in skills}
        elem_ids = {"burn_specialist", "ion_overcharge", "deep_freeze",
                    "suppression_expert", "elemental_versatility"}
        missing = elem_ids - ids
        assert not missing, f"Missing elemental mastery skills: {missing}"


class TestSkillPrerequisites:
    """Verify prerequisite chains are correct."""

    def test_hull_branch_prereqs(self) -> None:
        skills = _load_combat_skills()
        skill_map = {s["id"]: s for s in skills}

        assert skill_map["armor_expertise"]["prerequisite_id"] == "hull_reinforcement"
        assert skill_map["last_stand_mastery"]["prerequisite_id"] == "armor_expertise"
        assert skill_map["combat_field_repairs"]["prerequisite_id"] == "hull_reinforcement"
        assert skill_map["endurance"]["prerequisite_id"] == "hull_reinforcement"
        assert skill_map["juggernaut_capstone"]["prerequisite_id"] == "endurance"

    def test_shield_branch_prereqs(self) -> None:
        skills = _load_combat_skills()
        skill_map = {s["id"]: s for s in skills}

        assert skill_map["shield_regen_skill"]["prerequisite_id"] == "shield_mastery"
        assert skill_map["overcharge"]["prerequisite_id"] == "shield_regen_skill"
        assert skill_map["shield_discipline"]["prerequisite_id"] == "shield_mastery"
        assert skill_map["energy_shields"]["prerequisite_id"] == "shield_mastery"
        assert skill_map["sentinel_capstone"]["prerequisite_id"] == "energy_shields"

    def test_evasion_branch_prereqs(self) -> None:
        skills = _load_combat_skills()
        skill_map = {s["id"]: s for s in skills}

        assert skill_map["afterburner"]["prerequisite_id"] == "evasive_maneuvers"
        assert skill_map["counterstrike_mastery"]["prerequisite_id"] == "afterburner"
        assert skill_map["light_foot"]["prerequisite_id"] == "evasive_maneuvers"
        assert skill_map["slippery"]["prerequisite_id"] == "evasive_maneuvers"
        assert skill_map["ghost_capstone"]["prerequisite_id"] == "slippery"

    def test_elemental_mastery_prereqs(self) -> None:
        skills = _load_combat_skills()
        skill_map = {s["id"]: s for s in skills}

        assert skill_map["burn_specialist"]["prerequisite_id"] == "weapons_training"
        assert skill_map["ion_overcharge"]["prerequisite_id"] == "precision_targeting"
        assert skill_map["deep_freeze"]["prerequisite_id"] == "weapons_training"
        assert skill_map["suppression_expert"]["prerequisite_id"] == "precision_targeting"
        assert skill_map["elemental_versatility"]["prerequisite_id"] == "burn_specialist"

    def test_all_prereqs_reference_existing_skills(self) -> None:
        """Every prerequisite_id must point to another skill in the combat tree."""
        skills = _load_combat_skills()
        ids = {s["id"] for s in skills}
        for skill in skills:
            prereq = skill.get("prerequisite_id")
            if prereq:
                assert prereq in ids, (
                    f"Skill {skill['id']} has prereq '{prereq}' which doesn't exist"
                )


class TestCapstoneSkills:
    """Verify capstone skills are correctly configured."""

    def test_capstones_are_max_level_1(self) -> None:
        skills = _load_combat_skills()
        capstone_ids = {"juggernaut_capstone", "sentinel_capstone", "ghost_capstone",
                        "elemental_versatility"}
        for skill in skills:
            if skill["id"] in capstone_ids:
                assert skill["max_level"] == 1, (
                    f"Capstone {skill['id']} should be max_level 1"
                )

    def test_no_duplicate_skill_ids(self) -> None:
        skills = _load_combat_skills()
        ids = [s["id"] for s in skills]
        dupes = [id for id in ids if ids.count(id) > 1]
        assert not dupes, f"Duplicate skill IDs: {set(dupes)}"


class TestBonusTypes:
    """Verify bonus types are set correctly for combat bonuses."""

    def test_armor_expertise_bonus_type(self) -> None:
        skills = _load_combat_skills()
        skill = next(s for s in skills if s["id"] == "armor_expertise")
        assert skill["bonus_type"] == "armor_bonus"
        assert skill["bonus_per_level"] == 1.0

    def test_shield_regen_skill_bonus_type(self) -> None:
        skills = _load_combat_skills()
        skill = next(s for s in skills if s["id"] == "shield_regen_skill")
        assert skill["bonus_type"] == "shield_regen_bonus"
        assert skill["bonus_per_level"] == 2.0

    def test_afterburner_bonus_type(self) -> None:
        skills = _load_combat_skills()
        skill = next(s for s in skills if s["id"] == "afterburner")
        assert skill["bonus_type"] == "afterburner_bonus"
        assert skill["bonus_per_level"] == 5.0

    def test_burn_specialist_bonus_type(self) -> None:
        skills = _load_combat_skills()
        skill = next(s for s in skills if s["id"] == "burn_specialist")
        assert skill["bonus_type"] == "burn_damage_bonus"
        assert skill["bonus_per_level"] == 0.20
