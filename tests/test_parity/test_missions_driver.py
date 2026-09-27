"""Mission goldens: procedural boards, every authored mission's lifecycle, deadlines."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from tools.parity.drivers import missions


def _named() -> dict:
    return {case.name: case for case in missions.build_cases()}


def test_a_board_per_system_and_a_lifecycle_per_mission() -> None:
    cases = _named()
    dl = get_data_loader()
    for system_id in dl.systems:
        assert f"board_{system_id}" in cases
    for mission in dl.missions:
        assert f"lifecycle_{mission.id}" in cases


def test_every_authored_mission_completes() -> None:
    for name, case in _named().items():
        if name.startswith("lifecycle_"):
            assert any(s["call"] == "complete_mission" for s in case.steps), name


def test_soft_deadline_multipliers_differ() -> None:
    cases = _named()
    credits = [
        cases[f"soft_deadline_{days}"].steps[-1]["state"]["player"]["credits"]
        for days in missions.DEADLINE_DAYS
    ]
    assert len(set(credits)) == len(credits)


def test_cases_are_stable() -> None:
    assert [c.to_json("x") for c in missions.build_cases()] == [
        c.to_json("x") for c in missions.build_cases()
    ]
