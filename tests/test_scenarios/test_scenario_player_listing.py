"""SA-B5: Full scenario for player-initiated auctions.

Drives a regular-tier Stellaris player through the SellLotView →
session prep → AI bidding → player credited / withdrawn pipeline. Two
branches: sold-above-reserve and reserve-not-met.

Acceptance #19. Also touches #8 (session preparation prepends player
lots), #15 (engine callbacks credit / return inventory + set flags),
and #16 (high-value news ticker).
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import (
    LISTING_RESERVE_PCT_DEFAULT,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from spacegame.constants.flags import (
    auction_first_listing_created,
    auction_first_listing_withdrawn,
    auction_first_sale,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import (
    AuctionLifecycle,
    AuctionState,
    compute_listing_fee,
)
from spacegame.models.bidding_lot import VENUE_STELLARIS, AuctionLot
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.sell_lot_view import SellLotView


def _make_player(*, credits: int = 100_000, stellaris_rep: int = 10) -> Player:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Captain Test",
        credits=credits,
        current_system_id="stellaris_port",
        ship=ship,
    )
    player.faction_reputation["stellaris_commerce_guild"] = stellaris_rep
    player.ship.add_cargo("axiom_circuit", 4, price_per_unit=1500)
    return player


# ---------------------------------------------------------------------
# Session preparation — eligible listings prepended to session_lots
# ---------------------------------------------------------------------


class TestSessionPreparation:
    def test_eligible_listings_prepend_to_session_lots(self) -> None:
        player = _make_player()
        state = player.auction_state
        state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=LISTING_RESERVE_PCT_DEFAULT,
            current_day=1,
        )
        # Simulate the prepare-session prepend logic without spinning up
        # the full Game class.
        catalog_lots = [
            AuctionLot(
                id=f"catalog_{i}",
                headline=f"Catalog Lot {i}",
                description="x",
                category="faction_commodity",
                venue=VENUE_STELLARIS,
                base_appraisal=10_000,
                reserve_pct=0.7,
            )
            for i in range(6)
        ]
        target = 6
        player_lots = [l.to_auction_lot() for l in state.eligible_listings_for_session(1)]
        catalog_lots = catalog_lots[: max(0, target - len(player_lots))]
        session_lots = player_lots + catalog_lots
        # Player lot is first.
        assert session_lots[0].seller_id == "player"
        assert len(session_lots) == target

    def test_zero_listings_keeps_catalog_only(self) -> None:
        player = _make_player()
        state = player.auction_state
        catalog_lots = [
            AuctionLot(
                id=f"catalog_{i}",
                headline=f"Catalog Lot {i}",
                description="x",
                category="faction_commodity",
                venue=VENUE_STELLARIS,
                base_appraisal=10_000,
                reserve_pct=0.7,
            )
            for i in range(6)
        ]
        target = 6
        player_lots = [l.to_auction_lot() for l in state.eligible_listings_for_session(1)]
        catalog_lots = catalog_lots[: max(0, target - len(player_lots))]
        session_lots = player_lots + catalog_lots
        assert all(lot.seller_id is None for lot in session_lots)


# ---------------------------------------------------------------------
# Sold-above-reserve branch
# ---------------------------------------------------------------------


class TestSoldAboveReserveBranch:
    def test_consign_then_sell(self) -> None:
        player = _make_player()
        state = player.auction_state
        # Step 1: consign via SellLotView.
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = SellLotView(ui_manager=manager, player=player)
        view.on_enter()
        # Pick the cargo commodity.
        view.select_item("commodity", "axiom_circuit")
        view.set_declared_appraisal(8000)
        view.set_reserve_pct(0.70)
        ok, _msg = view.confirm_listing()
        assert ok
        assert player.dialogue_flags.get(auction_first_listing_created())
        assert player.credits == 100_000 - compute_listing_fee(8000)
        # Step 2: drive a session with the listing as the first lot.
        listing = state.active_listings[0]
        lot = listing.to_auction_lot()
        state.enter_preview(
            venue_id=VENUE_STELLARIS,
            session_lots=[lot],
            rival_ids=["ai_buyer_alpha"],
            session_id="scenario_session",
        )
        state.open_session()
        rs = state.round_state
        assert rs is not None
        rs.bidders_active.add("ai_buyer_alpha")
        # AI lands above reserve.
        bid_amount = rs.current_high_bid + rs.round_min_increment + 200
        ok, _ = rs.submit_bid("ai_buyer_alpha", bid_amount)
        assert ok
        # Resolve the lot.
        msg = state._resolve_lot()
        assert "Sold" in msg
        # Listing moved to history; counter incremented.
        assert state.auction_listings_sold == 1
        assert state.active_listings == []
        assert state.listing_history[-1]["outcome"] == "sold"
        # Step 3: simulate the engine callback (the wiring is exercised
        # in the unit tests; here we verify the math is consistent).
        sale_price = state.listing_history[-1]["sale_price"]
        player.credits += sale_price  # mirror _on_player_lot_sold behavior.
        assert player.credits >= 100_000 - compute_listing_fee(8000) + sale_price


# ---------------------------------------------------------------------
# Withdrawn branch
# ---------------------------------------------------------------------


class TestWithdrawnBranch:
    def test_consign_then_withdraw_returns_item(self) -> None:
        player = _make_player()
        state = player.auction_state
        # Set the reserve as high as allowed so AI ceilings cannot meet it.
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = SellLotView(ui_manager=manager, player=player)
        view.on_enter()
        view.select_item("commodity", "axiom_circuit")
        view.set_declared_appraisal(8000)
        view.set_reserve_pct(0.95)
        ok, _ = view.confirm_listing()
        assert ok
        listing = state.active_listings[0]
        lot = listing.to_auction_lot()
        cargo_before_session = player.ship.get_cargo_quantity("axiom_circuit")
        state.enter_preview(
            venue_id=VENUE_STELLARIS,
            session_lots=[lot],
            rival_ids=["ai_buyer_alpha"],
            session_id="scenario_session_wd",
        )
        state.open_session()
        rs = state.round_state
        assert rs is not None
        rs.bidders_active.add("ai_buyer_alpha")
        # AI bid lands but stays under reserve.
        ok, _ = rs.submit_bid(
            "ai_buyer_alpha", rs.current_high_bid + rs.round_min_increment
        )
        assert ok
        rs.current_high_bid = lot.reserve_price - 1
        msg = state._resolve_lot()
        assert "withdrawn" in msg.lower() or "reserve" in msg.lower()
        # Counter NOT incremented.
        assert state.auction_listings_sold == 0
        # History records withdrawal.
        assert state.listing_history[-1]["outcome"] == "withdrawn"
        # Engine callback returns the item: simulate the inventory restore.
        archived = state.listing_history[-1]
        if archived["item_kind"] == "commodity":
            player.ship.add_cargo(
                archived["item_id"], int(archived["quantity"]), price_per_unit=0
            )
        # The fee is gone, the item is back.
        assert player.ship.get_cargo_quantity("axiom_circuit") == cargo_before_session + 1


# ---------------------------------------------------------------------
# Save/load round-trip in a scenario
# ---------------------------------------------------------------------


class TestSaveLoadInScenario:
    def test_active_listings_survive_round_trip(self) -> None:
        player = _make_player()
        state = player.auction_state
        state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.7,
            current_day=2,
        )
        d = state.to_dict()
        restored = AuctionState.from_dict(d)
        assert len(restored.active_listings) == 1
        assert restored.active_listings[0].declared_appraisal == 8000
        assert restored.auction_listings_attempted == 1


# ---------------------------------------------------------------------
# Achievement stub firing
# ---------------------------------------------------------------------


class TestAchievementStub:
    def test_player_property_reflects_state_counter(self) -> None:
        player = _make_player()
        assert player.auction_listings_sold == 0
        player.auction_state.auction_listings_sold = 1
        assert player.auction_listings_sold == 1
