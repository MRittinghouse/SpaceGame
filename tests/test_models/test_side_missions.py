"""Tests for side mission framework — model fields, filtering, and lifecycle."""

from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)


def _make_side_mission(
    mid: str = "side_test",
    name: str = "Test Side Mission",
    **kwargs,
) -> Mission:
    """Create a side mission with defaults for testing."""
    defaults = {
        "id": mid,
        "name": name,
        "description": "A test side mission.",
        "mission_type": "side",
        "objectives": [
            MissionObjective(
                type=ObjectiveType.REACH_SYSTEM,
                target_id="nexus_prime",
                description="Go to Nexus Prime",
            )
        ],
        "rewards": [MissionReward(reward_type="credits", amount=100)],
        "discovery_method": "station_board",
    }
    defaults.update(kwargs)
    return Mission(**defaults)


def _make_campaign_mission(
    mid: str = "campaign_test",
    name: str = "Test Campaign",
) -> Mission:
    """Create a campaign mission with defaults."""
    return Mission(
        id=mid,
        name=name,
        description="A campaign mission.",
        mission_type="campaign",
        objectives=[
            MissionObjective(
                type=ObjectiveType.HAS_FLAG,
                target_id="some_flag",
                description="Do something",
            )
        ],
        rewards=[MissionReward(reward_type="xp", amount=50)],
    )


# ============================================================================
# Mission Model Field Tests
# ============================================================================


class TestMissionTypeField:
    """Tests for the mission_type field on Mission."""

    def test_default_mission_type_is_campaign(self) -> None:
        """Mission type defaults to 'campaign' for backward compat."""
        m = Mission(id="x", name="X", description="X")
        assert m.mission_type == "campaign"

    def test_side_mission_type(self) -> None:
        """Side missions can be created with type 'side'."""
        m = _make_side_mission()
        assert m.mission_type == "side"

    def test_campaign_mission_type(self) -> None:
        """Campaign missions have type 'campaign'."""
        m = _make_campaign_mission()
        assert m.mission_type == "campaign"


class TestSideMissionFields:
    """Tests for new side mission framework fields."""

    def test_available_at_default_empty(self) -> None:
        """available_at defaults to empty list."""
        m = Mission(id="x", name="X", description="X")
        assert m.available_at == []

    def test_available_at_set(self) -> None:
        """available_at stores system IDs."""
        m = _make_side_mission(available_at=["nexus_prime", "breakstone"])
        assert m.available_at == ["nexus_prime", "breakstone"]

    def test_available_after_default_empty(self) -> None:
        """available_after defaults to empty string."""
        m = Mission(id="x", name="X", description="X")
        assert m.available_after == ""

    def test_available_after_set(self) -> None:
        """available_after stores campaign mission prerequisite."""
        m = _make_side_mission(available_after="bill_of_landing")
        assert m.available_after == "bill_of_landing"

    def test_available_before_default_empty(self) -> None:
        """available_before defaults to empty string."""
        m = Mission(id="x", name="X", description="X")
        assert m.available_before == ""

    def test_available_before_set(self) -> None:
        """available_before stores expiration campaign mission ID."""
        m = _make_side_mission(available_before="the_collapse")
        assert m.available_before == "the_collapse"

    def test_repeatable_default_false(self) -> None:
        """repeatable defaults to False."""
        m = Mission(id="x", name="X", description="X")
        assert m.repeatable is False

    def test_repeatable_set(self) -> None:
        """repeatable can be set to True."""
        m = _make_side_mission(repeatable=True)
        assert m.repeatable is True

    def test_discovery_method_default(self) -> None:
        """discovery_method defaults to empty string."""
        m = Mission(id="x", name="X", description="X")
        assert m.discovery_method == ""

    def test_discovery_method_set(self) -> None:
        """discovery_method stores how the quest is found."""
        m = _make_side_mission(discovery_method="encounter")
        assert m.discovery_method == "encounter"


class TestMissionSerialization:
    """Tests for to_dict/from_dict with new side mission fields."""

    def test_side_mission_round_trip(self) -> None:
        """Side mission serializes and deserializes all new fields."""
        original = _make_side_mission(
            available_at=["nexus_prime"],
            available_after="bill_of_landing",
            available_before="the_collapse",
            repeatable=False,
            discovery_method="npc",
        )
        data = original.to_dict()
        restored = Mission.from_dict(data)

        assert restored.mission_type == "side"
        assert restored.available_at == ["nexus_prime"]
        assert restored.available_after == "bill_of_landing"
        assert restored.available_before == "the_collapse"
        assert restored.repeatable is False
        assert restored.discovery_method == "npc"

    def test_campaign_mission_backward_compat(self) -> None:
        """Old campaign missions without new fields deserialize correctly."""
        data = {
            "id": "old_mission",
            "name": "Old Mission",
            "description": "From before side missions existed.",
            "objectives": [
                {"type": "reach_system", "target_id": "nexus_prime"}
            ],
            "rewards": [{"reward_type": "credits", "amount": 100}],
        }
        m = Mission.from_dict(data)
        assert m.mission_type == "campaign"
        assert m.available_at == []
        assert m.available_after == ""
        assert m.available_before == ""
        assert m.repeatable is False
        assert m.discovery_method == ""

    def test_to_dict_includes_new_fields(self) -> None:
        """to_dict includes mission_type and side mission fields."""
        m = _make_side_mission(
            available_at=["verdant"],
            discovery_method="station_board",
        )
        d = m.to_dict()
        assert d["mission_type"] == "side"
        assert d["available_at"] == ["verdant"]
        assert d["discovery_method"] == "station_board"


# ============================================================================
# MissionManager Side Mission Filtering
# ============================================================================


class TestMissionManagerSideFiltering:
    """Tests for MissionManager handling side missions."""

    def test_get_missions_by_type(self) -> None:
        """Can filter missions by type (campaign vs side)."""
        campaign = _make_campaign_mission("c1", "Campaign 1")
        side = _make_side_mission("s1", "Side 1")
        mgr = MissionManager([campaign, side])
        # Both start unavailable, make them available
        mgr._status["c1"] = MissionStatus.AVAILABLE
        mgr._status["s1"] = MissionStatus.AVAILABLE

        campaign_missions = mgr.get_missions_by_type("campaign")
        side_missions = mgr.get_missions_by_type("side")

        assert len(campaign_missions) == 1
        assert campaign_missions[0].id == "c1"
        assert len(side_missions) == 1
        assert side_missions[0].id == "s1"

    def test_get_available_side_missions_at_system(self) -> None:
        """Side missions filter by current system via available_at."""
        s1 = _make_side_mission("s1", available_at=["nexus_prime"])
        s2 = _make_side_mission("s2", available_at=["breakstone"])
        s3 = _make_side_mission("s3", available_at=["nexus_prime", "breakstone"])
        mgr = MissionManager([s1, s2, s3])
        mgr._status["s1"] = MissionStatus.AVAILABLE
        mgr._status["s2"] = MissionStatus.AVAILABLE
        mgr._status["s3"] = MissionStatus.AVAILABLE

        at_nexus = mgr.get_available_at_system("nexus_prime")
        assert {m.id for m in at_nexus} == {"s1", "s3"}

    def test_empty_available_at_means_available_everywhere(self) -> None:
        """Side missions with empty available_at are available at any system."""
        s = _make_side_mission("s1", available_at=[])
        mgr = MissionManager([s])
        mgr._status["s1"] = MissionStatus.AVAILABLE

        at_any = mgr.get_available_at_system("forgeworks")
        assert len(at_any) == 1

    def test_available_after_gates_on_campaign(self) -> None:
        """Side missions with available_after don't become available until that campaign mission is complete."""
        campaign = _make_campaign_mission("c1")
        side = _make_side_mission("s1", available_after="c1")
        mgr = MissionManager([campaign, side])

        # Campaign not complete — side should stay unavailable
        newly = mgr.update_availability()
        assert "s1" not in newly
        assert mgr._status["s1"] == MissionStatus.UNAVAILABLE

        # Complete the campaign mission
        mgr._status["c1"] = MissionStatus.COMPLETED
        newly = mgr.update_availability()
        assert "s1" in newly
        assert mgr._status["s1"] == MissionStatus.AVAILABLE

    def test_available_before_expires_mission(self) -> None:
        """Side missions with available_before expire when that campaign mission completes."""
        campaign_gate = _make_campaign_mission("c_gate")
        campaign_expire = _make_campaign_mission("c_expire")
        side = _make_side_mission(
            "s1",
            available_after="c_gate",
            available_before="c_expire",
        )
        mgr = MissionManager([campaign_gate, campaign_expire, side])

        # Gate complete, expiry not — should become available
        mgr._status["c_gate"] = MissionStatus.COMPLETED
        mgr.update_availability()
        assert mgr._status["s1"] == MissionStatus.AVAILABLE

        # Now complete the expiry mission
        mgr._status["c_expire"] = MissionStatus.COMPLETED
        mgr.expire_missions()
        assert mgr._status["s1"] == MissionStatus.UNAVAILABLE

    def test_active_mission_not_expired(self) -> None:
        """Active side missions are not expired even if available_before triggers."""
        campaign_expire = _make_campaign_mission("c_expire")
        side = _make_side_mission("s1", available_before="c_expire")
        mgr = MissionManager([campaign_expire, side])
        mgr._status["s1"] = MissionStatus.ACTIVE

        mgr._status["c_expire"] = MissionStatus.COMPLETED
        mgr.expire_missions()
        # Active missions should NOT be expired
        assert mgr._status["s1"] == MissionStatus.ACTIVE

    def test_completed_mission_not_expired(self) -> None:
        """Completed side missions are not expired."""
        campaign_expire = _make_campaign_mission("c_expire")
        side = _make_side_mission("s1", available_before="c_expire")
        mgr = MissionManager([campaign_expire, side])
        mgr._status["s1"] = MissionStatus.COMPLETED

        mgr._status["c_expire"] = MissionStatus.COMPLETED
        mgr.expire_missions()
        assert mgr._status["s1"] == MissionStatus.COMPLETED

    def test_get_current_hint_prefers_campaign(self) -> None:
        """get_current_hint prefers campaign missions over side missions."""
        campaign = Mission(
            id="c1", name="Campaign", description="C",
            mission_type="campaign", hint="Campaign hint",
            objectives=[MissionObjective(type=ObjectiveType.HAS_FLAG, target_id="x")],
        )
        side = Mission(
            id="s1", name="Side", description="S",
            mission_type="side", hint="Side hint",
            objectives=[MissionObjective(type=ObjectiveType.HAS_FLAG, target_id="y")],
        )
        mgr = MissionManager([campaign, side])
        mgr._status["c1"] = MissionStatus.ACTIVE
        mgr._status["s1"] = MissionStatus.ACTIVE

        hint = mgr.get_current_hint()
        assert hint is not None
        assert hint[0] == "Campaign"

    def test_side_mission_hint_shown_when_no_campaign(self) -> None:
        """Side mission hints show when no campaign missions are active."""
        side = Mission(
            id="s1", name="Side", description="S",
            mission_type="side", hint="Side hint",
            objectives=[MissionObjective(type=ObjectiveType.HAS_FLAG, target_id="y")],
        )
        mgr = MissionManager([side])
        mgr._status["s1"] = MissionStatus.ACTIVE

        hint = mgr.get_current_hint()
        assert hint is not None
        assert hint[0] == "Side"


class TestMissionManagerDiscovery:
    """Tests for discovery_method-based behavior."""

    def test_encounter_triggered_missions_listed(self) -> None:
        """Missions with discovery_method='encounter' can be queried."""
        s1 = _make_side_mission("s1", discovery_method="encounter")
        s2 = _make_side_mission("s2", discovery_method="npc")
        mgr = MissionManager([s1, s2])
        mgr._status["s1"] = MissionStatus.AVAILABLE
        mgr._status["s2"] = MissionStatus.AVAILABLE

        encounter_missions = mgr.get_missions_by_discovery("encounter")
        assert len(encounter_missions) == 1
        assert encounter_missions[0].id == "s1"

    def test_station_board_missions_listed(self) -> None:
        """Missions with discovery_method='station_board' can be queried."""
        s1 = _make_side_mission("s1", discovery_method="station_board")
        s2 = _make_side_mission("s2", discovery_method="station_board")
        s3 = _make_side_mission("s3", discovery_method="npc")
        mgr = MissionManager([s1, s2, s3])
        for sid in ["s1", "s2", "s3"]:
            mgr._status[sid] = MissionStatus.AVAILABLE

        board_missions = mgr.get_missions_by_discovery("station_board")
        assert len(board_missions) == 2
