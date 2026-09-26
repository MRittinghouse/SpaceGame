"""Market goldens cover every system, pressure, stock, and the empty market."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from tools.parity.drivers.market import build_cases


def _cases() -> dict[str, object]:
    return {case.name: case for case in build_cases()}


class TestMarketCases:
    def test_a_price_table_per_system(self) -> None:
        names = set(_cases())
        for system_id in get_data_loader().systems:
            assert f"price_table_{system_id}" in names

    def test_empty_market_is_recorded(self) -> None:
        case = _cases()["off_market_herons_mark"]
        first = case.steps[0]  # type: ignore[attr-defined]
        assert first["call"] == "snapshot"
        assert first["state"]["prices"] == {}

    def test_pressure_hits_both_caps_then_decays_away(self) -> None:
        case = _cases()["player_pressure_nexus_prime"]
        mods = [step["state"]["player_supply_demand"] for step in case.steps]  # type: ignore[attr-defined]
        values = [v for m in mods for v in m.values()]
        assert 0.3 in values and -0.3 in values, "both caps must be reached"
        assert mods[-1] == {}, "decay must expire every modifier"

    def test_stock_case_records_a_failed_depletion(self) -> None:
        case = _cases()["stock_nexus_prime"]
        results = [s["result"] for s in case.steps if s["call"] == "deplete_stock"]  # type: ignore[attr-defined]
        assert any(r[0] is False for r in results)
        assert any(r[0] is True for r in results)

    def test_price_history_covers_every_trend(self) -> None:
        trends = {
            s["result"]
            for c in build_cases()
            if c.subsystem == "price_history"
            for s in c.steps
            if s["call"] == "get_trend"
        }
        assert trends == {"rising", "falling", "stable"}

    def test_cases_are_stable(self) -> None:
        assert [c.to_json("x") for c in build_cases()] == [c.to_json("x") for c in build_cases()]
