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
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest


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

    # Stubbed market: every commodity sells for 50.
    view.market = MagicMock()
    view.market.get_sell_price.return_value = 50
    view.market.record_sell = MagicMock()

    # View-internal helpers / state stubbed out so _execute_sell_all has
    # what it needs to run end-to-end.
    view._has_trade_permit = MagicMock(return_value=has_permit)
    view._black_market_mode = False
    view._refresh_tables = MagicMock()
    view.particles = MagicMock()
    view.transaction_message = ""
    view.message_timer = 0.0

    return view, player


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
        recorded = {
            call.args[0]: call.args[1] for call in view.market.record_sell.call_args_list
        }
        assert recorded == {"food": 5, "water": 3}

    def test_no_op_with_empty_cargo(self) -> None:
        view, player = _make_trading_view_with_real_player(
            starting_cargo={}, starting_credits=1000
        )

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
