"""Tests for campaign Act One features: trade permits, new reward types, on_accept_cargo."""

from spacegame.models.mission import (
    ObjectiveType,
    MissionStatus,
    MissionObjective,
    MissionReward,
    Mission,
    MissionManager,
    AcceptCargo,
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
    target_id: str = "",
) -> MissionReward:
    return MissionReward(reward_type=reward_type, amount=amount, target_id=target_id)


def _make_mission(
    mission_id: str = "test_mission",
    name: str = "Test Mission",
    description: str = "A test mission.",
    objectives: list[MissionObjective] | None = None,
    rewards: list[MissionReward] | None = None,
    prerequisites: list[str] | None = None,
    on_accept_cargo: list[AcceptCargo] | None = None,
    required_flags: list[str] | None = None,
    auto_accept: bool = False,
) -> Mission:
    return Mission(
        id=mission_id,
        name=name,
        description=description,
        objectives=objectives or [_make_objective()],
        rewards=rewards or [_make_reward()],
        prerequisites=prerequisites or [],
        on_accept_cargo=on_accept_cargo or [],
        required_flags=required_flags or [],
        auto_accept=auto_accept,
    )


# ============================================================================
# Trade Permits Tests
# ============================================================================


class TestTradePermits:
    """Tests for per-faction trade permit system on Player."""

    def test_player_starts_with_no_permits(self) -> None:
        player = _make_player()
        assert len(player.trade_permits) == 0, "New player should have no trade permits"

    def test_grant_trade_permit(self) -> None:
        player = _make_player()
        player.grant_trade_permit("commerce_guild")
        assert "commerce_guild" in player.trade_permits

    def test_has_trade_permit_true_after_grant(self) -> None:
        player = _make_player()
        assert not player.has_trade_permit("commerce_guild")
        player.grant_trade_permit("commerce_guild")
        assert player.has_trade_permit("commerce_guild")

    def test_has_trade_permit_false_for_other_faction(self) -> None:
        player = _make_player()
        player.grant_trade_permit("commerce_guild")
        assert not player.has_trade_permit("miners_union")

    def test_multiple_permits(self) -> None:
        player = _make_player()
        player.grant_trade_permit("commerce_guild")
        player.grant_trade_permit("miners_union")
        assert player.has_trade_permit("commerce_guild")
        assert player.has_trade_permit("miners_union")
        assert len(player.trade_permits) == 2

    def test_duplicate_grant_is_idempotent(self) -> None:
        player = _make_player()
        player.grant_trade_permit("commerce_guild")
        player.grant_trade_permit("commerce_guild")
        assert len(player.trade_permits) == 1


# ============================================================================
# Mission Reward Types Tests
# ============================================================================


class TestMissionRewardTypes:
    """Tests for new reward types: deduct_credits, remove_cargo."""

    def test_deduct_credits_reward(self) -> None:
        m1 = _make_mission(
            "m1",
            rewards=[MissionReward(reward_type="deduct_credits", amount=250)],
        )
        mgr = MissionManager([m1])
        player = _make_player(credits=2000)
        messages = mgr.apply_rewards("m1", player)
        assert player.credits == 1750, f"Should deduct 250 from 2000, got {player.credits}"
        assert any("250" in msg for msg in messages)

    def test_remove_cargo_reward(self) -> None:
        m1 = _make_mission(
            "m1",
            rewards=[MissionReward(reward_type="remove_cargo", amount=10, target_id="iron_ore")],
        )
        mgr = MissionManager([m1])
        player = _make_player()
        player.ship.add_cargo("iron_ore", 10)
        messages = mgr.apply_rewards("m1", player)
        assert player.ship.get_cargo_quantity("iron_ore") == 0, "Cargo should be removed"
        assert any("iron_ore" in msg for msg in messages)

    def test_collect_cargo_non_sticky(self) -> None:
        """collect_cargo objectives should flip back to False when cargo is sold."""
        m1 = _make_mission(
            "m1",
            objectives=[
                _make_objective(ObjectiveType.COLLECT_CARGO, "iron_ore", target_quantity=10),
                _make_objective(ObjectiveType.REACH_SYSTEM, "forgeworks"),
            ],
        )
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")

        player = _make_player(current_system_id="nexus_prime")
        player.ship.add_cargo("iron_ore", 10)

        # Check — cargo objective should be True
        mgr.check_objectives(player)
        progress = mgr.get_objective_progress("m1")
        assert progress[0] is True, "collect_cargo should be True with cargo"

        # Remove cargo — objective should flip back
        player.ship.remove_cargo("iron_ore", 10)
        mgr.check_objectives(player)
        progress = mgr.get_objective_progress("m1")
        assert progress[0] is False, "collect_cargo should flip to False after selling"

        # Reach destination without cargo — should NOT complete
        player.current_system_id = "forgeworks"
        completed = mgr.check_objectives(player)
        assert "m1" not in completed, "Mission should not complete without cargo"

        # Re-acquire cargo at destination — now should complete
        player.ship.add_cargo("iron_ore", 10)
        completed = mgr.check_objectives(player)
        assert "m1" in completed, "Mission should complete with cargo at destination"


# ============================================================================
# On-Accept Cargo Tests
# ============================================================================


class TestOnAcceptCargo:
    """Tests for AcceptCargo model and on_accept_cargo field."""

    def test_accept_cargo_creation(self) -> None:
        cargo = AcceptCargo(commodity_id="iron_ore", quantity=10)
        assert cargo.commodity_id == "iron_ore"
        assert cargo.quantity == 10

    def test_mission_has_on_accept_cargo(self) -> None:
        mission = _make_mission(
            on_accept_cargo=[AcceptCargo(commodity_id="iron_ore", quantity=10)],
        )
        assert len(mission.on_accept_cargo) == 1
        assert mission.on_accept_cargo[0].commodity_id == "iron_ore"
        assert mission.on_accept_cargo[0].quantity == 10

    def test_mission_without_on_accept_cargo(self) -> None:
        mission = _make_mission()
        assert len(mission.on_accept_cargo) == 0

    def test_on_accept_cargo_in_to_dict(self) -> None:
        mission = _make_mission(
            on_accept_cargo=[AcceptCargo(commodity_id="iron_ore", quantity=10)],
        )
        data = mission.to_dict()
        assert "on_accept_cargo" in data
        assert len(data["on_accept_cargo"]) == 1
        assert data["on_accept_cargo"][0]["commodity_id"] == "iron_ore"
        assert data["on_accept_cargo"][0]["quantity"] == 10


# ============================================================================
# Set Flag Reward Tests
# ============================================================================


class TestSetFlagReward:
    """Tests for set_flag reward type."""

    def test_sets_flag(self) -> None:
        """set_flag reward sets a dialogue flag on the player."""
        m1 = _make_mission(
            "m1",
            rewards=[MissionReward(reward_type="set_flag", amount=0, target_id="act1_complete")],
        )
        mgr = MissionManager([m1])
        player = _make_player()
        mgr.apply_rewards("m1", player)
        assert player.dialogue_flags.get("act1_complete") is True

    def test_reward_message(self) -> None:
        """set_flag reward produces a message."""
        m1 = _make_mission(
            "m1",
            rewards=[MissionReward(reward_type="set_flag", amount=0, target_id="act1_complete")],
        )
        mgr = MissionManager([m1])
        player = _make_player()
        messages = mgr.apply_rewards("m1", player)
        assert len(messages) >= 1


# ============================================================================
# Reputation Reward Tests
# ============================================================================


class TestReputationReward:
    """Tests for reputation reward type mechanics."""

    def test_positive(self) -> None:
        """Positive reputation reward increases faction standing."""
        player = _make_player()
        player.modify_reputation("commerce_guild", 10)
        assert player.faction_reputation["commerce_guild"] == 10

    def test_negative(self) -> None:
        """Negative reputation reward decreases faction standing."""
        player = _make_player()
        player.modify_reputation("miners_union", 20)
        player.modify_reputation("miners_union", -5)
        assert player.faction_reputation["miners_union"] == 15

    def test_new_faction(self) -> None:
        """Reputation reward for an unvisited faction starts from 0."""
        player = _make_player()
        player.modify_reputation("science_collective", 15)
        assert player.faction_reputation["science_collective"] == 15

    def test_accumulates(self) -> None:
        """Multiple reputation rewards accumulate."""
        player = _make_player()
        player.modify_reputation("commerce_guild", 10)
        player.modify_reputation("commerce_guild", 5)
        assert player.faction_reputation["commerce_guild"] == 15


# ============================================================================
# Campaign Mission Definition Tests
# ============================================================================


class TestCampaignMissions:
    """Tests for the specific campaign mission definitions."""

    def _make_bill_of_landing(self) -> Mission:
        return Mission(
            id="bill_of_landing",
            name="Bill of Landing",
            description="Acquire a trade permit.",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.TALK_TO_NPC,
                    target_id="officer_larsen",
                    target_quantity=1,
                    description="Speak with Customs Officer Larsen",
                ),
            ],
            rewards=[
                MissionReward(reward_type="deduct_credits", amount=250),
                MissionReward(reward_type="trade_permit", amount=0, target_id="current_system"),
                MissionReward(reward_type="xp", amount=20),
            ],
            prerequisites=[],
        )

    def _make_iron_delivery(self) -> Mission:
        return Mission(
            id="iron_delivery",
            name="Iron Ore Delivery",
            description="Deliver 10 iron ore to Forgeworks.",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.COLLECT_CARGO,
                    target_id="iron_ore",
                    target_quantity=10,
                    description="Have 10 Iron Ore in cargo",
                ),
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="forgeworks",
                    target_quantity=1,
                    description="Deliver to Forgeworks",
                ),
            ],
            rewards=[
                MissionReward(reward_type="credits", amount=500),
                MissionReward(reward_type="remove_cargo", amount=10, target_id="iron_ore"),
                MissionReward(reward_type="xp", amount=40),
            ],
            prerequisites=["bill_of_landing"],
            auto_accept=True,
            on_accept_cargo=[AcceptCargo(commodity_id="iron_ore", quantity=10)],
        )

    def test_bill_of_landing_available_on_start(self) -> None:
        bol = self._make_bill_of_landing()
        mgr = MissionManager([bol])
        newly = mgr.update_availability()
        assert "bill_of_landing" in newly, "Bill of landing should be available immediately"

    def test_bill_of_landing_completes_on_talk(self) -> None:
        bol = self._make_bill_of_landing()
        mgr = MissionManager([bol])
        mgr.update_availability()
        mgr.accept_mission("bill_of_landing")

        player = _make_player()
        # Not talked yet
        completed = mgr.check_objectives(player)
        assert "bill_of_landing" not in completed

        # Talk to Larsen
        player.dialogue_flags["talked_to_officer_larsen"] = True
        completed = mgr.check_objectives(player)
        assert "bill_of_landing" in completed

    def test_bill_of_landing_deducts_credits(self) -> None:
        bol = self._make_bill_of_landing()
        mgr = MissionManager([bol])
        player = _make_player(credits=2000)
        messages = mgr.apply_rewards("bill_of_landing", player)
        assert player.credits == 1750, f"Should deduct 250, got {player.credits}"

    def test_iron_delivery_requires_bill_of_landing(self) -> None:
        bol = self._make_bill_of_landing()
        delivery = self._make_iron_delivery()
        mgr = MissionManager([bol, delivery])
        mgr.update_availability()
        # Delivery should be unavailable
        assert "iron_delivery" not in [
            m.id for m in mgr.get_missions_by_status(MissionStatus.AVAILABLE)
        ]

    def test_iron_delivery_unlocks_after_bill(self) -> None:
        bol = self._make_bill_of_landing()
        delivery = self._make_iron_delivery()
        mgr = MissionManager([bol, delivery])
        mgr.update_availability()
        mgr.accept_mission("bill_of_landing")

        # Complete bill_of_landing
        player = _make_player()
        player.dialogue_flags["talked_to_officer_larsen"] = True
        mgr.check_objectives(player)

        # Now delivery should unlock
        newly = mgr.update_availability()
        assert "iron_delivery" in newly

    def test_iron_delivery_full_flow(self) -> None:
        """Test the full delivery mission: accept → cargo → travel → complete."""
        delivery = self._make_iron_delivery()
        mgr = MissionManager([delivery])
        # Force to available for this test
        mgr._status["iron_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("iron_delivery")

        player = _make_player(current_system_id="nexus_prime")
        # Simulate on_accept_cargo
        player.ship.add_cargo("iron_ore", 10, 0)

        # Not at forgeworks yet
        completed = mgr.check_objectives(player)
        assert "iron_delivery" not in completed

        # Arrive at forgeworks with cargo
        player.current_system_id = "forgeworks"
        completed = mgr.check_objectives(player)
        assert "iron_delivery" in completed

        # Apply rewards
        messages = mgr.apply_rewards("iron_delivery", player)
        assert player.credits == 2500, f"Should gain 500 credits, got {player.credits}"
        assert player.ship.get_cargo_quantity("iron_ore") == 0, "Cargo should be removed"


# ============================================================================
# One-Time Dialogue Trigger Tests
# ============================================================================


class TestLarsenDialogueTrigger:
    """Tests for the Officer Larsen one-time encounter guard."""

    def test_flag_prevents_retrigger(self) -> None:
        """Once talked_to_officer_larsen is True, the trigger should not fire."""
        player = _make_player(current_system_id="nexus_prime")
        player.dialogue_flags["talked_to_officer_larsen"] = True
        # Simulate the guard condition from game.py
        should_trigger = (
            player.current_system_id == "nexus_prime"
            and not player.dialogue_flags.get("talked_to_officer_larsen", False)
        )
        assert not should_trigger, "Larsen dialogue should not re-trigger once flag is set"

    def test_flag_absent_allows_trigger(self) -> None:
        """Without the flag, the trigger should fire on first visit."""
        player = _make_player(current_system_id="nexus_prime")
        should_trigger = (
            player.current_system_id == "nexus_prime"
            and not player.dialogue_flags.get("talked_to_officer_larsen", False)
        )
        assert should_trigger, "Larsen dialogue should trigger when flag is absent"

    def test_flag_not_triggered_at_other_systems(self) -> None:
        """The trigger should not fire at non-Nexus systems."""
        player = _make_player(current_system_id="breakstone")
        should_trigger = (
            player.current_system_id == "nexus_prime"
            and not player.dialogue_flags.get("talked_to_officer_larsen", False)
        )
        assert not should_trigger, "Larsen dialogue should not trigger at other systems"

    def test_flag_survives_serialization(self) -> None:
        """The flag should persist through a save/load cycle."""
        player = _make_player()
        player.dialogue_flags["talked_to_officer_larsen"] = True

        # Simulate save (to_dict equivalent for dialogue_flags)
        saved_flags = dict(player.dialogue_flags)

        # Simulate load
        new_player = _make_player()
        new_player.dialogue_flags = saved_flags

        assert new_player.dialogue_flags.get("talked_to_officer_larsen", False), (
            "talked_to_officer_larsen flag should survive save/load"
        )


class TestLarsenHideAfterPermit:
    """Tests that Officer Larsen disappears from the cantina after the permit is obtained."""

    def test_npc_hide_after_flag_field_exists(self) -> None:
        """NPC dataclass should support hide_after_flag field."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="test_npc",
            name="Test",
            title="Tester",
            portrait_color=(100, 100, 100),
            home_system_id="nexus_prime",
            dialogue_id="test_dialogue",
            hide_after_flag="some_flag",
        )
        assert npc.hide_after_flag == "some_flag"

    def test_npc_hide_after_flag_defaults_empty(self) -> None:
        """NPCs without hide_after_flag should default to empty string."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="test_npc",
            name="Test",
            title="Tester",
            portrait_color=(100, 100, 100),
            home_system_id="nexus_prime",
            dialogue_id="test_dialogue",
        )
        assert npc.hide_after_flag == ""

    def test_larsen_has_hide_after_flag_in_data(self) -> None:
        """Officer Larsen NPC data should have hide_after_flag set."""
        from spacegame.data_loader import get_data_loader

        loader = get_data_loader()
        larsen = loader.npcs.get("officer_larsen")
        assert larsen is not None, "Officer Larsen should exist in NPC data"
        assert larsen.hide_after_flag == "larsen_permit_complete", (
            "Larsen should be hidden after permit is complete"
        )

    def test_larsen_no_auto_trigger_gate_flag(self) -> None:
        """Larsen should NOT have auto_trigger_gate_flag (mission system handles his trigger)."""
        from spacegame.data_loader import get_data_loader

        loader = get_data_loader()
        larsen = loader.npcs.get("officer_larsen")
        assert larsen is not None
        assert larsen.auto_trigger_gate_flag == "", (
            "Larsen should not have auto_trigger_gate_flag — M01 handles his trigger"
        )

    def test_cantina_filters_hidden_npcs(self) -> None:
        """NPCs with hide_after_flag set in player.dialogue_flags should not appear in cantina."""
        from spacegame.models.dialogue import NPC

        npcs = [
            NPC(
                id="visible_npc",
                name="Visible",
                title="Test",
                portrait_color=(100, 100, 100),
                home_system_id="nexus_prime",
                dialogue_id="test1",
            ),
            NPC(
                id="hidden_npc",
                name="Hidden",
                title="Test",
                portrait_color=(100, 100, 100),
                home_system_id="nexus_prime",
                dialogue_id="test2",
                hide_after_flag="completed_flag",
            ),
        ]

        # Player has the flag set — hidden_npc should be filtered out
        player = _make_player()
        player.dialogue_flags["completed_flag"] = True

        filtered = [
            npc
            for npc in npcs
            if not npc.hide_after_flag
            or not player.dialogue_flags.get(npc.hide_after_flag, False)
        ]
        assert len(filtered) == 1
        assert filtered[0].id == "visible_npc"

    def test_cantina_shows_npc_before_flag_set(self) -> None:
        """NPCs with hide_after_flag should appear when the flag is NOT yet set."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="officer_larsen",
            name="Officer Larsen",
            title="Customs Officer",
            portrait_color=(140, 160, 180),
            home_system_id="nexus_prime",
            dialogue_id="larsen_customs",
            hide_after_flag="larsen_permit_complete",
        )

        player = _make_player()
        # Flag not set — NPC should be visible
        should_show = not npc.hide_after_flag or not player.dialogue_flags.get(
            npc.hide_after_flag, False
        )
        assert should_show, "Larsen should be visible before permit is obtained"


# ============================================================================
# Chapter 2 Mission Chain Tests (M03–M07)
# ============================================================================


class TestChapter2MissionChain:
    """Tests for the Chapter 2 story mission chain: M03–M07."""

    def _make_chapter2_missions(self) -> list[Mission]:
        """Build the full Chapter 2 mission set for chain testing."""
        return [
            _make_mission(
                "iron_delivery",
                name="Iron Ore Delivery",
                objectives=[
                    _make_objective(ObjectiveType.COLLECT_CARGO, "iron_ore", 10),
                    _make_objective(ObjectiveType.REACH_SYSTEM, "forgeworks"),
                ],
                rewards=[
                    _make_reward("credits", 500),
                    _make_reward("set_flag", 0, "iron_ore_delivered"),
                    _make_reward("xp", 40),
                ],
            ),
            _make_mission(
                "footing_the_bill",
                name="Footing the Bill",
                prerequisites=["iron_delivery"],
                required_flags=["talked_to_elena_cantina"],
                auto_accept=True,
                objectives=[
                    _make_objective(ObjectiveType.HAS_FLAG, "elena_gave_trading_tips"),
                ],
                rewards=[_make_reward("xp", 50)],
            ),
            _make_mission(
                "union_territory",
                name="Union Territory",
                prerequisites=["footing_the_bill"],
                required_flags=["met_hanna_voss"],
                objectives=[
                    _make_objective(ObjectiveType.COLLECT_CARGO, "food", 5),
                    _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
                ],
                rewards=[
                    _make_reward("remove_cargo", 5, "food"),
                    _make_reward("trade_permit", 0, "miners_union"),
                    _make_reward("set_flag", 0, "breakstone_permit_earned"),
                    _make_reward("xp", 75),
                ],
            ),
            _make_mission(
                "the_foremans_son",
                name="The Foreman's Son",
                prerequisites=["union_territory"],
                required_flags=["met_marcus_jin"],
                auto_accept=True,
                objectives=[
                    _make_objective(ObjectiveType.HAS_FLAG, "learned_father_story"),
                ],
                rewards=[
                    _make_reward("set_flag", 0, "completed_mining_tutorial"),
                    _make_reward("xp", 60),
                ],
            ),
            _make_mission(
                "the_scholars_errand",
                name="The Scholar's Errand",
                prerequisites=["union_territory"],
                required_flags=["met_priya_osei"],
                auto_accept=True,
                objectives=[
                    _make_objective(ObjectiveType.REACH_SYSTEM, "axiom_labs"),
                ],
                rewards=[
                    _make_reward("credits", 200),
                    _make_reward("set_flag", 0, "escorted_priya_axiom"),
                    _make_reward("xp", 80),
                ],
            ),
            _make_mission(
                "the_drifters_deal",
                name="The Drifter's Deal",
                prerequisites=["union_territory"],
                required_flags=["met_tomas_drifter"],
                auto_accept=True,
                objectives=[
                    _make_objective(ObjectiveType.HAS_FLAG, "drifter_deal_resolved"),
                ],
                rewards=[_make_reward("xp", 50)],
            ),
            _make_mission(
                "drifters_delivery",
                name="Drifter's Delivery",
                prerequisites=["the_drifters_deal"],
                required_flags=["accepted_drifter_deal"],
                on_accept_cargo=[AcceptCargo(commodity_id="textiles", quantity=5)],
                objectives=[
                    _make_objective(ObjectiveType.REACH_SYSTEM, "stellaris_port"),
                    _make_objective(ObjectiveType.COMPLETE_TRADE, "", 1),
                ],
                rewards=[
                    _make_reward("remove_cargo", 5, "textiles"),
                    _make_reward("credits", 300),
                    _make_reward("set_flag", 0, "tomas_friendship"),
                    _make_reward("set_flag", 0, "drifter_deal_resolved"),
                    _make_reward("xp", 80),
                ],
            ),
        ]

    def test_footing_the_bill_requires_flags_and_prereqs(self) -> None:
        """M03 needs iron_delivery completed AND talked_to_elena_cantina flag."""
        missions = self._make_chapter2_missions()
        mgr = MissionManager(missions)
        player = _make_player()

        # Complete iron_delivery
        mgr.update_availability()
        mgr._status["iron_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("iron_delivery")
        player.ship.add_cargo("iron_ore", 10)
        player.current_system_id = "forgeworks"
        mgr.check_objectives(player)
        mgr.apply_rewards("iron_delivery", player)

        # Without Elena flag, M03 stays unavailable
        mgr.update_availability(player.dialogue_flags)
        assert mgr._status["footing_the_bill"] == MissionStatus.UNAVAILABLE

        # Set Elena flag — M03 auto-accepts
        player.dialogue_flags["talked_to_elena_cantina"] = True
        mgr.update_availability(player.dialogue_flags)
        assert mgr._status["footing_the_bill"] == MissionStatus.ACTIVE, (
            "auto_accept mission should transition directly to ACTIVE"
        )

    def test_footing_the_bill_completes_on_flag(self) -> None:
        """M03 completes when elena_gave_trading_tips flag is set."""
        m03 = _make_mission(
            "footing_the_bill",
            auto_accept=True,
            objectives=[
                _make_objective(ObjectiveType.HAS_FLAG, "elena_gave_trading_tips"),
            ],
            rewards=[_make_reward("xp", 50)],
        )
        mgr = MissionManager([m03])
        mgr._status["footing_the_bill"] = MissionStatus.ACTIVE

        player = _make_player()
        # Not set yet
        completed = mgr.check_objectives(player)
        assert "footing_the_bill" not in completed

        # Set flag via dialogue
        player.dialogue_flags["elena_gave_trading_tips"] = True
        completed = mgr.check_objectives(player)
        assert "footing_the_bill" in completed

    def test_union_territory_cargo_and_location(self) -> None:
        """M04 requires 5 food at breakstone."""
        m04 = _make_mission(
            "union_territory",
            objectives=[
                _make_objective(ObjectiveType.COLLECT_CARGO, "food", 5),
                _make_objective(ObjectiveType.REACH_SYSTEM, "breakstone"),
            ],
            rewards=[
                _make_reward("remove_cargo", 5, "food"),
                _make_reward("trade_permit", 0, "miners_union"),
                _make_reward("set_flag", 0, "breakstone_permit_earned"),
            ],
        )
        mgr = MissionManager([m04])
        mgr._status["union_territory"] = MissionStatus.ACTIVE

        player = _make_player(current_system_id="nexus_prime")
        player.ship.add_cargo("food", 5)

        # Food but wrong location
        completed = mgr.check_objectives(player)
        assert "union_territory" not in completed

        # Right location with food
        player.current_system_id = "breakstone"
        completed = mgr.check_objectives(player)
        assert "union_territory" in completed

        # Apply rewards (trade_permit handled by engine, not MissionManager)
        mgr.apply_rewards("union_territory", player)
        assert player.ship.get_cargo_quantity("food") == 0
        assert player.dialogue_flags.get("breakstone_permit_earned") is True

    def test_m05_m06_m07_unlock_after_breakstone_permit(self) -> None:
        """M05, M06, M07 all unlock after union_territory + respective NPC flags."""
        missions = self._make_chapter2_missions()
        mgr = MissionManager(missions)
        player = _make_player()

        # Force chain to union_territory completed
        for mid in ["iron_delivery", "footing_the_bill", "union_territory"]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Set NPC meeting flags
        player.dialogue_flags["talked_to_elena_cantina"] = True
        player.dialogue_flags["met_hanna_voss"] = True
        player.dialogue_flags["met_marcus_jin"] = True
        player.dialogue_flags["met_priya_osei"] = True
        player.dialogue_flags["met_tomas_drifter"] = True
        player.dialogue_flags["breakstone_permit_earned"] = True

        mgr.update_availability(player.dialogue_flags)

        # All three should auto-accept to ACTIVE
        assert mgr._status["the_foremans_son"] == MissionStatus.ACTIVE
        assert mgr._status["the_scholars_errand"] == MissionStatus.ACTIVE
        assert mgr._status["the_drifters_deal"] == MissionStatus.ACTIVE

    def test_drifter_decline_path_resolves(self) -> None:
        """Declining the deal sets drifter_deal_resolved, auto-completing M07."""
        missions = self._make_chapter2_missions()
        mgr = MissionManager(missions)

        # Force drifters_deal to active
        for mid in ["iron_delivery", "footing_the_bill", "union_territory"]:
            mgr._status[mid] = MissionStatus.COMPLETED
        mgr._status["the_drifters_deal"] = MissionStatus.ACTIVE

        player = _make_player()
        player.dialogue_flags["declined_drifter_deal"] = True
        player.dialogue_flags["drifter_deal_resolved"] = True

        # drifters_deal should complete on the has_flag check
        completed = mgr.check_objectives(player)
        assert "the_drifters_deal" in completed

        # drifters_delivery should NOT become available (no accepted_drifter_deal)
        mgr.apply_rewards("the_drifters_deal", player)
        player.dialogue_flags["met_tomas_drifter"] = True
        mgr.update_availability(player.dialogue_flags)
        assert mgr._status["drifters_delivery"] == MissionStatus.UNAVAILABLE

    def test_drifter_accept_path_requires_delivery(self) -> None:
        """Accepting the deal opens drifters_delivery mission."""
        missions = self._make_chapter2_missions()
        mgr = MissionManager(missions)

        # Force drifters_deal to completed
        for mid in ["iron_delivery", "footing_the_bill", "union_territory", "the_drifters_deal"]:
            mgr._status[mid] = MissionStatus.COMPLETED

        player = _make_player()
        player.dialogue_flags["accepted_drifter_deal"] = True
        player.dialogue_flags["met_tomas_drifter"] = True

        newly = mgr.update_availability(player.dialogue_flags)
        assert "drifters_delivery" in newly
        assert mgr._status["drifters_delivery"] == MissionStatus.AVAILABLE

    def test_drifters_delivery_full_flow(self) -> None:
        """M07b: accept → cargo → travel → trade → complete."""
        m07b = _make_mission(
            "drifters_delivery",
            on_accept_cargo=[AcceptCargo(commodity_id="textiles", quantity=5)],
            objectives=[
                _make_objective(ObjectiveType.REACH_SYSTEM, "stellaris_port"),
                _make_objective(ObjectiveType.COMPLETE_TRADE, "", 1),
            ],
            rewards=[
                _make_reward("remove_cargo", 5, "textiles"),
                _make_reward("credits", 300),
                _make_reward("set_flag", 0, "drifter_deal_resolved"),
            ],
        )
        mgr = MissionManager([m07b])
        mgr._status["drifters_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("drifters_delivery")

        player = _make_player(current_system_id="havens_rest")
        player.ship.add_cargo("textiles", 5)

        # Not at stellaris yet
        completed = mgr.check_objectives(player)
        assert "drifters_delivery" not in completed

        # Arrive at stellaris, but haven't traded
        player.current_system_id = "stellaris_port"
        completed = mgr.check_objectives(player)
        assert "drifters_delivery" not in completed

        # Complete a trade
        player.trades_completed = 1
        completed = mgr.check_objectives(player)
        assert "drifters_delivery" in completed

        # Apply rewards
        mgr.apply_rewards("drifters_delivery", player)
        assert player.ship.get_cargo_quantity("textiles") == 0
        assert player.credits == 2300  # 2000 + 300
        assert player.dialogue_flags.get("drifter_deal_resolved") is True


# ============================================================================
# Chapter 2 Recruitment Gate Tests
# ============================================================================


class TestRecruitmentMissionGates:
    """Recruitment missions require Chapter 2 story missions + NPC flags."""

    def _make_recruit_with_prereqs(
        self, recruit_id: str, prereq: str, flag: str, target_system: str
    ) -> tuple[Mission, Mission]:
        """Create a prerequisite mission and its gated recruitment mission."""
        prereq_mission = _make_mission(prereq, name=prereq)
        recruit = _make_mission(
            recruit_id,
            name=f"Recruit {recruit_id}",
            prerequisites=[prereq],
            required_flags=[flag],
            objectives=[_make_objective(ObjectiveType.REACH_SYSTEM, target_system)],
            rewards=[_make_reward("crew", 0, recruit_id)],
        )
        return prereq_mission, recruit

    def test_recruit_navigator_gated(self) -> None:
        prereq, recruit = self._make_recruit_with_prereqs(
            "recruit_navigator", "footing_the_bill", "talked_to_elena_cantina", "nexus_prime"
        )
        mgr = MissionManager([prereq, recruit])
        mgr._status["footing_the_bill"] = MissionStatus.COMPLETED

        # Without flag
        mgr.update_availability()
        assert mgr._status["recruit_navigator"] == MissionStatus.UNAVAILABLE

        # With flag
        flags = {"talked_to_elena_cantina": True}
        mgr.update_availability(flags)
        assert mgr._status["recruit_navigator"] == MissionStatus.AVAILABLE

    def test_recruit_engineer_gated(self) -> None:
        prereq, recruit = self._make_recruit_with_prereqs(
            "recruit_engineer", "the_foremans_son", "met_marcus_jin", "breakstone"
        )
        mgr = MissionManager([prereq, recruit])
        mgr._status["the_foremans_son"] = MissionStatus.COMPLETED

        flags = {"met_marcus_jin": True}
        mgr.update_availability(flags)
        assert mgr._status["recruit_engineer"] == MissionStatus.AVAILABLE

    def test_recruit_scientist_gated(self) -> None:
        prereq, recruit = self._make_recruit_with_prereqs(
            "recruit_scientist", "the_scholars_errand", "met_priya_osei", "axiom_labs"
        )
        mgr = MissionManager([prereq, recruit])
        mgr._status["the_scholars_errand"] = MissionStatus.COMPLETED

        flags = {"met_priya_osei": True}
        mgr.update_availability(flags)
        assert mgr._status["recruit_scientist"] == MissionStatus.AVAILABLE

    def test_recruit_trader_gated(self) -> None:
        prereq, recruit = self._make_recruit_with_prereqs(
            "recruit_trader", "the_drifters_deal", "met_tomas_drifter", "havens_rest"
        )
        mgr = MissionManager([prereq, recruit])
        mgr._status["the_drifters_deal"] = MissionStatus.COMPLETED

        flags = {"met_tomas_drifter": True}
        mgr.update_availability(flags)
        assert mgr._status["recruit_trader"] == MissionStatus.AVAILABLE


# ============================================================================
# Auto-Trigger Logic Tests
# ============================================================================


class TestAutoTriggerLogic:
    """Tests for data-driven NPC auto-trigger conditions."""

    def test_trigger_fires_when_conditions_met(self) -> None:
        """Auto-trigger fires at NPC's home system with prerequisites."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="elena_reeves",
            name="Elena Reeves",
            title="Navigator",
            portrait_color=(100, 180, 255),
            home_system_id="nexus_prime",
            dialogue_id="elena_cantina",
            auto_trigger_gate_flag="talked_to_elena_cantina",
            auto_trigger_prerequisites=["iron_ore_delivered"],
        )
        player = _make_player(current_system_id="nexus_prime")
        player.dialogue_flags["iron_ore_delivered"] = True

        # Simulate the check from _check_auto_triggers
        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(
                player.dialogue_flags.get(f, False)
                for f in npc.auto_trigger_prerequisites
            )
        )
        assert should_trigger, "Elena should auto-trigger at nexus_prime after iron_ore_delivered"

    def test_trigger_blocked_by_gate_flag(self) -> None:
        """Auto-trigger does not fire when gate flag already set."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="elena_reeves",
            name="Elena Reeves",
            title="Navigator",
            portrait_color=(100, 180, 255),
            home_system_id="nexus_prime",
            dialogue_id="elena_cantina",
            auto_trigger_gate_flag="talked_to_elena_cantina",
            auto_trigger_prerequisites=["iron_ore_delivered"],
        )
        player = _make_player(current_system_id="nexus_prime")
        player.dialogue_flags["iron_ore_delivered"] = True
        player.dialogue_flags["talked_to_elena_cantina"] = True  # Already met

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(
                player.dialogue_flags.get(f, False)
                for f in npc.auto_trigger_prerequisites
            )
        )
        assert not should_trigger, "Should not re-trigger after gate flag is set"

    def test_trigger_blocked_by_missing_prereq(self) -> None:
        """Auto-trigger does not fire when prerequisites are not met."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="marcus_jin",
            name="Marcus Jin",
            title="Mining Foreman",
            portrait_color=(200, 160, 60),
            home_system_id="breakstone",
            dialogue_id="marcus_recognition",
            auto_trigger_gate_flag="met_marcus_jin",
            auto_trigger_prerequisites=["breakstone_permit_earned"],
        )
        player = _make_player(current_system_id="breakstone")
        # Missing breakstone_permit_earned

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(
                player.dialogue_flags.get(f, False)
                for f in npc.auto_trigger_prerequisites
            )
        )
        assert not should_trigger, "Should not trigger without prerequisites"

    def test_trigger_blocked_by_wrong_system(self) -> None:
        """Auto-trigger does not fire at the wrong system."""
        from spacegame.models.dialogue import NPC

        npc = NPC(
            id="tomas_drifter",
            name="Tomas Drifter",
            title="Frontier Scout",
            portrait_color=(110, 210, 120),
            home_system_id="havens_rest",
            dialogue_id="tomas_havens",
            auto_trigger_gate_flag="met_tomas_drifter",
            auto_trigger_prerequisites=["breakstone_permit_earned"],
        )
        player = _make_player(current_system_id="nexus_prime")
        player.dialogue_flags["breakstone_permit_earned"] = True

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(
                player.dialogue_flags.get(f, False)
                for f in npc.auto_trigger_prerequisites
            )
        )
        assert not should_trigger, "Tomas should not trigger at nexus_prime"
