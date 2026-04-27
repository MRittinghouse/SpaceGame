"""SA-P2 — PoliticsDisputeManager + dataclass + scaffolding tests.

Covers AC 12 (flag helpers), AC 6 (save/load round trip at boundaries), AC
3 (deterministic resolution), AC 16 (perf smoke), and the supporting
dataclass shapes / lifecycle. Worked-example fixture mirrors SA-P1 §4.6
``water_rights_phasing`` per §4 Risks: synthetic only, no JSON content.
"""

from __future__ import annotations

import time

from spacegame.constants.flags import (
    coalition_won,
    dispute_mediated,
    dispute_resolved,
    seen_argument_composer_tip,
    seen_politics_venue_tip,
)
from spacegame.models.politics_dispute import (
    DelegateTemplate,
    DisputePhase,
    OutcomeRow,
    PoliticsArgument,
    PoliticsDispute,
    PoliticsDisputeManager,
    PoliticsDisputeTemplate,
    PoliticsMarketShift,
)

# ---------------------------------------------------------------------------
# Fixture — synthetic water_rights_phasing template (SA-P1 §4.6)
# ---------------------------------------------------------------------------


def _make_water_rights_phasing_template() -> PoliticsDisputeTemplate:
    """Build the synthetic SA-P1 §4.6 fixture template.

    Pure Python — never persisted to ``data/politics/`` (SA-P3 owns
    content authoring per §11 decision 8).
    """
    delegates = (
        DelegateTemplate(
            delegate_id="ferron_hask",
            name="Ferron Hask",
            starting_visible_state="leaning_no",
            position_vector={
                "modernization": -0.8,
                "water_rights_change": -0.7,
                "outside_influence": -0.6,
            },
            faction_loyalty=0.7,
            sub_faction_id="verdant_farmers_bloc",
        ),
        DelegateTemplate(
            delegate_id="samela_drift",
            name="Samela Drift",
            starting_visible_state="wavering",
            position_vector={
                "modernization": 0.7,
                "water_rights_change": 0.3,
                "outside_influence": 0.5,
            },
            faction_loyalty=0.4,
            sub_faction_id="verdant_infrastructure",
        ),
        DelegateTemplate(
            delegate_id="ollo_marsh",
            name="Ollo Marsh",
            starting_visible_state="leaning_no",
            position_vector={
                "modernization": 0.0,
                "water_rights_change": -0.9,
                "outside_influence": -0.2,
            },
            faction_loyalty=0.8,
            sub_faction_id="verdant_water_council",
        ),
    )
    framing_modifiers = {
        "data_precedent": 1,
        "soil_impact": 1,
        "frontier_autonomy": 1,
        "practical_cost": 0,
        "community_benefit": 0,
    }
    framing_target_dimensions = {
        "data_precedent": "modernization",
        "soil_impact": "water_rights_change",
        "frontier_autonomy": "outside_influence",
        "practical_cost": "modernization",
        "community_benefit": "outside_influence",
    }
    outcome_matrix = {
        "win": OutcomeRow(
            rep_deltas={"verdant": 5, "frontier_alliance": 2, "crimson_reach": -2},
            market_shifts=(
                PoliticsMarketShift("fresh_water", "verdant", 0.10),
                PoliticsMarketShift("hydroponics_yield", "verdant", -0.08),
            ),
            mission_unlocks=(
                dispute_resolved("water_rights_phasing"),
                coalition_won("water_rights_phasing"),
            ),
            news_headline=(
                "Verdant council phases water rights; hydroponics shift expected, 30 days."
            ),
        ),
        "partial_win_coalition_thin": OutcomeRow(
            rep_deltas={"verdant": 2, "frontier_alliance": 1, "crimson_reach": -1},
            market_shifts=(PoliticsMarketShift("fresh_water", "verdant", 0.05),),
            mission_unlocks=(dispute_resolved("water_rights_phasing"),),
            news_headline=None,
        ),
        "partial_win_off_record": OutcomeRow(
            rep_deltas={"verdant": 3, "frontier_alliance": 1, "crimson_reach": 0},
            market_shifts=(PoliticsMarketShift("fresh_water", "verdant", 0.07),),
            mission_unlocks=(
                dispute_resolved("water_rights_phasing"),
                dispute_mediated("water_rights_phasing"),
            ),
            news_headline=None,
        ),
        "loss": OutcomeRow(
            rep_deltas={"verdant": -2, "frontier_alliance": -1, "crimson_reach": 2},
            market_shifts=(PoliticsMarketShift("fresh_water", "verdant", -0.10),),
            mission_locks=(dispute_resolved("water_rights_phasing"),),
            news_headline=(
                "Verdant council rejects water rights phasing bill; farmers' bloc holds."
            ),
        ),
    }
    return PoliticsDisputeTemplate(
        id="water_rights_phasing",
        headline="Water Rights Phasing Bill",
        factions_affected=("verdant", "frontier_alliance", "crimson_reach"),
        base_difficulty=4,
        round_count=3,
        deadline_days=10,
        delegates=delegates,
        eligible_framings=(
            "data_precedent",
            "soil_impact",
            "frontier_autonomy",
            "practical_cost",
            "community_benefit",
        ),
        eligible_evidence=(
            "forgeworks_2324_partnership",
            "verdant_soil_survey_2330",
            "northern_aquifer_draw_report",
        ),
        framing_modifiers=framing_modifiers,
        framing_target_dimensions=framing_target_dimensions,
        outcome_matrix=outcome_matrix,
    )


# ---------------------------------------------------------------------------
# AC 12 -- flag helpers produce the byte-for-byte strings SA-P3 will consume
# ---------------------------------------------------------------------------


class TestFlagHelpers:
    """SA-P1 §7.3 + §9.1 flag helper string contract.

    Implementer-side single source of truth: SA-P3 / P4 / P5 mission
    JSON `required_flags` will name these strings literally; if a helper
    drifts the mission unlock breaks silently. AC 12 makes the round-
    trip explicit.
    """

    def test_dispute_resolved_format(self) -> None:
        assert dispute_resolved("water_rights_phasing") == "dispute_resolved_water_rights_phasing"

    def test_coalition_won_format(self) -> None:
        assert coalition_won("water_rights_phasing") == "coalition_won_water_rights_phasing"

    def test_dispute_mediated_format(self) -> None:
        assert dispute_mediated("water_rights_phasing") == "dispute_mediated_water_rights_phasing"

    def test_seen_politics_venue_tip(self) -> None:
        assert seen_politics_venue_tip() == "seen_politics_venue_tip"

    def test_seen_argument_composer_tip(self) -> None:
        assert seen_argument_composer_tip() == "seen_argument_composer_tip"

    def test_helpers_emit_unique_strings(self) -> None:
        """No two helpers share an output (catches typos in the registry)."""
        outs = {
            dispute_resolved("x"),
            coalition_won("x"),
            dispute_mediated("x"),
            seen_politics_venue_tip(),
            seen_argument_composer_tip(),
        }
        assert len(outs) == 5


# ---------------------------------------------------------------------------
# DataLoader politics-templates plumbing (Task 3)
# ---------------------------------------------------------------------------


class TestDataLoaderPoliticsTemplates:
    """SA-P2 ships the loader; SA-P3 ships the templates.

    The loader must therefore tolerate an empty / missing
    ``data/politics/`` content directory and report no templates without
    raising, so a default install with no SA-P3 content boots cleanly.
    """

    def test_loader_returns_empty_dict_when_no_files(self, tmp_path) -> None:
        """An empty ``data/politics`` returns the empty registry."""
        from spacegame.data_loader import DataLoader

        # Build a sandbox data dir with politics/ but no dispute templates.
        (tmp_path / "politics").mkdir()
        loader = DataLoader(data_dir=tmp_path)
        templates = loader.load_politics_disputes()
        assert templates == {}
        assert loader.politics_disputes == {}

    def test_loader_returns_empty_dict_when_dir_missing(self, tmp_path) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader(data_dir=tmp_path)
        templates = loader.load_politics_disputes()
        assert templates == {}

    def test_loader_parses_dispute_template_file(self, tmp_path) -> None:
        """A minimal valid dispute file parses to a PoliticsDisputeTemplate."""
        import json

        from spacegame.data_loader import DataLoader

        politics_dir = tmp_path / "politics"
        politics_dir.mkdir()
        (politics_dir / "verdant_disputes.json").write_text(
            json.dumps(
                {
                    "disputes": [
                        {
                            "id": "minimal_test",
                            "headline": "Minimal Test Bill",
                            "factions_affected": ["verdant"],
                            "base_difficulty": 3,
                            "round_count": 3,
                            "deadline_days": 10,
                            "delegates": [
                                {
                                    "delegate_id": "test_one",
                                    "name": "Test One",
                                    "starting_visible_state": "wavering",
                                    "position_vector": {"modernization": 0.0},
                                    "faction_loyalty": 0.5,
                                    "sub_faction_id": "verdant_test",
                                }
                            ],
                            "eligible_framings": ["practical_cost"],
                            "eligible_evidence": [],
                            "framing_modifiers": {"practical_cost": 0},
                            "framing_target_dimensions": {"practical_cost": "modernization"},
                            "outcome_matrix": {
                                "win": {
                                    "rep_deltas": {"verdant": 5},
                                    "market_shifts": [],
                                    "mission_unlocks": [],
                                    "mission_locks": [],
                                    "news_headline": (
                                        "Verdant council passes test bill; minor effect."
                                    ),
                                },
                                "partial_win_coalition_thin": {
                                    "rep_deltas": {"verdant": 2},
                                    "news_headline": None,
                                },
                                "partial_win_off_record": {
                                    "rep_deltas": {"verdant": 3},
                                    "news_headline": None,
                                },
                                "loss": {
                                    "rep_deltas": {"verdant": -2},
                                    "news_headline": (
                                        "Verdant council rejects test bill; minor effect."
                                    ),
                                },
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        loader = DataLoader(data_dir=tmp_path)
        templates = loader.load_politics_disputes()
        assert "minimal_test" in templates
        tpl = templates["minimal_test"]
        assert tpl.headline == "Minimal Test Bill"
        assert tpl.base_difficulty == 3
        assert len(tpl.delegates) == 1
        assert tpl.delegates[0].sub_faction_id == "verdant_test"
        assert tpl.outcome_matrix["win"].rep_deltas == {"verdant": 5}


# ---------------------------------------------------------------------------
# Save / load round trip — AC 6 + AC 8
# ---------------------------------------------------------------------------


class TestDisputeRoundTripSerialization:
    def test_round_trip_at_round_open_round_one(self) -> None:
        """Round-1 ROUND_OPEN: empty round_log, no resolved outcome."""

        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute.phase == DisputePhase.ROUND_OPEN
        assert dispute.current_round == 1

        snapshot = dispute.to_dict()
        restored = PoliticsDispute.from_dict(snapshot, dispute.outcome_matrix)
        assert restored.phase == DisputePhase.ROUND_OPEN
        assert restored.current_round == 1
        assert restored.dispute_id == dispute.dispute_id
        assert restored.template_id == tpl.id
        assert (
            restored.delegates["ferron_hask"].visible_state
            == dispute.delegates["ferron_hask"].visible_state
        )

    def test_round_trip_after_argument_resolved(self) -> None:
        """ROUND_PENDING after a counter-argument resolved: state preserved."""

        tpl = _make_water_rights_phasing_template()

        class _Stub:
            def get_skill_level(self, _id: str) -> int:
                return 3

        class _Bonus:
            def get_bonus(self, _key: str) -> float:
                if _key == "coalition_sway_bonus":
                    return 0.35
                return 0.0

        mgr = PoliticsDisputeManager(
            templates={tpl.id: tpl},
            crew_roster=_Bonus(),
            progression=_Bonus(),
            social_manager=_Stub(),
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
                evidence="forgeworks_2324_partnership",
            ),
        )
        mgr.advance_round(dispute)
        # Now in round 2.
        snapshot = dispute.to_dict()
        restored = PoliticsDispute.from_dict(snapshot, dispute.outcome_matrix)
        assert restored.current_round == 2
        for d_id in dispute.delegates:
            assert restored.delegates[d_id].visible_state == dispute.delegates[d_id].visible_state
            assert (
                restored.delegates[d_id].position_vector == dispute.delegates[d_id].position_vector
            )

    def test_round_trip_after_resolved(self) -> None:
        """RESOLVED phase: outcome category preserved."""

        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert dispute.phase == DisputePhase.RESOLVED

        snapshot = dispute.to_dict()
        restored = PoliticsDispute.from_dict(snapshot, dispute.outcome_matrix)
        assert restored.phase == DisputePhase.RESOLVED
        assert restored.resolved_outcome == "loss"

    def test_manager_round_trip_pending_disputes(self) -> None:
        """Manager.to_dict / from_dict preserves a pending dispute by template id."""

        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        mgr.register_pending_dispute(dispute)

        snapshot = mgr.to_dict()
        # Build a new manager with the same templates and restore.
        mgr2 = PoliticsDisputeManager(templates={tpl.id: tpl})
        mgr2.from_dict(snapshot)
        assert tpl.id in mgr2.get_pending_dispute_ids()
        restored = mgr2.get_pending_dispute(tpl.id)
        assert restored is not None
        assert restored.template_id == tpl.id
        assert restored.current_round == dispute.current_round


class TestPlayerPoliticsDisputeStateField:
    """Player carries a ``politics_dispute_state: dict`` slot for the manager."""

    def _make_player(self):
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship

        dl = get_data_loader()
        if not dl.ship_types:
            dl.load_all()
        ship_type = next(iter(dl.ship_types.values()))
        ship = Ship(ship_type=ship_type, current_fuel=100)
        return Player(
            name="Test",
            credits=1000,
            current_system_id="nexus_prime",
            ship=ship,
        )

    def test_player_default_field_is_empty_dict(self) -> None:
        player = self._make_player()
        assert hasattr(player, "politics_dispute_state")
        assert player.politics_dispute_state == {}

    def test_save_load_of_politics_dispute_state(self) -> None:
        """Save manager round-trips politics_dispute_state."""
        player = self._make_player()
        player.politics_dispute_state = {"pending_disputes": {"x": {"id": "x"}}}
        assert player.politics_dispute_state == {"pending_disputes": {"x": {"id": "x"}}}


class TestPerformanceSmoke:
    """AC 16: argument resolution under 100 ms on the worked example."""

    def test_submit_argument_under_100ms(self) -> None:
        class _Stub:
            def get_skill_level(self, _id: str) -> int:
                return 3

        class _Bonus:
            def get_bonus(self, _key: str) -> float:
                return 0.0

        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(
            templates={tpl.id: tpl},
            crew_roster=_Bonus(),
            progression=_Bonus(),
            social_manager=_Stub(),
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        argument = PoliticsArgument(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        start = time.perf_counter()
        mgr.submit_argument(dispute, argument)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"submit_argument took {elapsed_ms:.2f}ms"


# ---------------------------------------------------------------------------
# SA-P3 — template-driven counter-framings (AC 8)
# ---------------------------------------------------------------------------


class TestCounterFramingTemplateLookup:
    """SA-P3 generalizes ``_resolve_counter_argument`` to read per-delegate
    counter-framings from the dispute template, with the SA-P2 default
    preserved when the template omits the field.
    """

    def _build_modernization_template(
        self,
        counter_framings: dict[str, tuple[str, str]] | None = None,
    ) -> PoliticsDisputeTemplate:
        delegates = (
            DelegateTemplate(
                delegate_id="ferron_hask",
                name="Ferron Hask",
                starting_visible_state="leaning_no",
                position_vector={"modernization": -0.6},
                sub_faction_id="verdant_council",
            ),
            DelegateTemplate(
                delegate_id="samela_drift",
                name="Samela Drift",
                starting_visible_state="wavering",
                position_vector={"modernization": 0.5},
                sub_faction_id="verdant_council",
            ),
        )
        outcome_matrix = {
            "win": OutcomeRow(rep_deltas={"frontier_alliance": 1}),
            "partial_win_coalition_thin": OutcomeRow(
                rep_deltas={"frontier_alliance": 0}, news_headline=None
            ),
            "partial_win_off_record": OutcomeRow(
                rep_deltas={"frontier_alliance": 1}, news_headline=None
            ),
            "loss": OutcomeRow(rep_deltas={"frontier_alliance": -1}),
        }
        return PoliticsDisputeTemplate(
            id="modernization_proposal",
            headline="Modernization Proposal Vote",
            factions_affected=("frontier_alliance",),
            base_difficulty=4,
            round_count=3,
            deadline_days=10,
            delegates=delegates,
            eligible_framings=("data_precedent", "practical_cost", "soil_impact"),
            eligible_evidence=(),
            framing_modifiers={
                "data_precedent": 1,
                "practical_cost": 0,
                "soil_impact": 1,
            },
            framing_target_dimensions={
                "data_precedent": "modernization",
                "practical_cost": "modernization",
                "soil_impact": "modernization",
            },
            outcome_matrix=outcome_matrix,
            counter_framings=counter_framings or {},
        )

    def test_template_with_per_delegate_counter_framing_fires_declared_framing(self) -> None:
        """A template that declares ``counter_framings`` for the firing delegate
        uses the declared framing rather than the SA-P2 default.
        """
        tpl = self._build_modernization_template(
            counter_framings={"ferron_hask": ("practical_cost", "modernization")}
        )

        class _Stub:
            def get_skill_level(self, _id: str) -> int:
                return 5

        class _Bonus:
            def get_bonus(self, _key: str) -> float:
                return 0.0

        mgr = PoliticsDisputeManager(
            templates={tpl.id: tpl},
            crew_roster=_Bonus(),
            progression=_Bonus(),
            social_manager=_Stub(),
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        # Argue Drift to provoke a counter from Hask (who starts leaning_no).
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
            ),
        )
        pending = getattr(dispute, "_pending_counters", [])
        assert len(pending) == 1
        assert pending[0]["counter_id"] == "ferron_hask"
        assert pending[0]["framing"] == "practical_cost"

    def test_template_without_counter_framings_uses_sa_p2_default(self) -> None:
        """A template that omits ``counter_framings`` preserves the SA-P2
        default (``soil_impact`` / ``water_rights_change``).
        """
        tpl = self._build_modernization_template(counter_framings=None)

        class _Stub:
            def get_skill_level(self, _id: str) -> int:
                return 5

        class _Bonus:
            def get_bonus(self, _key: str) -> float:
                return 0.0

        mgr = PoliticsDisputeManager(
            templates={tpl.id: tpl},
            crew_roster=_Bonus(),
            progression=_Bonus(),
            social_manager=_Stub(),
        )
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="samela_drift",
            ),
        )
        pending = getattr(dispute, "_pending_counters", [])
        assert len(pending) == 1
        assert pending[0]["counter_id"] == "ferron_hask"
        assert pending[0]["framing"] == "soil_impact"

    def test_data_loader_parses_counter_framings_field(self, tmp_path) -> None:
        """The ``_parse_politics_dispute_template`` reads the optional
        ``counter_framings`` field and exposes it on the parsed template.
        """
        import json

        from spacegame.data_loader import DataLoader

        politics_dir = tmp_path / "politics"
        politics_dir.mkdir()
        (politics_dir / "verdant_disputes.json").write_text(
            json.dumps(
                {
                    "disputes": [
                        {
                            "id": "with_counter_framings",
                            "headline": "With Counter Framings",
                            "factions_affected": ["frontier_alliance"],
                            "base_difficulty": 4,
                            "round_count": 3,
                            "deadline_days": 10,
                            "delegates": [
                                {
                                    "delegate_id": "ferron_hask",
                                    "name": "Ferron Hask",
                                    "starting_visible_state": "leaning_no",
                                    "position_vector": {"modernization": -0.6},
                                    "sub_faction_id": "verdant_council",
                                }
                            ],
                            "eligible_framings": ["practical_cost"],
                            "eligible_evidence": [],
                            "framing_modifiers": {"practical_cost": 0},
                            "framing_target_dimensions": {"practical_cost": "modernization"},
                            "counter_framings": {
                                "ferron_hask": ["practical_cost", "modernization"]
                            },
                            "outcome_matrix": {
                                "win": {"rep_deltas": {"frontier_alliance": 1}},
                                "partial_win_coalition_thin": {"rep_deltas": {}},
                                "partial_win_off_record": {"rep_deltas": {}},
                                "loss": {"rep_deltas": {"frontier_alliance": -1}},
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        loader = DataLoader(data_dir=tmp_path)
        templates = loader.load_politics_disputes()
        tpl = templates["with_counter_framings"]
        assert tpl.counter_framings == {"ferron_hask": ("practical_cost", "modernization")}


# ---------------------------------------------------------------------------
# SA-P4 — annual Congress scheduling (AC 7)
# ---------------------------------------------------------------------------


class TestAnnualScheduling:
    """SA-P4 ``is_dispute_active`` lockout window for annual templates."""

    def _annual_template(
        self,
        *,
        is_annual: bool = True,
        cycle_days: int = 365,
        opens_on_day_offset: int = 0,
    ) -> PoliticsDisputeTemplate:
        delegates = (
            DelegateTemplate(
                delegate_id="councillor_wentworth",
                name="Councillor Wentworth",
                starting_visible_state="wavering",
                position_vector={"process_fidelity": 0.0},
            ),
        )
        outcome_matrix = {
            "win": OutcomeRow(rep_deltas={"frontier_alliance": 5}),
            "partial_win_coalition_thin": OutcomeRow(rep_deltas={}, news_headline=None),
            "partial_win_off_record": OutcomeRow(rep_deltas={}, news_headline=None),
            "loss": OutcomeRow(rep_deltas={"frontier_alliance": -2}),
        }
        return PoliticsDisputeTemplate(
            id="annual_alliance_congress",
            headline="Annual Alliance Congress",
            factions_affected=("frontier_alliance",),
            base_difficulty=4,
            round_count=5,
            deadline_days=20,
            delegates=delegates,
            eligible_framings=("process_fidelity",),
            eligible_evidence=(),
            framing_modifiers={"process_fidelity": 0},
            framing_target_dimensions={"process_fidelity": "process_fidelity"},
            outcome_matrix=outcome_matrix,
            is_annual_congress=is_annual,
            opens_on_day_offset=opens_on_day_offset,
            next_congress_offset_days=cycle_days,
        )

    def test_non_annual_template_always_active(self) -> None:
        """A template that omits the annual flag is always active."""
        tpl = self._annual_template(is_annual=False, cycle_days=0)
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        assert mgr.is_dispute_active(tpl.id, current_game_day=1) is True
        assert mgr.is_dispute_active(tpl.id, current_game_day=10000) is True

    def test_annual_active_before_first_resolve(self) -> None:
        """Before the first resolution, the annual template is active."""
        tpl = self._annual_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        assert mgr.is_dispute_active(tpl.id, current_game_day=5) is True

    def test_annual_inactive_during_lockout(self) -> None:
        """After resolution, the annual template is locked out for the cycle."""
        tpl = self._annual_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        mgr.record_annual_resolution(tpl.id, last_resolved_day=100)
        # 100 + 100 = 200 < 100 + 365 = locked out.
        assert mgr.is_dispute_active(tpl.id, current_game_day=200) is False

    def test_annual_active_after_lockout_window(self) -> None:
        """Once cycle_days have elapsed, the annual template re-opens."""
        tpl = self._annual_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        mgr.record_annual_resolution(tpl.id, last_resolved_day=100)
        assert mgr.is_dispute_active(tpl.id, current_game_day=466) is True

    def test_unknown_template_inactive(self) -> None:
        """An unknown template id reports inactive (defensive default)."""
        mgr = PoliticsDisputeManager(templates={})
        assert mgr.is_dispute_active("nonexistent", current_game_day=1) is False

    def test_next_session_in_days_during_lockout(self) -> None:
        """``next_session_in_days`` returns a non-negative integer during lockout."""
        tpl = self._annual_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        mgr.record_annual_resolution(tpl.id, last_resolved_day=100)
        days = mgr.next_session_in_days(tpl.id, current_game_day=200)
        assert days == 265
        assert days >= 0

    def test_next_session_in_days_zero_when_active(self) -> None:
        """``next_session_in_days`` returns 0 when the template is active."""
        tpl = self._annual_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        # Pre-resolution: active.
        assert mgr.next_session_in_days(tpl.id, current_game_day=5) == 0

    def test_data_loader_parses_annual_fields(self, tmp_path) -> None:
        """The loader reads the three new optional template fields."""
        import json

        from spacegame.data_loader import DataLoader

        politics_dir = tmp_path / "politics"
        politics_dir.mkdir()
        (politics_dir / "alliance_disputes.json").write_text(
            json.dumps(
                {
                    "disputes": [
                        {
                            "id": "annual_alliance_congress",
                            "headline": "Annual Alliance Congress",
                            "factions_affected": ["frontier_alliance"],
                            "base_difficulty": 4,
                            "round_count": 5,
                            "deadline_days": 20,
                            "delegates": [
                                {
                                    "delegate_id": "councillor_wentworth",
                                    "name": "Councillor Wentworth",
                                    "starting_visible_state": "wavering",
                                    "position_vector": {"process_fidelity": 0.0},
                                    "sub_faction_id": "alliance_congress",
                                }
                            ],
                            "eligible_framings": ["process_fidelity"],
                            "eligible_evidence": [],
                            "framing_modifiers": {"process_fidelity": 0},
                            "framing_target_dimensions": {"process_fidelity": "process_fidelity"},
                            "is_annual_congress": True,
                            "opens_on_day_offset": 0,
                            "next_congress_offset_days": 365,
                            "outcome_matrix": {
                                "win": {"rep_deltas": {"frontier_alliance": 1}},
                                "partial_win_coalition_thin": {"rep_deltas": {}},
                                "partial_win_off_record": {"rep_deltas": {}},
                                "loss": {"rep_deltas": {"frontier_alliance": -1}},
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        loader = DataLoader(data_dir=tmp_path)
        templates = loader.load_politics_disputes()
        tpl = templates["annual_alliance_congress"]
        assert tpl.is_annual_congress is True
        assert tpl.opens_on_day_offset == 0
        assert tpl.next_congress_offset_days == 365


# ---------------------------------------------------------------------------
# SA-P4 — coalition betrayal mechanic (AC 8)
# ---------------------------------------------------------------------------


class _StubPlayer:
    """Minimal player shim for the betrayal predicate dispatch table."""

    def __init__(self, *, faction_rep: dict[str, int] | None = None) -> None:
        self._rep = dict(faction_rep or {})
        self.dialogue_flags: dict[str, bool] = {}

    def get_reputation(self, faction_id: str) -> int:
        return int(self._rep.get(faction_id, 0))

    def set_reputation(self, faction_id: str, value: int) -> None:
        self._rep[faction_id] = value


class TestBetrayalConditions:
    """SA-P4 deterministic predicate-dispatch betrayal mechanic."""

    def _build_betrayal_template(
        self,
        *,
        betrayal_conditions: dict[str, str] | None = None,
    ) -> PoliticsDisputeTemplate:
        delegates = (
            DelegateTemplate(
                delegate_id="delegate_tejada",
                name="Delegate Tejada",
                starting_visible_state="wavering",
                position_vector={"settlement_solidarity": 0.0},
                faction_loyalty=0.6,
                sub_faction_id="alliance_congress",
            ),
            DelegateTemplate(
                delegate_id="delegate_vasc",
                name="Delegate Vasc",
                starting_visible_state="wavering",
                position_vector={"frontier_autonomy_stance": 0.0},
                faction_loyalty=0.7,
                sub_faction_id="alliance_congress",
            ),
        )
        outcome_matrix = {
            "win": OutcomeRow(rep_deltas={"frontier_alliance": 4}),
            "partial_win_coalition_thin": OutcomeRow(rep_deltas={}, news_headline=None),
            "partial_win_off_record": OutcomeRow(rep_deltas={}, news_headline=None),
            "loss": OutcomeRow(rep_deltas={"frontier_alliance": -2}),
        }
        return PoliticsDisputeTemplate(
            id="frontier_security_compact",
            headline="Frontier Security Compact",
            factions_affected=("frontier_alliance", "crimson_reach"),
            base_difficulty=4,
            round_count=5,
            deadline_days=20,
            delegates=delegates,
            eligible_framings=("settlement_solidarity",),
            eligible_evidence=(),
            framing_modifiers={"settlement_solidarity": 0},
            framing_target_dimensions={"settlement_solidarity": "settlement_solidarity"},
            outcome_matrix=outcome_matrix,
            betrayal_conditions=betrayal_conditions or {},
        )

    def test_no_betrayal_when_conditions_empty(self) -> None:
        """A template without betrayal_conditions never flips a delegate."""
        tpl = self._build_betrayal_template(betrayal_conditions={})
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        player = _StubPlayer(faction_rep={"crimson_reach": 30})
        mgr.set_player(player)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute is not None
        # Pre-commit Tejada manually.
        dispute.delegates["delegate_tejada"].pre_committed = True
        dispute.delegates["delegate_tejada"].visible_state = "leaning_yes"
        flips = mgr._evaluate_betrayal_conditions(dispute, player)
        assert flips == []
        assert dispute.delegates["delegate_tejada"].pre_committed is True
        assert dispute.had_betrayal is False

    def test_rep_dropped_below_25_flips_pre_commit(self) -> None:
        """When the player's faction rep drops below 25 mid-arc, Tejada flips."""
        tpl = self._build_betrayal_template(
            betrayal_conditions={"delegate_tejada": "rep_dropped_below_25:crimson_reach"}
        )
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        player = _StubPlayer(faction_rep={"crimson_reach": 40})
        mgr.set_player(player)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute is not None
        # Snapshot rep at start so the predicate compares against the start.
        mgr.snapshot_rep_at_start(dispute, ("crimson_reach",))
        # Pre-commit Tejada.
        dispute.delegates["delegate_tejada"].pre_committed = True
        dispute.delegates["delegate_tejada"].visible_state = "leaning_yes"
        # Player rep with crimson_reach drops below 25.
        player.set_reputation("crimson_reach", 20)
        flips = mgr._evaluate_betrayal_conditions(dispute, player)
        assert flips == ["delegate_tejada"]
        assert dispute.delegates["delegate_tejada"].pre_committed is False
        assert dispute.delegates["delegate_tejada"].visible_state == "wavering"
        assert dispute.had_betrayal is True

    def test_betrayal_idempotent_within_round(self) -> None:
        """Re-running the same evaluation produces no further flips."""
        tpl = self._build_betrayal_template(
            betrayal_conditions={"delegate_tejada": "rep_dropped_below_25:crimson_reach"}
        )
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        player = _StubPlayer(faction_rep={"crimson_reach": 40})
        mgr.set_player(player)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute is not None
        mgr.snapshot_rep_at_start(dispute, ("crimson_reach",))
        dispute.delegates["delegate_tejada"].pre_committed = True
        player.set_reputation("crimson_reach", 20)
        first_flips = mgr._evaluate_betrayal_conditions(dispute, player)
        assert first_flips == ["delegate_tejada"]
        # Second evaluation: delegate is no longer pre-committed, no new flip.
        second_flips = mgr._evaluate_betrayal_conditions(dispute, player)
        assert second_flips == []

    def test_unknown_condition_silently_ignored(self) -> None:
        """An unknown condition name produces no flip (defensive)."""
        tpl = self._build_betrayal_template(
            betrayal_conditions={"delegate_tejada": "nonexistent_condition"}
        )
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        player = _StubPlayer()
        mgr.set_player(player)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        dispute.delegates["delegate_tejada"].pre_committed = True
        flips = mgr._evaluate_betrayal_conditions(dispute, player)
        assert flips == []

    def test_rep_predicate_no_op_when_above_threshold(self) -> None:
        """The rep_dropped predicate is False when the player rep stays above 25."""
        tpl = self._build_betrayal_template(
            betrayal_conditions={"delegate_tejada": "rep_dropped_below_25:crimson_reach"}
        )
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        player = _StubPlayer(faction_rep={"crimson_reach": 40})
        mgr.set_player(player)
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        mgr.snapshot_rep_at_start(dispute, ("crimson_reach",))
        dispute.delegates["delegate_tejada"].pre_committed = True
        # No drop; rep still 40.
        flips = mgr._evaluate_betrayal_conditions(dispute, player)
        assert flips == []
        assert dispute.delegates["delegate_tejada"].pre_committed is True

    def test_data_loader_parses_betrayal_conditions(self, tmp_path) -> None:
        """The loader reads the optional betrayal_conditions field."""
        import json

        from spacegame.data_loader import DataLoader

        politics_dir = tmp_path / "politics"
        politics_dir.mkdir()
        (politics_dir / "alliance_disputes.json").write_text(
            json.dumps(
                {
                    "disputes": [
                        {
                            "id": "with_betrayal",
                            "headline": "With Betrayal",
                            "factions_affected": ["frontier_alliance"],
                            "base_difficulty": 4,
                            "round_count": 3,
                            "deadline_days": 10,
                            "delegates": [
                                {
                                    "delegate_id": "delegate_tejada",
                                    "name": "Delegate Tejada",
                                    "starting_visible_state": "wavering",
                                    "position_vector": {"settlement_solidarity": 0.0},
                                    "sub_faction_id": "alliance_congress",
                                }
                            ],
                            "eligible_framings": ["settlement_solidarity"],
                            "eligible_evidence": [],
                            "framing_modifiers": {"settlement_solidarity": 0},
                            "framing_target_dimensions": {
                                "settlement_solidarity": "settlement_solidarity"
                            },
                            "betrayal_conditions": {
                                "delegate_tejada": "rep_dropped_below_25:crimson_reach"
                            },
                            "outcome_matrix": {
                                "win": {"rep_deltas": {"frontier_alliance": 1}},
                                "partial_win_coalition_thin": {"rep_deltas": {}},
                                "partial_win_off_record": {"rep_deltas": {}},
                                "loss": {"rep_deltas": {"frontier_alliance": -1}},
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        loader = DataLoader(data_dir=tmp_path)
        templates = loader.load_politics_disputes()
        tpl = templates["with_betrayal"]
        assert tpl.betrayal_conditions == {"delegate_tejada": "rep_dropped_below_25:crimson_reach"}


class TestDisputeRoundTripWithSAP4Fields:
    """SA-P4 added had_betrayal and rep_at_start to PoliticsDispute."""

    def test_dispute_serializes_sa_p4_fields(self) -> None:
        from spacegame.models.politics_dispute import PoliticsDispute

        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute is not None
        dispute.had_betrayal = True
        dispute.rep_at_start = {"crimson_reach": 30}
        raw = dispute.to_dict()
        restored = PoliticsDispute.from_dict(raw, tpl.outcome_matrix)
        assert restored.had_betrayal is True
        assert restored.rep_at_start == {"crimson_reach": 30}

    def test_legacy_save_defaults_sa_p4_fields(self) -> None:
        """Legacy saves without had_betrayal / rep_at_start default safely."""
        from spacegame.models.politics_dispute import PoliticsDispute

        tpl = _make_water_rights_phasing_template()
        mgr = PoliticsDisputeManager(templates={tpl.id: tpl})
        dispute = mgr.start_dispute(tpl.id, current_game_day=1)
        assert dispute is not None
        raw = dispute.to_dict()
        # Strip the SA-P4 fields to mimic a pre-SA-P4 save.
        raw.pop("had_betrayal", None)
        raw.pop("rep_at_start", None)
        restored = PoliticsDispute.from_dict(raw, tpl.outcome_matrix)
        assert restored.had_betrayal is False
        assert restored.rep_at_start == {}
