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
from spacegame.models.flag_producers import content_flag_producers
from spacegame.models.mission import MissionManager, ObjectiveType
from tests.test_data.test_dialogue_integrity import _collect_all_flag_uses

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# BB-17: a mission whose required flags hold this flag waits for SP10. Nothing sets it.
HOLD_BACK_FLAG = "held_back_until_sp10"
# BB-17: the two missions the author held back for SP10 (Task 7 adds the flag to both).
HELD_BACK_MISSIONS: set[str] = {"two_calls", "the_silent_shaft"}
# BB-15: every mission's accept cargo must fit the starting ship's hold.
STARTING_SHIP_TYPE = "shuttle"
# BB-15: the Nexus Prime jobs a new captain can hold together on day one, with no gate
# between them. Their accept cargo must fit the starting hold together.
DAY_ONE_JOBS = ("iron_delivery", "coolant_run", "the_price_of_information")

PENDING_PRODUCER_CYCLES: set[str] = set()
# The writing session (BB-69): Oren's fail-forward nodes set it. Plan B1 keeps him listed meanwhile.
PENDING_CHECK_GATED_FLAGS: set[str] = {"oren_intel_received"}
PENDING_UNPRODUCED_HIDE_FLAGS: set[str] = set()
PENDING_SELF_LOOPING_CHECKS: set[str] = set()
PENDING_UNKNOWN_FORCED_ENEMIES: set[str] = set()
PENDING_UNKNOWN_EVENT_COMMODITIES: set[str] = set()
PENDING_OVERSIZED_ACCEPT_CARGO: set[str] = set()
PENDING_DAY_ONE_CARGO_OVERFLOW: set[str] = set()
PENDING_SHARED_CREW_MOVE_IDS: set[str] = set()
PENDING_MOVE_IDS_ON_TWO_ITEMS: set[str] = set()
# BB-12: templates that refuse any bribe. hulk_derelict and shield_drone cost 0 but stay
# bribable (a zero total refuses on its own in the port).
REFUSES_BRIBES = {
    "ledger_raider",
    "ledger_striker",
    "ledger_vanguard",
    "bounty_tracker",
    "bounty_enforcer",
    "bounty_vanguard",
    "bounty_ace",
    "faction_enforcer",
    "corsair_king",
    "guild_arbiter",
    "iron_maw",
    "ledger_phantom",
    "the_collector",
    "void_leviathan",
    "rogue_ai_vessel",
    "reach_dreadnought",
}


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
    that needs this one completed. A side mission with a non-flag objective may await a
    flag the side-mission auto-resolve still sets, one nothing outside the mission
    produces (``MissionManager._auto_resolvable``, BB-19); any other flag it awaits needs
    a usable producer like any mission's. A mission held back behind HOLD_BACK_FLAG is
    skipped.
    """
    real = _producers(dl)
    dependents = _dependents(dl)
    manager = MissionManager(
        dl.missions,
        produced_flags=content_flag_producers(
            dl.dialogue_trees.values(), dl.encounter_definitions, dl.npcs.values()
        ),
    )
    broken: set[str] = set()
    for mission in dl.missions:
        if HOLD_BACK_FLAG in mission.required_flags:
            continue
        has_non_flag = any(o.type != ObjectiveType.HAS_FLAG for o in mission.objectives)
        auto_resolved = mission.mission_type == "side" and has_non_flag
        for objective in mission.objectives:
            if objective.type != ObjectiveType.HAS_FLAG:
                continue
            if auto_resolved and manager._auto_resolvable(mission.id, objective.target_id):
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
    A check's success flag never frees it. The mission's own reward, or the reward of a
    mission that needs this one completed, never frees the flag, the same rule
    producer_cycles applies. A flag with no such producer is producer_cycles' business, so
    it is skipped here.
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
    dependents = _dependents(dl)
    gated: set[str] = set()
    for mission in dl.missions:
        for objective in mission.objectives:
            if objective.type != ObjectiveType.HAS_FLAG:
                continue
            flag = objective.target_id
            usable = [
                source
                for source in real.get(flag, set())
                if not _is_own_cycle(source, mission.id, dependents)
            ]
            if not usable:
                continue
            outside_dialogue = any(not source.startswith("dialogue:") for source in usable)
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
    """Forced-encounter enemy ids that name no template, so no fight is readied (BB-30).

    A hostile forced encounter that names no enemy passes here: lab_rat and the_informant
    name none, and their encounter definitions (lab_rat_malfunction, informant_pursuit) do
    not exist. F-43 records both for SP10.
    """
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
        # Floors for every input a check walks, so a renamed key cannot empty it and pass.
        assert (
            sum(o.type == ObjectiveType.HAS_FLAG for m in dl.missions for o in m.objectives) >= 60
        )
        checks = [
            response
            for tree in dl.dialogue_trees.values()
            for node in tree.nodes.values()
            for response in node.responses
            if response.skill_check is not None
        ]
        assert len(checks) >= 40
        assert sum(1 for npc in dl.npcs.values() if npc.hide_after_flag) >= 15
        assert (
            sum(
                len(m.forced_encounter.enemy_template_ids)
                for m in dl.missions
                if m.forced_encounter is not None
            )
            >= 8
        )
        assert sum(1 for m in dl.missions if m.on_accept_cargo) >= 5
        crew_moves = {
            move["id"] for template in dl.crew_templates.values() for move in template.combat_moves
        }
        assert len(crew_moves) >= 12
        events = json.loads((DATA_DIR / "economy" / "galaxy_events.json").read_text("utf-8"))
        events = events["galaxy_events"]
        assert sum(len(e.get("price_modifiers") or {}) for e in events) >= 12
        assert sum(len(e.get("blocked_commodities") or []) for e in events) >= 6

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

    def test_bribe_refusing_templates_are_marked(self) -> None:
        dl = _loader()
        marked = {t.id for t in dl.enemy_templates.values() if not t.bribable}
        assert marked == REFUSES_BRIBES
        zero_cost = {t.id for t in dl.enemy_templates.values() if t.bribe_cost == 0}
        assert zero_cost - {"hulk_derelict", "shield_drone"} <= REFUSES_BRIBES

    @pytest.mark.timeout(300)
    def test_the_hold_back_flag_stays_unset_and_holds_back_two_missions(self) -> None:
        dl = _loader()
        assert not _producers(dl).get(HOLD_BACK_FLAG), (
            f"something now sets {HOLD_BACK_FLAG}: producer_cycles must check the held-back "
            "missions again"
        )
        carriers = {m.id for m in dl.missions if HOLD_BACK_FLAG in m.required_flags}
        assert carriers <= HELD_BACK_MISSIONS, (
            f"unexpected missions hold back on {HOLD_BACK_FLAG}: {carriers - HELD_BACK_MISSIONS}"
        )
