"""Dialogue goldens: every response of every node, and the ambient line pickers.

Each response is selected from a fresh manager positioned on its node, so steps are
independent. Two profiles: "novice" (default social skills, no flags) and "expert" (every
social skill at 10, every flag the tree's responses require). Reputation changes need a
PoliticsManager (wave B), so they are skipped here, as Python skips them without one
(ruling P5).
"""

from __future__ import annotations

import dataclasses

from spacegame.data_loader import get_data_loader
from spacegame.models.ambient_dialogue import AmbientDialogueManager
from spacegame.models.crew import CrewRoster
from spacegame.models.crew_interjection import CrewInterjectionResolver
from spacegame.models.dialogue import DialogueManager, DialogueTree
from spacegame.models.social import SocialManager
from spacegame.models.station_chatter import StationChatterManager
from spacegame.sim_rng import SimRng, stable_seed
from tools.parity.driver import Case
from tools.parity.drivers.combat import LOADOUTS, build_fight, play_round

COMPANIONS = ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")
LOYALTY = 60


def _npc_for(tree_id: str) -> str | None:
    for npc_id, npc in get_data_loader().npcs.items():
        if npc.dialogue_id == tree_id:
            return npc_id
    return None


def _required_flags(tree: DialogueTree) -> dict[str, bool]:
    return {
        f: True for node in tree.nodes.values() for r in node.responses for f in r.required_flags
    }


def _manager(profile: str, tree: DialogueTree) -> tuple[DialogueManager, SocialManager, CrewRoster]:
    social = SocialManager()
    if profile == "expert":
        for skill in social._skills.values():
            skill.level = 10
    roster = CrewRoster(get_data_loader().crew_templates)
    for crew_id in COMPANIONS:
        roster.recruit(crew_id, 4)
        roster.adjust_loyalty(crew_id, LOYALTY - 30)
    manager = DialogueManager()
    manager.set_social_manager(social)
    manager.set_crew_roster(roster)
    manager.load_flags(_required_flags(tree) if profile == "expert" else {})
    return manager, social, roster


def _tree_case(tree_id: str, tree: DialogueTree) -> Case:
    npc_id = _npc_for(tree_id)
    case = Case("dialogue", f"tree_{tree_id}", {"npc_id": npc_id, "loyalty": LOYALTY})
    for profile in ("novice", "expert"):
        for node_id, node in tree.nodes.items():
            probe, _, _ = _manager(profile, tree)
            probe.start_dialogue(tree, npc_id)
            probe._current_node_id = node_id
            available = probe.get_available_responses()
            for index, response in enumerate(available):
                manager, social, roster = _manager(profile, tree)
                manager.start_dialogue(tree, npc_id)
                manager._current_node_id = node_id
                manager.select_response(index)
                result = {
                    "available": [node.responses.index(r) for r in available],
                    "response": node.responses.index(response),
                    "next_node": manager._current_node_id if manager.is_active else None,
                    "check": list(manager._last_check_result)
                    if manager._last_check_result
                    else None,
                }
                members = roster.get_state()["members"]
                state = {
                    "flags": sorted(k for k, v in manager.get_flags().items() if v),
                    "disposition": social.get_state()["disposition"],
                    "loyalty": {cid: members[cid]["loyalty"] for cid in COMPANIONS},
                }
                case.record("select", [profile, node_id, index], result, state)
    return case


def _sorted_ambient_state(manager: AmbientDialogueManager) -> dict[str, object]:
    """``AmbientDialogueManager.to_dict()`` with hash-order collections sorted.

    ``shown_indices`` comes from a ``set[int]``. Int hashes are never salted by
    ``PYTHONHASHSEED``, so this is already stable across processes, but sorting it
    keeps the golden state readable and immune to any future change in how the set
    is built (global constraint: never write a hash-order-dependent value).
    """
    raw = manager.to_dict()
    return {
        "shown_indices": sorted(raw["shown_indices"]),
        "last_combat_day": raw["last_combat_day"],
    }


def _ambient() -> Case:
    dl = get_data_loader()
    manager = AmbientDialogueManager(dl.ambient_lines, rng=SimRng.from_key("parity_ambient"))
    loyalty = dict.fromkeys(COMPANIONS, LOYALTY)
    case = Case("dialogue", "ambient", {"loyalty": LOYALTY})
    contexts = sorted({line.context for line in dl.ambient_lines})
    for context in contexts:
        for crew_id in COMPANIONS:
            line = manager.get_line(
                context,
                crew_id,
                "nexus_prime",
                "commerce_guild",
                list(COMPANIONS),
                LOYALTY,
                "sold_cargo",
                {},
            )
            case.record("get_line", [context, crew_id], line, _sorted_ambient_state(manager))
    for _ in range(5):
        case.record(
            "get_random_idle",
            [],
            manager.get_random_idle(list(COMPANIONS), loyalty),
            _sorted_ambient_state(manager),
        )
    actions = sorted({line.action_type for line in dl.ambient_lines if line.action_type})
    for action in actions:
        action_line = manager.get_player_action_line(action, list(COMPANIONS), loyalty)
        case.record("get_player_action_line", [action], action_line, _sorted_ambient_state(manager))
    return case


def _sorted_chatter_state(manager: StationChatterManager) -> dict[str, object]:
    """``StationChatterManager.to_dict()`` with its two shown-id sets sorted.

    Both collections hold line id strings, whose hash *is* salted by
    ``PYTHONHASHSEED``: ``list(some_str_set)`` has a different order per process.
    The global constraint requires goldens never carry a hash-order-dependent
    value, so this sorts both before they reach ``Case.record``.
    """
    raw = manager.to_dict()
    return {
        "shown": {sid: sorted(ids) for sid, ids in raw["shown"].items()},
        "retired": sorted(raw["retired"]),
    }


def _chatter() -> Case:
    dl = get_data_loader()
    manager = StationChatterManager(dl.station_chatter_lines, rng=SimRng.from_key("parity_chatter"))
    case = Case("dialogue", "chatter", {})
    for system_id in dl.systems:
        for rep in (-60, 0, 70):
            for events in ([], ["embargo"]):
                lines = manager.get_chatter(system_id, rep, events, 3, {})
                case.record(
                    "get_chatter", [system_id, rep, events], lines, _sorted_chatter_state(manager)
                )
    return case


def _interjections() -> Case:
    dl = get_data_loader()
    crew_aboard = [(cid, dl.crew_templates[cid].name) for cid in COMPANIONS]
    case = Case("dialogue", "interjections", {"crew": [c for c, _ in crew_aboard]})
    for enemy_id in ("pirate_raider", "guild_dreadnought", "corsair_king"):
        seed = stable_seed("parity_interjection", enemy_id)
        fight = build_fight(
            f"interjections_{enemy_id}",
            ship_type_id="war_frigate",
            loadout=LOADOUTS[0],
            enemy_ids=(enemy_id,),
            seed=seed,
            hull=900,
        )
        resolver = CrewInterjectionResolver(list(dl.crew_interjections), crew_aboard, seed=seed)
        scratch = Case("dialogue", "scratch", {})
        for _ in range(12):
            if fight.engine.is_combat_over():
                break
            events = resolver.evaluate_round(fight.state)
            if events:
                resolver.commit(events[0])
            case.record(
                "evaluate_round",
                [enemy_id, fight.state.round_number],
                [dataclasses.asdict(e) for e in events],
                {},
            )
            play_round(fight, scratch)
        outcome = fight.state.result.value
        events = resolver.evaluate_outcome(fight.state, outcome)
        case.record(
            "evaluate_outcome", [enemy_id, outcome], [dataclasses.asdict(e) for e in events], {}
        )
    return case


def build_cases() -> list[Case]:
    """Every dialogue case."""
    dl = get_data_loader()
    dl.load_all()
    return [
        *[_tree_case(tree_id, tree) for tree_id, tree in dl.dialogue_trees.items()],
        _ambient(),
        _chatter(),
        _interjections(),
    ]
