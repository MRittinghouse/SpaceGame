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
    for node_id in ("is_it_legal", "why_trust", "what_if_caught"):
        node = _dl().dialogue_trees["tomas_havens"].nodes[node_id]
        for reply in node.responses:
            if reply.set_flag == "declined_drifter_deal":
                assert any(accepted.get(f) for f in reply.excluded_flags), node_id
