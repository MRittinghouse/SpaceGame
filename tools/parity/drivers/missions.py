"""Mission goldens (SP3 spec 6.2).

Lifecycle cases force a mission to AVAILABLE through the manager's status table, so each
authored mission is tested alone, whatever its prerequisites. The Godot adapter does the
same through its own manager.
"""

from __future__ import annotations

import copy
import dataclasses

from spacegame.constants.flags import talked_to_npc
from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster
from spacegame.models.mission import MissionManager, MissionObjective, MissionStatus, ObjectiveType
from spacegame.models.player import Player
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.sim_rng import stable_seed
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player, player_snapshot

BOARD_DAYS = range(1, 7)
DEADLINE_MISSION = "iron_delivery"  # 600 credits; full pay to day 14, 0.75 to day 18, then 0.5
DEADLINE_DAYS = (5, 16, 25)
PLAYER_NAME = "ParityPilot"


def _manager() -> MissionManager:
    dl = get_data_loader()
    dl.load_all()
    return MissionManager(copy.deepcopy(dl.missions))


def _satisfy(player: Player, objective: MissionObjective) -> None:
    kind, target, qty = objective.type, objective.target_id, objective.target_quantity
    if kind == ObjectiveType.REACH_SYSTEM:
        player.current_system_id = target
    elif kind == ObjectiveType.TALK_TO_NPC:
        player.dialogue_flags[talked_to_npc(target)] = True
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
    manager = _manager()
    player = fresh_player(name=PLAYER_NAME, credits=5000)
    roster = CrewRoster(dl.crew_templates)
    mission = manager.get_mission(mission_id)
    assert mission is not None
    case = Case("missions", name, {"mission_id": mission_id, "complete_on_day": complete_on_day})
    if mission.crew_member_id:
        roster.recruit(mission.crew_member_id, 4)
    manager._status[mission_id] = MissionStatus.AVAILABLE
    result = manager.accept_mission(mission_id, game_day=1, player=player)
    case.record(
        "accept_mission",
        [mission_id, 1],
        result,
        _mission_state(manager, mission_id, player, roster),
    )
    player.game_day = complete_on_day
    # Satisfy and re-check one objective at a time, breaking as soon as the mission
    # completes. A mission with two distinct reach_system targets (deliver-then-return
    # shapes, several authored side missions) can never have both true from one
    # simultaneous _satisfy pass, because current_system_id holds only one value at a
    # time; check_objectives also stops reporting a mission as newly-completed once its
    # status leaves ACTIVE, so a call made after that point would wrongly read back
    # empty. Stepping through the objectives in their authored order, and recording the
    # call that first reports completion, mirrors how the player actually clears them
    # in play and keeps every authored mission's lifecycle golden real.
    completed: list[str] = []
    for objective in mission.objectives:
        _satisfy(player, objective)
        completed = manager.check_objectives(player, recruited_crew_ids=roster.recruited_ids)
        if mission_id in completed:
            break
    case.record(
        "check_objectives",
        [],
        sorted(completed),
        _mission_state(manager, mission_id, player, roster),
    )
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
    manager = _manager()
    case = Case("missions", "availability", {})
    all_flags = {flag: True for m in manager._missions.values() for flag in m.required_flags}
    for flags, day in (({}, 1), (all_flags, 1), (all_flags, 60)):
        newly = manager.update_availability(dict(flags), player_reputation={}, game_day=day)
        statuses: dict[str, object] = {
            mid: _status_value(manager, mid) for mid in manager._missions
        }
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
