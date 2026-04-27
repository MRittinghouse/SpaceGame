"""SA-P2 — PoliticsDelegate state-machine tests.

Covers the visible-state chain (design §4.4), position vector cap at
+/-1.0, bias-init formula (§4.5), corridor pre-commit cap (§5.5), and
the Cass Weller intel reveal (§7.5).
"""

from __future__ import annotations

import pytest

from spacegame.models.politics_dispute import (
    VISIBLE_STATES,
    DisputePhase,
    PoliticsDelegate,
    PoliticsDisputeManager,
    _shift_visible,
    _visible_index,
)
from tests.test_models.test_politics_dispute import _make_water_rights_phasing_template

# ---------------------------------------------------------------------------
# Visible-state chain helpers
# ---------------------------------------------------------------------------


class TestVisibleStateChain:
    def test_chain_order(self) -> None:
        assert VISIBLE_STATES == (
            "committed_no",
            "leaning_no",
            "wavering",
            "leaning_yes",
            "committed_yes",
        )

    def test_index_round_trip(self) -> None:
        for i, state in enumerate(VISIBLE_STATES):
            assert _visible_index(state) == i

    def test_unknown_state_clamps_to_wavering(self) -> None:
        assert _visible_index("not_a_state") == VISIBLE_STATES.index("wavering")

    @pytest.mark.parametrize(
        "start,steps,expected",
        [
            ("committed_no", 1, "leaning_no"),
            ("leaning_no", 1, "wavering"),
            ("wavering", 1, "leaning_yes"),
            ("leaning_yes", 1, "committed_yes"),
            ("committed_yes", 1, "committed_yes"),  # capped at top
            ("leaning_yes", -1, "wavering"),
            ("wavering", -1, "leaning_no"),
            ("committed_no", -1, "committed_no"),  # capped at bottom
            ("wavering", 0, "wavering"),
            ("wavering", 5, "committed_yes"),  # clamps to top
            ("wavering", -5, "committed_no"),  # clamps to bottom
        ],
    )
    def test_shift_visible(self, start: str, steps: int, expected: str) -> None:
        assert _shift_visible(start, steps) == expected


# ---------------------------------------------------------------------------
# Bias initialization (design §4.5)
# ---------------------------------------------------------------------------


class TestBiasInitialization:
    def test_session_init_sets_starting_visible_states(self) -> None:
        """PoliticsDispute starts each delegate at template's starting state."""
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        assert dispute.delegates["ferron_hask"].visible_state == "leaning_no"
        assert dispute.delegates["samela_drift"].visible_state == "wavering"
        assert dispute.delegates["ollo_marsh"].visible_state == "leaning_no"

    def test_session_init_copies_position_vectors(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        hask = dispute.delegates["ferron_hask"]
        assert hask.position_vector["modernization"] == pytest.approx(-0.8)
        assert hask.position_vector["water_rights_change"] == pytest.approx(-0.7)
        assert hask.position_vector["outside_influence"] == pytest.approx(-0.6)

    def test_session_init_copies_position_vector_independently(self) -> None:
        """Mutating the runtime delegate must not affect the template."""
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        dispute.delegates["ferron_hask"].position_vector["modernization"] = 0.99

        # Re-instantiate; original template starting position must persist.
        dispute2 = mgr.start_dispute(tpl.id, current_game_day=2)
        assert dispute2.delegates["ferron_hask"].position_vector["modernization"] == pytest.approx(
            -0.8
        )

    def test_session_init_default_disposition(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        # All delegates start at DISPOSITION_DEFAULT (50) per social.py.
        for delegate in dispute.delegates.values():
            assert delegate.disposition == 50

    def test_session_init_phase_round_open_round_one(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        assert dispute.phase == DisputePhase.ROUND_OPEN
        assert dispute.current_round == 1

    def test_session_init_closes_on_day(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=42)

        # closes_on_day = current_game_day + template.deadline_days (10).
        assert dispute.closes_on_day == 52

    def test_session_init_unknown_template_returns_none(self) -> None:
        mgr = PoliticsDisputeManager(templates={})
        assert mgr.start_dispute("does_not_exist", current_game_day=1) is None

    def test_faction_loyalty_carries_to_runtime(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute.delegates["ferron_hask"].faction_loyalty == pytest.approx(0.7)
        assert dispute.delegates["samela_drift"].faction_loyalty == pytest.approx(0.4)
        assert dispute.delegates["ollo_marsh"].faction_loyalty == pytest.approx(0.8)

    def test_sub_faction_id_carries_to_runtime(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute.delegates["ferron_hask"].sub_faction_id == "verdant_farmers_bloc"


# ---------------------------------------------------------------------------
# Position vector cap at +/-1.0 (design §4.4)
# ---------------------------------------------------------------------------


class TestPositionVectorCap:
    def test_apply_argument_pass_caps_at_positive_one(self) -> None:
        """Repeated +0.20 advances cap at +1.0."""
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        # Drift modernization starts at +0.7. After two +0.20 nudges,
        # raw value is +1.10; capped to +1.0.
        for _ in range(5):
            mgr._apply_position_delta(
                dispute.delegates["samela_drift"],
                "modernization",
                0.20,
            )
        assert dispute.delegates["samela_drift"].position_vector["modernization"] == pytest.approx(
            1.0
        )

    def test_apply_argument_fail_caps_at_negative_one(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        # Hask outside_influence starts at -0.6. Eight -0.15 counter
        # nudges go to -1.80; capped to -1.0.
        for _ in range(8):
            mgr._apply_position_delta(
                dispute.delegates["ferron_hask"],
                "outside_influence",
                -0.15,
            )
        assert dispute.delegates["ferron_hask"].position_vector[
            "outside_influence"
        ] == pytest.approx(-1.0)

    def test_apply_to_unknown_dimension_initializes_then_caps(self) -> None:
        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)

        # New dimension 'process_fidelity' starts at 0.0; +0.20 brings
        # it to +0.20.
        mgr._apply_position_delta(
            dispute.delegates["ferron_hask"],
            "process_fidelity",
            0.20,
        )
        assert dispute.delegates["ferron_hask"].position_vector[
            "process_fidelity"
        ] == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestDelegateSerialization:
    def test_round_trip_preserves_all_fields(self) -> None:
        original = PoliticsDelegate(
            delegate_id="ferron_hask",
            name="Ferron Hask",
            visible_state="wavering",
            position_vector={"modernization": -0.5, "water_rights_change": 0.1},
            disposition=42,
            faction_loyalty=0.7,
            sub_faction_id="verdant_farmers_bloc",
            pre_committed=True,
            conceded=False,
            consecutive_corridor_fails=2,
        )
        restored = PoliticsDelegate.from_dict(original.to_dict())
        assert restored.delegate_id == original.delegate_id
        assert restored.name == original.name
        assert restored.visible_state == original.visible_state
        assert restored.position_vector == original.position_vector
        assert restored.disposition == original.disposition
        assert restored.faction_loyalty == pytest.approx(original.faction_loyalty)
        assert restored.sub_faction_id == original.sub_faction_id
        assert restored.pre_committed is original.pre_committed
        assert restored.conceded is original.conceded
        assert restored.consecutive_corridor_fails == original.consecutive_corridor_fails

    def test_from_dict_tolerates_missing_optional_fields(self) -> None:
        """Backward-compat for older saves: only delegate_id is required."""
        d = PoliticsDelegate.from_dict({"delegate_id": "x"})
        assert d.delegate_id == "x"
        assert d.disposition == 50
        assert d.position_vector == {}
        assert d.pre_committed is False


# ---------------------------------------------------------------------------
# Disposition modifier mirrors social.py exactly
# ---------------------------------------------------------------------------


class TestDispositionModifier:
    """SA-P2 must mirror social.py:275 byte-for-byte (`(disp - 50) // 10`).

    Floor-divide-toward-negative-infinity is the source-of-truth quirk:
    Python's `//` differs from `int(x // y)` for negative inputs in some
    languages, and we want to stay deterministic across save versions.
    """

    @pytest.mark.parametrize(
        "disposition,expected",
        [
            (50, 0),
            (60, 1),
            (59, 0),
            (40, -1),
            (49, -1),  # (49-50)//10 = -1//10 = -1 (floor toward -inf)
            (30, -2),
            (100, 5),
            (0, -5),
        ],
    )
    def test_disposition_modifier_formula(self, disposition: int, expected: int) -> None:
        from spacegame.models.politics_dispute import _disposition_modifier

        assert _disposition_modifier(disposition) == expected


# ---------------------------------------------------------------------------
# Per-round state machine — SA-P1 §2.2 + §4.4
# ---------------------------------------------------------------------------


class _StubBonus:
    def __init__(self, b: dict) -> None:
        self._b = b

    def get_bonus(self, key: str) -> float:
        return float(self._b.get(key, 0.0))


class _StubSocial:
    def __init__(self, levels: dict) -> None:
        self._l = levels

    def get_skill_level(self, skill_id: str) -> int:
        return int(self._l.get(skill_id, 1))


def _make_full_setup(
    persuasion: int = 3,
    coalition_sway_crew: float = 0.15,
    coalition_sway_skill: float = 0.20,
    arbitration_crew: float = 0.0,
    arbitration_skill: float = 0.0,
    coalition_size_crew: float = 0.0,
    coalition_size_skill: float = 0.0,
):
    from spacegame.models.politics_dispute import PoliticsDisputeManager

    tpl = _make_water_rights_phasing_template()
    crew = _StubBonus(
        {
            "coalition_sway_bonus": coalition_sway_crew,
            "arbitration_neutrality_bonus": arbitration_crew,
            "coalition_size_bonus": coalition_size_crew,
        }
    )
    progression = _StubBonus(
        {
            "coalition_sway_bonus": coalition_sway_skill,
            "arbitration_neutrality_bonus": arbitration_skill,
            "coalition_size_bonus": coalition_size_skill,
        }
    )
    social = _StubSocial({"persuasion": persuasion, "leadership": persuasion})
    mgr = PoliticsDisputeManager(
        templates={tpl.id: tpl},
        crew_roster=crew,
        progression=progression,
        social_manager=social,
    )
    dispute = mgr.start_dispute(tpl.id, current_game_day=1)
    return mgr, dispute


class TestPerRoundStateMachine:
    def test_submit_argument_pass_advances_target_one_step_toward_yes(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute = _make_full_setup()
        arg = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        assert dispute.delegates["samela_drift"].visible_state == "wavering"
        result = mgr.submit_argument(dispute, arg)
        assert result.passes is True
        # Drift moves wavering -> leaning_yes (counter then might revert, but
        # we're checking the open-arguments effect first; counter-argument
        # phase fires only on advance_round).
        assert dispute.delegates["samela_drift"].visible_state == "leaning_yes"
        assert dispute.delegates["samela_drift"].position_vector["modernization"] == pytest.approx(
            0.90
        )  # +0.7 + 0.20

    def test_submit_argument_fail_no_state_change(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute = _make_full_setup(persuasion=1)
        arg = PoliticsArgument(
            framing="practical_cost",  # 0 framing mod
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        # 1 + 0 + 0 + 0.15 + 0.20 = 1.35 -> floor 1 vs D4 -> fail
        before_state = dispute.delegates["samela_drift"].visible_state
        before_pos = dispute.delegates["samela_drift"].position_vector["modernization"]
        result = mgr.submit_argument(dispute, arg)
        assert result.passes is False
        assert dispute.delegates["samela_drift"].visible_state == before_state
        assert dispute.delegates["samela_drift"].position_vector["modernization"] == pytest.approx(
            before_pos
        )

    def test_committed_delegate_immune_to_arguments(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute = _make_full_setup()
        dispute.delegates["samela_drift"].visible_state = "committed_no"
        arg = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        mgr.submit_argument(dispute, arg)
        # Committed delegates do not move (§4.4).
        assert dispute.delegates["samela_drift"].visible_state == "committed_no"

    def test_advance_round_runs_counter_argument_phase(self) -> None:
        """Counter targets the most-favorable-toward-yes who isn't committed_yes."""
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute = _make_full_setup()
        # Round 1: argue Drift to leaning_yes.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
                evidence="forgeworks_2324_partnership",
            ),
        )
        assert dispute.delegates["samela_drift"].visible_state == "leaning_yes"
        # Counter phase: Hask (leaning_no at round start) fires counter at
        # the most-favorable-toward-yes, which is now Drift (leaning_yes,
        # not committed_yes).
        mgr.advance_round(dispute)
        # Drift dropped one step toward leaning_no.
        assert dispute.delegates["samela_drift"].visible_state == "wavering"
        # Round counter incremented.
        assert dispute.current_round == 2

    def test_responds_to_pre_empts_counter_argument(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute = _make_full_setup()
        # Round 1: argue Drift to leaning_yes WITH a soil_impact pre-load.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
                evidence="forgeworks_2324_partnership",
                responds_to="soil_impact",  # the Hask counter framing
            ),
        )
        # Hask's counter-argument framing happens to be soil_impact (the
        # canonical opposition response). responds_to should pre-empt.
        mgr.advance_round(dispute)
        assert dispute.delegates["samela_drift"].visible_state == "leaning_yes"

    def test_vote_immediate_does_not_run_counter_phase(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute = _make_full_setup()
        # Argue Drift to leaning_yes.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
                evidence="forgeworks_2324_partnership",
            ),
        )
        # Player votes immediately — counter does NOT fire.
        mgr.cast_vote(dispute)
        assert dispute.delegates["samela_drift"].visible_state == "leaning_yes"

    def test_abstain_advances_round_with_no_state_change(self) -> None:
        mgr, dispute = _make_full_setup()
        before_states = {d_id: d.visible_state for d_id, d in dispute.delegates.items()}
        mgr.abstain_round(dispute)
        for d_id, d in dispute.delegates.items():
            assert d.visible_state == before_states[d_id]
        assert dispute.current_round == 2

    def test_final_round_force_resolves_after_action(self) -> None:
        from spacegame.models.politics_dispute import (
            DisputePhase,
            PoliticsArgument,
        )

        mgr, dispute = _make_full_setup()
        # Walk to final round.
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        # Now on round 3 (final). Argue then advance triggers resolution.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
                evidence="forgeworks_2324_partnership",
            ),
        )
        mgr.advance_round(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.resolved_outcome is not None


class TestCoalitionPreCommitCap:
    """SA-P1 §5.5 cap formula across investment combinations."""

    @pytest.mark.parametrize(
        "crew_size,skill_size,expected_cap",
        [
            (0.0, 0.0, 1),  # bare base
            (1.0, 0.0, 2),  # Desta only
            (0.0, 0.5, 1),  # delegate_reach L1 alone (floor(0.5) = 0)
            (1.0, 0.5, 2),  # Desta + L1
            (1.0, 1.0, 3),  # Desta + delegate_reach L2
            (0.0, 1.0, 2),  # delegate_reach L2 alone
        ],
    )
    def test_pre_commit_cap_formula(
        self, crew_size: float, skill_size: float, expected_cap: int
    ) -> None:
        from spacegame.models.politics_dispute import PoliticsDisputeManager

        crew = _StubBonus({"coalition_size_bonus": crew_size})
        progression = _StubBonus({"coalition_size_bonus": skill_size})
        mgr = PoliticsDisputeManager(crew_roster=crew, progression=progression)
        assert mgr.get_pre_commit_cap() == expected_cap


class TestCorridorPreCommitVisit:
    """Successful corridor visits set pre_committed and override visible_state."""

    def test_successful_pre_commit_visit_sets_leaning_yes(self) -> None:
        mgr, dispute = _make_full_setup()
        # Force success by stubbing — the underlying resolve_check call
        # is mocked here via the manager's helper.
        ok, _msg = mgr.do_corridor_visit(
            dispute,
            delegate_id="samela_drift",
            framing="practical_cost",
            success_override=True,
        )
        assert ok is True
        assert dispute.delegates["samela_drift"].pre_committed is True
        assert dispute.delegates["samela_drift"].visible_state == "leaning_yes"

    def test_failed_visit_increments_consecutive_fails_and_no_state_change(
        self,
    ) -> None:
        mgr, dispute = _make_full_setup()
        before_state = dispute.delegates["samela_drift"].visible_state
        ok, _msg = mgr.do_corridor_visit(
            dispute,
            delegate_id="samela_drift",
            framing="practical_cost",
            success_override=False,
        )
        assert ok is False
        assert dispute.delegates["samela_drift"].pre_committed is False
        assert dispute.delegates["samela_drift"].visible_state == before_state
        assert dispute.delegates["samela_drift"].consecutive_corridor_fails == 1

    def test_repeated_failures_escalate_difficulty_in_get_corridor_difficulty(
        self,
    ) -> None:
        """Per §5.5: each consecutive fail adds +1 to next visit's difficulty."""
        mgr, dispute = _make_full_setup()
        base_diff = mgr.get_corridor_difficulty(dispute, "samela_drift")
        mgr.do_corridor_visit(
            dispute,
            delegate_id="samela_drift",
            framing="practical_cost",
            success_override=False,
        )
        assert mgr.get_corridor_difficulty(dispute, "samela_drift") == base_diff + 1
        mgr.do_corridor_visit(
            dispute,
            delegate_id="samela_drift",
            framing="practical_cost",
            success_override=False,
        )
        assert mgr.get_corridor_difficulty(dispute, "samela_drift") == base_diff + 2

    def test_success_resets_consecutive_fail_counter(self) -> None:
        mgr, dispute = _make_full_setup()
        mgr.do_corridor_visit(
            dispute,
            delegate_id="samela_drift",
            framing="practical_cost",
            success_override=False,
        )
        mgr.do_corridor_visit(
            dispute,
            delegate_id="samela_drift",
            framing="practical_cost",
            success_override=True,
        )
        assert dispute.delegates["samela_drift"].consecutive_corridor_fails == 0

    def test_starting_position_distribution_changes_with_pre_commits(self) -> None:
        """AC 7: 0 / 1 / 2 pre-commits produce strictly different starting distributions."""
        _mgr_0, dispute_0 = _make_full_setup()
        mgr_1, dispute_1 = _make_full_setup(coalition_size_crew=1.0)
        mgr_2, dispute_2 = _make_full_setup(coalition_size_crew=1.0, coalition_size_skill=1.0)

        mgr_1.do_corridor_visit(dispute_1, "samela_drift", "practical_cost", success_override=True)
        mgr_2.do_corridor_visit(dispute_2, "samela_drift", "practical_cost", success_override=True)
        mgr_2.do_corridor_visit(dispute_2, "ferron_hask", "practical_cost", success_override=True)

        states_0 = sorted(d.visible_state for d in dispute_0.delegates.values())
        states_1 = sorted(d.visible_state for d in dispute_1.delegates.values())
        states_2 = sorted(d.visible_state for d in dispute_2.delegates.values())

        assert states_0 != states_1
        assert states_1 != states_2
        assert states_0 != states_2

    def test_pre_commit_cap_blocks_excess_visits(self) -> None:
        """Bare base cap is 1; second commit attempt blocks even if check passes."""
        mgr, dispute = _make_full_setup(coalition_sway_crew=0.0, coalition_sway_skill=0.0)
        # Override the manager's coalition_size bonus to bare base.
        # _make_full_setup wires both to 0.15 by default, but
        # coalition_size_bonus is a separate key — it's already 0.0.
        ok1, _ = mgr.do_corridor_visit(
            dispute, "samela_drift", "practical_cost", success_override=True
        )
        ok2, msg = mgr.do_corridor_visit(
            dispute, "ferron_hask", "practical_cost", success_override=True
        )
        assert ok1 is True
        assert ok2 is False
        assert "cap" in msg.lower()


class TestCassWellerIntelReveal:
    """SA-P1 §7.5: Cass Weller's binary bonus reveals position vectors qualitatively."""

    def test_intel_reveal_returns_qualitative_text_per_dimension(self) -> None:
        from spacegame.models.politics_dispute import (
            qualitative_position_summary,
        )

        # High negative threshold -> "Skeptical of"; high positive -> "Open to";
        # near zero -> "Undecided on" (neutral band).
        summary_hask = qualitative_position_summary(
            {
                "modernization": -0.8,
                "water_rights_change": -0.7,
                "outside_influence": -0.6,
            }
        )
        assert "Skeptical of modernization" in summary_hask
        assert "Skeptical of outside influence" in summary_hask

        summary_drift = qualitative_position_summary(
            {
                "modernization": 0.7,
                "water_rights_change": 0.3,
                "outside_influence": 0.5,
            }
        )
        assert "Open to modernization" in summary_drift
        assert "Open to outside influence" in summary_drift

    def test_intel_reveal_text_has_no_em_dashes_or_banned_phrases(self) -> None:
        from spacegame.models.politics_dispute import (
            qualitative_position_summary,
        )

        sample = qualitative_position_summary(
            {
                "modernization": -0.8,
                "water_rights_change": 0.3,
                "outside_influence": 0.0,
            }
        )
        # Writing Bible: no em-dashes, no banned phrases.
        assert "—" not in sample
        assert "–" not in sample
        assert " -- " not in sample
        assert "couldn't help but" not in sample.lower()
        assert "a testament to" not in sample.lower()

    def test_intel_reveal_fires_once_per_session(self) -> None:
        from spacegame.models.politics_dispute import PoliticsDisputeManager

        crew_with_cass = _StubBonus({"arbitration_dispute_intel": 1.0})
        mgr = PoliticsDisputeManager(
            templates={
                _make_water_rights_phasing_template().id: (_make_water_rights_phasing_template())
            },
            crew_roster=crew_with_cass,
        )
        tpl = _make_water_rights_phasing_template()
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        # First reveal returns content.
        first = mgr.try_reveal_intel(dispute)
        assert first is not None
        assert len(first) > 0
        # Second call same session returns None.
        second = mgr.try_reveal_intel(dispute)
        assert second is None
        # New session resets the gate.
        mgr.end_session()
        third = mgr.try_reveal_intel(dispute)
        assert third is not None

    def test_intel_reveal_no_op_when_cass_not_on_crew(self) -> None:
        from spacegame.models.politics_dispute import PoliticsDisputeManager

        crew_no_cass = _StubBonus({})
        mgr = PoliticsDisputeManager(
            templates={
                _make_water_rights_phasing_template().id: (_make_water_rights_phasing_template())
            },
            crew_roster=crew_no_cass,
        )
        tpl = _make_water_rights_phasing_template()
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        result = mgr.try_reveal_intel(dispute)
        assert result is None


class TestDeterministicResolution:
    """AC 3: same inputs always produce identical outputs (no randomness)."""

    def test_same_inputs_produce_identical_dispute_state_two_runs(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr_a, dispute_a = _make_full_setup()
        mgr_b, dispute_b = _make_full_setup()

        for mgr, dispute in ((mgr_a, dispute_a), (mgr_b, dispute_b)):
            mgr.submit_argument(
                dispute,
                PoliticsArgument(
                    framing="data_precedent",
                    audience_delegate_id="samela_drift",
                    evidence="forgeworks_2324_partnership",
                ),
            )
            mgr.advance_round(dispute)
            mgr.submit_argument(
                dispute,
                PoliticsArgument(
                    framing="soil_impact",
                    audience_delegate_id="ferron_hask",
                    evidence="verdant_soil_survey_2330",
                    responds_to="data_precedent",
                ),
            )
            mgr.advance_round(dispute)

        for d_id in dispute_a.delegates:
            assert (
                dispute_a.delegates[d_id].visible_state == dispute_b.delegates[d_id].visible_state
            )
            assert (
                dispute_a.delegates[d_id].position_vector
                == dispute_b.delegates[d_id].position_vector
            )
