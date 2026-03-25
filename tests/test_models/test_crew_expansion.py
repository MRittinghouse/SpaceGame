"""Tests for lightweight crew expansion (companion vs crew distinction)."""

from spacegame.models.crew import CrewAbility, CrewRoster, CrewTemplate, LoyaltyTier


def _companion_template() -> CrewTemplate:
    """Create a companion-style template for testing."""
    return CrewTemplate(
        id="test_companion",
        name="Test Companion",
        role="navigator",
        description="A test companion.",
        portrait_color=[100, 180, 255],
        abilities=[
            CrewAbility(
                bonus_type="fuel_efficiency_bonus",
                bonus_value=2.0,
                description="Efficient Routing",
                unlock_level=1,
            ),
            CrewAbility(
                bonus_type="fuel_efficiency_bonus",
                bonus_value=3.0,
                description="Advanced Navigation",
                unlock_level=3,
            ),
        ],
        max_level=5,
        xp_thresholds=[0, 50, 150, 350, 700],
        faction_id="commerce_guild",
        home_system_id="stellaris_port",
        is_companion=True,
    )


def _crew_template() -> CrewTemplate:
    """Create a lightweight crew template for testing."""
    return CrewTemplate(
        id="test_crew",
        name="Test Crew",
        role="cargo handler",
        description="A test crew member.",
        portrait_color=[200, 160, 60],
        abilities=[
            CrewAbility(
                bonus_type="cargo_bonus",
                bonus_value=15.0,
                description="Cargo Handling",
                unlock_level=1,
            ),
        ],
        max_level=1,
        xp_thresholds=[0],
        faction_id="miners_union",
        home_system_id="breakstone",
        is_companion=False,
    )


class TestIsCompanionField:
    """Tests for the is_companion field on CrewTemplate."""

    def test_is_companion_defaults_false(self) -> None:
        template = CrewTemplate(
            id="default",
            name="Default",
            role="generic",
            description="No companion flag set.",
            portrait_color=[100, 100, 100],
        )
        assert template.is_companion is False

    def test_companion_flag_true(self) -> None:
        template = _companion_template()
        assert template.is_companion is True

    def test_crew_flag_false(self) -> None:
        template = _crew_template()
        assert template.is_companion is False


class TestCrewBonuses:
    """Tests for crew bonus behavior (no loyalty multiplier)."""

    def test_crew_bonus_ignores_loyalty_multiplier(self) -> None:
        """Crew bonuses should always use 1.0x regardless of loyalty."""
        crew = _crew_template()
        companion = _companion_template()
        roster = CrewRoster({"test_crew": crew, "test_companion": companion})

        roster.recruit("test_crew", 4)
        roster.recruit("test_companion", 4)

        # Boost both to Devoted tier
        roster.adjust_loyalty("test_crew", 70)
        roster.adjust_loyalty("test_companion", 70)

        # Companion at Devoted should get 1.5x multiplier
        companion_bonus = companion.get_bonus_at_level("fuel_efficiency_bonus", 1)
        assert companion_bonus == 2.0
        # Companion total with 1.5x loyalty = 3.0
        # Crew cargo_bonus should be flat 15.0 (1.0x, no loyalty scaling)
        cargo_total = roster.get_bonus("cargo_bonus")
        assert cargo_total == 15.0  # No loyalty multiplier for crew

    def test_crew_and_companion_bonuses_stack(self) -> None:
        """Bonuses from crew and companions should sum correctly."""
        crew = CrewTemplate(
            id="crew_trader",
            name="Crew Trader",
            role="negotiator",
            description="Trades stuff.",
            portrait_color=[100, 100, 100],
            abilities=[
                CrewAbility("buy_price_reduction", 0.03, "Trade Contacts", 1),
            ],
            max_level=1,
            xp_thresholds=[0],
            is_companion=False,
        )
        companion = CrewTemplate(
            id="comp_trader",
            name="Companion Trader",
            role="trader",
            description="Also trades.",
            portrait_color=[110, 210, 120],
            abilities=[
                CrewAbility("buy_price_reduction", 0.03, "Trade Contacts", 1),
            ],
            max_level=5,
            xp_thresholds=[0, 50, 150, 350, 700],
            is_companion=True,
        )
        roster = CrewRoster({"crew_trader": crew, "comp_trader": companion})
        roster.recruit("crew_trader", 4)
        roster.recruit("comp_trader", 4)

        total = roster.get_bonus("buy_price_reduction")
        assert total == 0.06  # 0.03 + 0.03


class TestCrewLoyalty:
    """Tests for crew loyalty behavior (fixed, no adjustment)."""

    def test_crew_loyalty_stays_fixed(self) -> None:
        """Crew loyalty should not change when adjust_loyalty is called."""
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)

        initial_loyalty = roster.get_member_state("test_crew")["loyalty"]  # type: ignore[index]
        roster.adjust_loyalty("test_crew", 50)
        after_loyalty = roster.get_member_state("test_crew")["loyalty"]  # type: ignore[index]
        assert after_loyalty == initial_loyalty

    def test_crew_loyalty_no_flags(self) -> None:
        """Crew should never generate loyalty threshold flags."""
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)

        flags = roster.adjust_loyalty("test_crew", 100)
        assert flags == []

    def test_adjust_loyalty_all_skips_crew(self) -> None:
        """adjust_loyalty_all should skip non-companion crew."""
        crew = _crew_template()
        companion = _companion_template()
        roster = CrewRoster({"test_crew": crew, "test_companion": companion})
        roster.recruit("test_crew", 4)
        roster.recruit("test_companion", 4)

        roster.adjust_loyalty_all(20)
        crew_loyalty = roster.get_member_state("test_crew")["loyalty"]  # type: ignore[index]
        comp_loyalty = roster.get_member_state("test_companion")["loyalty"]  # type: ignore[index]

        # Crew loyalty unchanged from initial 30
        assert crew_loyalty == 30
        # Companion loyalty adjusted: 30 + 20 = 50
        assert comp_loyalty == 50


class TestCrewXP:
    """Tests for crew XP behavior (no XP gain)."""

    def test_crew_no_xp_gain(self) -> None:
        """Crew with max_level=1 should not gain XP."""
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)

        messages = roster.add_xp_to_all(100)
        state = roster.get_member_state("test_crew")
        assert state is not None
        assert state["xp"] == 0
        assert state["level"] == 1
        assert len(messages) == 0

    def test_crew_no_attribute_allocation(self) -> None:
        """Crew should not be able to allocate attribute points."""
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)

        success, msg = roster.allocate_crew_attribute("test_crew", "com")
        assert not success


class TestCrewRecruitment:
    """Tests for crew recruitment and dismissal."""

    def test_recruit_crew_succeeds(self) -> None:
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        success, name = roster.recruit("test_crew", 4)
        assert success
        assert name == "Test Crew"
        assert roster.is_recruited("test_crew")

    def test_dismiss_crew_succeeds(self) -> None:
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)
        success, msg = roster.dismiss("test_crew")
        assert success
        assert not roster.is_recruited("test_crew")
        assert roster.is_dismissed("test_crew")

    def test_crew_dismiss_and_rerecruit(self) -> None:
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)
        roster.dismiss("test_crew")
        success, _ = roster.recruit("test_crew", 4)
        assert success
        assert roster.is_recruited("test_crew")

    def test_crew_no_departure_risk(self) -> None:
        """Crew should never depart since their loyalty stays fixed."""
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)

        # Even calling process_departures shouldn't remove crew
        departures = roster.process_departures()
        assert len(departures) == 0
        assert roster.is_recruited("test_crew")


class TestCrewAvailableAtSystem:
    """Tests for finding available crew at a system."""

    def test_get_available_crew_at_system(self) -> None:
        """Should find unrecruited, undismissed crew at a system."""
        crew1 = CrewTemplate(
            id="crew_a",
            name="Crew A",
            role="handler",
            description="At breakstone.",
            portrait_color=[100, 100, 100],
            max_level=1,
            xp_thresholds=[0],
            home_system_id="breakstone",
            is_companion=False,
        )
        crew2 = CrewTemplate(
            id="crew_b",
            name="Crew B",
            role="analyst",
            description="At nexus.",
            portrait_color=[100, 100, 100],
            max_level=1,
            xp_thresholds=[0],
            home_system_id="nexus_prime",
            is_companion=False,
        )
        companion = CrewTemplate(
            id="comp_a",
            name="Companion A",
            role="navigator",
            description="Also at breakstone but companion.",
            portrait_color=[100, 100, 100],
            home_system_id="breakstone",
            is_companion=True,
        )
        roster = CrewRoster({"crew_a": crew1, "crew_b": crew2, "comp_a": companion})

        available = roster.get_available_crew_at_system("breakstone")
        ids = [t.id for t, in_available in [(t, True) for t in available]]
        assert "crew_a" in ids
        assert "crew_b" not in ids  # Wrong system
        # Companions should not appear in available crew
        assert "comp_a" not in ids

    def test_recruited_crew_not_available(self) -> None:
        crew = _crew_template()
        roster = CrewRoster({"test_crew": crew})
        roster.recruit("test_crew", 4)

        available = roster.get_available_crew_at_system("breakstone")
        assert len(available) == 0
