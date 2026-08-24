"""Regression tests for the lifecycle-scoped accessor pattern.

QF-8 introduces a uniform pattern for `Optional[X]` view attributes whose
lifetime is bounded by ``on_enter()``/``on_exit()``: raw storage lives at
``_attr`` and a ``@property attr -> X`` accessor raises ``RuntimeError``
with a lifecycle-naming message when the storage is None.

These tests exercise the four session-shaped view accessors landed in
QF-8: ``TradingView.market``, ``SalvageView.session``, ``MiningView.session``,
``RefiningView.session``. Each accessor is exercised in three states:

1. Fresh view (before ``on_enter()``): raises ``RuntimeError`` with a
   message naming the view class and the ``on_enter()`` lifecycle.
2. Post ``on_enter()``: returns the live, non-None object.
3. Post ``on_exit()``: raises again (storage cleared on exit).

The tests use the ``tests/test_scenarios/_view_harness.py`` pygame init
+ fresh UI manager pattern so they run deterministically headless.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from tests.test_scenarios._view_harness import (
    ensure_pygame,
    fresh_ui_manager,
    smoke_player,
)


@pytest.fixture(autouse=True)
def _pygame_ready() -> None:
    ensure_pygame()


# ── TradingView.market ─────────────────────────────────────────────────────────


def _make_trading_view():
    from spacegame.views.trading_view import TradingView

    dl = get_data_loader()
    dl.load_all()
    ui = fresh_ui_manager()
    player = smoke_player()
    return TradingView(
        ui_manager=ui,
        player=player,
        systems=dl.systems,
        commodities=dl.commodities,
    )


class TestTradingViewMarketAccessor:
    def test_trading_view_market_raises_before_on_enter(self) -> None:
        view = _make_trading_view()
        with pytest.raises(RuntimeError) as excinfo:
            _ = view.market
        msg = str(excinfo.value)
        assert "TradingView" in msg
        assert "market" in msg
        assert "on_enter" in msg

    def test_trading_view_market_returns_after_on_enter(self) -> None:
        view = _make_trading_view()
        # Set the tip-seen flag so on_enter takes the direct-init path
        # rather than the tip-dismiss branch.
        view.player.dialogue_flags["seen_tip_trading"] = True
        view.on_enter()
        try:
            market = view.market
            assert market is not None
            # Live object: has the get_price method the callsites rely on.
            assert hasattr(market, "get_price")
        finally:
            view.on_exit()

    def test_trading_view_market_raises_after_on_exit(self) -> None:
        view = _make_trading_view()
        view.player.dialogue_flags["seen_tip_trading"] = True
        view.on_enter()
        view.on_exit()
        with pytest.raises(RuntimeError):
            _ = view.market


# ── SalvageView.session ────────────────────────────────────────────────────────


def _make_salvage_view():
    from spacegame.views.salvage_view import SalvageView

    dl = get_data_loader()
    dl.load_all()
    ui = fresh_ui_manager()
    player = smoke_player()
    return SalvageView(
        ui_manager=ui,
        player=player,
        commodities=dl.commodities,
    )


class TestSalvageViewSessionAccessor:
    def test_salvage_view_session_raises_before_on_enter(self) -> None:
        view = _make_salvage_view()
        with pytest.raises(RuntimeError) as excinfo:
            _ = view.session
        msg = str(excinfo.value)
        assert "SalvageView" in msg
        assert "session" in msg
        assert "on_enter" in msg

    def test_salvage_view_session_returns_after_on_enter(self) -> None:
        view = _make_salvage_view()
        view.on_enter()
        try:
            # SalvageView.on_enter starts in derelict-selection mode; a
            # SalvageSession is created after the player picks a derelict.
            # Simulate that by invoking the internal starter with the
            # first available derelict type.
            from spacegame.models.salvage import DERELICT_TYPES

            view._start_with_derelict(DERELICT_TYPES[0])
            session = view.session
            assert session is not None
            assert hasattr(session, "scan_cell")
        finally:
            view.on_exit()

    def test_salvage_view_session_raises_after_on_exit(self) -> None:
        view = _make_salvage_view()
        view.on_enter()
        from spacegame.models.salvage import DERELICT_TYPES

        view._start_with_derelict(DERELICT_TYPES[0])
        view.on_exit()
        with pytest.raises(RuntimeError):
            _ = view.session


# ── MiningView.session ─────────────────────────────────────────────────────────


def _make_mining_view():
    from spacegame.views.mining_view import MiningView

    dl = get_data_loader()
    dl.load_all()
    ui = fresh_ui_manager()
    player = smoke_player()
    return MiningView(
        ui_manager=ui,
        player=player,
        commodities=dl.commodities,
    )


class TestMiningViewSessionAccessor:
    def test_mining_view_session_raises_before_on_enter(self) -> None:
        view = _make_mining_view()
        with pytest.raises(RuntimeError) as excinfo:
            _ = view.session
        msg = str(excinfo.value)
        assert "MiningView" in msg
        assert "session" in msg
        assert "on_enter" in msg

    def test_mining_view_session_returns_after_on_enter(self) -> None:
        view = _make_mining_view()
        view.on_enter()
        try:
            session = view.session
            assert session is not None
            assert hasattr(session, "energy")
        finally:
            view.on_exit()

    def test_mining_view_session_raises_after_on_exit(self) -> None:
        view = _make_mining_view()
        view.on_enter()
        view.on_exit()
        with pytest.raises(RuntimeError):
            _ = view.session


# ── RefiningView.session ───────────────────────────────────────────────────────


def _make_refining_view():
    from spacegame.views.refining_view import RefiningView

    dl = get_data_loader()
    dl.load_all()
    ui = fresh_ui_manager()
    player = smoke_player()
    return RefiningView(
        ui_manager=ui,
        player=player,
        commodities=dl.commodities,
        recipes=dl.recipes,
        system_id=player.current_system_id,
    )


class TestRefiningViewSessionAccessor:
    def test_refining_view_session_raises_before_on_enter(self) -> None:
        view = _make_refining_view()
        with pytest.raises(RuntimeError) as excinfo:
            _ = view.session
        msg = str(excinfo.value)
        assert "RefiningView" in msg
        assert "session" in msg
        assert "on_enter" in msg

    def test_refining_view_session_returns_after_on_enter(self) -> None:
        view = _make_refining_view()
        view.on_enter()
        try:
            session = view.session
            assert session is not None
            assert hasattr(session, "available_recipes")
        finally:
            view.on_exit()

    def test_refining_view_session_raises_after_on_exit(self) -> None:
        view = _make_refining_view()
        view.on_enter()
        view.on_exit()
        with pytest.raises(RuntimeError):
            _ = view.session
