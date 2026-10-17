"""BB-1: the mission log's collect hint shows the count the collect leg tests.

A collect leg counts only the units no other active mission's accept cargo holds, so the
hint beside it must read the same free count rather than the raw main hold.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager, ObjectiveType
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.mission_log_view import MissionLogView


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _manager(**statuses: str) -> MissionManager:
    dl = get_data_loader()
    dl.load_all()
    manager = MissionManager(dl.missions)
    manager.load_state({"status": dict(statuses)})
    return manager


def _player(system_id: str) -> Player:
    dl = get_data_loader()
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    return Player("TestPilot", 5000, system_id, ship)


def _log_view(manager: MissionManager, player: Player) -> MissionLogView:
    ui = pygame_gui.UIManager((1280, 720))
    view = MissionLogView(ui, manager, data_loader=get_data_loader(), player=player)
    view.on_enter()
    return view


def _collect_leg(manager: MissionManager, mission_id: str):
    mission = manager.get_mission(mission_id)
    assert mission is not None
    return next(o for o in mission.objectives if o.type == ObjectiveType.COLLECT_CARGO)


def test_another_missions_accept_cargo_is_not_counted_in_the_hint() -> None:
    manager = _manager(the_heirloom_seeds="active", union_territory="active")
    player = _player("breakstone")
    player.ship.add_cargo("food", 7, 0)
    view = _log_view(manager, player)
    leg = _collect_leg(manager, "union_territory")
    assert view._get_objective_detail(leg, "union_territory") == "→ 4/5 in cargo for this mission"


def test_a_missions_own_accept_cargo_is_counted_in_its_hint() -> None:
    manager = _manager(iron_delivery="active")
    player = _player("nexus_prime")
    player.ship.add_cargo("iron_ore", 6, 0)
    view = _log_view(manager, player)
    leg = _collect_leg(manager, "iron_delivery")
    assert view._get_objective_detail(leg, "iron_delivery") == (
        f"→ 6/{leg.target_quantity} in cargo for this mission"
    )
