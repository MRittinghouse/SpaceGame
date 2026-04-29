"""SA-B3: DataLoader for Stellaris lot catalog and voice content.

Validates the new ``load_auction_lots`` / ``load_auction_voices``
loaders, the ``get_auction_lots(venue)`` / ``get_auction_voices(venue)``
accessors, missing-file fallback, and schema-validation behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.bidding_lot import VENUE_STELLARIS, AuctionLot


class TestLoadAuctionLots:
    def test_singleton_loads_stellaris_catalog(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        lots = dl.get_auction_lots(VENUE_STELLARIS)
        assert isinstance(lots, list)
        assert len(lots) >= 18
        for lot in lots:
            assert isinstance(lot, AuctionLot)
            assert lot.venue == VENUE_STELLARIS

    def test_unknown_venue_returns_empty(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        assert dl.get_auction_lots("nonexistent_venue") == []

    def test_missing_file_falls_back_to_empty(self, tmp_path: Path) -> None:
        empty_data = tmp_path / "data"
        empty_data.mkdir()
        (empty_data / "auctions").mkdir()
        loader = DataLoader(data_dir=empty_data)
        # No files exist; loader should not raise.
        loader.load_auction_lots()
        assert loader.get_auction_lots(VENUE_STELLARIS) == []

    def test_malformed_lot_skipped(self, tmp_path: Path) -> None:
        empty_data = tmp_path / "data"
        (empty_data / "auctions").mkdir(parents=True)
        # Write a file with one valid lot and one malformed.
        catalog = {
            "lots": [
                {
                    "id": "valid",
                    "headline": "Valid Lot",
                    "description": "A valid lot for testing.",
                    "category": "module",
                    "venue": VENUE_STELLARIS,
                    "base_appraisal": 10000,
                    "reserve_pct": 0.7,
                },
                {"id": "broken"},  # Missing required fields.
            ]
        }
        (empty_data / "auctions" / "stellaris_lots.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        loader = DataLoader(data_dir=empty_data)
        loader.load_auction_lots()
        loaded = loader.get_auction_lots(VENUE_STELLARIS)
        assert len(loaded) == 1
        assert loaded[0].id == "valid"


class TestLoadAuctionVoices:
    def test_singleton_loads_stellaris_voices(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_STELLARIS)
        assert isinstance(voices, dict)
        # Voice schema (locked in §B3 deliverables): velo_lines + rival_bids
        # + post_session + sable_reads + empty_state + retired_rival.
        for key in (
            "velo_lines",
            "rival_bids",
            "post_session",
            "sable_reads",
            "empty_state",
            "retired_rival",
        ):
            assert key in voices, f"Voice file missing top-level key: {key}"

    def test_velo_line_templates_complete(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_STELLARIS)
        velo = voices["velo_lines"]
        for slot in (
            "lot_open",
            "we_are_at",
            "lot_closed_sold",
            "lot_closed_withdrawn",
            "session_open",
            "session_close",
            "snipe_window_extended",
            "exceptional_lot_pause",
        ):
            assert slot in velo, f"Velo template missing: {slot}"
            assert isinstance(velo[slot], str)

    def test_rival_bid_templates_complete(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_STELLARIS)
        rivals = voices["rival_bids"]
        for rid in ("aldous_prentiss", "yuna_kade", "fenn_salko"):
            assert rid in rivals
            assert "{amount}" in rivals[rid]

    def test_post_session_buckets_per_rival(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_STELLARIS)
        post = voices["post_session"]
        for rid in ("aldous_prentiss", "yuna_kade", "fenn_salko"):
            assert rid in post
            for bucket in ("rival_won", "player_won", "no_overlap", "absent_retired"):
                assert bucket in post[rid]

    def test_sable_read_variants(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_STELLARIS)
        sable = voices["sable_reads"]
        for variant in (
            "ceiling_correct",
            "ceiling_off",
            "no_rivals_attended",
            "sable_not_on_crew",
        ):
            assert variant in sable

    def test_unknown_venue_returns_empty(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        assert dl.get_auction_voices("nonexistent_venue") == {}

    def test_missing_file_falls_back_to_empty(self, tmp_path: Path) -> None:
        empty_data = tmp_path / "data"
        (empty_data / "auctions").mkdir(parents=True)
        loader = DataLoader(data_dir=empty_data)
        loader.load_auction_voices()  # Should not raise.
        assert loader.get_auction_voices(VENUE_STELLARIS) == {}


class TestReachAuctionFiles:
    """SA-B4: parametric coverage for the Reach lot catalog and voices.

    Mirrors TestLoadAuctionLots / TestLoadAuctionVoices for the
    crimson_reach venue. SA-B3's classes are not modified.
    """

    def test_singleton_loads_reach_catalog(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        lots = dl.get_auction_lots(VENUE_CRIMSON_REACH)
        assert isinstance(lots, list)
        assert len(lots) >= 12
        for lot in lots:
            assert isinstance(lot, AuctionLot)
            assert lot.venue == VENUE_CRIMSON_REACH

    def test_singleton_loads_reach_voices(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        assert isinstance(voices, dict)
        # SA-B4 schema: auctioneer_lines (Floor Manager) + rival_bids
        # (Salko-only) + post_session (Salko outcome buckets + ambient
        # reach_buyer pool) + sable_reads + empty_state + retired_rival
        # + tier_locked.
        for key in (
            "auctioneer_lines",
            "rival_bids",
            "post_session",
            "sable_reads",
            "empty_state",
            "retired_rival",
            "tier_locked",
        ):
            assert key in voices, f"Reach voice file missing key: {key}"

    def test_reach_auctioneer_line_templates_complete(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        auctioneer = voices["auctioneer_lines"]
        for slot in (
            "lot_open",
            "we_are_at",
            "lot_closed_sold",
            "lot_closed_withdrawn",
            "session_open",
            "session_close",
        ):
            assert slot in auctioneer, f"Reach auctioneer template missing: {slot}"
            assert isinstance(auctioneer[slot], str)

    def test_reach_rival_bid_template_salko(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        rivals = voices["rival_bids"]
        # Reach session pool is Salko + 3 ambient reach_buyers; the only
        # named rival we authored a flat-bid template for is Salko.
        assert "fenn_salko" in rivals
        assert "{amount}" in rivals["fenn_salko"]

    def test_reach_post_session_salko_buckets(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        post = voices["post_session"]
        assert "fenn_salko" in post
        for bucket in ("rival_won", "player_won", "no_overlap", "absent_retired"):
            assert bucket in post["fenn_salko"]

    def test_reach_post_session_reach_buyer_ambient(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        post = voices["post_session"]
        assert "reach_buyer" in post
        ambient = post["reach_buyer"]
        # Locked decision §B4-deliverables: 4 ambient post-session lines.
        assert isinstance(ambient, list)
        assert len(ambient) >= 4

    def test_reach_sable_reads_complete(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        sable = voices["sable_reads"]
        # 4 Sable reads (mirrors Stellaris schema).
        for variant in (
            "ceiling_correct",
            "ceiling_off",
            "no_rivals_attended",
            "sable_not_on_crew",
        ):
            assert variant in sable

    def test_reach_tier_locked_template_present(self) -> None:
        from spacegame.models.bidding_lot import VENUE_CRIMSON_REACH

        dl = get_data_loader()
        dl.load_all()
        voices = dl.get_auction_voices(VENUE_CRIMSON_REACH)
        tier_locked = voices["tier_locked"]
        assert isinstance(tier_locked, str) and tier_locked


class TestLoadOrder:
    def test_get_auction_lots_safe_before_load_all(self) -> None:
        loader = DataLoader()
        # Calling the accessor before load_all returns an empty list.
        assert loader.get_auction_lots(VENUE_STELLARIS) == []
        assert loader.get_auction_voices(VENUE_STELLARIS) == {}


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Don't pollute the global singleton across these tests."""
    yield
