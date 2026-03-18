"""Tests for station chatter system.

Covers ChatterLine dataclass and StationChatterManager filtering,
shown-line tracking, reset, and serialization round-trips.
"""

from spacegame.models.station_chatter import ChatterLine, StationChatterManager


# ============================================================================
# Helpers
# ============================================================================


def _make_line(
    id: str = "line_001",
    system_id: str = "nexus_prime",
    text: str = "Another freighter just docked.",
    category: str = "overheard",
    faction_id: str = "",
    min_reputation: int = -100,
    max_reputation: int = 100,
    requires_event_type: str = "",
    weight: int = 10,
) -> ChatterLine:
    """Create a single ChatterLine with sensible defaults."""
    return ChatterLine(
        id=id,
        system_id=system_id,
        text=text,
        category=category,
        faction_id=faction_id,
        min_reputation=min_reputation,
        max_reputation=max_reputation,
        requires_event_type=requires_event_type,
        weight=weight,
    )


def _make_lines_for_two_systems() -> list[ChatterLine]:
    """Create a varied set of lines across two systems."""
    return [
        _make_line(id="np_001", system_id="nexus_prime", text="Nexus line one."),
        _make_line(id="np_002", system_id="nexus_prime", text="Nexus line two."),
        _make_line(id="np_003", system_id="nexus_prime", text="Nexus line three."),
        _make_line(id="bs_001", system_id="breakstone", text="Breakstone line one."),
        _make_line(id="bs_002", system_id="breakstone", text="Breakstone line two."),
    ]


def _make_reputation_lines() -> list[ChatterLine]:
    """Create lines with varying reputation requirements."""
    return [
        _make_line(
            id="rep_low",
            system_id="nexus_prime",
            text="Guild enforcers are watching.",
            min_reputation=-100,
            max_reputation=-10,
        ),
        _make_line(
            id="rep_mid",
            system_id="nexus_prime",
            text="Fair weather trader.",
            min_reputation=-9,
            max_reputation=49,
        ),
        _make_line(
            id="rep_high",
            system_id="nexus_prime",
            text="They say you're a hero around here.",
            min_reputation=50,
            max_reputation=100,
        ),
    ]


def _make_event_lines() -> list[ChatterLine]:
    """Create lines with event requirements mixed with unconditional lines."""
    return [
        _make_line(
            id="always_01",
            system_id="nexus_prime",
            text="Just another day at the docks.",
            requires_event_type="",
        ),
        _make_line(
            id="blockade_01",
            system_id="nexus_prime",
            text="Nothing moves without a Guild stamp right now.",
            requires_event_type="trade_blockade",
        ),
        _make_line(
            id="surge_01",
            system_id="nexus_prime",
            text="Prices are through the roof this week.",
            requires_event_type="price_surge",
        ),
    ]


def _make_manager(lines: list[ChatterLine] | None = None) -> StationChatterManager:
    """Create a StationChatterManager from the given (or default) lines."""
    if lines is None:
        lines = _make_lines_for_two_systems()
    return StationChatterManager(lines)


# ============================================================================
# Basic Filtering Tests
# ============================================================================


class TestSystemFiltering:
    """get_chatter only returns lines for the requested system_id."""

    def test_returns_lines_for_requested_system(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert len(results) > 0, "Should return lines for nexus_prime"

    def test_does_not_return_lines_from_other_system(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        for text in results:
            assert "Breakstone" not in text, "nexus_prime query should not include Breakstone text"

    def test_unknown_system_returns_empty_list(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("deep_void", player_rep=0, active_event_types=[], count=3)
        assert results == [], "Unknown system should return empty list"

    def test_correct_system_text_is_returned(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("breakstone", player_rep=0, active_event_types=[], count=2)
        assert all("Breakstone" in t for t in results), "All returned lines should be Breakstone lines"


# ============================================================================
# Reputation Filtering Tests
# ============================================================================


class TestReputationFiltering:
    """get_chatter respects min_reputation and max_reputation bounds."""

    def test_returns_line_within_reputation_range(self) -> None:
        manager = _make_manager(_make_reputation_lines())
        results = manager.get_chatter("nexus_prime", player_rep=60, active_event_types=[], count=3)
        assert any("hero" in t for t in results), "High-rep line should be returned for rep=60"

    def test_excludes_line_below_min_reputation(self) -> None:
        manager = _make_manager(_make_reputation_lines())
        # rep=60 is above max_reputation=-10 for the low-rep line
        results = manager.get_chatter("nexus_prime", player_rep=60, active_event_types=[], count=3)
        assert not any("enforcers" in t for t in results), "Low-rep line should be excluded for rep=60"

    def test_excludes_line_above_max_reputation(self) -> None:
        manager = _make_manager(_make_reputation_lines())
        # rep=-50 is below min_reputation=50 for the high-rep line
        results = manager.get_chatter("nexus_prime", player_rep=-50, active_event_types=[], count=3)
        assert not any("hero" in t for t in results), "High-rep line should be excluded for rep=-50"

    def test_boundary_min_reputation_is_inclusive(self) -> None:
        manager = _make_manager(_make_reputation_lines())
        # rep=50 is exactly the min_reputation of the high-rep line
        results = manager.get_chatter("nexus_prime", player_rep=50, active_event_types=[], count=3)
        assert any("hero" in t for t in results), "Line with min_reputation=50 should appear at rep=50"

    def test_boundary_max_reputation_is_inclusive(self) -> None:
        manager = _make_manager(_make_reputation_lines())
        # rep=-10 is exactly the max_reputation of the low-rep line
        results = manager.get_chatter("nexus_prime", player_rep=-10, active_event_types=[], count=3)
        assert any("enforcers" in t for t in results), "Line with max_reputation=-10 should appear at rep=-10"

    def test_no_lines_match_reputation_returns_empty(self) -> None:
        lines = [
            _make_line(
                id="only_line",
                system_id="nexus_prime",
                text="Guild eyes everywhere.",
                min_reputation=80,
                max_reputation=100,
            )
        ]
        manager = _make_manager(lines)
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert results == [], "No matching reputation should return empty list"


# ============================================================================
# Event-Reactive Filtering Tests
# ============================================================================


class TestEventFiltering:
    """get_chatter includes event-gated lines only when the event is active."""

    def test_unconditional_line_always_included(self) -> None:
        manager = _make_manager(_make_event_lines())
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert any("another day" in t for t in results), "Unconditional line should always appear"

    def test_event_line_included_when_event_active(self) -> None:
        manager = _make_manager(_make_event_lines())
        results = manager.get_chatter(
            "nexus_prime", player_rep=0, active_event_types=["trade_blockade"], count=3
        )
        assert any("blockade" in t.lower() or "Guild stamp" in t for t in results), (
            "Blockade line should appear when trade_blockade is active"
        )

    def test_event_line_excluded_when_event_inactive(self) -> None:
        manager = _make_manager(_make_event_lines())
        results = manager.get_chatter(
            "nexus_prime", player_rep=0, active_event_types=[], count=3
        )
        assert not any("Guild stamp" in t for t in results), (
            "Blockade line should not appear when no events are active"
        )

    def test_only_matching_event_lines_included(self) -> None:
        manager = _make_manager(_make_event_lines())
        results = manager.get_chatter(
            "nexus_prime", player_rep=0, active_event_types=["price_surge"], count=3
        )
        assert not any("Guild stamp" in t for t in results), (
            "Non-matching event line should be excluded even when another event is active"
        )
        assert any("Prices" in t for t in results), (
            "price_surge line should appear when price_surge is active"
        )


# ============================================================================
# Count Parameter Tests
# ============================================================================


class TestCountParameter:
    """get_chatter returns at most `count` lines."""

    def test_returns_requested_count_when_enough_lines(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=2)
        assert len(results) == 2, f"Expected 2 lines, got {len(results)}"

    def test_returns_fewer_when_not_enough_lines(self) -> None:
        lines = [
            _make_line(id="solo", system_id="nexus_prime", text="Lone drifter passes through.")
        ]
        manager = _make_manager(lines)
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=5)
        assert len(results) == 1, "Should return only available lines, not pad to count"

    def test_default_count_is_three(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[])
        assert len(results) <= 3, "Default count should be 3"


# ============================================================================
# No Duplicates Tests
# ============================================================================


class TestNoDuplicates:
    """get_chatter never returns the same line text twice in one call."""

    def test_no_duplicate_texts_in_single_call(self) -> None:
        manager = _make_manager()
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert len(results) == len(set(results)), "Returned lines should be unique within one call"

    def test_no_duplicates_even_with_count_equal_to_pool_size(self) -> None:
        manager = _make_manager()
        # nexus_prime has 3 lines in the default fixture
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert len(set(results)) == len(results), "All returned lines should be distinct"


# ============================================================================
# Shown Tracking Tests
# ============================================================================


class TestShownTracking:
    """Previously shown lines are not repeated until all lines are exhausted or reset."""

    def test_shown_lines_not_returned_on_next_call(self) -> None:
        manager = _make_manager()
        first = set(
            manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=2)
        )
        second = set(
            manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=2)
        )
        # With only 3 lines in the pool and count=2, there is one remaining; the second
        # batch should not overlap with the first.
        assert first.isdisjoint(second), (
            "Second call should not repeat lines already shown in first call"
        )

    def test_shown_tracking_is_per_system(self) -> None:
        manager = _make_manager()
        # Exhaust nexus_prime lines
        manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        # Breakstone lines should still be available
        results = manager.get_chatter(
            "breakstone", player_rep=0, active_event_types=[], count=2
        )
        assert len(results) == 2, "Shown tracking for nexus_prime should not affect breakstone"

    def test_returns_empty_when_all_lines_shown(self) -> None:
        lines = [
            _make_line(id="only_one", system_id="nexus_prime", text="The only line here.")
        ]
        manager = _make_manager(lines)
        manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=1)
        second = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=1)
        assert second == [], "Should return empty once all lines have been shown"


# ============================================================================
# Reset Shown Tests
# ============================================================================


class TestResetShown:
    """reset_shown clears tracking for a specific system."""

    def test_reset_allows_lines_to_be_shown_again(self) -> None:
        lines = [
            _make_line(id="only_one", system_id="nexus_prime", text="The only line here.")
        ]
        manager = _make_manager(lines)
        manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=1)

        manager.reset_shown("nexus_prime")

        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=1)
        assert results == ["The only line here."], "Reset should allow the line to appear again"

    def test_reset_only_affects_specified_system(self) -> None:
        manager = _make_manager()
        # Exhaust both systems
        manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        manager.get_chatter("breakstone", player_rep=0, active_event_types=[], count=2)

        # Reset only nexus_prime
        manager.reset_shown("nexus_prime")

        # nexus_prime should work again
        nexus_results = manager.get_chatter(
            "nexus_prime", player_rep=0, active_event_types=[], count=1
        )
        assert len(nexus_results) == 1, "nexus_prime should have lines after reset"

        # Breakstone still exhausted
        breakstone_results = manager.get_chatter(
            "breakstone", player_rep=0, active_event_types=[], count=1
        )
        assert breakstone_results == [], "Breakstone should still be exhausted"


# ============================================================================
# Serialization Tests
# ============================================================================


class TestSerialization:
    """to_dict / from_dict round-trip preserves shown-line state."""

    def test_to_dict_returns_dict(self) -> None:
        manager = _make_manager()
        data = manager.to_dict()
        assert isinstance(data, dict), "to_dict should return a dict"

    def test_from_dict_restores_shown_state(self) -> None:
        lines = _make_lines_for_two_systems()
        manager = _make_manager(lines)

        # Show one line in nexus_prime
        shown = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=1)
        assert len(shown) == 1

        data = manager.to_dict()

        # Restore from dict
        manager2 = StationChatterManager.from_dict(data, lines)

        # The shown line should still be tracked — it won't appear again
        for _ in range(10):
            results = manager2.get_chatter(
                "nexus_prime", player_rep=0, active_event_types=[], count=3
            )
            assert shown[0] not in results, (
                f"Previously shown line '{shown[0]}' should remain tracked after from_dict"
            )

    def test_from_dict_round_trip_preserves_unshown_lines(self) -> None:
        lines = _make_lines_for_two_systems()
        manager = _make_manager(lines)

        # Show nothing; serialize immediately
        data = manager.to_dict()
        manager2 = StationChatterManager.from_dict(data, lines)

        results = manager2.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert len(results) == 3, "All lines should be available after a clean round-trip"

    def test_from_dict_with_empty_shown_state(self) -> None:
        lines = _make_lines_for_two_systems()
        # Construct minimal dict as if saving with no shown state
        data: dict = {}
        manager = StationChatterManager.from_dict(data, lines)
        results = manager.get_chatter("nexus_prime", player_rep=0, active_event_types=[], count=3)
        assert len(results) == 3, "Empty dict should produce a manager with no shown state"
