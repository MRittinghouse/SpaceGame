"""Tests that views properly clean up pygame_gui elements on exit.

Issue 5.4: Verifies on_enter() creates elements and on_exit() kills them,
preventing zombie UI elements that persist across state transitions.
"""

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from unittest.mock import MagicMock


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_ui_manager() -> pygame_gui.UIManager:
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _make_player() -> Player:
    dl = get_data_loader()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    return Player("TestCaptain", 5000, "nexus_prime", ship)


def _count_alive_elements(manager: pygame_gui.UIManager) -> int:
    """Count non-root alive UI elements managed by a UIManager."""
    # The root container is always present; count elements beyond it
    return len([e for e in manager.get_root_container().elements])


class TestMainMenuViewCleanup:
    def test_on_exit_kills_all_buttons(self) -> None:
        from spacegame.views.main_menu_view import MainMenuView

        mgr = _make_ui_manager()
        from spacegame.save_manager import SaveManager
        view = MainMenuView(mgr, SaveManager())
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create UI elements"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestPauseMenuViewCleanup:
    def test_on_exit_kills_all_buttons(self) -> None:
        from spacegame.views.pause_menu_view import PauseMenuView

        mgr = _make_ui_manager()
        view = PauseMenuView(mgr)
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create UI elements"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestSettingsViewCleanup:
    def test_on_exit_kills_all_elements(self) -> None:
        from spacegame.views.settings_view import SettingsView

        mgr = _make_ui_manager()
        from pathlib import Path
        import tempfile
        view = SettingsView(mgr, Path(tempfile.gettempdir()))
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create UI elements"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestSaveLoadViewCleanup:
    def test_on_exit_kills_all_elements(self) -> None:
        from spacegame.views.save_load_view import SaveLoadView
        from spacegame.save_manager import SaveManager

        mgr = _make_ui_manager()
        save_mgr = SaveManager()
        view = SaveLoadView(mgr, save_mgr, mode="load")
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create UI elements"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestNameInputViewCleanup:
    def test_on_exit_kills_all_elements(self) -> None:
        from spacegame.views.name_input_view import NameInputView

        mgr = _make_ui_manager()
        view = NameInputView(mgr)
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create name input + button"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestAchievementsViewCleanup:
    def test_on_exit_kills_back_button(self) -> None:
        from spacegame.views.achievements_view import AchievementsView
        from spacegame.achievement_manager import AchievementManager

        mgr = _make_ui_manager()
        dl = get_data_loader()
        player = _make_player()
        am = AchievementManager(dl.achievements)
        view = AchievementsView(mgr, player, am)
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create back button"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestStatisticsViewCleanup:
    def test_on_exit_kills_all_elements(self) -> None:
        from spacegame.views.statistics_view import StatisticsView

        mgr = _make_ui_manager()
        player = _make_player()
        view = StatisticsView(mgr, player)
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create UI elements"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"


class TestRepairBayViewCleanup:
    def test_on_exit_kills_all_elements(self) -> None:
        from spacegame.views.repair_bay_view import RepairBayView

        mgr = _make_ui_manager()
        player = _make_player()
        view = RepairBayView(mgr, player, cost_per_hp=5)
        before = _count_alive_elements(mgr)
        view.on_enter()
        during = _count_alive_elements(mgr)
        assert during > before, "on_enter should create UI elements"
        view.on_exit()
        after = _count_alive_elements(mgr)
        assert after == before, f"on_exit should kill all elements: {after} != {before}"
