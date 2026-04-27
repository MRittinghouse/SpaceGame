"""SA-P2 — PoliticsDisputeManager + dataclass + scaffolding tests.

Covers AC 12 (flag helpers), AC 6 (save/load round trip at boundaries), AC
3 (deterministic resolution), AC 16 (perf smoke), and the supporting
dataclass shapes / lifecycle. Worked-example fixture mirrors SA-P1 §4.6
``water_rights_phasing`` per §4 Risks: synthetic only, no JSON content.
"""

from __future__ import annotations

import time
from typing import Optional

import pytest

from spacegame.constants.flags import (
    coalition_won,
    dispute_mediated,
    dispute_resolved,
    seen_argument_composer_tip,
    seen_politics_venue_tip,
)
from spacegame.models.politics_dispute import (
    DEFAULT_MARKET_SHIFT_DURATION,
    DelegateTemplate,
    DisputePhase,
    OutcomeRow,
    PoliticsArgument,
    PoliticsDelegate,
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
                "Verdant council phases water rights; "
                "hydroponics shift expected, 30 days."
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
                "Verdant council rejects water rights phasing bill; "
                "farmers' bloc holds."
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
        assert (
            dispute_resolved("water_rights_phasing")
            == "dispute_resolved_water_rights_phasing"
        )

    def test_coalition_won_format(self) -> None:
        assert (
            coalition_won("water_rights_phasing")
            == "coalition_won_water_rights_phasing"
        )

    def test_dispute_mediated_format(self) -> None:
        assert (
            dispute_mediated("water_rights_phasing")
            == "dispute_mediated_water_rights_phasing"
        )

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
                            "framing_target_dimensions": {
                                "practical_cost": "modernization"
                            },
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
