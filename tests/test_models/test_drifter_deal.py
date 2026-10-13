"""Bug bash BB-71: Tomas's handshake resolves the deal his missions wait on."""

from __future__ import annotations

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.mission import MissionManager, MissionStatus
from spacegame.models.player import Player
from spacegame.models.ship import Ship

ACCEPT = [
    "[Sit down and eat]",
    "You mentioned you're a scout. Good money in that?",
    "What are you proposing?",
    "You've got a deal.",
    "I'll get it done.",
]
DECLINE = [*ACCEPT[:3], "Sorry, I don't bend rules.", "Thanks for the food, Tomas."]
DEFER = [
    *ACCEPT[:3],
    "Why should I trust you?",
    "I need to think about it. Not right now.",
    "Thanks for the food, Tomas.",
]


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _walk(choices: list[str], flags: dict[str, bool]) -> dict[str, bool]:
    """Play tomas_havens through the named replies and return the flags it leaves."""
    manager = DialogueManager()
    manager.load_flags(dict(flags))
    manager.start_dialogue(_dl().dialogue_trees["tomas_havens"], npc_id="tomas_drifter")
    for text in choices:
        replies = [r.text for r in manager.get_available_responses()]
        manager.select_response(replies.index(text))
    assert not manager.is_active
    return manager.get_flags()


def _opening() -> dict[str, bool]:
    return {"breakstone_permit_earned": True, "met_tomas_drifter": True}


def _player() -> Player:
    ship = Ship(ship_type=_dl().ship_types["shuttle"], current_fuel=40)
    return Player("TestPilot", 5000, "havens_rest", ship)


def _deal_manager() -> MissionManager:
    manager = MissionManager(_dl().missions)
    manager.load_state({"status": {"union_territory": "completed"}})
    return manager


def _settle(manager: MissionManager, player: Player) -> list[str]:
    """Run the check until it completes nothing, as the game's per-frame check does.

    One mission completes per check (bug bash BB-11), so a mission the walk's flags also
    finish can come first.
    """
    done: list[str] = []
    for _ in range(20):
        completed = manager.check_objectives(player)
        if not completed:
            break
        done += completed
    return done


def test_accepting_the_deal_resolves_it() -> None:
    flags = _walk(ACCEPT, _opening())
    assert flags.get("accepted_drifter_deal") and flags.get("drifter_deal_resolved")
    manager, player = _deal_manager(), _player()
    player.dialogue_flags.update(flags)
    manager.update_availability(player.dialogue_flags, game_day=30, player=player)
    if manager.get_status("the_drifters_deal") == MissionStatus.AVAILABLE:
        manager.accept_mission("the_drifters_deal", game_day=30, player=player)
    assert "the_drifters_deal" in _settle(manager, player)


def test_declining_the_deal_resolves_it_too() -> None:
    flags = _walk(DECLINE, _opening())
    assert flags.get("declined_drifter_deal") and flags.get("drifter_deal_resolved")
    assert not flags.get("accepted_drifter_deal")


def test_a_reopened_scene_never_sets_both_deal_flags() -> None:
    accepted = {**_opening(), "accepted_drifter_deal": True}
    for node_id in ("is_it_legal", "what_if_caught"):
        node = _dl().dialogue_trees["tomas_havens"].nodes[node_id]
        for reply in node.responses:
            if reply.set_flag == "declined_drifter_deal":
                assert any(accepted.get(f) for f in reply.excluded_flags), node_id
    # why_trust's second reply is Tomas's deferral (polish design 6): walking it sets neither.
    deferred = _walk(DEFER, _opening())
    assert not deferred.get("accepted_drifter_deal") and not deferred.get("declined_drifter_deal")


def _accepted_run() -> tuple[MissionManager, Player]:
    """The deal accepted at Tomas's table and completed, the delivery taken with its bales."""
    manager, player = _deal_manager(), _player()
    player.dialogue_flags.update(_walk(ACCEPT, _opening()))
    manager.update_availability(player.dialogue_flags, game_day=30, player=player)
    assert manager.get_status("the_drifters_deal") == MissionStatus.ACTIVE
    assert "the_drifters_deal" in _settle(manager, player)
    manager.complete_mission("the_drifters_deal", player)
    accepted = manager.update_availability(player.dialogue_flags, game_day=30, player=player)
    assert "drifters_delivery" in accepted
    assert manager.get_status("drifters_delivery") == MissionStatus.ACTIVE
    delivery = manager.get_mission("drifters_delivery")
    assert delivery is not None
    for cargo in delivery.on_accept_cargo:  # Game._load_auto_accept_cargo's part
        player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
    return manager, player


def test_the_handshake_runs_both_missions() -> None:
    manager, player = _accepted_run()
    player.current_system_id = "stellaris_port"
    assert "drifters_delivery" in _settle(manager, player)
    done = manager.complete_mission("drifters_delivery", player)
    assert player.ship.get_cargo_quantity("textiles") == 0
    assert "+300 Credits" in done.reward_messages
    assert "tomas_friendship" not in player.dialogue_flags


def test_sold_bales_must_be_held_again_to_finish() -> None:
    manager, player = _accepted_run()
    player.ship.remove_cargo("textiles", 5)
    player.current_system_id = "stellaris_port"
    assert "drifters_delivery" not in _settle(manager, player)
    player.ship.add_cargo("textiles", 5, 0)
    assert "drifters_delivery" in _settle(manager, player)


def test_friendship_comes_with_his_recruitment() -> None:
    recruit = next(m for m in _dl().missions if m.id == "recruit_trader")
    rewards = [(r.reward_type, r.target_id) for r in recruit.rewards]
    assert ("set_flag", "tomas_friendship") in rewards
    delivery = next(m for m in _dl().missions if m.id == "drifters_delivery")
    assert not [r for r in delivery.rewards if r.reward_type == "set_flag"]
