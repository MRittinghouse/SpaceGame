"""
Tests for the player progression system.
"""

import pytest
from spacegame.models.progression import (
    PlayerProgression,
    SkillNode,
    SkillTreeType,
    LEVEL_XP_THRESHOLDS,
    create_default_skills,
    get_xp_threshold,
)


class TestPlayerProgression:
    """Tests for PlayerProgression."""

    def test_initial_state(self):
        prog = PlayerProgression()
        assert prog.xp == 0
        assert prog.level == 1
        assert prog.skill_points == 0
        assert len(prog.skills) == 109  # 9 trees, 89 base + 20 Phase 12C combat expansion

    def test_add_xp(self):
        prog = PlayerProgression()
        messages = prog.add_xp(50)
        assert prog.xp == 50
        assert prog.level == 1
        assert len(messages) == 0

    def test_level_up(self):
        prog = PlayerProgression()
        messages = prog.add_xp(get_xp_threshold(2))
        assert prog.level == 2
        assert prog.skill_points == 1
        assert len(messages) == 1
        assert "Level up" in messages[0]

    def test_multiple_level_ups(self):
        prog = PlayerProgression()
        messages = prog.add_xp(get_xp_threshold(4))
        assert prog.level == 4
        assert prog.skill_points == 3

    def test_xp_progress(self):
        prog = PlayerProgression()
        prog.add_xp(50)
        progress = prog.get_xp_progress()
        assert 0.0 < progress < 1.0

    def test_xp_for_next_level(self):
        prog = PlayerProgression()
        assert prog.get_xp_for_next_level() == get_xp_threshold(2)

    def test_no_level_cap(self):
        prog = PlayerProgression()
        prog.add_xp(50000)
        assert prog.level > 10, "No level cap — should level past 10"
        assert prog.get_xp_for_next_level() is not None


class TestSkillNode:
    """Tests for SkillNode."""

    def test_initial_state(self):
        skill = SkillNode(
            id="test",
            name="Test",
            description="Test",
            tree=SkillTreeType.TRADING,
            max_level=3,
            bonus_type="test_bonus",
            bonus_per_level=0.1,
        )
        assert not skill.is_unlocked
        assert not skill.is_maxed
        assert skill.get_bonus() == 0.0

    def test_unlock(self):
        skill = SkillNode(
            id="test",
            name="Test",
            description="Test",
            tree=SkillTreeType.TRADING,
            max_level=3,
            bonus_type="test_bonus",
            bonus_per_level=0.1,
        )
        skill.current_level = 1
        assert skill.is_unlocked
        assert skill.get_bonus() == pytest.approx(0.1)

    def test_max_level(self):
        skill = SkillNode(
            id="test",
            name="Test",
            description="Test",
            tree=SkillTreeType.TRADING,
            max_level=3,
            bonus_type="test_bonus",
            bonus_per_level=0.1,
        )
        skill.current_level = 3
        assert skill.is_maxed
        assert skill.get_bonus() == pytest.approx(0.3)


class TestSkillInvestment:
    """Tests for investing skill points."""

    def test_level_up_skill(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(2))  # Level 2, 1 skill point
        success, msg = prog.level_up_skill("negotiator")
        assert success
        assert prog.skills["negotiator"].current_level == 1
        assert prog.get_available_skill_points() == 0

    def test_insufficient_points(self):
        prog = PlayerProgression()
        success, msg = prog.level_up_skill("negotiator")
        assert not success

    def test_prerequisite_required(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(3))  # Level 3, 2 skill points
        success, msg = prog.level_up_skill("market_eye")
        assert not success
        assert "Requires" in msg

    def test_prerequisite_met(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(3))  # Level 3, 2 skill points
        prog.level_up_skill("negotiator")
        success, msg = prog.level_up_skill("market_eye")
        assert success

    def test_maxed_skill(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))  # Lots of points
        prog.level_up_skill("negotiator")
        prog.level_up_skill("negotiator")
        prog.level_up_skill("negotiator")
        success, msg = prog.level_up_skill("negotiator")
        assert not success
        assert "maxed" in msg.lower()

    def test_get_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(3))  # Level 3, 2 skill points
        prog.level_up_skill("negotiator")
        prog.level_up_skill("negotiator")
        bonus = prog.get_bonus("buy_price_reduction")
        assert bonus == pytest.approx(0.04)

    def test_get_skill_tree(self):
        prog = PlayerProgression()
        trading_skills = prog.get_skill_tree(SkillTreeType.TRADING)
        gathering_skills = prog.get_skill_tree(SkillTreeType.GATHERING)
        leadership_skills = prog.get_skill_tree(SkillTreeType.LEADERSHIP)
        assert len(trading_skills) == 10
        assert len(gathering_skills) == 8
        assert len(leadership_skills) == 10


class TestProgressionSerialization:
    """Tests for save/load of progression data."""

    def test_to_dict(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(2))
        prog.level_up_skill("negotiator")
        data = prog.to_dict()
        assert data["xp"] == get_xp_threshold(2)
        assert data["level"] == 2
        assert data["skills"]["negotiator"] == 1

    def test_from_dict(self):
        data = {
            "xp": 500,
            "level": 4,
            "skill_points": 3,
            "skill_points_spent": 2,
            "skills": {"negotiator": 2},
        }
        prog = PlayerProgression.from_dict(data)
        assert prog.xp == 500
        assert prog.level == 4
        assert prog.skills["negotiator"].current_level == 2
        assert prog.get_available_skill_points() == 1

    def test_roundtrip(self):
        prog = PlayerProgression()
        prog.add_xp(1200)  # Enough for level 3 (2 skill points)
        prog.level_up_skill("negotiator")
        prog.level_up_skill("efficient_drills")

        data = prog.to_dict()
        restored = PlayerProgression.from_dict(data)

        assert restored.xp == prog.xp
        assert restored.level == prog.level
        assert restored.skills["negotiator"].current_level == 1
        assert restored.skills["efficient_drills"].current_level == 1


class TestLeadershipTree:
    """Tests for the Leadership & Operations skill tree."""

    def test_leadership_skills_exist(self):
        prog = PlayerProgression()
        expected = [
            "crew_manager",
            "diplomatic_relations",
            "inspiring_leader",
            "tariff_negotiation",
            "crew_mentor",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing from skills"

    def test_crew_manager_is_root(self):
        prog = PlayerProgression()
        skill = prog.skills["crew_manager"]
        assert skill.prerequisite_id is None
        assert skill.max_level == 1
        assert skill.tree == SkillTreeType.LEADERSHIP

    def test_diplomatic_relations_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["diplomatic_relations"]
        assert skill.prerequisite_id == "crew_manager"
        assert skill.max_level == 2

    def test_inspiring_leader_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["inspiring_leader"]
        assert skill.prerequisite_id == "crew_manager"
        assert skill.max_level == 2

    def test_tariff_negotiation_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["tariff_negotiation"]
        assert skill.prerequisite_id == "diplomatic_relations"
        assert skill.max_level == 2

    def test_crew_mentor_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["crew_mentor"]
        assert skill.prerequisite_id == "inspiring_leader"
        assert skill.max_level == 2

    def test_crew_manager_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))  # Plenty of points
        prog.level_up_skill("crew_manager")
        assert prog.get_bonus("crew_slot_bonus") == pytest.approx(1.0)

    def test_diplomatic_relations_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        prog.level_up_skill("crew_manager")
        prog.level_up_skill("diplomatic_relations")
        prog.level_up_skill("diplomatic_relations")
        assert prog.get_bonus("reputation_gain_bonus") == pytest.approx(2.0)

    def test_tariff_negotiation_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        prog.level_up_skill("crew_manager")
        prog.level_up_skill("diplomatic_relations")
        prog.level_up_skill("tariff_negotiation")
        prog.level_up_skill("tariff_negotiation")
        assert prog.get_bonus("tariff_reduction") == pytest.approx(0.10)

    def test_crew_mentor_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        prog.level_up_skill("crew_manager")
        prog.level_up_skill("inspiring_leader")
        prog.level_up_skill("crew_mentor")
        prog.level_up_skill("crew_mentor")
        assert prog.get_bonus("crew_xp_bonus") == pytest.approx(4.0)

    def test_prerequisite_blocks_investment(self):
        """Cannot invest in diplomatic_relations without crew_manager."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        success, msg = prog.level_up_skill("diplomatic_relations")
        assert not success
        assert "Requires" in msg


class TestSocialTree:
    """Tests for the Social skill tree."""

    def test_social_tree_type_exists(self):
        assert SkillTreeType.SOCIAL.value == "social"

    def test_social_skills_exist(self):
        prog = PlayerProgression()
        expected = ["silver_tongue", "commanding_presence", "keen_insight"]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing from skills"

    def test_silver_tongue_is_root(self):
        prog = PlayerProgression()
        skill = prog.skills["silver_tongue"]
        assert skill.prerequisite_id is None
        assert skill.max_level == 2
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.bonus_type == "persuasion_bonus"

    def test_commanding_presence_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["commanding_presence"]
        assert skill.prerequisite_id == "silver_tongue"
        assert skill.max_level == 2
        assert skill.bonus_type == "intimidation_bonus"

    def test_keen_insight_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["keen_insight"]
        assert skill.prerequisite_id == "silver_tongue"
        assert skill.max_level == 2
        assert skill.bonus_type == "observation_bonus"

    def test_social_tree_count(self):
        prog = PlayerProgression()
        social_skills = prog.get_skill_tree(SkillTreeType.SOCIAL)
        assert len(social_skills) == 10

    def test_social_skill_bonuses(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))  # Plenty of points
        prog.level_up_skill("silver_tongue")
        prog.level_up_skill("silver_tongue")
        assert prog.get_bonus("persuasion_bonus") == pytest.approx(2.0)

    def test_social_prereq_blocks(self):
        """Cannot invest in commanding_presence without silver_tongue."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        success, msg = prog.level_up_skill("commanding_presence")
        assert not success
        assert "Requires" in msg

    def test_serialization_backward_compatible(self):
        """Old saves without social skills should load with level 0 defaults."""
        data = {
            "xp": 500,
            "level": 4,
            "skill_points": 3,
            "skill_points_spent": 1,
            "skills": {"negotiator": 1},
        }
        prog = PlayerProgression.from_dict(data)
        assert prog.skills["silver_tongue"].current_level == 0
        assert prog.skills["commanding_presence"].current_level == 0
        assert prog.skills["keen_insight"].current_level == 0
