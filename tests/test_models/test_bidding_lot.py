"""SA-B2: AuctionLot dataclass + categories + serialization tests."""

from __future__ import annotations

import dataclasses

import pytest

from spacegame.models.bidding_lot import (
    LOT_CATEGORIES,
    LOT_CATEGORY_ANTIQUITY,
    LOT_CATEGORY_CONTRABAND,
    LOT_CATEGORY_DERELICT_RIGHTS,
    LOT_CATEGORY_FACTION_COMMODITY,
    LOT_CATEGORY_MODULE,
    LOT_CATEGORY_RARE_UPGRADE,
    LOT_CATEGORY_RESTRICTED_WEAPON,
    LOT_CATEGORY_SALVAGE_LOT,
    REP_TIER_APPRENTICE,
    REP_TIER_CERTIFIED,
    REP_TIER_NONE,
    REP_TIER_PATRON,
    REP_TIER_REGULAR,
    VENUE_CRIMSON_REACH,
    VENUE_STELLARIS,
    AuctionLot,
    rep_tier_at_least,
)


def _make_kings_repeater() -> AuctionLot:
    """Worked example 1 from design doc §3.4 — Stellaris headliner."""
    return AuctionLot(
        id="kings_repeater_reissue_lot_2332",
        headline="The King's Repeater (Re-issue, Documented)",
        description="Stellaris Engineering ran twelve re-issues. Provenance documented.",
        category=LOT_CATEGORY_MODULE,
        venue=VENUE_STELLARIS,
        base_appraisal=28000,
        reserve_pct=0.75,
        rep_tier_required=REP_TIER_CERTIFIED,
        is_headliner=True,
        source_module_id="legendary_kings_repeater",
    )


def _make_axiom_array() -> AuctionLot:
    """Worked example 2 from design doc §3.4 — Stellaris faction-gated lot."""
    return AuctionLot(
        id="axiom_nav_array_lot_14c",
        headline="Axiom-Series Navigational Array (Series C, Lot 14)",
        description="Fourteen units certified under Axiom Labs' export license.",
        category=LOT_CATEGORY_FACTION_COMMODITY,
        venue=VENUE_STELLARIS,
        base_appraisal=8500,
        reserve_pct=0.82,
        faction_gate="commerce_guild",
        rep_tier_required=REP_TIER_REGULAR,
    )


def _make_reach_contraband() -> AuctionLot:
    """Worked example 3 from design doc §3.4 — Reach contraband lot."""
    return AuctionLot(
        id="unstamped_fuel_additive_lot_reach_88",
        headline="Unstamped Fuel Additives (4 units, mixed grade)",
        description="Four canisters. Two Navigator-grade. Two unclassified.",
        category=LOT_CATEGORY_CONTRABAND,
        venue=VENUE_CRIMSON_REACH,
        base_appraisal=6000,
        reserve_pct=0.65,
        rep_tier_required=REP_TIER_APPRENTICE,
        contraband=True,
    )


class TestAuctionLotCategoryConstants:
    def test_all_category_constants_present(self) -> None:
        assert LOT_CATEGORY_MODULE == "module"
        assert LOT_CATEGORY_ANTIQUITY == "antiquity"
        assert LOT_CATEGORY_FACTION_COMMODITY == "faction_commodity"
        assert LOT_CATEGORY_RARE_UPGRADE == "rare_upgrade"
        assert LOT_CATEGORY_DERELICT_RIGHTS == "derelict_rights"
        assert LOT_CATEGORY_CONTRABAND == "contraband"
        assert LOT_CATEGORY_RESTRICTED_WEAPON == "restricted_weapon"
        assert LOT_CATEGORY_SALVAGE_LOT == "salvage_lot"

    def test_category_set_has_eight_entries(self) -> None:
        assert len(LOT_CATEGORIES) == 8
        assert LOT_CATEGORY_MODULE in LOT_CATEGORIES
        assert LOT_CATEGORY_SALVAGE_LOT in LOT_CATEGORIES


class TestAuctionLotSchema:
    def test_required_fields_present(self) -> None:
        lot = _make_kings_repeater()
        assert lot.id == "kings_repeater_reissue_lot_2332"
        assert lot.category == LOT_CATEGORY_MODULE
        assert lot.venue == VENUE_STELLARIS
        assert lot.base_appraisal == 28000

    def test_default_optional_fields(self) -> None:
        lot = AuctionLot(
            id="x",
            headline="X",
            description="x.",
            category=LOT_CATEGORY_MODULE,
            venue=VENUE_STELLARIS,
            base_appraisal=1000,
            reserve_pct=0.7,
        )
        assert lot.faction_gate is None
        assert lot.rep_tier_required == REP_TIER_NONE
        assert lot.is_headliner is False
        assert lot.season_tag is None
        assert lot.contraband is False
        assert lot.source_module_id is None
        assert lot.recently_seen_count == 0

    def test_lot_is_frozen(self) -> None:
        lot = _make_kings_repeater()
        with pytest.raises(dataclasses.FrozenInstanceError):
            lot.base_appraisal = 99999  # type: ignore[misc]


class TestReservePrice:
    def test_kings_repeater_reserve_matches_design_doc(self) -> None:
        """Design doc §3.4 example 1: 0.75 * 28000 = 21000."""
        lot = _make_kings_repeater()
        assert lot.reserve_price == 21000

    def test_axiom_reserve_matches_design_doc(self) -> None:
        """Design doc §3.4 example 2: 0.82 * 8500 = 6970."""
        lot = _make_axiom_array()
        assert lot.reserve_price == 6970

    def test_reach_contraband_reserve_matches_design_doc(self) -> None:
        """Design doc §3.4 example 3: 0.65 * 6000 = 3900."""
        lot = _make_reach_contraband()
        assert lot.reserve_price == 3900

    def test_reserve_truncates_not_rounds(self) -> None:
        """``int(8500 * 0.81) = 6885``, not 6886. Truncation matches the doc."""
        lot = AuctionLot(
            id="x",
            headline="X",
            description="x.",
            category=LOT_CATEGORY_MODULE,
            venue=VENUE_STELLARIS,
            base_appraisal=8500,
            reserve_pct=0.81,
        )
        assert lot.reserve_price == int(8500 * 0.81)


class TestRecentlySeenMutationViaReplace:
    def test_with_recently_seen_increments(self) -> None:
        lot = _make_kings_repeater()
        bumped = lot.with_recently_seen(lot.recently_seen_count + 1)
        assert lot.recently_seen_count == 0  # Original untouched (frozen).
        assert bumped.recently_seen_count == 1
        # All other fields preserved.
        assert bumped.id == lot.id
        assert bumped.base_appraisal == lot.base_appraisal

    def test_dataclasses_replace_works_on_frozen_lot(self) -> None:
        lot = _make_kings_repeater()
        bumped = dataclasses.replace(lot, recently_seen_count=4)
        assert bumped.recently_seen_count == 4
        assert lot.recently_seen_count == 0


class TestAuctionLotSerialization:
    def test_round_trip_preserves_all_fields(self) -> None:
        lot = _make_kings_repeater()
        d = lot.to_dict()
        restored = AuctionLot.from_dict(d)
        assert restored == lot

    def test_round_trip_for_reach_contraband(self) -> None:
        lot = _make_reach_contraband()
        d = lot.to_dict()
        restored = AuctionLot.from_dict(d)
        assert restored == lot

    def test_from_dict_uses_defaults_for_missing_optional_fields(self) -> None:
        minimal = {
            "id": "minimal",
            "headline": "Minimal Lot",
            "description": "minimal.",
            "category": LOT_CATEGORY_MODULE,
            "venue": VENUE_STELLARIS,
            "base_appraisal": 1000,
            "reserve_pct": 0.7,
        }
        lot = AuctionLot.from_dict(minimal)
        assert lot.faction_gate is None
        assert lot.rep_tier_required == REP_TIER_NONE
        assert lot.is_headliner is False
        assert lot.recently_seen_count == 0


class TestRepTierComparison:
    @pytest.mark.parametrize(
        "player_tier,required_tier,expected",
        [
            (REP_TIER_NONE, REP_TIER_NONE, True),
            (REP_TIER_NONE, REP_TIER_APPRENTICE, False),
            (REP_TIER_REGULAR, REP_TIER_REGULAR, True),
            (REP_TIER_REGULAR, REP_TIER_CERTIFIED, False),
            (REP_TIER_CERTIFIED, REP_TIER_REGULAR, True),
            (REP_TIER_PATRON, REP_TIER_PATRON, True),
            (REP_TIER_PATRON, REP_TIER_APPRENTICE, True),
        ],
    )
    def test_tier_comparison(self, player_tier: str, required_tier: str, expected: bool) -> None:
        assert rep_tier_at_least(player_tier, required_tier) is expected

    def test_unknown_player_tier_falls_back_to_none(self) -> None:
        assert rep_tier_at_least("nonsense", REP_TIER_REGULAR) is False

    def test_unknown_required_tier_returns_false(self) -> None:
        assert rep_tier_at_least(REP_TIER_PATRON, "nonsense") is False
