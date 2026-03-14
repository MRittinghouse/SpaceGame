"""Tests for criminal heat display and bounty hunter integration (Phase E.5).

Covers heat color coding, bounty hunter trigger thresholds,
safe haven exemption, and signal jammer reduction.
"""

from spacegame.config import get_heat_display_color
from spacegame.models.smuggling import (
    should_trigger_bounty_hunter,
    get_bounty_hunter_tier,
    calculate_bounty_hunter_chance,
)


# ============================================================================
# Heat Display Colors
# ============================================================================


class TestHeatDisplayColor:
    """Heat indicator uses color coding by severity."""

    def test_heat_zero_not_shown(self) -> None:
        """Heat 0 returns None (no display)."""
        assert get_heat_display_color(0) is None

    def test_heat_white_1_to_10(self) -> None:
        """Heat 1-10 returns white."""
        assert get_heat_display_color(1) == (255, 255, 255)
        assert get_heat_display_color(10) == (255, 255, 255)

    def test_heat_yellow_11_to_25(self) -> None:
        """Heat 11-25 returns yellow."""
        assert get_heat_display_color(11) == (255, 255, 0)
        assert get_heat_display_color(25) == (255, 255, 0)

    def test_heat_orange_26_to_50(self) -> None:
        """Heat 26-50 returns orange."""
        assert get_heat_display_color(26) == (255, 165, 0)
        assert get_heat_display_color(50) == (255, 165, 0)

    def test_heat_red_51_plus(self) -> None:
        """Heat 51+ returns red."""
        assert get_heat_display_color(51) == (255, 50, 50)
        assert get_heat_display_color(100) == (255, 50, 50)


# ============================================================================
# Bounty Hunter Trigger Logic
# ============================================================================


class TestBountyHunterTriggers:
    """Bounty hunter encounters depend on heat thresholds."""

    def test_no_bounty_below_26(self) -> None:
        """Heat below 26 never triggers bounty hunters."""
        tier = get_bounty_hunter_tier(25)
        assert tier is None
        tier = get_bounty_hunter_tier(0)
        assert tier is None

    def test_freelance_tier_26_to_50(self) -> None:
        """Heat 26-50 produces freelance tier."""
        tier = get_bounty_hunter_tier(26)
        assert tier is not None
        assert tier.value == "freelance"
        tier = get_bounty_hunter_tier(50)
        assert tier.value == "freelance"

    def test_licensed_tier_51_to_75(self) -> None:
        """Heat 51-75 produces licensed tier."""
        tier = get_bounty_hunter_tier(51)
        assert tier is not None
        assert tier.value == "licensed"

    def test_elite_tier_76_plus(self) -> None:
        """Heat 76+ produces elite tier."""
        tier = get_bounty_hunter_tier(76)
        assert tier is not None
        assert tier.value == "elite"

    def test_crimson_reach_safe_haven(self) -> None:
        """Crimson Reach never triggers bounty hunters."""
        chance = calculate_bounty_hunter_chance(
            criminal_heat=80,
            system_id="crimson_reach",
        )
        assert chance == 0.0

    def test_signal_jammer_reduces_chance(self) -> None:
        """Signal jammer reduces bounty hunter encounter chance."""
        base_chance = calculate_bounty_hunter_chance(
            criminal_heat=50,
            system_id="nexus_prime",
        )
        jammer_chance = calculate_bounty_hunter_chance(
            criminal_heat=50,
            has_signal_jammer=True,
            system_id="nexus_prime",
        )
        assert jammer_chance < base_chance

    def test_should_trigger_deterministic(self) -> None:
        """Same inputs always produce same result."""
        results = set()
        for _ in range(10):
            result = should_trigger_bounty_hunter(
                criminal_heat=50,
                game_day=42,
                system_id="nexus_prime",
            )
            results.add(result)
        assert len(results) == 1
