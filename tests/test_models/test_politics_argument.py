"""SA-P2 — argument-construction resolution tests.

Reproduces the worked numerical examples from SA-P1 §4.6 (Drift round-1
pass) and §6.3 (Marsh mediation fail) byte-for-byte. Covers framing-to-
skill routing, evidence-absent +1 difficulty, crew/skill bonus stacking,
and slot dependency rules.
"""

from __future__ import annotations

from typing import Optional

import pytest

from tests.test_models.test_politics_dispute import _make_water_rights_phasing_template

from spacegame.models.politics_dispute import (
    ArgumentResolution,
    PoliticsArgument,
    PoliticsDelegate,
    PoliticsDisputeManager,
)


# ---------------------------------------------------------------------------
# Stub bonus providers — keep resolution tests free of crew/progression deps.
# ---------------------------------------------------------------------------


class _StubBonus:
    """Minimal duck-typed stand-in for CrewRoster / Progression."""

    def __init__(self, bonuses: Optional[dict[str, float]] = None) -> None:
        self._bonuses = dict(bonuses or {})

    def get_bonus(self, bonus_type: str) -> float:
        return float(self._bonuses.get(bonus_type, 0.0))


class _StubSocial:
    """Stand-in for SocialManager — only needs get_skill_level."""

    def __init__(self, skill_levels: Optional[dict[str, int]] = None) -> None:
        self._levels = dict(skill_levels or {})

    def get_skill_level(self, skill_id: str) -> int:
        return int(self._levels.get(skill_id, 1))


# ---------------------------------------------------------------------------
# Resolution formula — SA-P1 §6.2
# ---------------------------------------------------------------------------


class TestArgumentResolutionFormula:
    """Implements SA-P1 §6.2: floor(base + framing + disp + crew + tree).

    Worked examples in §4.6 and §6.3 reproduce here byte-for-byte.
    """

    def _make_manager(
        self,
        *,
        persuasion: int = 3,
        leadership: int = 3,
        coalition_sway_crew: float = 0.0,
        coalition_sway_skill: float = 0.0,
        arbitration_crew: float = 0.0,
        arbitration_skill: float = 0.0,
    ) -> tuple[PoliticsDisputeManager, "object"]:
        crew = _StubBonus(
            {
                "coalition_sway_bonus": coalition_sway_crew,
                "arbitration_neutrality_bonus": arbitration_crew,
            }
        )
        progression = _StubBonus(
            {
                "coalition_sway_bonus": coalition_sway_skill,
                "arbitration_neutrality_bonus": arbitration_skill,
            }
        )
        social = _StubSocial({"persuasion": persuasion, "leadership": leadership})
        tpl = _make_water_rights_phasing_template()
        return (
            PoliticsDisputeManager(
                templates={tpl.id: tpl},
                crew_roster=crew,
                progression=progression,
                social_manager=social,
            ),
            tpl,
        )

    def test_drift_round_one_data_precedent_pass(self) -> None:
        """SA-P1 §4.6 round 1: 3 + 1 + 0 + 0.15 + 0.20 = 4.35 -> floor 4 vs D4 -> pass."""
        mgr, tpl = self._make_manager(
            persuasion=3,
            coalition_sway_crew=0.15,
            coalition_sway_skill=0.20,
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.effective_floor == 4
        assert resolution.passes is True
        assert resolution.difficulty == 4
        # Component breakdown for explainability + downstream UI.
        assert resolution.base_skill == 3
        assert resolution.framing_mod == 1
        assert resolution.disposition_mod == 0
        assert resolution.crew_bonus == pytest.approx(0.15)
        assert resolution.tree_bonus == pytest.approx(0.20)

    def test_marsh_mediation_community_benefit_fail(self) -> None:
        """SA-P1 §6.3: 3 + 0 + 0 + 0.15 + 0.20 = 3.35 -> floor 3 vs D4 -> fail."""
        mgr, tpl = self._make_manager(
            persuasion=3,
            arbitration_crew=0.15,
            arbitration_skill=0.20,
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="community_benefit",
            audience_delegate_id="ollo_marsh",
            evidence="northern_aquifer_draw_report",
            is_mediation=True,
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.effective_floor == 3
        assert resolution.passes is False
        assert resolution.difficulty == 4
        assert resolution.crew_bonus == pytest.approx(0.15)
        assert resolution.tree_bonus == pytest.approx(0.20)

    def test_evidence_absent_raises_difficulty(self) -> None:
        """SA-P1 §6.5: empty evidence slot adds +1 to effective difficulty."""
        mgr, tpl = self._make_manager(
            persuasion=3,
            coalition_sway_crew=0.15,
            coalition_sway_skill=0.20,
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence=None,  # absent
        )
        resolution = mgr.preview_argument(dispute, argument)
        # 4.35 floor = 4 still, but difficulty is now 5.
        assert resolution.effective_floor == 4
        assert resolution.difficulty == 5
        assert resolution.passes is False
        assert resolution.evidence_absent_penalty == 1

    def test_disposition_modifier_increases_effective(self) -> None:
        """Disposition 60 -> +1 effective modifier (matches social.py:275)."""
        mgr, tpl = self._make_manager(persuasion=3)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        dispute.delegates["samela_drift"].disposition = 60
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.disposition_mod == 1

    def test_disposition_modifier_decreases_effective(self) -> None:
        """Disposition 30 -> -2 modifier (matches social.py:275)."""
        mgr, tpl = self._make_manager(persuasion=4)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        dispute.delegates["samela_drift"].disposition = 30
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        resolution = mgr.preview_argument(dispute, argument)
        # 4 + 1 + (-2) + 0 + 0 = 3 vs D4 -> fail.
        assert resolution.disposition_mod == -2
        assert resolution.effective_floor == 3
        assert resolution.passes is False

    def test_frontier_autonomy_routes_to_leadership(self) -> None:
        """SA-P1 §6.4: frontier_autonomy uses Leadership, not Persuasion."""
        mgr, tpl = self._make_manager(persuasion=1, leadership=4)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="frontier_autonomy",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.base_skill == 4

    def test_other_framings_route_to_persuasion(self) -> None:
        """SA-P1 §6.4 default: Persuasion is the base skill for argue mode."""
        mgr, tpl = self._make_manager(persuasion=4, leadership=1)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        for framing in (
            "data_precedent",
            "soil_impact",
            "practical_cost",
            "community_benefit",
        ):
            argument = PoliticsArgument(
                framing=framing,
                audience_delegate_id="samela_drift",
                evidence="forgeworks_2324_partnership",
            )
            resolution = mgr.preview_argument(dispute, argument)
            assert resolution.base_skill == 4, f"{framing} should use Persuasion"

    def test_mediate_uses_persuasion_even_for_frontier_autonomy(self) -> None:
        """SA-P1 §6.2 trailing line: mediate base skill is always Persuasion."""
        mgr, tpl = self._make_manager(persuasion=3, leadership=5)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="frontier_autonomy",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
            is_mediation=True,
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.base_skill == 3

    def test_mediate_uses_arbitration_bonuses_not_coalition(self) -> None:
        """Argue uses coalition_sway; mediate uses arbitration_neutrality."""
        mgr, tpl = self._make_manager(
            persuasion=3,
            coalition_sway_crew=0.15,
            coalition_sway_skill=0.20,
            arbitration_crew=0.0,
            arbitration_skill=0.0,
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        # In mediate mode, even with coalition bonuses available, the
        # crew/tree contributions read from arbitration_neutrality.
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
            is_mediation=True,
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.crew_bonus == pytest.approx(0.0)
        assert resolution.tree_bonus == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Slot dependency rules — SA-P1 §6.6
# ---------------------------------------------------------------------------


class TestArgumentSlotRules:
    def test_argument_without_framing_returns_failed_resolution(self) -> None:
        from spacegame.models.politics_dispute import (
            PoliticsArgument,
            PoliticsDisputeManager,
        )

        mgr = PoliticsDisputeManager(
            templates={
                _make_water_rights_phasing_template().id: (
                    _make_water_rights_phasing_template()
                )
            },
            social_manager=_StubSocial({"persuasion": 3}),
        )
        tpl = _make_water_rights_phasing_template()
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        # Empty framing string -> not a valid argument.
        argument = PoliticsArgument(
            framing="",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.passes is False
        assert resolution.error == "framing_required"

    def test_argument_without_audience_returns_failed_resolution(self) -> None:
        mgr = PoliticsDisputeManager(
            templates={
                _make_water_rights_phasing_template().id: (
                    _make_water_rights_phasing_template()
                )
            },
            social_manager=_StubSocial({"persuasion": 3}),
        )
        tpl = _make_water_rights_phasing_template()
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="",
            evidence="forgeworks_2324_partnership",
        )
        resolution = mgr.preview_argument(dispute, argument)
        assert resolution.passes is False
        assert resolution.error == "audience_required"
