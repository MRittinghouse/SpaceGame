"""Trade and player goldens (SP3 spec 6.2)."""

from __future__ import annotations

from tools.parity.drivers import player, trade


def test_every_profile_prices_every_system() -> None:
    names = {case.name for case in trade.build_cases()}
    assert names == {f"prices_{p}" for p in trade.PROFILES}


def test_player_cases_record_failures_and_payouts() -> None:
    cases = {case.name: case for case in player.build_cases()}
    buys = [s["result"] for s in cases["trading"].steps if s["call"] == "buy_commodity"]
    assert [r[0] for r in buys] == [True, True, False, False]
    victory = cases["payouts"].steps[0]["result"]
    assert victory["xp"] > 0 and victory["credits"] > 0


def test_cases_are_stable() -> None:
    for module in (trade, player):
        assert [c.to_json("x") for c in module.build_cases()] == [
            c.to_json("x") for c in module.build_cases()
        ]
