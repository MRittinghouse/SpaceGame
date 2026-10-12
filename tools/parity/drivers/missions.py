"""Mission goldens (SP3 spec 6.2).

Lifecycle cases force a mission to AVAILABLE through MissionManager.load_state, from
setup["mission_state"], a public path the Godot manager also has. Each authored mission is
tested alone, whatever its prerequisites.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

from spacegame.constants.flags import talked_to_npc
from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.flag_producers import content_flag_producers
from spacegame.models.mission import MissionManager, MissionObjective, ObjectiveType
from spacegame.models.player import Player
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.sim_rng import stable_seed
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player, player_snapshot

BOARD_DAYS = range(1, 7)
# 600 credits for ten units, paid on the units aboard; the driver meets the one-unit collect
# objective, so 60 to day 14, 45 to day 18, then 30
DEADLINE_MISSION = "iron_delivery"
DEADLINE_DAYS = (5, 16, 25)
PLAYER_NAME = "ParityPilot"


def _manager() -> MissionManager:
    dl = get_data_loader()
    return MissionManager(
        copy.deepcopy(dl.missions),
        produced_flags=content_flag_producers(
            dl.dialogue_trees.values(), dl.encounter_definitions, dl.npcs.values()
        ),
    )


def _build_player(fields: dict[str, Any]) -> Player:
    """Construct a Player from a setup's player sub-dict, plus synced data only."""
    return fresh_player(
        name=fields["name"],
        credits=fields["credits"],
        system_id=fields["system_id"],
        ship_type_id=fields["ship_type"],
        fuel=fields["fuel"],
    )


def _satisfy(manager: MissionManager, player: Player, objective: MissionObjective) -> None:
    kind, target, qty = objective.type, objective.target_id, objective.target_quantity
    if kind == ObjectiveType.REACH_SYSTEM:
        player.current_system_id = target
    elif kind == ObjectiveType.TALK_TO_NPC:
        player.dialogue_flags[talked_to_npc(target)] = True
        manager.record_conversation(target)
    elif kind == ObjectiveType.HAVE_CREDITS:
        player.credits = max(player.credits, qty)
    elif kind == ObjectiveType.COLLECT_CARGO:
        player.ship.add_cargo(target, qty, 0)
    elif kind == ObjectiveType.HAS_FLAG:
        player.dialogue_flags[target] = True
    elif kind == ObjectiveType.COMPLETE_TRADE:
        player.trades_completed = max(player.trades_completed, qty)
    elif kind == ObjectiveType.WIN_COMBAT:
        player.combats_won = max(player.combats_won, qty)


def _status_value(manager: MissionManager, mission_id: str) -> str:
    """The status string for a mission id known to ``manager``.

    ``get_status`` types as ``Optional`` for an id it has never heard of, but every
    caller here reads back an id the same manager just accepted or enumerated.
    """
    status = manager.get_status(mission_id)
    assert status is not None
    return status.value


def _mission_state(
    manager: MissionManager, mission_id: str, player: Player, roster: CrewRoster
) -> dict[str, object]:
    return {
        "status": _status_value(manager, mission_id),
        "progress": list(manager.get_objective_progress(mission_id)),
        "player": player_snapshot(player),
        "crew": roster.get_state(),
    }


def _lifecycle(mission_id: str, name: str, *, complete_on_day: int = 1) -> Case:
    dl = get_data_loader()
    loader_mission = next(m for m in dl.missions if m.id == mission_id)
    player_fields: dict[str, Any] = {
        "name": PLAYER_NAME,
        "credits": 5000,
        "system_id": "nexus_prime",
        "ship_type": "shuttle",
        "fuel": 40,
    }
    crew_entries: list[dict[str, Any]] = (
        [{"crew_id": loader_mission.crew_member_id}] if loader_mission.crew_member_id else []
    )
    mission_state: dict[str, Any] = {"status": {mission_id: "available"}}
    setup: dict[str, Any] = {
        "mission_id": mission_id,
        "complete_on_day": complete_on_day,
        "player": player_fields,
        "crew_slots": 4,
        "crew": crew_entries,
        "mission_state": mission_state,
        "reputation_spillover": False,
    }
    case = Case("missions", name, setup)

    manager = _manager()
    player = _build_player(setup["player"])
    roster = CrewRoster(dl.crew_templates)
    for entry in setup["crew"]:
        roster.recruit(entry["crew_id"], setup["crew_slots"])
    manager.load_state(setup["mission_state"])
    mission = manager.get_mission(mission_id)
    assert mission is not None

    result = manager.accept_mission(mission_id, game_day=1, player=player)
    case.record(
        "accept_mission",
        [mission_id, 1],
        result,
        _mission_state(manager, mission_id, player, roster),
    )
    player.game_day = setup["complete_on_day"]
    # Each check step is exactly one check_objectives call, made after _satisfy applied
    # objectives[args[0]]. The loop stops at the call that completes the mission. The
    # objective-progress lock (check_objectives never re-evaluates an objective already
    # marked true) plus the side-mission HAS_FLAG auto-resolve are why a golden can end
    # before its last objective.
    completed: list[str] = []
    for index, objective in enumerate(mission.objectives):
        _satisfy(manager, player, objective)
        completed = manager.check_objectives(player, recruited_crew_ids=roster.recruited_ids)
        case.record(
            "check_objectives",
            [index],
            sorted(completed),
            _mission_state(manager, mission_id, player, roster),
        )
        if mission_id in completed:
            break
    if mission_id in completed:
        done = manager.complete_mission(
            mission_id, player, crew_roster=roster, faction_ids=list(dl.factions)
        )
        case.record(
            "complete_mission",
            [mission_id],
            dataclasses.asdict(done),
            _mission_state(manager, mission_id, player, roster),
        )
    return case


def _board(system_id: str) -> Case:
    dl = get_data_loader()
    seed = stable_seed("player", PLAYER_NAME)
    generator = ProceduralMissionGenerator(
        dl.systems, dl.commodities, dl.enemy_templates, seed=seed
    )
    case = Case("missions", f"board_{system_id}", {"seed": seed})
    for day in BOARD_DAYS:
        board = generator.generate_for_system(system_id, day)
        case.record("generate_for_system", [system_id, day], [m.to_dict() for m in board], {})
    return case


def _availability() -> Case:
    dl = get_data_loader()
    manager = _manager()
    reputation: dict[str, int] = {}
    setup: dict[str, Any] = {"player_reputation": reputation, "player": None}
    case = Case("missions", "availability", setup)
    all_flags = {flag: True for m in dl.missions for flag in m.required_flags}
    for flags, day in (({}, 1), (all_flags, 1), (all_flags, 60)):
        # args[0] lists the flag names, each passed as True in the flags dict.
        newly = manager.update_availability(
            dict(flags), player_reputation=reputation, game_day=day, player=None
        )
        statuses = manager.get_state()["status"]
        case.record("update_availability", [sorted(flags), day], sorted(newly), statuses)
    return case


def build_cases() -> list[Case]:
    """Every mission case."""
    dl = get_data_loader()
    dl.load_all()
    return [
        *[_board(system_id) for system_id in dl.systems],
        *[_lifecycle(m.id, f"lifecycle_{m.id}") for m in dl.missions],
        *[
            _lifecycle(DEADLINE_MISSION, f"soft_deadline_{d}", complete_on_day=d)
            for d in DEADLINE_DAYS
        ],
        _availability(),
    ]
