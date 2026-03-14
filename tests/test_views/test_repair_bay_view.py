"""Tests for RepairBayView — hull repair service."""

import pygame
import pygame_gui
from spacegame.config import GameState, WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.data_loader import DataLoader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.repair_bay_view import RepairBayView


def _make_test_env(
    credits: int = 5000,
    hull_fraction: float = 0.5,
) -> tuple[pygame_gui.UIManager, Player, int]:
    """Create test environment. Returns (manager, player, cost_per_hp)."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    loader = DataLoader()
    loader.load_all()

    ship_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    ship.current_hull = int(ship_type.combat_hull * hull_fraction)
    player = Player("Test Captain", credits, "nexus_prime", ship)
    cost_per_hp = 10
    return manager, player, cost_per_hp


class TestRepairBayConstruction:
    """Tests for RepairBayView creation."""

    def test_create_repair_bay_view(self) -> None:
        manager, player, cost = _make_test_env()
        view = RepairBayView(
            ui_manager=manager, player=player, cost_per_hp=cost,
        )
        assert view is not None
        assert view.next_state is None

    def test_stores_cost_per_hp(self) -> None:
        manager, player, cost = _make_test_env()
        view = RepairBayView(
            ui_manager=manager, player=player, cost_per_hp=cost,
        )
        assert view.cost_per_hp == 10


class TestRepairBayLifecycle:
    """Tests for on_enter / on_exit."""

    def test_on_enter_sets_active(self) -> None:
        manager, player, cost = _make_test_env()
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_clears_active(self) -> None:
        manager, player, cost = _make_test_env()
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view.on_exit()
        assert not view.active


class TestRepairBayData:
    """Tests for repair cost calculations displayed to player."""

    def test_damage_amount(self) -> None:
        manager, player, cost = _make_test_env(hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        assert view.get_damage_amount() == 30  # shuttle max=60, half=30

    def test_repair_cost(self) -> None:
        manager, player, cost = _make_test_env(hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        assert view.get_repair_cost() == 300  # 30 HP * 10 CR/HP

    def test_no_damage_zero_cost(self) -> None:
        manager, player, cost = _make_test_env(hull_fraction=1.0)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        assert view.get_damage_amount() == 0
        assert view.get_repair_cost() == 0

    def test_can_afford_repair(self) -> None:
        manager, player, cost = _make_test_env(credits=5000, hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        assert view.can_afford_repair()

    def test_cannot_afford_repair(self) -> None:
        manager, player, cost = _make_test_env(credits=100, hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        assert not view.can_afford_repair()


class TestRepairBayNavigation:
    """Tests for navigation."""

    def test_back_returns_to_station_hub(self) -> None:
        manager, player, cost = _make_test_env()
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view._request_back()
        assert view.get_next_state() == GameState.STATION_HUB
        view.on_exit()


class TestRepairBayRepairAction:
    """Tests for the repair action."""

    def test_repair_restores_hull(self) -> None:
        manager, player, cost = _make_test_env(credits=5000, hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view._execute_repair()
        assert player.ship.current_hull == player.ship.ship_type.combat_hull
        view.on_exit()

    def test_repair_deducts_credits(self) -> None:
        manager, player, cost = _make_test_env(credits=5000, hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view._execute_repair()
        assert player.credits == 4700  # 5000 - (30 * 10)
        view.on_exit()

    def test_repair_shows_success_message(self) -> None:
        manager, player, cost = _make_test_env(credits=5000, hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view._execute_repair()
        assert view.message is not None
        assert view.message_timer > 0
        view.on_exit()

    def test_repair_fails_insufficient_credits(self) -> None:
        manager, player, cost = _make_test_env(credits=100, hull_fraction=0.5)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view._execute_repair()
        # Hull unchanged
        assert player.ship.current_hull == 30
        assert player.credits == 100
        view.on_exit()

    def test_repair_fails_hull_full(self) -> None:
        manager, player, cost = _make_test_env(credits=5000, hull_fraction=1.0)
        view = RepairBayView(ui_manager=manager, player=player, cost_per_hp=cost)
        view.on_enter()
        view._execute_repair()
        assert player.credits == 5000  # No charge
        view.on_exit()
