"""Trade and player goldens (SP3 spec 6.2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from tools.parity.drivers import player, trade

_PLAYER_KEYS = {"name", "credits", "system_id", "ship_type", "fuel"}
_BONUS_TYPES = [
    "buy_price_reduction",
    "sell_price_bonus",
    "tariff_reduction",
    "black_market_sell_bonus",
    "reputation_gain_bonus",
    "faction_rep_multiplier",
]


def _all_setups() -> list[dict[str, object]]:
    setups = [case.setup for case in trade.build_cases()]
    setups += [case.setup for case in player.build_cases()]
    return setups


def test_every_setup_has_the_five_key_player_dict() -> None:
    for setup in _all_setups():
        assert set(setup["player"]) == _PLAYER_KEYS  # type: ignore[arg-type]


def test_every_profile_prices_every_system() -> None:
    names = {case.name for case in trade.build_cases()}
    assert names == {f"prices_{p}" for p in trade.PROFILES}


def test_reputation_profiles_pin_max_skills_and_reputation() -> None:
    factions = {s.faction for s in get_data_loader().systems.values()}
    for profile, expected_rep in (("allied", 80), ("hostile", -80)):
        setup = trade.PROFILES[profile]
        assert setup["max_level_bonus_types"] == _BONUS_TYPES
        assert setup["faction_reputation"] == {f: expected_rep for f in factions}


def test_crewed_profile_lists_crew_in_recruit_order() -> None:
    setup = trade.PROFILES["crewed"]
    assert setup["crew"] == [
        {"crew_id": crew_id, "loyalty_delta": 60}
        for crew_id in ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")
    ]


def test_route_profile_carries_previous_system_and_trips() -> None:
    setup = trade.PROFILES["route"]
    assert setup["previous_system_id"] == "verdant"
    assert setup["route_trips"] == [
        {"origin": "verdant", "destination": "nexus_prime", "count": 10}
    ]


def test_every_trade_setup_has_full_faction_assignments() -> None:
    expected = {sid: s.faction for sid, s in get_data_loader().systems.items()}
    for setup in trade.PROFILES.values():
        assert setup["faction_assignments"] == expected


def test_defeat_setups_pin_cargo_credits_and_bonuses() -> None:
    cases = {case.name: case for case in player.build_cases()}
    defeat_setup = cases["defeat"].setup
    assert defeat_setup["cargo"] == [
        {"commodity_id": "food", "quantity": 20, "price": 10},
        {"commodity_id": "electronics", "quantity": 10, "price": 10},
        {"commodity_id": "scrap_metal", "quantity": 1, "price": 10},
    ]
    assert defeat_setup["player"]["credits"] == 3000  # type: ignore[index]
    assert defeat_setup["faction_assignments"] == {"nexus_prime": "commerce_guild"}
    assert cases["defeat_insured"].setup["max_level_bonus_types"] == ["insurance"]


def test_defeat_quest_cargo_case_keeps_the_quest_good() -> None:
    cases = {case.name: case for case in player.build_cases()}
    case = cases["defeat_quest_cargo"]
    assert {e["commodity_id"] for e in case.setup["cargo"]} >= {"data_chip"}  # type: ignore[union-attr]
    cargo = case.steps[0]["state"]["ship"]["current_cargo"]  # type: ignore[index]
    assert cargo["data_chip"] == 1
    assert cargo["food"] == 14


def test_player_cases_record_failures_and_payouts() -> None:
    cases = {case.name: case for case in player.build_cases()}
    buys = [s["result"] for s in cases["trading"].steps if s["call"] == "buy_commodity"]
    assert [r[0] for r in buys] == [True, True, False, False]
    assert buys[3][1] == "Insufficient cargo space"
    refuels = [s["result"] for s in cases["trading"].steps if s["call"] == "refuel_ship"]
    assert any(r[1] == "Added 55 fuel (tank full) for 495 CR" for r in refuels)
    victory = cases["payouts"].steps[0]["result"]
    assert victory["xp"] > 0 and victory["credits"] > 0


def test_cases_are_stable() -> None:
    for module in (trade, player):
        assert [c.to_json("x") for c in module.build_cases()] == [
            c.to_json("x") for c in module.build_cases()
        ]
