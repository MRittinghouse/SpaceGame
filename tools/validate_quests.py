#!/usr/bin/env python3
"""Quest data validation CLI tool.

Loads all game data and runs cross-reference validation checks.
Outputs a human-readable report of errors and warnings.

Usage:
    python tools/validate_quests.py

Exit codes:
    0 — All checks passed
    1 — Validation errors found
"""

import json
import sys
from collections import deque
from pathlib import Path

# Ensure project root is on the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from spacegame.data_loader import DataLoader  # noqa: E402
from spacegame.models.mission import ObjectiveType  # noqa: E402


def _collect_settable_flags(loader: DataLoader) -> set[str]:
    """Collect all flags that can be set by dialogues, rewards, encounters, or engine."""
    flags: set[str] = set()

    for tree in loader.dialogue_trees.values():
        for node in tree.nodes.values():
            for response in node.responses:
                if response.set_flag:
                    flags.add(response.set_flag)
                if response.skill_check:
                    if response.skill_check.set_flag_on_success:
                        flags.add(response.skill_check.set_flag_on_success)
                    if response.skill_check.set_flag_on_failure:
                        flags.add(response.skill_check.set_flag_on_failure)

    for mission in loader.missions:
        for reward in mission.rewards:
            if reward.reward_type == "set_flag" and reward.target_id:
                flags.add(reward.target_id)

    for defn in loader.encounter_definitions:
        for choice in defn.choices:
            for reward in choice.outcome.rewards:
                if reward.reward_type == "set_flag" and reward.target_id:
                    flags.add(reward.target_id)

    for npc_id in loader.npcs:
        flags.add(f"talked_to_{npc_id}")

    for npc in loader.npcs.values():
        gate = getattr(npc, "auto_trigger_gate_flag", None)
        if gate:
            flags.add(gate)

    for mission in loader.missions:
        if mission.ground_mission_complete_flag:
            flags.add(mission.ground_mission_complete_flag)

    return flags


def validate(loader: DataLoader) -> tuple[list[str], list[str]]:
    """Run all validation checks.

    Returns:
        Tuple of (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    commodity_ids = set(loader.commodities.keys())
    system_ids = set(loader.systems.keys())
    npc_ids = set(loader.npcs.keys())
    faction_ids = set(loader.factions.keys())
    tree_ids = set(loader.dialogue_trees.keys())
    mission_ids = {m.id for m in loader.missions}

    # --- Mission cross-references ---
    for mission in loader.missions:
        for obj in mission.objectives:
            if obj.type == ObjectiveType.COLLECT_CARGO and obj.target_id not in commodity_ids:
                errors.append(
                    f"Mission '{mission.id}': collect_cargo target "
                    f"'{obj.target_id}' not in commodities"
                )
            if obj.type == ObjectiveType.REACH_SYSTEM and obj.target_id not in system_ids:
                errors.append(
                    f"Mission '{mission.id}': reach_system target "
                    f"'{obj.target_id}' not in systems"
                )
            if obj.type == ObjectiveType.TALK_TO_NPC and obj.target_id not in npc_ids:
                errors.append(
                    f"Mission '{mission.id}': talk_to_npc target "
                    f"'{obj.target_id}' not in NPCs"
                )
        for cargo in mission.on_accept_cargo:
            if cargo.commodity_id not in commodity_ids:
                errors.append(
                    f"Mission '{mission.id}': on_accept_cargo "
                    f"'{cargo.commodity_id}' not in commodities"
                )
        for prereq in mission.prerequisites:
            if prereq not in mission_ids:
                errors.append(
                    f"Mission '{mission.id}': prerequisite '{prereq}' not in missions"
                )
        if mission.available_after and mission.available_after not in mission_ids:
            errors.append(
                f"Mission '{mission.id}': available_after "
                f"'{mission.available_after}' not in missions"
            )
        if mission.available_before and mission.available_before not in mission_ids:
            errors.append(
                f"Mission '{mission.id}': available_before "
                f"'{mission.available_before}' not in missions"
            )
        for reward in mission.rewards:
            if reward.reward_type == "modify_reputation" and reward.target_id not in faction_ids:
                errors.append(
                    f"Mission '{mission.id}': modify_reputation target "
                    f"'{reward.target_id}' not in factions"
                )

    # --- NPC cross-references ---
    for npc in loader.npcs.values():
        if npc.dialogue_id and npc.dialogue_id not in tree_ids:
            errors.append(
                f"NPC '{npc.id}' ({npc.name}): dialogue_id "
                f"'{npc.dialogue_id}' not in dialogue trees"
            )
        if npc.home_system_id and npc.home_system_id not in system_ids:
            errors.append(
                f"NPC '{npc.id}' ({npc.name}): home_system_id "
                f"'{npc.home_system_id}' not in systems"
            )
        if npc.faction_id and npc.faction_id not in faction_ids:
            errors.append(
                f"NPC '{npc.id}' ({npc.name}): faction_id "
                f"'{npc.faction_id}' not in factions"
            )

    # --- Dialogue node references ---
    for tree in loader.dialogue_trees.values():
        if tree.start_node_id not in tree.nodes:
            errors.append(
                f"Dialogue '{tree.id}': start_node_id "
                f"'{tree.start_node_id}' not in nodes"
            )
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.next_node_id and resp.next_node_id not in tree.nodes:
                    errors.append(
                        f"Dialogue '{tree.id}' node '{node.id}': "
                        f"next_node_id '{resp.next_node_id}' not in nodes"
                    )

    # --- Dialogue orphan nodes ---
    for tree in loader.dialogue_trees.values():
        visited: set[str] = set()
        queue: deque[str] = deque()
        if tree.start_node_id in tree.nodes:
            queue.append(tree.start_node_id)
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            node = tree.nodes.get(nid)
            if not node:
                continue
            for resp in node.responses:
                if resp.next_node_id and resp.next_node_id not in visited:
                    queue.append(resp.next_node_id)
                if resp.skill_check:
                    for target in [resp.skill_check.success_node_id, resp.skill_check.failure_node_id]:
                        if target and target not in visited:
                            queue.append(target)
        orphans = set(tree.nodes.keys()) - visited
        if orphans:
            warnings.append(
                f"Dialogue '{tree.id}': unreachable nodes: {sorted(orphans)}"
            )

    # --- Node-level set_flag (silently ignored by parser) ---
    for filename in ["dialogues.json", "crew_quest_dialogues.json"]:
        filepath = project_root / "data" / "dialogue" / filename
        if not filepath.exists():
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for tree_data in raw.get("dialogues", []):
            for node in tree_data.get("nodes", []):
                if "set_flag" in node:
                    errors.append(
                        f"Dialogue '{tree_data['id']}' node '{node['id']}': "
                        f"node-level set_flag='{node['set_flag']}' is silently "
                        f"ignored — move to response level"
                    )

    # --- Flag reachability ---
    settable = _collect_settable_flags(loader)
    engine_flags = {
        "iron_ore_delivered", "iron_delivery_failed", "broker_ore_sold",
        "talked_to_officer_larsen", "escape_combat_survived",
    }
    for mission in loader.missions:
        for flag in mission.required_flags:
            if flag in settable or flag in engine_flags:
                continue
            if flag.startswith("crew_loyalty_"):
                continue
            warnings.append(
                f"Mission '{mission.id}': required_flag '{flag}' "
                f"not settable by any dialogue, reward, or encounter"
            )

    # --- Encounter-triggered quests ---
    encounter_flags: set[str] = set()
    for defn in loader.encounter_definitions:
        for choice in defn.choices:
            for reward in choice.outcome.rewards:
                if reward.reward_type == "set_flag" and reward.target_id:
                    encounter_flags.add(reward.target_id)
    for mission in loader.missions:
        if mission.discovery_method != "encounter":
            continue
        flag_objs = [o for o in mission.objectives if o.type == ObjectiveType.HAS_FLAG]
        if flag_objs and flag_objs[0].target_id not in encounter_flags:
            errors.append(
                f"Mission '{mission.id}' (discovery_method=encounter): "
                f"flag '{flag_objs[0].target_id}' not set by any encounter"
            )

    return errors, warnings


def main() -> int:
    """Run validation and print report."""
    print("Loading game data...")
    loader = DataLoader(data_dir=project_root / "data")
    loader.load_all()

    print("Running validation...\n")
    errs, warns = validate(loader)

    if warns:
        print(f"WARNINGS ({len(warns)}):")
        for w in warns:
            print(f"  [WARN] {w}")
        print()

    if errs:
        print(f"ERRORS ({len(errs)}):")
        for e in errs:
            print(f"  [ERR]  {e}")
        print()
        print(f"RESULT: {len(errs)} error(s), {len(warns)} warning(s)")
        return 1

    print(f"RESULT: All checks passed ({len(warns)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
