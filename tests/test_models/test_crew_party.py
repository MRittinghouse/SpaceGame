"""Tests for crew party management: dismiss state preservation, re-recruitment, costs, and blocking."""

from spacegame.models.crew import (
    CrewAbility,
    CrewTemplate,
    CrewRoster,
    LoyaltyTier,
)
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
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
    home_system_id: str = "stellaris_port",
    faction_id: str = "commerce_guild",
) -> CrewTemplate:
    if abilities is None:
        abilities = [
            _make_ability("fuel_efficiency_bonus", 2.0, "Efficient Routing", 1),
        ]
    return CrewTemplate(
        id=template_id,
        name=name,
        role=role,
        description=f"A test crew member: {name}",
        portrait_color=[100, 180, 255],
        abilities=abilities,
        home_system_id=home_system_id,
        faction_id=faction_id,
        is_companion=True,
    )


def _make_roster_with_recruited(
    template_id: str = "elena_reeves",
    **template_kwargs: object,
) -> tuple[CrewRoster, CrewTemplate]:
    """Create a roster with one recruited crew member."""
    template = _make_template(template_id=template_id, **template_kwargs)  # type: ignore[arg-type]
    roster = CrewRoster({template_id: template})
    roster.recruit(template_id, 4)
    return roster, template


# ============================================================================
# Step 1: Dismiss State Preservation
# ============================================================================


class TestDismissPreservesState:
    """Verify that dismiss() preserves crew state in _dismissed dict."""

    def test_dismiss_preserves_level_and_xp(self) -> None:
        roster, _ = _make_roster_with_recruited()
        # Level up the crew member
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["level"] = 3
        state["xp"] = 200

        success, _ = roster.dismiss("elena_reeves")
        assert success

        # Re-recruit and verify state preserved
        success, _ = roster.recruit("elena_reeves", 4)
        assert success
        restored = roster.get_member_state("elena_reeves")
        assert restored is not None
        assert restored["level"] == 3, "Level should be preserved"
        assert restored["xp"] == 200, "XP should be preserved"

    def test_dismiss_preserves_loyalty(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.adjust_loyalty("elena_reeves", 40)  # 30 + 40 = 70

        roster.dismiss("elena_reeves")
        roster.recruit("elena_reeves", 4)

        restored = roster.get_member_state("elena_reeves")
        assert restored is not None
        assert restored["loyalty"] == 70

    def test_dismiss_preserves_attributes(self) -> None:
        roster, _ = _make_roster_with_recruited()
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["attributes"]["com"] = 5
        state["attribute_points"] = 2

        roster.dismiss("elena_reeves")
        roster.recruit("elena_reeves", 4)

        restored = roster.get_member_state("elena_reeves")
        assert restored is not None
        assert restored["attributes"]["com"] == 5
        assert restored["attribute_points"] == 2

    def test_dismiss_preserves_bonus_abilities(self) -> None:
        roster, _ = _make_roster_with_recruited()
        ability = _make_ability("sell_price_bonus", 0.05, "Insider Network")
        roster.add_bonus_ability("elena_reeves", ability)

        roster.dismiss("elena_reeves")
        roster.recruit("elena_reeves", 4)

        restored = roster.get_member_state("elena_reeves")
        assert restored is not None
        assert len(restored.get("bonus_abilities", [])) == 1
        assert restored["bonus_abilities"][0]["description"] == "Insider Network"

    def test_dismiss_sets_location_to_home_system(self) -> None:
        roster, _ = _make_roster_with_recruited(home_system_id="stellaris_port")
        roster.dismiss("elena_reeves")

        assert roster.is_dismissed("elena_reeves")
        dismissed = roster.get_dismissed_at_system("stellaris_port")
        assert len(dismissed) == 1
        assert dismissed[0][0].id == "elena_reeves"

    def test_dismiss_sets_departed_false(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.dismiss("elena_reeves")

        dismissed = roster.get_dismissed_at_system("stellaris_port")
        assert len(dismissed) == 1
        _, state = dismissed[0]
        assert state["departed"] is False


# ============================================================================
# Step 1: Forced Departure State Preservation
# ============================================================================


class TestForcedDeparture:
    """Verify that process_departures() preserves state with departed=True."""

    def test_process_departures_preserves_state(self) -> None:
        roster, _ = _make_roster_with_recruited()
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["level"] = 4
        state["xp"] = 500
        # Drop loyalty to 0 to trigger departure
        roster.adjust_loyalty("elena_reeves", -30)

        departures = roster.process_departures()
        assert len(departures) == 1

        # Re-recruit and verify state preserved
        roster.recruit("elena_reeves", 4)
        restored = roster.get_member_state("elena_reeves")
        assert restored is not None
        assert restored["level"] == 4
        assert restored["xp"] == 500

    def test_process_departures_sets_departed_true(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.adjust_loyalty("elena_reeves", -30)
        roster.process_departures()

        dismissed = roster.get_dismissed_at_system("stellaris_port")
        assert len(dismissed) == 1
        _, state = dismissed[0]
        assert state["departed"] is True

    def test_process_departures_sets_location(self) -> None:
        roster, _ = _make_roster_with_recruited(home_system_id="stellaris_port")
        roster.adjust_loyalty("elena_reeves", -30)
        roster.process_departures()

        assert roster.is_dismissed("elena_reeves")
        at_stellaris = roster.get_dismissed_at_system("stellaris_port")
        assert len(at_stellaris) == 1
        at_other = roster.get_dismissed_at_system("breakstone")
        assert len(at_other) == 0


# ============================================================================
# Step 1: Re-Recruitment
# ============================================================================


class TestReRecruitment:
    """Verify recruit() restores preserved state for dismissed crew."""

    def test_recruit_restores_preserved_state(self) -> None:
        roster, _ = _make_roster_with_recruited()
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["level"] = 3
        state["loyalty"] = 70

        roster.dismiss("elena_reeves")
        assert "elena_reeves" not in roster._recruited

        success, msg = roster.recruit("elena_reeves", 4)
        assert success, f"Re-recruit should succeed: {msg}"
        assert "elena_reeves" in roster._recruited

    def test_recruit_restores_level_xp_loyalty(self) -> None:
        roster, _ = _make_roster_with_recruited()
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["level"] = 5
        state["xp"] = 700
        state["loyalty"] = 85

        roster.dismiss("elena_reeves")
        roster.recruit("elena_reeves", 4)

        restored = roster.get_member_state("elena_reeves")
        assert restored is not None
        assert restored["level"] == 5
        assert restored["xp"] == 700
        assert restored["loyalty"] == 85

    def test_recruit_restores_bonus_abilities(self) -> None:
        roster, _ = _make_roster_with_recruited()
        ability = _make_ability("cargo_bonus", 10.0, "Reinforced Plating")
        roster.add_bonus_ability("elena_reeves", ability)

        roster.dismiss("elena_reeves")
        roster.recruit("elena_reeves", 4)

        bonus = roster.get_bonus("cargo_bonus")
        assert bonus > 0, "Bonus ability should be active after re-recruit"

    def test_recruit_removes_from_dismissed(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.dismiss("elena_reeves")
        assert roster.is_dismissed("elena_reeves")

        roster.recruit("elena_reeves", 4)
        assert not roster.is_dismissed("elena_reeves")

    def test_recruit_dismissed_respects_slot_limit(self) -> None:
        template_a = _make_template("crew_a", "Crew A", home_system_id="sys_a")
        template_b = _make_template("crew_b", "Crew B", home_system_id="sys_b")
        roster = CrewRoster({"crew_a": template_a, "crew_b": template_b})

        # Recruit and dismiss crew_a
        roster.recruit("crew_a", 4)
        roster.dismiss("crew_a")

        # Fill all slots with crew_b
        roster.recruit("crew_b", 1)  # 1 slot total

        # Try to re-recruit crew_a — should fail, slot full
        success, msg = roster.recruit("crew_a", 1)
        assert not success, "Should fail when slots full"
        assert "No crew slots" in msg

    def test_fresh_recruit_still_gets_default_state(self) -> None:
        """A never-dismissed crew member gets fresh default state."""
        template = _make_template()
        roster = CrewRoster({"elena_reeves": template})

        roster.recruit("elena_reeves", 4)
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        assert state["level"] == 1
        assert state["xp"] == 0
        assert state["loyalty"] == 30


# ============================================================================
# Step 1: Dismissed Tracking Queries
# ============================================================================


class TestDismissedTracking:
    """Verify dismissed crew query methods."""

    def test_get_dismissed_at_system_filters_by_location(self) -> None:
        template_a = _make_template("crew_a", "Crew A", home_system_id="sys_a")
        template_b = _make_template("crew_b", "Crew B", home_system_id="sys_b")
        roster = CrewRoster({"crew_a": template_a, "crew_b": template_b})

        roster.recruit("crew_a", 4)
        roster.recruit("crew_b", 4)
        roster.dismiss("crew_a")
        roster.dismiss("crew_b")

        at_a = roster.get_dismissed_at_system("sys_a")
        assert len(at_a) == 1
        assert at_a[0][0].id == "crew_a"

        at_b = roster.get_dismissed_at_system("sys_b")
        assert len(at_b) == 1
        assert at_b[0][0].id == "crew_b"

    def test_is_dismissed_true_after_dismiss(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.dismiss("elena_reeves")
        assert roster.is_dismissed("elena_reeves")

    def test_is_dismissed_false_after_rerecruit(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.dismiss("elena_reeves")
        roster.recruit("elena_reeves", 4)
        assert not roster.is_dismissed("elena_reeves")

    def test_is_recruited_true_when_active(self) -> None:
        roster, _ = _make_roster_with_recruited()
        assert roster.is_recruited("elena_reeves")

    def test_is_recruited_false_when_dismissed(self) -> None:
        roster, _ = _make_roster_with_recruited()
        roster.dismiss("elena_reeves")
        assert not roster.is_recruited("elena_reeves")


# ============================================================================
# Step 1: Serialization
# ============================================================================


class TestDismissedSerialization:
    """Verify save/load round-trip with dismissed crew."""

    def test_roundtrip_with_dismissed_crew(self) -> None:
        roster, _ = _make_roster_with_recruited()
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["level"] = 3
        state["loyalty"] = 60

        roster.dismiss("elena_reeves")
        saved = roster.get_state()

        # Load into fresh roster
        template = _make_template()
        new_roster = CrewRoster({"elena_reeves": template})
        new_roster.load_state(saved)

        assert new_roster.is_dismissed("elena_reeves")
        assert not new_roster.is_recruited("elena_reeves")

        # Re-recruit from loaded state
        new_roster.recruit("elena_reeves", 4)
        restored = new_roster.get_member_state("elena_reeves")
        assert restored is not None
        assert restored["level"] == 3
        assert restored["loyalty"] == 60

    def test_load_old_save_without_dismissed_key(self) -> None:
        """Backward compat: old saves have no 'dismissed' key."""
        template = _make_template()
        roster = CrewRoster({"elena_reeves": template})

        old_save = {
            "recruited": ["elena_reeves"],
            "members": {
                "elena_reeves": {
                    "level": 2,
                    "xp": 100,
                    "loyalty": 45,
                    "attributes": {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 1},
                    "attribute_points": 0,
                    "bonus_abilities": [],
                }
            },
        }
        roster.load_state(old_save)

        assert roster.is_recruited("elena_reeves")
        assert not roster.is_dismissed("elena_reeves")
        # _dismissed should be empty
        assert roster.get_dismissed_at_system("stellaris_port") == []

    def test_dismissed_state_survives_save_load(self) -> None:
        roster, _ = _make_roster_with_recruited()
        # Set departed via process_departures
        roster.adjust_loyalty("elena_reeves", -30)
        roster.process_departures()

        saved = roster.get_state()

        template = _make_template()
        new_roster = CrewRoster({"elena_reeves": template})
        new_roster.load_state(saved)

        dismissed = new_roster.get_dismissed_at_system("stellaris_port")
        assert len(dismissed) == 1
        _, state = dismissed[0]
        assert state["departed"] is True


# ============================================================================
# Step 2: Re-recruitment Costs
# ============================================================================


class TestReRecruitCost:
    """Verify credit costs scale with loyalty tier and departed flag."""

    def _dismiss_at_loyalty(
        self, loyalty: int, departed: bool = False
    ) -> CrewRoster:
        roster, _ = _make_roster_with_recruited()
        # Set loyalty to desired value
        roster.adjust_loyalty("elena_reeves", loyalty - 30)  # starts at 30
        if departed:
            # Force loyalty to 0 for departure
            roster.adjust_loyalty("elena_reeves", -loyalty)
            roster.process_departures()
            # Manually fix loyalty in dismissed state to test cost at target tier
            roster._dismissed["elena_reeves"]["loyalty"] = loyalty
        else:
            roster.dismiss("elena_reeves")
        return roster

    def test_cost_zero_for_devoted(self) -> None:
        roster = self._dismiss_at_loyalty(90)
        assert roster.get_recruit_cost("elena_reeves") == 0

    def test_cost_zero_for_loyal(self) -> None:
        roster = self._dismiss_at_loyalty(75)
        assert roster.get_recruit_cost("elena_reeves") == 0

    def test_cost_zero_for_warm(self) -> None:
        roster = self._dismiss_at_loyalty(55)
        assert roster.get_recruit_cost("elena_reeves") == 0

    def test_cost_moderate_for_neutral(self) -> None:
        from spacegame.config import CREW_RERECRUIT_NEUTRAL

        roster = self._dismiss_at_loyalty(35)
        assert roster.get_recruit_cost("elena_reeves") == CREW_RERECRUIT_NEUTRAL

    def test_cost_high_for_wary(self) -> None:
        from spacegame.config import CREW_RERECRUIT_WARY

        roster = self._dismiss_at_loyalty(20)
        assert roster.get_recruit_cost("elena_reeves") == CREW_RERECRUIT_WARY

    def test_cost_harsh_for_discontented(self) -> None:
        from spacegame.config import CREW_RERECRUIT_DISCONTENTED

        roster = self._dismiss_at_loyalty(5)
        assert roster.get_recruit_cost("elena_reeves") == CREW_RERECRUIT_DISCONTENTED

    def test_departed_surcharge_added(self) -> None:
        from spacegame.config import CREW_RERECRUIT_NEUTRAL, CREW_DEPARTED_SURCHARGE

        roster = self._dismiss_at_loyalty(35, departed=True)
        expected = CREW_RERECRUIT_NEUTRAL + CREW_DEPARTED_SURCHARGE
        assert roster.get_recruit_cost("elena_reeves") == expected

    def test_cost_zero_for_non_dismissed(self) -> None:
        template = _make_template()
        roster = CrewRoster({"elena_reeves": template})
        assert roster.get_recruit_cost("elena_reeves") == 0


# ============================================================================
# Step 3: Dismiss Blocking
# ============================================================================


class TestDismissBlocking:
    """Verify can_dismiss() blocks Priya during lab_rat mission."""

    def test_can_dismiss_blocks_priya_during_lab_rat(self) -> None:
        template = _make_template(
            "dr_priya_osei", "Dr. Priya Osei", "scientist",
            home_system_id="axiom_labs",
        )
        roster = CrewRoster({"dr_priya_osei": template})
        roster.recruit("dr_priya_osei", 4)

        can, reason = roster.can_dismiss("dr_priya_osei", ["lab_rat", "some_other"])
        assert not can, "Priya should be blocked during lab_rat"
        assert "Lab Rat" in reason

    def test_can_dismiss_allows_priya_when_lab_rat_not_active(self) -> None:
        template = _make_template(
            "dr_priya_osei", "Dr. Priya Osei", "scientist",
            home_system_id="axiom_labs",
        )
        roster = CrewRoster({"dr_priya_osei": template})
        roster.recruit("dr_priya_osei", 4)

        can, reason = roster.can_dismiss("dr_priya_osei", ["some_other_mission"])
        assert can, f"Priya should be dismissable without lab_rat: {reason}"

    def test_can_dismiss_allows_other_crew_during_lab_rat(self) -> None:
        roster, _ = _make_roster_with_recruited()

        can, reason = roster.can_dismiss("elena_reeves", ["lab_rat"])
        assert can, f"Elena should always be dismissable: {reason}"


# ============================================================================
# Step 4: Crew Quest Gating on Party Membership
# ============================================================================


def _make_player_stub(
    system_id: str = "stellaris_port",
    credits: int = 5000,
    flags: dict[str, bool] | None = None,
) -> object:
    """Create a minimal player-like object for mission objective checks."""

    class PlayerStub:
        def __init__(self) -> None:
            self.current_system_id = system_id
            self.credits = credits
            self.dialogue_flags: dict[str, bool] = flags or {}
            self.trades_completed = 0
            self.combats_won = 0
            self.ship = type("Ship", (), {"get_cargo_quantity": lambda self, x: 0})()

    return PlayerStub()


class TestCrewQuestGating:
    """Verify crew quests skip objective checks when crew not recruited."""

    def _make_crew_mission(
        self, mission_id: str = "elena_old_charts", crew_member_id: str = "elena_reeves"
    ) -> Mission:
        return Mission(
            id=mission_id,
            name="Old Charts",
            description="Elena's quest",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="stellaris_port",
                    description="Travel to Stellaris Port",
                ),
            ],
            rewards=[],
            auto_accept=True,
            mission_type="crew",
            crew_member_id=crew_member_id,
        )

    def test_crew_quest_skipped_when_crew_not_recruited(self) -> None:
        mission = self._make_crew_mission()
        mgr = MissionManager([mission])
        mgr._status["elena_old_charts"] = MissionStatus.ACTIVE

        player = _make_player_stub(system_id="stellaris_port")
        # Elena not in recruited set — quest should be skipped
        completed = mgr.check_objectives(player, recruited_crew_ids=set())
        assert "elena_old_charts" not in completed

    def test_crew_quest_progresses_when_crew_recruited(self) -> None:
        mission = self._make_crew_mission()
        mgr = MissionManager([mission])
        mgr._status["elena_old_charts"] = MissionStatus.ACTIVE

        player = _make_player_stub(system_id="stellaris_port")
        completed = mgr.check_objectives(
            player, recruited_crew_ids={"elena_reeves"}
        )
        assert "elena_old_charts" in completed

    def test_non_crew_mission_unaffected_by_recruited_ids(self) -> None:
        """Normal missions with no crew_member_id always evaluate."""
        mission = Mission(
            id="side_quest",
            name="Side Quest",
            description="A side quest",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="stellaris_port",
                ),
            ],
            rewards=[],
            mission_type="side",
        )
        mgr = MissionManager([mission])
        mgr._status["side_quest"] = MissionStatus.ACTIVE

        player = _make_player_stub(system_id="stellaris_port")
        completed = mgr.check_objectives(player, recruited_crew_ids=set())
        assert "side_quest" in completed

    def test_crew_quest_stays_active_when_crew_dismissed(self) -> None:
        """Crew quest should remain ACTIVE (not failed) when crew is dismissed."""
        mission = self._make_crew_mission()
        mgr = MissionManager([mission])
        mgr._status["elena_old_charts"] = MissionStatus.ACTIVE

        player = _make_player_stub(system_id="stellaris_port")
        # Check with Elena absent
        mgr.check_objectives(player, recruited_crew_ids=set())
        assert mgr._status["elena_old_charts"] == MissionStatus.ACTIVE
