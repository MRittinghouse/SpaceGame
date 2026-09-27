"""Galaxy-event golden cases: a 200-day run and a forced chain (SP3 spec 6.2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.galaxy_event import GalaxyEvent, GalaxyEventGenerator
from tools.parity.driver import Case

RUN_DAYS = range(1, 201)
CHAIN_DAYS = range(2, 31)


def _generator() -> GalaxyEventGenerator:
    dl = get_data_loader()
    dl.load_all()
    return GalaxyEventGenerator(dl.galaxy_event_templates, chains=dl.galaxy_event_chains)


def _state(gen: GalaxyEventGenerator, active: dict[str, list[GalaxyEvent]]) -> dict[str, object]:
    return {
        "active": {sid: [e.to_dict() for e in events] for sid, events in active.items()},
        "pending_chains": [[day, template_id] for day, template_id in gen.pending_chains()],
    }


def _advance(
    case: Case, gen: GalaxyEventGenerator, active: dict[str, list[GalaxyEvent]], day: int
) -> None:
    new = gen.advance_day(day, active)
    case.record("advance_day", [day], new.to_dict() if new else None, _state(gen, active))


def _run() -> Case:
    case = Case("galaxy", "events_days_1_200", {"days": [RUN_DAYS.start, RUN_DAYS.stop - 1]})
    gen = _generator()
    active: dict[str, list[GalaxyEvent]] = {}
    for day in RUN_DAYS:
        _advance(case, gen, active, day)
    return case


def _chain() -> Case:
    gen = _generator()
    head = gen._build_event_from_template(gen._template_by_id["breakstone_strike"], 1)
    case = Case("galaxy", "strike_chain", {"head": head.to_dict()})
    active = {head.system_id: [head]}
    for day in CHAIN_DAYS:
        _advance(case, gen, active, day)
    return case


def build_cases() -> list[Case]:
    """Every galaxy-event case."""
    return [_run(), _chain()]
