"""Tests for the trading view's reactive Buy/Sell button state.

Sprint 5b follow-up: trading view now pre-emptively disables Buy/Sell
buttons when the action cannot succeed, with a tooltip explaining why.
These tests verify the disable reasons fire correctly across the common
failure modes and re-enable when the blocker clears.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


def _make_trading_view(
    *,
    credits: int = 5000,
    has_permit: bool = True,
    cargo: dict | None = None,
    stock_override: int | None = None,
):
    """Minimal TradingView with controllable state."""
    from spacegame.views.trading_view import TradingView

    cargo = cargo or {}
    view = TradingView.__new__(TradingView)

    # Minimal player state
    view.player = MagicMock()
    view.player.credits = credits
    view.player.progression.get_bonus.return_value = 0.0
    view.player.dialogue_flags = {}
    view.player.ship = MagicMock()
    view.player.ship.current_cargo = cargo
    view.player.ship.max_cargo = 100
    view.player.ship.get_cargo_quantity.side_effect = lambda cid: cargo.get(cid, 0)
    view.player.ship.can_carry.return_value = True

    view.market = MagicMock()
    view.market.get_stock.return_value = 10 if stock_override is None else stock_override
    view.market.get_base_stock.return_value = 10
    view.market.get_price.return_value = 100

    view.commodities = {
        "food": MagicMock(id="food", legality=MagicMock(), volume_per_unit=1),
    }
    view.commodities["food"].name = "Food"

    # Permit gating
    view._has_trade_permit = MagicMock(return_value=has_permit)
    view._black_market_mode = False
    view._get_black_market_buy_price = MagicMock(return_value=100)
    view._get_adjusted_buy_price = MagicMock(return_value=100)

    # Buttons (real pygame_gui so enable/disable and tool_tip_text work)
    ui = pygame_gui.UIManager((1280, 720))
    rect = pygame.Rect(0, 0, 100, 30)
    view.buy_button = pygame_gui.elements.UIButton(rect, "BUY", ui)
    view.buy_max_button = pygame_gui.elements.UIButton(pygame.Rect(0, 30, 100, 30), "MAX", ui)
    view.sell_button = pygame_gui.elements.UIButton(pygame.Rect(0, 60, 100, 30), "SELL", ui)
    view.sell_max_button = pygame_gui.elements.UIButton(pygame.Rect(0, 90, 100, 30), "MAX", ui)
    view.sell_all_button = pygame_gui.elements.UIButton(
        pygame.Rect(0, 120, 100, 30), "SELL ALL", ui
    )

    # Selection helpers
    view._selected_market_id: str | None = "food"
    view._selected_cargo_id: str | None = None
    view._get_selected_market_commodity = MagicMock(side_effect=lambda: view._selected_market_id)
    view._get_selected_cargo_commodity = MagicMock(side_effect=lambda: view._selected_cargo_id)

    return view


class TestBuyReasons:
    """Each Buy-disable reason fires correctly."""

    def test_enabled_when_all_conditions_met(self) -> None:
        view = _make_trading_view()
        view._refresh_button_states()
        assert view.buy_button.is_enabled
        assert view.buy_button.tool_tip_text is None

    def test_disabled_when_no_permit(self) -> None:
        view = _make_trading_view(has_permit=False)
        view._refresh_button_states()
        assert not view.buy_button.is_enabled
        assert "permit" in view.buy_button.tool_tip_text.lower()

    def test_disabled_when_nothing_selected(self) -> None:
        view = _make_trading_view()
        view._selected_market_id = None
        view._refresh_button_states()
        assert not view.buy_button.is_enabled
        assert "pick" in view.buy_button.tool_tip_text.lower()

    def test_disabled_when_out_of_stock(self) -> None:
        view = _make_trading_view(stock_override=0)
        view._refresh_button_states()
        assert not view.buy_button.is_enabled
        assert "stock" in view.buy_button.tool_tip_text.lower()

    def test_disabled_when_cant_afford(self) -> None:
        view = _make_trading_view(credits=10)  # Less than 100 unit price
        view._refresh_button_states()
        assert not view.buy_button.is_enabled
        assert "afford" in view.buy_button.tool_tip_text.lower()

    def test_disabled_when_hold_full(self) -> None:
        view = _make_trading_view()
        view.player.ship.can_carry.return_value = False
        view._refresh_button_states()
        assert not view.buy_button.is_enabled
        assert "hold" in view.buy_button.tool_tip_text.lower()

    def test_buy_max_mirrors_buy_state(self) -> None:
        """Max variant always matches the base button's state."""
        view = _make_trading_view(credits=10)
        view._refresh_button_states()
        assert not view.buy_max_button.is_enabled
        view2 = _make_trading_view()
        view2._refresh_button_states()
        assert view2.buy_max_button.is_enabled


class TestSellReasons:
    """Each Sell-disable reason fires correctly."""

    def test_enabled_when_cargo_selected_and_have_stock(self) -> None:
        view = _make_trading_view(cargo={"food": 5})
        view._selected_cargo_id = "food"
        view._refresh_button_states()
        assert view.sell_button.is_enabled
        assert view.sell_button.tool_tip_text is None

    def test_disabled_when_no_permit(self) -> None:
        view = _make_trading_view(has_permit=False, cargo={"food": 5})
        view._selected_cargo_id = "food"
        view._refresh_button_states()
        assert not view.sell_button.is_enabled

    def test_disabled_when_no_cargo_selected(self) -> None:
        view = _make_trading_view(cargo={"food": 5})
        view._selected_cargo_id = None
        view._refresh_button_states()
        assert not view.sell_button.is_enabled
        assert "pick" in view.sell_button.tool_tip_text.lower()

    def test_disabled_when_selected_cargo_empty(self) -> None:
        view = _make_trading_view(cargo={"food": 0})
        view._selected_cargo_id = "food"
        view._refresh_button_states()
        assert not view.sell_button.is_enabled
        assert "nothing" in view.sell_button.tool_tip_text.lower()


class TestSellAllReasons:
    """Each Sell-All-disable reason fires correctly.

    Sell All gates differently from Sell: it operates on the whole cargo
    hold, so it does not require a row selection — only a permit and at
    least one unit aboard. Before this gating the button stayed clickable
    with empty cargo, which surfaced the playtester confusion that led to
    the underlying crash report (and the click-with-no-cargo no-op path).
    """

    def test_enabled_when_permit_and_cargo_present(self) -> None:
        view = _make_trading_view(cargo={"food": 5})
        view._refresh_button_states()
        assert view.sell_all_button.is_enabled
        assert view.sell_all_button.tool_tip_text is None

    def test_enabled_without_cargo_selection(self) -> None:
        # Selection independence is the whole point of Sell All. The
        # button must stay enabled even with nothing highlighted on the
        # cargo side, as long as cargo exists.
        view = _make_trading_view(cargo={"food": 5})
        view._selected_cargo_id = None
        view._refresh_button_states()
        assert view.sell_all_button.is_enabled

    def test_disabled_when_no_permit(self) -> None:
        view = _make_trading_view(has_permit=False, cargo={"food": 5})
        view._refresh_button_states()
        assert not view.sell_all_button.is_enabled
        assert "permit" in view.sell_all_button.tool_tip_text.lower()

    def test_disabled_when_cargo_empty(self) -> None:
        view = _make_trading_view(cargo={})
        view._refresh_button_states()
        assert not view.sell_all_button.is_enabled
        assert "nothing" in view.sell_all_button.tool_tip_text.lower()

    def test_disabled_when_only_zero_qty_entries(self) -> None:
        # A cargo dict with stale zero entries should still count as empty.
        view = _make_trading_view(cargo={"food": 0, "water": 0})
        view._refresh_button_states()
        assert not view.sell_all_button.is_enabled


class TestStateTransitions:
    """Button state re-enables when the blocker clears."""

    def test_re_enables_after_credits_added(self) -> None:
        view = _make_trading_view(credits=10)
        view._refresh_button_states()
        assert not view.buy_button.is_enabled

        view.player.credits = 5000
        view._refresh_button_states()
        assert view.buy_button.is_enabled

    def test_re_enables_after_stock_restocked(self) -> None:
        view = _make_trading_view(stock_override=0)
        view._refresh_button_states()
        assert not view.buy_button.is_enabled

        view.market.get_stock.return_value = 5
        view._refresh_button_states()
        assert view.buy_button.is_enabled
