"""The crew roster's Talk button asks the game to open the selected companion's scene."""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.views.crew_roster_view import CrewRosterView


def test_talk_asks_the_game_to_open_the_selected_companions_scene() -> None:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    roster = CrewRoster(dl.crew_templates)
    ok, msg = roster.recruit("elena_reeves", 4)
    assert ok, msg
    view = CrewRosterView(manager, roster, 4)
    view.on_enter()
    button = view._talk_btn
    assert button is not None and button.visible
    view.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center))
    assert view.pending_talk_id == "elena_reeves"
    assert view.next_state == GameState.DIALOGUE
    view.on_exit()
