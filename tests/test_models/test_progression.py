"""
Tests for the player progression system.
"""

import pytest

from spacegame.models.progression import (
    _SKILL_MIGRATION_MAP,
    PlayerProgression,
    SkillNode,
    SkillTreeType,
    get_xp_threshold,
)


class TestPlayerProgression:
    """Tests for PlayerProgression."""

    def test_initial_state(self):
        prog = PlayerProgression()
        assert prog.xp == 0
        assert prog.level == 1
        assert prog.skill_points == 0
        assert len(prog.skills) == 89  # 6 trees + 7 NV-6.5 skill-axis additions + 7 SA-C2

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
        prog.add_xp(get_xp_threshold(4))
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
            tree=SkillTreeType.COMMERCE,
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
            tree=SkillTreeType.COMMERCE,
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
            tree=SkillTreeType.COMMERCE,
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
        success, _msg = prog.level_up_skill("negotiator")
        assert success
        assert prog.skills["negotiator"].current_level == 1
        assert prog.get_available_skill_points() == 0

    def test_insufficient_points(self):
        prog = PlayerProgression()
        success, _msg = prog.level_up_skill("negotiator")
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
        success, _msg = prog.level_up_skill("market_eye")
        assert success

    def test_maxed_skill(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))  # Lots of points
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
        assert bonus == pytest.approx(0.10)

    def test_get_skill_tree(self):
        prog = PlayerProgression()
        commerce_skills = prog.get_skill_tree(SkillTreeType.COMMERCE)
        combat_skills = prog.get_skill_tree(SkillTreeType.COMBAT)
        leadership_skills = prog.get_skill_tree(SkillTreeType.LEADERSHIP)
        assert len(commerce_skills) == 14  # +2 SA-C2 (lot_appraiser, spread_trader)
        assert len(combat_skills) == 22
        assert len(leadership_skills) == 13  # +2 NV-6.5 (give_the_word, command_presence) + 2 SA-C2


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
        prog.level_up_skill("click_power")

        data = prog.to_dict()
        restored = PlayerProgression.from_dict(data)

        assert restored.xp == prog.xp
        assert restored.level == prog.level
        assert restored.skills["negotiator"].current_level == 1
        assert restored.skills["click_power"].current_level == 1


class TestLeadershipTree:
    """Tests for the Leadership & Operations skill tree."""

    def test_leadership_skills_exist(self):
        prog = PlayerProgression()
        expected = [
            "crew_manager",
            "diplomatic_relations",
            "inspiring_leader",
            "crew_mentor",
            "battle_commander",
        ]
        for skill_id in expected:
            assert skill_id in prog.skills, f"{skill_id} missing from skills"

    def test_crew_manager_is_root(self):
        prog = PlayerProgression()
        skill = prog.skills["crew_manager"]
        assert skill.prerequisite_id is None
        assert skill.max_level == 2
        assert skill.tree == SkillTreeType.LEADERSHIP

    def test_diplomatic_relations_is_root(self):
        prog = PlayerProgression()
        skill = prog.skills["diplomatic_relations"]
        assert skill.prerequisite_id is None
        assert skill.max_level == 2

    def test_inspiring_leader_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["inspiring_leader"]
        assert skill.prerequisite_id == "crew_manager"
        assert skill.max_level == 2

    def test_battle_commander_prereq(self):
        prog = PlayerProgression()
        skill = prog.skills["battle_commander"]
        assert skill.prerequisite_id == "crew_manager"
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
        prog.level_up_skill("diplomatic_relations")
        prog.level_up_skill("diplomatic_relations")
        assert prog.get_bonus("reputation_gain_bonus") == pytest.approx(2.0)

    def test_battle_commander_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        prog.level_up_skill("crew_manager")
        prog.level_up_skill("battle_commander")
        prog.level_up_skill("battle_commander")
        assert prog.get_bonus("crew_combat_damage") == pytest.approx(0.30)

    def test_crew_mentor_bonus(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        prog.level_up_skill("crew_manager")
        prog.level_up_skill("inspiring_leader")
        prog.level_up_skill("crew_mentor")
        prog.level_up_skill("crew_mentor")
        assert prog.get_bonus("crew_xp_bonus") == pytest.approx(4.0)

    def test_prerequisite_blocks_investment(self):
        """Cannot invest in inspiring_leader without crew_manager."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        success, msg = prog.level_up_skill("inspiring_leader")
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

    def test_commanding_presence_is_root(self):
        prog = PlayerProgression()
        skill = prog.skills["commanding_presence"]
        assert skill.prerequisite_id is None
        assert skill.max_level == 2
        assert skill.bonus_type == "intimidation_bonus"

    def test_keen_insight_is_root(self):
        prog = PlayerProgression()
        skill = prog.skills["keen_insight"]
        assert skill.prerequisite_id is None
        assert skill.max_level == 2
        assert skill.bonus_type == "observation_bonus"

    def test_social_tree_count(self):
        prog = PlayerProgression()
        social_skills = prog.get_skill_tree(SkillTreeType.SOCIAL)
        assert len(social_skills) == 15  # +2 NV-6.5 (poker_face, ghost_protocol) + 2 SA-C2

    def test_social_skill_bonuses(self):
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))  # Plenty of points
        prog.level_up_skill("silver_tongue")
        prog.level_up_skill("silver_tongue")
        assert prog.get_bonus("persuasion_bonus") == pytest.approx(2.0)

    def test_social_prereq_blocks(self):
        """Cannot invest in master_negotiator without commanding_presence."""
        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(15))
        success, msg = prog.level_up_skill("master_negotiator")
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


# ============================================================================
# SA-C2: Station Anchors Arc — Seven New Skill Nodes
# ============================================================================

_SA_C2_SKILL_IDS = [
    "lot_appraiser",
    "coalition_sway",
    "delegate_reach",
    "mediation_instinct",
    "spread_trader",
    "research_yield",
    "research_oversight",
]


def _make_rich_prog() -> PlayerProgression:
    """Return a progression with abundant skill points (20 points)."""
    prog = PlayerProgression()
    prog.add_xp(get_xp_threshold(21))  # 20 levels = 20 skill points
    return prog


class TestSACArcSkills:
    """Tests for the 7 SA-arc skill nodes added in SA-C2."""

    # === Field correctness ===

    def test_lot_appraiser_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["lot_appraiser"]
        assert skill.id == "lot_appraiser"
        assert skill.name == "Lot Appraiser"
        assert skill.description == "+5% post-auction valuation accuracy per level"
        assert skill.tree == SkillTreeType.COMMERCE
        assert skill.prerequisite_id == "market_eye"
        assert skill.max_level == 2
        assert skill.bonus_type == "auction_lot_appraisal_bonus"
        assert skill.bonus_per_level == pytest.approx(0.05)

    def test_coalition_sway_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["coalition_sway"]
        assert skill.id == "coalition_sway"
        assert skill.name == "Coalition Sway"
        assert (
            skill.description == "+10% delegate persuasion modifier per level in Politics disputes"
        )
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "silver_tongue"
        assert skill.max_level == 2
        assert skill.bonus_type == "coalition_sway_bonus"
        assert skill.bonus_per_level == pytest.approx(0.10)

    def test_delegate_reach_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["delegate_reach"]
        assert skill.id == "delegate_reach"
        assert skill.name == "Delegate Reach"
        assert (
            skill.description
            == "+0.5 to delegate pre-commitment cap per level before a Politics vote"
        )
        assert skill.tree == SkillTreeType.LEADERSHIP
        assert skill.prerequisite_id == "give_the_word"
        assert skill.max_level == 2
        assert skill.bonus_type == "coalition_size_bonus"
        assert skill.bonus_per_level == pytest.approx(0.5)

    def test_mediation_instinct_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["mediation_instinct"]
        assert skill.id == "mediation_instinct"
        assert skill.name == "Mediation Instinct"
        assert skill.description == "+10% partial-win odds in mediation resolutions per level"
        assert skill.tree == SkillTreeType.SOCIAL
        assert skill.prerequisite_id == "empathic_read"
        assert skill.max_level == 2
        assert skill.bonus_type == "arbitration_neutrality_bonus"
        assert skill.bonus_per_level == pytest.approx(0.10)

    def test_spread_trader_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["spread_trader"]
        assert skill.id == "spread_trader"
        assert skill.name == "Spread Trader"
        assert skill.description == "+5% futures contract spread reduction per level on entry"
        assert skill.tree == SkillTreeType.COMMERCE
        assert skill.prerequisite_id == "tariff_negotiation"
        assert skill.max_level == 2
        assert skill.bonus_type == "speculator_premium_reduction"
        assert skill.bonus_per_level == pytest.approx(0.05)

    def test_research_yield_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["research_yield"]
        assert skill.id == "research_yield"
        assert skill.name == "Research Yield"
        assert skill.description == "+5% project return at the Okafor Institute per level"
        assert skill.tree == SkillTreeType.INDUSTRY
        assert skill.prerequisite_id == "efficient_refining"
        assert skill.max_level == 2
        assert skill.bonus_type == "research_yield_bonus"
        assert skill.bonus_per_level == pytest.approx(0.05)

    def test_research_oversight_exists_with_correct_fields(self) -> None:
        prog = PlayerProgression()
        skill = prog.skills["research_oversight"]
        assert skill.id == "research_oversight"
        assert skill.name == "Research Oversight"
        assert (
            skill.description
            == "+5% project failure odds reduction per level at the Okafor Institute"
        )
        assert skill.tree == SkillTreeType.LEADERSHIP
        assert skill.prerequisite_id == "diplomatic_relations"
        assert skill.max_level == 2
        assert skill.bonus_type == "research_risk_reduction"
        assert skill.bonus_per_level == pytest.approx(0.05)

    # === Bonus at levels ===

    def test_lot_appraiser_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("auction_lot_appraisal_bonus") == pytest.approx(0.0)
        prog.level_up_skill("negotiator")
        prog.level_up_skill("market_eye")
        prog.level_up_skill("lot_appraiser")
        assert prog.get_bonus("auction_lot_appraisal_bonus") == pytest.approx(0.05)
        prog.level_up_skill("lot_appraiser")
        assert prog.get_bonus("auction_lot_appraisal_bonus") == pytest.approx(0.10)

    def test_coalition_sway_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("coalition_sway_bonus") == pytest.approx(0.0)
        prog.level_up_skill("silver_tongue")
        prog.level_up_skill("coalition_sway")
        assert prog.get_bonus("coalition_sway_bonus") == pytest.approx(0.10)
        prog.level_up_skill("coalition_sway")
        assert prog.get_bonus("coalition_sway_bonus") == pytest.approx(0.20)

    def test_delegate_reach_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("coalition_size_bonus") == pytest.approx(0.0)
        prog.level_up_skill("give_the_word")
        prog.level_up_skill("delegate_reach")
        assert prog.get_bonus("coalition_size_bonus") == pytest.approx(0.5)
        prog.level_up_skill("delegate_reach")
        assert prog.get_bonus("coalition_size_bonus") == pytest.approx(1.0)

    def test_mediation_instinct_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("arbitration_neutrality_bonus") == pytest.approx(0.0)
        prog.level_up_skill("keen_insight")
        prog.level_up_skill("empathic_read")
        prog.level_up_skill("mediation_instinct")
        assert prog.get_bonus("arbitration_neutrality_bonus") == pytest.approx(0.10)
        prog.level_up_skill("mediation_instinct")
        assert prog.get_bonus("arbitration_neutrality_bonus") == pytest.approx(0.20)

    def test_spread_trader_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("speculator_premium_reduction") == pytest.approx(0.0)
        prog.level_up_skill("negotiator")
        prog.level_up_skill("tariff_negotiation")
        prog.level_up_skill("spread_trader")
        assert prog.get_bonus("speculator_premium_reduction") == pytest.approx(0.05)
        prog.level_up_skill("spread_trader")
        assert prog.get_bonus("speculator_premium_reduction") == pytest.approx(0.10)

    def test_research_yield_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("research_yield_bonus") == pytest.approx(0.0)
        prog.level_up_skill("efficient_refining")
        prog.level_up_skill("research_yield")
        assert prog.get_bonus("research_yield_bonus") == pytest.approx(0.05)
        prog.level_up_skill("research_yield")
        assert prog.get_bonus("research_yield_bonus") == pytest.approx(0.10)

    def test_research_oversight_bonus_at_levels(self) -> None:
        prog = _make_rich_prog()
        assert prog.get_bonus("research_risk_reduction") == pytest.approx(0.0)
        prog.level_up_skill("diplomatic_relations")
        prog.level_up_skill("research_oversight")
        assert prog.get_bonus("research_risk_reduction") == pytest.approx(0.05)
        prog.level_up_skill("research_oversight")
        assert prog.get_bonus("research_risk_reduction") == pytest.approx(0.10)

    # === Prerequisite gating ===

    def test_lot_appraiser_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("lot_appraiser")
        assert not success, "Should fail when market_eye not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("negotiator")
        prog.level_up_skill("market_eye")
        success, msg = prog.level_up_skill("lot_appraiser")
        assert success, f"Should succeed after market_eye unlocked: {msg}"

    def test_coalition_sway_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("coalition_sway")
        assert not success, "Should fail when silver_tongue not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("silver_tongue")
        success, msg = prog.level_up_skill("coalition_sway")
        assert success, f"Should succeed after silver_tongue unlocked: {msg}"

    def test_delegate_reach_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("delegate_reach")
        assert not success, "Should fail when give_the_word not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("give_the_word")
        success, msg = prog.level_up_skill("delegate_reach")
        assert success, f"Should succeed after give_the_word unlocked: {msg}"

    def test_mediation_instinct_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("mediation_instinct")
        assert not success, "Should fail when empathic_read not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("keen_insight")
        prog.level_up_skill("empathic_read")
        success, msg = prog.level_up_skill("mediation_instinct")
        assert success, f"Should succeed after empathic_read unlocked: {msg}"

    def test_spread_trader_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("spread_trader")
        assert not success, "Should fail when tariff_negotiation not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("negotiator")
        prog.level_up_skill("tariff_negotiation")
        success, msg = prog.level_up_skill("spread_trader")
        assert success, f"Should succeed after tariff_negotiation unlocked: {msg}"

    def test_research_yield_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("research_yield")
        assert not success, "Should fail when efficient_refining not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("efficient_refining")
        success, msg = prog.level_up_skill("research_yield")
        assert success, f"Should succeed after efficient_refining unlocked: {msg}"

    def test_research_oversight_prereq_gates_level_up(self) -> None:
        prog = _make_rich_prog()
        success, msg = prog.level_up_skill("research_oversight")
        assert not success, "Should fail when diplomatic_relations not unlocked"
        assert "Requires" in msg
        prog.level_up_skill("diplomatic_relations")
        success, msg = prog.level_up_skill("research_oversight")
        assert success, f"Should succeed after diplomatic_relations unlocked: {msg}"

    # === Max level cap ===

    def test_lot_appraiser_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("negotiator")
        prog.level_up_skill("market_eye")
        prog.level_up_skill("lot_appraiser")
        prog.level_up_skill("lot_appraiser")
        success, msg = prog.level_up_skill("lot_appraiser")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    def test_coalition_sway_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("silver_tongue")
        prog.level_up_skill("coalition_sway")
        prog.level_up_skill("coalition_sway")
        success, msg = prog.level_up_skill("coalition_sway")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    def test_delegate_reach_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("give_the_word")
        prog.level_up_skill("delegate_reach")
        prog.level_up_skill("delegate_reach")
        success, msg = prog.level_up_skill("delegate_reach")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    def test_mediation_instinct_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("keen_insight")
        prog.level_up_skill("empathic_read")
        prog.level_up_skill("mediation_instinct")
        prog.level_up_skill("mediation_instinct")
        success, msg = prog.level_up_skill("mediation_instinct")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    def test_spread_trader_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("negotiator")
        prog.level_up_skill("tariff_negotiation")
        prog.level_up_skill("spread_trader")
        prog.level_up_skill("spread_trader")
        success, msg = prog.level_up_skill("spread_trader")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    def test_research_yield_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("efficient_refining")
        prog.level_up_skill("research_yield")
        prog.level_up_skill("research_yield")
        success, msg = prog.level_up_skill("research_yield")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    def test_research_oversight_cannot_exceed_max_level(self) -> None:
        prog = _make_rich_prog()
        prog.level_up_skill("diplomatic_relations")
        prog.level_up_skill("research_oversight")
        prog.level_up_skill("research_oversight")
        success, msg = prog.level_up_skill("research_oversight")
        assert not success, "Third level-up should fail"
        assert "maxed" in msg.lower()

    # === Migration map invariance ===

    def test_lot_appraiser_not_in_migration_map(self) -> None:
        assert "lot_appraiser" not in _SKILL_MIGRATION_MAP
        assert "lot_appraiser" not in _SKILL_MIGRATION_MAP.values()

    def test_coalition_sway_not_in_migration_map(self) -> None:
        assert "coalition_sway" not in _SKILL_MIGRATION_MAP
        assert "coalition_sway" not in _SKILL_MIGRATION_MAP.values()

    def test_delegate_reach_not_in_migration_map(self) -> None:
        assert "delegate_reach" not in _SKILL_MIGRATION_MAP
        assert "delegate_reach" not in _SKILL_MIGRATION_MAP.values()

    def test_mediation_instinct_not_in_migration_map(self) -> None:
        assert "mediation_instinct" not in _SKILL_MIGRATION_MAP
        assert "mediation_instinct" not in _SKILL_MIGRATION_MAP.values()

    def test_spread_trader_not_in_migration_map(self) -> None:
        assert "spread_trader" not in _SKILL_MIGRATION_MAP
        assert "spread_trader" not in _SKILL_MIGRATION_MAP.values()

    def test_research_yield_not_in_migration_map(self) -> None:
        assert "research_yield" not in _SKILL_MIGRATION_MAP
        assert "research_yield" not in _SKILL_MIGRATION_MAP.values()

    def test_research_oversight_not_in_migration_map(self) -> None:
        assert "research_oversight" not in _SKILL_MIGRATION_MAP
        assert "research_oversight" not in _SKILL_MIGRATION_MAP.values()

    # === Save round-trip tests ===

    def test_pre_sa_c2_save_loads_new_skills_at_level_zero(self) -> None:
        """Pre-SA-C2 save fixture (without new skill IDs) loads with all 7 at level 0."""
        data = {
            "xp": 1000,
            "level": 5,
            "skill_points": 2,
            "skill_points_spent": 2,
            "skills": {
                "negotiator": 2,
                "trade_network": 1,
                "silver_tongue": 1,
            },
        }
        prog = PlayerProgression.from_dict(data)
        for skill_id in _SA_C2_SKILL_IDS:
            assert prog.skills[skill_id].current_level == 0, (
                f"{skill_id} should default to level 0 when absent from save"
            )

    def test_post_sa_c2_save_round_trips_leveled_new_skills(self) -> None:
        """Post-SA-C2 save with leveled new skills round-trips correctly."""
        prog = _make_rich_prog()
        # Level each new skill to 1
        prog.level_up_skill("negotiator")
        prog.level_up_skill("market_eye")
        prog.level_up_skill("lot_appraiser")
        prog.level_up_skill("silver_tongue")
        prog.level_up_skill("coalition_sway")
        prog.level_up_skill("give_the_word")
        prog.level_up_skill("delegate_reach")
        prog.level_up_skill("keen_insight")
        prog.level_up_skill("empathic_read")
        prog.level_up_skill("mediation_instinct")
        prog.level_up_skill("tariff_negotiation")  # needs negotiator (already done)
        prog.level_up_skill("spread_trader")
        prog.level_up_skill("efficient_refining")
        prog.level_up_skill("research_yield")
        prog.level_up_skill("diplomatic_relations")
        prog.level_up_skill("research_oversight")

        saved = prog.to_dict()
        restored = PlayerProgression.from_dict(saved)

        for skill_id in _SA_C2_SKILL_IDS:
            orig_level = prog.skills[skill_id].current_level
            rest_level = restored.skills[skill_id].current_level
            assert rest_level == orig_level, (
                f"{skill_id}: expected {orig_level}, got {rest_level} after round-trip"
            )
