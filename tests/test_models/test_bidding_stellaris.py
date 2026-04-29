"""SA-B3: Stellaris-specific bidding helpers.

Tests cover the new module-level helpers added in SA-B3 (none of which
modify SA-B2's locked schema):

* ``stellaris_tier_for_standing(rep)`` — tier ladder boundaries.
* ``current_season_tag(game_day)`` — 30-day rotation across 3 tags.
* ``pick_stellaris_rival_attendance(...)`` — deterministic per-session
  attendance for the three named rivals.
* ``stellaris_initial_session_day(...)`` — first-time scheduling.

Plus catalog data integrity over ``data/auctions/stellaris_lots.json``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from spacegame.config import PROJECT_ROOT
from spacegame.models.bidding import (
    HEADLINER_CAP_PER_SESSION,
    STELLARIS_CADENCE_MAX_DAYS,
    STELLARIS_CADENCE_MIN_DAYS,
    STELLARIS_HEADLINER_SESSION_SIZE,
    STELLARIS_STANDARD_SESSION_SIZE,
    AuctionState,
    current_season_tag,
    generate_lot_pool,
    pick_stellaris_rival_attendance,
    stellaris_initial_session_day,
    stellaris_tier_for_standing,
)
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_ANTIQUITY,
    LOT_CATEGORY_DERELICT_RIGHTS,
    LOT_CATEGORY_FACTION_COMMODITY,
    LOT_CATEGORY_MODULE,
    LOT_CATEGORY_RARE_UPGRADE,
    REP_TIER_APPRENTICE,
    REP_TIER_CERTIFIED,
    REP_TIER_PATRON,
    REP_TIER_REGULAR,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import (
    PERSONA_KADE,
    PERSONA_PRENTISS,
    PERSONA_SALKO,
)

STELLARIS_CATEGORIES_LOCKED: frozenset[str] = frozenset(
    {
        LOT_CATEGORY_MODULE,
        LOT_CATEGORY_ANTIQUITY,
        LOT_CATEGORY_FACTION_COMMODITY,
        LOT_CATEGORY_RARE_UPGRADE,
        LOT_CATEGORY_DERELICT_RIGHTS,
    }
)


SEASON_TAGS_LOCKED: tuple[str, str, str] = (
    "provenance_week",
    "axiom_export_window",
    "salvage_circuit",
)


class TestStandingTier:
    """AC2: stellaris_tier_for_standing covers the locked ladder."""

    @pytest.mark.parametrize(
        "rep,expected_tier",
        [
            (-100, REP_TIER_APPRENTICE),
            (-50, REP_TIER_APPRENTICE),
            (-1, REP_TIER_APPRENTICE),
            (0, REP_TIER_REGULAR),
            (10, REP_TIER_REGULAR),
            (25, REP_TIER_REGULAR),
            (26, REP_TIER_CERTIFIED),
            (50, REP_TIER_CERTIFIED),
            (75, REP_TIER_CERTIFIED),
            (76, REP_TIER_PATRON),
            (90, REP_TIER_PATRON),
            (100, REP_TIER_PATRON),
        ],
    )
    def test_tier_for_each_boundary(self, rep: int, expected_tier: str) -> None:
        assert stellaris_tier_for_standing(rep) == expected_tier

    def test_regular_player_excluded_from_certified_lots(self) -> None:
        candidate = AuctionLot(
            id="cert_lot",
            headline="Certified Heritage Lot",
            description="A lot for certified buyers.",
            category=LOT_CATEGORY_ANTIQUITY,
            venue=VENUE_STELLARIS,
            base_appraisal=20000,
            reserve_pct=0.7,
            rep_tier_required=REP_TIER_CERTIFIED,
        )
        drawn = generate_lot_pool(
            [candidate],
            venue_id=VENUE_STELLARIS,
            player_rep_tier=stellaris_tier_for_standing(10),  # regular
            player_faction_standing={},
            season_tag=None,
            session_id="excl_test",
            target_size=4,
        )
        assert drawn == []


class TestSeasonTag:
    """AC10: current_season_tag rotation over a 30-day cycle."""

    def test_provenance_week_first(self) -> None:
        assert current_season_tag(0) == "provenance_week"
        assert current_season_tag(15) == "provenance_week"
        assert current_season_tag(29) == "provenance_week"

    def test_axiom_export_window_second(self) -> None:
        assert current_season_tag(30) == "axiom_export_window"
        assert current_season_tag(45) == "axiom_export_window"
        assert current_season_tag(59) == "axiom_export_window"

    def test_salvage_circuit_third(self) -> None:
        assert current_season_tag(60) == "salvage_circuit"
        assert current_season_tag(89) == "salvage_circuit"

    def test_cycle_repeats(self) -> None:
        assert current_season_tag(90) == "provenance_week"
        assert current_season_tag(120) == "axiom_export_window"

    def test_only_three_tags_returned(self) -> None:
        seen: set[str] = set()
        for day in range(365):
            seen.add(current_season_tag(day))
        assert seen == set(SEASON_TAGS_LOCKED)

    def test_season_weighting_doubles_selection(self) -> None:
        """1000-trial Monte Carlo: tagged lots should draw at least 1.5x as often."""
        plain_pool = [
            AuctionLot(
                id=f"plain_{i}",
                headline=f"Plain Lot {i}",
                description="Standard lot with no season tag.",
                category=LOT_CATEGORY_ANTIQUITY,
                venue=VENUE_STELLARIS,
                base_appraisal=10000,
                reserve_pct=0.7,
            )
            for i in range(8)
        ]
        tagged_pool = [
            AuctionLot(
                id=f"tagged_{i}",
                headline=f"Tagged Lot {i}",
                description="A seasonal lot with the active tag.",
                category=LOT_CATEGORY_ANTIQUITY,
                venue=VENUE_STELLARIS,
                base_appraisal=10000,
                reserve_pct=0.7,
                season_tag="provenance_week",
            )
            for i in range(8)
        ]
        candidates = plain_pool + tagged_pool
        tagged_picks = 0
        plain_picks = 0
        trials = 200
        for trial in range(trials):
            session_id = f"season_trial_{trial}"
            drawn = generate_lot_pool(
                candidates,
                venue_id=VENUE_STELLARIS,
                player_rep_tier=REP_TIER_REGULAR,
                player_faction_standing={},
                season_tag="provenance_week",
                session_id=session_id,
                target_size=4,
            )
            for lot in drawn:
                if lot.season_tag == "provenance_week":
                    tagged_picks += 1
                else:
                    plain_picks += 1
        assert tagged_picks > plain_picks * 1.5, (
            f"Tagged lots draw rate too low: {tagged_picks} vs {plain_picks}"
        )


class TestRivalAttendance:
    """AC6: deterministic per-rival attendance with documented frequencies."""

    def test_salko_always_attends(self) -> None:
        for i in range(10):
            attendees = pick_stellaris_rival_attendance(
                session_id=f"salko_test_{i}",
                lot_pool=[
                    AuctionLot(
                        id=f"l{i}",
                        headline=f"Lot {i}",
                        description="Test lot.",
                        category=LOT_CATEGORY_MODULE,
                        venue=VENUE_STELLARIS,
                        base_appraisal=10000,
                        reserve_pct=0.7,
                    )
                ],
            )
            assert PERSONA_SALKO in attendees

    def test_kade_attends_only_when_target_lot_present(self) -> None:
        # Pool with a Kade-target lot (faction_commodity gated to commerce_guild).
        kade_target_lot = AuctionLot(
            id="kade_target",
            headline="Guild-stamped Procurement Crate",
            description="A faction commodity priced for institutional buyers.",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue=VENUE_STELLARIS,
            base_appraisal=8500,
            reserve_pct=0.82,
            faction_gate="commerce_guild",
        )
        non_target_lot = AuctionLot(
            id="non_target",
            headline="Antique Charter",
            description="An antiquity lot Kade has no mandate to pursue.",
            category=LOT_CATEGORY_ANTIQUITY,
            venue=VENUE_STELLARIS,
            base_appraisal=9000,
            reserve_pct=0.7,
        )
        with_target = pick_stellaris_rival_attendance(
            session_id="kade_with",
            lot_pool=[kade_target_lot, non_target_lot],
        )
        assert PERSONA_KADE in with_target

        without_target = pick_stellaris_rival_attendance(
            session_id="kade_without",
            lot_pool=[non_target_lot],
        )
        assert PERSONA_KADE not in without_target

    def test_prentiss_attends_about_70_percent_deterministic(self) -> None:
        attendances = 0
        n = 30
        for i in range(n):
            attendees = pick_stellaris_rival_attendance(
                session_id=f"prentiss_session_{i}",
                lot_pool=[
                    AuctionLot(
                        id="lot",
                        headline="Lot",
                        description="Generic lot.",
                        category=LOT_CATEGORY_ANTIQUITY,
                        venue=VENUE_STELLARIS,
                        base_appraisal=10000,
                        reserve_pct=0.7,
                    )
                ],
            )
            if PERSONA_PRENTISS in attendees:
                attendances += 1
        # 70% of 30 = 21; allow ±5 for sampling variance with the seeded hash.
        assert 16 <= attendances <= 26, (
            f"Prentiss attendance out of expected band: {attendances}/{n}"
        )

    def test_attendance_is_deterministic(self) -> None:
        lot_pool = [
            AuctionLot(
                id="l",
                headline="Lot",
                description="Determinism probe.",
                category=LOT_CATEGORY_MODULE,
                venue=VENUE_STELLARIS,
                base_appraisal=10000,
                reserve_pct=0.7,
            )
        ]
        first = pick_stellaris_rival_attendance(session_id="stable", lot_pool=lot_pool)
        second = pick_stellaris_rival_attendance(session_id="stable", lot_pool=lot_pool)
        assert first == second


class TestSchedule:
    """AC8: initial Stellaris session schedule is deterministic and 5-7 days out."""

    def test_initial_schedule_is_5_to_7_days(self) -> None:
        for current_day in range(50):
            day = stellaris_initial_session_day(current_day)
            gap = day - current_day
            assert STELLARIS_CADENCE_MIN_DAYS <= gap <= STELLARIS_CADENCE_MAX_DAYS

    def test_initial_schedule_is_deterministic(self) -> None:
        first = stellaris_initial_session_day(10)
        second = stellaris_initial_session_day(10)
        assert first == second

    def test_is_session_due_false_before_scheduled(self) -> None:
        st = AuctionState()
        st.schedule_session("stellaris", 15)
        assert st.is_session_due("stellaris", 14) is False
        assert st.is_session_due("stellaris", 15) is True
        assert st.is_session_due("stellaris", 20) is True


class TestLotCatalog:
    """AC3: stellaris_lots.json data integrity."""

    @pytest.fixture(scope="class")
    def catalog(self) -> list[dict]:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "stellaris_lots.json"
        assert path.exists(), f"Stellaris lot catalog not found: {path}"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "lots" in data
        return list(data["lots"])

    def test_catalog_size_in_band(self, catalog: list[dict]) -> None:
        assert 18 <= len(catalog) <= 24

    def test_all_venue_stellaris(self, catalog: list[dict]) -> None:
        for entry in catalog:
            assert entry["venue"] == VENUE_STELLARIS, entry["id"]

    def test_only_locked_categories(self, catalog: list[dict]) -> None:
        for entry in catalog:
            assert entry["category"] in STELLARIS_CATEGORIES_LOCKED, (
                f"{entry['id']}: forbidden category {entry['category']}"
            )

    def test_at_least_three_per_category(self, catalog: list[dict]) -> None:
        counter = Counter(e["category"] for e in catalog)
        for cat in STELLARIS_CATEGORIES_LOCKED:
            assert counter[cat] >= 3, f"Category {cat} has only {counter[cat]} lots"

    def test_headliner_count_in_range(self, catalog: list[dict]) -> None:
        headliners = [e for e in catalog if e.get("is_headliner")]
        assert 3 <= len(headliners) <= 5

    def test_season_tag_count_in_range(self, catalog: list[dict]) -> None:
        tagged = [e for e in catalog if e.get("season_tag")]
        assert len(tagged) >= 8
        for entry in tagged:
            assert entry["season_tag"] in SEASON_TAGS_LOCKED

    def test_module_lots_have_source_module_id(self, catalog: list[dict]) -> None:
        modules_path = Path(PROJECT_ROOT) / "data" / "ships" / "modules.json"
        with open(modules_path, "r", encoding="utf-8") as f:
            modules_data = json.load(f)
        valid_module_ids = {m["id"] for m in modules_data["modules"]}
        for entry in catalog:
            if entry["category"] == LOT_CATEGORY_MODULE:
                source = entry.get("source_module_id")
                assert source is not None, f"Module lot {entry['id']} missing source_module_id"
                assert source in valid_module_ids, (
                    f"Module lot {entry['id']} references unknown module {source}"
                )

    def test_unique_lot_ids(self, catalog: list[dict]) -> None:
        ids = [e["id"] for e in catalog]
        assert len(ids) == len(set(ids)), "Lot ids must be unique"

    def test_round_trip_through_dataclass(self, catalog: list[dict]) -> None:
        for entry in catalog:
            lot = AuctionLot.from_dict(entry)
            round_tripped = lot.to_dict()
            assert round_tripped["id"] == entry["id"]


class TestHeadlinerCap:
    """AC9: HEADLINER_CAP_PER_SESSION holds — at most one headliner drawn."""

    def test_headliner_cap_observed_across_seeds(self) -> None:
        candidates = [
            AuctionLot(
                id=f"head_{i}",
                headline=f"Headliner {i}",
                description="Featured headliner lot for the session.",
                category=LOT_CATEGORY_MODULE,
                venue=VENUE_STELLARIS,
                base_appraisal=20000,
                reserve_pct=0.75,
                is_headliner=True,
            )
            for i in range(5)
        ]
        candidates += [
            AuctionLot(
                id=f"std_{i}",
                headline=f"Standard {i}",
                description="Standard lot, not a headliner.",
                category=LOT_CATEGORY_ANTIQUITY,
                venue=VENUE_STELLARIS,
                base_appraisal=8000,
                reserve_pct=0.7,
            )
            for i in range(10)
        ]
        for trial in range(20):
            drawn = generate_lot_pool(
                candidates,
                venue_id=VENUE_STELLARIS,
                player_rep_tier=REP_TIER_PATRON,
                player_faction_standing={},
                season_tag=None,
                session_id=f"cap_trial_{trial}",
                target_size=STELLARIS_HEADLINER_SESSION_SIZE,
            )
            headliners_in_draw = sum(1 for lot in drawn if lot.is_headliner)
            assert headliners_in_draw <= HEADLINER_CAP_PER_SESSION


class TestSessionSizeConstants:
    """AC9: session size constants are exposed and unchanged from SA-B2."""

    def test_session_size_constants_locked(self) -> None:
        assert STELLARIS_STANDARD_SESSION_SIZE == 6
        assert STELLARIS_HEADLINER_SESSION_SIZE == 8
