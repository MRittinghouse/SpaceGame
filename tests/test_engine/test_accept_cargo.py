"""F-37 (bug bash BB-7): an availability pass loads the cargo of a mission it accepts."""

from __future__ import annotations

from unittest.mock import patch

from spacegame.data_loader import get_data_loader
from spacegame.engine.game import Game
from spacegame.models.mission import (
    AcceptCargo,
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship


def _game(flags: dict[str, bool]) -> tuple[Game, MissionManager]:
    dl = get_data_loader()
    dl.load_all()
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    game._player = Player("TestPilot", 5000, "nexus_prime", ship)
    game._player.dialogue_flags.update(flags)
    manager = MissionManager(dl.missions)
    manager.load_state({"status": {"bill_of_landing": "completed"}})
    game.mission_manager = manager
    game._mission_notifications = []
    return game, manager


def _contract(mission_id: str, auto_accept: bool) -> Mission:
    return Mission(
        id=mission_id,
        name=mission_id,
        description="A test contract.",
        objectives=[MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")],
        rewards=[MissionReward(reward_type="credits", amount=100)],
        on_accept_cargo=[AcceptCargo(commodity_id="food", quantity=2)],
        auto_accept=auto_accept,
    )


def test_a_dialogue_accepted_contract_loads_its_chip() -> None:
    game, manager = _game({"price_of_info_accepted": True})
    newly = manager.update_availability(game.player.dialogue_flags, game_day=1, player=game.player)
    assert "the_price_of_information" in newly
    for mission_id in newly:
        game._load_auto_accept_cargo(mission_id)
    assert game.player.ship.get_cargo_quantity("sealed_audit_chip") == 1
    assert "Cargo Loaded: 1 sealed_audit_chip" in game._mission_notifications


def test_only_an_accepted_auto_accept_mission_loads() -> None:
    game, manager = _game({})
    manager.add_mission(_contract("offered", auto_accept=False))
    manager.add_mission(_contract("waiting", auto_accept=True))
    game._load_auto_accept_cargo("offered")
    game._load_auto_accept_cargo("waiting")
    assert game.player.ship.get_cargo_quantity("food") == 0
    assert game._mission_notifications == []
