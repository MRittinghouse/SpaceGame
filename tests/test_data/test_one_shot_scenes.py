"""One-shot scenes and the keep rule: the content rules of the polish design's 6.1.

Rules 1 to 4, 8 and 10 live here (bug bash BB-38, BB-67, BB-68, BB-69, BB-71, BB-72).
Rules 5 to 7 (no check gate, no self-looping check, no producer cycle) are plan A1's, in
``test_content_contracts.py``. Rule 9 (a return tree pays once) is
``test_a_return_pays_once``, with the return trees of the writing session (plan W3a-S).
"""

from __future__ import annotations

import functools

import pytest

from spacegame.constants.flags import talked_to_npc
from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import NPC, DialogueTree
from spacegame.models.mission import Mission, MissionManager, ObjectiveType
from spacegame.models.npc_availability import is_listed, npc_tree_ids, settable_flags
from tests.test_data.test_content_contracts import _dependents, _is_own_cycle, _producers

# Flag pairs no reply may set one side of once the other is set (rule 3).
EXCLUSIVE_PAIRS = (("accepted_drifter_deal", "declined_drifter_deal"),)
# The most (node, flags) states one walk visits; the content stays far below it.
WALK_LIMIT = 100_000
DEX_RECORDS = ("dex_halloran", "dex_tunnel_contact", "dex_final_lead")


def _loader() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _one_shot(dl: DataLoader) -> list[NPC]:
    return [npc for npc in dl.npcs.values() if npc.auto_trigger_gate_flag]


def _exits(tree: DialogueTree, flags: frozenset[str], *, passes: bool) -> list[frozenset[str]]:
    """The flags each route through a tree sets, from its start to an end.

    A route ends at a reply with no next node, at a node none of whose replies its flags
    allow, or at a missing node. A check takes both branches, or only its failure branch
    when ``passes`` is False.
    """
    exits: list[frozenset[str]] = []
    pending = [(tree.start_node_id, flags, frozenset[str]())]
    seen: set[tuple[str, frozenset[str]]] = set()
    while pending:
        assert len(seen) < WALK_LIMIT, tree.id
        node_id, held, gained = pending.pop()
        if (node_id, held) in seen:
            continue
        seen.add((node_id, held))
        node = tree.nodes.get(node_id)
        replies = (
            []
            if node is None
            else [
                r
                for r in node.responses
                if all(f in held for f in r.required_flags)
                and not any(f in held for f in r.excluded_flags)
            ]
        )
        if not replies:
            exits.append(gained)
            continue
        for reply in replies:
            own = {reply.set_flag} if reply.set_flag else set()
            check = reply.skill_check
            if check is None:
                branches = [(reply.next_node_id, own)]
            else:
                fail = {check.set_flag_on_failure} if check.set_flag_on_failure else set()
                branches = [(check.failure_node_id, own | fail)]
                if passes:
                    win = {check.set_flag_on_success} if check.set_flag_on_success else set()
                    branches.append((check.success_node_id, own | win))
            for next_id, new in branches:
                if next_id is None:
                    exits.append(gained | new)
                else:
                    pending.append((next_id, held | new, gained | new))
    return exits


def _waits_on(
    dl: DataLoader,
    npc: NPC,
    real: dict[str, set[str]],
    dependents: dict[str, set[str]],
) -> list[tuple[Mission, str]]:
    """(mission, flag): the mission's has_flag objective waits on a flag only this NPC sets.

    A producer counts unless it is the mission's own reward or the reward of a mission
    that needs it (A1's ``_is_own_cycle``).
    """
    trees = set(npc_tree_ids(npc))
    found: list[tuple[Mission, str]] = []
    for mission in dl.missions:
        for objective in mission.objectives:
            if objective.type != ObjectiveType.HAS_FLAG:
                continue
            usable = {
                s
                for s in real.get(objective.target_id, set())
                if not _is_own_cycle(s, mission.id, dependents)
            }
            if usable and all(
                s.startswith("dialogue:") and s.split(":")[1] in trees for s in usable
            ):
                found.append((mission, objective.target_id))
    return found


@functools.cache
def _kept_exits() -> tuple[tuple[NPC, Mission, str, frozenset[str]], ...]:
    """Every exit of a one-shot scene that leaves an awaited flag unset, with its flags.

    The flags hold the conversation's own talked_to flag, which the game sets when a
    dialogue ends (``Game._route_from_dialogue``), so a test resolves the NPC's state as the
    game would. Cached: A1's producer index scans the whole code base, so it is built once.
    """
    dl = _loader()
    real, dependents = _producers(dl), _dependents(dl)
    kept: list[tuple[NPC, Mission, str, frozenset[str]]] = []
    for npc in _one_shot(dl):
        opening = frozenset([*npc.auto_trigger_prerequisites, npc.auto_trigger_gate_flag])
        exits = set(_exits(dl.dialogue_trees[npc.dialogue_id], opening, passes=True))
        for mission, flag in _waits_on(dl, npc, real, dependents):
            for gained in exits:
                if flag not in gained:
                    kept.append((npc, mission, flag, opening | gained | {talked_to_npc(npc.id)}))
    return tuple(kept)


@pytest.mark.timeout(300)
def test_the_kept_npcs_are_elena_glyn_oren_and_tomas() -> None:
    """Elena's walk-away, Glyn's decline, Oren's walk-away and Tomas's deferral are kept."""
    names = {npc.id for npc, _mission, _flag, _flags in _kept_exits()}
    assert names == {"dex_halloran", "elena_reeves", "oren_tak", "tomas_drifter"}


@pytest.mark.timeout(300)
def test_an_exit_that_strands_a_mission_keeps_its_npc() -> None:
    """Rule 1: the keep rule lists the NPC after every exit that leaves its flag unset."""
    dl = _loader()
    dropped: list[str] = []
    for npc, mission, _flag, flags in _kept_exits():
        manager = MissionManager(dl.missions)
        status = "active" if mission.auto_accept else "available"
        manager.load_state({"status": {mission.id: status}})
        held = dict.fromkeys(flags, True)
        settable = settable_flags(npc, dl.dialogue_trees)
        if not is_listed(npc, npc.home_system_id, held, manager, set(), settable):
            dropped.append(f"{npc.id}:{mission.id}:{sorted(flags)}")
    assert not dropped


@pytest.mark.timeout(300)
def test_a_kept_npc_has_a_way_back() -> None:
    """Rule 2: after every kept exit the NPC opens a return tree, and a route through it
    with every check failing sets the awaited flag."""
    dl = _loader()
    replaying: set[str] = set()
    gated: set[str] = set()
    for npc, _mission, flag, flags in _kept_exits():
        tree_id = npc.get_active_dialogue_id(dict.fromkeys(flags, True))
        if tree_id == npc.dialogue_id:
            replaying.add(npc.id)
        routes = _exits(dl.dialogue_trees[tree_id], flags, passes=False)
        if not any(flag in route for route in routes):
            gated.add(npc.id)
    assert replaying == set(), sorted(replaying)
    assert gated == set(), sorted(gated)


def _exit_paths(tree: DialogueTree, node_id: str, path: tuple = ()) -> list[tuple]:
    """Every reply path from a node to an exit, taking both branches of a check."""
    node = tree.nodes.get(node_id)
    if node is None:
        return [path]
    visited = {step.next_node_id for step in path}
    paths: list[tuple] = []
    for reply in node.responses:
        step = (*path, reply)
        if reply.skill_check is not None:
            for branch in (reply.skill_check.success_node_id, reply.skill_check.failure_node_id):
                paths += _exit_paths(tree, branch, step)
        elif reply.next_node_id is None:
            paths.append(step)
        elif reply.next_node_id not in visited:
            paths += _exit_paths(tree, reply.next_node_id, step)
    return paths


def test_a_return_pays_once() -> None:
    """Rule 9: in a return tree every check, pass or fail, leads only to exits that set the
    awaited flag, and every disposition or standing change sits on a reply that sets it."""
    dl = _loader()
    returns = 0
    for npc in dl.npcs.values():
        for state in npc.dialogue_states:
            if talked_to_npc(npc.id) not in state.required_flags:
                continue
            returns += 1
            (awaited,) = state.excluded_flags
            tree = dl.dialogue_trees[state.dialogue_id]
            for node in tree.nodes.values():
                for reply in node.responses:
                    if reply.disposition_change or reply.faction_reputation_changes:
                        assert reply.set_flag == awaited, (tree.id, node.id, reply.text)
                    check = reply.skill_check
                    if check is None:
                        continue
                    for branch in (check.success_node_id, check.failure_node_id):
                        for path in _exit_paths(tree, branch):
                            assert any(s.set_flag == awaited for s in path), (tree.id, branch)
    assert returns == 4


def test_no_reply_sets_one_side_of_an_exclusive_pair_once_the_other_is_set() -> None:
    """Rule 3: a reopened scene cannot set both deal flags (Tomas's sub-node replies)."""
    pairs = EXCLUSIVE_PAIRS + tuple((b, a) for a, b in EXCLUSIVE_PAIRS)
    open_sides: list[str] = []
    for tree in _loader().dialogue_trees.values():
        for node in tree.nodes.values():
            for index, reply in enumerate(node.responses):
                for one, other in pairs:
                    if reply.set_flag == one and other not in reply.excluded_flags:
                        open_sides.append(f"{tree.id}:{node.id}:{index}")
    assert not open_sides


def test_a_one_shot_scene_opens_its_first_tree() -> None:
    """Rule 4: with only its prerequisites and gate set, the base tree opens."""
    for npc in _one_shot(_loader()):
        flags = dict.fromkeys([*npc.auto_trigger_prerequisites, npc.auto_trigger_gate_flag], True)
        assert npc.get_active_dialogue_id(flags) == npc.dialogue_id, npc.id


def test_no_one_shot_npc_carries_a_hide_flag() -> None:
    """Rule 8: no hide flag can be set while a mission waits on that NPC alone.

    No one-shot NPC has a hide flag, so the keep rule never meets one. A writer who gives
    one a hide flag extends this test with the reachability check first.
    """
    assert [npc.id for npc in _one_shot(_loader()) if npc.hide_after_flag] == []


def test_one_dex_at_a_time() -> None:
    """Rule 10: three records share Dex's name at Nexus Prime; one is listed at a time."""
    dl = _loader()
    beats: list[tuple[set[str], dict[str, str], list[str]]] = [
        ({"cargo_lost_complete"}, {"cargo_lost": "completed"}, ["dex_halloran"]),
        ({"met_dex_halloran"}, {"whispers_at_the_bar": "active"}, ["dex_halloran"]),
        ({"dex_favor_accepted"}, {"whispers_at_the_bar": "completed"}, []),
        ({"guild_hardware_discovered"}, {}, ["dex_tunnel_contact"]),
        ({"dex_tunnel_briefing_heard"}, {}, []),
        (
            {"singularity_weapon_discovered", "convergence_data_verified"},
            {"the_ledger": "active"},
            ["dex_final_lead"],
        ),
        ({"assembly_location_known"}, {"the_ledger": "completed"}, []),
    ]
    flags: dict[str, bool] = {}
    statuses: dict[str, str] = {}
    for gained, moved, expected in beats:
        flags.update(dict.fromkeys(gained, True))
        statuses.update(moved)
        manager = MissionManager(dl.missions)
        manager.load_state({"status": dict(statuses)})
        listed = [
            npc_id
            for npc_id in DEX_RECORDS
            if is_listed(
                dl.npcs[npc_id],
                "nexus_prime",
                flags,
                manager,
                set(),
                settable_flags(dl.npcs[npc_id], dl.dialogue_trees),
            )
        ]
        assert listed == expected, sorted(gained)


def test_reva_waits_for_cargo_lost_and_dex_for_its_end() -> None:
    """BB-72: a captain who never saw the distress call meets neither early."""
    dl = _loader()
    reva, dex = dl.npcs["reva_sato"], dl.npcs["dex_halloran"]
    none = frozenset[str]()
    assert not is_listed(reva, "nova_research", {}, None, set(), none)
    assert is_listed(reva, "nova_research", {"cargo_lost_accepted": True}, None, set(), none)
    assert not is_listed(dex, "nexus_prime", {"cargo_lost_resolved": True}, None, set(), none)
    assert is_listed(dex, "nexus_prime", {"cargo_lost_complete": True}, None, set(), none)


def test_hanna_waits_for_elenas_lesson() -> None:
    """Design 6.3: a walk-away from Elena no longer plays Hanna's errand early."""
    hanna = _loader().npcs["hanna_voss"]
    assert hanna.auto_trigger_prerequisites == ["elena_gave_trading_tips"]
