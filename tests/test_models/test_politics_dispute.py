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
        assert tpl.counter_framings == {
            "ferron_hask": ("practical_cost", "modernization")
        }
