"""Crew roster golden cases (SP3 spec 6.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.crew_scene import SceneContext, refusal
from tools.parity.driver import Case

COMPANIONS = ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")


def _roster() -> CrewRoster:
    dl = get_data_loader()
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


_AT_30: tuple[tuple[str, int], ...] = tuple((crew_id, 30) for crew_id in COMPANIONS)


def _with(
    loyalty: tuple[tuple[str, int], ...], crew_id: str, value: int
) -> tuple[tuple[str, int], ...]:
    return tuple((cid, value if cid == crew_id else held) for cid, held in loyalty)


@dataclass(frozen=True)
class _SceneStep:
    """One state the scenes_due case reads the gate in (polish design 3.1)."""

    label: str
    loyalty: tuple[tuple[str, int], ...] = _AT_30
    offset: int = 0
    statuses: tuple[tuple[str, str], ...] = ()
    flags: tuple[str, ...] = ()
    system_id: str = "nexus_prime"
    spoken: tuple[str, ...] = ()

    def args(self) -> dict[str, Any]:
        """The step's state as the golden records it."""
        return {
            "loyalty": dict(self.loyalty),
            "offset": self.offset,
            "statuses": dict(self.statuses),
            "flags": list(self.flags),
            "system_id": self.system_id,
            "spoken": list(self.spoken),
        }


_ELENA_DONE = (("elena_old_charts", "completed"), ("elena_wreck_meridian", "active"))
_SCENE_STEPS: tuple[_SceneStep, ...] = (
    _SceneStep("fresh"),
    _SceneStep("Elena at the mark", loyalty=_with(_AT_30, "elena_reeves", 50)),
    _SceneStep("Legend", loyalty=_with(_AT_30, "marcus_jin", 40), offset=10),
    _SceneStep(
        "Elena spoke this landing",
        loyalty=_with(_AT_30, "elena_reeves", 50),
        spoken=("elena_reeves",),
    ),
    _SceneStep(
        "agreed, away",
        loyalty=_with(_AT_30, "elena_reeves", 55),
        statuses=(("elena_old_charts", "active"),),
        flags=("elena_old_charts_agreed",),
    ),
    _SceneStep(
        "agreed, there",
        loyalty=_with(_AT_30, "elena_reeves", 55),
        statuses=(("elena_old_charts", "active"),),
        flags=("elena_old_charts_agreed",),
        system_id="stellaris_port",
        spoken=("elena_reeves",),
    ),
    _SceneStep(
        "declined",
        loyalty=_with(_AT_30, "elena_reeves", 50),
        flags=("elena_old_charts_declined",),
    ),
    _SceneStep(
        "stage 2",
        loyalty=_with(_AT_30, "elena_reeves", 70),
        statuses=(("elena_old_charts", "completed"),),
        flags=("elena_quest_stage1_complete",),
    ),
    _SceneStep(
        "Elena dismissed",
        loyalty=_AT_30[1:],
        statuses=_ELENA_DONE,
        flags=("elena_quest_stage1_complete", "elena_wreck_meridian_agreed"),
        system_id="iron_depths",
    ),
    _SceneStep(
        "Elena rehired",
        loyalty=_with(_AT_30, "elena_reeves", 72),
        statuses=_ELENA_DONE,
        flags=("elena_quest_stage1_complete", "elena_wreck_meridian_agreed"),
        system_id="iron_depths",
    ),
    _SceneStep("Tomas at the mark", loyalty=_with(_AT_30, "tomas_drifter", 50)),
    _SceneStep(
        "the inspector's stage",
        loyalty=_with(_AT_30, "marcus_jin", 75),
        statuses=(("marcus_old_debts", "completed"), ("marcus_the_inspector", "active")),
        flags=("marcus_quest_stage1_complete", "marcus_the_inspector_agreed"),
        system_id="forgeworks",
    ),
)


def _scenes_due() -> Case:
    """The crew scenes' gate (polish design 3.1): every scene read in each step's state."""
    dl = get_data_loader()
    scenes = list(dl.crew_scenes.values())
    names = {tid: template.name for tid, template in dl.crew_templates.items()}
    systems = {sid: system.name for sid, system in dl.systems.items()}
    case = Case("crew", "scenes_due", {"scene_ids": [scene.id for scene in scenes]})
    for step in _SCENE_STEPS:
        ctx = SceneContext(
            crew_names=names,
            loyalty=dict(step.loyalty),
            loyalty_offset=step.offset,
            statuses=dict(step.statuses),
            flags=dict.fromkeys(step.flags, True),
            system_id=step.system_id,
            system_names=systems,
            spoken=frozenset(step.spoken),
        )
        result = {scene.id: refusal(scene, ctx) for scene in scenes}
        case.record("due", [step.label, step.args()], result, {})
    return case


def build_cases() -> list[Case]:
    """Every crew case."""
    get_data_loader().load_all()
    return [_companions(), _leadership(), _triggers(), _departures(), _scenes_due()]
