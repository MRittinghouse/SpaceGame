"""SA-B2: Save/load round-trip coverage for Player.auction_state.

Verifies:
  - A default player serializes/deserializes with an empty AuctionState.
  - A populated AuctionState (mid-session BID_WINDOW with one lot
    resolved + one in flight, plus pending pool) round-trips losslessly.
  - A legacy save predating SA-B2 (no ``auction_state`` key) loads with
    a default AuctionState (acceptance criterion 7).
"""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import (
    AuctionLifecycle,
    AuctionState,
    _LotResultRecord,
    _SessionHistoryEntry,
)
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_MODULE,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import PERSONA_PRENTISS
from spacegame.models.bidding_round import DEFAULT_SPEED_SETTING
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.save_manager import SaveManager


def _shuttle() -> Ship:
    dl = get_data_loader()
    dl.load_all()
    return Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)


def _round_trip(player: Player) -> Player:
    mgr = SaveManager()
    data = mgr._serialize_player(player)
    json_str = json.dumps(data)
    return mgr._deserialize_player(json.loads(json_str))


def _module_lot(lot_id: str) -> AuctionLot:
    return AuctionLot(
        id=lot_id,
        headline=f"Lot {lot_id}",
        description="--",
        category=LOT_CATEGORY_MODULE,
        venue=VENUE_STELLARIS,
        base_appraisal=12000,
        reserve_pct=0.75,
    )


class TestAuctionStateSaveLoad:
    def test_default_state_round_trips(self) -> None:
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="stellaris_port",
            ship=_shuttle(),
        )
        restored = _round_trip(player)
        assert isinstance(restored.auction_state, AuctionState)
        assert restored.auction_state.speed_setting == DEFAULT_SPEED_SETTING
        assert restored.auction_state.lifecycle == AuctionLifecycle.SCHEDULED
        assert restored.auction_state.pending_lot_pool == []

    def test_preview_with_pending_pool_round_trips(self) -> None:
        player = Player(
            name="Tester",
            credits=2000,
            current_system_id="stellaris_port",
            ship=_shuttle(),
        )
        player.auction_state.pending_lot_pool = [_module_lot("a"), _module_lot("b")]
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [_module_lot("a"), _module_lot("b")],
            rival_ids=[PERSONA_PRENTISS],
            session_id="sess1",
        )
        restored = _round_trip(player)
        st = restored.auction_state
        assert st.lifecycle == AuctionLifecycle.PREVIEW
        assert st.active_auction_id == VENUE_STELLARIS
        assert len(st.pending_lot_pool) == 2
        assert len(st.active_session_lots) == 2
        assert st.session_personas == [PERSONA_PRENTISS]

    def test_mid_session_bid_window_round_trips(self) -> None:
        player = Player(
            name="Tester",
            credits=2000,
            current_system_id="stellaris_port",
            ship=_shuttle(),
        )
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [_module_lot("a"), _module_lot("b")],
            rival_ids=[],
            session_id="sess_mid",
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        bid = player.auction_state.player_min_raise_amount()
        ok, _ = player.auction_state.submit_player_bid(bid)
        assert ok
        restored = _round_trip(player)
        st = restored.auction_state
        assert st.lifecycle == AuctionLifecycle.BID_WINDOW
        assert st.round_state is not None
        assert st.round_state.current_high_bidder_id == "player"
        assert st.round_state.current_high_bid == bid

    def test_post_session_close_round_trips(self) -> None:
        player = Player(
            name="Tester",
            credits=2000,
            current_system_id="stellaris_port",
            ship=_shuttle(),
        )
        st = player.auction_state
        st.last_auction_day["stellaris"] = 50
        st.next_auction_day["stellaris"] = 56
        st.won_lots = ["lot_x"]
        st.session_history.append(
            _SessionHistoryEntry(
                session_id="sess_done",
                venue_id=VENUE_STELLARIS,
                closed_on_day=50,
                lot_results=[
                    _LotResultRecord(
                        lot_id="lot_x",
                        sold=True,
                        winner_id="player",
                        sale_price=11500,
                        player_bid=True,
                        rivals_bid=[],
                    ),
                ],
                rival_ids=[],
            )
        )
        st.auction_lots_won_total = 1
        st.auction_lots_won_stellaris = 1
        restored = _round_trip(player)
        assert restored.auction_state.last_auction_day == {"stellaris": 50}
        assert restored.auction_state.next_auction_day == {"stellaris": 56}
        assert restored.auction_state.won_lots == ["lot_x"]
        assert restored.auction_state.session_history[0].lot_results[0].sold is True
        assert restored.auction_lots_won_total == 1
        assert restored.auction_lots_won_stellaris == 1

    def test_legacy_save_no_auction_state_key_loads_clean(self) -> None:
        """Acceptance criterion 7: pre-SA-B2 save deserializes with defaults."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        mgr = SaveManager()
        data = mgr._serialize_player(player)
        # Strip the SA-B2 key like a pre-SA-B2 save would have it.
        data.pop("auction_state", None)
        restored = mgr._deserialize_player(json.loads(json.dumps(data)))
        assert isinstance(restored.auction_state, AuctionState)
        assert restored.auction_state.lifecycle == AuctionLifecycle.SCHEDULED
        assert restored.auction_state.speed_setting == DEFAULT_SPEED_SETTING
        assert restored.auction_state.won_lots == []
        assert restored.auction_state.pending_lot_pool == []

    def test_speed_setting_persists_across_save_load(self) -> None:
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="stellaris_port",
            ship=_shuttle(),
        )
        player.auction_state.speed_setting = "fast"
        restored = _round_trip(player)
        assert restored.auction_state.speed_setting == "fast"
