"""Tests for player identity system — titles, playstyle, ship naming."""

import pytest

from spacegame.models.player_identity import (
    get_title,
    get_all_titles,
    get_primary_title,
    get_playstyle,
    get_playstyle_label,
    MINING_TITLES,
    TRADING_TITLES,
    COMBAT_TITLES,
)


class TestReputationTitles:
    """Title tiers earned from cumulative player stats."""

    def test_no_title_below_threshold(self) -> None:
        assert get_title(0, MINING_TITLES) is None
        assert get_title(9, MINING_TITLES) is None

    def test_first_tier_title(self) -> None:
        assert get_title(10, MINING_TITLES) == "Prospector"

    def test_highest_earned_title(self) -> None:
        assert get_title(2000, MINING_TITLES) == "Deep Core Pioneer"
        assert get_title(9999, MINING_TITLES) == "Iron Baron"

    def test_trading_tiers(self) -> None:
        assert get_title(5, TRADING_TITLES) == "Peddler"
        assert get_title(200, TRADING_TITLES) == "Market Shark"
        assert get_title(5000, TRADING_TITLES) == "Tycoon"

    def test_combat_tiers(self) -> None:
        assert get_title(3, COMBAT_TITLES) == "Scrapper"
        assert get_title(250, COMBAT_TITLES) == "Warlord"


class TestAllTitles:
    """Computing all titles from player stats."""

    def test_all_titles_empty_for_new_player(self) -> None:
        titles = get_all_titles()
        assert len(titles) == 0

    def test_all_titles_returns_earned(self) -> None:
        titles = get_all_titles(ore_mined=100, trades_completed=50)
        assert "mining" in titles
        assert "trading" in titles
        assert "combat" not in titles

    def test_all_titles_covers_all_domains(self) -> None:
        titles = get_all_titles(
            ore_mined=5000, trades_completed=5000, combats_won=250,
            items_salvaged=1500, items_refined=1000, systems_visited=11,
        )
        assert len(titles) == 6


class TestPrimaryTitle:
    """Picking the single best title."""

    def test_rookie_for_new_player(self) -> None:
        assert get_primary_title() == "Rookie"

    def test_highest_tier_wins(self) -> None:
        # Trading at tier 3 (Market Shark) vs mining at tier 1 (Prospector)
        title = get_primary_title(ore_mined=10, trades_completed=200)
        assert title == "Market Shark"

    def test_same_tier_uses_priority(self) -> None:
        # Both at tier 1, trading has priority
        title = get_primary_title(ore_mined=10, trades_completed=5)
        assert title in ("Peddler", "Prospector")


class TestPlaystyle:
    """Playstyle detection from activity ratios."""

    def test_balanced_for_new_player(self) -> None:
        assert get_playstyle() == "balanced"

    def test_dominant_trading(self) -> None:
        style = get_playstyle(trades_completed=200)
        assert style == "trading"

    def test_dominant_mining(self) -> None:
        style = get_playstyle(ore_mined=500)
        assert style == "mining"

    def test_balanced_when_even(self) -> None:
        # Equal engagement across activities
        style = get_playstyle(
            ore_mined=100, trades_completed=50,
            combats_won=15, items_salvaged=50,
        )
        assert style == "balanced"

    def test_playstyle_label(self) -> None:
        label = get_playstyle_label(trades_completed=200)
        assert label == "Trader"

    def test_freelancer_for_balanced(self) -> None:
        label = get_playstyle_label()
        assert label == "Freelancer"
