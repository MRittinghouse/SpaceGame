"""Market pricing golden cases, the SP2 tracer bullet (SP2 spec Section 7.4).

Market events, politics shifts, and galaxy-event multipliers are SP3 cases.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.commodity import Commodity
from spacegame.models.event import EventType, MarketEvent
from spacegame.models.galaxy_event import GalaxyEvent, GalaxyEventGenerator
from spacegame.models.market import Market, PriceHistory
from spacegame.models.politics_dispute import PoliticsMarketShift
from tools.parity.driver import Case

PRICE_TABLE_DAYS = range(2, 31)  # spec 7.4: days 1 to 30
DECAY_DAYS = range(2, 21)


def _all_commodities() -> list[Commodity]:
    return list(get_data_loader().commodities.values())


def _snapshot(market: Market) -> dict[str, object]:
    return {"game_day": market.game_day, "prices": market.get_all_prices(), **market.to_dict()}


class _Recorder:
    """Applies calls to one Market and records each with the state after it."""

    def __init__(self, case: Case, system_id: str, day: int) -> None:
        self.case = case
        self.system = get_data_loader().systems[system_id]
        self.market = Market(self.system, _all_commodities(), game_day=day)

    def call(self, name: str, *args: object) -> object:
        if name == "snapshot":
            result: object = None
        elif name == "initialize_stock":
            self.market.initialize_stock(self.system, _all_commodities())
            result = None
        elif name == "apply_event":
            spec = dict(args[0])  # type: ignore[call-overload]
            spec["event_type"] = EventType(spec["event_type"])
            self.market.apply_event(MarketEvent(**spec))
            result = None
        elif name == "add_politics_shift":
            self.market.add_politics_shift(PoliticsMarketShift(**args[0]))  # type: ignore[arg-type]
            result = None
        elif name == "add_galaxy_event":
            # No public entry point exists: game.py never feeds galaxy events to markets (F-2).
            self.market.galaxy_events.append(GalaxyEvent.from_dict(args[0]))  # type: ignore[arg-type]
            self.market._generate_prices()
            result = None
        else:
            result = getattr(self.market, name)(*args)
        self.case.record(name, list(args), result, _snapshot(self.market))
        return result


def _priced_ids(market: Market) -> list[str]:
    return sorted(cid for cid, c in market.commodities.items() if c.base_price > 0)


def _price_tables() -> list[Case]:
    cases: list[Case] = []
    for system_id in get_data_loader().systems:
        case = Case("market", f"price_table_{system_id}", {"system_id": system_id, "day": 1})
        rec = _Recorder(case, system_id, 1)
        rec.call("snapshot")
        for day in PRICE_TABLE_DAYS:
            rec.call("update_day", day)
        cases.append(case)
    return cases


def _pressure(system_id: str) -> Case:
    case = Case("market", f"player_pressure_{system_id}", {"system_id": system_id, "day": 1})
    rec = _Recorder(case, system_id, 1)
    first, second = _priced_ids(rec.market)[:2]
    rec.call("snapshot")
    rec.call("initialize_stock")
    rec.call("record_buy", first, 5)
    rec.call("record_buy", first, 20)
    rec.call("record_sell", second, 3)
    rec.call("record_sell", second, 30)
    rec.call("record_buy", second, 7)
    for day in DECAY_DAYS:
        rec.call("update_day", day)
    return case


def _stock() -> Case:
    case = Case("market", "stock_nexus_prime", {"system_id": "nexus_prime", "day": 1})
    rec = _Recorder(case, "nexus_prime", 1)
    first, second = _priced_ids(rec.market)[:2]
    rec.call("snapshot")
    rec.call("initialize_stock")
    rec.call("deplete_stock", first, 10)
    rec.call("deplete_stock", first, 100_000)
    rec.call("deplete_stock", second, rec.market.get_stock(second))
    for _ in range(4):
        rec.call("regenerate_stock")
    rec.call("deplete_stock", "not_a_commodity", 1)
    return case


def _off_market() -> Case:
    case = Case("market", "off_market_herons_mark", {"system_id": "herons_mark", "day": 1})
    rec = _Recorder(case, "herons_mark", 1)
    rec.call("snapshot")
    rec.call("get_price", "food")
    rec.call("get_sell_price", "food")
    rec.call("get_sell_price", "data_chip")
    rec.call("get_sell_price", "not_a_commodity")
    rec.call("initialize_stock")
    return case


def _history(name: str, steps: list[tuple[str, list[object]]]) -> Case:
    case = Case("price_history", name, {"max_days": 7})
    history = PriceHistory(max_days=7)
    for call, args in steps:
        result = getattr(history, call)(*args)
        case.record(call, args, result, history.to_dict())
    return case


def _histories() -> list[Case]:
    rising: list[tuple[str, list[object]]] = [
        ("record", ["nexus_prime", "food", day, 20 + day * 3]) for day in range(1, 11)
    ]
    rising += [("get_history", ["nexus_prime", "food"]), ("get_trend", ["nexus_prime", "food"])]
    falling: list[tuple[str, list[object]]] = [
        ("record", ["verdant", "fuel", day, 100 - day * 4]) for day in range(1, 6)
    ]
    falling += [("get_trend", ["verdant", "fuel"])]
    edges: list[tuple[str, list[object]]] = [
        ("get_trend", ["nowhere", "food"]),
        ("get_history", ["nowhere", "food"]),
        ("record", ["axiom_labs", "medical", 1, 50]),
        ("get_trend", ["axiom_labs", "medical"]),
        ("record", ["axiom_labs", "medical", 2, 51]),
        ("get_trend", ["axiom_labs", "medical"]),
        ("record", ["axiom_labs", "art", 1, 0]),
        ("record", ["axiom_labs", "art", 2, 3]),
        ("get_trend", ["axiom_labs", "art"]),
    ]
    return [
        _history("rising_trims", rising),
        _history("falling", falling),
        _history("edges", edges),
    ]


EVENT_MULTIPLIERS = (("shortage", 1.8), ("surplus", 0.6), ("disaster", 2.5), ("boom", 1.4))


def _event_cases() -> list[Case]:
    cases: list[Case] = []
    for event_type, mult in EVENT_MULTIPLIERS:
        case = Case("market", f"event_{event_type}", {"system_id": "nexus_prime", "day": 1})
        rec = _Recorder(case, "nexus_prime", 1)
        rec.call(
            "apply_event",
            {
                "event_type": event_type,
                "commodity_id": "food",
                "system_id": "nexus_prime",
                "price_multiplier": mult,
                "duration_days": 4,
                "day_started": 1,
                "description": event_type,
            },
        )
        for day in range(2, 8):
            rec.call("update_day", day)
        cases.append(case)
    return cases


def _politics_case() -> Case:
    case = Case("market", "politics_shifts", {"system_id": "nexus_prime", "day": 1})
    rec = _Recorder(case, "nexus_prime", 1)
    rec.call(
        "add_politics_shift",
        {
            "commodity_id": "food",
            "system_id": "nexus_prime",
            "magnitude": 0.1,
            "duration_days": 5,
            "start_day": 1,
        },
    )
    rec.call(
        "add_politics_shift",
        {
            "commodity_id": "food",
            "system_id": "nexus_prime",
            "magnitude": -0.25,
            "duration_days": 3,
            "start_day": 2,
        },
    )
    rec.call(
        "add_politics_shift",
        {
            "commodity_id": "food",
            "system_id": "verdant",
            "magnitude": 0.5,
            "duration_days": 9,
            "start_day": 1,
        },
    )
    for day in range(2, 11):
        rec.call("update_day", day)
    return case


def _galaxy_event_cases() -> list[Case]:
    dl = get_data_loader()
    gen = GalaxyEventGenerator(dl.galaxy_event_templates, chains=dl.galaxy_event_chains)
    cases: list[Case] = []
    seen: set[str] = set()
    for template in dl.galaxy_event_templates:
        event_type = str(template["event_type"])
        if event_type in seen or event_type == "pirate_surge":
            continue
        seen.add(event_type)
        # The private _build_event_from_template is used on purpose: the built event is
        # recorded as event.to_dict() in the add_galaxy_event step's args, so the Godot
        # adapter rebuilds it from that dict and never re-rolls it.
        event = gen._build_event_from_template(template, 1)
        system_id = event.system_id
        case = Case("market", f"galaxy_{event_type}", {"system_id": system_id, "day": 1})
        rec = _Recorder(case, system_id, 1)
        rec.call("add_galaxy_event", event.to_dict())
        for day in range(2, event.duration_days + 3):
            rec.call("update_day", day)
        cases.append(case)
    return cases


def build_cases() -> list[Case]:
    """Every market and price-history case."""
    return [
        *_price_tables(),
        _pressure("nexus_prime"),
        _pressure("forgeworks"),
        _stock(),
        _off_market(),
        *_histories(),
        *_event_cases(),
        _politics_case(),
        *_galaxy_event_cases(),
    ]
