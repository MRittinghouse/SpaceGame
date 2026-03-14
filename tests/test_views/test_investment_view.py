"""Tests for InvestmentView — per-system passive income investments."""

import pygame
import pygame_gui
from spacegame.config import GameState, WINDOW_WIDTH, WINDOW_HEIGHT
from spacegame.data_loader import DataLoader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.investment import InvestmentManager, InvestmentTemplate, InvestmentTier
from spacegame.views.investment_view import InvestmentView


def _make_template(
    system_id: str = "nexus_prime",
    returns_type: str = "credits",
    commodity: str | None = None,
) -> InvestmentTemplate:
    return InvestmentTemplate(
        system_id=system_id,
        investment_type="trade_office",
        name="Trade Office",
        description="Invest in trade operations.",
        tiers=[
            InvestmentTier(1, 1000, 10, returns_type, commodity),
            InvestmentTier(2, 5000, 50, returns_type, commodity),
            InvestmentTier(3, 15000, 200, returns_type, commodity),
        ],
    )


def _make_test_env(
    credits: int = 5000,
    system_id: str = "nexus_prime",
) -> tuple[pygame_gui.UIManager, Player, InvestmentManager]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    loader = DataLoader()
    loader.load_all()

    ship_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player("Test Captain", credits, system_id, ship)

    template = _make_template(system_id)
    inv_mgr = InvestmentManager(templates={system_id: template})
    return manager, player, inv_mgr


class TestInvestmentViewConstruction:
    def test_create_view(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env()
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        assert view is not None
        assert view.next_state is None

    def test_stores_system_id(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env()
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        assert view.system_id == "nexus_prime"


class TestInvestmentViewLifecycle:
    def test_on_enter_sets_active(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env()
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_clears_active(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env()
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        view.on_exit()
        assert not view.active


class TestInvestmentViewActions:
    def test_invest_creates_investment(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env(credits=5000)
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        view._execute_invest()
        assert inv_mgr.get_investment("nexus_prime") is not None
        assert player.credits == 4000
        assert player.investments_owned == 1
        view.on_exit()

    def test_invest_insufficient_credits(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env(credits=500)
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        view._execute_invest()
        assert inv_mgr.get_investment("nexus_prime") is None
        assert player.credits == 500
        view.on_exit()

    def test_upgrade_increases_tier(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env(credits=10000)
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        view._execute_invest()  # tier 1, cost 1000
        view._execute_upgrade()  # tier 2, cost 5000
        assert inv_mgr.get_investment("nexus_prime").tier == 2
        assert player.credits == 4000  # 10000 - 1000 - 5000
        view.on_exit()

    def test_collect_returns(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env(credits=5000)
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        view._execute_invest()
        inv_mgr.advance_day(6, active_events={}, danger_levels={})
        view._execute_collect()
        assert player.credits == 4050  # 5000 - 1000 + 50 (5 days * 10)
        view.on_exit()


class TestInvestmentViewNavigation:
    def test_back_returns_to_station_hub(self) -> None:
        ui_mgr, player, inv_mgr = _make_test_env()
        view = InvestmentView(
            ui_manager=ui_mgr, player=player,
            investment_manager=inv_mgr, system_id="nexus_prime",
        )
        view.on_enter()
        view._request_back()
        assert view.get_next_state() == GameState.STATION_HUB
        view.on_exit()
