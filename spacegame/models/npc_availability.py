"""Who a captain can talk to at a station (bug bash BB-38, BB-67, BB-68, BB-71, BB-72).

An NPC is listed at the ship's system when, in order: it lives there; it is not a crew
member aboard (a companion talks through crew talk); every flag in its
``auto_trigger_prerequisites`` is set; its ``hide_after_flag`` is empty or unset; and its
one-shot scene has not played (its ``auto_trigger_gate_flag`` is empty or unset) or an
open mission still needs it. The last clause is the keep rule: a one-shot NPC whose scene
played stays listed while an available or active mission waits on a flag one of its
trees can set, or an active mission's unmet talk objective names it. A hide flag always
wins, so the keep never brings back someone the story sent away.

A kept NPC opens the tree its state machine picks; each kept NPC's first state is its return
scene (polish design 6), so a second visit never replays the first. The iron job marks only
the NPCs who can close it (polish design 6.1). The Godot port lists one clause more: the
twelve Act II v1 NPCs are never listed there (deviation D-21). The station hub's Talk list,
the cantina's list and its quest marker, and the ``dialogue/npcs_here`` golden read this.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from typing import TYPE_CHECKING, Optional

from spacegame.models.flag_producers import tree_flags
from spacegame.models.iron_consignment import MISSION as IRON_MISSION
from spacegame.models.iron_consignment import closers as iron_closers
from spacegame.models.mission import MissionStatus, ObjectiveType

if TYPE_CHECKING:
    from spacegame.models.dialogue import NPC, DialogueTree
    from spacegame.models.mission import MissionManager


def npc_tree_ids(npc: "NPC") -> list[str]:
    """The NPC's base tree id, then each dialogue state's tree id, in content order."""
    return [npc.dialogue_id, *(state.dialogue_id for state in npc.dialogue_states)]


def settable_flags(npc: "NPC", trees: Mapping[str, "DialogueTree"]) -> frozenset[str]:
    """Every flag one of the NPC's trees can set: the keep rule's index.

    Args:
        npc: The NPC.
        trees: Every dialogue tree by id.

    Returns:
        The flags.
    """
    flags: set[str] = set()
    for tree_id in npc_tree_ids(npc):
        tree = trees.get(tree_id)
        if tree is not None:
            flags |= tree_flags(tree)
    return frozenset(flags)


def settable_index(
    npcs: Iterable["NPC"], trees: Mapping[str, "DialogueTree"]
) -> dict[str, frozenset[str]]:
    """``settable_flags`` for every NPC, by id."""
    return {npc.id: settable_flags(npc, trees) for npc in npcs}


def needed_by(
    npc_id: str,
    settable: Collection[str],
    manager: Optional["MissionManager"],
    flags: Mapping[str, bool],
) -> str:
    """The open mission this person can move, or "" for none.

    The first mission in content order that is available or active with an unset has_flag
    objective one of the NPC's trees can set, or active with an unmet talk objective that
    names the NPC; the iron job instead names the NPCs who can close it in its stored state
    (``iron_consignment.closers``). It drives the keep rule and the cantina's quest marker.

    Args:
        npc_id: The NPC.
        settable: The flags the NPC's trees can set (``settable_flags``).
        manager: The mission manager, or None.
        flags: The player's dialogue flags.

    Returns:
        The mission id, or "".
    """
    if manager is None:
        return ""
    for mission in manager.open_missions():
        # Polish design 6.1: the iron job is marked only on the NPCs who can close it in its
        # stored state, not on everyone whose tree could set its hand-over flag
        if mission.id == IRON_MISSION:
            if npc_id in iron_closers(flags):
                return mission.id
            continue
        active = manager.get_status(mission.id) == MissionStatus.ACTIVE
        progress = manager.get_objective_progress(mission.id)
        for index, objective in enumerate(mission.objectives):
            if objective.type == ObjectiveType.HAS_FLAG:
                if objective.target_id in settable and not flags.get(objective.target_id, False):
                    return mission.id
            elif objective.type == ObjectiveType.TALK_TO_NPC and active:
                met = index < len(progress) and progress[index]
                if objective.target_id == npc_id and not met:
                    return mission.id
    return ""


def is_listed(
    npc: "NPC",
    system_id: str,
    flags: Mapping[str, bool],
    manager: Optional["MissionManager"],
    recruited_ids: Collection[str],
    settable: Collection[str],
) -> bool:
    """Whether the NPC is in the Talk list at this system.

    Args:
        npc: The NPC.
        system_id: The ship's system.
        flags: The player's dialogue flags.
        manager: The mission manager, or None (then nothing keeps a played scene).
        recruited_ids: The crew aboard, by template id.
        settable: The flags the NPC's trees can set.

    Returns:
        Whether the NPC is listed.
    """
    if npc.home_system_id != system_id or npc.id in recruited_ids:
        return False
    if not all(flags.get(f, False) for f in npc.auto_trigger_prerequisites):
        return False
    if npc.hide_after_flag and flags.get(npc.hide_after_flag, False):
        return False
    gate = npc.auto_trigger_gate_flag
    if gate and flags.get(gate, False):
        return needed_by(npc.id, settable, manager, flags) != ""
    return True


def npcs_here(
    npcs: Iterable["NPC"],
    system_id: str,
    flags: Mapping[str, bool],
    manager: Optional["MissionManager"],
    recruited_ids: Collection[str],
    index: Mapping[str, Collection[str]],
) -> list[tuple[str, str]]:
    """Every NPC listed at this system, with the mission each can move, in NPC order.

    Args:
        npcs: Every NPC, in content order.
        system_id: The ship's system.
        flags: The player's dialogue flags.
        manager: The mission manager, or None.
        recruited_ids: The crew aboard, by template id.
        index: ``settable_index`` for the NPCs.

    Returns:
        (npc id, ``needed_by``) pairs.
    """
    listed: list[tuple[str, str]] = []
    for npc in npcs:
        settable = index.get(npc.id, frozenset())
        if is_listed(npc, system_id, flags, manager, recruited_ids, settable):
            listed.append((npc.id, needed_by(npc.id, settable, manager, flags)))
    return listed
