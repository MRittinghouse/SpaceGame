"""Tests for social skill system models."""

import pytest
from spacegame.models.social import (
    SocialSkill,
    SocialManager,
    SOCIAL_XP_THRESHOLDS,
    MAX_SOCIAL_LEVEL,
    XP_ON_SUCCESS,
    XP_ON_FAILURE,
)


# ============================================================================
# SocialSkill Tests
# ============================================================================


class TestSocialSkill:
    """Tests for SocialSkill dataclass."""

    def test_creation_defaults(self) -> None:
        skill = SocialSkill(id="persuasion", name="Persuasion")
        assert skill.id == "persuasion"
        assert skill.name == "Persuasion"
        assert skill.level == 1
        assert skill.xp == 0

    def test_creation_with_values(self) -> None:
        skill = SocialSkill(id="intimidation", name="Intimidation", level=3, xp=20)
        assert skill.level == 3
        assert skill.xp == 20

    def test_add_xp_no_levelup(self) -> None:
        skill = SocialSkill(id="persuasion", name="Persuasion")
        messages = skill.add_xp(3, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert skill.xp == 3
        assert skill.level == 1
        assert len(messages) == 0

    def test_add_xp_triggers_levelup(self) -> None:
        skill = SocialSkill(id="persuasion", name="Persuasion")
        # Threshold for level 2 is 8
        messages = skill.add_xp(8, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert skill.xp == 8
        assert skill.level == 2
        assert len(messages) == 1
        assert "Persuasion" in messages[0]

    def test_add_xp_multiple_levelups(self) -> None:
        skill = SocialSkill(id="persuasion", name="Persuasion")
        # Threshold for level 3 is 25
        messages = skill.add_xp(25, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert skill.xp == 25
        assert skill.level == 3
        assert len(messages) == 2  # Level 2 and level 3

    def test_max_level_cap(self) -> None:
        skill = SocialSkill(id="persuasion", name="Persuasion")
        messages = skill.add_xp(999, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert skill.level == MAX_SOCIAL_LEVEL
        assert skill.xp == 999  # XP still accumulates

    def test_add_xp_incremental(self) -> None:
        """Adding XP in increments produces same result as one large addition."""
        skill = SocialSkill(id="persuasion", name="Persuasion")
        skill.add_xp(5, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert skill.level == 1
        # 5 + 3 = 8, threshold for level 2
        messages = skill.add_xp(3, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert skill.level == 2
        assert len(messages) == 1

    def test_to_dict(self) -> None:
        skill = SocialSkill(id="observation", name="Observation", level=2, xp=8)
        data = skill.to_dict()
        assert data == {"id": "observation", "name": "Observation", "level": 2, "xp": 8}

    def test_from_dict(self) -> None:
        data = {"id": "intimidation", "name": "Intimidation", "level": 3, "xp": 20}
        skill = SocialSkill.from_dict(data)
        assert skill.id == "intimidation"
        assert skill.name == "Intimidation"
        assert skill.level == 3
        assert skill.xp == 20

    def test_round_trip(self) -> None:
        original = SocialSkill(id="persuasion", name="Persuasion", level=4, xp=35)
        restored = SocialSkill.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.level == original.level
        assert restored.xp == original.xp


# ============================================================================
# SocialManager — Skill Access Tests
# ============================================================================


class TestSocialManagerSkills:
    """Tests for SocialManager skill access."""

    def test_default_skills_created(self) -> None:
        mgr = SocialManager()
        assert mgr.get_skill("persuasion") is not None
        assert mgr.get_skill("intimidation") is not None
        assert mgr.get_skill("observation") is not None

    def test_all_skills_start_at_level_1(self) -> None:
        mgr = SocialManager()
        assert mgr.get_skill_level("persuasion") == 1
        assert mgr.get_skill_level("intimidation") == 1
        assert mgr.get_skill_level("observation") == 1

    def test_get_skill_nonexistent(self) -> None:
        mgr = SocialManager()
        assert mgr.get_skill("deception") is None

    def test_get_skill_level_nonexistent(self) -> None:
        mgr = SocialManager()
        assert mgr.get_skill_level("deception") == 0

    def test_get_all_skills(self) -> None:
        mgr = SocialManager()
        skills = mgr.get_all_skills()
        assert len(skills) == 3
        ids = {s.id for s in skills}
        assert ids == {"persuasion", "intimidation", "observation"}


# ============================================================================
# SocialManager — Disposition Tests
# ============================================================================


class TestSocialManagerDisposition:
    """Tests for NPC disposition tracking."""

    def test_default_disposition(self) -> None:
        mgr = SocialManager()
        assert mgr.get_disposition("elena_reeves") == 50

    def test_modify_disposition_increase(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 10)
        assert mgr.get_disposition("elena_reeves") == 60

    def test_modify_disposition_decrease(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", -20)
        assert mgr.get_disposition("elena_reeves") == 30

    def test_disposition_clamp_max(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 200)
        assert mgr.get_disposition("elena_reeves") == 100

    def test_disposition_clamp_min(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", -200)
        assert mgr.get_disposition("elena_reeves") == 0

    def test_independent_npc_dispositions(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 10)
        mgr.modify_disposition("marcus_jin", -10)
        assert mgr.get_disposition("elena_reeves") == 60
        assert mgr.get_disposition("marcus_jin") == 40


# ============================================================================
# SocialManager — Effective Level Tests
# ============================================================================


class TestSocialManagerEffectiveLevel:
    """Tests for effective level calculation (skill + disposition modifier)."""

    def test_neutral_disposition_no_modifier(self) -> None:
        mgr = SocialManager()
        # Disposition 50 -> modifier 0 -> effective = skill level 1
        assert mgr.get_effective_level("persuasion", "elena_reeves") == 1

    def test_high_disposition_positive_modifier(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 20)  # disposition 70
        # Modifier = (70 - 50) // 10 = +2
        assert mgr.get_effective_level("persuasion", "elena_reeves") == 3

    def test_low_disposition_negative_modifier(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", -20)  # disposition 30
        # Modifier = (30 - 50) // 10 = -2, skill 1 + (-2) = -1 -> clamped to 0
        assert mgr.get_effective_level("persuasion", "elena_reeves") == 0

    def test_effective_level_minimum_zero(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", -200)  # disposition 0
        # Modifier = (0 - 50) // 10 = -5, skill 1 + (-5) = -4 -> clamped to 0
        assert mgr.get_effective_level("persuasion", "elena_reeves") == 0

    def test_max_disposition_modifier(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 50)  # disposition 100
        # Modifier = (100 - 50) // 10 = +5
        assert mgr.get_effective_level("persuasion", "elena_reeves") == 6

    def test_effective_level_unknown_skill(self) -> None:
        mgr = SocialManager()
        assert mgr.get_effective_level("deception", "elena_reeves") == 0


# ============================================================================
# SocialManager — Check Resolution Tests
# ============================================================================


class TestSocialManagerChecks:
    """Tests for skill check resolution."""

    def test_can_pass_check_success(self) -> None:
        mgr = SocialManager()
        # Level 1, disposition 50 (modifier 0) -> effective 1, difficulty 1
        assert mgr.can_pass_check("persuasion", 1, "elena_reeves") is True

    def test_can_pass_check_failure(self) -> None:
        mgr = SocialManager()
        # Level 1, disposition 50 -> effective 1, difficulty 2
        assert mgr.can_pass_check("persuasion", 2, "elena_reeves") is False

    def test_can_pass_check_with_disposition_boost(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 10)  # disposition 60, modifier +1
        # Effective 2 >= difficulty 2
        assert mgr.can_pass_check("persuasion", 2, "elena_reeves") is True

    def test_resolve_check_success(self) -> None:
        mgr = SocialManager()
        success, msg = mgr.resolve_check("persuasion", 1, "elena_reeves")
        assert success is True
        assert "passed" in msg.lower() or "success" in msg.lower()

    def test_resolve_check_failure(self) -> None:
        mgr = SocialManager()
        success, msg = mgr.resolve_check("persuasion", 3, "elena_reeves")
        assert success is False
        assert "failed" in msg.lower()

    def test_resolve_check_awards_xp_on_success(self) -> None:
        mgr = SocialManager()
        mgr.resolve_check("persuasion", 1, "elena_reeves")
        skill = mgr.get_skill("persuasion")
        assert skill is not None and skill.xp == XP_ON_SUCCESS

    def test_resolve_check_awards_xp_on_failure(self) -> None:
        mgr = SocialManager()
        mgr.resolve_check("persuasion", 5, "elena_reeves")
        skill = mgr.get_skill("persuasion")
        assert skill is not None and skill.xp == XP_ON_FAILURE

    def test_resolve_check_increases_disposition_on_success(self) -> None:
        mgr = SocialManager()
        mgr.resolve_check("persuasion", 1, "elena_reeves")
        assert mgr.get_disposition("elena_reeves") == 53  # 50 + 3

    def test_resolve_check_decreases_disposition_on_failure(self) -> None:
        mgr = SocialManager()
        mgr.resolve_check("persuasion", 5, "elena_reeves")
        assert mgr.get_disposition("elena_reeves") == 48  # 50 - 2

    def test_resolve_check_unknown_skill(self) -> None:
        mgr = SocialManager()
        success, msg = mgr.resolve_check("deception", 1, "elena_reeves")
        assert success is False
        assert "unknown" in msg.lower()

    def test_resolve_check_can_trigger_levelup(self) -> None:
        mgr = SocialManager()
        # Level up threshold at 8 XP, XP_ON_SUCCESS = 2
        # Need 4 successful checks (8 XP >= 8 threshold)
        mgr.resolve_check("persuasion", 1, "elena_reeves")  # 2 XP
        mgr.resolve_check("persuasion", 1, "elena_reeves")  # 4 XP
        mgr.resolve_check("persuasion", 1, "elena_reeves")  # 6 XP
        success, msg = mgr.resolve_check("persuasion", 1, "elena_reeves")  # 8 XP
        assert mgr.get_skill_level("persuasion") == 2


# ============================================================================
# SocialManager — Serialization Tests
# ============================================================================


class TestSocialManagerSerialization:
    """Tests for social state serialization."""

    def test_get_state(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 10)
        state = mgr.get_state()
        assert "skills" in state
        assert "disposition" in state
        assert state["disposition"]["elena_reeves"] == 60

    def test_load_state(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 10)
        mgr.resolve_check("persuasion", 1, "elena_reeves")
        state = mgr.get_state()

        mgr2 = SocialManager()
        mgr2.load_state(state)
        assert mgr2.get_disposition("elena_reeves") == mgr.get_disposition("elena_reeves")
        assert mgr2.get_skill_level("persuasion") == mgr.get_skill_level("persuasion")
        skill = mgr2.get_skill("persuasion")
        assert skill is not None and skill.xp == XP_ON_SUCCESS

    def test_load_state_empty(self) -> None:
        mgr = SocialManager()
        mgr.load_state({})
        # Should reset to defaults
        assert mgr.get_skill_level("persuasion") == 1
        assert mgr.get_disposition("elena_reeves") == 50

    def test_state_round_trip(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("elena_reeves", 15)
        mgr.modify_disposition("marcus_jin", -5)
        # Level up persuasion through repeated checks
        for _ in range(3):
            mgr.resolve_check("persuasion", 1, "elena_reeves")

        state = mgr.get_state()
        mgr2 = SocialManager()
        mgr2.load_state(state)

        assert mgr2.get_skill_level("persuasion") == mgr.get_skill_level("persuasion")
        assert mgr2.get_skill("persuasion").xp == mgr.get_skill("persuasion").xp
        assert mgr2.get_disposition("elena_reeves") == mgr.get_disposition("elena_reeves")
        assert mgr2.get_disposition("marcus_jin") == mgr.get_disposition("marcus_jin")
        # Unmodified NPC still defaults
        assert mgr2.get_disposition("tomas_drifter") == 50


# ============================================================================
# SocialManager — Progression + Attribute Integration Tests
# ============================================================================


class TestSocialManagerProgressionIntegration:
    """Tests for SocialManager with skill tree bonuses."""

    def _make_progression_with_social(self) -> "PlayerProgression":
        from spacegame.models.progression import PlayerProgression

        prog = PlayerProgression()
        prog.add_xp(5200)  # Max level for plenty of points
        return prog

    def test_set_progression(self) -> None:
        from spacegame.models.progression import PlayerProgression

        mgr = SocialManager()
        prog = PlayerProgression()
        mgr.set_progression(prog)
        # Should not raise

    def test_effective_level_with_tree_bonus(self) -> None:
        mgr = SocialManager()
        prog = self._make_progression_with_social()
        prog.level_up_skill("silver_tongue")  # +1 persuasion bonus
        mgr.set_progression(prog)

        # Base use-level = 1, disposition mod = 0, tree bonus = 1
        effective = mgr.get_effective_level("persuasion", "test_npc")
        assert effective == 2  # 1 + 0 + 1

    def test_effective_level_with_max_tree_bonus(self) -> None:
        mgr = SocialManager()
        prog = self._make_progression_with_social()
        prog.level_up_skill("silver_tongue")
        prog.level_up_skill("silver_tongue")  # +2 persuasion bonus
        mgr.set_progression(prog)

        effective = mgr.get_effective_level("persuasion", "test_npc")
        assert effective == 3  # 1 + 0 + 2

    def test_tree_bonus_only_for_matching_skill(self) -> None:
        mgr = SocialManager()
        prog = self._make_progression_with_social()
        prog.level_up_skill("silver_tongue")  # Only persuasion bonus
        mgr.set_progression(prog)

        # Intimidation should NOT get persuasion bonus
        effective = mgr.get_effective_level("intimidation", "test_npc")
        assert effective == 1  # 1 + 0 + 0 (no intimidation_bonus in tree)

    def test_effective_level_without_progression(self) -> None:
        """Backward compatible: no progression set, no crash."""
        mgr = SocialManager()
        effective = mgr.get_effective_level("persuasion", "test_npc")
        assert effective == 1  # Just base use-level


class TestSocialManagerAttributeIntegration:
    """Tests for SocialManager with attribute bonuses."""

    def test_set_attribute_sheet(self) -> None:
        from spacegame.models.attributes import AttributeSheet

        mgr = SocialManager()
        sheet = AttributeSheet()
        mgr.set_attribute_sheet(sheet)
        # Should not raise

    def test_effective_level_with_synergy(self) -> None:
        from spacegame.models.attributes import AttributeSheet

        mgr = SocialManager()
        values = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 4}
        sheet = AttributeSheet(values=values)
        mgr.set_attribute_sheet(sheet)

        # Base = 1, disposition = 0, tree = 0, synergy = 4 // 2 = 2
        effective = mgr.get_effective_level("persuasion", "test_npc")
        assert effective == 3  # 1 + 0 + 0 + 2

    def test_effective_level_without_attribute_sheet(self) -> None:
        """Backward compatible: no attribute sheet set, no crash."""
        mgr = SocialManager()
        effective = mgr.get_effective_level("persuasion", "test_npc")
        assert effective == 1

    def test_effective_level_combined_all_sources(self) -> None:
        """All four sources stacking: use + disposition + tree + synergy."""
        from spacegame.models.progression import PlayerProgression
        from spacegame.models.attributes import AttributeSheet

        mgr = SocialManager()

        # Set up progression with silver_tongue level 1
        prog = PlayerProgression()
        prog.add_xp(5200)
        prog.level_up_skill("silver_tongue")  # +1 persuasion
        mgr.set_progression(prog)

        # Set up attribute sheet with SYN 4 (bonus = 2)
        values = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 4}
        sheet = AttributeSheet(values=values)
        mgr.set_attribute_sheet(sheet)

        # Set disposition high (+10 = modifier +1)
        mgr.modify_disposition("test_npc", 10)

        # use_level=1, disp_mod=+1, tree=+1, synergy=+2 = 5
        effective = mgr.get_effective_level("persuasion", "test_npc")
        assert effective == 5

    def test_can_pass_check_with_bonuses(self) -> None:
        """Bonuses should help pass otherwise-impossible checks."""
        from spacegame.models.progression import PlayerProgression

        mgr = SocialManager()
        # Without tree bonus, can't pass difficulty 2
        assert not mgr.can_pass_check("persuasion", 2, "test_npc")

        # Add tree bonus
        prog = PlayerProgression()
        prog.add_xp(5200)
        prog.level_up_skill("silver_tongue")
        mgr.set_progression(prog)

        # Now effective = 2, can pass difficulty 2
        assert mgr.can_pass_check("persuasion", 2, "test_npc")
