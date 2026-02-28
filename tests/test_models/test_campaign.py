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
) -> Mission:
    return Mission(
        id=mission_id,
        name=name,
        description=description,
        objectives=objectives or [_make_objective()],
        rewards=rewards or [_make_reward()],
        prerequisites=prerequisites or [],
        on_accept_cargo=on_accept_cargo or [],
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
