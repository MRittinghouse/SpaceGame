"""Bug bash BB-1 and BB-11: a hand-over pays on what it takes, one contract at a time."""

from __future__ import annotations

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _iron(accepted_day: int = 1) -> MissionManager:
    manager = MissionManager(_dl().missions)
    manager.load_state(
        {"status": {"iron_delivery": "active"}, "accepted_day": {"iron_delivery": accepted_day}}
    )
    return manager


def _player(system_id: str = "forgeworks", day: int = 1) -> Player:
    ship = Ship(ship_type=_dl().ship_types["shuttle"], current_fuel=40)
    player = Player("TestPilot", 5000, system_id, ship)
    player.game_day = day
    return player


def _delivery(mission_id: str, destination: str = "verdant") -> Mission:
    return Mission(
        id=mission_id,
        name=mission_id,
        description="A test delivery.",
        objectives=[
            MissionObjective(type=ObjectiveType.COLLECT_CARGO, target_id="food", target_quantity=5),
            MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id=destination),
        ],
        rewards=[
            MissionReward(reward_type="credits", amount=300),
            MissionReward(reward_type="deliver_cargo", amount=5, target_id="food"),
        ],
        ordered_final=True,
    )


class TestDeliverCargo:
    def test_a_short_load_pays_on_what_is_weighed(self) -> None:
        manager, player = _iron(), _player()
        player.ship.add_cargo("iron_ore", 7, 0)
        messages = manager.apply_rewards("iron_delivery", player)
        assert player.credits == 5000 + 420
        assert player.ship.get_cargo_quantity("iron_ore") == 0
        assert "+420 Credits (7 of 10 delivered)" in messages
        assert "Delivered 7 iron_ore" in messages
        assert "+40 XP" in messages

    def test_late_and_short_name_both_clauses(self) -> None:
        manager, player = _iron(accepted_day=1), _player(day=16)
        player.ship.add_cargo("iron_ore", 7, 0)
        messages = manager.apply_rewards("iron_delivery", player)
        assert player.credits == 5000 + 315
        assert "+315 Credits (late, 75% of 600, 7 of 10 delivered)" in messages

    def test_a_full_load_reads_as_it_always_did(self) -> None:
        manager, player = _iron(), _player()
        player.ship.add_cargo("iron_ore", 12, 0)
        messages = manager.apply_rewards("iron_delivery", player)
        assert player.credits == 5000 + 600
        assert player.ship.get_cargo_quantity("iron_ore") == 2
        assert messages[:2] == ["+600 Credits", "Delivered 10 iron_ore"]

    def test_a_hand_over_leaves_another_missions_cargo_aboard(self) -> None:
        """Odom's ten stay aboard; a board delivery of iron ore takes only the captain's."""
        manager, player = _iron(), _player("verdant")
        manager.add_mission(
            Mission(
                id="proc_delivery_ore",
                name="ore",
                description="A test delivery.",
                objectives=[MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")],
                rewards=[
                    MissionReward(reward_type="credits", amount=200),
                    MissionReward(reward_type="deliver_cargo", amount=6, target_id="iron_ore"),
                ],
            ),
            MissionStatus.ACTIVE,
        )
        player.ship.add_cargo("iron_ore", 13, 0)
        manager.apply_rewards("proc_delivery_ore", player)
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert player.credits == 5000 + 100


class TestOneContractAtATime:
    def test_one_load_pays_one_contract(self) -> None:
        manager = MissionManager([])
        for mission_id in ("proc_delivery_a", "proc_delivery_b"):
            manager.add_mission(_delivery(mission_id), MissionStatus.ACTIVE)
        player = _player("verdant")
        player.ship.add_cargo("food", 5, 0)
        assert manager.check_objectives(player) == ["proc_delivery_a"]
        manager.complete_mission("proc_delivery_a", player)
        assert player.ship.get_cargo_quantity("food") == 0
        assert manager.check_objectives(player) == []
        assert manager.get_status("proc_delivery_b") == MissionStatus.ACTIVE
        assert player.credits == 5000 + 300

    def test_missions_met_together_complete_on_successive_checks(self) -> None:
        manager = MissionManager([])
        for mission_id in ("first", "second"):
            manager.add_mission(
                Mission(
                    id=mission_id,
                    name=mission_id,
                    description="A test trip.",
                    objectives=[
                        MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")
                    ],
                    rewards=[MissionReward(reward_type="xp", amount=10)],
                ),
                MissionStatus.ACTIVE,
            )
        player = _player("verdant")
        assert manager.check_objectives(player) == ["first"]
        assert manager.check_objectives(player) == ["second"]
        assert manager.check_objectives(player) == []


def _unpaired_remove_rewards(missions: list[Mission]) -> tuple[list[str], set[str]]:
    """Missions with a remove_cargo reward and no collect leg for it, and the ones checked."""
    checked: set[str] = set()
    unpaired: list[str] = []
    for mission in missions:
        for reward in mission.rewards:
            if reward.reward_type != "remove_cargo":
                continue
            checked.add(mission.id)
            if not any(
                o.type == ObjectiveType.COLLECT_CARGO
                and o.target_id == reward.target_id
                and o.target_quantity >= reward.amount
                for o in mission.objectives
            ):
                unpaired.append(mission.id)
    return unpaired, checked


class TestDeliverCargoContent:
    def test_each_remove_cargo_reward_has_its_collect_leg(self) -> None:
        """A remove_cargo reward draws only what its collect leg counted on free units.

        The completing check rechecks that leg on free units (bug bash BB-1), so the
        reward never takes a consigned unit; the cargo-removal registry relies on it.
        """
        unpaired, checked = _unpaired_remove_rewards(_dl().missions)
        assert unpaired == []
        assert {
            "union_territory",
            "the_crimson_run",
            "the_price_of_information",
            "miners_plight",
            "wrenchs_request",
        } <= checked

    def test_each_hand_over_names_the_accept_cargo(self) -> None:
        """At most one deliver_cargo a mission, its amount the cargo the mission loads."""
        for mission in _dl().missions:
            hand_overs = [r for r in mission.rewards if r.reward_type == "deliver_cargo"]
            assert len(hand_overs) <= 1, mission.id
            for reward in hand_overs:
                loaded = {c.commodity_id: c.quantity for c in mission.on_accept_cargo}
                if loaded:
                    assert loaded.get(reward.target_id) == reward.amount, mission.id

    def test_the_consignments_are_handed_over(self) -> None:
        by_id = {m.id: m for m in _dl().missions}
        consignments = (
            ("iron_delivery", "iron_ore", 10),
            ("cargo_lost", "electronics", 5),
            ("drifters_delivery", "textiles", 5),
            ("coolant_run", "machinery", 4),
        )
        for mission_id, good, amount in consignments:
            rewards = [(r.reward_type, r.target_id, r.amount) for r in by_id[mission_id].rewards]
            assert ("deliver_cargo", good, amount) in rewards, mission_id
            assert not any(kind == "remove_cargo" for kind, _, _ in rewards), mission_id
