"""Tests for OkaforView (SA-R1 / SA-R2).

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
  - SA-R2: _kweon_dialogue_id() routing (failure_debrief > arc_beat > ambient)
  - SA-R2: _close_active_dialogue() sets arc-beat seen-flags + legacy_ending
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.constants.flags import (
    met_npc,
    okafor_collaborator_share,
    okafor_failure_debrief_shown,
    okafor_first_failure_seen,
    okafor_legacy_clinic_callback_seen,
    okafor_legacy_first_heal_seen,
    okafor_legacy_first_profit_seen,
    okafor_legacy_heal_ending_seen,
    okafor_legacy_heal_pattern_seen,
    okafor_legacy_mission_completed,
    okafor_legacy_profit_ending_seen,
    okafor_legacy_profit_pattern_seen,
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
    def test_failure_debrief_pending_when_flag_set_and_unseen(self) -> None:
        """Pending = True when failure happened and the debrief tree has not played."""
        manager, player = _make_env()
        player.dialogue_flags[okafor_first_failure_seen()] = True
        # Debrief has not been shown yet — the Kweon button must route to the debrief.
        view = _make_view(player, manager)
        view.on_enter()
        assert view._failure_debrief_pending is True
        view.on_exit()

    def test_failure_debrief_pending_false_after_shown(self) -> None:
        """Pending = False once the debrief tree has been dismissed."""
        manager, player = _make_env()
        player.dialogue_flags[okafor_first_failure_seen()] = True
        player.dialogue_flags[okafor_failure_debrief_shown()] = True
        view = _make_view(player, manager)
        view.on_enter()
        assert view._failure_debrief_pending is False
        view.on_exit()

    def test_failure_debrief_pending_false_when_no_failure_yet(self) -> None:
        """Pending = False before any project failure has occurred."""
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert view._failure_debrief_pending is False
        view.on_exit()


class TestNpcDock:
    """Acceptance #2 + rework task 13: every authored dialogue tree is reachable."""

    def test_dock_speaker_ids_includes_kweon_and_three_researchers(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        ids = view.get_visible_dock_speaker_ids()
        assert "kweon_director" in ids
        assert "dr_iris_navarro" in ids
        assert "theo_brandt" in ids
        assert "sana_dey" in ids
        view.on_exit()

    def test_dock_excludes_nuri_when_not_in_crew(self) -> None:
        manager, player = _make_env()
        # No crew_state — Nuri is not surfaced.
        view = _make_view(player, manager)
        view.on_enter()
        assert "nuri_solberg" not in view.get_visible_dock_speaker_ids()
        view.on_exit()

    def test_dock_includes_nuri_when_in_crew(self) -> None:
        manager, player = _make_env()
        player.crew_state = {"active": ["nuri_solberg"]}
        view = _make_view(player, manager)
        view.on_enter()
        assert "nuri_solberg" in view.get_visible_dock_speaker_ids()
        view.on_exit()

    def test_npc_buttons_created_for_each_visible_speaker(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        for speaker_id in view.get_visible_dock_speaker_ids():
            assert speaker_id in view._npc_buttons, f"Missing button for speaker '{speaker_id}'"
        view.on_exit()

    def test_destroy_ui_clears_npc_buttons(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert view._npc_buttons
        view.on_exit()
        assert not view._npc_buttons

    def test_kweon_button_opens_intro_tree(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("kweon_director")
        node = view.get_active_dialogue_node()
        assert node is not None
        assert node.speaker_id == "kweon_director"
        # The intro tree starts at "greeting".
        assert view._active_dialogue_node_id == "greeting"
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "kweon_okafor_intro"
        view.on_exit()

    def test_iris_button_opens_iris_tree(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("dr_iris_navarro")
        node = view.get_active_dialogue_node()
        assert node is not None
        assert node.speaker_id == "dr_iris_navarro"
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "iris_navarro_okafor"
        view.on_exit()

    def test_theo_and_sana_buttons_open_their_trees(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("theo_brandt")
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "theo_brandt_okafor"
        view._close_active_dialogue()
        view._open_npc_dialogue("sana_dey")
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "sana_dey_okafor"
        view.on_exit()

    def test_nuri_button_opens_collaborator_tree_when_in_crew(self) -> None:
        manager, player = _make_env()
        player.crew_state = {"active": ["nuri_solberg"]}
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("nuri_solberg")
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "nuri_solberg_okafor_collaborator"
        view.on_exit()

    def test_advance_dialogue_walks_to_next_node(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("kweon_director")
        assert view._active_dialogue_node_id == "greeting"
        view._advance_dialogue()
        # greeting → board_pitch (first response).
        assert view._active_dialogue_node_id == "board_pitch"
        view.on_exit()

    def test_advance_dialogue_to_terminal_closes_panel(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("kweon_director")
        # Walk: greeting → board_pitch → ip_explanation → null (close).
        view._advance_dialogue()
        view._advance_dialogue()
        view._advance_dialogue()
        assert view._active_dialogue_tree is None
        assert view._active_dialogue_node_id is None
        view.on_exit()

    def test_open_unknown_speaker_is_noop(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("does_not_exist")
        assert view.get_active_dialogue_node() is None
        view.on_exit()

    def test_kweon_routes_to_failure_debrief_when_pending(self) -> None:
        """Kweon's button opens the failure-debrief tree after the first failure."""
        manager, player = _make_env()
        player.dialogue_flags[okafor_first_failure_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("kweon_director")
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "kweon_failure_debrief"
        view.on_exit()

    def test_kweon_failure_debrief_dismiss_sets_shown_flag(self) -> None:
        """Walking through the failure-debrief tree marks the shown flag."""
        manager, player = _make_env()
        player.dialogue_flags[okafor_first_failure_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("kweon_director")
        # Single-node tree → advance closes and sets the shown flag.
        view._advance_dialogue()
        assert view._active_dialogue_tree is None
        assert player.dialogue_flags.get(okafor_failure_debrief_shown()) is True
        view.on_exit()

    def test_kweon_routes_to_intro_after_debrief_shown(self) -> None:
        """Once the failure-debrief is dismissed, Kweon returns to the intro tree."""
        manager, player = _make_env()
        player.dialogue_flags[okafor_first_failure_seen()] = True
        player.dialogue_flags[okafor_failure_debrief_shown()] = True
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("kweon_director")
        assert view._active_dialogue_tree is not None
        assert view._active_dialogue_tree.id == "kweon_okafor_intro"
        view.on_exit()


# ---------------------------------------------------------------------------
# SA-R2 — _kweon_dialogue_id() routing and close-handler arc-beat flags
# ---------------------------------------------------------------------------


def _make_state_with_heal(n: int) -> OkaforResearchState:
    return OkaforResearchState(legacy_heal_completed=n)


def _make_state_with_profit(n: int) -> OkaforResearchState:
    return OkaforResearchState(legacy_profit_completed=n)


class TestKweonDialogueIdRouting:
    """Acceptance #5 — _kweon_dialogue_id() priority order."""

    def test_failure_debrief_beats_arc_beat(self) -> None:
        """failure_debrief_pending takes top priority."""
        manager, player = _make_env()
        player.dialogue_flags[okafor_first_failure_seen()] = True
        # Arc beat is also due (1 heal completed, first_heal not seen)
        player.okafor_research_state = _make_state_with_heal(1)
        view = _make_view(player, manager)
        view.on_enter()
        assert view._kweon_dialogue_id() == "kweon_failure_debrief"
        view.on_exit()

    def test_arc_beat_beats_ambient_when_pending(self) -> None:
        """Arc beat fires ahead of the ambient greeting."""
        manager, player = _make_env()
        player.okafor_research_state = _make_state_with_heal(1)
        view = _make_view(player, manager)
        view.on_enter()
        result = view._kweon_dialogue_id()
        assert result == "kweon_legacy_first_heal"
        view.on_exit()

    def test_ambient_returned_when_no_beat_pending(self) -> None:
        """Falls through to ambient intro when no arc beat is due."""
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState()
        view = _make_view(player, manager)
        view.on_enter()
        assert view._kweon_dialogue_id() == "kweon_okafor_intro"
        view.on_exit()

    def test_profit_beat_routes_correctly(self) -> None:
        manager, player = _make_env()
        player.okafor_research_state = _make_state_with_profit(1)
        view = _make_view(player, manager)
        view.on_enter()
        assert view._kweon_dialogue_id() == "kweon_legacy_first_profit"
        view.on_exit()

    def test_heal_pattern_routes_at_three(self) -> None:
        manager, player = _make_env()
        player.okafor_research_state = _make_state_with_heal(3)
        player.dialogue_flags[okafor_legacy_first_heal_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        assert view._kweon_dialogue_id() == "kweon_legacy_heal_pattern"
        view.on_exit()

    def test_heal_ending_routes_at_spread(self) -> None:
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState(
            legacy_heal_completed=6, legacy_profit_completed=1
        )
        player.dialogue_flags[okafor_legacy_first_heal_seen()] = True
        player.dialogue_flags[okafor_legacy_heal_pattern_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        assert view._kweon_dialogue_id() == "kweon_legacy_heal_ending"
        view.on_exit()


class TestCloseHandlerSetsArcBeatFlags:
    """Acceptance #6 — closing an arc-beat tree sets the matching seen-flag."""

    def _open_arc_tree(self, view: OkaforView, tree_id: str) -> None:
        """Directly open a specific dialogue tree (bypasses routing)."""
        dl = get_data_loader()
        tree = dl.get_dialogue(tree_id)
        assert tree is not None, f"Tree {tree_id!r} not found in data"
        view._active_dialogue_tree = tree
        view._active_dialogue_node_id = tree.start_node_id
        view._active_dialogue_is_failure_debrief = False

    @pytest.mark.parametrize(
        "tree_id,flag_fn",
        [
            ("kweon_legacy_first_heal", okafor_legacy_first_heal_seen),
            ("kweon_legacy_first_profit", okafor_legacy_first_profit_seen),
            ("kweon_legacy_heal_pattern", okafor_legacy_heal_pattern_seen),
            ("kweon_legacy_profit_pattern", okafor_legacy_profit_pattern_seen),
        ],
    )
    def test_closing_arc_tree_sets_seen_flag(
        self,
        tree_id: str,
        flag_fn: object,
    ) -> None:
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState()
        view = _make_view(player, manager)
        view.on_enter()
        self._open_arc_tree(view, tree_id)
        assert not player.dialogue_flags.get(flag_fn())  # type: ignore[operator]
        view._close_active_dialogue()
        assert player.dialogue_flags.get(flag_fn()) is True  # type: ignore[operator]
        view.on_exit()

    def test_closing_heal_ending_sets_legacy_ending(self) -> None:
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState()
        view = _make_view(player, manager)
        view.on_enter()
        self._open_arc_tree(view, "kweon_legacy_heal_ending")
        view._close_active_dialogue()
        assert player.dialogue_flags.get(okafor_legacy_heal_ending_seen()) is True
        assert player.okafor_research_state.legacy_ending == "heal"
        view.on_exit()

    def test_closing_profit_ending_sets_legacy_ending(self) -> None:
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState()
        view = _make_view(player, manager)
        view.on_enter()
        self._open_arc_tree(view, "kweon_legacy_profit_ending")
        view._close_active_dialogue()
        assert player.dialogue_flags.get(okafor_legacy_profit_ending_seen()) is True
        assert player.okafor_research_state.legacy_ending == "profit"
        view.on_exit()

    def test_after_pattern_close_ambient_returns_next_or_ambient(self) -> None:
        """After closing the heal-pattern beat, re-routing gives next beat or ambient."""
        manager, player = _make_env()
        player.okafor_research_state = _make_state_with_heal(3)
        player.dialogue_flags[okafor_legacy_first_heal_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        # Pattern beat fires
        assert view._kweon_dialogue_id() == "kweon_legacy_heal_pattern"
        # Simulate dismissal
        self._open_arc_tree(view, "kweon_legacy_heal_pattern")
        view._close_active_dialogue()
        assert player.dialogue_flags.get(okafor_legacy_heal_pattern_seen()) is True
        # Now routing should return ambient (no more pending beats)
        result = view._kweon_dialogue_id()
        assert result in ("kweon_okafor_intro", "kweon_legacy_heal_ending")
        view.on_exit()


# ============================================================================
# SA-R3: Post-clinic-run callback routing + close-handler flag
# ============================================================================


class TestPostClinicRunCallbackRouting:
    """SA-R3 AC #7 and #8 — post-clinic-run callback in the priority chain."""

    def _setup_view_post_clinic(
        self,
        callback_seen: bool = False,
        arc_beat_pending: bool = False,
    ) -> tuple[OkaforView, "Player"]:
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState()
        # Mark clinic run completed
        player.dialogue_flags[okafor_legacy_mission_completed()] = True
        if callback_seen:
            player.dialogue_flags[okafor_legacy_clinic_callback_seen()] = True
        if arc_beat_pending:
            # Set up a pending first-heal beat
            player.okafor_research_state.legacy_heal_completed = 1
        view = _make_view(player, manager)
        view.on_enter()
        return view, player

    def test_post_clinic_run_callback_fires_when_mission_completed_and_not_seen(
        self,
    ) -> None:
        view, _player = self._setup_view_post_clinic(callback_seen=False)
        result = view._kweon_dialogue_id()
        assert result == "kweon_legacy_post_clinic_run", (
            f"Expected post-clinic-run callback, got {result!r}"
        )
        view.on_exit()

    def test_ambient_returns_when_callback_already_seen(self) -> None:
        view, _player = self._setup_view_post_clinic(callback_seen=True)
        # No arc beat pending, callback already seen -> ambient
        result = view._kweon_dialogue_id()
        assert result == "kweon_okafor_intro", (
            f"Expected ambient after callback seen, got {result!r}"
        )
        view.on_exit()

    def test_failure_debrief_beats_post_clinic_run(self) -> None:
        manager, player = _make_env()
        player.okafor_research_state = OkaforResearchState()
        player.dialogue_flags[okafor_legacy_mission_completed()] = True
        view = _make_view(player, manager)
        view.on_enter()
        # Force failure-debrief pending
        view._failure_debrief_pending = True
        result = view._kweon_dialogue_id()
        assert result == "kweon_failure_debrief", (
            f"failure_debrief must beat post-clinic-run, got {result!r}"
        )
        view.on_exit()

    def test_closing_callback_tree_sets_seen_flag(self) -> None:
        view, player = self._setup_view_post_clinic(callback_seen=False)
        dl = get_data_loader()
        tree = dl.get_dialogue("kweon_legacy_post_clinic_run")
        assert tree is not None, "kweon_legacy_post_clinic_run dialogue tree must exist"
        view._active_dialogue_tree = tree
        view._active_dialogue_node_id = tree.start_node_id
        view._active_dialogue_is_failure_debrief = False

        assert not player.dialogue_flags.get(okafor_legacy_clinic_callback_seen())
        view._close_active_dialogue()
        assert player.dialogue_flags.get(okafor_legacy_clinic_callback_seen()) is True, (
            "closing the post-clinic-run tree must set the seen flag"
        )
        # The callback is non-terminal — legacy_ending must NOT be set
        assert player.okafor_research_state.legacy_ending == "", (
            "post-clinic-run callback must not set legacy_ending"
        )
        view.on_exit()

    def test_arc_beat_fires_after_callback_dismissed(self) -> None:
        """Once the callback is seen, pending arc beats surface normally."""
        view, _player = self._setup_view_post_clinic(callback_seen=True, arc_beat_pending=True)
        # callback seen, arc beat pending → arc beat should surface
        result = view._kweon_dialogue_id()
        assert result == "kweon_legacy_first_heal", (
            f"Arc beat should surface once callback dismissed, got {result!r}"
        )


# ============================================================================
# SA-R3: Team-fund collaborator picker modal (AC #9)
# ============================================================================


class TestTeamFundPicker:
    """SA-R3 AC #9 — team-fund picker opens, manages selection, and funds correctly."""

    def _setup(self, credits: int = 500_000) -> tuple[OkaforView, "Player"]:
        manager, player = _make_env(credits=credits)
        view = _make_view(player, manager)
        view.on_enter()
        return view, player

    def test_open_picker_sets_active_state(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        assert view._picker_active is True
        assert view._picker_template_id == tpl_id
        view.on_exit()

    def test_picker_starts_with_empty_selection(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        assert view._picker_selected == []
        view.on_exit()

    def test_picker_toggle_adds_researcher(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        assert "dr_iris_navarro" in view._picker_selected
        view.on_exit()

    def test_picker_toggle_removes_researcher(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_toggle("dr_iris_navarro")
        assert "dr_iris_navarro" not in view._picker_selected
        view.on_exit()

    def test_picker_blocks_third_selection(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_toggle("theo_brandt")
        # Third toggle is blocked when 2 already selected
        view._picker_toggle("sana_dey")
        assert "sana_dey" not in view._picker_selected
        assert len(view._picker_selected) == 2
        view.on_exit()

    def test_picker_confirm_zero_selection_solo_funds(self) -> None:
        view, player = self._setup()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        starting = player.credits
        view._open_team_fund_picker(tpl_id)
        # Confirm with 0 → solo fund
        view._picker_confirm()
        assert not view._picker_active
        state = player.okafor_research_state
        assert state is not None
        assert tpl_id in state.active_projects
        # Solo cost = base cost (no collaborators)
        assert player.credits == starting - tpl.base_cost_credits
        view.on_exit()

    def test_picker_confirm_one_selection_funds_with_one(self) -> None:
        view, player = self._setup()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        starting = player.credits
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_confirm()
        assert not view._picker_active
        state = player.okafor_research_state
        assert state is not None
        assert tpl_id in state.active_projects
        expected_cost = compute_team_fund_cost(tpl.base_cost_credits, 1)
        assert player.credits == starting - expected_cost
        assert player.dialogue_flags.get(okafor_collaborator_share("dr_iris_navarro")) is True
        view.on_exit()

    def test_picker_confirm_two_selections_funds_with_two(self) -> None:
        view, player = self._setup()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        starting = player.credits
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_toggle("theo_brandt")
        view._picker_confirm()
        state = player.okafor_research_state
        assert state is not None
        assert tpl_id in state.active_projects
        expected_cost = compute_team_fund_cost(tpl.base_cost_credits, 2)
        assert player.credits == starting - expected_cost
        view.on_exit()

    def test_picker_cancel_does_not_fund(self) -> None:
        view, player = self._setup()
        tpl_id = _low_risk_template_id()
        starting = player.credits
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_cancel()
        assert not view._picker_active
        # No credits deducted, no active project
        assert player.credits == starting
        assert (
            player.okafor_research_state is None
            or tpl_id not in player.okafor_research_state.active_projects
        )
        view.on_exit()

    def test_picker_cancel_clears_selection(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_cancel()
        assert view._picker_selected == []
        assert view._picker_template_id is None
        view.on_exit()

    def test_live_cost_math_at_zero(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        view._open_team_fund_picker(tpl_id)
        cost, dur = view._picker_live_math()
        assert cost == tpl.base_cost_credits
        assert dur == tpl.base_duration_days
        view.on_exit()

    def test_live_cost_math_at_one(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        cost, dur = view._picker_live_math()
        assert cost == compute_team_fund_cost(tpl.base_cost_credits, 1)
        assert dur == compute_team_fund_duration(tpl.base_duration_days, 1)
        view.on_exit()

    def test_live_cost_math_at_two(self) -> None:
        view, _player = self._setup()
        tpl_id = _low_risk_template_id()
        tpl = get_template(tpl_id)
        assert tpl is not None
        view._open_team_fund_picker(tpl_id)
        view._picker_toggle("dr_iris_navarro")
        view._picker_toggle("theo_brandt")
        cost, dur = view._picker_live_math()
        assert cost == compute_team_fund_cost(tpl.base_cost_credits, 2)
        assert dur == compute_team_fund_duration(tpl.base_duration_days, 2)
        view.on_exit()

    def test_esc_during_picker_closes_picker_not_view(self) -> None:
        """ESC while the picker is open must dismiss the picker, not exit the view."""
        # Pre-set the seen-tip flag so the tip overlay is not created during
        # on_enter (the overlay has modal semantics and would eat the ESC key).
        manager, player = _make_env(credits=500_000)
        player.dialogue_flags[seen_okafor_tip()] = True
        view = _make_view(player, manager)
        view.on_enter()

        tpl_id = _low_risk_template_id()
        view._open_team_fund_picker(tpl_id)
        assert view._picker_active is True

        esc_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="\x1b")
        view.handle_event(esc_event)

        assert view._picker_active is False, "ESC must close the picker"
        assert view.next_state is None, "ESC on picker must not navigate away from the view"
        view.on_exit()
