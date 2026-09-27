"""Trade price goldens across player profiles (SP3 spec 6.2)."""

from __future__ import annotations

from typing import Any

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
_BONUS_TYPES = (
    "buy_price_reduction",
    "sell_price_bonus",
    "tariff_reduction",
    "black_market_sell_bonus",
    "reputation_gain_bonus",
    "faction_rep_multiplier",
)
_CREW_RECRUIT_ORDER = ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")
_CREW_SLOTS = 4


def _max_skill(player: Player, bonus_type: str) -> None:
    for node in player.progression.skills.values():
        if node.bonus_type == bonus_type:
            node.current_level = node.max_level


def _faction_assignments() -> dict[str, str]:
    return {system_id: system.faction for system_id, system in get_data_loader().systems.items()}


def _all_factions() -> list[str]:
    return sorted({system.faction for system in get_data_loader().systems.values()})


def _profile_setup(profile: str) -> dict[str, Any]:
    """One profile's setup dict: initial state no step records (progress.md:233)."""
    skilled = profile in ("skilled", "hostile", "allied")
    reputation = {"hostile": -80, "allied": 80}.get(profile)
    return {
        "player": {
            "name": "ParityPilot",
            "credits": 10000,
            "system_id": "nexus_prime",
            "ship_type": "shuttle",
            "fuel": 40,
        },
        "faction_assignments": _faction_assignments(),
        "max_level_bonus_types": list(_BONUS_TYPES) if skilled else [],
        "faction_reputation": (
            dict.fromkeys(_all_factions(), reputation) if reputation is not None else {}
        ),
        "crew_slots": _CREW_SLOTS,
        "crew": (
            [{"crew_id": crew_id, "loyalty_delta": 60} for crew_id in _CREW_RECRUIT_ORDER]
            if profile == "crewed"
            else []
        ),
        "previous_system_id": "verdant" if profile == "route" else "",
        "route_trips": (
            [{"origin": "verdant", "destination": "nexus_prime", "count": 10}]
            if profile == "route"
            else []
        ),
    }


PROFILES: dict[str, dict[str, Any]] = {
    name: _profile_setup(name)
    for name in ("plain", "skilled", "crewed", "route", "hostile", "allied")
}


def _build_player(setup: dict[str, Any]) -> Player:
    """Construct a Player from a setup dict plus synced data only."""
    fields = setup["player"]
    player = fresh_player(
        name=fields["name"],
        credits=fields["credits"],
        system_id=fields["system_id"],
        ship_type_id=fields["ship_type"],
        fuel=fields["fuel"],
    )
    for system_id, faction in setup["faction_assignments"].items():
        player.faction_assignments[system_id] = faction
    for bonus_type in setup["max_level_bonus_types"]:
        _max_skill(player, bonus_type)
    for faction_id, rep in setup["faction_reputation"].items():
        player.faction_reputation[faction_id] = rep
    crew = setup["crew"]
    if crew:
        roster = CrewRoster(get_data_loader().crew_templates)
        for entry in crew:
            roster.recruit(entry["crew_id"], setup["crew_slots"])
            roster.adjust_loyalty(entry["crew_id"], entry["loyalty_delta"])
        player.ship.set_crew_roster(roster)
    player.previous_system_id = setup["previous_system_id"]
    for trip in setup["route_trips"]:
        for _ in range(trip["count"]):
            player.trade_route_tracker.record_trip(trip["origin"], trip["destination"])
    return player


def _profile_case(profile: str) -> Case:
    dl = get_data_loader()
    setup = PROFILES[profile]
    case_setup: dict[str, Any] = dict(setup)
    case_setup["profile"] = profile
    case_setup["day"] = 3
    case = Case("trade", f"prices_{profile}", case_setup)
    for system_id in SYSTEMS:
        player = _build_player(setup)
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
