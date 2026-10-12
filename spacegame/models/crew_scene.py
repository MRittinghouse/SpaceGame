"""Crew scenes: one conversation of a crew quest, and the gate that says when it is due.

Polish design 3.1. A scene is declared in a ``scenes`` list on its crew quest's record in
``data/missions/crew_quests.json``; ``Mission`` never reads the key, so the missions and their
goldens never see scenes. The gate's six rules run in order, and the first that fails is the
refusal the action returns: the companion is aboard; the quest's status fits the beat (an opener
before the accept, a middle or a resolution while the quest is active); live loyalty reaches the
scene's mark less the Legend offset; the flags allow it; the scene's place is empty or here; and
a crew opener or middle waits when its companion already had a scene this landing.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

BEATS: tuple[str, ...] = ("opener", "middle", "resolution")
INITIATIVES: tuple[str, ...] = ("crew", "captain")

NO_SUCH_SCENE = "No one aboard wants to talk about that."
NOT_ABOARD = "{name} is not aboard."
NOTHING_NOW = "{name} has nothing to say about that now."
WRONG_PLACE = "{name} wants to talk about that at {system}."
NEXT_PORT = "{name} will bring it up at the next port."

_BEFORE_ACCEPT: tuple[str, ...] = ("unavailable", "available")
_ACTIVE = "active"


@dataclass(frozen=True)
class CrewScene:
    """One conversation of a crew quest (polish design 3.1)."""

    id: str
    quest_id: str
    crew_id: str
    beat: str
    initiative: str
    dialogue_id: str
    entry_node: str
    system_id: str = ""
    with_npc_id: str = ""
    min_loyalty: int = 0
    required_flags: tuple[str, ...] = ()
    excluded_flags: tuple[str, ...] = ()
    hook: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], quest_id: str, crew_id: str) -> CrewScene:
        """A scene from its record in a crew quest's ``scenes`` list.

        Args:
            data: The scene's record.
            quest_id: The id of the crew quest the record sits on.
            crew_id: The quest's ``crew_member_id``.

        Returns:
            The scene.
        """
        return cls(
            id=data["id"],
            quest_id=quest_id,
            crew_id=crew_id,
            beat=data["beat"],
            initiative=data["initiative"],
            dialogue_id=data["dialogue_id"],
            entry_node=data["entry_node"],
            system_id=data.get("system_id", ""),
            with_npc_id=data.get("with_npc_id", ""),
            min_loyalty=int(data.get("min_loyalty", 0)),
            required_flags=tuple(data.get("required_flags", [])),
            excluded_flags=tuple(data.get("excluded_flags", [])),
            hook=data.get("hook", ""),
        )


@dataclass(frozen=True)
class SceneContext:
    """What the gate reads: the crew aboard, the quests, the flags, the place and the landing."""

    crew_names: Mapping[str, str]
    loyalty: Mapping[str, int]
    loyalty_offset: int
    statuses: Mapping[str, str]
    flags: Mapping[str, bool]
    system_id: str
    system_names: Mapping[str, str]
    spoken: Collection[str] = ()


@dataclass(frozen=True)
class CrewTalkRow:
    """A scene the crew talk offers: a companion's matter, or a topic the captain may raise."""

    crew_id: str
    scene_id: str
    hook: str
    initiative: str


def parse_scenes(records: Iterable[Mapping[str, Any]]) -> dict[str, CrewScene]:
    """Every scene on these mission records, in content order.

    Args:
        records: Mission records as the JSON holds them.

    Returns:
        The scenes by id.
    """
    scenes: dict[str, CrewScene] = {}
    for record in records:
        for raw in record.get("scenes", []):
            scene = CrewScene.from_dict(raw, record["id"], record.get("crew_member_id", ""))
            scenes[scene.id] = scene
    return scenes


def _paced(scene: CrewScene) -> bool:
    return scene.initiative == "crew" and scene.beat in ("opener", "middle")


def refusal(scene: CrewScene, ctx: SceneContext) -> str:
    """Why the scene is not due, or "" when it is (the gate's six rules, in order).

    Args:
        scene: The scene.
        ctx: The game's state as the gate reads it.

    Returns:
        The first rule's refusal that fails, or "".
    """
    name = ctx.crew_names.get(scene.crew_id, scene.crew_id)
    if scene.crew_id not in ctx.loyalty:
        return NOT_ABOARD.format(name=name)
    status = ctx.statuses.get(scene.quest_id, "unavailable")
    fits = status in _BEFORE_ACCEPT if scene.beat == "opener" else status == _ACTIVE
    if not fits:
        return NOTHING_NOW.format(name=name)
    if ctx.loyalty[scene.crew_id] < scene.min_loyalty - ctx.loyalty_offset:
        return NOTHING_NOW.format(name=name)
    if not all(ctx.flags.get(flag, False) for flag in scene.required_flags):
        return NOTHING_NOW.format(name=name)
    if any(ctx.flags.get(flag, False) for flag in scene.excluded_flags):
        return NOTHING_NOW.format(name=name)
    if scene.system_id and scene.system_id != ctx.system_id:
        place = ctx.system_names.get(scene.system_id, scene.system_id)
        return WRONG_PLACE.format(name=name, system=place)
    if _paced(scene) and scene.crew_id in ctx.spoken:
        return NEXT_PORT.format(name=name)
    return ""


def talk_rows(
    scenes: Iterable[CrewScene], ctx: SceneContext, crew_order: Sequence[str]
) -> list[CrewTalkRow]:
    """The crew talk: each companion's first due matter, in roster order, then the captain's topics.

    Args:
        scenes: Every scene, in content order.
        ctx: The game's state as the gate reads it.
        crew_order: The companions aboard, in roster order.

    Returns:
        One row per companion with a matter due, then one per due captain topic.
    """
    due = [scene for scene in scenes if refusal(scene, ctx) == ""]
    rows: list[CrewTalkRow] = []
    for crew_id in crew_order:
        for scene in due:
            if scene.crew_id == crew_id and scene.initiative == "crew":
                rows.append(CrewTalkRow(crew_id, scene.id, scene.hook, scene.initiative))
                break
    rows.extend(
        CrewTalkRow(scene.crew_id, scene.id, scene.hook, scene.initiative)
        for scene in due
        if scene.initiative == "captain"
    )
    return rows


def place_hooks(scenes: Iterable[CrewScene], ctx: SceneContext) -> list[tuple[str, str]]:
    """The hooks a landing announces: each due crew scene whose place is here.

    Args:
        scenes: Every scene, in content order.
        ctx: The game's state as the gate reads it, the landing begun.

    Returns:
        (companion's name, hook) for each, in content order.
    """
    return [
        (ctx.crew_names.get(scene.crew_id, scene.crew_id), scene.hook)
        for scene in scenes
        if scene.initiative == "crew"
        and scene.system_id
        and scene.system_id == ctx.system_id
        and scene.hook
        and refusal(scene, ctx) == ""
    ]
