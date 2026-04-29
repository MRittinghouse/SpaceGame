"""SA-R3: Data-validation tests for the 10 Okafor Institute project templates.

Enforces locked numeric ranges and structural constraints across all templates
so future additions automatically inherit the validation (AC #3). The test is
fast — it inspects module-level template data with no resolution simulation.

Note on outcome_unlock_id: these are SA-R1 stub IDs (e.g., "advanced_sensor_array",
"efficient_thrusters") that map to planned future content not yet present in the
data files. The data-existence check is intentionally skipped here and documented
in ``requirements/sa_research_tuning_report.md`` (skip list, item 6). The unlock
type is validated as a legal token only.
"""

from __future__ import annotations

import pytest

from spacegame.models.okafor_research import (
    FAILURE_ODDS,
    OKAFOR_PROJECT_ETHICS,
    OKAFOR_PROJECT_TEMPLATES,
    OkaforProjectTemplate,
)

# ---------------------------------------------------------------------------
# Locked numeric ranges per SA-R1 plan (Decision 2 in SA-R3: audit-only)
# ---------------------------------------------------------------------------

COST_RANGE: dict[str, tuple[int, int]] = {
    "low": (5_000, 15_000),
    "mid": (20_000, 35_000),
    "high": (70_000, 125_000),
}

DURATION_RANGE: dict[str, tuple[int, int]] = {
    "low": (4, 10),
    "mid": (10, 16),
    "high": (20, 30),
}

PAYOUT_MIN_RATIO = 1.5
PAYOUT_MAX_RATIO = 4.5

LEGAL_FACTIONS = {"science_collective", "frontier_alliance", "miners_union"}
LEGAL_RISK_TIERS = {"low", "mid", "high"}
LEGAL_UNLOCK_TYPES = {"", "module", "upgrade", "commodity"}
LEGAL_ETHICS_TAGS = {"heal", "profit", "neutral"}

EXPECTED_TIER_TALLY = {"low": 4, "mid": 4, "high": 2}
EXPECTED_ETHICS_TALLY = {"heal": 3, "profit": 4, "neutral": 3}


# ---------------------------------------------------------------------------
# Parametric fixture
# ---------------------------------------------------------------------------


@pytest.fixture(params=list(OKAFOR_PROJECT_TEMPLATES), ids=lambda t: t.id)
def template(request: pytest.FixtureRequest) -> OkaforProjectTemplate:
    """Parametric fixture over all 10 project templates."""
    return request.param  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Per-template assertions
# ---------------------------------------------------------------------------


class TestEachTemplate:
    """Per-template structural + numeric assertions."""

    def test_risk_tier_is_legal(self, template: OkaforProjectTemplate) -> None:
        assert template.risk_tier in LEGAL_RISK_TIERS, (
            f"{template.id}: risk_tier {template.risk_tier!r} not in {LEGAL_RISK_TIERS}"
        )

    def test_base_cost_in_locked_range(self, template: OkaforProjectTemplate) -> None:
        lo, hi = COST_RANGE[template.risk_tier]
        assert lo <= template.base_cost_credits <= hi, (
            f"{template.id}: base_cost_credits {template.base_cost_credits} "
            f"outside [{lo}, {hi}] for tier {template.risk_tier!r}"
        )

    def test_base_duration_in_locked_range(self, template: OkaforProjectTemplate) -> None:
        lo, hi = DURATION_RANGE[template.risk_tier]
        assert lo <= template.base_duration_days <= hi, (
            f"{template.id}: base_duration_days {template.base_duration_days} "
            f"outside [{lo}, {hi}] for tier {template.risk_tier!r}"
        )

    def test_failure_odds_match_tier(self, template: OkaforProjectTemplate) -> None:
        expected = FAILURE_ODDS[template.risk_tier]
        assert template.base_failure_odds == expected, (
            f"{template.id}: base_failure_odds {template.base_failure_odds} "
            f"!= FAILURE_ODDS[{template.risk_tier!r}] = {expected}"
        )

    def test_payout_exceeds_min_ratio(self, template: OkaforProjectTemplate) -> None:
        floor = template.base_cost_credits * PAYOUT_MIN_RATIO
        assert template.base_success_payout > floor, (
            f"{template.id}: base_success_payout {template.base_success_payout} "
            f"<= floor {floor:.0f} (must be > {PAYOUT_MIN_RATIO}x cost)"
        )

    def test_payout_below_max_ratio(self, template: OkaforProjectTemplate) -> None:
        ceiling = template.base_cost_credits * PAYOUT_MAX_RATIO
        assert template.base_success_payout < ceiling, (
            f"{template.id}: base_success_payout {template.base_success_payout} "
            f">= ceiling {ceiling:.0f} (must be < {PAYOUT_MAX_RATIO}x cost)"
        )

    def test_faction_is_legal(self, template: OkaforProjectTemplate) -> None:
        assert template.faction in LEGAL_FACTIONS, (
            f"{template.id}: faction {template.faction!r} not in {LEGAL_FACTIONS}"
        )

    def test_outcome_unlock_type_is_legal(self, template: OkaforProjectTemplate) -> None:
        assert template.outcome_unlock_type in LEGAL_UNLOCK_TYPES, (
            f"{template.id}: outcome_unlock_type {template.outcome_unlock_type!r} "
            f"not in {LEGAL_UNLOCK_TYPES}"
        )

    def test_outcome_unlock_id_present_when_type_set(
        self, template: OkaforProjectTemplate
    ) -> None:
        if template.outcome_unlock_type:
            assert template.outcome_unlock_id, (
                f"{template.id}: outcome_unlock_type is set but outcome_unlock_id is empty"
            )
        else:
            assert not template.outcome_unlock_id, (
                f"{template.id}: outcome_unlock_id is set but outcome_unlock_type is empty"
            )

    def test_briefing_nonempty(self, template: OkaforProjectTemplate) -> None:
        assert template.briefing.strip(), f"{template.id}: briefing must not be empty"

    def test_success_debrief_nonempty(self, template: OkaforProjectTemplate) -> None:
        assert template.success_debrief.strip(), (
            f"{template.id}: success_debrief must not be empty"
        )

    def test_failure_debrief_nonempty(self, template: OkaforProjectTemplate) -> None:
        assert template.failure_debrief.strip(), (
            f"{template.id}: failure_debrief must not be empty"
        )


# ---------------------------------------------------------------------------
# Global (non-parametric) aggregate assertions
# ---------------------------------------------------------------------------


class TestTemplateTotals:
    """Aggregate constraints across all 10 templates."""

    def test_exactly_ten_templates(self) -> None:
        assert len(OKAFOR_PROJECT_TEMPLATES) == 10, (
            f"Expected 10 templates, got {len(OKAFOR_PROJECT_TEMPLATES)}"
        )

    def test_tier_tally_is_4_4_2(self) -> None:
        counts: dict[str, int] = {t: 0 for t in LEGAL_RISK_TIERS}
        for tpl in OKAFOR_PROJECT_TEMPLATES:
            counts[tpl.risk_tier] += 1
        assert counts == EXPECTED_TIER_TALLY, (
            f"Tier tally must be {EXPECTED_TIER_TALLY}, got {counts}"
        )

    def test_template_ids_are_unique(self) -> None:
        ids = [tpl.id for tpl in OKAFOR_PROJECT_TEMPLATES]
        assert len(ids) == len(set(ids)), "All template ids must be unique"

    def test_ethics_keyset_matches_template_keyset(self) -> None:
        template_ids = {tpl.id for tpl in OKAFOR_PROJECT_TEMPLATES}
        ethics_ids = set(OKAFOR_PROJECT_ETHICS.keys())
        assert ethics_ids == template_ids, (
            f"Ethics keyset mismatch.\n"
            f"Extra in ethics: {ethics_ids - template_ids}\n"
            f"Missing from ethics: {template_ids - ethics_ids}"
        )

    def test_ethics_tally_is_3_heal_4_profit_3_neutral(self) -> None:
        counts: dict[str, int] = {t: 0 for t in LEGAL_ETHICS_TAGS}
        for tag in OKAFOR_PROJECT_ETHICS.values():
            counts[tag] += 1
        assert counts == EXPECTED_ETHICS_TALLY, (
            f"Ethics tally must be {EXPECTED_ETHICS_TALLY}, got {counts}"
        )

    def test_ethics_values_are_legal(self) -> None:
        for tid, tag in OKAFOR_PROJECT_ETHICS.items():
            assert tag in LEGAL_ETHICS_TAGS, (
                f"{tid}: ethics tag {tag!r} not in {LEGAL_ETHICS_TAGS}"
            )
