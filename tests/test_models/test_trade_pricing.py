"""Trade price formulas, lifted from TradingView (SP3 spec 6.1)."""

from __future__ import annotations

from spacegame.config import REP_PER_TRADE
from spacegame.data_loader import get_data_loader
from spacegame.models.market import Market
from spacegame.models.trade_pricing import (
    black_market_buy_price,
    black_market_sell_price,
    buy_price,
    effective_tariff,
    refuel_price,
    route_bonus,
    sell_price,
    trade_reputation_gain,
)
from tests.test_scenarios._helpers import fresh_player


def _market(system_id: str = "nexus_prime", day: int = 3) -> Market:
    dl = get_data_loader()
    dl.load_all()
    return Market(dl.systems[system_id], list(dl.commodities.values()), game_day=day)


def _old_buy(base: int, discount: float, tariff: float, reduction: float) -> int:
    if tariff > 0:
        tariff = max(0.0, tariff - reduction)
    return max(1, int(base * (1.0 - discount + tariff)))


class TestBuySell:
    def test_plain_player_pays_market_price(self) -> None:
        player = fresh_player()
        market = _market()
        assert buy_price(player, market, "food") == max(1, int(market.get_price("food") * 1.0))

    def test_skill_discount_and_hostile_tariff(self) -> None:
        player = fresh_player()
        player.progression.skills["negotiator"].current_level = 2
        faction = "commerce_guild"
        player.faction_assignments["nexus_prime"] = faction
        player.faction_reputation[faction] = -80  # hostile: +0.30 tariff
        market = _market()
        base = market.get_price("food")
        assert buy_price(player, market, "food") == _old_buy(base, 0.1, 0.30, 0.0)
        assert sell_price(player, market, "food") == max(
            1, int(market.get_sell_price("food") * (1.0 + 0.0 - 0.30))
        )

    def test_route_bonus_tiers(self) -> None:
        player = fresh_player()
        assert route_bonus(player) == 0.0
        player.previous_system_id = "forgeworks"
        for _ in range(5):
            player.trade_route_tracker.record_trip("forgeworks", "nexus_prime")
        assert route_bonus(player) == 0.10

    def test_tariff_reduction_only_reduces_penalties(self) -> None:
        player = fresh_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_reputation["commerce_guild"] = 80  # allied: -0.20
        assert effective_tariff(player) == -0.20

    def test_perk_bonus_adds_last(self) -> None:
        player = fresh_player()
        market = _market()
        base = market.get_price("food")
        assert buy_price(player, market, "food", perk_bonus=0.05) == _old_buy(base, 0.05, 0.0, 0.0)


class TestOtherPrices:
    def test_refuel(self) -> None:
        market = _market()
        assert refuel_price(market, free_fuel=True) == 0
        assert refuel_price(market, free_fuel=False) == market.get_price("fuel")

    def test_black_market_prices_floor_at_one(self) -> None:
        player = fresh_player()
        market = _market()
        commodity = get_data_loader().commodities["food"]
        assert black_market_buy_price(market, commodity) >= 1
        assert black_market_sell_price(player, market, commodity) >= 1

    def test_reputation_gain(self) -> None:
        player = fresh_player()
        assert trade_reputation_gain(player) == REP_PER_TRADE
