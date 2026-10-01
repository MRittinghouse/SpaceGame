"""Dialogue goldens cover every tree node, both profiles, and the line pickers."""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import Any

from spacegame.data_loader import get_data_loader
from spacegame.models.ambient_dialogue import AmbientDialogueManager
from spacegame.models.combat import EnemyShip
from spacegame.models.crew import CrewRoster
from spacegame.models.crew_interjection import CrewInterjectionResolver, InterjectionEvent
from spacegame.models.dialogue import DialogueManager
from spacegame.models.social import SocialManager
from spacegame.models.station_chatter import StationChatterManager
from spacegame.sim_rng import SimRng
from tools.parity.driver import Case
from tools.parity.drivers import dialogue

# Neither profile can pick these: novice lacks required flags; expert's flags trip excluded ones.
UNSELECTED_RESPONSES: frozenset[tuple[str, str, int]] = frozenset(
    {
        ("merchant_delivery", "greet", 6),
        ("merchant_delivery", "greet", 8),
        ("reva_distress", "greet", 0),
        ("reva_distress", "greet", 1),
        ("reva_distress", "greet", 3),
        ("cassiel_maren_forgery", "start", 3),
        ("dead_ledger_investigation", "greet", 2),
        ("dead_ledger_investigation", "greet", 3),
    }
)


def _named() -> dict:
    return {case.name: case for case in dialogue.build_cases()}


def test_every_node_of_every_tree_is_visited() -> None:
    cases = _named()
    for tree_id, tree in get_data_loader().dialogue_trees.items():
        visited = {s["args"][1] for s in cases[f"tree_{tree_id}"].steps}
        with_responses = {nid for nid, node in tree.nodes.items() if node.responses}
        assert with_responses <= visited, tree_id


def test_every_response_is_selected_or_named() -> None:
    """Every response is selected by some step, or is named in UNSELECTED_RESPONSES."""
    cases = _named()
    missing: set[tuple[str, str, int]] = set()
    for tree_id, tree in get_data_loader().dialogue_trees.items():
        selected = {(s["args"][1], s["result"]["response"]) for s in cases[f"tree_{tree_id}"].steps}
        for node_id, node in tree.nodes.items():
            for index in range(len(node.responses)):
                if (node_id, index) not in selected:
                    missing.add((tree_id, node_id, index))
    assert missing == UNSELECTED_RESPONSES
    for tree_id, node_id, index in UNSELECTED_RESPONSES:
        response = get_data_loader().dialogue_trees[tree_id].nodes[node_id].responses[index]
        assert response.set_flag is None
        assert response.skill_check is None
        assert response.disposition_change == 0
        assert not response.faction_reputation_changes
        assert not response.crew_loyalty_changes


def test_skill_checks_pass_and_fail() -> None:
    checks = [
        s["result"]["check"]
        for name, c in _named().items()
        if name.startswith("tree_")
        for s in c.steps
        if s["result"]["check"] is not None
    ]
    assert any(c[0] for c in checks) and any(not c[0] for c in checks)


def test_line_pickers_and_interjections_are_recorded() -> None:
    cases = _named()
    assert any(s["result"] for s in cases["ambient"].steps)
    assert any(s["result"] for s in cases["chatter"].steps)
    assert any(s["result"] for s in cases["interjections"].steps)


def test_cases_are_stable() -> None:
    assert [c.to_json("x") for c in dialogue.build_cases()] == [
        c.to_json("x") for c in dialogue.build_cases()
    ]


# === Replay from setup ===
# A Python stand-in for the Godot adapter: every case is rebuilt from its setup, its step
# args, and synced data, with exactly one model call per recorded step. It never calls the
# driver's builders or reads its constants, so a case whose inputs live only in driver
# code fails here.


def _replay_tree(case: Case) -> Case:
    dl = get_data_loader()
    setup: dict[str, Any] = case.setup
    tree = dl.dialogue_trees[setup["tree_id"]]
    replay = Case("dialogue", case.name, setup)
    for step in case.steps:
        profile, node_id, index = step["args"]
        profile_setup = setup["profiles"][profile]
        social = SocialManager()
        social.load_state(profile_setup["social"])
        roster = CrewRoster(dl.crew_templates)
        for entry in setup["crew"]:
            roster.recruit(entry["crew_id"], setup["crew_slots"])
            roster.adjust_loyalty(entry["crew_id"], entry["loyalty_delta"])
        manager = DialogueManager()
        manager.set_social_manager(social)
        manager.set_crew_roster(roster)
        manager.load_flags(profile_setup["flags"])
        manager.start_dialogue(tree, setup["npc_id"])
        manager._current_node_id = node_id
        node = tree.nodes[node_id]
        available = manager.get_available_responses()
        response = available[index]
        manager.select_response(index)
        check = manager.get_last_check_result()
        members = roster.get_state()["members"]
        result = {
            "available": [node.responses.index(r) for r in available],
            "response": node.responses.index(response),
            "next_node": manager._current_node_id if manager.is_active else None,
            "check": list(check) if check else None,
        }
        state = {
            "flags": sorted(k for k, v in manager.get_flags().items() if v),
            "disposition": social.get_state()["disposition"],
            "loyalty": {e["crew_id"]: members[e["crew_id"]]["loyalty"] for e in setup["crew"]},
        }
        replay.record("select", step["args"], result, state)
    return replay


def _replay_ambient(case: Case) -> Case:
    dl = get_data_loader()
    s: dict[str, Any] = case.setup
    manager = AmbientDialogueManager(dl.ambient_lines, rng=SimRng.from_key(*s["rng_key"]))
    replay = Case("dialogue", case.name, s)
    for step in case.steps:
        call, args = step["call"], step["args"]
        result: object
        if call == "get_line":
            result = manager.get_line(
                args[0],
                args[1],
                s["system_id"],
                s["faction_id"],
                list(s["recruited_ids"]),
                s["loyalty"],
                s["action_type"],
                dict(s["player_flags"]),
            )
        elif call == "get_random_idle":
            result = manager.get_random_idle(list(s["recruited_ids"]), dict(s["loyalty_map"]))
        else:
            result = manager.get_player_action_line(
                args[0], list(s["recruited_ids"]), dict(s["loyalty_map"])
            )
        raw = manager.to_dict()
        state = {
            "shown_indices": sorted(raw["shown_indices"]),
            "last_combat_day": raw["last_combat_day"],
        }
        replay.record(call, args, result, state)
    return replay


def _replay_chatter(case: Case) -> Case:
    dl = get_data_loader()
    s: dict[str, Any] = case.setup
    manager = StationChatterManager(dl.station_chatter_lines, rng=SimRng.from_key(*s["rng_key"]))
    replay = Case("dialogue", case.name, s)
    for step in case.steps:
        system_id, rep, events = step["args"]
        lines = manager.get_chatter(system_id, rep, events, s["count"], dict(s["player_flags"]))
        raw = manager.to_dict()
        state = {
            "shown": {sid: sorted(ids) for sid, ids in raw["shown"].items()},
            "retired": sorted(raw["retired"]),
        }
        replay.record("get_chatter", step["args"], lines, state)
    return replay


def _combat_state(inputs: dict[str, Any]) -> Any:
    """A stand-in CombatState holding only what the step args carry.

    A SimpleNamespace, not a CombatState: if the resolver ever reads a field the args do
    not record, this raises AttributeError and the replay fails.
    """
    dl = get_data_loader()
    enemies = []
    for entry in inputs["enemies"]:
        enemy = EnemyShip.from_template(dl.enemy_templates[entry["template_id"]])
        enemy.current_hull = entry["current_hull"]
        enemy.is_fled = entry["is_fled"]
        enemies.append(enemy)
    return SimpleNamespace(
        round_number=inputs["round_number"],
        player=SimpleNamespace(**inputs["player"]),
        enemies=enemies,
        surviving_enemies=[e for e in enemies if e.is_alive and not e.is_fled],
    )


def _replay_interjections(case: Case) -> Case:
    dl = get_data_loader()
    s: dict[str, Any] = case.setup
    crew_aboard = [(crew_id, name) for crew_id, name in s["crew_aboard"]]
    resolvers: dict[str, CrewInterjectionResolver] = {}
    offered: dict[str, list[InterjectionEvent]] = {}
    replay = Case("dialogue", case.name, s)
    for step in case.steps:
        call, args = step["call"], step["args"]
        label = args[0]
        if label not in resolvers:
            resolvers[label] = CrewInterjectionResolver(
                list(dl.crew_interjections), crew_aboard, seed=s["seeds"][label]
            )
        resolver = resolvers[label]
        result: object = None
        if call == "evaluate_round":
            offered[label] = resolver.evaluate_round(_combat_state(args[1]))
            result = [dataclasses.asdict(e) for e in offered[label]]
        elif call == "evaluate_outcome":
            # evaluate_outcome never reads the combat state, so the replay passes none.
            offered[label] = resolver.evaluate_outcome(None, args[1])  # type: ignore[arg-type]
            result = [dataclasses.asdict(e) for e in offered[label]]
        else:
            event = next(e for e in offered[label] if [e.crew_id, e.trigger] == args[1:])
            resolver.commit(event)
        state = {"fired": sorted([crew_id, trigger] for crew_id, trigger in resolver.fired)}
        replay.record(call, args, result, state)
    return replay


def test_cases_replay_from_setup() -> None:
    for name, case in _named().items():
        if name.startswith("tree_"):
            replay = _replay_tree(case)
        elif name == "ambient":
            replay = _replay_ambient(case)
        elif name == "chatter":
            replay = _replay_chatter(case)
        else:
            assert name == "interjections", name
            replay = _replay_interjections(case)
        assert replay.to_json("x") == case.to_json("x"), name


def test_interjections_cover_every_trigger_and_outcome() -> None:
    steps = _named()["interjections"].steps
    triggers = {e["trigger"] for s in steps if s["call"] == "evaluate_round" for e in s["result"]}
    assert triggers == {"first_turn", "player_low_hp", "enemy_low_hp", "enemy_type_match"}
    outcomes = [s for s in steps if s["call"] == "evaluate_outcome"]
    assert {s["args"][1] for s in outcomes} == {"victory", "defeat"}
    assert all(s["result"] for s in outcomes)


def test_tree_npc_follows_dialogue_states() -> None:
    """A tree opened through an NPC's dialogue_states runs as that NPC, as in the game."""
    cases = _named()
    for npc_id, npc in get_data_loader().npcs.items():
        for tree_id in [npc.dialogue_id, *(state.dialogue_id for state in npc.dialogue_states)]:
            assert cases[f"tree_{tree_id}"].setup["npc_id"] == npc_id, tree_id
