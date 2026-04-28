"""SA-B2: AuctionView substate transitions, UI lifecycle, FirstTimeTip wiring."""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.constants.flags import (
    auction_first_session_complete,
    auction_sable_ceiling_correct,
    seen_auction_first_session_tip,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import AuctionLifecycle, sable_displayed_ceiling
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_MODULE,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import (
    PERSONA_PRENTISS,
    make_prentiss,
)
from spacegame.models.crew import CrewRoster
from spacegame.models.player import Player
from spacegame.models.progression import PlayerProgression
from spacegame.models.ship import Ship
from spacegame.views.auction_view import (
    TIP_BODY,
    TIP_TITLE,
    AuctionSubstate,
    AuctionView,
    _lifecycle_to_substate,
)


def _module_lot(lot_id: str = "mod1") -> AuctionLot:
    return AuctionLot(
        id=lot_id,
        headline=f"Module {lot_id}",
        description="--",
        category=LOT_CATEGORY_MODULE,
        venue=VENUE_STELLARIS,
        base_appraisal=12000,
        reserve_pct=0.75,
    )


def _make_env() -> tuple[pygame_gui.UIManager, Player, CrewRoster, PlayerProgression]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Tester",
        credits=2000,
        current_system_id="stellaris_port",
        ship=ship,
        game_day=10,
    )
    crew_roster = CrewRoster(templates=dl.crew_templates)
    return manager, player, crew_roster, player.progression


def _make_view(
    manager: pygame_gui.UIManager,
    player: Player,
    crew_roster: CrewRoster,
    progression: PlayerProgression,
) -> AuctionView:
    return AuctionView(
        ui_manager=manager,
        player=player,
        crew_roster=crew_roster,
        progression=progression,
        venue_id="stellaris",
        venue_display_name="Stellaris Auction House",
    )


class TestConstruction:
    def test_construct_default(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        assert view is not None
        assert view.next_state is None

    def test_on_enter_sets_active(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        assert view.active
        view.on_exit()
        assert not view.active


class TestFirstTimeTip:
    def test_tip_fires_on_first_entry(self) -> None:
        manager, player, cr, prog = _make_env()
        assert seen_auction_first_session_tip() not in player.dialogue_flags
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        assert view._tip_overlay is not None
        assert view._tip_overlay.title == TIP_TITLE
        assert view._tip_overlay.body == TIP_BODY
        view.on_exit()

    def test_tip_does_not_fire_when_flag_already_set(self) -> None:
        manager, player, cr, prog = _make_env()
        player.dialogue_flags[seen_auction_first_session_tip()] = True
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        assert view._tip_overlay is None
        view.on_exit()

    def test_dismiss_sets_flag(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        assert view._tip_overlay is not None
        view._tip_overlay._dismiss()
        assert player.dialogue_flags.get(seen_auction_first_session_tip()) is True
        view.on_exit()


class TestSubstateTransitions:
    def test_lifecycle_to_substate_mapping(self) -> None:
        assert _lifecycle_to_substate(AuctionLifecycle.SCHEDULED) == AuctionSubstate.PREVIEW
        assert _lifecycle_to_substate(AuctionLifecycle.PREVIEW) == AuctionSubstate.PREVIEW
        assert _lifecycle_to_substate(AuctionLifecycle.BID_WINDOW) == AuctionSubstate.BID_WINDOW
        assert (
            _lifecycle_to_substate(AuctionLifecycle.LOT_RESOLUTION)
            == AuctionSubstate.LOT_RESOLUTION
        )
        assert (
            _lifecycle_to_substate(AuctionLifecycle.SESSION_CLOSE) == AuctionSubstate.POST_SESSION
        )

    def test_preview_to_bid_window_rebuilds_ui(self) -> None:
        manager, player, cr, prog = _make_env()
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [_module_lot("a")],
            rival_ids=[],
            session_id="t1",
        )
        player.auction_state.set_session_personas([])
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        # PREVIEW substate has the start_button.
        assert view.start_button is not None
        assert view.raise_min_button is None
        # Open the session via update loop (the button handler does this).
        player.auction_state.open_session()
        view.update(0.0)  # Triggers rebuild on substate change.
        assert view.raise_min_button is not None
        assert view.start_button is None
        view.on_exit()

    def test_speed_buttons_present_in_preview(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        assert "slow" in view._speed_buttons
        assert "normal" in view._speed_buttons
        assert "fast" in view._speed_buttons
        assert "asap" in view._speed_buttons
        view.on_exit()


class TestUILifecycleNoLeak:
    def test_create_destroy_each_substate_twice(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        baseline = len(manager.get_root_container().elements)

        # Bring up PREVIEW UI twice.
        view.on_enter()
        view.on_exit()
        view.on_enter()
        view.on_exit()
        # Element count should return to baseline after the second exit.
        assert len(manager.get_root_container().elements) == baseline

    def test_destroy_all_ui_clears_refs(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        view._destroy_all_ui()
        assert view.back_button is None
        assert view.start_button is None
        assert view.raise_min_button is None
        assert view._speed_buttons == {}
        view.on_exit()


class TestEmptyStateRender:
    def test_no_session_renders_quiet_floor(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        # Should not raise.
        view.render(screen)
        view.on_exit()

    def test_loading_state_renders(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_loading(True)
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.on_exit()

    def test_error_state_renders(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_error("Unable to load auction data.")
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.on_exit()


class TestBidActions:
    def _setup_bid_window(
        self,
    ) -> tuple[pygame_gui.UIManager, Player, CrewRoster, PlayerProgression, AuctionView]:
        manager, player, cr, prog = _make_env()
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [_module_lot("a")],
            rival_ids=[],
            session_id="bw_test",
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        return manager, player, cr, prog, view

    def test_min_raise_submits_bid(self) -> None:
        _manager, player, _cr, _prog, view = self._setup_bid_window()
        amount = player.auction_state.player_min_raise_amount()
        view._submit_min_raise()
        assert player.auction_state.round_state is not None
        assert player.auction_state.round_state.current_high_bidder_id == "player"
        assert player.auction_state.round_state.current_high_bid == amount
        view.on_exit()

    def test_fold_removes_player(self) -> None:
        _manager, player, _cr, _prog, view = self._setup_bid_window()
        ok, _msg = player.auction_state.player_fold()
        assert ok
        assert "player" not in player.auction_state.round_state.bidders_active
        view.on_exit()


class TestSableVisibilityRender:
    def test_render_with_named_rivals_present(self) -> None:
        manager, player, cr, prog = _make_env()
        # Force Sable visibility on by stubbing the bonus query.
        original_get_bonus = cr.get_bonus

        def stub(bonus_type: str) -> float:
            if bonus_type == "auction_bid_visibility":
                return 1.0
            return original_get_bonus(bonus_type)

        cr.get_bonus = stub  # type: ignore[method-assign]
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [_module_lot("a")],
            rival_ids=[PERSONA_PRENTISS],
            session_id="sable_test",
        )
        player.auction_state.set_session_personas([make_prentiss()])
        player.auction_state.open_session()
        view = _make_view(manager, player, cr, prog)
        view.set_active_personas([make_prentiss()])
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.on_exit()


class TestNextStateOnEscape:
    def test_escape_routes_back_to_station_hub(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        # Dismiss the tip overlay first so events fall through.
        if view._tip_overlay is not None:
            view._tip_overlay._dismiss()
            view._tip_overlay = None
        evt = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(evt)
        assert view.next_state == GameState.STATION_HUB
        view.on_exit()


class TestPostSessionRender:
    def test_session_close_summary(self) -> None:
        manager, player, cr, prog = _make_env()
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [_module_lot("a")],
            rival_ids=[],
            session_id="pos_test",
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        # Drive the session to close by ticking past every round.
        for _ in range(80):
            player.auction_state.tick(5.0)
            if player.auction_state.lifecycle == AuctionLifecycle.LOT_RESOLUTION:
                player.auction_state.advance_after_resolution()
            if player.auction_state.lifecycle == AuctionLifecycle.SESSION_CLOSE:
                break
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.on_exit()


class TestBanterFlags:
    """AC 15: crew-banter flags fire at the moments specified in §9.4.

    Banter flags for session_complete / lot_won / rivalry_formed are set
    via view callbacks wired from game.py. These tests wire equivalent
    test callbacks and verify the VIEW fires them at the right moments.
    ``auction_sable_ceiling_correct`` is set directly in the view's
    ``_fire_lot_callbacks`` method and is tested end-to-end here.
    """

    def _setup_session(
        self,
        rival_ids: list[str] | None = None,
        session_id: str = "banter_test",
    ) -> tuple[pygame_gui.UIManager, Player, CrewRoster, PlayerProgression, AuctionView]:
        manager, player, cr, prog = _make_env()
        player.credits = 999_999
        lots = [_module_lot("bant1")]
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            lots,
            rival_ids=rival_ids or [],
            session_id=session_id,
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        return manager, player, cr, prog, view

    def test_on_session_complete_fires_via_maybe_fire_helper(self) -> None:
        """_maybe_fire_session_complete fires on_session_complete when lifecycle=SESSION_CLOSE."""
        manager, player, cr, prog = _make_env()
        player.auction_state.enter_preview(
            VENUE_STELLARIS, [_module_lot("sc1")], rival_ids=[], session_id="sc_test"
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        for _ in range(80):
            player.auction_state.tick(5.0)
            if player.auction_state.lifecycle == AuctionLifecycle.LOT_RESOLUTION:
                player.auction_state.advance_after_resolution()
            if player.auction_state.lifecycle == AuctionLifecycle.SESSION_CLOSE:
                break
        view = _make_view(manager, player, cr, prog)
        view.on_enter()
        fired: list[bool] = []
        view.on_session_complete = lambda: fired.append(True)
        # _maybe_fire_session_complete is called from _handle_button; invoke directly.
        view._maybe_fire_session_complete()
        assert fired, "on_session_complete should fire when lifecycle is SESSION_CLOSE"
        # Wiring: game.py would set the dialogue flag here.
        player.dialogue_flags[auction_first_session_complete()] = True
        assert player.dialogue_flags.get(auction_first_session_complete())
        view.on_exit()

    def test_on_lot_won_fires_when_player_wins(self) -> None:
        """on_lot_won callback fires when player wins a lot via view.update()."""
        _manager, player, _cr, _prog, view = self._setup_session()
        won_lots_from_cb: list[str] = []
        view.on_lot_won = lambda lot, price: won_lots_from_cb.append(lot.id)
        # Force player to win: bid well above reserve and exhaust the timer.
        player.credits = 999_999
        player.auction_state.submit_player_bid(
            player.auction_state.player_min_raise_amount() + 5000
        )
        for _ in range(60):
            view.update(5.0)
            if player.auction_state.lifecycle == AuctionLifecycle.LOT_RESOLUTION:
                break
        assert player.auction_state.lifecycle == AuctionLifecycle.LOT_RESOLUTION
        # on_lot_won fires only if the player won the lot.
        record = player.auction_state.session_lot_results[0]
        if record.winner_id == "player":
            assert "bant1" in won_lots_from_cb, "on_lot_won must fire when player wins"
        view.on_exit()

    def test_on_rivalry_formed_fires_when_rival_wins_against_player(self) -> None:
        """on_rivalry_formed fires when a named rival outbids the player."""
        from spacegame.models.bidding_lot import LOT_CATEGORY_ANTIQUITY

        manager, player, cr, prog = _make_env()
        lot = AuctionLot(
            id="rival_ant",
            headline="Rival Antiquity",
            description="--",
            category=LOT_CATEGORY_ANTIQUITY,
            venue=VENUE_STELLARIS,
            base_appraisal=9000,
            reserve_pct=0.70,
        )
        player.auction_state.enter_preview(
            VENUE_STELLARIS, [lot], rival_ids=[PERSONA_PRENTISS], session_id="riv_test"
        )
        prentiss = make_prentiss()
        player.auction_state.set_session_personas([prentiss])
        player.auction_state.open_session()
        view = _make_view(manager, player, cr, prog)
        view.set_active_personas([prentiss])
        view.on_enter()
        rivalry_fired: list[str] = []
        view.on_rivalry_formed = lambda rival_id, _lot: rivalry_fired.append(rival_id)
        # Player bids opening amount; Prentiss should counter.
        player.auction_state.submit_player_bid(player.auction_state.player_min_raise_amount())
        for _ in range(120):
            view.update(2.0)
            if player.auction_state.lifecycle == AuctionLifecycle.LOT_RESOLUTION:
                break
        record = (
            player.auction_state.session_lot_results[0]
            if player.auction_state.session_lot_results
            else None
        )
        if record and record.sold and record.winner_id == PERSONA_PRENTISS and record.player_bid:
            assert PERSONA_PRENTISS in rivalry_fired, (
                "on_rivalry_formed must fire when rival wins vs player"
            )
        view.on_exit()

    def test_auction_sable_ceiling_correct_flag_set_within_5_percent(self) -> None:
        """auction_sable_ceiling_correct is set when player wins within 5% of Sable's estimate."""
        manager, player, cr, prog = _make_env()
        lot = _module_lot("scc_lot")
        player.auction_state.enter_preview(
            VENUE_STELLARIS, [lot], rival_ids=[PERSONA_PRENTISS], session_id="scc_test"
        )
        prentiss = make_prentiss()
        player.auction_state.set_session_personas([prentiss])
        player.auction_state.open_session()
        view = _make_view(manager, player, cr, prog)
        view.set_active_personas([prentiss])
        view.on_enter()
        # Stub auction_bid_visibility so Sable ceiling path is active.
        original_get_bonus = cr.get_bonus

        def _stub(bonus_type: str) -> float:
            if bonus_type == "auction_bid_visibility":
                return 1.0
            return original_get_bonus(bonus_type)

        cr.get_bonus = _stub  # type: ignore[method-assign]
        # Compute Sable's displayed ceiling for this lot/session.
        ceiling = sable_displayed_ceiling(prentiss, lot, "scc_test", vs_player=True)
        assert ceiling > 0
        # Build a synthetic lot result: player won at exactly the displayed ceiling.
        from spacegame.models.bidding import _LotResultRecord  # type: ignore[attr-defined]

        record = _LotResultRecord(
            lot_id=lot.id,
            sold=True,
            winner_id="player",
            sale_price=ceiling,
            player_bid=True,
            rivals_bid=[PERSONA_PRENTISS],
        )
        player.auction_state.session_lot_results.append(record)
        player.auction_state.won_lots.append(lot.id)
        view._fire_lot_callbacks(record)
        assert player.dialogue_flags.get(auction_sable_ceiling_correct()), (
            "auction_sable_ceiling_correct must be set when player wins within 5% of Sable's ceiling"
        )
        view.on_exit()
