"""SA-B4: Reach-specific bidding helpers and Reach lot catalog integrity.

Tests cover the new module-level helpers added in SA-B4 (none of which
modify SA-B2 / SA-B3 schemas):

* ``tier_ladder_for_venue(venue_id)`` -- venue-aware tier dispatch.
* ``_tier_distance(player_tier, required_tier, venue_id=...)`` -- ladder
  distance for the rep-tier weight multiplier.
* ``reach_session_due(state, current_day)`` -- demand-driven cadence.
* ``reach_advance_demand(state, current_day)`` -- per-day arrivals counter.
* ``wreckers_tier_for_membership(player)`` -- Player -> Wreckers' Guild
  tier-string adapter.

Plus catalog data integrity over ``data/auctions/crimson_reach_lots.json``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from spacegame.config import PROJECT_ROOT
from spacegame.models.bidding import (
    REACH_DEMAND_MAX_GAP_DAYS,
    REACH_DEMAND_PROBABILITY,
    REACH_SESSION_SIZE,
    AuctionState,
    _tier_distance,
    generate_lot_pool,
    reach_advance_demand,
    reach_session_due,
    tier_ladder_for_venue,
    wreckers_tier_for_membership,
)
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_CONTRABAND,
    LOT_CATEGORY_FACTION_COMMODITY,
    LOT_CATEGORY_RESTRICTED_WEAPON,
    LOT_CATEGORY_SALVAGE_LOT,
    VENUE_CRIMSON_REACH,
    AuctionLot,
)

REACH_CATEGORIES_LOCKED: frozenset[str] = frozenset(
    {
        LOT_CATEGORY_CONTRABAND,
        LOT_CATEGORY_RESTRICTED_WEAPON,
        LOT_CATEGORY_SALVAGE_LOT,
        LOT_CATEGORY_FACTION_COMMODITY,
    }
)

REACH_TIER_LADDER: tuple[str, ...] = ("none", "apprentice", "journeyman", "master")
STELLARIS_TIER_LADDER: tuple[str, ...] = (
    "none",
    "apprentice",
    "regular",
    "certified",
    "patron",
)


def _make_reach_lot(
    *,
    lot_id: str,
    rep_tier_required: str,
    category: str = LOT_CATEGORY_SALVAGE_LOT,
    is_headliner: bool = False,
    season_tag: Any = None,
    base_appraisal: int = 8000,
    reserve_pct: float = 0.7,
) -> AuctionLot:
    return AuctionLot(
        id=lot_id,
        headline=lot_id.replace("_", " ").title(),
        description="Test fixture for Reach lot.",
        category=category,
        venue=VENUE_CRIMSON_REACH,
        base_appraisal=base_appraisal,
        reserve_pct=reserve_pct,
        rep_tier_required=rep_tier_required,
        is_headliner=is_headliner,
        season_tag=season_tag,
    )


class TestTierLadderForVenue:
    """AC3: tier_ladder_for_venue dispatches per venue."""

    def test_stellaris_ladder_unchanged(self) -> None:
        assert tier_ladder_for_venue("stellaris") == STELLARIS_TIER_LADDER

    def test_reach_ladder(self) -> None:
        assert tier_ladder_for_venue("crimson_reach") == REACH_TIER_LADDER

    def test_unknown_venue_falls_back_to_stellaris(self) -> None:
        # Conservative default: unknown venues use the legacy Stellaris ladder
        # so SA-B3 callers that never pass venue_id keep their behavior.
        assert tier_ladder_for_venue("not_a_venue") == STELLARIS_TIER_LADDER


class TestTierDistanceVenueAware:
    """AC3: _tier_distance dispatches per venue and SA-B3 behavior is preserved."""

    def test_stellaris_default_unchanged(self) -> None:
        # Existing SA-B3 callers don't pass venue_id; default keeps their math.
        assert _tier_distance("patron", "regular") == 2
        assert _tier_distance("regular", "regular") == 0
        assert _tier_distance("apprentice", "regular") == 0  # below requirement clamps

    def test_reach_ladder_distance(self) -> None:
        assert _tier_distance("master", "apprentice", venue_id="crimson_reach") == 2
        assert _tier_distance("journeyman", "journeyman", venue_id="crimson_reach") == 0
        assert _tier_distance("apprentice", "apprentice", venue_id="crimson_reach") == 0
        # Reach ladder doesn't include "regular" / "certified" / "patron";
        # unknown tier falls back to 0.
        assert _tier_distance("certified", "apprentice", venue_id="crimson_reach") == 0

    def test_stellaris_explicit_pass_unchanged(self) -> None:
        assert _tier_distance("patron", "apprentice", venue_id="stellaris") == 3


def _make_test_player() -> "object":
    from spacegame.data_loader import get_data_loader
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship

    loader = get_data_loader()
    loader.load_all()
    shuttle = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle, current_fuel=shuttle.fuel_capacity)
    return Player(name="Test", credits=2000, current_system_id="crimson_reach", ship=ship)


class TestWreckersTierForMembership:
    """AC: wreckers_tier_for_membership delegates to the Player helper."""

    def test_returns_canonical_tier_string(self) -> None:
        # Drive sub_reputation directly to test the tier-mapping; the
        # production path mutates rep via ``modify_sub_reputation``.
        player = _make_test_player()
        # Default: unjoined.
        assert wreckers_tier_for_membership(player) == "unjoined"
        # Apprentice threshold (1+).
        player.sub_reputation["wreckers_guild"] = 5
        assert wreckers_tier_for_membership(player) == "apprentice"
        # Journeyman threshold (30+).
        player.sub_reputation["wreckers_guild"] = 30
        assert wreckers_tier_for_membership(player) == "journeyman"
        # Master threshold (70+).
        player.sub_reputation["wreckers_guild"] = 80
        assert wreckers_tier_for_membership(player) == "master"


class TestReachSessionDue:
    """AC8: reach_session_due fires when counter >= REACH_SESSION_SIZE OR cap days."""

    def test_returns_false_below_threshold_and_no_cap(self) -> None:
        state = AuctionState()
        state.last_auction_day["crimson_reach"] = 0
        # No pending arrivals counter set: not due.
        assert not reach_session_due(state, current_day=3)

    def test_returns_true_when_pending_counter_meets_size(self) -> None:
        state = AuctionState()
        state.last_auction_day["crimson_reach"] = 0
        state.next_auction_day["crimson_reach_pending"] = REACH_SESSION_SIZE
        assert reach_session_due(state, current_day=3)

    def test_returns_true_when_max_gap_reached_even_with_low_counter(self) -> None:
        state = AuctionState()
        state.last_auction_day["crimson_reach"] = 0
        state.next_auction_day["crimson_reach_pending"] = 1
        # Day 8 is exactly the cap.
        assert reach_session_due(state, current_day=REACH_DEMAND_MAX_GAP_DAYS)

    def test_returns_true_when_no_prior_session_and_cap_elapsed(self) -> None:
        # Fresh save, no Reach history. Once the cap elapses from day 0,
        # the session should still fire so the player isn't gated forever.
        state = AuctionState()
        # No last_auction_day entry for Reach (fresh save).
        state.next_auction_day["crimson_reach_pending"] = 0
        # current_day already at cap.
        assert reach_session_due(state, current_day=REACH_DEMAND_MAX_GAP_DAYS)


class TestReachAdvanceDemand:
    """AC8: reach_advance_demand is deterministic per game-day."""

    def test_idempotent_across_reload(self) -> None:
        # Same state, same day-range, same counter increments.
        state_a = AuctionState()
        state_b = AuctionState()
        for d in range(1, 11):
            reach_advance_demand(state_a, current_day=d)
            reach_advance_demand(state_b, current_day=d)
        a = state_a.next_auction_day.get("crimson_reach_pending", 0)
        b = state_b.next_auction_day.get("crimson_reach_pending", 0)
        assert a == b, f"Reach demand counter must be deterministic: {a} vs {b}"

    def test_counter_advances_within_probability_band(self) -> None:
        # Run 200 days; expected counter ≈ 200 * 0.35 = 70 ± reasonable band.
        state = AuctionState()
        for d in range(1, 201):
            reach_advance_demand(state, current_day=d)
        counter = state.next_auction_day.get("crimson_reach_pending", 0)
        expected = int(200 * REACH_DEMAND_PROBABILITY)
        # Allow ±25 deviation. With the seeded sha256-based draw the actual
        # value is fixed; this band sanity-checks the probability is wired.
        assert abs(counter - expected) <= 25, (
            f"Counter {counter} too far from expected {expected} for "
            f"REACH_DEMAND_PROBABILITY={REACH_DEMAND_PROBABILITY}"
        )

    def test_counter_resets_on_reach_session_close(self) -> None:
        state = AuctionState()
        state.next_auction_day["crimson_reach_pending"] = 4
        state.active_auction_id = "crimson_reach"
        state.active_session_id = "test_session"
        # Append a session-history entry so close_session_for_day has
        # something to stamp.
        from spacegame.models.bidding import _SessionHistoryEntry

        state.session_history.append(
            _SessionHistoryEntry(
                session_id="test_session",
                venue_id="crimson_reach",
                closed_on_day=0,
                lot_results=[],
                rival_ids=[],
            )
        )
        state.close_session_for_day(current_day=10)
        assert state.next_auction_day.get("crimson_reach_pending", 0) == 0

    def test_demand_only_advances_for_reach_not_stellaris(self) -> None:
        # Sanity: calling reach_advance_demand should not touch Stellaris's
        # next_auction_day["stellaris"].
        state = AuctionState()
        state.next_auction_day["stellaris"] = 42
        for d in range(1, 5):
            reach_advance_demand(state, current_day=d)
        assert state.next_auction_day["stellaris"] == 42


class TestGenerateLotPoolReachVenue:
    """AC3: generate_lot_pool respects the Reach tier ladder."""

    def test_journeyman_player_excluded_from_master_lots(self) -> None:
        candidates = [
            _make_reach_lot(lot_id="reach_master_lot", rep_tier_required="master"),
            _make_reach_lot(lot_id="reach_journey_lot", rep_tier_required="journeyman"),
            _make_reach_lot(lot_id="reach_app_lot", rep_tier_required="apprentice"),
        ]
        drawn = generate_lot_pool(
            candidates,
            venue_id=VENUE_CRIMSON_REACH,
            player_rep_tier="journeyman",
            player_faction_standing={},
            season_tag=None,
            session_id="test_session_journey",
            target_size=4,
        )
        ids = {lot.id for lot in drawn}
        assert "reach_master_lot" not in ids
        assert ids.issubset({"reach_journey_lot", "reach_app_lot"})

    def test_master_player_can_draw_all_tiers(self) -> None:
        candidates = [
            _make_reach_lot(lot_id="reach_master_lot", rep_tier_required="master"),
            _make_reach_lot(lot_id="reach_journey_lot", rep_tier_required="journeyman"),
            _make_reach_lot(lot_id="reach_app_lot", rep_tier_required="apprentice"),
        ]
        drawn = generate_lot_pool(
            candidates,
            venue_id=VENUE_CRIMSON_REACH,
            player_rep_tier="master",
            player_faction_standing={},
            season_tag=None,
            session_id="test_session_master",
            target_size=4,
        )
        ids = {lot.id for lot in drawn}
        assert "reach_master_lot" in ids


class TestReachLotCatalog:
    """AC4: catalog data integrity for Reach lots."""

    @pytest.fixture(scope="class")
    def reach_lot_catalog(self) -> list[dict[str, Any]]:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "crimson_reach_lots.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return list(data["lots"])

    def test_catalog_size_in_locked_band(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        # Locked decision §B4.9: 12-16 lots.
        assert 12 <= len(reach_lot_catalog) <= 16, (
            f"Catalog size {len(reach_lot_catalog)} outside [12, 16]"
        )

    def test_all_lots_at_reach_venue(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        for entry in reach_lot_catalog:
            assert entry["venue"] == VENUE_CRIMSON_REACH

    def test_all_categories_locked(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        for entry in reach_lot_catalog:
            assert entry["category"] in REACH_CATEGORIES_LOCKED, (
                f"Lot {entry['id']} uses non-Reach category {entry['category']}"
            )

    def test_at_least_one_lot_per_category(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        cats = Counter(entry["category"] for entry in reach_lot_catalog)
        for required in REACH_CATEGORIES_LOCKED:
            assert cats[required] >= 1, f"Catalog missing at least one lot for category {required}"

    def test_headliner_count_in_locked_band(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        # Locked decision §B4.10: 1-2 headliners.
        headliners = [e for e in reach_lot_catalog if e.get("is_headliner")]
        assert 1 <= len(headliners) <= 2

    def test_no_season_tags(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        # Locked decision §B4.11: zero season tags at Reach.
        for entry in reach_lot_catalog:
            assert entry.get("season_tag") in (None, ""), (
                f"Lot {entry['id']} has season_tag {entry.get('season_tag')!r}; "
                "Reach lots must have no season tag"
            )

    def test_no_module_category(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        # Reach categories are explicit; no module re-issues belong here.
        for entry in reach_lot_catalog:
            assert entry["category"] != "module"

    def test_all_tiers_in_reach_ladder(self, reach_lot_catalog: list[dict[str, Any]]) -> None:
        for entry in reach_lot_catalog:
            tier = entry.get("rep_tier_required", "none")
            assert tier in REACH_TIER_LADDER, (
                f"Lot {entry['id']} has rep_tier_required={tier!r} not in "
                f"Reach ladder {REACH_TIER_LADDER}"
            )

    def test_tier_coverage_apprentice_journeyman_master(
        self, reach_lot_catalog: list[dict[str, Any]]
    ) -> None:
        tiers = {entry.get("rep_tier_required", "none") for entry in reach_lot_catalog}
        for required in ("apprentice", "journeyman", "master"):
            assert required in tiers, f"Catalog missing at least one lot at tier {required}"


class TestLegalityConsequenceMagnitudes:
    """AC10: locked legality penalty magnitudes (data assertion).

    These are constants the engine reads; the actual rep modification is
    wired in engine/game.py and exercised by the scenario test. This unit
    test just locks the magnitudes so changes are loud.
    """

    def test_contraband_penalty_locked(self) -> None:
        from spacegame.models.bidding import REACH_CONTRABAND_REP_PENALTY

        assert REACH_CONTRABAND_REP_PENALTY == -2

    def test_restricted_weapon_penalty_locked(self) -> None:
        from spacegame.models.bidding import REACH_RESTRICTED_WEAPON_REP_PENALTY

        assert REACH_RESTRICTED_WEAPON_REP_PENALTY == -1


class TestReachAchievementStubRegistered:
    """AC19: achievement_auction_reach_debut stub id is registered."""

    def test_stub_constant_exists(self) -> None:
        from spacegame.models.bidding import ACHIEVEMENT_AUCTION_REACH_DEBUT

        assert ACHIEVEMENT_AUCTION_REACH_DEBUT == "auction_reach_debut"
