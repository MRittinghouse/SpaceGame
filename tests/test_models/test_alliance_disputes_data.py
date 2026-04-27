"""SA-P4 — data-validation tests for ``data/politics/alliance_disputes.json``.

Enforces SA-P1 §3.1 schema completeness for every shipped Alliance
Congress template, the four-issue-family categorization, the campaign-arc
count, the annual-Congress count, flag-helper round-trip, cross-references
against commodities / systems / factions, ≤80-char news headlines, and
the betrayal-condition validity from the engine dispatch table.
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
from spacegame.models.politics_dispute import (
    BETRAYAL_CONDITION_NAMES,
    PoliticsDisputeTemplate,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
ALLIANCE_PATH = PROJECT_ROOT / "data" / "politics" / "alliance_disputes.json"

# Categorize templates into the four Congress issue families per
# station_anchors.md:132. Exactly two templates per family.
ISSUE_FAMILIES: dict[str, set[str]] = {
    "inter_settlement_trade": {
        "cross_settlement_tariff_review",
        "frontier_trade_unification_act",
    },
    "defense_response": {
        "crimson_response_protocol_review",
        "frontier_security_compact",
    },
    "settlement_modernization": {
        "infrastructure_capital_pool",
        "cross_settlement_logistics_overhaul",
    },
    "cross_settlement_infrastructure": {
        "cross_settlement_water_compact",
        "annual_alliance_congress",
    },
}

# Four canonical Congress speakers per character_voices.md:1060-1228.
CONGRESS_DELEGATE_IDS = {
    "councillor_wentworth",
    "councillor_shirane",
    "delegate_vasc",
    "delegate_tejada",
}

# Four Congress dimensions per planner risk-lock.
CONGRESS_DIMENSIONS = {
    "frontier_autonomy_stance",
    "trade_leverage",
    "process_fidelity",
    "settlement_solidarity",
}

# Outcome categories per SA-P1 §5.1.
OUTCOME_CATEGORIES = (
    "win",
    "partial_win_coalition_thin",
    "partial_win_off_record",
    "loss",
)

# SA-P3 outcome flags this sprint's templates may gate on.
SA_P3_GATE_FLAGS = {
    "dispute_resolved_water_rights_phasing",
    "dispute_resolved_aquifer_concession_renewal",
    "dispute_resolved_frontier_trade_route_levy",
    "dispute_resolved_infrastructure_co_op_vote",
    "dispute_resolved_forgeworks_partnership_extension",
    "dispute_resolved_co_op_dividend_distribution",
    "dispute_resolved_hydroponics_yield_quota",
    "dispute_resolved_settler_food_credit_dispute",
    "coalition_won_water_rights_phasing",
    "coalition_won_aquifer_concession_renewal",
    "coalition_won_frontier_trade_route_levy",
    "coalition_won_infrastructure_co_op_vote",
    "coalition_won_forgeworks_partnership_extension",
    "coalition_won_co_op_dividend_distribution",
    "coalition_won_hydroponics_yield_quota",
    "coalition_won_settler_food_credit_dispute",
}


@pytest.fixture(scope="module")
def alliance_raw() -> list[dict]:
    """Raw JSON for the eight Congress templates."""
    with open(ALLIANCE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("disputes", []))


@pytest.fixture(scope="module")
def alliance_templates() -> dict[str, PoliticsDisputeTemplate]:
    """Loader-parsed Congress templates (Verdant filtered out)."""
    loader = DataLoader(data_dir=PROJECT_ROOT / "data")
    all_templates = loader.load_politics_disputes()
    congress_ids = set().union(*ISSUE_FAMILIES.values())
    return {tid: tpl for tid, tpl in all_templates.items() if tid in congress_ids}


@pytest.fixture(scope="module")
def commodity_ids() -> set[str]:
    path = PROJECT_ROOT / "data" / "economy" / "commodities.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"] for c in data["commodities"]}


@pytest.fixture(scope="module")
def system_ids() -> set[str]:
    path = PROJECT_ROOT / "data" / "galaxy" / "systems.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["id"] for s in data["systems"]}


@pytest.fixture(scope="module")
def faction_ids() -> set[str]:
    path = PROJECT_ROOT / "data" / "factions.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {f["id"] for f in data["factions"]}


# ---------------------------------------------------------------------------
# AC 1 — file exists, exactly 8 templates with required fields
# ---------------------------------------------------------------------------


class TestSchema:
    def test_file_exists(self) -> None:
        assert ALLIANCE_PATH.exists()

    def test_loads_eight_templates(self, alliance_templates) -> None:
        assert len(alliance_templates) == 8

    def test_required_fields_populated(self, alliance_templates) -> None:
        for tid, tpl in alliance_templates.items():
            assert tid == tpl.id
            assert tpl.headline
            assert tpl.factions_affected
            assert tpl.base_difficulty > 0
            assert tpl.round_count > 0
            assert tpl.deadline_days > 0
            assert len(tpl.delegates) >= 4
            assert tpl.eligible_framings
            assert tpl.framing_modifiers
            assert tpl.framing_target_dimensions

    def test_no_tbd_placeholders(self, alliance_raw) -> None:
        for entry in alliance_raw:
            blob = json.dumps(entry, ensure_ascii=False)
            assert "TBD" not in blob, f"{entry['id']} contains TBD"

    def test_all_four_outcome_categories(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for cat in OUTCOME_CATEGORIES:
                assert cat in tpl.outcome_matrix, f"{tpl.id} missing {cat}"


# ---------------------------------------------------------------------------
# AC 2 — issue-family categorization (2 per family)
# ---------------------------------------------------------------------------


class TestIssueFamilies:
    def test_two_per_family(self, alliance_templates) -> None:
        ids = set(alliance_templates)
        for family, family_ids in ISSUE_FAMILIES.items():
            present = ids & family_ids
            assert len(present) == 2, f"{family}: expected 2, got {present}"

    def test_total_categorized(self, alliance_templates) -> None:
        all_categorized = set().union(*ISSUE_FAMILIES.values())
        assert all_categorized == set(alliance_templates)


# ---------------------------------------------------------------------------
# AC 3 — exactly 3 campaign arcs, exactly 1 annual_congress
# ---------------------------------------------------------------------------


class TestCampaignAndAnnual:
    def test_exactly_three_campaign_arcs(self, alliance_templates) -> None:
        count = sum(1 for t in alliance_templates.values() if t.is_campaign_arc)
        assert count == 3

    def test_exactly_one_annual_congress(self, alliance_templates) -> None:
        count = sum(1 for t in alliance_templates.values() if t.is_annual_congress)
        assert count == 1

    def test_annual_congress_cycle_at_least_365(self, alliance_templates) -> None:
        annuals = [t for t in alliance_templates.values() if t.is_annual_congress]
        assert len(annuals) == 1
        assert annuals[0].next_congress_offset_days >= 365

    def test_annual_congress_is_also_campaign_arc(self, alliance_templates) -> None:
        annual = next(t for t in alliance_templates.values() if t.is_annual_congress)
        assert annual.is_campaign_arc is True

    def test_campaign_arcs_at_least_five_rounds(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            if tpl.is_campaign_arc:
                assert tpl.round_count >= 5, f"{tpl.id} campaign arc must be >=5 rounds"


# ---------------------------------------------------------------------------
# AC 4 — outcome matrix completeness, news-headline rules
# ---------------------------------------------------------------------------


class TestOutcomeMatrix:
    def test_win_loss_have_news_headline(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for cat in ("win", "loss"):
                assert tpl.outcome_matrix[cat].news_headline, f"{tpl.id}/{cat}"

    def test_news_headline_max_80_chars(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                if row.news_headline is None:
                    continue
                assert len(row.news_headline) <= 80, (
                    f"{tpl.id}/{cat}: {len(row.news_headline)} chars > 80"
                )

    def test_news_headline_no_em_dashes(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for _cat, row in tpl.outcome_matrix.items():
                if row.news_headline is None:
                    continue
                assert "—" not in row.news_headline
                assert "--" not in row.news_headline


# ---------------------------------------------------------------------------
# AC 5 — flag-helper round-trip
# ---------------------------------------------------------------------------


class TestFlagHelperRoundTrip:
    def test_mission_unlocks_round_trip(self, alliance_templates) -> None:
        valid: dict[str, set[str]] = {
            tid: {dispute_resolved(tid), coalition_won(tid), dispute_mediated(tid)}
            for tid in alliance_templates
        }
        for tpl in alliance_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for flag in row.mission_unlocks:
                    assert flag in valid[tpl.id], (
                        f"{tpl.id}/{cat}: flag {flag!r} fails helper round-trip"
                    )

    def test_mission_locks_round_trip(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for flag in row.mission_locks:
                    assert flag == dispute_resolved(tpl.id), f"{tpl.id}/{cat}: lock {flag!r}"

    def test_no_inline_dispute_strings_outside_helper(self, alliance_raw) -> None:
        legal_prefixes = (
            "dispute_resolved_",
            "coalition_won_",
            "dispute_mediated_",
        )
        for entry in alliance_raw:
            for cat, row in entry["outcome_matrix"].items():
                for flag in row.get("mission_unlocks", []) + row.get("mission_locks", []):
                    assert flag.startswith(legal_prefixes), f"{entry['id']}/{cat}: flag {flag!r}"


# ---------------------------------------------------------------------------
# AC 6 — cross-references (commodities, systems, factions, dimensions)
# ---------------------------------------------------------------------------


class TestCrossReferences:
    def test_commodity_ids_exist(self, alliance_templates, commodity_ids) -> None:
        for tpl in alliance_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for shift in row.market_shifts:
                    assert shift.commodity_id in commodity_ids, (
                        f"{tpl.id}/{cat}: unknown commodity {shift.commodity_id!r}"
                    )

    def test_system_ids_exist(self, alliance_templates, system_ids) -> None:
        for tpl in alliance_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for shift in row.market_shifts:
                    assert shift.system_id in system_ids, (
                        f"{tpl.id}/{cat}: unknown system {shift.system_id!r}"
                    )

    def test_rep_delta_factions_exist(self, alliance_templates, faction_ids) -> None:
        for tpl in alliance_templates.values():
            for cat, row in tpl.outcome_matrix.items():
                for fid in row.rep_deltas:
                    assert fid in faction_ids, f"{tpl.id}/{cat}: unknown faction {fid!r}"

    def test_factions_affected_in_factions_json(self, alliance_templates, faction_ids) -> None:
        for tpl in alliance_templates.values():
            for fid in tpl.factions_affected:
                assert fid in faction_ids, f"{tpl.id} factions_affected: {fid!r}"

    def test_dimensions_are_congress_canon(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for d in tpl.delegates:
                for dim in d.position_vector:
                    assert dim in CONGRESS_DIMENSIONS, (
                        f"{tpl.id}/{d.delegate_id}: dimension {dim!r} not Congress canon"
                    )

    def test_framing_target_dimensions_are_congress_canon(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for framing, dim in tpl.framing_target_dimensions.items():
                assert dim in CONGRESS_DIMENSIONS, (
                    f"{tpl.id}: framing {framing!r} target {dim!r} not Congress canon"
                )


# ---------------------------------------------------------------------------
# Delegate roster + sub-faction
# ---------------------------------------------------------------------------


class TestDelegates:
    def test_each_delegate_id_is_canonical_or_one_off(self, alliance_templates) -> None:
        """Each delegate id is one of the four Congress speakers OR a one-off."""
        for tpl in alliance_templates.values():
            for d in tpl.delegates:
                # One-off settlement reps allowed if they don't shadow a canon id.
                # SA-P4 ships all canonical; this is a soft assertion.
                assert d.delegate_id in CONGRESS_DELEGATE_IDS or d.delegate_id, (
                    f"{tpl.id}: empty delegate_id"
                )

    def test_each_delegate_uses_alliance_congress_sub_faction(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for d in tpl.delegates:
                assert d.sub_faction_id == "alliance_congress", (
                    f"{tpl.id}/{d.delegate_id}: sub_faction_id={d.sub_faction_id!r}"
                )

    def test_canonical_delegates_appear_in_every_template(self, alliance_templates) -> None:
        """All four Congress speakers appear in every template's roster."""
        for tpl in alliance_templates.values():
            ids = {d.delegate_id for d in tpl.delegates}
            assert CONGRESS_DELEGATE_IDS <= ids, (
                f"{tpl.id}: missing delegates {CONGRESS_DELEGATE_IDS - ids}"
            )


# ---------------------------------------------------------------------------
# Counter-framings
# ---------------------------------------------------------------------------


class TestCounterFramings:
    def test_keys_are_template_delegates(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            roster = {d.delegate_id for d in tpl.delegates}
            for delegate_id in tpl.counter_framings:
                assert delegate_id in roster, (
                    f"{tpl.id}: counter_framings key {delegate_id!r} not in roster"
                )

    def test_framings_in_eligible(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for delegate_id, (framing, _dim) in tpl.counter_framings.items():
                assert framing in tpl.eligible_framings, (
                    f"{tpl.id}: counter_framings[{delegate_id}] framing {framing!r}"
                )

    def test_dimensions_are_congress_canon(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for _delegate_id, (_framing, dim) in tpl.counter_framings.items():
                assert dim in CONGRESS_DIMENSIONS, (
                    f"{tpl.id}: counter dimension {dim!r} not Congress canon"
                )


# ---------------------------------------------------------------------------
# Betrayal conditions
# ---------------------------------------------------------------------------


class TestBetrayalConditions:
    def test_keys_are_template_delegates(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            roster = {d.delegate_id for d in tpl.delegates}
            for delegate_id in tpl.betrayal_conditions:
                assert delegate_id in roster, (
                    f"{tpl.id}: betrayal_conditions key {delegate_id!r} not in roster"
                )

    def test_condition_names_in_dispatch_table(self, alliance_templates) -> None:
        for tpl in alliance_templates.values():
            for _delegate_id, condition in tpl.betrayal_conditions.items():
                name = condition.split(":", 1)[0]
                assert name in BETRAYAL_CONDITION_NAMES, (
                    f"{tpl.id}: condition {condition!r} not in dispatch table"
                )

    def test_rep_dropped_argument_is_known_faction(self, alliance_templates, faction_ids) -> None:
        for tpl in alliance_templates.values():
            for _delegate_id, condition in tpl.betrayal_conditions.items():
                if not condition.startswith("rep_dropped_below_25:"):
                    continue
                _, faction_arg = condition.split(":", 1)
                assert faction_arg in faction_ids, (
                    f"{tpl.id}: rep_dropped target {faction_arg!r} not a known faction"
                )


# ---------------------------------------------------------------------------
# Cross-venue gate (at least 2 templates require SA-P3 outcomes)
# ---------------------------------------------------------------------------


class TestCrossVenueGate:
    def test_at_least_two_templates_gate_on_sa_p3(self, alliance_templates) -> None:
        gating = [
            tpl
            for tpl in alliance_templates.values()
            if any(flag in SA_P3_GATE_FLAGS for flag in tpl.required_flags)
        ]
        assert len(gating) >= 2, (
            f"Cross-venue gating: expected ≥2 templates, got {[t.id for t in gating]}"
        )


# ---------------------------------------------------------------------------
# Alliance-wide market shifts (≥4 templates with shifts at 2+ Alliance systems)
# ---------------------------------------------------------------------------


class TestAllianceWideMarketShifts:
    """At least 4 of 8 templates declare market shifts at 2+ Alliance systems."""

    ALLIANCE_SYSTEMS = {"havens_rest", "verdant", "forgeworks", "crimson_reach"}

    def test_at_least_four_templates_have_alliance_wide_shifts(self, alliance_templates) -> None:
        count = 0
        for tpl in alliance_templates.values():
            for _cat, row in tpl.outcome_matrix.items():
                systems = {s.system_id for s in row.market_shifts} & self.ALLIANCE_SYSTEMS
                if len(systems) >= 2:
                    count += 1
                    break
        assert count >= 4, f"Alliance-wide market shifts: expected ≥4 templates, got {count}"
