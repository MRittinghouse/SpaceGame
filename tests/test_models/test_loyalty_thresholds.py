"""Tests for crew loyalty thresholds and gameplay impact."""

from spacegame.models.crew import (
    CrewAbility,
    CrewTemplate,
    CrewRoster,
    LoyaltyTier,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_ability(
    bonus_type: str = "fuel_efficiency_bonus",
    bonus_value: float = 2.0,
    description: str = "Test ability",
    unlock_level: int = 1,
) -> CrewAbility:
    return CrewAbility(
        bonus_type=bonus_type,
        bonus_value=bonus_value,
        description=description,
        unlock_level=unlock_level,
    )


def _make_template(
    template_id: str = "elena_reeves",
    name: str = "Elena Reeves",
    role: str = "navigator",
    abilities: list[CrewAbility] | None = None,
) -> CrewTemplate:
    if abilities is None:
        abilities = [
            _make_ability("fuel_efficiency_bonus", 2.0, "Efficient Routing", 1),
            _make_ability("fuel_efficiency_bonus", 3.0, "Advanced Navigation", 3),
        ]
    return CrewTemplate(
        id=template_id,
        name=name,
        role=role,
        description=f"A test crew member: {name}",
        portrait_color=[100, 180, 255],
        abilities=abilities,
        is_companion=True,
    )


def _make_roster() -> CrewRoster:
    templates = {
        "elena_reeves": _make_template(),
        "marcus_jin": _make_template(
            "marcus_jin",
            "Marcus Jin",
            "engineer",
            [_make_ability("cargo_bonus", 15.0, "Cargo Optimization", 1)],
        ),
    }
    return CrewRoster(templates)


def _recruit_at_loyalty(
    roster: CrewRoster, template_id: str, loyalty: int
) -> None:
    """Recruit a crew member and set their loyalty to a specific value."""
    roster.recruit(template_id, crew_slots=5)
    state = roster.get_member_state(template_id)
    assert state is not None
    state["loyalty"] = loyalty


# ============================================================================
# Tier Boundary Tests
# ============================================================================


class TestLoyaltyTierBoundaries:
    """Tests that loyalty values map to correct tiers."""

    def test_loyalty_0_is_discontented(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 0)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.DISCONTENTED

    def test_loyalty_9_is_discontented(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 9)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.DISCONTENTED

    def test_loyalty_10_is_wary(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 10)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.WARY

    def test_loyalty_29_is_wary(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 29)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.WARY

    def test_loyalty_30_is_neutral(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 30)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.NEUTRAL

    def test_loyalty_49_is_neutral(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 49)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.NEUTRAL

    def test_loyalty_50_is_warm(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 50)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.WARM

    def test_loyalty_69_is_warm(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 69)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.WARM

    def test_loyalty_70_is_loyal(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 70)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.LOYAL

    def test_loyalty_84_is_loyal(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 84)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.LOYAL

    def test_loyalty_85_is_devoted(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 85)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.DEVOTED

    def test_loyalty_100_is_devoted(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 100)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.DEVOTED

    def test_unrecruited_member_returns_none(self) -> None:
        roster = _make_roster()
        assert roster.get_loyalty_tier("elena_reeves") is None


# ============================================================================
# Bonus Multiplier Tests
# ============================================================================


class TestLoyaltyBonusMultiplier:
    """Tests that loyalty tiers apply correct bonus multipliers."""

    def test_neutral_gives_1x_multiplier(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 30)
        assert roster.get_loyalty_multiplier("elena_reeves") == 1.0

    def test_wary_gives_1x_multiplier(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 15)
        assert roster.get_loyalty_multiplier("elena_reeves") == 1.0

    def test_warm_gives_1x_multiplier(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 55)
        assert roster.get_loyalty_multiplier("elena_reeves") == 1.0

    def test_loyal_gives_1_25x_multiplier(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 70)
        assert roster.get_loyalty_multiplier("elena_reeves") == 1.25

    def test_devoted_gives_1_5x_multiplier(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 85)
        assert roster.get_loyalty_multiplier("elena_reeves") == 1.5

    def test_get_bonus_applies_loyalty_multiplier(self) -> None:
        """Loyal crew member should get 1.25x bonus."""
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 75)  # Loyal tier
        # Elena level 1: fuel_efficiency_bonus = 2.0, multiplier = 1.25
        bonus = roster.get_bonus("fuel_efficiency_bonus")
        assert bonus == 2.0 * 1.25, f"Expected {2.0 * 1.25}, got {bonus}"

    def test_get_bonus_devoted_multiplier(self) -> None:
        """Devoted crew member should get 1.5x bonus."""
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 90)  # Devoted tier
        bonus = roster.get_bonus("fuel_efficiency_bonus")
        assert bonus == 2.0 * 1.5, f"Expected {2.0 * 1.5}, got {bonus}"

    def test_get_bonus_multiple_crew_different_loyalty(self) -> None:
        """Two crew at different loyalty tiers should each get own multiplier."""
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 85)  # Devoted: 1.5x
        _recruit_at_loyalty(roster, "marcus_jin", 30)  # Neutral: 1.0x
        # Elena: 2.0 * 1.5 = 3.0 fuel_efficiency_bonus
        assert roster.get_bonus("fuel_efficiency_bonus") == 3.0
        # Marcus: 15.0 * 1.0 = 15.0 cargo_bonus
        assert roster.get_bonus("cargo_bonus") == 15.0


# ============================================================================
# Departure Tests
# ============================================================================


class TestCrewDeparture:
    """Tests for crew departure warnings and departures."""

    def test_no_warnings_at_normal_loyalty(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 30)
        warnings = roster.check_departure_warnings()
        assert len(warnings) == 0

    def test_warning_at_low_loyalty(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 5)
        warnings = roster.check_departure_warnings()
        assert len(warnings) == 1
        assert "Elena" in warnings[0]

    def test_no_departure_above_zero(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 1)
        departures = roster.process_departures()
        assert len(departures) == 0
        assert len(roster.get_recruited_members()) == 1

    def test_departure_at_zero_loyalty(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 0)
        departures = roster.process_departures()
        assert len(departures) == 1
        assert "Elena" in departures[0]
        assert len(roster.get_recruited_members()) == 0

    def test_multiple_departures(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 0)
        _recruit_at_loyalty(roster, "marcus_jin", 0)
        departures = roster.process_departures()
        assert len(departures) == 2


# ============================================================================
# Threshold Flag Tests
# ============================================================================


class TestLoyaltyThresholdFlags:
    """Tests that crossing loyalty thresholds generates flags for quest gating."""

    def test_crossing_50_generates_flag(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 48)
        flags = roster.adjust_loyalty("elena_reeves", 5)  # 48 -> 53
        assert "crew_loyalty_elena_reeves_50" in flags

    def test_crossing_70_generates_flag(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 68)
        flags = roster.adjust_loyalty("elena_reeves", 5)  # 68 -> 73
        assert "crew_loyalty_elena_reeves_70" in flags

    def test_crossing_85_generates_flag(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 83)
        flags = roster.adjust_loyalty("elena_reeves", 5)  # 83 -> 88
        assert "crew_loyalty_elena_reeves_85" in flags

    def test_no_flag_when_not_crossing_threshold(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 30)
        flags = roster.adjust_loyalty("elena_reeves", 5)  # 30 -> 35
        assert len(flags) == 0

    def test_crossing_multiple_thresholds_at_once(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 45)
        flags = roster.adjust_loyalty("elena_reeves", 45)  # 45 -> 90
        assert "crew_loyalty_elena_reeves_50" in flags
        assert "crew_loyalty_elena_reeves_70" in flags
        assert "crew_loyalty_elena_reeves_85" in flags

    def test_decreasing_loyalty_does_not_generate_flags(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 75)
        flags = roster.adjust_loyalty("elena_reeves", -10)  # 75 -> 65
        assert len(flags) == 0


# ============================================================================
# Serialization Tests
# ============================================================================


class TestLoyaltyThresholdSerialization:
    """Tests that loyalty tiers work correctly after save/load."""

    def test_loyalty_tier_persists_through_save_load(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 85)
        assert roster.get_loyalty_tier("elena_reeves") == LoyaltyTier.DEVOTED

        saved = roster.get_state()
        roster2 = _make_roster()
        roster2.load_state(saved)

        assert roster2.get_loyalty_tier("elena_reeves") == LoyaltyTier.DEVOTED

    def test_bonus_multiplier_correct_after_load(self) -> None:
        roster = _make_roster()
        _recruit_at_loyalty(roster, "elena_reeves", 75)
        original_bonus = roster.get_bonus("fuel_efficiency_bonus")

        saved = roster.get_state()
        roster2 = _make_roster()
        roster2.load_state(saved)

        assert roster2.get_bonus("fuel_efficiency_bonus") == original_bonus
