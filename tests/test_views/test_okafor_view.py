"""Tests for OkaforView (SA-R1).

Covers:
  - Construction with synthetic state
  - on_enter / on_exit lifecycle and UI cleanup
  - First-time tip overlay fires once per save
  - met_npc flag fires on view entry
  - Project board renders 5-7 deterministic offers
  - Fund flow (solo) deducts credits and inserts ActiveProject
  - Fund flow with collaborators applies team-fund math + sets per-researcher flags
  - IP-disposition (held → licensed sets schedule; held → sold removes holding)
  - First-failure flag fires only once
  - Insufficient credits is rejected gracefully
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.constants.flags import (
    met_npc,
    okafor_collaborator_share,
    okafor_first_failure_seen,
    okafor_patent_disposed_first,
    okafor_project_funded_first,
    seen_okafor_tip,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.okafor_research import (
    OKAFOR_PROJECT_TEMPLATES,
    ROYALTY_INTERVAL_DAYS,
    SELL_LUMP_SUM_RATE,
    OkaforResearchState,
    PatentHolding,
    compute_team_fund_cost,
    compute_team_fund_duration,
    get_template,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.okafor_view import OkaforView


def _make_env(*, credits: int = 200_000, game_day: int = 5) -> tuple[pygame_gui.UIManager, Player]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Test Captain",
        credits=credits,
        current_system_id="axiom_labs",
        ship=ship,
        game_day=game_day,
    )
    return manager, player


def _make_view(player: Player, manager: pygame_gui.UIManager) -> OkaforView:
    return OkaforView(ui_manager=manager, player=player, crew_roster=None)


def _low_risk_template_id() -> str:
    for tpl in OKAFOR_PROJECT_TEMPLATES:
        if tpl.risk_tier == "low":
            return tpl.id
    raise RuntimeError("No low-risk template")


class TestConstruction:
    def test_construct(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        assert view is not None
        assert view.next_state is None

    def test_on_enter_sets_active(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_destroys_ui(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view.on_exit()
        assert view.back_button is None


class TestEntryFlags:
    def test_first_entry_does_not_set_seen_okafor_tip_immediately(self) -> None:
        # Tip overlay creates but the seen flag only sets on dismissal.
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.dialogue_flags.get(seen_okafor_tip()) is not True
        # Tip exists when not yet dismissed.
        assert view._tip_overlay is not None
        view.on_exit()

    def test_dismissing_tip_sets_seen_flag(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        # Trigger the dismiss callback directly.
        if view._tip_overlay and view._tip_overlay.on_dismiss:
            view._tip_overlay.on_dismiss()
        assert player.dialogue_flags.get(seen_okafor_tip()) is True
        view.on_exit()

    def test_returning_does_not_refire_tip(self) -> None:
        manager, player = _make_env()
        player.dialogue_flags[seen_okafor_tip()] = True
        view = _make_view(player, manager)
        view.on_enter()
        assert view._tip_overlay is None
        view.on_exit()

    def test_met_npc_kweon_director_set_on_entry(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.dialogue_flags.get(met_npc("kweon_director")) is True
        view.on_exit()


class TestProjectBoard:
    def test_offers_are_deterministic_per_window(self) -> None:
        manager, player = _make_env(game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        offers_a = view.get_offered_template_ids()
        view.on_exit()
        # Same player, same window — second visit reproduces offers.
        view2 = _make_view(player, manager)
        view2.on_enter()
        offers_b = view2.get_offered_template_ids()
        view2.on_exit()
        assert offers_a == offers_b

    def test_offer_count_is_5_to_7(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        n = len(view.get_offered_template_ids())
        assert 5 <= n <= 7
        view.on_exit()

    def test_offers_filter_out_already_funded(self) -> None:
        manager, player = _make_env(credits=200_000, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        offers_a = view.get_offered_template_ids()
        # Fund the first offer.
        funded = view._fund_project(offers_a[0], collaborators=[])
        assert funded
        # Now the offer should be filtered from the visible board.
        offers_b = view.get_offered_template_ids()
        assert offers_a[0] not in offers_b
        view.on_exit()


class TestFundFlow:
    def test_solo_fund_deducts_credits_and_inserts_active(self) -> None:
        manager, player = _make_env(credits=200_000, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        tpl_id = _low_risk_template_id()
        starting_credits = player.credits
        funded = view._fund_project(tpl_id, collaborators=[])
        assert funded, "low-tier fund should succeed"
        tpl = get_template(tpl_id)
        assert tpl is not None
        assert player.credits == starting_credits - tpl.base_cost_credits
        assert player.okafor_research_state is not None
        assert tpl_id in player.okafor_research_state.active_projects
        active = player.okafor_research_state.active_projects[tpl_id]
        assert active.cost_paid == tpl.base_cost_credits
        assert active.duration_days == tpl.base_duration_days
        view.on_exit()

    def test_team_fund_one_collaborator_applies_math(self) -> None:
        """Acceptance #6 — team-fund with 1 collaborator: 1.5x cost, 0.7x duration."""
        manager, player = _make_env(credits=500_000, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        starting_credits = player.credits
        funded = view._fund_project(tpl_id, collaborators=["dr_iris_navarro"])
        assert funded
        expected_cost = compute_team_fund_cost(tpl.base_cost_credits, 1)
        expected_duration = compute_team_fund_duration(tpl.base_duration_days, 1)
        active = player.okafor_research_state.active_projects[tpl_id]  # type: ignore[union-attr]
        assert active.cost_paid == expected_cost
        assert active.duration_days == expected_duration
        assert player.credits == starting_credits - expected_cost
        # Per-collaborator dialogue flag set.
        assert player.dialogue_flags.get(okafor_collaborator_share("dr_iris_navarro")) is True
        view.on_exit()

    def test_team_fund_two_collaborators_applies_math(self) -> None:
        """Acceptance #6 — team-fund with 2: 2.0x cost, 0.5x duration."""
        manager, player = _make_env(credits=500_000, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        funded = view._fund_project(tpl_id, collaborators=["dr_iris_navarro", "theo_brandt"])
        assert funded
        active = player.okafor_research_state.active_projects[tpl_id]  # type: ignore[union-attr]
        assert active.cost_paid == compute_team_fund_cost(tpl.base_cost_credits, 2)
        assert active.duration_days == compute_team_fund_duration(tpl.base_duration_days, 2)
        assert player.dialogue_flags.get(okafor_collaborator_share("dr_iris_navarro")) is True
        assert player.dialogue_flags.get(okafor_collaborator_share("theo_brandt")) is True
        view.on_exit()

    def test_fund_rejects_insufficient_credits(self) -> None:
        manager, player = _make_env(credits=100, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        tpl_id = _low_risk_template_id()
        funded = view._fund_project(tpl_id, collaborators=[])
        assert funded is False
        assert (
            player.okafor_research_state is None or not player.okafor_research_state.active_projects
        )
        view.on_exit()

    def test_fund_sets_first_funded_flag(self) -> None:
        manager, player = _make_env(credits=200_000, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        tpl_id = _low_risk_template_id()
        view._fund_project(tpl_id, collaborators=[])
        assert player.dialogue_flags.get(okafor_project_funded_first()) is True
        view.on_exit()

    def test_double_fund_same_template_rejected(self) -> None:
        manager, player = _make_env(credits=500_000, game_day=5)
        view = _make_view(player, manager)
        view.on_enter()
        tpl_id = _low_risk_template_id()
        assert view._fund_project(tpl_id, collaborators=[]) is True
        # Second attempt must not re-deduct credits or replace the active.
        starting = player.credits
        assert view._fund_project(tpl_id, collaborators=[]) is False
        assert player.credits == starting
        view.on_exit()


class TestPatentDisposition:
    def _seed_held_holding(self, player: Player) -> PatentHolding:
        state = OkaforResearchState(
            holdings=[
                PatentHolding(
                    holding_id="x_5",
                    template_id="x",
                    state="held",
                    success_payout=100_000,
                ),
            ],
        )
        player.okafor_research_state = state
        return state.holdings[0]

    def test_license_holding_starts_royalty_schedule(self) -> None:
        manager, player = _make_env(game_day=20)
        view = _make_view(player, manager)
        view.on_enter()
        holding = self._seed_held_holding(player)
        view._license_patent("x_5")
        assert holding.state == "licensed"
        assert holding.license_start_day == 20
        assert holding.next_royalty_day == 20 + ROYALTY_INTERVAL_DAYS
        assert player.dialogue_flags.get(okafor_patent_disposed_first()) is True
        view.on_exit()

    def test_sell_holding_pays_lump_and_removes_it(self) -> None:
        manager, player = _make_env(game_day=20, credits=0)
        view = _make_view(player, manager)
        view.on_enter()
        self._seed_held_holding(player)
        view._sell_patent("x_5")
        # 60% of 100k = 60k.
        assert player.credits == int(100_000 * SELL_LUMP_SUM_RATE)
        assert player.okafor_research_state is not None
        assert player.okafor_research_state.find_holding("x_5") is None
        assert player.dialogue_flags.get(okafor_patent_disposed_first()) is True
        view.on_exit()


class TestFailureDebrief:
    def test_first_failure_flag_recorded_on_view_open_after_tick(self) -> None:
        """The view surfaces the first-failure debrief when seen flag toggles."""
        # The Game._tick_okafor_projects sets okafor_first_failure_seen.
        # Here we simulate that the flag was already set from a prior tick
        # and verify the view exposes the debrief copy without re-firing.
        manager, player = _make_env()
        # Pretend the tick fired the failure flag earlier this play session.
        player.dialogue_flags[okafor_first_failure_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        # _failure_debrief_pending should be False once the flag is already
        # set (so the debrief banner shows once and not again).
        assert view._failure_debrief_pending is False
        view.on_exit()
