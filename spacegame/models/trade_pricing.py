"""Trade price formulas: the skill, crew, route, perk, and tariff stack (SP3 spec 6.1).

Lifted from TradingView. The summation order matches the view exactly, because float
addition is not associative and the Godot port replays these goldens bit for bit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from spacegame.config import REP_PER_TRADE
from spacegame.models.faction import get_tariff_modifier

if TYPE_CHECKING:
    from spacegame.models.commodity import Commodity
    from spacegame.models.market import Market
    from spacegame.models.player import Player


def route_bonus(player: Player) -> float:
    """Trade route efficiency bonus for the leg just flown (0.0 to 0.15)."""
    if not player.previous_system_id:
        return 0.0
    return player.trade_route_tracker.get_efficiency_bonus(
        player.previous_system_id, player.current_system_id
    )


def _faction_tariff(player: Player) -> float:
    faction_id = player.get_faction_for_system(player.current_system_id)
    if not faction_id:
        return 0.0
    return get_tariff_modifier(player.get_reputation(faction_id))


def effective_tariff(player: Player) -> float:
    """The system faction's tariff, with Leadership reduction applied to penalties only."""
    tariff = _faction_tariff(player)
    if tariff > 0:
        tariff = max(0.0, tariff - player.progression.get_bonus("tariff_reduction"))
    return tariff


def buy_price(player: Player, market: Market, commodity_id: str, perk_bonus: float = 0.0) -> int:
    """Price per unit the player pays.

    Args:
        player: The buyer.
        market: The system's market.
        commodity_id: Commodity to price.
        perk_bonus: Faction perk ``buy_price_bonus`` (0.0 without a politics manager).

    Returns:
        The adjusted price, at least 1.
    """
    base_price = market.get_price(commodity_id)
    discount = player.progression.get_bonus("buy_price_reduction")
    discount += player.ship.get_crew_bonus("buy_price_reduction")
    discount += route_bonus(player)
    discount += perk_bonus
    tariff = effective_tariff(player)
    adjusted = base_price * (1.0 - discount + tariff)
    return max(1, int(adjusted))


def sell_price(player: Player, market: Market, commodity_id: str, perk_bonus: float = 0.0) -> int:
    """Price per unit the player receives.

    Args:
        player: The seller.
        market: The system's market.
        commodity_id: Commodity to price.
        perk_bonus: Faction perk ``sell_price_bonus`` (0.0 without a politics manager).

    Returns:
        The adjusted price, at least 1.
    """
    base_price = market.get_sell_price(commodity_id)
    bonus = player.progression.get_bonus("sell_price_bonus")
    bonus += player.ship.get_crew_bonus("sell_price_bonus")
    bonus += route_bonus(player)
    bonus += perk_bonus
    tariff = effective_tariff(player)
    adjusted = base_price * (1.0 + bonus - tariff)
    return max(1, int(adjusted))


def black_market_buy_price(market: Market, commodity: Commodity) -> int:
    """Black-market buy price: legality modifier, no tariff."""
    from spacegame.models.smuggling import get_black_market_price_modifier

    base_price = market.get_price(commodity.id)
    modifier = get_black_market_price_modifier(commodity.legality)
    return max(1, int(base_price * (1.0 + modifier)))


def black_market_sell_price(player: Player, market: Market, commodity: Commodity) -> int:
    """Black-market sell price: legality modifier plus the Commerce sell bonus."""
    from spacegame.models.smuggling import get_black_market_price_modifier

    base_price = market.get_sell_price(commodity.id)
    modifier = get_black_market_price_modifier(commodity.legality)
    modifier += player.progression.get_bonus("black_market_sell_bonus")
    return max(1, int(base_price * (1.0 + modifier)))


def refuel_price(market: Market, free_fuel: bool) -> int:
    """Fuel price per unit; the free-fuel faction perk makes it 0."""
    return 0 if free_fuel else market.get_price("fuel")


def trade_reputation_gain(player: Player) -> int:
    """Reputation earned with the system's faction for the first trade of a landing."""
    rep_gain = REP_PER_TRADE + int(player.progression.get_bonus("reputation_gain_bonus"))
    ambassador_lvl = player.progression.get_bonus("faction_rep_multiplier")
    if ambassador_lvl > 0:
        rep_gain = int(rep_gain * (1.0 + ambassador_lvl))
    return rep_gain
