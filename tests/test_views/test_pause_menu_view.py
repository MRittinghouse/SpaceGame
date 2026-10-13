"""The pause menu's Save waits for the conversation to end (the author's read of W3a, 2026-10-13).

A save between two replies would keep half a scene, so the menu greys Save out while a
dialogue is open; every other button works.
"""

from __future__ import annotations

from collections.abc import Iterator

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.views.pause_menu_view import PauseMenuView


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> Iterator[None]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _press(view: PauseMenuView, button: object) -> None:
    view.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": button}))


def test_save_is_greyed_out_inside_a_conversation() -> None:
    mgr = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = PauseMenuView(mgr, save_allowed=False)
    view.on_enter()
    assert view.save_button is not None
    assert not view.save_button.is_enabled
    _press(view, view.save_button)
    assert not view.should_show_save_dialog()
    view.on_exit()


def test_save_is_live_outside_a_conversation() -> None:
    mgr = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = PauseMenuView(mgr)
    view.on_enter()
    assert view.save_button is not None
    assert view.save_button.is_enabled
    _press(view, view.save_button)
    assert view.should_show_save_dialog()
    view.on_exit()
