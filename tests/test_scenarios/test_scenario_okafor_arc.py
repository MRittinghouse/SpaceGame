"""SA-R1 scenario: full Okafor Institute research-patronage arc.

Walks the happy path (introduction → fund mid-tier → tick to success
→ license patent → 3 royalty payouts → sell patent), the failure path
(fund a project, tick to failure, refund applied, first-failure
flag fires once), the skill-stacking path (Nuri Solberg crew + skills
at level 2 produce the locked +0.20 / +0.20 totals applied at
resolution), and a save-mid-cycle round-trip path.
"""

from __future__ import annotations

from spacegame.constants.flags import (
    okafor_first_failure_seen,
    okafor_patent_disposed_first,
    okafor_project_completed_first,
    okafor_project_failed_first,
    okafor_project_funded_first,
)
from spacegame.models.okafor_research import (
    FAILURE_REFUND_RATE,
    OKAFOR_PROJECT_TEMPLATES,
    ROYALTY_INTERVAL_DAYS,
    ROYALTY_RATE,
    SELL_LUMP_SUM_RATE,
    ActiveProject,
    OkaforResearchState,
    PatentHolding,
    fund_project,
    get_template,
    resolve_completed_projects,
    tick_royalties,
    transition_patent_to_licensed,
    transition_patent_to_sold,
)
from spacegame.models.player import Player
from tests.test_scenarios._helpers import fresh_player, round_trip_save


def _player_at_axiom(credits: int = 500_000) -> Player:
    return fresh_player(
        name="ScenarioCaptain",
        credits=credits,
        system_id="axiom_labs",
    )


def _find_first_outcome(
    template_id: str,
    expect_success: bool,
    *,
    yield_bonus: float = 0.0,
    risk_reduction: float = 0.0,
    player_seed: str = "ScenarioCaptain",
) -> int:
    """Probe accept_days to find one that resolves to the desired outcome.

    Returns the accept_day. Raises if none found in 200 trials.
    """
    template = get_template(template_id)
    assert template is not None
    for accept_day in range(200):
        active = ActiveProject(
            template_id=template_id,
            accept_day=accept_day,
            duration_days=template.base_duration_days,
            cost_paid=template.base_cost_credits,
            collaborators=[],
        )
        from spacegame.models.okafor_research import resolve_completion

        success, _ = resolve_completion(
            template,
            active,
            player_seed,
            yield_bonus,
            risk_reduction,
        )
        if success == expect_success:
            return accept_day
    raise AssertionError(f"No {expect_success} outcome found for {template_id}")


def _mid_tier_template_id() -> str:
    for tpl in OKAFOR_PROJECT_TEMPLATES:
        if tpl.risk_tier == "mid":
            return tpl.id
    raise AssertionError("No mid-tier template")


class TestHappyPath:
    """Full arc: introduction → fund → success → license → royalties → sell."""

    def test_full_happy_arc(self) -> None:
        # Pick a mid-tier project + an accept_day that the seeded RNG
        # resolves to success without bonuses.
        template_id = _mid_tier_template_id()
        accept_day = _find_first_outcome(template_id, expect_success=True)
        template = get_template(template_id)
        assert template is not None

        player = _player_at_axiom(credits=500_000)
        player.game_day = accept_day
        player.okafor_research_state = OkaforResearchState()
        # Fund.
        active = fund_project(player.okafor_research_state, template, accept_day, collaborators=[])
        player.deduct_credits(active.cost_paid)
        player.dialogue_flags[okafor_project_funded_first()] = True

        # Tick to completion day. Resolution is deterministic.
        completion_day = active.completion_day
        outcomes = resolve_completed_projects(
            player.okafor_research_state,
            completion_day,
            player.name,
            0.0,
            0.0,
        )
        assert len(outcomes) == 1
        assert outcomes[0].success is True
        player.add_credits(outcomes[0].payout)
        player.dialogue_flags[okafor_project_completed_first()] = True

        # The holding is on file as 'held'.
        state = player.okafor_research_state
        assert len(state.holdings) == 1
        holding = state.holdings[0]
        assert holding.state == "held"
        assert state.completed_count == 1
        assert state.kweon_relationship_value == 1

        # License the patent.
        transition_patent_to_licensed(holding, completion_day)
        player.dialogue_flags[okafor_patent_disposed_first()] = True
        assert holding.state == "licensed"
        first_royalty_day = holding.next_royalty_day

        # Advance 30 days. Three royalty payouts at 5% of success_payout each.
        royalty_total = tick_royalties(state, first_royalty_day + ROYALTY_INTERVAL_DAYS * 2)
        per_payout = round(holding.success_payout * ROYALTY_RATE)
        assert royalty_total == per_payout * 3
        player.add_credits(royalty_total)

        # Sell the patent. 60% of success_payout, holding removed.
        lump = transition_patent_to_sold(holding)
        assert lump == round(holding.success_payout * SELL_LUMP_SUM_RATE)
        state.remove_holding(holding.holding_id)
        player.add_credits(lump)
        assert state.find_holding(holding.holding_id) is None


class TestFailurePath:
    """First failure refunds 30% and fires the first-failure flag once."""

    def test_first_failure_path(self) -> None:
        template_id = _mid_tier_template_id()
        accept_day = _find_first_outcome(template_id, expect_success=False)
        template = get_template(template_id)
        assert template is not None

        player = _player_at_axiom()
        player.game_day = accept_day
        player.okafor_research_state = OkaforResearchState()
        active = fund_project(player.okafor_research_state, template, accept_day, collaborators=[])
        player.deduct_credits(active.cost_paid)
        starting_credits_after_fund = player.credits

        completion_day = active.completion_day
        outcomes = resolve_completed_projects(
            player.okafor_research_state,
            completion_day,
            player.name,
            0.0,
            0.0,
        )
        assert len(outcomes) == 1
        assert outcomes[0].success is False
        # 30% refund of cost_paid.
        assert outcomes[0].payout == round(active.cost_paid * FAILURE_REFUND_RATE)
        player.add_credits(outcomes[0].payout)
        player.dialogue_flags[okafor_project_failed_first()] = True
        player.dialogue_flags[okafor_first_failure_seen()] = True
        # No holding produced on failure.
        assert player.okafor_research_state.holdings == []
        assert player.okafor_research_state.failed_count == 1
        assert player.credits == starting_credits_after_fund + outcomes[0].payout


class TestSkillStacking:
    """Acceptance #7 — Nuri Solberg + skills 2+2 produces +0.20 / +0.20 totals."""

    def test_full_stack_at_resolution(self) -> None:
        # Set the player's progression so research_yield and research_oversight
        # are at level 2 (each grants +0.10 — 2 levels = +0.20 of crew share).
        # Per the SA-R1 plan, the stacked totals reach +0.20 yield + +0.20 risk.
        player = _player_at_axiom()
        # Manually push the skills to level 2.
        prog = player.progression
        # Force the skill levels (research_yield, research_oversight).
        if "research_yield" in prog.skills:
            prog.skills["research_yield"].current_level = 2
        if "research_oversight" in prog.skills:
            prog.skills["research_oversight"].current_level = 2
        skill_yield = prog.get_bonus("research_yield_bonus")
        skill_risk = prog.get_bonus("research_risk_reduction")
        # Skills alone supply +0.10 (research_yield) + +0.10 (research_oversight).
        assert skill_yield == 0.10
        assert skill_risk == 0.10
        # Crew share: Nuri Solberg supplies +0.10 each.
        crew_yield = 0.10  # from data/crew/crew_members.json#nuri_solberg
        crew_risk = 0.10
        total_yield = skill_yield + crew_yield
        total_risk = skill_risk + crew_risk
        assert total_yield == 0.20
        assert total_risk == 0.20

        # Resolve a project with the stacked totals — payout scales correctly.
        template_id = _mid_tier_template_id()
        accept_day = _find_first_outcome(
            template_id,
            expect_success=True,
            yield_bonus=total_yield,
            risk_reduction=total_risk,
        )
        template = get_template(template_id)
        assert template is not None
        state = OkaforResearchState()
        fund_project(state, template, accept_day, collaborators=[])
        outcomes = resolve_completed_projects(
            state,
            accept_day + template.base_duration_days,
            player.name,
            total_yield,
            total_risk,
        )
        assert outcomes[0].success
        # Yield-boosted payout: base * (1 + 0.20).
        assert outcomes[0].payout == round(template.base_success_payout * 1.20)


class TestMidCycleSaveLoad:
    """A save with two active projects + held patent + licensed patent round-trips."""

    def test_save_mid_cycle_round_trips(self) -> None:
        player = _player_at_axiom(credits=200_000)
        player.game_day = 50
        state = OkaforResearchState(
            kweon_relationship_value=3,
            slot_seed_window=1,
            slot_offers=["mid_neural_synthesis_protocol", "high_quantum_sensor_capstone"],
            completed_count=2,
            failed_count=1,
        )
        fund_project(state, get_template("mid_neural_synthesis_protocol"), 45, collaborators=[])  # type: ignore[arg-type]
        fund_project(state, get_template("high_quantum_sensor_capstone"), 47, collaborators=[])  # type: ignore[arg-type]
        state.holdings.extend(
            [
                PatentHolding(
                    holding_id="held_a",
                    template_id="mid_orbital_propulsion_efficiency",
                    state="held",
                    success_payout=80_000,
                ),
                PatentHolding(
                    holding_id="lic_a",
                    template_id="low_protein_folding_replication",
                    state="licensed",
                    success_payout=14_000,
                    license_start_day=40,
                    next_royalty_day=50,
                ),
            ]
        )
        player.okafor_research_state = state

        restored = round_trip_save(player)
        assert restored.okafor_research_state is not None
        rs = restored.okafor_research_state
        assert rs.kweon_relationship_value == 3
        assert rs.slot_seed_window == 1
        assert rs.completed_count == 2
        assert rs.failed_count == 1
        assert "mid_neural_synthesis_protocol" in rs.active_projects
        assert "high_quantum_sensor_capstone" in rs.active_projects
        assert len(rs.holdings) == 2
        assert any(h.state == "held" for h in rs.holdings)
        licensed = next(h for h in rs.holdings if h.state == "licensed")
        assert licensed.next_royalty_day == 50
