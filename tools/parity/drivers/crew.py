"""Crew roster golden cases (SP3 spec 6.2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from tools.parity.driver import Case

COMPANIONS = ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")


def _roster() -> CrewRoster:
    dl = get_data_loader()
    dl.load_all()
    return CrewRoster(dl.crew_templates)


def _bonus_types() -> list[str]:
    dl = get_data_loader()
    return sorted({a.bonus_type for t in dl.crew_templates.values() for a in t.abilities})


def _state(roster: CrewRoster) -> dict[str, object]:
    return {
        "roster": roster.get_state(),
        "bonuses": {bt: roster.get_bonus(bt) for bt in _bonus_types()},
    }


class _Recorder:
    def __init__(self, case: Case, roster: CrewRoster) -> None:
        self.case = case
        self.roster = roster

    def call(self, name: str, *args: object) -> object:
        result = getattr(self.roster, name)(*args)
        self.case.record(name, list(args), result, _state(self.roster))
        return result


def _companions() -> Case:
    case = Case("crew", "companions", {"crew_slots": 4})
    rec = _Recorder(case, _roster())
    for crew_id in COMPANIONS:
        rec.call("recruit", crew_id, 4)
    rec.call("recruit", "juno_park", 4)  # roster full: fails
    rec.call("add_xp_to_all", 60)
    rec.call("add_xp_to_all", 400)
    for amount in (25, 20, 16, -40):
        rec.call("adjust_loyalty", "elena_reeves", amount)
    rec.call("adjust_loyalty_all", 30)
    rec.call("dismiss", "marcus_jin")
    rec.call("recruit", "marcus_jin", 4)  # restores the dismissed state
    return case


def _leadership() -> Case:
    case = Case("crew", "leadership", {"crew_slots": 4})
    rec = _Recorder(case, _roster())
    rec.call("recruit", "elena_reeves", 4)
    rec.call("apply_leadership", 20, True)
    rec.call("adjust_loyalty", "elena_reeves", -50)
    rec.call("adjust_loyalty", "elena_reeves", 70)
    rec.call("apply_leadership", 0, False)
    rec.call("adjust_loyalty", "elena_reeves", 10)
    # The floor and the flag offset both reset on this call: the drop below
    # proves the floor is back at 0, and the later crossings prove the flag
    # offset is only active while legendary is True.
    rec.call("adjust_loyalty", "elena_reeves", -100)
    rec.call("apply_leadership", 0, True)
    rec.call("adjust_loyalty", "elena_reeves", 45)
    rec.call("apply_leadership", 0, False)
    rec.call("adjust_loyalty", "elena_reeves", 10)
    return case


def _triggers() -> Case:
    case = Case("crew", "triggers", {"crew_slots": 4})
    rec = _Recorder(case, _roster())
    for crew_id in COMPANIONS[:2]:
        rec.call("recruit", crew_id, 4)
    rec.call("on_trades", 3, 2, 1)
    rec.call("on_jumps", 4, 2)
    rec.call("on_trades", 1, 0, 0)
    rec.call("on_trades", 10, 0, 1)
    rec.call("on_jumps", 20, 0)
    return case


def _departures() -> Case:
    case = Case("crew", "departures", {"crew_slots": 4})
    rec = _Recorder(case, _roster())
    rec.call("recruit", "tomas_drifter", 4)
    rec.call("adjust_loyalty", "tomas_drifter", -25)
    rec.call("check_departure_warnings")
    rec.call("adjust_loyalty", "tomas_drifter", -10)
    rec.call("process_departures")
    return case


def build_cases() -> list[Case]:
    """Every crew case."""
    return [_companions(), _leadership(), _triggers(), _departures()]
