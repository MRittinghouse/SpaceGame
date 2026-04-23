"""NV-6.5 infrastructure tests — expanded skill registry + plumbing.

Covers:
  - All 7 registered skills (persuasion, intimidation, observation,
    deception, technical, piloting, leadership) exist and level via XP.
  - ``SKILL_TO_ATTRIBUTE`` routes synergy correctly: socials → SYN,
    Technical → ING, Piloting → ACU.
  - ``SKILLS_USING_DISPOSITION`` selectively applies the disposition
    modifier — expertise skills (Technical, Piloting) ignore NPC mood.
  - Tree bonuses apply via ``{skill}_bonus`` dynamic lookup.
  - XP growth from refining (Technical) and combat (Piloting) hooks
    grant XP through the social manager.
  - Save/load backward compatibility: old 3-skill saves load cleanly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from spacegame.models.attributes import AttributeSheet
from spacegame.models.social import (
    MAX_SOCIAL_LEVEL,
    SKILL_TO_ATTRIBUTE,
    SKILLS_USING_DISPOSITION,
    SOCIAL_SKILL_DEFINITIONS,
    SOCIAL_XP_THRESHOLDS,
    SocialManager,
    XP_ON_COMBAT_WIN,
    XP_ON_REFINE_SUCCESS,
    XP_ON_SUCCESS,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestExpandedRegistry:
    def test_seven_skills_registered(self) -> None:
        assert set(SOCIAL_SKILL_DEFINITIONS.keys()) == {
            "persuasion",
            "intimidation",
            "observation",
            "deception",
            "technical",
            "piloting",
            "leadership",
        }

    def test_new_skills_default_to_level_one(self) -> None:
        mgr = SocialManager()
        for sid in ("deception", "technical", "piloting", "leadership"):
            skill = mgr.get_skill(sid)
            assert skill is not None
            assert skill.level == 1
            assert skill.xp == 0

    def test_new_skills_level_via_xp(self) -> None:
        mgr = SocialManager()
        tech = mgr.get_skill("technical")
        assert tech is not None
        # Hit level 2 threshold (8 XP)
        tech.add_xp(8, MAX_SOCIAL_LEVEL, SOCIAL_XP_THRESHOLDS)
        assert tech.level == 2


# ---------------------------------------------------------------------------
# SKILL_TO_ATTRIBUTE
# ---------------------------------------------------------------------------


class TestSkillToAttributeMapping:
    def test_all_skills_mapped(self) -> None:
        # Every registered skill must have an attribute mapping
        for sid in SOCIAL_SKILL_DEFINITIONS:
            assert sid in SKILL_TO_ATTRIBUTE, f"{sid} missing from SKILL_TO_ATTRIBUTE"

    def test_socials_route_to_synergy(self) -> None:
        for sid in ("persuasion", "intimidation", "observation", "deception", "leadership"):
            assert SKILL_TO_ATTRIBUTE[sid] == "syn"

    def test_technical_routes_to_ingenuity(self) -> None:
        assert SKILL_TO_ATTRIBUTE["technical"] == "ing"

    def test_piloting_routes_to_acuity(self) -> None:
        assert SKILL_TO_ATTRIBUTE["piloting"] == "acu"

    def test_effective_level_uses_mapped_attribute(self) -> None:
        """Technical should draw synergy from Ingenuity, not Synergy."""
        mgr = SocialManager()
        sheet = AttributeSheet()
        # Pump ING up, SYN stays at default — Technical should benefit.
        sheet.values["ing"] = 6
        mgr.set_attribute_sheet(sheet)
        # Technical base 1 + disp 0 (excluded) + tree 0 + synergy (6//2=3) + spec 0 = 4
        assert mgr.get_effective_level("technical", "some_npc") == 4

    def test_piloting_draws_from_acuity_not_synergy(self) -> None:
        mgr = SocialManager()
        sheet = AttributeSheet()
        sheet.values["acu"] = 6
        sheet.values["syn"] = 1  # baseline
        mgr.set_attribute_sheet(sheet)
        # Piloting base 1 + synergy (acu=6//2=3) + spec 0 = 4
        assert mgr.get_effective_level("piloting", "some_npc") == 4


# ---------------------------------------------------------------------------
# SKILLS_USING_DISPOSITION
# ---------------------------------------------------------------------------


class TestSelectiveDisposition:
    def test_social_skills_use_disposition(self) -> None:
        for sid in ("persuasion", "intimidation", "observation", "deception", "leadership"):
            assert sid in SKILLS_USING_DISPOSITION

    def test_expertise_skills_ignore_disposition(self) -> None:
        assert "technical" not in SKILLS_USING_DISPOSITION
        assert "piloting" not in SKILLS_USING_DISPOSITION

    def test_technical_ignores_high_disposition(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("some_npc", 50)  # max disposition
        # Technical base 1 + disp 0 (excluded) + spec 0 = 1
        assert mgr.get_effective_level("technical", "some_npc") == 1

    def test_piloting_ignores_low_disposition(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("some_npc", -30)  # disposition 20
        # Piloting base 1 + disp 0 (excluded) + spec 0 = 1
        assert mgr.get_effective_level("piloting", "some_npc") == 1

    def test_deception_uses_disposition(self) -> None:
        """New social skill still responds to NPC mood."""
        mgr = SocialManager()
        mgr.modify_disposition("some_npc", 30)  # disposition 80
        # Deception base 1 + disp (80-50)//10=3 + spec 0 = 4
        assert mgr.get_effective_level("deception", "some_npc") == 4

    def test_leadership_uses_disposition(self) -> None:
        mgr = SocialManager()
        mgr.modify_disposition("some_npc", 30)
        assert mgr.get_effective_level("leadership", "some_npc") == 4


# ---------------------------------------------------------------------------
# Tree bonuses via dynamic lookup
# ---------------------------------------------------------------------------


class TestTreeBonusesForNewSkills:
    def test_deception_bonus_applies(self) -> None:
        mgr = SocialManager()
        prog = MagicMock()

        def get_bonus(key: str) -> float:
            return 2.0 if key == "deception_bonus" else 0.0

        prog.get_bonus.side_effect = get_bonus
        mgr.set_progression(prog)
        # Base 1 + tree 2 + faction_social_bonus 0 + spec 0 = 3
        assert mgr.get_effective_level("deception", "some_npc") == 3

    def test_technical_bonus_applies(self) -> None:
        mgr = SocialManager()
        prog = MagicMock()

        def get_bonus(key: str) -> float:
            return 2.0 if key == "technical_bonus" else 0.0

        prog.get_bonus.side_effect = get_bonus
        mgr.set_progression(prog)
        # Technical: base 1 + tree 2 + no faction_social (not a social skill) + spec 0 = 3
        assert mgr.get_effective_level("technical", "some_npc") == 3

    def test_piloting_bonus_applies(self) -> None:
        mgr = SocialManager()
        prog = MagicMock()

        def get_bonus(key: str) -> float:
            return 1.0 if key == "piloting_bonus" else 0.0

        prog.get_bonus.side_effect = get_bonus
        mgr.set_progression(prog)
        # Piloting: base 1 + tree 1 + spec 0 = 2
        assert mgr.get_effective_level("piloting", "some_npc") == 2

    def test_leadership_bonus_applies(self) -> None:
        mgr = SocialManager()
        prog = MagicMock()

        def get_bonus(key: str) -> float:
            return 1.0 if key == "leadership_bonus" else 0.0

        prog.get_bonus.side_effect = get_bonus
        mgr.set_progression(prog)
        # Leadership: base 1 + tree 1 + disp 0 + faction_social 0 + spec 0 = 2
        assert mgr.get_effective_level("leadership", "some_npc") == 2

    def test_faction_social_bonus_skips_expertise_skills(self) -> None:
        """Cultural Savant only helps social-interaction skills, not Technical/Piloting."""
        mgr = SocialManager()
        prog = MagicMock()

        def get_bonus(key: str) -> float:
            # Simulate Cultural Savant active in faction-aligned system
            return 2.0 if key == "faction_social_bonus" else 0.0

        prog.get_bonus.side_effect = get_bonus
        mgr.set_progression(prog)
        # Technical: base 1 + tree 0 + faction_social 0 (skipped) + spec 0 = 1
        assert mgr.get_effective_level("technical", "some_npc") == 1
        # Persuasion: base 1 + tree 0 + faction_social 2 + spec 0 = 3
        assert mgr.get_effective_level("persuasion", "some_npc") == 3


# ---------------------------------------------------------------------------
# Tree skill existence
# ---------------------------------------------------------------------------


class TestTreeSkillsExist:
    def test_all_new_base_tree_skills_registered(self) -> None:
        from spacegame.models.progression import create_default_skills

        skills = create_default_skills()
        for expected in ("poker_face", "tool_sense", "steady_stick", "give_the_word"):
            assert expected in skills, f"NV-6.5 base tree skill {expected} missing"

    def test_variant_tree_skills_registered(self) -> None:
        from spacegame.models.progression import create_default_skills

        skills = create_default_skills()
        for expected in ("ghost_protocol", "engineer_insight", "command_presence"):
            assert expected in skills, f"NV-6.5 variant tree skill {expected} missing"

    def test_base_skills_have_correct_bonus_types(self) -> None:
        from spacegame.models.progression import create_default_skills

        skills = create_default_skills()
        assert skills["poker_face"].bonus_type == "deception_bonus"
        assert skills["tool_sense"].bonus_type == "technical_bonus"
        assert skills["steady_stick"].bonus_type == "piloting_bonus"
        assert skills["give_the_word"].bonus_type == "leadership_bonus"


# ---------------------------------------------------------------------------
# XP growth constants
# ---------------------------------------------------------------------------


class TestXPGrowthConstants:
    def test_refine_xp_constant_exists(self) -> None:
        assert XP_ON_REFINE_SUCCESS > 0
        assert XP_ON_REFINE_SUCCESS == XP_ON_SUCCESS  # Same as dialogue success

    def test_combat_xp_constant_exists(self) -> None:
        assert XP_ON_COMBAT_WIN > 0
        assert XP_ON_COMBAT_WIN == XP_ON_SUCCESS


# ---------------------------------------------------------------------------
# Save/load back-compat
# ---------------------------------------------------------------------------


class TestSaveLoadBackCompat:
    def test_old_save_with_three_skills_loads_cleanly(self) -> None:
        """A pre-NV-6.5 save has only persuasion/intimidation/observation in
        its social_state. Loading into the new 7-skill system must not
        crash and must default the 4 new skills to level 1."""
        mgr = SocialManager()
        old_state = {
            "skills": {
                "persuasion": {"id": "persuasion", "name": "Persuasion", "level": 3, "xp": 30},
                "intimidation": {"id": "intimidation", "name": "Intimidation", "level": 2, "xp": 10},
                "observation": {"id": "observation", "name": "Observation", "level": 1, "xp": 0},
            },
            "disposition": {"elena_reeves": 60},
        }
        mgr.load_state(old_state)

        # Old skills preserved
        assert mgr.get_skill("persuasion").level == 3
        assert mgr.get_skill("intimidation").level == 2
        # New skills default to level 1, zero XP
        for sid in ("deception", "technical", "piloting", "leadership"):
            skill = mgr.get_skill(sid)
            assert skill is not None
            assert skill.level == 1
            assert skill.xp == 0

    def test_new_state_round_trips(self) -> None:
        mgr = SocialManager()
        mgr.get_skill("deception").level = 3
        mgr.get_skill("deception").xp = 30
        mgr.get_skill("technical").level = 2

        state = mgr.get_state()
        mgr2 = SocialManager()
        mgr2.load_state(state)
        assert mgr2.get_skill("deception").level == 3
        assert mgr2.get_skill("deception").xp == 30
        assert mgr2.get_skill("technical").level == 2


# ---------------------------------------------------------------------------
# XP hooks — integration stubs
# ---------------------------------------------------------------------------


class TestXPHookWiring:
    def test_refining_view_accepts_social_manager(self) -> None:
        """RefiningView constructor exposes social_manager parameter."""
        import inspect

        from spacegame.views.refining_view import RefiningView

        sig = inspect.signature(RefiningView.__init__)
        assert "social_manager" in sig.parameters

    def test_game_has_grant_piloting_xp_helper(self) -> None:
        """game.py exposes the combat-win Piloting XP grant method."""
        from spacegame.engine.game import Game

        assert hasattr(Game, "_grant_piloting_xp_on_combat_win")
