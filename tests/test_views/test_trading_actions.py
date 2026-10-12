"""Tests for the trading view's action handlers (sell/buy execution paths).

Complements ``test_trading_button_states.py``: that file covers the
enable/disable / tooltip logic; this file covers the actual side-effects
of clicking the action buttons (cargo movement, credits, market record).

Background: a playtester reported a hard crash on clicking "Sell All"
with non-empty cargo. Root cause was at trading_view.py:1221: the call
to ``Player.sell_commodity`` was passing 4 args (the buy signature),
but ``sell_commodity`` only takes 3. ``Player.buy_commodity`` needs the
``commodity_volumes`` map to enforce hold capacity; selling frees space
so it does not. These tests run the action path against real Player and
Ship models so the wrong signature surfaces as a TypeError, instead of
hiding behind a MagicMock that silently accepts any call shape.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

if TYPE_CHECKING:
    from spacegame.models.player import Player
    from spacegame.views.trading_view import TradingView


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _make_trading_view_with_real_player(
    *,
    starting_cargo: dict[str, int] | None = None,
    starting_credits: int = 1000,
    has_permit: bool = True,
    mission_manager: object = None,
):
    """Build a minimal TradingView wired to a real Player + Ship.

    Real models matter here: this test class is hunting for shape/signature
    bugs in the call from view → model. A MagicMock player would silently
    swallow a wrong arg count and the test would pass on a broken view.
    """
    from spacegame.data_loader import DataLoader
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship
    from spacegame.views.trading_view import TradingView

    loader = DataLoader()
    loader.load_all()

    shuttle_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)
    for commodity_id, qty in (starting_cargo or {}).items():
        ship.add_cargo(commodity_id, qty)

    player = Player(
        name="Test", credits=starting_credits, current_system_id="nexus_prime", ship=ship
    )

    view = TradingView.__new__(TradingView)
    view.player = player
    view.commodities = loader.commodities
    view.systems = loader.systems
    view.mission_manager = mission_manager

    # Stubbed market: every commodity sells for 50.
    # QF-8: TradingView.market is now a raising @property; set raw storage.
    view._market = MagicMock()
    view._market.get_sell_price.return_value = 50
    view._market.record_sell = MagicMock()

    # View-internal helpers / state stubbed out so _execute_sell_all has
    # what it needs to run end-to-end.
    view._has_trade_permit = MagicMock(return_value=has_permit)
    view._black_market_mode = False
    view._refresh_tables = MagicMock()
    view.particles = MagicMock()
    view.transaction_message = ""
    view.message_timer = 0.0

    return view, player


class TestQuestGoodsStayOffTheTradeScreen:
    """BB-7: a sale must not strand the chip deliveries."""

    def test_cargo_rows_list_market_goods_and_not_quest_goods(self) -> None:
        view, _player = _make_trading_view_with_real_player(
            starting_cargo={"food": 5, "data_chip": 1}
        )
        _rows, ids = view._build_cargo_rows()
        assert ids == ["food"]

    def test_sell_all_sells_market_goods_and_leaves_quest_goods(self) -> None:
        view, player = _make_trading_view_with_real_player(
            starting_cargo={"food": 5, "data_chip": 1}
        )
        view._execute_sell_all()
        assert player.ship.get_cargo_quantity("food") == 0
        assert player.ship.get_cargo_quantity("data_chip") == 1

    def test_sell_all_is_disabled_with_only_quest_goods(self) -> None:
        view, _player = _make_trading_view_with_real_player(starting_cargo={"data_chip": 1})
        assert view._why_cannot_sell_all() == "Nothing to sell."

    def test_sell_all_is_enabled_with_market_goods(self) -> None:
        view, _player = _make_trading_view_with_real_player(
            starting_cargo={"food": 5, "data_chip": 1}
        )
        assert view._why_cannot_sell_all() is None


class TestExecuteSellAll:
    """Sell-all flow exercised against a real Player + Ship.

    Repro of playtester crash: cargo non-empty → click Sell All →
    TypeError because the view passes the buy signature to sell_commodity.
    """

    def test_does_not_raise_with_non_empty_cargo(self) -> None:
        view, _player = _make_trading_view_with_real_player(
            starting_cargo={"food": 10}, starting_credits=1000
        )

        # Pre-fix this raises TypeError: sell_commodity() takes 4 positional
        # arguments but 5 were given. Post-fix it returns cleanly.
        view._execute_sell_all()

    def test_empties_cargo_and_credits_player(self) -> None:
        view, player = _make_trading_view_with_real_player(
            starting_cargo={"food": 10}, starting_credits=1000
        )

        view._execute_sell_all()

        assert player.ship.get_cargo_quantity("food") == 0, "All cargo should be sold"
        assert player.credits == 1000 + 50 * 10, "Credits should reflect total sale"

    def test_sells_every_commodity_in_cargo(self) -> None:
        view, player = _make_trading_view_with_real_player(
            starting_cargo={"food": 5, "water": 3, "metals": 2}, starting_credits=1000
        )

        view._execute_sell_all()

        assert player.ship.get_cargo_quantity("food") == 0
        assert player.ship.get_cargo_quantity("water") == 0
        assert player.ship.get_cargo_quantity("metals") == 0
        # 10 total units at 50 each.
        assert player.credits == 1000 + 50 * 10

    def test_records_each_sell_against_the_market(self) -> None:
        view, _player = _make_trading_view_with_real_player(
            starting_cargo={"food": 5, "water": 3}, starting_credits=1000
        )

        view._execute_sell_all()

        # Each commodity gets its own record_sell call, with the quantity sold.
        recorded = {call.args[0]: call.args[1] for call in view.market.record_sell.call_args_list}
        assert recorded == {"food": 5, "water": 3}

    def test_no_op_with_empty_cargo(self) -> None:
        view, player = _make_trading_view_with_real_player(starting_cargo={}, starting_credits=1000)

        view._execute_sell_all()

        assert player.credits == 1000, "Credits unchanged when nothing to sell"
        view.market.record_sell.assert_not_called()

    def test_no_op_without_trade_permit(self) -> None:
        view, player = _make_trading_view_with_real_player(
            starting_cargo={"food": 10}, starting_credits=1000, has_permit=False
        )

        view._execute_sell_all()

        assert player.ship.get_cargo_quantity("food") == 10, "Cargo untouched without permit"
        assert player.credits == 1000, "Credits untouched without permit"


class TestSellMaxAsksForTheTradePermit:
    """BB-74: MAX SELL is gated by the same permit as every other sale.

    Uses the real ``_has_trade_permit`` so the refusal comes from the
    missing Union permit, not from a stub.
    """

    @staticmethod
    def _build(permits: set[str]):
        from unittest.mock import patch

        from spacegame.data_loader import DataLoader
        from spacegame.models.faction import generate_faction_assignments

        view, player = _make_trading_view_with_real_player(
            starting_cargo={"food": 5}, starting_credits=1000
        )
        del view._has_trade_permit
        loader = DataLoader()
        loader.load_all()
        player.current_system_id = "breakstone"
        player.faction_assignments = generate_faction_assignments(loader.get_all_systems())
        player.trade_permits = set(permits)
        view._get_selected_cargo_commodity = MagicMock(return_value="food")
        view._get_adjusted_sell_price = MagicMock(return_value=30)
        view._apply_trade_reputation = MagicMock()
        patcher = patch("spacegame.views.trading_view.get_audio_manager")
        patcher.start()
        return view, player, patcher

    def test_sell_max_refuses_at_breakstone_without_the_union_permit(self) -> None:
        from spacegame.views.trading_view import NO_PERMIT

        view, player, patcher = self._build(
            {"commerce_guild", "science_collective", "frontier_alliance"}
        )
        try:
            view._execute_sell_max()
        finally:
            patcher.stop()
        assert player.ship.get_cargo_quantity("food") == 5
        assert player.credits == 1000
        assert view.transaction_message == NO_PERMIT
        view._apply_trade_reputation.assert_not_called()
        view.market.record_sell.assert_not_called()

    def test_sell_max_sells_everything_with_the_union_permit(self) -> None:
        view, player, patcher = self._build(
            {"commerce_guild", "science_collective", "frontier_alliance", "miners_union"}
        )
        try:
            view._execute_sell_max()
        finally:
            patcher.stop()
        assert player.ship.get_cargo_quantity("food") == 0
        assert player.credits == 1000 + 150
        view._apply_trade_reputation.assert_called_once()


class TestRestRunsTheIronClock:
    """Bug bash BB-4: a rest runs the iron job's clock, as a landing does."""

    def test_the_rest_that_reaches_the_late_tier_moves_the_campaign_on(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.mission import MissionManager

        dl = get_data_loader()
        dl.load_all()
        manager = MissionManager(dl.missions)
        manager.load_state(
            {
                "status": {"bill_of_landing": "completed", "iron_delivery": "active"},
                "accepted_day": {"iron_delivery": 1},
            }
        )
        view, player = _make_trading_view_with_real_player(mission_manager=manager)
        player.ship.add_cargo("iron_ore", 10, 0)
        player.game_day = 18
        view._execute_rest()
        assert "iron_delivery_moved_on" not in player.dialogue_flags
        view._execute_rest()
        assert player.game_day == 20
        assert player.dialogue_flags["iron_delivery_moved_on"] is True

    def test_a_rest_files_a_sale_on_record(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.mission import MissionManager

        dl = get_data_loader()
        dl.load_all()
        manager = MissionManager(dl.missions)
        manager.load_state(
            {
                "status": {"bill_of_landing": "completed", "iron_delivery": "active"},
                "accepted_day": {"iron_delivery": 1},
            }
        )
        view, player = _make_trading_view_with_real_player(mission_manager=manager)
        player.ship.add_cargo("iron_ore", 6, 0)
        player.dialogue_flags["broker_ore_sold"] = True
        player.dialogue_flags["iron_job_moved"] = True
        player.game_day = 19
        view._execute_rest()
        assert manager.get_status("iron_delivery").value == "failed"
        assert player.ship.get_cargo_quantity("iron_ore") == 0
        assert "Freight violation filed." in view.transaction_message
        assert player.dialogue_flags["iron_job_moved"] is False


def _give_hidden_compartment(player: Player) -> None:
    """Install a hidden compartment with room for every hide these tests try."""
    from spacegame.models.smuggling import HiddenCompartment

    player.hidden_compartment = HiddenCompartment(total_cargo_capacity=50)


def _select_cargo(view: TradingView, commodity_id: str, quantity: int) -> None:
    """Select a cargo row and type a quantity, as the hide and sell buttons read them."""
    view._get_selected_cargo_commodity = MagicMock(return_value=commodity_id)
    # QF-8: quantity_input is a read-only property over _quantity_input
    view._quantity_input = MagicMock()
    view._quantity_input.get_text.return_value = str(quantity)
    view._refresh_tables = MagicMock()


class TestOdomsOreStaysInTheMainHold:
    """Odom's consigned ore cannot be hidden while his job is open."""

    def test_odoms_ore_cannot_be_hidden(self) -> None:
        from spacegame.data_loader import get_data_loader
        from spacegame.models.iron_consignment import HIDE_REFUSED
        from spacegame.models.mission import MissionManager

        dl = get_data_loader()
        dl.load_all()
        manager = MissionManager(dl.missions)
        manager.load_state(
            {"status": {"iron_delivery": "active"}, "accepted_day": {"iron_delivery": 1}}
        )
        view, player = _make_trading_view_with_real_player(mission_manager=manager)
        player.ship.add_cargo("iron_ore", 12, 0)
        _give_hidden_compartment(player)
        _select_cargo(view, "iron_ore", quantity=5)
        view._execute_hide_cargo()
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        _select_cargo(view, "iron_ore", quantity=5)
        view._execute_hide_cargo()
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert view.transaction_message == HIDE_REFUSED


class TestConsignedCargo:
    """Bug bash BB-1 and BB-11: a mission's accept cargo stays aboard unless named."""

    def _view(
        self,
        cargo: dict[str, int],
        board: bool = False,
        hidden: dict[str, int] | None = None,
    ):
        from spacegame.data_loader import get_data_loader
        from spacegame.models.mission import (
            AcceptCargo,
            Mission,
            MissionManager,
            MissionObjective,
            MissionStatus,
            ObjectiveType,
        )

        dl = get_data_loader()
        dl.load_all()
        manager = MissionManager(dl.missions)
        manager.load_state({"status": {"iron_delivery": "active"}})
        if board:
            manager.add_mission(
                Mission(
                    id="proc_smuggling_test",
                    name="test",
                    description="A test contract.",
                    objectives=[
                        MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")
                    ],
                    rewards=[],
                    on_accept_cargo=[AcceptCargo(commodity_id="weapons_components", quantity=3)],
                ),
                MissionStatus.ACTIVE,
            )
        view, player = _make_trading_view_with_real_player(
            starting_cargo=cargo, mission_manager=manager
        )
        if hidden:
            from spacegame.models.smuggling import HiddenCompartment

            player.hidden_compartment = HiddenCompartment(
                total_cargo_capacity=50, hidden_cargo=dict(hidden)
            )
        view._get_adjusted_sell_price = MagicMock(return_value=14)
        view._apply_trade_reputation = MagicMock()
        # QF-8: quantity_input is a read-only property over _quantity_input
        view._quantity_input = MagicMock()
        return view, player

    def _sell(self, view, commodity_id: str, quantity: int) -> None:
        view._get_selected_cargo_commodity = MagicMock(return_value=commodity_id)
        view.quantity_input.get_text.return_value = str(quantity)
        view._execute_sell()

    def test_sell_all_sells_only_the_captains_own_ore(self) -> None:
        view, player = self._view({"iron_ore": 15, "food": 4})
        view._execute_sell_all()
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert player.ship.get_cargo_quantity("food") == 0

    def test_sell_max_sells_only_the_surplus(self) -> None:
        view, player = self._view({"iron_ore": 13})
        view._get_selected_cargo_commodity = MagicMock(return_value="iron_ore")
        view._execute_sell_max()
        assert player.ship.get_cargo_quantity("iron_ore") == 10

    def test_sell_max_with_only_consigned_ore_sells_nothing(self) -> None:
        view, player = self._view({"iron_ore": 10})
        view._get_selected_cargo_commodity = MagicMock(return_value="iron_ore")
        view._execute_sell_max()
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert view.transaction_message == "No cargo to sell"

    def test_naming_odoms_ore_sells_it_and_records_the_sale(self) -> None:
        view, player = self._view({"iron_ore": 10})
        self._sell(view, "iron_ore", 1)
        assert player.ship.get_cargo_quantity("iron_ore") == 9
        assert player.dialogue_flags["broker_ore_sold"] is True

    def test_selling_the_captains_own_ore_records_nothing(self) -> None:
        view, player = self._view({"iron_ore": 15})
        self._sell(view, "iron_ore", 5)
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert "broker_ore_sold" not in player.dialogue_flags

    def test_a_board_contracts_cargo_is_sealed(self) -> None:
        from spacegame.views.trading_view import SEALED_CARGO

        view, player = self._view({"weapons_components": 5}, board=True)
        self._sell(view, "weapons_components", 2)
        assert player.ship.get_cargo_quantity("weapons_components") == 3
        self._sell(view, "weapons_components", 1)
        assert player.ship.get_cargo_quantity("weapons_components") == 3
        assert view.transaction_message == SEALED_CARGO

    def test_sell_all_with_only_consigned_cargo_says_so(self) -> None:
        view, player = self._view({"iron_ore": 10})
        view._execute_sell_all()
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert view.transaction_message == "No cargo to sell"

    def test_the_seal_holds_at_the_black_market(self) -> None:
        from spacegame.views.trading_view import SEALED_CARGO

        view, player = self._view({"weapons_components": 5}, board=True)
        view._black_market_mode = True
        view._get_black_market_sell_price = MagicMock(return_value=14)
        self._sell(view, "weapons_components", 2)
        assert player.ship.get_cargo_quantity("weapons_components") == 3
        self._sell(view, "weapons_components", 1)
        assert player.ship.get_cargo_quantity("weapons_components") == 3
        assert view.transaction_message == SEALED_CARGO

    def test_a_failed_sale_records_nothing(self) -> None:
        view, player = self._view({"iron_ore": 10})
        self._sell(view, "iron_ore", 11)
        assert player.ship.get_cargo_quantity("iron_ore") == 10
        assert view.transaction_message == "Insufficient quantity in cargo"
        assert "broker_ore_sold" not in player.dialogue_flags

    def test_hidden_ore_still_counts_as_aboard(self) -> None:
        """Five of Odom's ten hidden, five more bought: selling five is the captain's own."""
        view, player = self._view({"iron_ore": 10}, hidden={"iron_ore": 5})
        self._sell(view, "iron_ore", 5)
        assert player.ship.get_cargo_quantity("iron_ore") == 5
        assert "broker_ore_sold" not in player.dialogue_flags
        self._sell(view, "iron_ore", 1)
        assert player.dialogue_flags["broker_ore_sold"] is True

    def test_hiding_a_contracts_cargo_leaves_the_captains_own_unsealed(self) -> None:
        """The contract's three hidden, three of the captain's own in the main hold."""
        view, player = self._view(
            {"weapons_components": 3}, board=True, hidden={"weapons_components": 3}
        )
        self._sell(view, "weapons_components", 3)
        assert player.ship.get_cargo_quantity("weapons_components") == 0
