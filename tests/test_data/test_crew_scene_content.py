"""Polish design 3.1's content rules for crew scenes, on the shipped data (spec 5.1's G12).

Rules 7, 9 and 10 do not hold for every tree shipped before the crew quests' wiring slice; each
keeps an allowlist of exactly those offenders, and a test asserts every entry still offends, so the
lists only shrink as each companion's polish slice (W5 to W8) rewrites that companion's trees.
Rule 6 is read strictly: every closing walk of a resolution sets every has_flag objective of its
quest, which also catches the take-both walk of the Meridian wreck.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.crew_scene import BEATS, INITIATIVES, CrewScene
from spacegame.models.dialogue import DialogueTree
from spacegame.models.mission import ObjectiveType
from spacegame.models.social import SOCIAL_SKILL_DEFINITIONS

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CREW_TREES_FILE = DATA / "dialogue" / "crew_quest_dialogues.json"
CREW_QUESTS_FILE = DATA / "missions" / "crew_quests.json"
PRIYA = "dr_priya_osei"
MARCUS = "marcus_jin"
# G12 (writing-discipline spec 5.1): the four arcs' money outcomes total 5,900 CR or less.
MONEY_CAP = 5900

# Today's offenders of rules 7, 9 and 10 (polish design 3.1); each slice empties its companion's.
ALLOWED: frozenset[tuple[str, str]] = frozenset(
    {
        ("7", "marcus_alternate_inspector"),
        ("7", "marcus_bribed_inspector"),
        ("7", "marcus_went_public"),
        ("7", "tomas_chose_peace"),
        ("7", "tomas_direct_confrontation"),
        ("9", "priya_paper_dialogue"),
        ("10", "marcus_confrontation_dialogue.partial"),
        ("10", "marcus_confrontation_dialogue.success"),
        ("10", "marcus_inspector_dialogue.bribe"),
        ("10", "marcus_inspector_dialogue.public"),
        ("10", "marcus_old_debts_dialogue.grateful"),
        ("10", "marcus_old_debts_dialogue.start"),
        ("10", "priya_paper_dialogue.start"),
        ("10", "priya_peer_review_dialogue.data_fail"),
        ("10", "priya_peer_review_dialogue.start"),
        ("10", "priya_peer_review_dialogue.witness_fail"),
        ("10", "priya_retracted_paper_dialogue.backstory"),
        ("10", "priya_retracted_paper_dialogue.start"),
        ("10", "priya_theorem_dialogue.partial"),
        ("10", "priya_theorem_dialogue.start"),
        ("10", "priya_theorem_dialogue.success"),
    }
)

_APOSTROPHE = "['’]"
_CONTRACTION = re.compile(
    rf"\b\w+n{_APOSTROPHE}t\b|\b\w+{_APOSTROPHE}(?:re|ve|ll|d|m)\b"
    rf"|\b(?:it|he|she|there|that|what|who|here|where|let){_APOSTROPHE}s\b",
    re.IGNORECASE,
)
_CAPTAIN = re.compile(r"\bCaptain\b")
_CHECK_TEXT = re.compile(r"^\[(\w+) (\d+)\] ")
_READER_KEYS = frozenset(
    {
        "required_flags",
        "excluded_flags",
        "forbidden_flags",
        "requires_flags",
        "auto_trigger_prerequisites",
        "hide_after_flag",
        "trigger_flag",
    }
)

_LOADER: DataLoader | None = None


def _loader() -> DataLoader:
    global _LOADER
    if _LOADER is None:
        _LOADER = get_data_loader()
        _LOADER.load_all()
    return _LOADER


def _crew_tree_ids() -> list[str]:
    raw = json.loads(CREW_TREES_FILE.read_text(encoding="utf-8"))
    return [tree["id"] for tree in raw["dialogues"]]


def _walks(tree: DialogueTree, entry: str) -> Iterator[tuple[frozenset[str], bool]]:
    """Every walk from the entry node to an end: the flags it sets, and whether it is a deferral
    taken straight from the entry node (a reply there that ends the talk and sets nothing)."""

    def step(node_id: str, path: tuple[str, ...], flags: frozenset[str]) -> Iterator[Any]:
        node = tree.get_node(node_id)
        if node is None or not node.responses:
            yield flags, False
            return
        for response in node.responses:
            now = flags | ({response.set_flag} if response.set_flag else set())
            check = response.skill_check
            if check is not None:
                for branch, extra in (
                    (check.success_node_id, check.set_flag_on_success),
                    (check.failure_node_id, check.set_flag_on_failure),
                ):
                    if branch not in path:
                        yield from step(
                            branch, path + (branch,), now | ({extra} if extra else set())
                        )
                continue
            if response.next_node_id is None:
                yield now, node_id == entry and len(path) == 1 and not response.set_flag
            elif response.next_node_id not in path:
                yield from step(response.next_node_id, path + (response.next_node_id,), now)

    yield from step(entry, (entry,), frozenset())


def _readers() -> set[str]:
    """Every flag the data reads: the reader keys anywhere under data/, has_flag objectives, and
    the flags an outcome_rewards entry pays."""
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in _READER_KEYS:
                    found.update([item] if isinstance(item, str) else list(item))
                elif key == "outcome_rewards":
                    found.update(entry["flag"] for entry in item)
                visit(item)
            if value.get("type") == "has_flag" and isinstance(value.get("target_id"), str):
                found.add(value["target_id"])
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for path in DATA.rglob("*.json"):
        visit(json.loads(path.read_text(encoding="utf-8")))
    found.discard("")
    return found


def _offences() -> set[tuple[str, str]]:
    loader = _loader()
    scenes: list[CrewScene] = list(loader.crew_scenes.values())
    raw_quests = json.loads(CREW_QUESTS_FILE.read_text(encoding="utf-8"))["missions"]
    missions = {mission.id: mission for mission in loader.missions}
    crew_trees = {tid: loader.dialogue_trees[tid] for tid in _crew_tree_ids()}
    out: set[tuple[str, str]] = set()

    # Rule 1: scene ids unique, and disjoint from NPC and tree ids
    raw_ids = [s["id"] for record in raw_quests for s in record.get("scenes", [])]
    for sid, count in Counter(raw_ids).items():
        if count > 1 or sid in loader.npcs or sid in loader.dialogue_trees:
            out.add(("1", sid))
    # Rule 2: every field names real content
    for scene in scenes:
        tree = loader.dialogue_trees.get(scene.dialogue_id)
        if (
            tree is None
            or scene.entry_node not in tree.nodes
            or scene.beat not in BEATS
            or scene.initiative not in INITIATIVES
            or (scene.system_id and scene.system_id not in loader.systems)
            or (scene.with_npc_id and scene.with_npc_id not in loader.npcs)
            or scene.crew_id not in loader.crew_templates
            or scene.min_loyalty < 0
        ):
            out.add(("2", scene.id))
    # Rule 3: scenes only on crew quests; each has a resolution; an opener iff its gate asks
    for scene in scenes:
        if missions[scene.quest_id].mission_type != "crew":
            out.add(("3", scene.id))
    for mission in missions.values():
        if mission.mission_type != "crew":
            continue
        beats = {s.beat for s in scenes if s.quest_id == mission.id}
        asks = f"{mission.id}_agreed" in mission.required_flags
        if "resolution" not in beats or ("opener" in beats) != asks:
            out.add(("3", mission.id))
    for scene in scenes:
        # Rule 4: every crew-initiative scene has a hook
        if scene.initiative == "crew" and not scene.hook:
            out.add(("4", scene.id))
        tree = crew_trees.get(scene.dialogue_id) or loader.dialogue_trees.get(scene.dialogue_id)
        if tree is None:
            continue
        # Rule 5: every walk off the entry sets a closing flag, but a deferral from the entry
        closing = set(scene.excluded_flags)
        for flags, deferral in _walks(tree, scene.entry_node):
            if not deferral and not flags & closing:
                out.add(("5", scene.id))
        # Rule 6 (strict): every closing walk of a resolution sets every has_flag objective
        if scene.beat == "resolution":
            needed = {
                o.target_id
                for o in missions[scene.quest_id].objectives
                if o.type == ObjectiveType.HAS_FLAG
            }
            for flags, deferral in _walks(tree, scene.entry_node):
                if not deferral and not needed <= flags:
                    out.add(("6", scene.id))
    readers = _readers()
    for tid, tree in crew_trees.items():
        expressions: set[str] = set()
        for node in tree.nodes.values():
            if node.expression:
                expressions.add(node.expression)
            text = node.text
            if node.speaker_id == PRIYA and _CONTRACTION.search(text):
                out.add(("10", f"{tid}.{node.id}"))
            if node.speaker_id == MARCUS and _CAPTAIN.search(text):
                out.add(("10", f"{tid}.{node.id}"))
            for index, response in enumerate(node.responses):
                key = f"{tid}.{node.id}.{index}"
                # Rule 7: every flag a crew tree sets has a reader
                check = response.skill_check
                for flag in (
                    response.set_flag,
                    check.set_flag_on_success if check else None,
                    check.set_flag_on_failure if check else None,
                ):
                    if flag and flag not in readers:
                        out.add(("7", flag))
                # Rule 8: a check is a registered skill in [Skill N] form, carrying no change
                if check is not None:
                    match = _CHECK_TEXT.match(response.text)
                    if (
                        check.skill not in SOCIAL_SKILL_DEFINITIONS
                        or match is None
                        or match.group(1).lower() != check.skill
                        or int(match.group(2)) != check.difficulty
                        or response.set_flag
                        or response.crew_loyalty_changes
                        or check.set_flag_on_success
                        or check.set_flag_on_failure
                    ):
                        out.add(("8", key))
                # Rule 11: a gated reply requires flags or excludes them, never both
                if response.required_flags and response.excluded_flags:
                    out.add(("11", key))
        # Rule 9: three or more distinct expressions in every crew tree
        if len(expressions) < 3:
            out.add(("9", tid))
    # Rule 10 for hooks: Priya's hold no contraction, Marcus's no "Captain"
    for scene in scenes:
        if scene.crew_id == PRIYA and _CONTRACTION.search(scene.hook):
            out.add(("10", f"hook:{scene.id}"))
        if scene.crew_id == MARCUS and _CAPTAIN.search(scene.hook):
            out.add(("10", f"hook:{scene.id}"))
    # Rule 12: per quest, at most one paid flag set on any walk of its scenes
    for record in raw_quests:
        paid = {entry["flag"] for entry in record.get("outcome_rewards", [])}
        if not paid:
            continue
        for scene in (s for s in scenes if s.quest_id == record["id"]):
            for flags, _ in _walks(loader.dialogue_trees[scene.dialogue_id], scene.entry_node):
                if len(flags & paid) > 1:
                    out.add(("12", scene.id))
    # G12's money cap: each quest's largest paid outcome in credits, summed over the arcs
    money = sum(
        max(
            (
                sum(
                    reward.get("amount", 0)
                    for reward in entry.get("rewards", [])
                    if reward.get("reward_type") == "credits"
                )
                for entry in record.get("outcome_rewards", [])
            ),
            default=0,
        )
        for record in raw_quests
    )
    if money > MONEY_CAP:
        out.add(("12", "money"))
    return out


class TestCrewSceneContent:
    def test_no_rule_has_a_new_offence(self) -> None:
        new = sorted(_offences() - ALLOWED)
        assert not new, f"Crew-scene content rules broken (rule, where): {new}"

    def test_every_allowed_entry_still_offends(self) -> None:
        stale = sorted(ALLOWED - _offences())
        assert not stale, f"Fixed; delete these from ALLOWED so the list only shrinks: {stale}"

    def test_every_walk_of_the_wreck_finds_it(self) -> None:
        tree = _loader().dialogue_trees["elena_wreck_dialogue"]
        for flags, deferral in _walks(tree, "start"):
            assert deferral or {"elena_wreck_found", "elena_choice_made"} <= flags, flags

    def test_the_twelve_quests_each_have_an_opener_a_raise_and_a_resolution(self) -> None:
        scenes = list(_loader().crew_scenes.values())
        assert len(scenes) == 36
        by_quest = Counter(scene.quest_id for scene in scenes)
        assert set(by_quest.values()) == {3} and len(by_quest) == 12
