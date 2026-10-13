"""Dialogue goldens: every node of every tree, the ambient and chatter line pickers, crew
interjections, the Talk list, and the captain's tokens.

Each response is selected from a fresh manager positioned on its node, so steps are
independent. Every case builds its managers from its own setup, so the Godot adapter
rebuilds the same objects from setup and synced data alone. Tree cases carry two
profiles: "novice" (default social skills, no flags) and "expert" (every social skill at
MAX_SOCIAL_LEVEL, every flag the tree's responses require). Reputation changes need a
PoliticsManager (wave B), so they are skipped here, as Python skips them without one
(ruling P5).

A response that neither profile can pick (novice lacks its required flags, and a flag
expert loads trips its excluded flags) is recorded only as filtered out of a step's
available list. test_dialogue_driver.UNSELECTED_RESPONSES names each one, and
parity/port_notes.md lists them.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from typing import Any

from spacegame.data_loader import get_data_loader
from spacegame.models.ambient_dialogue import AmbientDialogueManager
from spacegame.models.captain_tokens import TOKEN_NAMES, Pronouns, fill
from spacegame.models.combat import CombatResult, CombatState
from spacegame.models.crew import CrewRoster
from spacegame.models.crew_interjection import CrewInterjectionResolver, InterjectionEvent
from spacegame.models.dialogue import DialogueManager, DialogueTree
from spacegame.models.mission import MissionManager
from spacegame.models.npc_availability import npcs_here, settable_index
from spacegame.models.social import (
    MAX_SOCIAL_LEVEL,
    SOCIAL_SKILL_DEFINITIONS,
    SOCIAL_XP_THRESHOLDS,
    SocialManager,
)
from spacegame.models.station_chatter import StationChatterManager
from spacegame.sim_rng import SimRng, stable_seed
from tools.parity.driver import REPO_ROOT, Case
from tools.parity.drivers.combat import LOADOUTS, MAX_ROUNDS, build_fight, play_round

COMPANIONS = ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")
LOYALTY = 60
CREW_SLOTS = 4
# CrewRoster.recruit starts every member at loyalty 30, so this delta lands each companion
# on LOYALTY. trade.py records its crew the same way.
_CREW: tuple[dict[str, Any], ...] = tuple(
    {"crew_id": crew_id, "loyalty_delta": LOYALTY - 30} for crew_id in COMPANIONS
)
# Every social skill at the highest level the game can reach, loaded through the public
# SocialManager.load_state (the encounters driver's "boosted" profile).
EXPERT_SOCIAL: dict[str, Any] = {
    "skills": {
        sid: {
            "id": sid,
            "name": name,
            "level": MAX_SOCIAL_LEVEL,
            "xp": SOCIAL_XP_THRESHOLDS[MAX_SOCIAL_LEVEL - 1],
        }
        for sid, name in SOCIAL_SKILL_DEFINITIONS.items()
    },
    "disposition": {},
}
# (label, enemy template ids, player hull). Together the three fights fire every
# round trigger (first_turn, player_low_hp, enemy_low_hp, enemy_type_match) and both
# combat outcomes: union_brawler is marcus_jin's nemesis, and corsair_king beats a
# 40-hull frigate after its hull drops below 30%.
INTERJECTION_FIGHTS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("raider", ("pirate_raider",), 900),
    ("nemesis", ("union_brawler",), 900),
    ("defeat", ("corsair_king",), 40),
)


def _npc_for(tree_id: str) -> str | None:
    """The NPC that opens this tree, as ``Game.start_dialogue`` resolves it.

    A tree is either an NPC's base ``dialogue_id`` or one of its ``dialogue_states``.
    """
    for npc_id, npc in get_data_loader().npcs.items():
        if npc.dialogue_id == tree_id or any(s.dialogue_id == tree_id for s in npc.dialogue_states):
            return npc_id
    return None


def _required_flags(tree: DialogueTree) -> dict[str, bool]:
    flags = {
        r_flag
        for node in tree.nodes.values()
        for r in node.responses
        for r_flag in r.required_flags
    }
    return dict.fromkeys(sorted(flags), True)


def _tree_setup(tree_id: str, tree: DialogueTree) -> dict[str, Any]:
    return {
        "tree_id": tree_id,
        "npc_id": _npc_for(tree_id),
        "crew_slots": CREW_SLOTS,
        "crew": [dict(entry) for entry in _CREW],
        "profiles": {
            "novice": {"social": {}, "flags": {}},
            "expert": {"social": EXPERT_SOCIAL, "flags": _required_flags(tree)},
        },
    }


def _manager(
    setup: dict[str, Any], profile: str
) -> tuple[DialogueManager, SocialManager, CrewRoster]:
    """A dialogue manager, its social manager, and its roster, built from setup alone."""
    social = SocialManager()
    social.load_state(setup["profiles"][profile]["social"])
    roster = CrewRoster(get_data_loader().crew_templates)
    for entry in setup["crew"]:
        roster.recruit(entry["crew_id"], setup["crew_slots"])
        roster.adjust_loyalty(entry["crew_id"], entry["loyalty_delta"])
    manager = DialogueManager()
    manager.set_social_manager(social)
    manager.set_crew_roster(roster)
    manager.load_flags(setup["profiles"][profile]["flags"])
    return manager, social, roster


def _positioned(
    setup: dict[str, Any], profile: str, tree: DialogueTree, node_id: str
) -> tuple[DialogueManager, SocialManager, CrewRoster]:
    manager, social, roster = _manager(setup, profile)
    manager.start_dialogue(tree, setup["npc_id"])
    # No public setter moves a manager to a node mid-tree; the Godot adapter sets its
    # current node the same way (plan Task 14).
    manager._current_node_id = node_id
    return manager, social, roster


def _tree_case(tree_id: str, tree: DialogueTree) -> Case:
    setup = _tree_setup(tree_id, tree)
    case = Case("dialogue", f"tree_{tree_id}", setup)
    for profile in setup["profiles"]:
        for node_id, node in tree.nodes.items():
            probe, _, _ = _positioned(setup, profile, tree, node_id)
            available = probe.get_available_responses()
            for index, response in enumerate(available):
                manager, social, roster = _positioned(setup, profile, tree, node_id)
                manager.select_response(index)
                check = manager.get_last_check_result()
                result = {
                    "available": [node.responses.index(r) for r in available],
                    "response": node.responses.index(response),
                    # The raw id, not get_current_node(): a dangling next_node_id stays visible.
                    "next_node": manager._current_node_id if manager.is_active else None,
                    "check": list(check) if check else None,
                }
                members = roster.get_state()["members"]
                state = {
                    "flags": sorted(k for k, v in manager.get_flags().items() if v),
                    "disposition": social.get_state()["disposition"],
                    "loyalty": {
                        e["crew_id"]: members[e["crew_id"]]["loyalty"] for e in setup["crew"]
                    },
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
    setup: dict[str, Any] = {
        "rng_key": ["parity_ambient"],
        "recruited_ids": list(COMPANIONS),
        "loyalty": LOYALTY,
        "loyalty_map": dict.fromkeys(COMPANIONS, LOYALTY),
        "system_id": "nexus_prime",
        "faction_id": "commerce_guild",
        "action_type": "sold_cargo",
        # {} rather than None: an explicit dict turns get_line's flag filter on.
        "player_flags": {},
    }
    manager = AmbientDialogueManager(dl.ambient_lines, rng=SimRng.from_key(*setup["rng_key"]))
    case = Case("dialogue", "ambient", setup)
    contexts = sorted({line.context for line in dl.ambient_lines})
    for context in contexts:
        for crew_id in setup["recruited_ids"]:
            line = manager.get_line(
                context,
                crew_id,
                setup["system_id"],
                setup["faction_id"],
                list(setup["recruited_ids"]),
                setup["loyalty"],
                setup["action_type"],
                dict(setup["player_flags"]),
            )
            case.record("get_line", [context, crew_id], line, _sorted_ambient_state(manager))
    for _ in range(5):
        case.record(
            "get_random_idle",
            [],
            manager.get_random_idle(list(setup["recruited_ids"]), dict(setup["loyalty_map"])),
            _sorted_ambient_state(manager),
        )
    actions = sorted({line.action_type for line in dl.ambient_lines if line.action_type})
    for action in actions:
        action_line = manager.get_player_action_line(
            action, list(setup["recruited_ids"]), dict(setup["loyalty_map"])
        )
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
    setup: dict[str, Any] = {"rng_key": ["parity_chatter"], "count": 3, "player_flags": {}}
    manager = StationChatterManager(
        dl.station_chatter_lines, rng=SimRng.from_key(*setup["rng_key"])
    )
    case = Case("dialogue", "chatter", setup)
    for system_id in dl.systems:
        for rep in (-60, 0, 70):
            for events in ([], ["embargo"]):
                lines = manager.get_chatter(
                    system_id, rep, events, setup["count"], dict(setup["player_flags"])
                )
                case.record(
                    "get_chatter", [system_id, rep, events], lines, _sorted_chatter_state(manager)
                )
    return case


def _trigger_inputs(state: CombatState) -> dict[str, Any]:
    """Every CombatState field CrewInterjectionResolver reads, in golden form."""
    return {
        "round_number": state.round_number,
        "player": {"hull": state.player.hull, "max_hull": state.player.max_hull},
        "enemies": [
            {"template_id": e.template.id, "current_hull": e.current_hull, "is_fled": e.is_fled}
            for e in state.enemies
        ],
    }


def _fired(resolver: CrewInterjectionResolver) -> dict[str, object]:
    return {"fired": sorted([crew_id, trigger] for crew_id, trigger in resolver.fired)}


def _commit(
    case: Case, label: str, resolver: CrewInterjectionResolver, event: InterjectionEvent
) -> None:
    resolver.commit(event)
    case.record("commit", [label, event.crew_id, event.trigger], None, _fired(resolver))


def _interjections() -> Case:
    dl = get_data_loader()
    crew_aboard = [(cid, dl.crew_templates[cid].name) for cid in COMPANIONS]
    seeds = {
        label: stable_seed("parity_interjection", label) for label, _, _ in INTERJECTION_FIGHTS
    }
    setup: dict[str, Any] = {"crew_aboard": [list(pair) for pair in crew_aboard], "seeds": seeds}
    case = Case("dialogue", "interjections", setup)
    for label, enemy_ids, hull in INTERJECTION_FIGHTS:
        fight = build_fight(
            f"interjections_{label}",
            ship_type_id="war_frigate",
            loadout=LOADOUTS[0],
            enemy_ids=enemy_ids,
            seed=seeds[label],
            hull=hull,
        )
        resolver = CrewInterjectionResolver(
            list(dl.crew_interjections), crew_aboard, seed=seeds[label]
        )
        scratch = Case("dialogue", "scratch", {})
        for _ in range(MAX_ROUNDS):
            if fight.engine.is_combat_over():
                break
            events = resolver.evaluate_round(fight.state)
            case.record(
                "evaluate_round",
                [label, _trigger_inputs(fight.state)],
                [dataclasses.asdict(e) for e in events],
                _fired(resolver),
            )
            if events:
                _commit(case, label, resolver, events[0])
            play_round(fight, scratch)
        result = fight.state.result
        assert result in (CombatResult.VICTORY, CombatResult.DEFEAT), f"{label}: {result}"
        events = resolver.evaluate_outcome(fight.state, result.value)
        case.record(
            "evaluate_outcome",
            [label, result.value],
            [dataclasses.asdict(e) for e in events],
            _fired(resolver),
        )
        if events:
            _commit(case, label, resolver, events[0])
    return case


@dataclasses.dataclass(frozen=True)
class _TalkStep:
    """One story state the Talk list golden lists people for (bug bash BB-38)."""

    label: str
    system_id: str
    flags: tuple[str, ...] = ()
    statuses: tuple[tuple[str, str], ...] = ()
    recruited: tuple[str, ...] = ()
    progress: tuple[tuple[str, tuple[bool, ...]], ...] = ()


_ELENA_AWAY = ("iron_delivery_moved_on", "larsen_permit_complete", "talked_to_elena_cantina")
_ELENA_OPEN = (
    ("bill_of_landing", "completed"),
    ("iron_delivery", "completed"),
    ("footing_the_bill", "active"),
)
# Each clause of npc_availability.is_listed, after every station's day one: a one-shot scene
# not yet played, the keep rule after each kept exit and its release once the awaited flag is
# set, a companion aboard, a lesson learned, a hide flag, a prerequisite, and a talk objective
# that keeps someone only while its mission is active and the talk unmet. Python lists the twelve
# Act II v1 NPCs, and so does this golden; leaving them out is the port's clause alone (D-21).
TALK_STEPS: tuple[_TalkStep, ...] = (
    _TalkStep("elena_first_open", "nexus_prime", _ELENA_AWAY[:2], _ELENA_OPEN[:2]),
    _TalkStep("elena_walked_away", "nexus_prime", _ELENA_AWAY, _ELENA_OPEN),
    _TalkStep("elena_aboard", "nexus_prime", _ELENA_AWAY, _ELENA_OPEN, ("elena_reeves",)),
    _TalkStep(
        "elena_taught",
        "nexus_prime",
        (*_ELENA_AWAY, "elena_gave_trading_tips"),
        (*_ELENA_OPEN[:2], ("footing_the_bill", "completed")),
    ),
    _TalkStep(
        "elena_lesson_landed",
        "nexus_prime",
        (*_ELENA_AWAY, "elena_gave_trading_tips"),
        _ELENA_OPEN,
    ),
    _TalkStep(
        "dex_declined",
        "nexus_prime",
        ("cargo_lost_complete", "larsen_permit_complete", "met_dex_halloran"),
        (("cargo_lost", "completed"), ("whispers_at_the_bar", "active")),
    ),
    # Synthetic: the_drifters_deal auto-accepts once Tomas is met, so play never leaves it
    # available with his scene spent. Tomas's deferral (polish design 6) leaves his deal active
    # with his scene spent, which tomas_thinking pins; this step stays the one where an
    # available mission keeps a spent NPC (the keep rule's 'available' half).
    _TalkStep(
        "tomas_unresolved",
        "havens_rest",
        ("breakstone_permit_earned", "met_tomas_drifter"),
        (("union_territory", "completed"), ("the_drifters_deal", "available")),
    ),
    _TalkStep(
        "tomas_thinking",
        "havens_rest",
        ("breakstone_permit_earned", "met_tomas_drifter", "talked_to_tomas_drifter"),
        (("union_territory", "completed"), ("the_drifters_deal", "active")),
    ),
    _TalkStep(
        "oren_kept",
        "breakstone",
        ("favor_ground_complete", "met_oren_tak"),
        (("the_favor_returned", "active"),),
    ),
    _TalkStep("reva_waits", "nova_research"),
    _TalkStep(
        "reva_reached", "nova_research", ("cargo_lost_accepted",), (("cargo_lost", "active"),)
    ),
    _TalkStep(
        "intake_offered",
        "forgeworks",
        ("talked_to_cargo_broker",),
        (("iron_delivery", "available"),),
    ),
    _TalkStep(
        "intake_awaited",
        "forgeworks",
        ("talked_to_cargo_broker", "iron_job_full"),
        (("iron_delivery", "active"),),
    ),
    _TalkStep(
        "odom_short_load",
        "nexus_prime",
        ("larsen_permit_complete", "talked_to_cargo_broker", "iron_job_short_lost"),
        (("iron_delivery", "active"),),
    ),
    _TalkStep(
        "odom_gone",
        "nexus_prime",
        ("iron_delivery_failed", "larsen_permit_complete"),
        (("iron_delivery", "failed"),),
    ),
    _TalkStep(
        "larsen_met",
        "nexus_prime",
        statuses=(("bill_of_landing", "active"),),
        progress=(("bill_of_landing", (True,)),),
    ),
)


def _talk_step(step: _TalkStep) -> dict[str, Any]:
    return {
        "label": step.label,
        "system_id": step.system_id,
        "flags": dict.fromkeys(sorted(step.flags), True),
        "mission_state": {
            "status": dict(step.statuses),
            "progress": {mission_id: list(done) for mission_id, done in step.progress},
        },
        "recruited": list(step.recruited),
    }


def _npcs_here() -> Case:
    dl = get_data_loader()
    day_one = [
        _TalkStep(f"day_one_{system_id}", system_id, (), (("bill_of_landing", "active"),))
        for system_id in dl.systems
    ]
    setup: dict[str, Any] = {"steps": [_talk_step(s) for s in (*day_one, *TALK_STEPS)]}
    case = Case("dialogue", "npcs_here", setup)
    index = settable_index(dl.npcs.values(), dl.dialogue_trees)
    for step in setup["steps"]:
        manager = MissionManager(copy.deepcopy(dl.missions))
        manager.load_state(step["mission_state"])
        listed = npcs_here(
            dl.npcs.values(),
            step["system_id"],
            dict(step["flags"]),
            manager,
            set(step["recruited"]),
            index,
        )
        case.record("npcs_here", [step["label"]], [list(pair) for pair in listed], {})
    return case


# Writing discipline spec 2.5 to 2.7: the captain's tokens, rendered for the three choices. The
# probes cover the spec's two worked lines, every token, the contractions, {day}, and braces the
# renderer leaves for a surface's own fill; every shipped line that carries a token joins them.
CAPTAIN_TOKEN_PROBES: tuple[str, ...] = (
    "{They}{v:'s|'re} asleep in the pilot's chair again. Leave {them}.",
    "Dock records list {player} as master of record. {They} {v:holds|hold} a provisional license.",
    "{they} {They} {them} {their} {Their} {theirs} {themself} {sir} {Sir} {son} {Son}",
    "{they}{v:'s|'ve} gone. {they} {v:doesn't|don't} know. {they} {v:wasn't|weren't}. {they}'ll",
    "Day {day}. Fourteen-oh-six.",
    "{system} and {shakedown_demand} wait for their own fill.",
)
CAPTAIN_TOKEN_DAY = 61
_CAPTAIN_TOKEN = re.compile(r"\{v:[^{}]*\}|\{(?:" + "|".join(sorted(TOKEN_NAMES - {"v"})) + r")\}")


def _shipped_token_lines() -> list[str]:
    """Every string under data/ that carries a captain token, sorted."""
    found: set[str] = set()
    for path in sorted((REPO_ROOT / "data").rglob("*.json")):
        stack: list[object] = [json.loads(path.read_text(encoding="utf-8"))]
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                if _CAPTAIN_TOKEN.search(node):
                    found.add(node)
            elif isinstance(node, dict):
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return sorted(found)


def _captain_tokens() -> Case:
    lines = [*CAPTAIN_TOKEN_PROBES, *_shipped_token_lines()]
    setup: dict[str, Any] = {
        "choices": [choice.value for choice in Pronouns],
        "day": CAPTAIN_TOKEN_DAY,
        "lines": lines,
    }
    case = Case("dialogue", "captain_tokens", setup)
    for choice in Pronouns:
        for line in lines:
            for day in (CAPTAIN_TOKEN_DAY, None):
                case.record("fill", [choice.value, line, day], fill(line, choice, day), {})
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
        _npcs_here(),
        _captain_tokens(),
    ]
