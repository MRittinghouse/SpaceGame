"""Mission goldens: procedural boards, every authored mission's lifecycle, deadlines."""

from __future__ import annotations

import dataclasses

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from tools.parity.driver import Case
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


def test_lifecycles_replay_from_setup() -> None:
    """Every lifecycle_* and soft_deadline_* case rebuilds from setup and synced data alone.

    Rebuilds a fresh Case from case.setup, the recorded step args, and synced data (the
    data loader, and the driver's own _manager/_build_player/_satisfy/_mission_state
    helpers) with exactly one model call per recorded step, and checks the replay matches
    the golden byte for byte. Never calls missions._lifecycle: the point is to prove the
    case is rebuildable by an adapter that only has setup and args, not driver internals.
    """
    dl = get_data_loader()
    dl.load_all()
    for case in missions.build_cases():
        if not (case.name.startswith("lifecycle_") or case.name.startswith("soft_deadline_")):
            continue
        assert set(case.setup["player"]) == {"name", "credits", "system_id", "ship_type", "fuel"}
        assert {"crew_slots", "crew", "mission_state", "reputation_spillover"} <= set(case.setup)

        manager = missions._manager()
        player = missions._build_player(case.setup["player"])
        roster = CrewRoster(dl.crew_templates)
        for entry in case.setup["crew"]:
            roster.recruit(entry["crew_id"], case.setup["crew_slots"])
        manager.load_state(case.setup["mission_state"])
        mission = manager.get_mission(case.setup["mission_id"])
        assert mission is not None

        replay = Case("missions", case.name, case.setup)
        for step in case.steps:
            call, args = step["call"], step["args"]
            if call == "accept_mission":
                result = manager.accept_mission(args[0], game_day=args[1], player=player)
                replay.record(
                    "accept_mission",
                    args,
                    result,
                    missions._mission_state(manager, case.setup["mission_id"], player, roster),
                )
                player.game_day = case.setup["complete_on_day"]
            elif call == "check_objectives":
                missions._satisfy(player, mission.objectives[args[0]])
                completed = manager.check_objectives(
                    player, recruited_crew_ids=roster.recruited_ids
                )
                replay.record(
                    "check_objectives",
                    args,
                    sorted(completed),
                    missions._mission_state(manager, case.setup["mission_id"], player, roster),
                )
            elif call == "complete_mission":
                done = manager.complete_mission(
                    args[0], player, crew_roster=roster, faction_ids=list(dl.factions)
                )
                replay.record(
                    "complete_mission",
                    args,
                    dataclasses.asdict(done),
                    missions._mission_state(manager, case.setup["mission_id"], player, roster),
                )
        assert replay.to_json("x") == case.to_json("x"), case.name
