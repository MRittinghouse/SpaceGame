"""Tests for LensReaction dataclass and LensReactor dispatcher (A2-4A).

TDD order: tests were written before the implementation. The test
structure mirrors the sprint's Task 1 (LensReaction) and Task 2 (LensReactor).
"""

from __future__ import annotations

import pytest

from spacegame.models.lens_reaction import LensReaction

# ---------------------------------------------------------------------------
# LensReaction dataclass tests
# ---------------------------------------------------------------------------


class TestLensReaction:
    def _valid_record(self) -> dict:
        return {
            "lens_id": "wealth",
            "context": "wreckers_hall_enrollment_pitch",
            "threshold": 40,
            "lines": ["line a", "line b", "line c"],
        }

    def test_from_dict_builds_valid_record(self) -> None:
        r = LensReaction.from_dict(self._valid_record())
        assert r.lens_id == "wealth"
        assert r.context == "wreckers_hall_enrollment_pitch"
        assert r.threshold == 40
        assert r.lines == ("line a", "line b", "line c")

    def test_from_dict_stores_lines_as_tuple(self) -> None:
        r = LensReaction.from_dict(self._valid_record())
        assert isinstance(r.lines, tuple)

    def test_from_dict_rejects_missing_lens_id(self) -> None:
        data = self._valid_record()
        del data["lens_id"]
        with pytest.raises(ValueError, match="lens_id"):
            LensReaction.from_dict(data)

    def test_from_dict_rejects_missing_context(self) -> None:
        data = self._valid_record()
        del data["context"]
        with pytest.raises(ValueError, match="context"):
            LensReaction.from_dict(data)

    def test_from_dict_rejects_missing_threshold(self) -> None:
        data = self._valid_record()
        del data["threshold"]
        with pytest.raises(ValueError, match="threshold"):
            LensReaction.from_dict(data)

    def test_from_dict_rejects_missing_lines(self) -> None:
        data = self._valid_record()
        del data["lines"]
        with pytest.raises(ValueError, match="lines"):
            LensReaction.from_dict(data)

    def test_from_dict_rejects_empty_lines(self) -> None:
        data = self._valid_record()
        data["lines"] = []
        with pytest.raises(ValueError, match="non-empty"):
            LensReaction.from_dict(data)

    def test_from_dict_is_frozen(self) -> None:
        r = LensReaction.from_dict(self._valid_record())
        with pytest.raises((AttributeError, TypeError)):
            r.lens_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LensReactor tests
# ---------------------------------------------------------------------------


def _make_fresh_player(name: str = "Test", game_day: int = 1):
    """Create a minimal fresh player with zero lens investment."""
    from spacegame.models.lens_investment import LensInvestment
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship
    from tests.test_scenarios._helpers import real_ship_type

    ship_type = real_ship_type("shuttle")
    ship = Ship(ship_type=ship_type, current_fuel=40)
    player = Player(
        name=name,
        credits=10000,
        current_system_id="nexus_prime",
        ship=ship,
    )
    player.game_day = game_day
    player.lens_investment = LensInvestment()
    return player


def _wealth_mid() -> LensReaction:
    return LensReaction(
        lens_id="wealth",
        context="wreckers_hall_enrollment_pitch",
        threshold=40,
        lines=("wealth-mid-1", "wealth-mid-2", "wealth-mid-3"),
    )


def _wealth_high() -> LensReaction:
    return LensReaction(
        lens_id="wealth",
        context="wreckers_hall_enrollment_pitch",
        threshold=80,
        lines=("wealth-high-1", "wealth-high-2", "wealth-high-3"),
    )


def _vengeance_mid() -> LensReaction:
    return LensReaction(
        lens_id="vengeance",
        context="wreckers_hall_enrollment_pitch",
        threshold=40,
        lines=("vengeance-mid-1", "vengeance-mid-2", "vengeance-mid-3"),
    )


def _fixture_pool() -> list[LensReaction]:
    return [_wealth_mid(), _wealth_high(), _vengeance_mid()]


class TestLensReactor:
    def _make_reactor(self, pool=None):
        from spacegame.models.lens_reactor import LensReactor

        return LensReactor(pool or _fixture_pool())

    def test_choose_variant_returns_default_when_no_lens_above_threshold(self) -> None:
        player = _make_fresh_player()
        reactor = self._make_reactor()
        result = reactor.choose_variant(
            player,
            "wreckers_hall_enrollment_pitch",
            {"default": ["the-default"]},
        )
        assert result == "the-default"

    def test_choose_variant_returns_lens_line_when_one_lens_qualifies(self) -> None:
        player = _make_fresh_player()
        player.lens_investment.add_investment("wealth", 45, "sold_cargo")
        reactor = self._make_reactor()
        result = reactor.choose_variant(
            player,
            "wreckers_hall_enrollment_pitch",
            {"default": ["the-default"]},
        )
        assert result in ("wealth-mid-1", "wealth-mid-2", "wealth-mid-3"), (
            f"Expected a wealth-mid variant, got {result!r}"
        )
        assert result != "the-default"

    def test_choose_variant_returns_high_tier_when_both_tiers_qualify(self) -> None:
        player = _make_fresh_player()
        player.lens_investment.add_investment("wealth", 85, "sold_cargo")
        reactor = self._make_reactor()
        result = reactor.choose_variant(
            player,
            "wreckers_hall_enrollment_pitch",
            {"default": ["the-default"]},
        )
        assert result in ("wealth-high-1", "wealth-high-2", "wealth-high-3"), (
            f"Expected a wealth-high variant, got {result!r}"
        )

    def test_choose_variant_breaks_ties_alphabetically_by_lens_id(self) -> None:
        """When two lenses tie on threshold, alphabetically first lens_id wins.

        'community' < 'vengeance' alphabetically, so community wins the tie.
        """
        from spacegame.models.lens_reactor import LensReactor

        community_mid = LensReaction(
            lens_id="community",
            context="wreckers_hall_enrollment_pitch",
            threshold=40,
            lines=("community-mid-1", "community-mid-2", "community-mid-3"),
        )
        pool = [community_mid, _vengeance_mid()]
        reactor = LensReactor(pool)
        player = _make_fresh_player()
        player.lens_investment.add_investment("community", 60, "source")
        player.lens_investment.add_investment("vengeance", 60, "source")
        result = reactor.choose_variant(
            player,
            "wreckers_hall_enrollment_pitch",
            {"default": ["the-default"]},
        )
        assert result in ("community-mid-1", "community-mid-2", "community-mid-3"), (
            f"Expected community (alphabetically first), got {result!r}"
        )

    def test_choose_variant_is_deterministic_across_repeated_calls(self) -> None:
        player = _make_fresh_player(name="SamePilot", game_day=5)
        player.lens_investment.add_investment("wealth", 50, "source")
        reactor = self._make_reactor()
        first = reactor.choose_variant(
            player,
            "wreckers_hall_enrollment_pitch",
            {"default": ["the-default"]},
        )
        for _ in range(99):
            result = reactor.choose_variant(
                player,
                "wreckers_hall_enrollment_pitch",
                {"default": ["the-default"]},
            )
            assert result == first, (
                f"choose_variant must be deterministic; got {result!r} != {first!r}"
            )

    def test_choose_variant_varies_when_game_day_changes(self) -> None:
        """Different game_day values should produce different results for 3-variant pools."""
        reactor = self._make_reactor(pool=[_wealth_mid()])
        results: set[str] = set()
        for day in range(1, 20):
            player = _make_fresh_player(name="Pilot", game_day=day)
            player.lens_investment.add_investment("wealth", 50, "source")
            result = reactor.choose_variant(
                player,
                "wreckers_hall_enrollment_pitch",
                {"default": ["the-default"]},
            )
            results.add(result)
        assert len(results) > 1, (
            "Different game_day values must produce at least two distinct lines "
            f"(got only: {results})"
        )

    def test_choose_variant_ignores_different_context(self) -> None:
        player = _make_fresh_player()
        player.lens_investment.add_investment("wealth", 50, "source")
        reactor = self._make_reactor()
        result = reactor.choose_variant(
            player,
            "some_other_context",
            {"default": ["the-default"]},
        )
        assert result == "the-default"
