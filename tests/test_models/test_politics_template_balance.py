"""SA-P6 — Template balance data-validation tests.

Parameterized across all 21 dispute templates. Catches out-of-range values
before they ship. Ranges are set to the max observed in shipped data plus a
small buffer; any value outside the range must be explicitly justified in
the tuning report.

Campaign arcs and the Annual Congress are exempt from standard-template
rep/duration caps — they have wider budgets by design. Specific exceptions
are called out in test docstrings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from spacegame.data_loader import DataLoader

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTCOME_CATEGORIES = ("win", "partial_win_coalition_thin", "partial_win_off_record", "loss")


def _load_templates() -> dict:
    loader = DataLoader(data_dir=PROJECT_ROOT / "data")
    return loader.load_politics_disputes()


# Load once at collection time so parametrize IDs resolve without a side-channel.
_TEMPLATES: dict = _load_templates()
TEMPLATE_IDS: list[str] = list(_TEMPLATES.keys())


@pytest.fixture(scope="module")
def all_templates() -> dict:
    return _TEMPLATES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _primary_faction(win_row) -> str | None:
    """Return the faction with the largest positive rep delta in the win row."""
    candidates = {f: v for f, v in win_row.rep_deltas.items() if v > 0}
    if not candidates:
        return None
    return max(candidates, key=lambda f: candidates[f])


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


class TestTemplateStructure:
    """Every template must be structurally complete."""

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_all_outcome_categories_present(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        missing = [c for c in OUTCOME_CATEGORIES if c not in tpl.outcome_matrix]
        assert not missing, f"{tid}: missing outcome categories {missing}"

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_delegate_count_in_range(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        n = len(tpl.delegates)
        assert 3 <= n <= 6, f"{tid}: delegate count {n} outside [3, 6]"

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_delegates_share_sub_faction(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        factions = {d.sub_faction_id for d in tpl.delegates}
        assert len(factions) == 1, (
            f"{tid}: delegates span multiple sub_factions {factions} — "
            "each venue template must use a single sub_faction_id"
        )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_round_count_valid(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        assert tpl.round_count in {3, 5}, (
            f"{tid}: round_count={tpl.round_count} is not 3 (standard) or 5 (arc)"
        )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_deadline_days_in_range(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        # Standard templates must resolve within one short session cycle.
        # Campaign arcs can have tight deadlines (pressure mechanic) or extended ones.
        if tpl.is_campaign_arc:
            lo, hi = 5, 35
        else:
            lo, hi = 5, 20
        assert lo <= tpl.deadline_days <= hi, (
            f"{tid}: deadline_days={tpl.deadline_days} outside [{lo}, {hi}] "
            f"(is_campaign_arc={tpl.is_campaign_arc})"
        )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_base_difficulty_in_range(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        assert 1 <= tpl.base_difficulty <= 7, (
            f"{tid}: base_difficulty={tpl.base_difficulty} outside [1, 7]"
        )


# ---------------------------------------------------------------------------
# Rep delta balance
# ---------------------------------------------------------------------------


class TestRepBalance:
    """Rep delta ordinal hierarchy and magnitude guardrails."""

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_win_row_has_positive_primary_rep(self, tid: str, all_templates: dict) -> None:
        tpl = all_templates[tid]
        win_row = tpl.outcome_matrix["win"]
        pos = {f: v for f, v in win_row.rep_deltas.items() if v > 0}
        assert pos, f"{tid}: win row must have at least one positive rep delta"

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_win_rep_abs_in_range(self, tid: str, all_templates: dict) -> None:
        """Win-row primary rep abs ≤ 6 for standard templates, ≤ 8 for arcs.

        Annual Congress win rep = 8 is the intentional high-water mark for
        a once-per-year campaign centrepiece. Anything above 8 is a data error.
        """
        tpl = all_templates[tid]
        win_row = tpl.outcome_matrix["win"]
        cap = 8 if tpl.is_campaign_arc else 6
        for faction, delta in win_row.rep_deltas.items():
            assert abs(delta) <= cap, (
                f"{tid}: win row rep_delta[{faction}]={delta} exceeds cap {cap}"
            )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_ordinal_rep_hierarchy(self, tid: str, all_templates: dict) -> None:
        """win ≥ partial_win_off_record ≥ partial_win_coalition_thin for primary faction."""
        tpl = all_templates[tid]
        primary = _primary_faction(tpl.outcome_matrix["win"])
        if primary is None:
            return  # No positive faction — skip ordinal check.
        win_v = tpl.outcome_matrix["win"].rep_deltas.get(primary, 0)
        pwr_v = tpl.outcome_matrix["partial_win_off_record"].rep_deltas.get(primary, 0)
        pwct_v = tpl.outcome_matrix["partial_win_coalition_thin"].rep_deltas.get(primary, 0)
        assert win_v >= pwr_v, (
            f"{tid}: win rep ({win_v}) < partial_win_off_record rep ({pwr_v}) for faction {primary}"
        )
        assert pwr_v >= pwct_v, (
            f"{tid}: partial_win_off_record rep ({pwr_v}) < partial_win_coalition_thin rep "
            f"({pwct_v}) for faction {primary}"
        )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_loss_row_negative_primary_rep(self, tid: str, all_templates: dict) -> None:
        """Primary faction rep must be negative in the loss row."""
        tpl = all_templates[tid]
        primary = _primary_faction(tpl.outcome_matrix["win"])
        if primary is None:
            return
        loss_v = tpl.outcome_matrix["loss"].rep_deltas.get(primary, 0)
        assert loss_v < 0, f"{tid}: loss row rep_delta[{primary}]={loss_v} must be negative"

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_loss_rep_abs_in_range(self, tid: str, all_templates: dict) -> None:
        """Loss penalty must not exceed 6 for any faction to avoid snowballing."""
        tpl = all_templates[tid]
        for faction, delta in tpl.outcome_matrix["loss"].rep_deltas.items():
            assert abs(delta) <= 6, f"{tid}: loss row rep_delta[{faction}]={delta} abs exceeds 6"


# ---------------------------------------------------------------------------
# Market shift balance
# ---------------------------------------------------------------------------


class TestMarketShiftBalance:
    """Market shift magnitude and duration guardrails."""

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_win_and_loss_rows_have_market_shifts(self, tid: str, all_templates: dict) -> None:
        """Win and loss rows must have at least one market shift each."""
        tpl = all_templates[tid]
        assert len(tpl.outcome_matrix["win"].market_shifts) >= 1, (
            f"{tid}: win row has no market shifts"
        )
        assert len(tpl.outcome_matrix["loss"].market_shifts) >= 1, (
            f"{tid}: loss row has no market shifts"
        )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_all_shift_durations_in_range(self, tid: str, all_templates: dict) -> None:
        """Market shift duration 14 ≤ d ≤ 42 for all categories.

        Annual Congress loss row has duration 35 and win row up to 40 — these
        are the approved maximums. A cap of 42 prevents future rounding errors
        from producing silent outliers.
        """
        tpl = all_templates[tid]
        for cat in OUTCOME_CATEGORIES:
            row = tpl.outcome_matrix[cat]
            for shift in row.market_shifts:
                assert 14 <= shift.duration_days <= 42, (
                    f"{tid} [{cat}]: shift duration={shift.duration_days} outside [14, 42]"
                )

    @pytest.mark.parametrize("tid", TEMPLATE_IDS)
    def test_all_shift_magnitudes_in_range(self, tid: str, all_templates: dict) -> None:
        """Shift magnitude abs ≤ 0.15 — beyond this commodities swing too hard."""
        tpl = all_templates[tid]
        for cat in OUTCOME_CATEGORIES:
            row = tpl.outcome_matrix[cat]
            for shift in row.market_shifts:
                assert abs(shift.magnitude) <= 0.15, (
                    f"{tid} [{cat}]: shift magnitude={shift.magnitude} abs exceeds 0.15"
                )


# ---------------------------------------------------------------------------
# Campaign arc invariants
# ---------------------------------------------------------------------------


class TestCampaignArcInvariants:
    """Campaign-arc-specific structural and balance rules."""

    def test_all_campaign_arcs_have_round_count_5(self, all_templates: dict) -> None:
        arcs = {tid: t for tid, t in all_templates.items() if t.is_campaign_arc}
        assert arcs, "Expected at least one campaign arc"
        wrong = {tid: t.round_count for tid, t in arcs.items() if t.round_count != 5}
        assert not wrong, f"Campaign arcs with round_count != 5: {wrong}"

    def test_standard_templates_have_round_count_3(self, all_templates: dict) -> None:
        standard = {tid: t for tid, t in all_templates.items() if not t.is_campaign_arc}
        wrong = {tid: t.round_count for tid, t in standard.items() if t.round_count != 3}
        assert not wrong, f"Standard templates with round_count != 3: {wrong}"

    def test_campaign_arc_count_per_venue(self, all_templates: dict) -> None:
        """Each venue (sub_faction_id group) should have at least one campaign arc."""
        venue_arcs: dict[str, list[str]] = {}
        for tid, t in all_templates.items():
            if t.is_campaign_arc and t.delegates:
                venue = t.delegates[0].sub_faction_id
                venue_arcs.setdefault(venue, []).append(tid)
        assert len(venue_arcs) >= 3, (
            f"Expected arcs across ≥3 venues, found only: {list(venue_arcs.keys())}"
        )

    def test_annual_congress_exists_and_is_flagged(self, all_templates: dict) -> None:
        assert "annual_alliance_congress" in all_templates, (
            "annual_alliance_congress template must exist"
        )
        tpl = all_templates["annual_alliance_congress"]
        assert tpl.is_annual_congress is True, (
            "annual_alliance_congress must be flagged is_annual_congress=True"
        )
        assert tpl.is_campaign_arc is True, (
            "annual_alliance_congress must also be flagged is_campaign_arc=True"
        )

    def test_annual_congress_deadline_28(self, all_templates: dict) -> None:
        """Annual Congress has a 28-day window — intentional, locked in spec."""
        tpl = all_templates["annual_alliance_congress"]
        assert tpl.deadline_days == 28, (
            f"Annual Congress deadline_days={tpl.deadline_days}, expected 28"
        )

    def test_annual_congress_win_rep_8(self, all_templates: dict) -> None:
        """Annual Congress win rep = 8 — intentional high-water mark for annual centrepiece."""
        tpl = all_templates["annual_alliance_congress"]
        win_reps = tpl.outcome_matrix["win"].rep_deltas
        primary = _primary_faction(tpl.outcome_matrix["win"])
        assert primary is not None
        assert win_reps[primary] == 8, (
            f"Annual Congress win rep for {primary}={win_reps[primary]}, expected 8"
        )

    def test_debris_field_campaign_arc_flagged(self, all_templates: dict) -> None:
        """debris_field_territory_claim is the Reach campaign arc."""
        assert "debris_field_territory_claim" in all_templates
        tpl = all_templates["debris_field_territory_claim"]
        assert tpl.is_campaign_arc is True
        assert tpl.round_count == 5
