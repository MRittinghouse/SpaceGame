"""BB-22: refuelling an over-full tank is refused, not turned into a sale."""

from __future__ import annotations

from types import SimpleNamespace

from spacegame.views.trading_view import TradingView


def test_an_over_full_tank_is_refused() -> None:
    view = TradingView.__new__(TradingView)
    view.player = SimpleNamespace(ship=SimpleNamespace(max_fuel=40, current_fuel=55), credits=500)
    shown: list[str] = []
    view._show_message = shown.append
    view._execute_refuel()
    assert shown == ["Fuel tank is full"]
    assert view.player.credits == 500
