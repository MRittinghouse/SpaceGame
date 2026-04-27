"""SA-P4 — venue dispatch for ``_ensure_dispute_view`` (AC 10 / AC 11).

The engine consults a small ``_VENUE_REGISTRY`` lookup keyed by the
player's current system id; SA-P5 inherits without further engine work.
"""

from __future__ import annotations

from spacegame.engine.game import (
    _DEFAULT_VENUE_CONFIG,
    _VENUE_REGISTRY,
    _resolve_venue_config,
)


class _StubPlayer:
    def __init__(self, system_id: str) -> None:
        self.current_system_id = system_id


class TestVenueDispatch:
    """``_resolve_venue_config`` maps player.current_system_id to a venue tuple."""

    def test_verdant_player_resolves_to_verdant_venue(self) -> None:
        player = _StubPlayer("verdant")
        assert _resolve_venue_config(player) == ("verdant_mayors_council", "verdant")

    def test_havens_rest_player_resolves_to_alliance_congress(self) -> None:
        player = _StubPlayer("havens_rest")
        assert _resolve_venue_config(player) == (
            "havens_congress_hall",
            "frontier_alliance",
        )

    def test_unknown_system_falls_back_to_verdant(self) -> None:
        """A player at an unrelated system gets the SA-P3 fallback."""
        player = _StubPlayer("nexus_prime")
        assert _resolve_venue_config(player) == _DEFAULT_VENUE_CONFIG

    def test_none_player_falls_back_to_verdant(self) -> None:
        assert _resolve_venue_config(None) == _DEFAULT_VENUE_CONFIG

    def test_empty_system_falls_back_to_verdant(self) -> None:
        player = _StubPlayer("")
        assert _resolve_venue_config(player) == _DEFAULT_VENUE_CONFIG

    def test_registry_contains_both_known_venues(self) -> None:
        """SA-P3 + SA-P4 both appear in the registry with the expected ids."""
        assert "verdant" in _VENUE_REGISTRY
        assert "havens_rest" in _VENUE_REGISTRY
        assert _VENUE_REGISTRY["verdant"] == ("verdant_mayors_council", "verdant")
        assert _VENUE_REGISTRY["havens_rest"] == (
            "havens_congress_hall",
            "frontier_alliance",
        )

    def test_crimson_reach_resolves_to_wreckers_guild_venue(self) -> None:
        """SA-P5: player at Crimson Reach dispatches to the Wreckers' Guild venue."""
        player = _StubPlayer("crimson_reach")
        assert _resolve_venue_config(player) == ("crimson_wreckers_guild", "crimson_reach")

    def test_registry_contains_crimson_reach_entry(self) -> None:
        """SA-P5: crimson_reach key added alongside SA-P3/SA-P4 entries."""
        assert "crimson_reach" in _VENUE_REGISTRY
        assert _VENUE_REGISTRY["crimson_reach"] == ("crimson_wreckers_guild", "crimson_reach")


class TestStationHubRouting:
    """``UNIQUE_HALL_TARGETS`` includes the new Haven's Rest entry (AC 11)."""

    def test_havens_congress_hall_routes_to_dispute_state(self) -> None:
        from spacegame.config import GameState
        from spacegame.views.station_hub_view import UNIQUE_HALL_TARGETS

        assert UNIQUE_HALL_TARGETS["havens_congress_hall"] == GameState.DISPUTE

    def test_verdant_mayors_council_still_routes_to_dispute_state(self) -> None:
        """SA-P3 routing remains intact."""
        from spacegame.config import GameState
        from spacegame.views.station_hub_view import UNIQUE_HALL_TARGETS

        assert UNIQUE_HALL_TARGETS["verdant_mayors_council"] == GameState.DISPUTE
