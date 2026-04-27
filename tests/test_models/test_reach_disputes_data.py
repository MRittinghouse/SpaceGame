"""SA-P5 — data-validation tests for data/politics/reach_disputes.json.

AC 1, 2, 3, 4, 5, 6 (cross-reference assertions). Enforces schema
completeness, issue-family categorization, campaign-arc count,
outcome-matrix completeness, flag-helper round-trips, and cross-
reference validity against commodity, system, faction, and framing data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacegame.constants.flags import coalition_won, dispute_mediated, dispute_resolved
from spacegame.data_loader import DataLoader

PROJECT_ROOT = Path(__file__).parent.parent.parent
REACH_DISPUTES_PATH = PROJECT_ROOT / "data" / "politics" / "reach_disputes.json"
COMMODITIES_PATH = PROJECT_ROOT / "data" / "economy" / "commodities.json"
SYSTEMS_PATH = PROJECT_ROOT / "data" / "galaxy" / "systems.json"
FACTIONS_PATH = PROJECT_ROOT / "data" / "factions.json"

REACH_DIMENSIONS = frozenset(
    {"salvage_rights_position", "gray_market_compliance", "crew_solidarity"}
)
REACH_FRAMINGS = frozenset(
    {"salvage_precedent", "crew_loyalty", "street_authority", "practical_cost", "frontier_autonomy"}
)
VALID_BETRAYAL_CONDITIONS = frozenset(
    {"rep_dropped_below_25:crimson_reach", "counter_framing_succeeded", "rival_faction_unfavored"}
)
ISSUE_FAMILIES = frozenset(
    {
        "salvage_rights",
        "wreckers_vs_unaffiliated",
        "debris_field_territory",
        "gray_market_provenance",
    }
)


# ---------------------------------------------------------------------------
# Module-scoped fixtures (load once, reuse across all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def raw_disputes() -> list[dict]:
    """Load reach_disputes.json raw so we can inspect JSON-level strings."""
    with open(REACH_DISPUTES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["disputes"]


@pytest.fixture(scope="module")
def commodity_ids() -> frozenset[str]:
    with open(COMMODITIES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return frozenset(c["id"] for c in data["commodities"])


@pytest.fixture(scope="module")
def system_ids() -> frozenset[str]:
    with open(SYSTEMS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return frozenset(s["id"] for s in data["systems"])


@pytest.fixture(scope="module")
def faction_ids() -> frozenset[str]:
    with open(FACTIONS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return frozenset(f["id"] for f in data["factions"])


@pytest.fixture(scope="module")
def loaded_templates():
    """Load templates via DataLoader so parse path is exercised."""
    loader = DataLoader()
    loader.load_all()
    return loader.politics_disputes


# ---------------------------------------------------------------------------
# AC 1: schema completeness — all required fields present and non-empty
# ---------------------------------------------------------------------------


class TestSchemaCompleteness:
    REQUIRED_FIELDS = [
        "id",
        "headline",
        "factions_affected",
        "base_difficulty",
        "round_count",
        "deadline_days",
        "is_campaign_arc",
        "issue_family",
        "delegates",
        "eligible_framings",
        "eligible_evidence",
        "framing_modifiers",
        "framing_target_dimensions",
        "counter_framings",
        "betrayal_conditions",
        "outcome_matrix",
    ]

    def test_five_templates(self, raw_disputes: list[dict]) -> None:
        assert len(raw_disputes) == 5, f"Expected 5 templates, got {len(raw_disputes)}"

    def test_all_required_fields_present(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for field in self.REQUIRED_FIELDS:
                assert field in tpl, f"Template '{tpl.get('id')}' missing field '{field}'"

    def test_no_tbd_values(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for k, v in tpl.items():
                assert v != "TBD", f"Template '{tpl['id']}' field '{k}' is TBD"

    def test_each_template_has_four_delegates(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            count = len(tpl["delegates"])
            assert count == 4, f"Template '{tpl['id']}' has {count} delegates, expected 4"

    def test_all_delegates_have_wreckers_guild_sub_faction(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for d in tpl["delegates"]:
                assert d.get("sub_faction_id") == "wreckers_guild", (
                    f"Delegate '{d['delegate_id']}' in '{tpl['id']}' "
                    f"has sub_faction_id '{d.get('sub_faction_id')}', expected 'wreckers_guild'"
                )

    def test_malia_torres_in_every_template(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            ids = [d["delegate_id"] for d in tpl["delegates"]]
            assert "malia_torres" in ids, f"Template '{tpl['id']}' missing malia_torres delegate"

    def test_templates_parse_via_data_loader(self, loaded_templates) -> None:
        assert len(loaded_templates) >= 5, "DataLoader did not load Reach templates"
        reach_ids = {
            "salvage_rights_phasing",
            "outsider_salvage_concession",
            "wrecker_loyalty_oath_dispute",
            "debris_field_territory_claim",
            "gray_market_goods_provenance",
        }
        loaded_ids = set(loaded_templates.keys())
        missing = reach_ids - loaded_ids
        assert not missing, f"Templates missing from DataLoader: {missing}"


# ---------------------------------------------------------------------------
# AC 2: issue-family categorization
# ---------------------------------------------------------------------------


class TestIssueFamilyCategorization:
    def test_two_salvage_rights_templates(self, raw_disputes: list[dict]) -> None:
        count = sum(1 for t in raw_disputes if t.get("issue_family") == "salvage_rights")
        assert count == 2, f"Expected 2 salvage_rights templates, got {count}"

    def test_one_wreckers_vs_unaffiliated(self, raw_disputes: list[dict]) -> None:
        count = sum(
            1 for t in raw_disputes if t.get("issue_family") == "wreckers_vs_unaffiliated"
        )
        assert count == 1, f"Expected 1 wreckers_vs_unaffiliated template, got {count}"

    def test_one_debris_field_territory(self, raw_disputes: list[dict]) -> None:
        count = sum(
            1 for t in raw_disputes if t.get("issue_family") == "debris_field_territory"
        )
        assert count == 1, f"Expected 1 debris_field_territory template, got {count}"

    def test_one_gray_market_provenance(self, raw_disputes: list[dict]) -> None:
        count = sum(
            1 for t in raw_disputes if t.get("issue_family") == "gray_market_provenance"
        )
        assert count == 1, f"Expected 1 gray_market_provenance template, got {count}"

    def test_all_issue_families_known(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            fam = tpl.get("issue_family")
            assert fam in ISSUE_FAMILIES, (
                f"Template '{tpl['id']}' has unknown issue_family '{fam}'"
            )


# ---------------------------------------------------------------------------
# AC 3: exactly one campaign-arc template
# ---------------------------------------------------------------------------


class TestCampaignArc:
    def test_exactly_one_campaign_arc(self, raw_disputes: list[dict]) -> None:
        arcs = [t for t in raw_disputes if t.get("is_campaign_arc") is True]
        assert len(arcs) == 1, f"Expected 1 campaign arc, got {len(arcs)}"

    def test_campaign_arc_is_debris_field(self, raw_disputes: list[dict]) -> None:
        arcs = [t for t in raw_disputes if t.get("is_campaign_arc") is True]
        assert arcs[0]["id"] == "debris_field_territory_claim"

    def test_campaign_arc_has_five_rounds(self, raw_disputes: list[dict]) -> None:
        arc = next(t for t in raw_disputes if t.get("is_campaign_arc") is True)
        assert arc["round_count"] == 5, f"Campaign arc has {arc['round_count']} rounds"


# ---------------------------------------------------------------------------
# AC 4: outcome matrix completeness
# ---------------------------------------------------------------------------


class TestOutcomeMatrix:
    CATEGORIES = {"win", "partial_win_coalition_thin", "partial_win_off_record", "loss"}

    def test_all_four_categories_present(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            matrix = tpl["outcome_matrix"]
            missing = self.CATEGORIES - set(matrix.keys())
            assert not missing, (
                f"Template '{tpl['id']}' outcome_matrix missing: {missing}"
            )

    def test_win_loss_have_non_null_headlines(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            win_headline = tpl["outcome_matrix"]["win"].get("news_headline")
            loss_headline = tpl["outcome_matrix"]["loss"].get("news_headline")
            assert win_headline is not None and win_headline != "", (
                f"Template '{tpl['id']}' win headline is null/empty"
            )
            assert loss_headline is not None and loss_headline != "", (
                f"Template '{tpl['id']}' loss headline is null/empty"
            )

    def test_win_loss_headlines_max_80_chars(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for cat in ("win", "loss"):
                hl = tpl["outcome_matrix"][cat].get("news_headline") or ""
                assert len(hl) <= 80, (
                    f"Template '{tpl['id']}' {cat} headline length {len(hl)} > 80: '{hl}'"
                )


# ---------------------------------------------------------------------------
# AC 5: flag-helper round-trips
# ---------------------------------------------------------------------------


class TestFlagHelperRoundTrips:
    def _collect_flag_strings(self, raw_disputes: list[dict]) -> list[tuple[str, str]]:
        """Return (template_id, flag_string) for all mission_unlocks/locks/required_flags."""
        result = []
        for tpl in raw_disputes:
            tid = tpl["id"]
            for cat in tpl["outcome_matrix"].values():
                for flag in cat.get("mission_unlocks", []):
                    result.append((tid, flag))
                for flag in cat.get("mission_locks", []):
                    result.append((tid, flag))
            for flag in tpl.get("required_flags", []):
                result.append((tid, flag))
        return result

    def test_flag_strings_round_trip_via_helpers(self, raw_disputes: list[dict]) -> None:
        flag_pairs = self._collect_flag_strings(raw_disputes)
        for tid, flag in flag_pairs:
            if flag.startswith("dispute_resolved_"):
                dispute_id = flag[len("dispute_resolved_") :]
                reconstructed = dispute_resolved(dispute_id)
            elif flag.startswith("coalition_won_"):
                dispute_id = flag[len("coalition_won_") :]
                reconstructed = coalition_won(dispute_id)
            elif flag.startswith("dispute_mediated_"):
                dispute_id = flag[len("dispute_mediated_") :]
                reconstructed = dispute_mediated(dispute_id)
            else:
                # Non-helper flags (e.g., required_flags from other disputes) are OK.
                continue
            assert reconstructed == flag, (
                f"Template '{tid}': flag '{flag}' != helper output '{reconstructed}'"
            )


# ---------------------------------------------------------------------------
# AC 6: cross-reference validity
# ---------------------------------------------------------------------------


class TestCrossReferences:
    def test_all_commodities_exist(
        self, raw_disputes: list[dict], commodity_ids: frozenset[str]
    ) -> None:
        for tpl in raw_disputes:
            for cat in tpl["outcome_matrix"].values():
                for shift in cat.get("market_shifts", []):
                    cid = shift["commodity_id"]
                    assert cid in commodity_ids, (
                        f"Template '{tpl['id']}': commodity '{cid}' not in commodities.json"
                    )

    def test_all_systems_exist(
        self, raw_disputes: list[dict], system_ids: frozenset[str]
    ) -> None:
        for tpl in raw_disputes:
            for cat in tpl["outcome_matrix"].values():
                for shift in cat.get("market_shifts", []):
                    sid = shift["system_id"]
                    assert sid in system_ids, (
                        f"Template '{tpl['id']}': system '{sid}' not in systems.json"
                    )

    def test_at_least_one_crimson_reach_market_shift(self, raw_disputes: list[dict]) -> None:
        reach_shifts = [
            (tpl["id"], cat_name, shift)
            for tpl in raw_disputes
            for cat_name, cat in tpl["outcome_matrix"].items()
            for shift in cat.get("market_shifts", [])
            if shift["system_id"] == "crimson_reach"
        ]
        assert reach_shifts, "No market shifts at crimson_reach system found across all templates"

    def test_all_factions_exist(
        self, raw_disputes: list[dict], faction_ids: frozenset[str]
    ) -> None:
        for tpl in raw_disputes:
            for cat in tpl["outcome_matrix"].values():
                for fid in cat.get("rep_deltas", {}).keys():
                    assert fid in faction_ids, (
                        f"Template '{tpl['id']}': faction '{fid}' not in factions.json"
                    )

    def test_win_loss_have_nonzero_crimson_reach_delta(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for cat in ("win", "loss"):
                row = tpl["outcome_matrix"].get(cat, {})
                delta = row.get("rep_deltas", {}).get("crimson_reach")
                assert delta is not None and delta != 0, (
                    f"Template '{tpl['id']}' {cat} has zero/null crimson_reach rep_delta"
                )

    def test_all_dimension_labels_are_reach_dimensions(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for d in tpl["delegates"]:
                for dim in d.get("position_vector", {}).keys():
                    assert dim in REACH_DIMENSIONS, (
                        f"Template '{tpl['id']}' delegate '{d['delegate_id']}' "
                        f"uses unknown dimension '{dim}'"
                    )

    def test_framing_target_dimensions_keys_in_framing_modifiers(
        self, raw_disputes: list[dict]
    ) -> None:
        for tpl in raw_disputes:
            modifiers = set(tpl.get("framing_modifiers", {}).keys())
            targets = set(tpl.get("framing_target_dimensions", {}).keys())
            extra = targets - modifiers
            assert not extra, (
                f"Template '{tpl['id']}' framing_target_dimensions keys not in "
                f"framing_modifiers: {extra}"
            )

    def test_framing_target_dimensions_values_are_reach_dimensions(
        self, raw_disputes: list[dict]
    ) -> None:
        for tpl in raw_disputes:
            for framing, dim in tpl.get("framing_target_dimensions", {}).items():
                assert dim in REACH_DIMENSIONS, (
                    f"Template '{tpl['id']}' framing '{framing}' targets "
                    f"unknown dimension '{dim}'"
                )

    def test_all_framings_in_eligible_framings(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            eligible = set(tpl.get("eligible_framings", []))
            for framing in tpl.get("framing_modifiers", {}).keys():
                assert framing in eligible, (
                    f"Template '{tpl['id']}' framing_modifier key '{framing}' "
                    f"not in eligible_framings"
                )

    def test_betrayal_conditions_use_valid_names(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            for d_id, condition in tpl.get("betrayal_conditions", {}).items():
                # Validate against the full condition string (may have colon-arg suffix).
                base = condition.split(":")[0]
                valid_bases = {"rep_dropped_below_25", "counter_framing_succeeded",
                               "rival_faction_unfavored"}
                assert base in valid_bases, (
                    f"Template '{tpl['id']}' delegate '{d_id}' has unknown "
                    f"betrayal condition '{condition}'"
                )

    def test_betrayal_condition_delegates_in_roster(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            roster = {d["delegate_id"] for d in tpl["delegates"]}
            for d_id in tpl.get("betrayal_conditions", {}).keys():
                assert d_id in roster, (
                    f"Template '{tpl['id']}' betrayal_condition key '{d_id}' "
                    f"not in delegate roster"
                )

    def test_counter_framing_delegates_in_roster(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            roster = {d["delegate_id"] for d in tpl["delegates"]}
            for d_id in tpl.get("counter_framings", {}).keys():
                assert d_id in roster, (
                    f"Template '{tpl['id']}' counter_framing key '{d_id}' "
                    f"not in delegate roster"
                )

    def test_counter_framings_values_in_eligible(self, raw_disputes: list[dict]) -> None:
        for tpl in raw_disputes:
            eligible = set(tpl.get("eligible_framings", []))
            for d_id, framings in tpl.get("counter_framings", {}).items():
                for framing in framings:
                    assert framing in eligible, (
                        f"Template '{tpl['id']}' delegate '{d_id}' counter_framing "
                        f"'{framing}' not in eligible_framings"
                    )
