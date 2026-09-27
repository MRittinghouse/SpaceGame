"""Trade price goldens across player profiles (SP3 spec 6.2)."""

from __future__ import annotations

from collections.abc import Callable

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.market import Market
from spacegame.models.player import Player
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
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player

SYSTEMS = ("nexus_prime", "forgeworks", "crimson_reach")
PERKS = (0.0, 0.05)


def _assign_factions(player: Player) -> None:
    for system_id, system in get_data_loader().systems.items():
        player.faction_assignments[system_id] = system.faction


def _max_skill(player: Player, bonus_type: str) -> None:
    for node in player.progression.skills.values():
        if node.bonus_type == bonus_type:
            node.current_level = node.max_level


def _plain() -> Player:
    player = fresh_player()
    _assign_factions(player)
    return player


def _skilled() -> Player:
    player = _plain()
    for bonus_type in (
        "buy_price_reduction",
        "sell_price_bonus",
        "tariff_reduction",
        "black_market_sell_bonus",
        "reputation_gain_bonus",
        "faction_rep_multiplier",
    ):
        _max_skill(player, bonus_type)
    return player


def _crewed() -> Player:
    player = _plain()
    roster = CrewRoster(get_data_loader().crew_templates)
    for crew_id in ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter"):
        roster.recruit(crew_id, 4)
        roster.adjust_loyalty(crew_id, 60)
    player.ship.set_crew_roster(roster)
    return player


def _route() -> Player:
    player = _plain()
    player.previous_system_id = "verdant"
    for _ in range(10):
        player.trade_route_tracker.record_trip("verdant", "nexus_prime")
    return player


def _reputation(rep: int) -> Callable[[], Player]:
    def build() -> Player:
        player = _skilled()
        for faction_id in {s.faction for s in get_data_loader().systems.values()}:
            player.faction_reputation[faction_id] = rep
        return player

    return build


PROFILES: dict[str, Callable[[], Player]] = {
    "plain": _plain,
    "skilled": _skilled,
    "crewed": _crewed,
    "route": _route,
    "hostile": _reputation(-80),
    "allied": _reputation(80),
}


def _profile_case(profile: str) -> Case:
    dl = get_data_loader()
    case = Case("trade", f"prices_{profile}", {"profile": profile, "day": 3})
    for system_id in SYSTEMS:
        player = PROFILES[profile]()
        player.current_system_id = system_id
        market = Market(dl.systems[system_id], list(dl.commodities.values()), game_day=3)
        state: dict[str, object] = {
            "route_bonus": route_bonus(player),
            "tariff": effective_tariff(player),
        }
        for commodity_id in sorted(market.commodities):
            commodity = market.commodities[commodity_id]
            for perk in PERKS:
                result = {
                    "buy": buy_price(player, market, commodity_id, perk),
                    "sell": sell_price(player, market, commodity_id, perk),
                    "bm_buy": black_market_buy_price(market, commodity),
                    "bm_sell": black_market_sell_price(player, market, commodity),
                }
                case.record("prices", [system_id, commodity_id, perk], result, state)
        case.record("refuel_price", [system_id, False], refuel_price(market, False), state)
        case.record("refuel_price", [system_id, True], refuel_price(market, True), state)
        case.record("trade_reputation_gain", [system_id], trade_reputation_gain(player), state)
    return case


def build_cases() -> list[Case]:
    """One case per player profile."""
    return [_profile_case(name) for name in PROFILES]
