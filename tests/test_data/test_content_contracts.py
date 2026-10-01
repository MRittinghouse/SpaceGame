"""Cross-file content contracts the post-SP3 bug bash found broken (plan A1).

Each check walks the loaded content and returns the ids that break it. Its PENDING_*
set names the breaks a later task of plan A1 fixes, or, for the check gate, the later
plan that takes BB-69. A test fails on any break outside the set and on any listed break
that no longer happens, so each set only shrinks as its fix lands and cannot hide a new
break.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import DialogueTree
from spacegame.models.mission import ObjectiveType
from tests.test_data.test_dialogue_integrity import _collect_all_flag_uses

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# BB-17: a mission whose required flags hold this flag waits for SP10. Nothing sets it.
HOLD_BACK_FLAG = "held_back_until_sp10"
# BB-15: every mission's accept cargo must fit the starting ship's hold.
STARTING_SHIP_TYPE = "shuttle"
# BB-15: the Nexus Prime jobs a new captain can hold together on day one, with no gate
# between them. Their accept cargo must fit the starting hold together.
DAY_ONE_JOBS = ("iron_delivery", "coolant_run", "the_price_of_information")

PENDING_PRODUCER_CYCLES: set[str] = {
    "point_of_no_return:warp_gate_discovered",  # Task 7, BB-2
    "two_calls:two_calls_choice_made",  # Task 7, BB-17
    "two_calls:two_calls_resolved",  # Task 7, BB-17
}
# The later plan (BB-69): Oren's refusal gains a partial-intel node that sets it.
PENDING_CHECK_GATED_FLAGS: set[str] = {"oren_intel_received"}
PENDING_UNPRODUCED_HIDE_FLAGS: set[str] = {
    "torres_memorial:wrenchs_request_complete",  # Task 7, BB-32
}
PENDING_SELF_LOOPING_CHECKS: set[str] = {
    "elena_cantina:about_elena:1",  # Task 8, BB-73
    "arna_post_completion:catch:1",  # Task 8, BB-73
}
PENDING_UNKNOWN_FORCED_ENEMIES: set[str] = {
    "whistleblower:corporate_enforcer",  # Task 7, BB-30
}
PENDING_UNKNOWN_EVENT_COMMODITIES: set[str] = {
    "energy_breakthrough:fuel_cells",  # Task 12, BB-33
}
PENDING_OVERSIZED_ACCEPT_CARGO: set[str] = {"coolant_run:144"}  # Task 7, BB-15
PENDING_DAY_ONE_CARGO_OVERFLOW: set[str] = {"day_one:155"}  # Task 7, BB-15
PENDING_SHARED_CREW_MOVE_IDS: set[str] = {"emergency_repair"}  # Task 2, BB-13
PENDING_MOVE_IDS_ON_TWO_ITEMS: set[str] = {"point_defense"}  # Task 2, BB-89


def _loader() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _producers(dl: DataLoader) -> dict[str, set[str]]:
    """Every flag's producers, without the flag audit's invented mission producer.

    ``_collect_all_flag_uses`` credits every ``<mission_id>_complete`` flag to
    ``mission:<id>:auto``, and nothing sets such a flag. Forced-encounter trigger flags
    and ground-mission completion flags are set by code through variables, so they are
    added from the missions that name them.
    """
    producers, _consumers = _collect_all_flag_uses()
    real: dict[str, set[str]] = defaultdict(set)
    for flag, locations in producers.items():
        for location in locations:
            if not location.endswith(":auto"):
                real[flag].add(location)
    for mission in dl.missions:
        encounter = mission.forced_encounter
        if encounter is not None and encounter.trigger_flag:
            real[encounter.trigger_flag].add(f"forced:{mission.id}")
        if mission.ground_mission_complete_flag:
            real[mission.ground_mission_complete_flag].add(f"ground:{mission.id}")
    return real


def _dependents(dl: DataLoader) -> dict[str, set[str]]:
    """For each mission, the missions that need it completed, directly or through others."""
    needs = {
        m.id: set(m.prerequisites) | ({m.available_after} if m.available_after else set())
        for m in dl.missions
    }
    dependents: dict[str, set[str]] = defaultdict(set)
    for mission_id in needs:
        stack, seen = list(needs[mission_id]), set()
        while stack:
            required = stack.pop()
            if required in seen:
                continue
            seen.add(required)
            dependents[required].add(mission_id)
            stack.extend(needs.get(required, ()))
    return dependents


def _is_own_cycle(source: str, mission_id: str, dependents: dict[str, set[str]]) -> bool:
    """Whether a producer is the mission's own reward, or the reward of a mission needing it."""
    if not (source.startswith("mission:") and source.endswith(":reward")):
        return False
    rewarding = source.split(":")[1]
    return rewarding == mission_id or rewarding in dependents.get(mission_id, set())


def producer_cycles(dl: DataLoader) -> set[str]:
    """has_flag objectives with no producer reachable while their mission is open (BB-2).

    A producer counts unless it is the mission's own reward, or the reward of a mission
    that needs this one completed. A side mission with a non-flag objective passes, since
    the side-mission auto-resolve sets any flag nothing else produces. A mission held
    back behind HOLD_BACK_FLAG is skipped.
    """
    real = _producers(dl)
    dependents = _dependents(dl)
    broken: set[str] = set()
    for mission in dl.missions:
        if HOLD_BACK_FLAG in mission.required_flags:
            continue
        has_non_flag = any(o.type != ObjectiveType.HAS_FLAG for o in mission.objectives)
        if mission.mission_type == "side" and has_non_flag:
            continue
        for objective in mission.objectives:
            if objective.type != ObjectiveType.HAS_FLAG:
                continue
            usable = [
                source
                for source in real.get(objective.target_id, set())
                if not _is_own_cycle(source, mission.id, dependents)
            ]
            if not usable:
                broken.add(f"{mission.id}:{objective.target_id}")
    return broken


def _without_a_pass(tree: DialogueTree) -> set[str]:
    """The nodes a tree reaches from its start without passing a check.

    A reply with a skill check leads only to its failure node; any other reply leads to
    its next node.
    """
    seen: set[str] = set()
    pending = [tree.start_node_id]
    while pending:
        node_id = pending.pop()
        if node_id in seen or node_id not in tree.nodes:
            continue
        seen.add(node_id)
        for response in tree.nodes[node_id].responses:
            if response.skill_check is not None:
                pending.append(response.skill_check.failure_node_id)
            elif response.next_node_id:
                pending.append(response.next_node_id)
    return seen


def check_gated_flags(dl: DataLoader) -> set[str]:
    """Awaited flags set only past a passed skill check (BB-2's round-2 test 3).

    The writing guide says never to gate plot progression on a skill check. A has_flag
    objective's flag is free when any producer is: a reply's set_flag or a check's failure
    flag on a node its tree reaches without a pass, or any producer outside dialogue (a
    mission reward, an encounter, an NPC gate, a forced encounter, a ground mission, code).
    A check's success flag never frees it. A flag with no producer is producer_cycles'
    business, so it is skipped here.
    """
    free: set[str] = set()
    for tree in dl.dialogue_trees.values():
        for node_id in _without_a_pass(tree):
            for response in tree.nodes[node_id].responses:
                if response.set_flag:
                    free.add(response.set_flag)
                check = response.skill_check
                if check is not None and check.set_flag_on_failure:
                    free.add(check.set_flag_on_failure)
    real = _producers(dl)
    gated: set[str] = set()
    for mission in dl.missions:
        for objective in mission.objectives:
            flag = objective.target_id
            if objective.type != ObjectiveType.HAS_FLAG or not real.get(flag):
                continue
            outside_dialogue = any(not source.startswith("dialogue:") for source in real[flag])
            if not outside_dialogue and flag not in free:
                gated.add(flag)
    return gated


def unproduced_hide_flags(dl: DataLoader) -> set[str]:
    """NPC hide flags that nothing sets, so the NPC is never hidden (BB-32)."""
    real = _producers(dl)
    return {
        f"{npc.id}:{npc.hide_after_flag}"
        for npc in dl.npcs.values()
        if npc.hide_after_flag and not real.get(npc.hide_after_flag)
    }


def self_looping_checks(dl: DataLoader) -> set[str]:
    """Checks whose failure returns to their own node with the check still offered (BB-73)."""
    loops: set[str] = set()
    for tree in dl.dialogue_trees.values():
        for node in tree.nodes.values():
            for index, response in enumerate(node.responses):
                check = response.skill_check
                if check is None or check.failure_node_id != node.id:
                    continue
                failure_flag = check.set_flag_on_failure
                if failure_flag and failure_flag in response.excluded_flags:
                    continue
                loops.add(f"{tree.id}:{node.id}:{index}")
    return loops


def unknown_forced_enemies(dl: DataLoader) -> set[str]:
    """Forced-encounter enemy ids that name no template, so no fight is readied (BB-30)."""
    return {
        f"{mission.id}:{enemy_id}"
        for mission in dl.missions
        if mission.forced_encounter is not None
        for enemy_id in mission.forced_encounter.enemy_template_ids
        if enemy_id not in dl.enemy_templates
    }


def unknown_event_commodities(dl: DataLoader) -> set[str]:
    """Galaxy-event price and embargo keys that name no commodity (BB-33)."""
    document = json.loads((DATA_DIR / "economy" / "galaxy_events.json").read_text("utf-8"))
    unknown: set[str] = set()
    for event in document["galaxy_events"]:
        keys = list((event.get("price_modifiers") or {}).keys())
        keys += list(event.get("blocked_commodities") or [])
        unknown |= {f"{event['id']}:{key}" for key in keys if key not in dl.commodities}
    return unknown


def oversized_accept_cargo(dl: DataLoader) -> set[str]:
    """Missions whose accept cargo does not fit the starting ship's hold (BB-15)."""
    capacity = dl.ship_types[STARTING_SHIP_TYPE].cargo_capacity
    oversized: set[str] = set()
    for mission in dl.missions:
        volume = sum(
            cargo.quantity * dl.commodities[cargo.commodity_id].volume_per_unit
            for cargo in mission.on_accept_cargo
        )
        if volume > capacity:
            oversized.add(f"{mission.id}:{volume}")
    return oversized


def day_one_cargo_overflow(dl: DataLoader) -> set[str]:
    """The day-one jobs' accept cargo, if together it overfills the starting hold (BB-15).

    The Godot port loads every auto-accepted mission's cargo and never checks capacity,
    so an overfull hold refuses every purchase until a delivery.
    """
    capacity = dl.ship_types[STARTING_SHIP_TYPE].cargo_capacity
    by_id = {mission.id: mission for mission in dl.missions}
    volume = sum(
        cargo.quantity * dl.commodities[cargo.commodity_id].volume_per_unit
        for mission_id in DAY_ONE_JOBS
        for cargo in by_id[mission_id].on_accept_cargo
    )
    return {f"day_one:{volume}"} if volume > capacity else set()


def _equipment_moves() -> dict[str, set[str]]:
    """Each upgrade or part combat move id, mapped to the item ids that build it."""
    moves: dict[str, set[str]] = defaultdict(set)
    for name, key in (("upgrades.json", "upgrades"), ("parts.json", "parts")):
        document = json.loads((DATA_DIR / "ships" / name).read_text("utf-8"))
        for item in document[key]:
            move = item.get("combat_move")
            if move:
                moves[move["id"]].add(item["id"])
    return moves


def shared_crew_move_ids(dl: DataLoader) -> set[str]:
    """Crew move ids an upgrade or part move also uses, sharing a cooldown key (BB-13)."""
    crew: set[str] = set()
    for template in dl.crew_templates.values():
        if template.combat_move:
            crew.add(template.combat_move["id"])
        crew |= {move["id"] for move in template.combat_moves}
    return crew & set(_equipment_moves())


def move_ids_on_two_items() -> set[str]:
    """Move ids built by two different items, so one of them can never play (BB-89).

    upgrades.json and parts.json deliberately repeat each item under the same item id,
    so the contract is one item id per move id.
    """
    return {move_id for move_id, items in _equipment_moves().items() if len(items) > 1}


class TestContentContracts:
    def test_the_checks_see_the_content(self) -> None:
        dl = _loader()
        assert len(dl.missions) >= 60
        assert len(dl.dialogue_trees) >= 100
        assert len(dl.npcs) >= 60
        assert len(_equipment_moves()) >= 60

    @pytest.mark.timeout(300)
    def test_has_flag_objectives_have_a_producer_outside_their_own_cycle(self) -> None:
        assert producer_cycles(_loader()) == PENDING_PRODUCER_CYCLES

    @pytest.mark.timeout(300)
    def test_no_awaited_flag_waits_on_a_passed_check(self) -> None:
        assert check_gated_flags(_loader()) == PENDING_CHECK_GATED_FLAGS

    @pytest.mark.timeout(300)
    def test_every_hide_flag_has_a_producer(self) -> None:
        assert unproduced_hide_flags(_loader()) == PENDING_UNPRODUCED_HIDE_FLAGS

    def test_no_check_fails_back_to_itself(self) -> None:
        assert self_looping_checks(_loader()) == PENDING_SELF_LOOPING_CHECKS

    def test_forced_encounter_enemies_are_templates(self) -> None:
        assert unknown_forced_enemies(_loader()) == PENDING_UNKNOWN_FORCED_ENEMIES

    def test_galaxy_event_keys_are_commodities(self) -> None:
        assert unknown_event_commodities(_loader()) == PENDING_UNKNOWN_EVENT_COMMODITIES

    def test_accept_cargo_fits_the_starting_hold(self) -> None:
        assert oversized_accept_cargo(_loader()) == PENDING_OVERSIZED_ACCEPT_CARGO

    def test_the_day_one_jobs_fit_the_starting_hold_together(self) -> None:
        assert day_one_cargo_overflow(_loader()) == PENDING_DAY_ONE_CARGO_OVERFLOW

    def test_crew_and_equipment_move_ids_do_not_collide(self) -> None:
        assert shared_crew_move_ids(_loader()) == PENDING_SHARED_CREW_MOVE_IDS

    def test_each_equipment_move_id_belongs_to_one_item(self) -> None:
        assert move_ids_on_two_items() == PENDING_MOVE_IDS_ON_TWO_ITEMS
