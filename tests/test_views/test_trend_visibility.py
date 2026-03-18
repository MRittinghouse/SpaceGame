"""Tests for trend_visibility skill gating in trading view."""

from unittest.mock import MagicMock, patch

import pytest


class TestTrendVisibilityGating:
    """Verify trend column is hidden until Market Eye skill is unlocked."""

    def _make_trading_view(self, trend_bonus: float = 0.0) -> "TradingView":
        """Create a minimal TradingView with controllable trend_visibility bonus."""
        from spacegame.views.trading_view import TradingView

        with patch.object(TradingView, "__init__", lambda self: None):
            view = TradingView()

        view.player = MagicMock()
        view.player.current_system_id = "nexus_prime"
        view.player.progression = MagicMock()

        def fake_get_bonus(bonus_type: str) -> float:
            if bonus_type == "trend_visibility":
                return trend_bonus
            return 0.0

        view.player.progression.get_bonus = fake_get_bonus
        view.price_history = None
        view._black_market_mode = False

        # Minimal market mock
        commodity = MagicMock()
        commodity.name = "Ore"
        commodity.base_price = 100
        commodity.volume_per_unit = 1
        commodity.legality = MagicMock()
        commodity.legality.name = "LEGAL"
        # Make legality comparison fail for RESTRICTED/ILLEGAL checks
        from spacegame.models.commodity import Legality
        commodity.legality = Legality.LEGAL

        view.market = MagicMock()
        view.market.commodities = {"ore": commodity}
        view.market.get_price.return_value = 100
        view.market.get_stock.return_value = 50
        view.market.get_base_stock.return_value = 100
        view.market.get_market_report.return_value = {
            "trend": "Low",
            "is_specialty_export": False,
            "is_specialty_import": False,
        }
        view.commodities = {"ore": commodity}

        return view

    def test_no_skill_shows_question_mark(self) -> None:
        """Without trend_visibility, trend column shows '?'."""
        view = self._make_trading_view(trend_bonus=0.0)
        rows, ids = view._build_market_rows()
        assert len(rows) == 1
        trend_cell = rows[0][4]  # 5th column is trend
        assert trend_cell[0] == "?"

    def test_with_skill_shows_trend(self) -> None:
        """With trend_visibility, trend column shows actual trend."""
        view = self._make_trading_view(trend_bonus=1.0)
        rows, ids = view._build_market_rows()
        trend_cell = rows[0][4]
        trend_text = trend_cell[0] if isinstance(trend_cell, tuple) else trend_cell
        assert trend_text == "Low"

    def test_specialty_overrides_hidden_trend(self) -> None:
        """BUY HERE/SELL HERE shows even without trend skill."""
        view = self._make_trading_view(trend_bonus=0.0)
        view.market.get_market_report.return_value = {
            "trend": "Low",
            "is_specialty_export": True,
            "is_specialty_import": False,
        }
        rows, ids = view._build_market_rows()
        trend_cell = rows[0][4]
        assert trend_cell[0] == "BUY HERE"

    def test_history_trend_with_skill(self) -> None:
        """With skill and price history, shows history-based trend."""
        view = self._make_trading_view(trend_bonus=1.0)
        view.price_history = MagicMock()
        view.price_history.get_trend.return_value = "rising"
        rows, ids = view._build_market_rows()
        trend_cell = rows[0][4]
        assert "\u25b2" in trend_cell[0]  # Up arrow for rising
