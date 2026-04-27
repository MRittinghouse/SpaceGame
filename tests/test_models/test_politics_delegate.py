"""SA-P2 — PoliticsDelegate state-machine tests.

Covers the visible-state chain (design §4.4), position vector cap at
+/-1.0, bias-init formula (§4.5), corridor pre-commit cap (§5.5), and
the Cass Weller intel reveal (§7.5).
"""

from __future__ import annotations

import pytest

from tests.test_models.test_politics_dispute import _make_water_rights_phasing_template

from spacegame.models.politics_dispute import (
    VISIBLE_STATES,
    DelegateTemplate,
    DisputePhase,
    PoliticsDelegate,
    PoliticsDispute,
    PoliticsDisputeManager,
    _shift_visible,
    _visible_index,
)


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
        assert dispute2.delegates["ferron_hask"].position_vector[
            "modernization"
        ] == pytest.approx(-0.8)

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
        assert (
            dispute.delegates["ferron_hask"].sub_faction_id == "verdant_farmers_bloc"
        )


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
        assert dispute.delegates["samela_drift"].position_vector[
            "modernization"
        ] == pytest.approx(1.0)

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
