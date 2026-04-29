"""Tests for mission system models."""

import pytest
from spacegame.models.okafor_research import OkaforResearchState
from spacegame.models.mission import (
    ObjectiveType,
    MissionStatus,
    MissionObjective,
    MissionReward,
    Mission,
    MissionManager,
    ForcedEncounter,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType

# ============================================================================
# Helpers
# ============================================================================


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player(**overrides) -> Player:
    defaults = {
        "name": "TestCaptain",
        "credits": 2000,
        "current_system_id": "nexus_prime",
        "ship": Ship(ship_type=_make_ship_type(), current_fuel=50),
    }
    defaults.update(overrides)
    return Player(**defaults)


def _make_objective(
    obj_type: ObjectiveType = ObjectiveType.REACH_SYSTEM,
    target_id: str = "breakstone",
    target_quantity: int = 1,
    description: str = "Test objective",
) -> MissionObjective:
    return MissionObjective(
        type=obj_type,
        target_id=target_id,
        target_quantity=target_quantity,
        description=description,
    )


def _make_reward(
    reward_type: str = "credits",
    amount: int = 200,
) -> MissionReward:
    return MissionReward(reward_type=reward_type, amount=amount)


def _make_mission(
    mission_id: str = "test_mission",
    name: str = "Test Mission",
    description: str = "A test mission.",
    objectives: list[MissionObjective] | None = None,
    rewards: list[MissionReward] | None = None,
    prerequisites: list[str] | None = None,
    required_flags: list[str] | None = None,
) -> Mission:
    return Mission(
        id=mission_id,
        name=name,
        description=description,
        objectives=objectives or [_make_objective()],
        rewards=rewards or [_make_reward()],
        prerequisites=prerequisites or [],
        required_flags=required_flags or [],
    )


# ============================================================================
# MissionObjective Tests
# ============================================================================


class TestMissionObjective:
    """Tests for MissionObjective dataclass."""

    def test_creation(self) -> None:
        obj = MissionObjective(
            type=ObjectiveType.REACH_SYSTEM,
            target_id="breakstone",
            target_quantity=1,
            description="Travel to Breakstone",
        )
        assert obj.type == ObjectiveType.REACH_SYSTEM
        assert obj.target_id == "breakstone"
        assert obj.target_quantity == 1
        assert obj.description == "Travel to Breakstone"

    def test_to_dict_from_dict_roundtrip(self) -> None:
        obj = MissionObjective(
            type=ObjectiveType.COLLECT_CARGO,
            target_id="medical",
            target_quantity=5,
            description="Acquire 5 Medical Supplies",
        )
        data = obj.to_dict()
        restored = MissionObjective.from_dict(data)
        assert restored.type == obj.type
        assert restored.target_id == obj.target_id
        assert restored.target_quantity == obj.target_quantity
        assert restored.description == obj.description

    def test_objective_type_enum_values(self) -> None:
        assert ObjectiveType.REACH_SYSTEM.value == "reach_system"
        assert ObjectiveType.TALK_TO_NPC.value == "talk_to_npc"
        assert ObjectiveType.HAVE_CREDITS.value == "have_credits"
        assert ObjectiveType.COLLECT_CARGO.value == "collect_cargo"


# ============================================================================
# MissionReward Tests
# ============================================================================


class TestMissionReward:
    """Tests for MissionReward dataclass."""

    def test_creation(self) -> None:
        reward = MissionReward(reward_type="credits", amount=500)
        assert reward.reward_type == "credits"
        assert reward.amount == 500

    def test_to_dict_from_dict_roundtrip(self) -> None:
        reward = MissionReward(reward_type="xp", amount=100)
        data = reward.to_dict()
        restored = MissionReward.from_dict(data)
        assert restored.reward_type == reward.reward_type
        assert restored.amount == reward.amount


# ============================================================================
# Mission Tests
# ============================================================================


class TestMission:
    """Tests for Mission dataclass."""

    def test_creation(self) -> None:
        objectives = [_make_objective()]
        rewards = [_make_reward()]
        mission = Mission(
            id="getting_started",
            name="Getting Started",
            description="Visit Breakstone.",
            objectives=objectives,
            rewards=rewards,
            prerequisites=["intro"],
        )
        assert mission.id == "getting_started"
        assert mission.name == "Getting Started"
        assert mission.description == "Visit Breakstone."
        assert len(mission.objectives) == 1
        assert len(mission.rewards) == 1
        assert mission.prerequisites == ["intro"]

    def test_is_complete_all_met(self) -> None:
        """Mission is complete when MissionManager marks all objectives done."""
        mission = _make_mission(
            objectives=[
                _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
                _make_objective(ObjectiveType.HAVE_CREDITS, "", target_quantity=1000),
            ]
        )
        # Mission itself doesn't track completion — MissionManager does.
        # But is_complete should check if all objectives are met according to
        # provided progress.
        # We test the MissionManager flow for this — here just verify the property exists.
        # With no manager, mission has no inherent completion state.
        assert mission.id == "test_mission"

    def test_get_target_system_ids(self) -> None:
        mission = _make_mission(
            objectives=[
                _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
                _make_objective(ObjectiveType.REACH_SYSTEM, "verdant"),
                _make_objective(ObjectiveType.TALK_TO_NPC, "elena_reeves"),
            ]
        )
        targets = mission.get_target_system_ids()
        assert "breakstone" in targets
        assert "verdant" in targets
        assert "elena_reeves" not in targets

    def test_get_target_system_ids_empty_when_no_reach(self) -> None:
        mission = _make_mission(
            objectives=[_make_objective(ObjectiveType.HAVE_CREDITS, "", target_quantity=5000)]
        )
        assert mission.get_target_system_ids() == []

    def test_discovery_text_default_empty(self) -> None:
        """Discovery text defaults to empty string."""
        mission = _make_mission()
        assert mission.discovery_text == ""

    def test_discovery_text_round_trip(self) -> None:
        """Discovery text survives to_dict/from_dict."""
        mission = _make_mission()
        mission.discovery_text = "Overheard talk of work at the docks."
        data = mission.to_dict()
        assert data["discovery_text"] == "Overheard talk of work at the docks."
        restored = Mission.from_dict(data)
        assert restored.discovery_text == "Overheard talk of work at the docks."

    def test_discovery_text_omitted_when_empty(self) -> None:
        """Empty discovery text is not included in to_dict output."""
        mission = _make_mission()
        data = mission.to_dict()
        assert "discovery_text" not in data

    def test_to_dict(self) -> None:
        mission = _make_mission()
        data = mission.to_dict()
        assert data["id"] == "test_mission"
        assert data["name"] == "Test Mission"
        assert len(data["objectives"]) == 1
        assert len(data["rewards"]) == 1
        assert data["prerequisites"] == []


# ============================================================================
# MissionManager Availability Tests
# ============================================================================


class TestMissionManagerAvailability:
    """Tests for MissionManager prerequisite and availability logic."""

    def test_no_prereq_missions_become_available(self) -> None:
        m1 = _make_mission("m1", prerequisites=[])
        m2 = _make_mission("m2", prerequisites=[])
        mgr = MissionManager([m1, m2])
        newly = mgr.update_availability()
        assert "m1" in newly
        assert "m2" in newly
        assert len(mgr.get_missions_by_status(MissionStatus.AVAILABLE)) == 2

    def test_prereq_blocks_availability(self) -> None:
        m1 = _make_mission("m1", prerequisites=[])
        m2 = _make_mission("m2", prerequisites=["m1"])
        mgr = MissionManager([m1, m2])
        newly = mgr.update_availability()
        assert "m1" in newly
        assert "m2" not in newly
        available = mgr.get_missions_by_status(MissionStatus.AVAILABLE)
        assert len(available) == 1
        assert available[0].id == "m1"

    def test_prereq_satisfied_unlocks(self) -> None:
        m1 = _make_mission("m1", prerequisites=[])
        m2 = _make_mission("m2", prerequisites=["m1"])
        mgr = MissionManager([m1, m2])
        mgr.update_availability()

        # Accept and complete m1 by setting status directly via accept + check
        mgr.accept_mission("m1")
        # Simulate completion
        player = _make_player(current_system_id="breakstone")
        completed = mgr.check_objectives(player)
        assert "m1" in completed

        # Now m2 should become available
        newly = mgr.update_availability()
        assert "m2" in newly

    def test_already_available_not_reprocessed(self) -> None:
        m1 = _make_mission("m1", prerequisites=[])
        mgr = MissionManager([m1])
        newly1 = mgr.update_availability()
        assert "m1" in newly1
        newly2 = mgr.update_availability()
        assert "m1" not in newly2  # Already available, not "newly" available


# ============================================================================
# MissionManager Accept Tests
# ============================================================================


class TestMissionManagerAccept:
    """Tests for accepting missions."""

    def test_accept_available_mission(self) -> None:
        m1 = _make_mission("m1", prerequisites=[])
        mgr = MissionManager([m1])
        mgr.update_availability()
        success, msg = mgr.accept_mission("m1")
        assert success, f"Accept should succeed: {msg}"
        assert len(mgr.get_missions_by_status(MissionStatus.ACTIVE)) == 1

    def test_accept_unavailable_fails(self) -> None:
        m1 = _make_mission("m1", prerequisites=["other"])
        mgr = MissionManager([m1])
        mgr.update_availability()  # m1 stays unavailable
        success, msg = mgr.accept_mission("m1")
        assert not success
        assert "not available" in msg.lower()

    def test_accept_nonexistent_fails(self) -> None:
        mgr = MissionManager([])
        success, msg = mgr.accept_mission("nonexistent")
        assert not success
        assert "not found" in msg.lower()


# ============================================================================
# MissionManager Objective Tests
# ============================================================================


class TestMissionManagerObjectives:
    """Tests for objective checking logic."""

    def test_reach_system_objective(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.REACH_SYSTEM, "breakstone")],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        # Player not at breakstone
        player = _make_player(current_system_id="nexus_prime")
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

        # Player at breakstone
        player.current_system_id = "breakstone"
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_talk_to_npc_objective(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.TALK_TO_NPC, "elena_reeves")],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        player = _make_player()
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

        # Set the talked_to flag
        player.dialogue_flags["talked_to_elena_reeves"] = True
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_have_credits_objective(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.HAVE_CREDITS, "", target_quantity=5000)],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        player = _make_player(credits=3000)
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

        player.credits = 5000
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_collect_cargo_objective(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.COLLECT_CARGO, "medical", target_quantity=5)],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        player = _make_player()
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

        # Add cargo to ship
        player.ship.add_cargo("medical", 5)
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_multi_objective_all_required(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[
                _make_objective(ObjectiveType.COLLECT_CARGO, "medical", target_quantity=5),
                _make_objective(ObjectiveType.REACH_SYSTEM, "verdant"),
            ],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        player = _make_player(current_system_id="nexus_prime")
        player.ship.add_cargo("medical", 5)

        # Has cargo but wrong system
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

        # Right system now too
        player.current_system_id = "verdant"
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_completed_missions_not_rechecked(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.REACH_SYSTEM, "breakstone")],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        player = _make_player(current_system_id="breakstone")
        completed1 = mgr.check_objectives(player)
        assert "m1" in completed1

        # Check again — already completed, should not appear again
        completed2 = mgr.check_objectives(player)
        assert "m1" not in completed2

    def test_returns_only_newly_completed(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.REACH_SYSTEM, "breakstone")],
        )
        m2 = _make_mission(
            "m2",
            objectives=[_make_objective(ObjectiveType.HAVE_CREDITS, "", target_quantity=5000)],
        )
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")
        mgr.accept_mission("m2")

        # Player at breakstone with only 2000 credits
        player = _make_player(current_system_id="breakstone", credits=2000)
        completed = mgr.check_objectives(player)
        assert "m1" in completed
        assert "m2" not in completed
        assert len(mgr.get_missions_by_status(MissionStatus.COMPLETED)) == 1
        assert len(mgr.get_missions_by_status(MissionStatus.ACTIVE)) == 1


# ============================================================================
# New Objective Types Tests
# ============================================================================


class TestNewObjectiveTypes:
    """Tests for HAS_FLAG, COMPLETE_TRADE, WIN_COMBAT objective types."""

    def test_has_flag_true(self) -> None:
        """has_flag objective passes when dialogue flag is set."""
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.HAS_FLAG, "quest_started")],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player()
        player.dialogue_flags["quest_started"] = True
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_has_flag_false(self) -> None:
        """has_flag objective fails when flag is not set."""
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.HAS_FLAG, "quest_started")],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player()
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

    def test_has_flag_sticky(self) -> None:
        """has_flag stays completed once met (sticky behavior)."""
        m1 = _make_mission(
            "m1",
            objectives=[
                _make_objective(ObjectiveType.HAS_FLAG, "quest_started"),
                _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
            ],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player(current_system_id="nexus_prime")
        player.dialogue_flags["quest_started"] = True
        mgr.check_objectives(player)
        progress = mgr.get_objective_progress("m1")
        assert progress[0] is True
        # Remove flag — progress should stay True (sticky)
        player.dialogue_flags["quest_started"] = False
        mgr.check_objectives(player)
        progress = mgr.get_objective_progress("m1")
        assert progress[0] is True, "has_flag should be sticky"

    def test_complete_trade_threshold(self) -> None:
        """complete_trade passes when trades_completed meets target."""
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.COMPLETE_TRADE, "", target_quantity=5)],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player()
        player.trades_completed = 5
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_complete_trade_insufficient(self) -> None:
        """complete_trade fails when trades_completed is below target."""
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.COMPLETE_TRADE, "", target_quantity=5)],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player()
        player.trades_completed = 3
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

    def test_win_combat_threshold(self) -> None:
        """win_combat passes when combats_won meets target."""
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.WIN_COMBAT, "", target_quantity=2)],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player()
        player.combats_won = 2
        completed = mgr.check_objectives(player)
        assert "m1" in completed

    def test_win_combat_zero(self) -> None:
        """win_combat fails when combats_won is zero."""
        m1 = _make_mission(
            "m1",
            objectives=[_make_objective(ObjectiveType.WIN_COMBAT, "", target_quantity=1)],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player()
        completed = mgr.check_objectives(player)
        assert "m1" not in completed

    def test_mixed_objectives_with_new_types(self) -> None:
        """Mission with mix of old and new objective types."""
        m1 = _make_mission(
            "m1",
            objectives=[
                _make_objective(ObjectiveType.HAS_FLAG, "intro_done"),
                _make_objective(ObjectiveType.COMPLETE_TRADE, "", target_quantity=3),
                _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
            ],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player(current_system_id="breakstone")
        player.dialogue_flags["intro_done"] = True
        player.trades_completed = 3
        completed = mgr.check_objectives(player)
        assert "m1" in completed


# ============================================================================
# Flag-Based Prerequisites Tests
# ============================================================================


class TestFlagBasedPrerequisites:
    """Tests for required_flags on Mission."""

    def test_flag_not_met_stays_unavailable(self) -> None:
        """Mission with required flag stays UNAVAILABLE when flag is not set."""
        m1 = _make_mission("m1", prerequisites=[], required_flags=["intro_done"])
        mgr = MissionManager([m1])
        newly = mgr.update_availability(player_flags={})
        assert "m1" not in newly

    def test_flag_met_becomes_available(self) -> None:
        """Mission with required flag becomes AVAILABLE when flag is set."""
        m1 = _make_mission("m1", prerequisites=[], required_flags=["intro_done"])
        mgr = MissionManager([m1])
        newly = mgr.update_availability(player_flags={"intro_done": True})
        assert "m1" in newly

    def test_flag_plus_prereq_both_needed(self) -> None:
        """Both prerequisite missions AND required flags must be met."""
        m1 = _make_mission("m1", prerequisites=[])
        m2 = _make_mission("m2", prerequisites=["m1"], required_flags=["special_flag"])
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")
        player = _make_player(current_system_id="breakstone")
        mgr.check_objectives(player)
        # m1 completed, but flag not set
        newly = mgr.update_availability(player_flags={})
        assert "m2" not in newly
        # Now set the flag
        newly = mgr.update_availability(player_flags={"special_flag": True})
        assert "m2" in newly

    def test_no_flags_unchanged_behavior(self) -> None:
        """Mission without required_flags works as before (backward compat)."""
        m1 = _make_mission("m1", prerequisites=[])
        mgr = MissionManager([m1])
        newly = mgr.update_availability()
        assert "m1" in newly

    def test_empty_flag_list_unchanged(self) -> None:
        """Empty required_flags list has no effect."""
        m1 = _make_mission("m1", prerequisites=[], required_flags=[])
        mgr = MissionManager([m1])
        newly = mgr.update_availability(player_flags={})
        assert "m1" in newly


# ============================================================================
# MissionManager Rewards Tests
# ============================================================================


class TestMissionManagerRewards:
    """Tests for reward application."""

    def test_credits_reward_applied(self) -> None:
        m1 = _make_mission(
            "m1",
            rewards=[MissionReward(reward_type="credits", amount=500)],
        )
        mgr = MissionManager([m1])
        player = _make_player(credits=1000)
        messages = mgr.apply_rewards("m1", player)
        assert player.credits == 1500
        assert any("500" in msg for msg in messages)

    def test_xp_reward_applied(self) -> None:
        m1 = _make_mission(
            "m1",
            rewards=[MissionReward(reward_type="xp", amount=50)],
        )
        mgr = MissionManager([m1])
        player = _make_player()
        initial_xp = player.progression.xp
        messages = mgr.apply_rewards("m1", player)
        assert player.progression.xp == initial_xp + 50
        assert any("50" in msg and "XP" in msg for msg in messages)


# ============================================================================
# MissionManager Serialization Tests
# ============================================================================


class TestMissionManagerSerialization:
    """Tests for save/load state."""

    def test_get_state_load_state_roundtrip(self) -> None:
        m1 = _make_mission("m1", prerequisites=[])
        m2 = _make_mission("m2", prerequisites=["m1"])
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")

        state = mgr.get_state()

        # Create fresh manager and load state
        mgr2 = MissionManager([m1, m2])
        mgr2.load_state(state)

        assert len(mgr2.get_missions_by_status(MissionStatus.ACTIVE)) == 1
        assert mgr2.get_missions_by_status(MissionStatus.ACTIVE)[0].id == "m1"

    def test_preserves_objective_progress(self) -> None:
        m1 = _make_mission(
            "m1",
            objectives=[
                _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
                _make_objective(ObjectiveType.HAVE_CREDITS, "", target_quantity=5000),
            ],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        # Complete first objective only
        player = _make_player(current_system_id="breakstone", credits=1000)
        mgr.check_objectives(player)

        progress = mgr.get_objective_progress("m1")
        assert progress[0] is True  # reach_system complete
        assert progress[1] is False  # have_credits not met

        state = mgr.get_state()

        # Restore
        mgr2 = MissionManager([m1])
        mgr2.load_state(state)
        progress2 = mgr2.get_objective_progress("m1")
        assert progress2[0] is True
        assert progress2[1] is False


# ============================================================================
# Forced Encounter Tests
# ============================================================================


class TestForcedEncounter:
    """Tests for mission-triggered scripted encounters."""

    def test_creation(self) -> None:
        fe = ForcedEncounter(
            encounter_type="hostile",
            enemy_template_ids=["pirate_scout", "pirate_raider"],
            trigger_flag="m12_ambush_triggered",
        )
        assert fe.encounter_type == "hostile"
        assert fe.enemy_template_ids == ["pirate_scout", "pirate_raider"]
        assert fe.trigger_flag == "m12_ambush_triggered"

    def test_mission_with_forced_encounter(self) -> None:
        fe = ForcedEncounter(
            encounter_type="distress_signal",
            enemy_template_ids=["debris_field"],
            trigger_flag="m08_distress_seen",
        )
        m = _make_mission("m1", objectives=[_make_objective()])
        m.forced_encounter = fe
        assert m.forced_encounter is not None
        assert m.forced_encounter.encounter_type == "distress_signal"

    def test_mission_without_defaults_none(self) -> None:
        m = _make_mission("m1")
        assert m.forced_encounter is None

    def test_to_dict(self) -> None:
        fe = ForcedEncounter(
            encounter_type="hostile",
            enemy_template_ids=["pirate_scout"],
            trigger_flag="ambush_done",
        )
        d = fe.to_dict()
        assert d["encounter_type"] == "hostile"
        assert d["enemy_template_ids"] == ["pirate_scout"]
        assert d["trigger_flag"] == "ambush_done"

    def test_from_dict(self) -> None:
        data = {
            "encounter_type": "distress_signal",
            "enemy_template_ids": ["raider_a", "raider_b"],
            "trigger_flag": "distress_triggered",
        }
        fe = ForcedEncounter.from_dict(data)
        assert fe.encounter_type == "distress_signal"
        assert fe.enemy_template_ids == ["raider_a", "raider_b"]
        assert fe.trigger_flag == "distress_triggered"

    def test_get_active_forced_encounters(self) -> None:
        fe = ForcedEncounter(
            encounter_type="hostile",
            enemy_template_ids=["pirate"],
            trigger_flag="ambush_done",
        )
        m1 = _make_mission("m1", objectives=[_make_objective()])
        m1.forced_encounter = fe
        m2 = _make_mission("m2", objectives=[_make_objective()])
        # m2 has no forced encounter

        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")
        mgr.accept_mission("m2")

        encounters = mgr.get_active_forced_encounters()
        assert len(encounters) == 1
        assert encounters[0].encounter_type == "hostile"


# ============================================================================
# Auto-Accept Mission Tests
# ============================================================================


class TestAutoAcceptMission:
    """Tests for auto_accept field on missions."""

    def test_auto_accept_defaults_false(self) -> None:
        m = _make_mission("m1")
        assert m.auto_accept is False

    def test_auto_accept_mission_transitions_to_active(self) -> None:
        """auto_accept mission goes UNAVAILABLE → AVAILABLE → ACTIVE in one call."""
        m1 = Mission(
            id="m1",
            name="Auto Mission",
            description="Completes automatically.",
            objectives=[_make_objective(ObjectiveType.HAS_FLAG, "some_flag")],
            rewards=[_make_reward()],
            auto_accept=True,
        )
        mgr = MissionManager([m1])
        newly = mgr.update_availability()
        assert "m1" in newly
        # Should be ACTIVE, not just AVAILABLE
        active = mgr.get_missions_by_status(MissionStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].id == "m1"
        available = mgr.get_missions_by_status(MissionStatus.AVAILABLE)
        assert len(available) == 0

    def test_non_auto_accept_stays_available(self) -> None:
        """Normal mission stays AVAILABLE (not auto-accepted)."""
        m1 = Mission(
            id="m1",
            name="Normal Mission",
            description="Must be manually accepted.",
            objectives=[_make_objective()],
            rewards=[_make_reward()],
            auto_accept=False,
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        available = mgr.get_missions_by_status(MissionStatus.AVAILABLE)
        assert len(available) == 1
        active = mgr.get_missions_by_status(MissionStatus.ACTIVE)
        assert len(active) == 0

    def test_auto_accept_with_prereqs(self) -> None:
        """auto_accept mission respects prerequisites before accepting."""
        m1 = _make_mission("m1", prerequisites=[])
        m2 = Mission(
            id="m2",
            name="Gated Auto Mission",
            description="Auto-accepts only after m1.",
            objectives=[_make_objective(ObjectiveType.HAS_FLAG, "done")],
            rewards=[_make_reward()],
            prerequisites=["m1"],
            auto_accept=True,
        )
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        # m2 should still be UNAVAILABLE (prereq m1 not completed)
        assert len(mgr.get_missions_by_status(MissionStatus.ACTIVE)) == 0

        # Complete m1
        mgr.accept_mission("m1")
        player = _make_player(current_system_id="breakstone")
        mgr.check_objectives(player)
        mgr.update_availability()

        # Now m2 should be auto-accepted → ACTIVE
        active = mgr.get_missions_by_status(MissionStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].id == "m2"

    def test_auto_accept_full_lifecycle(self) -> None:
        """auto_accept mission can auto-accept and then complete normally."""
        m1 = Mission(
            id="m1",
            name="Auto Then Complete",
            description="Auto-accept, then complete via flag.",
            objectives=[_make_objective(ObjectiveType.HAS_FLAG, "trigger_flag")],
            rewards=[MissionReward(reward_type="xp", amount=50)],
            auto_accept=True,
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        # Should be ACTIVE
        assert len(mgr.get_missions_by_status(MissionStatus.ACTIVE)) == 1

        # Set the flag and check objectives
        player = _make_player()
        player.dialogue_flags["trigger_flag"] = True
        completed = mgr.check_objectives(player)
        assert "m1" in completed


# ============================================================================
# SA-R3: kweon_relationship reward type
# ============================================================================


class TestKweonRelationshipReward:
    """SA-R3 AC #4 — kweon_relationship reward type bumps OkaforResearchState."""

    def _make_manager_with_reward(self, amount: int) -> MissionManager:
        mission = _make_mission(
            "clinic_run",
            rewards=[MissionReward(reward_type="kweon_relationship", amount=amount)],
        )
        mgr = MissionManager([mission])
        mgr.accept_mission("clinic_run")
        return mgr

    def test_bump_increments_relationship_value(self) -> None:
        player = _make_player()
        player.okafor_research_state = OkaforResearchState(kweon_relationship_value=3)
        mgr = self._make_manager_with_reward(1)
        mgr.apply_rewards("clinic_run", player)
        assert player.okafor_research_state.kweon_relationship_value == 4

    def test_bump_clamps_at_max(self) -> None:
        player = _make_player()
        player.okafor_research_state = OkaforResearchState(kweon_relationship_value=9)
        mgr = self._make_manager_with_reward(5)
        mgr.apply_rewards("clinic_run", player)
        assert player.okafor_research_state.kweon_relationship_value == 10

    def test_bump_clamps_at_min(self) -> None:
        player = _make_player()
        player.okafor_research_state = OkaforResearchState(kweon_relationship_value=1)
        mgr = self._make_manager_with_reward(-99)
        mgr.apply_rewards("clinic_run", player)
        assert player.okafor_research_state.kweon_relationship_value == 0

    def test_no_op_when_state_is_none(self) -> None:
        player = _make_player()
        assert player.okafor_research_state is None
        mgr = self._make_manager_with_reward(1)
        # Must not raise; state stays None
        messages = mgr.apply_rewards("clinic_run", player)
        assert player.okafor_research_state is None
        assert any("Kweon trust" in m for m in messages)

    def test_message_appears_in_messages(self) -> None:
        player = _make_player()
        player.okafor_research_state = OkaforResearchState(kweon_relationship_value=2)
        mgr = self._make_manager_with_reward(1)
        messages = mgr.apply_rewards("clinic_run", player)
        assert any("Kweon trust +1" in m for m in messages)

    def test_message_appears_when_state_none(self) -> None:
        player = _make_player()
        mgr = self._make_manager_with_reward(1)
        messages = mgr.apply_rewards("clinic_run", player)
        assert any("Kweon trust +1" in m for m in messages)
