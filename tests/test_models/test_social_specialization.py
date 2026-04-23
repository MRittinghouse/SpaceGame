"""Tests for the social specialization soft modifier (NV-0).

Specialization rewards players for focusing on a specific social skill
relative to their others. It's a soft bonus on ``effective_level``:
players who consciously invest in one skill get a bonus; generalists
get neither bonus nor penalty; players who neglect a skill entirely
see a modest penalty when attempting checks in it.

Measured from ``base_level`` (use-based) only — tree/synergy/disposition
are orthogonal and already contribute to ``effective_level``.
"""

from __future__ import annotations

import pytest

from spacegame.models.social import (
    DISPOSITION_DEFAULT,
    MAX_SOCIAL_LEVEL,
    SOCIAL_XP_THRESHOLDS,
    SocialManager,
)


def _manager_with_levels(**levels: int) -> SocialManager:
    """Build a SocialManager with explicit base levels on each skill.

    Keyword args: persuasion, intimidation, observation.
    """
    mgr = SocialManager()
    for skill_id, level in levels.items():
        skill = mgr.get_skill(skill_id)
        assert skill is not None, f"unknown skill: {skill_id}"
        skill.level = level
    return mgr


# ---------------------------------------------------------------------------
# Specialization ratio
# ---------------------------------------------------------------------------


class TestSpecializationRatio:
    def test_balanced_skills_ratio_is_one(self) -> None:
        mgr = _manager_with_levels(persuasion=2, intimidation=2, observation=2)
        assert mgr.get_specialization_ratio("persuasion") == pytest.approx(1.0)
        assert mgr.get_specialization_ratio("intimidation") == pytest.approx(1.0)
        assert mgr.get_specialization_ratio("observation") == pytest.approx(1.0)

    def test_full_specialist_ratio_above_one_five(self) -> None:
        mgr = _manager_with_levels(persuasion=5, intimidation=1, observation=1)
        ratio = mgr.get_specialization_ratio("persuasion")
        assert ratio > 1.5, f"expected >1.5, got {ratio}"

    def test_neglected_skill_ratio_well_below_one(self) -> None:
        mgr = _manager_with_levels(persuasion=1, intimidation=5, observation=5)
        ratio = mgr.get_specialization_ratio("persuasion")
        assert ratio < 0.5, f"expected <0.5, got {ratio}"

    def test_moderate_specialization_ratio(self) -> None:
        # Persuasion 4, others 2 → avg = 8/3 = 2.67 → ratio ≈ 1.5
        mgr = _manager_with_levels(persuasion=4, intimidation=2, observation=2)
        ratio = mgr.get_specialization_ratio("persuasion")
        assert ratio == pytest.approx(1.5, rel=0.05)

    def test_all_zero_levels_returns_one(self) -> None:
        # Edge case — no skills leveled yet (shouldn't happen but must not divide by zero).
        mgr = SocialManager()
        for skill in mgr.get_all_skills():
            skill.level = 0
        assert mgr.get_specialization_ratio("persuasion") == pytest.approx(1.0)

    def test_ratio_survives_single_skill_level_one(self) -> None:
        # All level 1 (default starting state).
        mgr = SocialManager()
        # All default to level 1
        assert mgr.get_specialization_ratio("persuasion") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Specialization bonus
# ---------------------------------------------------------------------------


class TestSpecializationBonus:
    def test_balanced_bonus_zero(self) -> None:
        mgr = _manager_with_levels(persuasion=3, intimidation=3, observation=3)
        assert mgr.get_specialization_bonus("persuasion") == 0

    def test_full_specialist_bonus_capped_at_two(self) -> None:
        mgr = _manager_with_levels(persuasion=5, intimidation=1, observation=1)
        assert mgr.get_specialization_bonus("persuasion") == 2

    def test_moderate_specialist_gets_plus_one(self) -> None:
        # Persuasion 4, others 2 → ratio 1.5 → (1.5-1.0)*2 = 1.0 → +1
        mgr = _manager_with_levels(persuasion=4, intimidation=2, observation=2)
        assert mgr.get_specialization_bonus("persuasion") == 1

    def test_neglected_skill_penalty_bounded(self) -> None:
        # Persuasion 1 with others 5 → ratio ~0.27 → raw ~-1.46 → -1
        mgr = _manager_with_levels(persuasion=1, intimidation=5, observation=5)
        bonus = mgr.get_specialization_bonus("persuasion")
        assert -2 <= bonus <= -1, f"expected -2 <= bonus <= -1, got {bonus}"

    def test_total_neglect_caps_at_negative_two(self) -> None:
        # Imagine skill locked at 0 while others maxed.
        mgr = _manager_with_levels(persuasion=1, intimidation=5, observation=5)
        # Force persuasion to 0 for the extreme case
        mgr.get_skill("persuasion").level = 0
        bonus = mgr.get_specialization_bonus("persuasion")
        assert bonus == -2

    def test_slight_lean_gives_zero_bonus(self) -> None:
        # Persuasion 3, others 2 → ratio ~1.29 → raw ~0.57 → 0 (requires full +0.5 to count)
        mgr = _manager_with_levels(persuasion=3, intimidation=2, observation=2)
        bonus = mgr.get_specialization_bonus("persuasion")
        assert bonus == 0, (
            "slight leaning should not grant a bonus — must earn the "
            "specialization through commitment"
        )


# ---------------------------------------------------------------------------
# Integration: specialization contributes to effective_level
# ---------------------------------------------------------------------------


class TestSpecializationInEffectiveLevel:
    def test_specialist_effective_level_includes_bonus(self) -> None:
        mgr = _manager_with_levels(persuasion=4, intimidation=2, observation=2)
        # base 4 + disp 0 + tree 0 + synergy 0 + spec +1 = 5
        effective = mgr.get_effective_level("persuasion", "some_npc")
        assert effective == 5

    def test_generalist_effective_level_no_spec_bonus(self) -> None:
        mgr = _manager_with_levels(persuasion=3, intimidation=3, observation=3)
        effective = mgr.get_effective_level("persuasion", "some_npc")
        assert effective == 3

    def test_neglected_skill_effective_level_penalty(self) -> None:
        mgr = _manager_with_levels(persuasion=1, intimidation=5, observation=5)
        # base 1 + disp 0 + tree 0 + synergy 0 + spec -1 = 0
        effective = mgr.get_effective_level("persuasion", "some_npc")
        assert effective == 0

    def test_specialization_cannot_drive_effective_below_zero(self) -> None:
        mgr = SocialManager()
        mgr.get_skill("persuasion").level = 0
        mgr.get_skill("intimidation").level = 5
        mgr.get_skill("observation").level = 5
        effective = mgr.get_effective_level("persuasion", "some_npc")
        assert effective >= 0

    def test_specialization_stacks_with_tree_bonus(self) -> None:
        """A specialist who also invested skill points benefits from both."""
        from unittest.mock import MagicMock

        mgr = _manager_with_levels(persuasion=4, intimidation=2, observation=2)
        prog = MagicMock()

        def get_bonus(key: str) -> float:
            if key == "persuasion_bonus":
                return 2.0
            return 0.0

        prog.get_bonus.side_effect = get_bonus
        mgr.set_progression(prog)

        # base 4 + tree +2 + spec +1 = 7
        effective = mgr.get_effective_level("persuasion", "some_npc")
        assert effective == 7


# ---------------------------------------------------------------------------
# Integration: can_pass_check honors specialization
# ---------------------------------------------------------------------------


class TestSpecializationInCheckResolution:
    def test_specialist_passes_harder_check_than_base_would(self) -> None:
        """A focused player should pass checks a similarly-leveled generalist can't."""
        specialist = _manager_with_levels(persuasion=4, intimidation=2, observation=2)
        generalist = _manager_with_levels(persuasion=4, intimidation=4, observation=4)

        # Difficulty 5 check: specialist has effective 5 (4 + 1 spec), generalist has 4
        assert specialist.can_pass_check("persuasion", 5, "npc") is True
        assert generalist.can_pass_check("persuasion", 5, "npc") is False

    def test_specialization_does_not_inflate_passive_checks(self) -> None:
        """Low-difficulty checks still accessible to generalists."""
        generalist = _manager_with_levels(persuasion=3, intimidation=3, observation=3)
        assert generalist.can_pass_check("persuasion", 3, "npc") is True
        assert generalist.can_pass_check("persuasion", 2, "npc") is True

    def test_neglected_skill_fails_check_despite_absolute_level(self) -> None:
        """High-level player who neglected this skill still feels it."""
        neglector = _manager_with_levels(persuasion=2, intimidation=5, observation=5)
        # base 2 + spec bonus from ratio (2/4=0.5, raw=-1) = 1
        assert neglector.can_pass_check("persuasion", 2, "npc") is False
