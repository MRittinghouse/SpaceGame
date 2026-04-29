"""SA-R1: Tests for the Okafor Institute research-patronage model.

Covers project templates, deterministic offer rolls on a 30-day window,
fund-flow math (solo + team-fund collaborators), tick-flow with the
seeded RNG resolution, success-payout scaling with research_yield_bonus,
failure refunds with research_risk_reduction, the patent state machine
(held → licensed → tick royalties; held → sold → holding removed),
and round-trip serialization.
"""

from __future__ import annotations

import pytest

from spacegame.models.okafor_research import (
    FAILURE_ODDS,
    FAILURE_REFUND_RATE,
    OKAFOR_PROJECT_TEMPLATES,
    ROYALTY_INTERVAL_DAYS,
    ROYALTY_RATE,
    SELL_LUMP_SUM_RATE,
    SLOT_OFFER_MAX,
    SLOT_OFFER_MIN,
    SLOT_REFRESH_WINDOW_DAYS,
    TEAM_FUND_MAX_COLLABORATORS,
    ActiveProject,
    OkaforProjectTemplate,
    OkaforResearchState,
    PatentHolding,
    compute_team_fund_cost,
    compute_team_fund_duration,
    fund_project,
    get_template,
    resolve_completion,
    roll_offers,
    seed_for_window,
    tick_royalties,
    transition_patent_to_licensed,
    transition_patent_to_sold,
)


class TestProjectTemplates:
    """Module-level template registry contract."""

    def test_ten_templates_authored(self) -> None:
        assert len(OKAFOR_PROJECT_TEMPLATES) == 10, "Sprint locks 10 templates"

    def test_templates_split_4_low_4_mid_2_high(self) -> None:
        counts = {"low": 0, "mid": 0, "high": 0}
        for tpl in OKAFOR_PROJECT_TEMPLATES:
            counts[tpl.risk_tier] += 1
        assert counts == {"low": 4, "mid": 4, "high": 2}, (
            f"Risk-tier distribution must be 4/4/2, got {counts}"
        )

    def test_templates_have_unique_ids(self) -> None:
        ids = [tpl.id for tpl in OKAFOR_PROJECT_TEMPLATES]
        assert len(ids) == len(set(ids)), "Template ids must be unique"

    def test_templates_use_correct_failure_odds_per_tier(self) -> None:
        for tpl in OKAFOR_PROJECT_TEMPLATES:
            assert tpl.base_failure_odds == FAILURE_ODDS[tpl.risk_tier], (
                f"{tpl.id}: base_failure_odds must match the tier's locked value"
            )

    def test_template_factions_include_three_required(self) -> None:
        factions = {tpl.faction for tpl in OKAFOR_PROJECT_TEMPLATES}
        assert "frontier_alliance" in factions, "Plan requires one Frontier Alliance medical-aid"
        assert "miners_union" in factions, "Plan requires one Miners' Union industrial-medicine"
        assert "science_collective" in factions, "Plan requires Collective core projects"

    def test_get_template_returns_known(self) -> None:
        tpl = get_template(OKAFOR_PROJECT_TEMPLATES[0].id)
        assert tpl is not None
        assert tpl.id == OKAFOR_PROJECT_TEMPLATES[0].id

    def test_get_template_returns_none_for_unknown(self) -> None:
        assert get_template("nonexistent_template") is None

    def test_template_is_frozen(self) -> None:
        tpl = OKAFOR_PROJECT_TEMPLATES[0]
        with pytest.raises(Exception):
            tpl.id = "mutated"  # type: ignore[misc]


class TestRollOffers:
    """Acceptance #3 — deterministic 5-7 offer rolls per 30-day window."""

    def test_seed_for_window_30_day_buckets(self) -> None:
        assert seed_for_window(0) == 0
        assert seed_for_window(SLOT_REFRESH_WINDOW_DAYS - 1) == 0
        assert seed_for_window(SLOT_REFRESH_WINDOW_DAYS) == 1
        assert seed_for_window(SLOT_REFRESH_WINDOW_DAYS * 2) == 2

    def test_offer_count_within_bounds(self) -> None:
        offers = roll_offers("test_player", 1)
        assert SLOT_OFFER_MIN <= len(offers) <= SLOT_OFFER_MAX

    def test_same_window_returns_same_offers(self) -> None:
        offers_a = roll_offers("captain_navi", 5)
        offers_b = roll_offers("captain_navi", SLOT_REFRESH_WINDOW_DAYS - 1)
        assert offers_a == offers_b, "Offers within one 30-day window must be identical"

    def test_window_rollover_produces_fresh_roll(self) -> None:
        offers_a = roll_offers("captain_navi", 5)
        offers_b = roll_offers("captain_navi", SLOT_REFRESH_WINDOW_DAYS + 5)
        assert offers_a != offers_b, "Crossing the 30-day window must reroll"

    def test_offers_are_real_template_ids(self) -> None:
        offers = roll_offers("captain_navi", 0)
        for offer_id in offers:
            assert get_template(offer_id) is not None

    def test_different_player_seeds_diverge(self) -> None:
        offers_a = roll_offers("alice", 0)
        offers_b = roll_offers("bob", 0)
        # Different seeds must produce different offers most of the time.
        assert offers_a != offers_b


class TestTeamFundMath:
    """Acceptance #6 — solo / team-1 / team-2 cost & duration math."""

    def test_solo_fund_unchanged(self) -> None:
        assert compute_team_fund_cost(50_000, 0) == 50_000
        assert compute_team_fund_duration(15, 0) == 15

    def test_one_collaborator_50_pct_more_cost_70_pct_duration(self) -> None:
        # 50,000 * 1.5 = 75,000; 15 * 0.7 = 10.5 → 11 (ceil).
        assert compute_team_fund_cost(50_000, 1) == 75_000
        assert compute_team_fund_duration(15, 1) == 11

    def test_two_collaborators_2x_cost_50_pct_duration(self) -> None:
        # 50,000 * 2.0 = 100,000; 15 * 0.5 = 7.5 → 8 (ceil).
        assert compute_team_fund_cost(50_000, 2) == 100_000
        assert compute_team_fund_duration(15, 2) == 8

    def test_collaborator_count_capped_at_two(self) -> None:
        assert TEAM_FUND_MAX_COLLABORATORS == 2

    def test_duration_minimum_one_day(self) -> None:
        # Even with full team-fund, duration cannot drop below 1 day.
        assert compute_team_fund_duration(1, 2) >= 1


class TestFundProject:
    """Acceptance #4 — funding deducts credits and inserts ActiveProject."""

    def _low_risk_template(self) -> OkaforProjectTemplate:
        for tpl in OKAFOR_PROJECT_TEMPLATES:
            if tpl.risk_tier == "low":
                return tpl
        pytest.fail("No low-risk template authored")
        raise AssertionError  # unreachable

    def test_fund_inserts_into_active_projects(self) -> None:
        state = OkaforResearchState()
        tpl = self._low_risk_template()
        active = fund_project(state, tpl, accept_day=10, collaborators=[])
        assert tpl.id in state.active_projects
        assert state.active_projects[tpl.id] is active

    def test_fund_records_collaborator_count_in_cost(self) -> None:
        state = OkaforResearchState()
        tpl = self._low_risk_template()
        active = fund_project(state, tpl, accept_day=10, collaborators=["nuri_solberg"])
        assert active.cost_paid == compute_team_fund_cost(tpl.base_cost_credits, 1)

    def test_fund_records_collaborator_count_in_duration(self) -> None:
        state = OkaforResearchState()
        tpl = self._low_risk_template()
        active = fund_project(state, tpl, accept_day=10, collaborators=["nuri_solberg", "theo_brandt"])
        assert active.duration_days == compute_team_fund_duration(tpl.base_duration_days, 2)


class TestResolveCompletion:
    """Acceptance #5, #7, #9 — deterministic resolution + bonus stacking + refund."""

    def _mid_risk_template(self) -> OkaforProjectTemplate:
        for tpl in OKAFOR_PROJECT_TEMPLATES:
            if tpl.risk_tier == "mid":
                return tpl
        pytest.fail("No mid-risk template authored")
        raise AssertionError

    def test_resolution_is_deterministic_for_same_inputs(self) -> None:
        tpl = self._mid_risk_template()
        active = ActiveProject(
            template_id=tpl.id, accept_day=42, duration_days=15, cost_paid=50_000, collaborators=[]
        )
        result_a = resolve_completion(tpl, active, "captain_navi", 0.0, 0.0)
        result_b = resolve_completion(tpl, active, "captain_navi", 0.0, 0.0)
        assert result_a == result_b, "Same seed inputs must produce identical resolution"

    def test_resolution_changes_with_accept_day(self) -> None:
        tpl = self._mid_risk_template()
        outcomes = set()
        for accept_day in range(1, 80):
            active = ActiveProject(
                template_id=tpl.id, accept_day=accept_day, duration_days=15, cost_paid=50_000,
                collaborators=[],
            )
            success, _ = resolve_completion(tpl, active, "captain_navi", 0.0, 0.0)
            outcomes.add(success)
        assert outcomes == {True, False}, "RNG must produce both outcomes across many accept_days"

    def test_success_payout_scales_with_yield_bonus(self) -> None:
        tpl = self._mid_risk_template()
        active = ActiveProject(
            template_id=tpl.id, accept_day=42, duration_days=15, cost_paid=tpl.base_cost_credits,
            collaborators=[],
        )
        # Probe many seeds to find a success path with bonus = 0.
        success_seed = None
        for candidate in range(0, 200):
            success, payout = resolve_completion(
                tpl,
                ActiveProject(template_id=tpl.id, accept_day=candidate, duration_days=15,
                              cost_paid=tpl.base_cost_credits, collaborators=[]),
                "captain_navi",
                0.0,
                0.0,
            )
            if success:
                success_seed = candidate
                break
        assert success_seed is not None, "Must find at least one success in 200 trials"
        active_for_success = ActiveProject(
            template_id=tpl.id, accept_day=success_seed, duration_days=15,
            cost_paid=tpl.base_cost_credits, collaborators=[],
        )
        _, baseline_payout = resolve_completion(tpl, active_for_success, "captain_navi", 0.0, 0.0)
        _, boosted_payout = resolve_completion(tpl, active_for_success, "captain_navi", 0.20, 0.0)
        assert boosted_payout == int(tpl.base_success_payout * 1.20)
        assert baseline_payout == tpl.base_success_payout

    def test_failure_refunds_30_percent_of_capital(self) -> None:
        tpl = self._mid_risk_template()
        # Force a failure: high risk_reduction subtracted from base via negative cap.
        # Use base_failure_odds tier high to find a failure.
        for candidate in range(0, 200):
            active = ActiveProject(
                template_id=tpl.id, accept_day=candidate, duration_days=15, cost_paid=50_000,
                collaborators=[],
            )
            success, payout = resolve_completion(tpl, active, "captain_navi", 0.0, 0.0)
            if not success:
                assert payout == int(50_000 * FAILURE_REFUND_RATE), (
                    "Failure must refund exactly 30% of cost_paid"
                )
                return
        pytest.fail("No failure path found in 200 trials at mid-risk")

    def test_risk_reduction_can_zero_out_failure_odds(self) -> None:
        # With risk_reduction >= base_failure_odds, every roll succeeds.
        for tpl in OKAFOR_PROJECT_TEMPLATES:
            if tpl.risk_tier != "mid":
                continue
            for accept_day in range(1, 60):
                active = ActiveProject(
                    template_id=tpl.id, accept_day=accept_day, duration_days=15,
                    cost_paid=tpl.base_cost_credits, collaborators=[],
                )
                success, _ = resolve_completion(
                    tpl, active, "captain_navi", 0.0, tpl.base_failure_odds + 0.5,
                )
                assert success, f"Risk reduction over the threshold must guarantee success"
            return

    def test_skill_and_crew_stack_to_full_bonus(self) -> None:
        """Acceptance #7 — totals when crew + skills both at +0.10 each = +0.20."""
        # The model resolves payouts and refunds using totals computed by the caller.
        # Verify that when totals are 0.20 / 0.20, results behave correctly.
        tpl = self._mid_risk_template()
        for candidate in range(0, 200):
            active = ActiveProject(
                template_id=tpl.id, accept_day=candidate, duration_days=15,
                cost_paid=tpl.base_cost_credits, collaborators=[],
            )
            success, payout = resolve_completion(tpl, active, "navi", 0.20, 0.20)
            if success:
                assert payout == int(tpl.base_success_payout * 1.20)
                return
        pytest.fail("Expected at least one success at +0.20 risk reduction")


class TestPatentStateMachine:
    """Acceptance #8 — held → licensed (royalties) → sold."""

    def test_holding_starts_held(self) -> None:
        h = PatentHolding(holding_id="x", template_id="t", state="held", success_payout=100_000)
        assert h.state == "held"

    def test_transition_to_licensed_sets_schedule(self) -> None:
        h = PatentHolding(holding_id="x", template_id="t", state="held", success_payout=100_000)
        transition_patent_to_licensed(h, current_day=50)
        assert h.state == "licensed"
        assert h.license_start_day == 50
        assert h.next_royalty_day == 50 + ROYALTY_INTERVAL_DAYS

    def test_transition_to_sold_returns_lump_sum(self) -> None:
        h = PatentHolding(holding_id="x", template_id="t", state="held", success_payout=100_000)
        lump = transition_patent_to_sold(h)
        assert h.state == "sold"
        assert lump == int(100_000 * SELL_LUMP_SUM_RATE)

    def test_tick_royalties_pays_per_interval(self) -> None:
        state = OkaforResearchState()
        h = PatentHolding(
            holding_id="x", template_id="t", state="licensed",
            success_payout=100_000, license_start_day=0,
            next_royalty_day=ROYALTY_INTERVAL_DAYS,
        )
        state.holdings.append(h)
        # Tick to day 10 → one payout
        total = tick_royalties(state, current_day=ROYALTY_INTERVAL_DAYS)
        assert total == int(100_000 * ROYALTY_RATE)
        assert h.next_royalty_day == ROYALTY_INTERVAL_DAYS * 2

    def test_tick_royalties_can_pay_multiple_intervals(self) -> None:
        state = OkaforResearchState()
        h = PatentHolding(
            holding_id="x", template_id="t", state="licensed",
            success_payout=100_000, license_start_day=0,
            next_royalty_day=ROYALTY_INTERVAL_DAYS,
        )
        state.holdings.append(h)
        # Jump 30 days → 3 payouts (days 10, 20, 30).
        total = tick_royalties(state, current_day=ROYALTY_INTERVAL_DAYS * 3)
        assert total == int(100_000 * ROYALTY_RATE) * 3
        assert h.next_royalty_day == ROYALTY_INTERVAL_DAYS * 4

    def test_tick_royalties_skips_held_and_sold(self) -> None:
        state = OkaforResearchState()
        held = PatentHolding(holding_id="a", template_id="t1", state="held", success_payout=100_000)
        sold = PatentHolding(holding_id="b", template_id="t2", state="sold", success_payout=100_000)
        state.holdings.append(held)
        state.holdings.append(sold)
        total = tick_royalties(state, current_day=100)
        assert total == 0


class TestSerialization:
    """Acceptance #10 — to_dict / from_dict round-trip; legacy saves load as None."""

    def test_active_project_round_trip(self) -> None:
        active = ActiveProject(
            template_id="x", accept_day=10, duration_days=15, cost_paid=50_000,
            collaborators=["nuri_solberg"],
        )
        restored = ActiveProject.from_dict(active.to_dict())
        assert restored == active

    def test_patent_holding_round_trip(self) -> None:
        h = PatentHolding(
            holding_id="x_10", template_id="x", state="licensed",
            success_payout=120_000, license_start_day=50, next_royalty_day=60,
        )
        restored = PatentHolding.from_dict(h.to_dict())
        assert restored == h

    def test_state_round_trip_with_full_content(self) -> None:
        state = OkaforResearchState(
            active_projects={
                "mid_a": ActiveProject(
                    template_id="mid_a", accept_day=10, duration_days=15,
                    cost_paid=50_000, collaborators=["nuri_solberg"],
                ),
                "high_b": ActiveProject(
                    template_id="high_b", accept_day=20, duration_days=25,
                    cost_paid=100_000, collaborators=[],
                ),
            },
            holdings=[
                PatentHolding(
                    holding_id="held_1", template_id="x", state="held",
                    success_payout=100_000,
                ),
                PatentHolding(
                    holding_id="lic_1", template_id="y", state="licensed",
                    success_payout=200_000, license_start_day=15, next_royalty_day=25,
                ),
            ],
            kweon_relationship_value=3,
            slot_seed_window=2,
            slot_offers=["mid_a", "high_b"],
            completed_count=4,
            failed_count=1,
        )
        restored = OkaforResearchState.from_dict(state.to_dict())
        assert restored == state

    def test_legacy_save_with_missing_keys_loads(self) -> None:
        # Empty dict simulates a partial / legacy save shape.
        state = OkaforResearchState.from_dict({})
        assert state.active_projects == {}
        assert state.holdings == []
        assert state.kweon_relationship_value == 0
        assert state.slot_seed_window == -1


class TestKweonRelationshipValue:
    """Locked decision: relationship arc, not sub-rep tier (range 0-10)."""

    def test_relationship_starts_at_zero(self) -> None:
        state = OkaforResearchState()
        assert state.kweon_relationship_value == 0

    def test_relationship_clamps_to_max(self) -> None:
        state = OkaforResearchState(kweon_relationship_value=99)
        state.bump_relationship(5)
        assert state.kweon_relationship_value == 10

    def test_relationship_clamps_to_min(self) -> None:
        state = OkaforResearchState(kweon_relationship_value=1)
        state.bump_relationship(-99)
        assert state.kweon_relationship_value == 0

    def test_relationship_increments_on_success(self) -> None:
        state = OkaforResearchState(kweon_relationship_value=2)
        state.bump_relationship(1)
        assert state.kweon_relationship_value == 3
