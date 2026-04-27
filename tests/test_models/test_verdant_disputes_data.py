"""SA-P3 — data-validation tests for ``data/politics/verdant_disputes.json``.

Enforces SA-P1 §3.1 schema completeness for every shipped Verdant
template, the four-issue-family categorization, the campaign-arc count,
flag-helper round-trip, cross-references against commodities / systems /
factions, and ≤80-char news headlines.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacegame.constants.flags import (
    coalition_won,
    dispute_mediated,
    dispute_resolved,
)
from spacegame.data_loader import DataLoader
from spacegame.models.politics_dispute import PoliticsDisputeTemplate

PROJECT_ROOT = Path(__file__).parent.parent.parent
VERDANT_PATH = PROJECT_ROOT / "data" / "politics" / "verdant_disputes.json"

# Categorize templates into the four Verdant issue families. Synced with
# the planner's hand-off (ROADMAP SA-P3 plan, step 5).
ISSUE_FAMILIES: dict[str, set[str]] = {
    "water_rights": {"water_rights_phasing", "aquifer_concession_renewal"},
    "modernization": {"infrastructure_co_op_vote", "forgeworks_partnership_extension"},
    "hydroponics_co_op": {"co_op_dividend_distribution", "hydroponics_yield_quota"},
    "settler_trade": {"settler_food_credit_dispute", "frontier_trade_route_levy"},
}
ALL_VERDANT_DELEGATE_IDS = {
    "mayor_vance",
    "delegate_hask",
    "delegate_drift",
    "delegate_marsh",
}

# Outcome categories per SA-P1 §5.1.
OUTCOME_CATEGORIES = (
    "win",
    "partial_win_coalition_thin",
    "partial_win_off_record",
    "loss",
)


@pytest.fixture(scope="module")
def verdant_raw() -> list[dict]:
    """Raw JSON for the eight Verdant templates."""
    with open(VERDANT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("disputes", []))


@pytest.fixture(scope="module")
def verdant_templates() -> dict[str, PoliticsDisputeTemplate]:
    """Loader-parsed Verdant templates keyed by template id.

    SA-P4 added Alliance Congress templates that load through the same
    ``data/politics`` directory; filter to the SA-P3 issue families so
    these tests only assert against Verdant content.
    """
    loader = DataLoader(data_dir=PROJECT_ROOT / "data")
    all_templates = loader.load_politics_disputes()
    verdant_ids = set().union(*ISSUE_FAMILIES.values())
    return {tid: tpl for tid, tpl in all_templates.items() if tid in verdant_ids}


@pytest.fixture(scope="module")
def commodity_ids() -> set[str]:
    """All commodity ids in ``data/economy/commodities.json``."""
    path = PROJECT_ROOT / "data" / "economy" / "commodities.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"] for c in data["commodities"]}


@pytest.fixture(scope="module")
def system_ids() -> set[str]:
    """All system ids in ``data/galaxy/systems.json``."""
    path = PROJECT_ROOT / "data" / "galaxy" / "systems.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["id"] for s in data["systems"]}


@pytest.fixture(scope="module")
def faction_ids() -> set[str]:
    """All faction ids in ``data/factions.json``."""
    path = PROJECT_ROOT / "data" / "factions.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {f["id"] for f in data["factions"]}


# ---------------------------------------------------------------------------
# AC 1 — file exists, parses, exactly 8 templates with required fields
# ---------------------------------------------------------------------------


class TestSchema:
    def test_file_exists(self) -> None:
        assert VERDANT_PATH.exists()

    def test_loads_eight_templates(self, verdant_templates) -> None:
        assert len(verdant_templates) == 8

    def test_loads_through_data_loader_without_error(self, verdant_templates) -> None:
        for tid, tpl in verdant_templates.items():
            assert tid == tpl.id
            assert tpl.headline
            assert tpl.factions_affected
            assert tpl.base_difficulty > 0
            assert tpl.round_count > 0
            assert tpl.deadline_days > 0
            assert len(tpl.delegates) == 4
            assert tpl.eligible_framings
            assert tpl.framing_modifiers
            assert tpl.framing_target_dimensions

    def test_required_fields_non_tbd(self, verdant_raw) -> None:
        """No literal ``TBD`` anchor strings hide in shipped content."""
        for entry in verdant_raw:
            blob = json.dumps(entry, ensure_ascii=False)
            assert "TBD" not in blob, f"{entry['id']} contains TBD placeholder"

    def test_outcome_matrix_carries_all_four_categories(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for cat in OUTCOME_CATEGORIES:
                assert cat in tpl.outcome_matrix, f"{tpl.id} missing outcome category {cat}"


# ---------------------------------------------------------------------------
# AC 2 — issue-family categorization
# ---------------------------------------------------------------------------


class TestIssueFamilies:
    def test_two_per_family(self, verdant_templates) -> None:
        ids = set(verdant_templates)
        for family, family_ids in ISSUE_FAMILIES.items():
            present = ids & family_ids
            assert len(present) == 2, f"{family}: expected 2 templates, got {present}"

    def test_total_categorized(self, verdant_templates) -> None:
        all_categorized = set().union(*ISSUE_FAMILIES.values())
        assert all_categorized == set(verdant_templates)


# ---------------------------------------------------------------------------
# AC 3 — exactly 2 campaign arcs
# ---------------------------------------------------------------------------


class TestCampaignArcs:
    def test_exactly_two_campaign_arcs(self, verdant_templates) -> None:
        count = sum(1 for t in verdant_templates.values() if t.is_campaign_arc)
        assert count == 2

    def test_modernization_proposal_is_campaign_arc(self, verdant_templates) -> None:
        # Per station_anchors.md:131, modernization-proposal recurring debate.
        assert verdant_templates["infrastructure_co_op_vote"].is_campaign_arc is True

    def test_campaign_arcs_run_at_least_five_rounds(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            if tpl.is_campaign_arc:
                assert tpl.round_count >= 5, f"{tpl.id} campaign arc must be ≥5 rounds"


# ---------------------------------------------------------------------------
# AC 4 — outcome matrix completeness, news headline rules
# ---------------------------------------------------------------------------


class TestOutcomeMatrix:
    def test_win_loss_have_news_headline(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for cat in ("win", "loss"):
                row = tpl.outcome_matrix[cat]
                assert row.news_headline, f"{tpl.id}/{cat} missing news_headline"

    def test_news_headline_max_80_chars(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                if row.news_headline is None:
                    continue
                assert len(row.news_headline) <= 80, (
                    f"{tpl.id}/{cat}: headline {len(row.news_headline)} chars > 80: "
                    f"{row.news_headline!r}"
                )

    def test_news_headline_no_em_dashes(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for _cat, row in tpl.outcome_matrix.items():
                if row.news_headline is None:
                    continue
                assert "—" not in row.news_headline
                assert "--" not in row.news_headline


# ---------------------------------------------------------------------------
# AC 5 — flag-helper round-trip on mission_unlocks / mission_locks
# ---------------------------------------------------------------------------


class TestFlagHelperRoundTrip:
    """Every flag string in the outcome matrix matches exactly the helper output."""

    def test_mission_unlocks_round_trip(self, verdant_templates) -> None:
        valid_strings: dict[str, set[str]] = {
            tid: {
                dispute_resolved(tid),
                coalition_won(tid),
                dispute_mediated(tid),
            }
            for tid in verdant_templates
        }
        for tpl in verdant_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for flag in row.mission_unlocks:
                    assert flag in valid_strings[tpl.id], (
                        f"{tpl.id}/{cat}: flag {flag!r} does not round-trip "
                        f"through any of dispute_resolved/coalition_won/dispute_mediated"
                    )

    def test_mission_locks_round_trip(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for flag in row.mission_locks:
                    assert flag == dispute_resolved(tpl.id), (
                        f"{tpl.id}/{cat}: lock {flag!r} should equal dispute_resolved({tpl.id!r})"
                    )

    def test_no_inline_dispute_strings_outside_helper(self, verdant_raw) -> None:
        """Every inline ``dispute_*`` string starts with a helper-prefix."""
        legal_prefixes = (
            "dispute_resolved_",
            "coalition_won_",
            "dispute_mediated_",
        )
        for entry in verdant_raw:
            for cat, row in entry["outcome_matrix"].items():
                for flag in row.get("mission_unlocks", []) + row.get("mission_locks", []):
                    assert flag.startswith(legal_prefixes), (
                        f"{entry['id']}/{cat}: flag {flag!r} does not start with a "
                        f"helper prefix {legal_prefixes}"
                    )


# ---------------------------------------------------------------------------
# AC 6 — cross-references against commodities / systems / factions
# ---------------------------------------------------------------------------


class TestCrossReferences:
    def test_commodity_ids_exist(self, verdant_templates, commodity_ids) -> None:
        for tpl in verdant_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for shift in row.market_shifts:
                    assert shift.commodity_id in commodity_ids, (
                        f"{tpl.id}/{cat}: unknown commodity {shift.commodity_id!r}"
                    )

    def test_system_ids_exist(self, verdant_templates, system_ids) -> None:
        for tpl in verdant_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for shift in row.market_shifts:
                    assert shift.system_id in system_ids, (
                        f"{tpl.id}/{cat}: unknown system {shift.system_id!r}"
                    )

    def test_faction_ids_exist_in_factions_json(self, verdant_templates, faction_ids) -> None:
        for tpl in verdant_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for fid in row.rep_deltas:
                    assert fid in faction_ids, f"{tpl.id}/{cat}: unknown faction id {fid!r}"

    def test_factions_affected_in_factions_json(self, verdant_templates, faction_ids) -> None:
        for tpl in verdant_templates.values():
            for fid in tpl.factions_affected:
                assert fid in faction_ids, f"{tpl.id} factions_affected: {fid!r}"


# ---------------------------------------------------------------------------
# AC 14 — delegate roster + sub-faction id
# ---------------------------------------------------------------------------


class TestDelegates:
    def test_each_delegate_id_is_one_of_four(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            ids = {d.delegate_id for d in tpl.delegates}
            assert ids <= ALL_VERDANT_DELEGATE_IDS, (
                f"{tpl.id}: unknown delegate ids {ids - ALL_VERDANT_DELEGATE_IDS}"
            )

    def test_each_delegate_uses_verdant_council_sub_faction(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for d in tpl.delegates:
                assert d.sub_faction_id == "verdant_council", (
                    f"{tpl.id}/{d.delegate_id}: sub_faction_id={d.sub_faction_id!r}"
                )


# ---------------------------------------------------------------------------
# Counter-framings field validity (§ planner risk lock)
# ---------------------------------------------------------------------------


class TestCounterFramings:
    def test_keys_are_template_delegates(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            roster = {d.delegate_id for d in tpl.delegates}
            for delegate_id in tpl.counter_framings:
                assert delegate_id in roster, (
                    f"{tpl.id}: counter_framings key {delegate_id!r} not in roster"
                )

    def test_framing_values_appear_in_eligible_framings(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            for delegate_id, (framing, _dim) in tpl.counter_framings.items():
                assert framing in tpl.eligible_framings, (
                    f"{tpl.id}: counter_framings[{delegate_id}] framing "
                    f"{framing!r} not in eligible_framings {tpl.eligible_framings}"
                )

    def test_dimensions_appear_in_framing_target_dimensions(self, verdant_templates) -> None:
        for tpl in verdant_templates.values():
            valid_dims = set(tpl.framing_target_dimensions.values())
            for delegate_id, (_framing, dim) in tpl.counter_framings.items():
                assert dim in valid_dims, (
                    f"{tpl.id}: counter_framings[{delegate_id}] dimension "
                    f"{dim!r} not in framing_target_dimensions"
                )

    def test_five_templates_declare_counter_framings(self, verdant_templates) -> None:
        """Plan locks 5 of 8 templates declare per-delegate counter-framings."""
        with_overrides = sum(1 for t in verdant_templates.values() if t.counter_framings)
        assert with_overrides == 5
