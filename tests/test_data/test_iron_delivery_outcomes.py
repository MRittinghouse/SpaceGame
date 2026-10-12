"""Bug bash BB-4: Elena, Footing the Bill and The Dead Ledger wait on the campaign's flag.

The flag ``iron_delivery_moved_on`` says the campaign no longer waits on Odom's errand.
The delivery's reward sets it, the betrayal's close sets it, and the job's clock sets it
(``spacegame.models.iron_consignment``), so no ending of the job ends the campaign.
"""

from __future__ import annotations

from spacegame.constants.flags import iron_delivery_moved_on
from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.iron_consignment import on_clock
from spacegame.models.mission import Mission, MissionManager, MissionStatus
from spacegame.models.player import Player
from spacegame.models.ship import Ship

FLAG = "iron_delivery_moved_on"


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _mission(mission_id: str) -> Mission:
    return next(m for m in _dl().missions if m.id == mission_id)


def test_the_helper_names_the_content_flag() -> None:
    assert iron_delivery_moved_on() == FLAG


def test_elena_comes_when_the_campaign_moves_on() -> None:
    assert _dl().npcs["elena_reeves"].auto_trigger_prerequisites == [FLAG]


def test_footing_the_bill_waits_on_the_flag_not_a_completed_delivery() -> None:
    footing = _mission("footing_the_bill")
    assert footing.prerequisites == ["bill_of_landing"]
    assert footing.required_flags == [FLAG, "talked_to_elena_cantina"]
    assert "settled or overdue" in footing.hint


def test_the_dead_ledger_waits_on_the_flag_not_a_completed_delivery() -> None:
    ledger = _mission("the_dead_ledger")
    assert ledger.available_after == "bill_of_landing"
    assert ledger.required_flags == [FLAG]


def test_the_delivery_sets_the_flag() -> None:
    rewards = [(r.reward_type, r.target_id) for r in _mission("iron_delivery").rewards]
    assert ("set_flag", FLAG) in rewards
    assert ("set_flag", "iron_ore_delivered") in rewards


def test_a_failed_delivery_no_longer_closes_the_campaign() -> None:
    manager = MissionManager(_dl().missions)
    manager.load_state({"status": {"bill_of_landing": "completed", "iron_delivery": "failed"}})
    flags = {"iron_delivery_failed": True, FLAG: True, "talked_to_elena_cantina": True}
    manager.update_availability(flags, game_day=12)
    assert manager.get_status("footing_the_bill") == MissionStatus.ACTIVE
    assert manager.get_status("the_dead_ledger") == MissionStatus.AVAILABLE


def test_a_job_left_open_moves_the_campaign_on_and_still_pays() -> None:
    dl = _dl()
    manager = MissionManager(dl.missions)
    manager.load_state(
        {
            "status": {"bill_of_landing": "completed", "iron_delivery": "active"},
            "accepted_day": {"iron_delivery": 1},
        }
    )
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    player = Player("TestPilot", 5000, "nexus_prime", ship)
    player.ship.add_cargo("iron_ore", 10, 0)
    assert on_clock(manager, player, player.dialogue_flags, 20)
    player.dialogue_flags["talked_to_elena_cantina"] = True
    manager.update_availability(player.dialogue_flags, game_day=20)
    assert manager.get_status("footing_the_bill") == MissionStatus.ACTIVE
    assert manager.get_status("iron_delivery") == MissionStatus.ACTIVE
    player.game_day = 25
    manager.apply_rewards("iron_delivery", player)
    assert player.credits == 5000 + 300


def _greet_targets(flags: dict[str, bool]) -> set[str]:
    manager = DialogueManager()
    manager.load_flags(flags)
    manager.start_dialogue(_dl().dialogue_trees["merchant_delivery"], "odom_broker")
    return {r.next_node_id for r in manager.get_available_responses()}


def test_a_finished_delivery_never_offers_the_betrayal() -> None:
    open_job = {"talked_to_cargo_broker": True, "broker_ore_sold": True}
    assert "betrayal" in _greet_targets(open_job)
    finished = {**open_job, "iron_ore_delivered": True, FLAG: True}
    targets = _greet_targets(finished)
    assert "thanks" in targets
    assert "betrayal" not in targets
