"""SA-B5: AuctionView player-seller integration tests.

Covers acceptance #9 (PREVIEW List-a-Lot button + Active Listings
subsection), #10 (BID_WINDOW player-seller suppression), #11
(LOT_RESOLUTION sold/withdrawn), #12 (POST_SESSION Sable line on
crew). All tests run against the AuctionView surface in isolation —
no engine wiring required.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    GameState,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import (
    AuctionLifecycle,
)
from spacegame.models.bidding_lot import LOT_CATEGORY_FACTION_COMMODITY, AuctionLot
from spacegame.models.crew import CrewRoster
from spacegame.models.player import Player
from spacegame.models.progression import PlayerProgression
from spacegame.models.ship import Ship
from spacegame.views.auction_view import AuctionSubstate, AuctionView


def _make_env(*, stellaris_rep: int = 10) -> tuple[pygame_gui.UIManager, Player]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Captain Test",
        credits=100_000,
        current_system_id="stellaris_port",
        ship=ship,
    )
    player.faction_reputation["stellaris_commerce_guild"] = stellaris_rep
    return manager, player


def _make_view(
    manager: pygame_gui.UIManager, player: Player, *, venue_id: str = "stellaris"
) -> AuctionView:
    return AuctionView(
        ui_manager=manager,
        player=player,
        crew_roster=CrewRoster(templates={}),
        progression=PlayerProgression(),
        venue_id=venue_id,
    )


def _player_lot() -> AuctionLot:
    return AuctionLot(
        id="player_listing_test_1",
        headline="Consigned: Axiom Circuit",
        description="A consigned circuit. Quietly listed.",
        category=LOT_CATEGORY_FACTION_COMMODITY,
        venue="stellaris",
        base_appraisal=8000,
        reserve_pct=0.7,
        seller_id="player",
    )


class TestPreviewListingAffordances:
    def test_button_renders_when_regular_at_stellaris(self) -> None:
        manager, player = _make_env(stellaris_rep=10)
        view = _make_view(manager, player)
        view.on_enter()
        assert view.list_a_lot_button is not None

    def test_button_absent_when_apprentice(self) -> None:
        manager, player = _make_env(stellaris_rep=-10)
        view = _make_view(manager, player)
        view.on_enter()
        assert view.list_a_lot_button is None

    def test_button_absent_when_reach(self) -> None:
        manager, player = _make_env(stellaris_rep=10)
        view = _make_view(manager, player, venue_id="crimson_reach")
        view.on_enter()
        assert view.list_a_lot_button is None

    def test_button_routes_to_sell_lot(self) -> None:
        manager, player = _make_env(stellaris_rep=10)
        view = _make_view(manager, player)
        view.on_enter()
        # Simulate a button press.
        assert view.list_a_lot_button is not None
        view._handle_button(view.list_a_lot_button)
        assert view.next_state == GameState.SELL_LOT


class TestActiveListingsSubsection:
    def test_renders_one_row_per_listing(self) -> None:
        manager, player = _make_env(stellaris_rep=10)
        # Stock a cargo + listing.
        player.ship.add_cargo("axiom_circuit", 4, price_per_unit=1500)
        player.auction_state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.7,
            current_day=1,
        )
        view = _make_view(manager, player)
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        # Should render without raising.
        view.render(screen)
        # Composition method: returns 1 row per listing.
        rows = view.active_listing_rows()
        assert len(rows) == 1


class TestBidWindowPlayerSeller:
    def _set_up_player_lot_session(self, view: AuctionView, player: Player) -> None:
        state = player.auction_state
        state.enter_preview(
            venue_id="stellaris",
            session_lots=[_player_lot()],
            rival_ids=["ai_buyer_alpha"],
            session_id="test_session",
        )
        state.open_session()
        if state.round_state is not None:
            state.round_state.bidders_active.add("ai_buyer_alpha")

    def test_bid_buttons_suppressed_for_player_seller(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        self._set_up_player_lot_session(view, player)
        view._rebuild_ui_for_substate()
        # Suppression: raise/hold/fold buttons must NOT exist.
        assert view.raise_min_button is None
        assert view.hold_button is None
        assert view.fold_button is None

    def test_your_lot_banner_renders(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        self._set_up_player_lot_session(view, player)
        view._rebuild_ui_for_substate()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)  # must not raise
        assert "Your lot" in view.player_seller_banner_text()

    def test_catalog_lot_keeps_bid_buttons(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        # A catalog lot (no seller_id) should keep the standard UI.
        catalog_lot = AuctionLot(
            id="catalog_x",
            headline="Catalog Lot",
            description="x",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue="stellaris",
            base_appraisal=8000,
            reserve_pct=0.7,
        )
        state = player.auction_state
        state.enter_preview(
            venue_id="stellaris",
            session_lots=[catalog_lot],
            rival_ids=["ai_buyer_alpha"],
            session_id="test_session",
        )
        state.open_session()
        view._rebuild_ui_for_substate()
        assert view.raise_min_button is not None


class TestLotResolutionPlayerSeller:
    def test_sold_message_for_player_seller(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        msg = view._lot_resolution_message_for_player_lot(sold=True, sale_price=8200)
        assert "8,200" in msg
        assert "Sold" in msg

    def test_withdrawn_message_for_player_seller(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        msg = view._lot_resolution_message_for_player_lot(sold=False, sale_price=0)
        assert "Reserve" in msg or "returns" in msg.lower()


class TestPostSessionPlayerListing:
    def test_sable_line_renders_when_listing_resolved(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        view.set_voice_templates(
            {
                "player_listing_post_session": {
                    "sold_above_reserve": "The room paid past the reserve. The lot read true and the credits cleared.",
                    "sold_near_reserve": "Hammer landed near the reserve. The room held the price you set.",
                    "withdrawn_no_bids": "No buyers stepped to the floor. The catalogue carried other lots.",
                    "withdrawn_bids_below_reserve": "Bids came in. None reached the reserve. The room held its limit.",
                }
            }
        )
        # Pretend a sold-above-reserve player resolution happened.
        line = view._sable_player_listing_line(
            outcome="sold", sale_price=10_000, reserve_price=5_600, sable_active=True
        )
        assert "reserve" in line.lower()

    def test_no_line_when_no_listing_resolved(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        # No active listing in history, returns empty string.
        line = view._sable_player_listing_line(
            outcome=None, sale_price=0, reserve_price=0, sable_active=True
        )
        assert line == ""

    def test_no_line_when_sable_off_crew(self) -> None:
        manager, player = _make_env()
        view = _make_view(manager, player)
        view.on_enter()
        line = view._sable_player_listing_line(
            outcome="sold", sale_price=10_000, reserve_price=5_600, sable_active=False
        )
        assert line == ""
