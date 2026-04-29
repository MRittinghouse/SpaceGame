"""SA-B5: Player-listing model tests.

Covers ``AuctionLot.seller_id`` field; ``_PlayerListing`` schema and
serialization; ``AuctionState.create_listing`` / ``cancel_listing`` /
``eligible_listings_for_session`` semantics; player-seller lot
resolution; save/load migration discipline per design doc §8.3.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from spacegame import config
from spacegame.constants.flags import (
    auction_first_listing_created,
    auction_first_listing_withdrawn,
    auction_first_sale,
    seen_first_listing_tip,
)
from spacegame.models.bidding import (
    AuctionLifecycle,
    AuctionState,
)
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_FACTION_COMMODITY,
    REP_TIER_REGULAR,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _make_basic_ship() -> Ship:
    """Build a Ship with enough cargo capacity for the listing tests."""
    ship_type = ShipType(
        id="testbed",
        name="Testbed",
        ship_class="starter",
        description="",
        cargo_capacity=50,
        fuel_capacity=100,
        fuel_efficiency=1,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="common",
    )
    return Ship(ship_type=ship_type, current_fuel=100)


def _make_player(*, credits: int = 100_000, stellaris_rep: int = 10) -> Player:
    """Construct a regular-tier (rep=10) Stellaris-credentialed player."""
    ship = _make_basic_ship()
    player = Player(
        name="Captain Test",
        credits=credits,
        current_system_id="stellaris_port",
        ship=ship,
    )
    player.faction_reputation["stellaris_commerce_guild"] = stellaris_rep
    # Stock the cargo so listing eligibility tests have material.
    player.ship.add_cargo("axiom_circuit", 4, price_per_unit=1500)
    player.parts_inventory["mining_laser_mk2"] = 2
    return player


# ---------------------------------------------------------------------
# AuctionLot.seller_id
# ---------------------------------------------------------------------


class TestSellerIdField:
    def test_default_is_none(self) -> None:
        lot = AuctionLot(
            id="x",
            headline="X",
            description="x",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue=VENUE_STELLARIS,
            base_appraisal=1000,
            reserve_pct=0.7,
        )
        assert lot.seller_id is None

    def test_to_dict_omits_when_none(self) -> None:
        lot = AuctionLot(
            id="x",
            headline="X",
            description="x",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue=VENUE_STELLARIS,
            base_appraisal=1000,
            reserve_pct=0.7,
        )
        assert "seller_id" not in lot.to_dict()

    def test_to_dict_emits_when_player(self) -> None:
        lot = AuctionLot(
            id="x",
            headline="X",
            description="x",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue=VENUE_STELLARIS,
            base_appraisal=1000,
            reserve_pct=0.7,
            seller_id="player",
        )
        d = lot.to_dict()
        assert d["seller_id"] == "player"

    def test_from_dict_round_trip_with_seller(self) -> None:
        data = {
            "id": "x",
            "headline": "X",
            "description": "x",
            "category": LOT_CATEGORY_FACTION_COMMODITY,
            "venue": VENUE_STELLARIS,
            "base_appraisal": 1000,
            "reserve_pct": 0.7,
            "seller_id": "player",
        }
        lot = AuctionLot.from_dict(data)
        assert lot.seller_id == "player"
        round_trip = AuctionLot.from_dict(lot.to_dict())
        assert round_trip.seller_id == "player"

    def test_from_dict_round_trip_without_seller(self) -> None:
        data = {
            "id": "x",
            "headline": "X",
            "description": "x",
            "category": LOT_CATEGORY_FACTION_COMMODITY,
            "venue": VENUE_STELLARIS,
            "base_appraisal": 1000,
            "reserve_pct": 0.7,
        }
        lot = AuctionLot.from_dict(data)
        assert lot.seller_id is None

    def test_existing_catalog_loads_unchanged(self) -> None:
        """SA-B3 / SA-B4 catalog files load with seller_id=None."""
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        for venue in ("stellaris", "crimson_reach"):
            file_path = repo_root / "data" / "auctions" / f"{venue}_lots.json"
            if not file_path.exists():
                continue
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            for raw in data.get("lots", []):
                lot = AuctionLot.from_dict(raw)
                assert lot.seller_id is None, (
                    f"{venue} catalog lot {raw.get('id')} should not declare seller_id"
                )


# ---------------------------------------------------------------------
# Listing economics constants
# ---------------------------------------------------------------------


class TestListingEconomics:
    def test_constants_match_locked_decisions(self) -> None:
        assert config.MAX_ACTIVE_LISTINGS == 3
        assert abs(config.LISTING_FEE_RATE - 0.05) < 1e-9
        assert config.LISTING_FEE_FLOOR == 100
        assert abs(config.LISTING_RESERVE_PCT_MIN - 0.50) < 1e-9
        assert abs(config.LISTING_RESERVE_PCT_MAX - 0.95) < 1e-9
        assert abs(config.LISTING_RESERVE_PCT_DEFAULT - 0.70) < 1e-9
        assert config.LISTING_TIER_REQUIRED == "regular"

    def test_sell_lot_state_exists(self) -> None:
        from spacegame.config import GameState

        assert GameState.SELL_LOT.value == "sell_lot"


# ---------------------------------------------------------------------
# Flag helpers
# ---------------------------------------------------------------------


class TestPlayerListingFlags:
    def test_seen_first_listing_tip(self) -> None:
        assert seen_first_listing_tip() == "seen_first_listing_tip"

    def test_first_listing_created(self) -> None:
        assert auction_first_listing_created() == "auction_first_listing_created"

    def test_first_sale(self) -> None:
        assert auction_first_sale() == "auction_first_sale"

    def test_first_listing_withdrawn(self) -> None:
        assert auction_first_listing_withdrawn() == "auction_first_listing_withdrawn"


# ---------------------------------------------------------------------
# _PlayerListing dataclass
# ---------------------------------------------------------------------


def _make_listing(
    *,
    listing_id: str = "listing_1",
    item_kind: str = "commodity",
    item_id: str = "axiom_circuit",
    quantity: int = 1,
    declared_appraisal: int = 8000,
    reserve_pct: float = 0.70,
    listing_fee_paid: int = 400,
    listed_on_day: int = 1,
):
    from spacegame.models.bidding import _PlayerListing

    return _PlayerListing(
        listing_id=listing_id,
        item_kind=item_kind,
        item_id=item_id,
        quantity=quantity,
        declared_appraisal=declared_appraisal,
        reserve_pct=reserve_pct,
        listing_fee_paid=listing_fee_paid,
        listed_on_day=listed_on_day,
        headline="Axiom Circuit (1 unit)",
        description="A consigned circuit. Quietly listed.",
        category=LOT_CATEGORY_FACTION_COMMODITY,
    )


class TestPlayerListingDataclass:
    def test_round_trip(self) -> None:
        from spacegame.models.bidding import _PlayerListing

        listing = _make_listing()
        d = listing.to_dict()
        restored = _PlayerListing.from_dict(d)
        assert restored == listing

    def test_to_auction_lot_marks_seller_player(self) -> None:
        listing = _make_listing()
        lot = listing.to_auction_lot()
        assert lot.seller_id == "player"
        assert lot.venue == VENUE_STELLARIS
        assert lot.base_appraisal == listing.declared_appraisal
        assert lot.headline == listing.headline
        assert lot.contraband is False
        assert lot.is_headliner is False
        assert lot.rep_tier_required == REP_TIER_REGULAR


# ---------------------------------------------------------------------
# Listing fee math
# ---------------------------------------------------------------------


class TestListingFeeMath:
    @pytest.mark.parametrize(
        "appraisal,expected",
        [
            (0, 100),
            (1, 100),
            (1999, 100),
            (2000, 100),
            (2001, 100),
            (50_000, 2_500),
            (1_000_000, 50_000),
        ],
    )
    def test_fee_floor_and_rate(self, appraisal: int, expected: int) -> None:
        from spacegame.models.bidding import compute_listing_fee

        assert compute_listing_fee(appraisal) == expected


# ---------------------------------------------------------------------
# AuctionState.create_listing
# ---------------------------------------------------------------------


class TestCreateListingValidation:
    def test_invalid_kind_returns_false(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg, _listing = state.create_listing(
            player=player,
            item_kind="weapon",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert not ok
        assert "kind" in msg.lower() or "item kind" in msg.lower()
        assert _listing is None
        # No state mutation.
        assert player.credits == 100_000
        assert state.active_listings == []
        assert player.ship.get_cargo_quantity("axiom_circuit") == 4

    def test_missing_inventory_returns_false(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg, _listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=99,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert not ok
        assert "inventory" in msg.lower() or "not enough" in msg.lower()
        assert _listing is None

    def test_appraisal_must_be_positive(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg, _listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=0,
            reserve_pct=0.70,
            current_day=1,
        )
        assert not ok
        assert "appraisal" in msg.lower()

    def test_reserve_pct_below_floor_rejected(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg, _ = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.40,
            current_day=1,
        )
        assert not ok
        assert "reserve" in msg.lower()

    def test_reserve_pct_above_ceiling_rejected(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg, _ = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.99,
            current_day=1,
        )
        assert not ok
        assert "reserve" in msg.lower()

    def test_slot_full_rejected(self) -> None:
        player = _make_player()
        state = player.auction_state
        # Pre-stock the ship + listings to fill slots.
        player.ship.add_cargo("axiom_circuit", 6, price_per_unit=1500)
        for i in range(config.MAX_ACTIVE_LISTINGS):
            ok, _, _ = state.create_listing(
                player=player,
                item_kind="commodity",
                item_id="axiom_circuit",
                quantity=1,
                declared_appraisal=8000,
                reserve_pct=0.70,
                current_day=1,
            )
            assert ok, f"listing {i} should succeed"
        # The 4th listing should fail.
        ok, msg, _ = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert not ok
        assert "slot" in msg.lower() or "limit" in msg.lower() or "active" in msg.lower()

    def test_tier_below_regular_rejected(self) -> None:
        player = _make_player(stellaris_rep=-10)  # apprentice
        state = player.auction_state
        ok, msg, _ = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert not ok
        assert "regular" in msg.lower() or "standing" in msg.lower() or "tier" in msg.lower()

    def test_insufficient_credits_for_fee_rejected(self) -> None:
        player = _make_player(credits=200)  # fee on 8000 = 400.
        state = player.auction_state
        ok, msg, _ = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert not ok
        assert "credits" in msg.lower() or "fee" in msg.lower()

    def test_success_deducts_fee_and_item(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg, listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=3,
        )
        assert ok, msg
        assert listing is not None
        assert listing.item_id == "axiom_circuit"
        assert listing.listing_fee_paid == 400
        assert listing.listed_on_day == 3
        # Side effects.
        assert player.credits == 100_000 - 400
        assert player.ship.get_cargo_quantity("axiom_circuit") == 3
        assert state.active_listings == [listing]
        assert state.auction_listings_attempted == 1
        assert state.auction_listing_fees_paid == 400

    def test_success_for_part_inventory(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, _msg, listing = state.create_listing(
            player=player,
            item_kind="part",
            item_id="mining_laser_mk2",
            quantity=1,
            declared_appraisal=10_000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert ok
        assert listing is not None
        assert listing.item_kind == "part"
        assert player.parts_inventory["mining_laser_mk2"] == 1


class TestCancelListing:
    def test_cancel_returns_item_no_refund(self) -> None:
        player = _make_player()
        state = player.auction_state
        _ok, _, listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=2,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert listing is not None
        ok, msg = state.cancel_listing(listing.listing_id, player)
        assert ok, msg
        # Item back in inventory.
        assert player.ship.get_cargo_quantity("axiom_circuit") == 4
        # Fee NOT refunded.
        assert player.credits == 100_000 - 400
        assert state.active_listings == []

    def test_cancel_unknown_listing_fails(self) -> None:
        player = _make_player()
        state = player.auction_state
        ok, msg = state.cancel_listing("does_not_exist", player)
        assert not ok
        assert "not found" in msg.lower() or "no such" in msg.lower()

    def test_cancel_blocked_when_lot_on_active_floor(self) -> None:
        """Listing already converted to a session lot cannot be cancelled (AC #5)."""
        player = _make_player()
        state = player.auction_state
        ok, _, listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert listing is not None
        # Simulate the listing being pulled into a live session by adding
        # the converted lot to active_session_lots directly.

        floor_lot = listing.to_auction_lot()
        state.active_session_lots.append(floor_lot)
        # Cancellation must now fail with the "on floor" message.
        ok, msg = state.cancel_listing(listing.listing_id, player)
        assert not ok
        assert "auction floor" in msg.lower() or "cannot cancel" in msg.lower()
        # The listing must remain in active_listings (not returned early).
        assert any(l.listing_id == listing.listing_id for l in state.active_listings)


class TestEligibleListings:
    def test_returns_listings_listed_on_or_before_current_day(self) -> None:
        player = _make_player()
        player.ship.add_cargo("axiom_circuit", 3, price_per_unit=1500)
        state = player.auction_state
        # Day 1, day 2, day 3.
        for day in (1, 2, 3):
            ok, _, _ = state.create_listing(
                player=player,
                item_kind="commodity",
                item_id="axiom_circuit",
                quantity=1,
                declared_appraisal=8000,
                reserve_pct=0.70,
                current_day=day,
            )
            assert ok
        eligible = state.eligible_listings_for_session(current_day=2)
        assert len(eligible) == 2

    def test_returns_at_most_max_active(self) -> None:
        player = _make_player()
        state = player.auction_state
        player.ship.add_cargo("axiom_circuit", 6, price_per_unit=1500)
        for _i in range(config.MAX_ACTIVE_LISTINGS):
            state.create_listing(
                player=player,
                item_kind="commodity",
                item_id="axiom_circuit",
                quantity=1,
                declared_appraisal=8000,
                reserve_pct=0.70,
                current_day=1,
            )
        eligible = state.eligible_listings_for_session(current_day=10)
        assert len(eligible) <= config.MAX_ACTIVE_LISTINGS


# ---------------------------------------------------------------------
# Player-seller resolution
# ---------------------------------------------------------------------


def _drive_auction_to_session(state: AuctionState, lots: list[AuctionLot]) -> None:
    """Helper: prepare a session and open the first lot.

    Adds a synthetic ``ai_buyer_alpha`` to the active-bidders set so the
    test can drive bids without spinning up the full persona infrastructure.
    """
    state.enter_preview(
        venue_id=VENUE_STELLARIS,
        session_lots=lots,
        rival_ids=["ai_buyer_alpha"],
        session_id="seller_session",
    )
    state.open_session()
    rs = state.round_state
    if rs is not None:
        rs.bidders_active.add("ai_buyer_alpha")


class TestResolvePlayerLot:
    def test_sold_archives_and_increments_counter(self) -> None:
        player = _make_player()
        state = player.auction_state
        _ok, _, listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert listing is not None
        lot = listing.to_auction_lot()
        _drive_auction_to_session(state, [lot])
        assert state.lifecycle == AuctionLifecycle.BID_WINDOW
        rs = state.round_state
        assert rs is not None
        # Force a sale at hammer above reserve via the round state. The
        # opening bid floor is reserve + min_increment, so we need to
        # land another min_increment above that to satisfy
        # ``submit_bid``'s ``current_high_bid + round_min_increment`` gate.
        bid_amount = rs.current_high_bid + rs.round_min_increment + 200
        ok, _ = rs.submit_bid("ai_buyer_alpha", bid_amount)
        assert ok
        # Manually drive the lot to resolution.
        msg = state._resolve_lot()
        assert "Sold" in msg or "sold" in msg.lower()
        assert state.auction_listings_sold == 1
        # Listing moved out of active_listings, into history.
        assert state.active_listings == []
        assert len(state.listing_history) == 1
        assert state.listing_history[0]["outcome"] == "sold"
        assert state.listing_history[0]["sale_price"] >= lot.reserve_price

    def test_withdrawn_archives_without_incrementing_sold(self) -> None:
        player = _make_player()
        state = player.auction_state
        _ok, _, listing = state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=1,
        )
        assert listing is not None
        lot = listing.to_auction_lot()
        _drive_auction_to_session(state, [lot])
        # Drop a low bid (still under reserve). Force the high bid back
        # below the reserve so the resolution path takes the withdrawn
        # branch rather than the sold branch.
        rs = state.round_state
        assert rs is not None
        ok, _ = rs.submit_bid("ai_buyer_alpha", rs.current_high_bid + rs.round_min_increment)
        assert ok
        rs.current_high_bid = lot.reserve_price - 1
        msg = state._resolve_lot()
        assert "withdrawn" in msg.lower() or "reserve" in msg.lower()
        assert state.auction_listings_sold == 0
        assert state.active_listings == []
        assert state.listing_history[-1]["outcome"] == "withdrawn"


# ---------------------------------------------------------------------
# AuctionState save/load migration
# ---------------------------------------------------------------------


class TestAuctionStateMigration:
    def test_old_save_loads_with_safe_defaults(self) -> None:
        old_save = {
            "pending_lot_pool": [],
            "active_auction_id": None,
            "active_session_id": None,
            "active_session_lots": [],
            "active_round": 0,
            "active_lot_index": 0,
            "session_history": [],
            "last_auction_day": {},
            "next_auction_day": {},
            "recent_bid_categories": [],
            "rival_session_attendance": {},
            "won_lots": [],
            "speed_setting": "normal",
            "lifecycle": "scheduled",
            "round_state": None,
            "session_personas": [],
            "session_lot_results": [],
            "seconds_since_last_bid": 0.0,
            "auction_lots_won_total": 0,
            "auction_lots_won_stellaris": 0,
            "auction_rivals_retired": 0,
            "auction_perfect_reads": 0,
        }
        loaded = AuctionState.from_dict(old_save)
        assert loaded.active_listings == []
        assert loaded.listing_history == []
        assert loaded.auction_listings_sold == 0
        assert loaded.auction_listings_attempted == 0
        assert loaded.auction_listing_fees_paid == 0

    def test_round_trip_preserves_listings(self) -> None:
        player = _make_player()
        state = player.auction_state
        state.create_listing(
            player=player,
            item_kind="commodity",
            item_id="axiom_circuit",
            quantity=1,
            declared_appraisal=8000,
            reserve_pct=0.70,
            current_day=2,
        )
        d = state.to_dict()
        restored = AuctionState.from_dict(d)
        assert len(restored.active_listings) == 1
        assert restored.active_listings[0].item_id == "axiom_circuit"
        assert restored.auction_listings_attempted == 1
        assert restored.auction_listing_fees_paid == 400


# ---------------------------------------------------------------------
# Player.auction_listings_sold property
# ---------------------------------------------------------------------


class TestPlayerListingProperty:
    def test_property_mirrors_state(self) -> None:
        player = _make_player()
        assert player.auction_listings_sold == 0
        player.auction_state.auction_listings_sold = 7
        assert player.auction_listings_sold == 7
