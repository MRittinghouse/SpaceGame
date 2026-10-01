"""The story flags content sets outside a mission's own rewards (BB-19).

The side-mission auto-resolve sets a has_flag objective's flag only when nothing else in
the content can set it; ``MissionManager`` adds the flags missions produce themselves
(forced-encounter trigger flags and other missions' set_flag rewards).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.dialogue import NPC, DialogueTree
    from spacegame.models.encounter import EncounterDefinition, EncounterOutcome


def _outcome_flags(outcome: Optional["EncounterOutcome"]) -> set[str]:
    if outcome is None:
        return set()
    return {
        reward.target_id
        for reward in outcome.rewards
        if reward.reward_type == "set_flag" and reward.target_id
    }


def tree_flags(tree: "DialogueTree") -> frozenset[str]:
    """Every flag one dialogue tree can set: replies' set_flags and their checks' flags.

    The Talk list's keep rule asks which flags an NPC's trees can set (bug bash BB-38).

    Args:
        tree: A dialogue tree.

    Returns:
        The flags.
    """
    flags: set[str] = set()
    for node in tree.nodes.values():
        for response in node.responses:
            if response.set_flag:
                flags.add(response.set_flag)
            check = response.skill_check
            if check is not None:
                flags |= {f for f in (check.set_flag_on_success, check.set_flag_on_failure) if f}
    return frozenset(flags)


def content_flag_producers(
    dialogue_trees: Iterable["DialogueTree"],
    encounter_definitions: Iterable["EncounterDefinition"],
    npcs: Iterable["NPC"],
) -> frozenset[str]:
    """Every flag a dialogue, an encounter, or an NPC's auto-trigger sets.

    A ground mission's completion flag is not a producer here: the ground system sets it
    through code, and the Godot port has no ground system yet, so the auto-resolve keeps
    setting it (BB-43).

    Args:
        dialogue_trees: Every dialogue tree.
        encounter_definitions: Every encounter definition.
        npcs: Every NPC.

    Returns:
        The flags those sources can set.
    """
    flags: set[str] = set()
    for tree in dialogue_trees:
        flags |= tree_flags(tree)
    for definition in encounter_definitions:
        for choice in definition.choices:
            flags |= _outcome_flags(choice.outcome) | _outcome_flags(choice.failure_outcome)
            encounter_check = choice.skill_check
            if encounter_check is not None:
                flags |= {
                    f
                    for f in (
                        encounter_check.set_flag_on_success,
                        encounter_check.set_flag_on_failure,
                    )
                    if f
                }
    for npc in npcs:
        if npc.auto_trigger_gate_flag:
            flags.add(npc.auto_trigger_gate_flag)
    return frozenset(flags)
