"""The strings the prose gates read (writing discipline spec 5.1).

Every player-facing string under ``data/``, and every string built in code under
``spacegame/views`` and ``spacegame/models``; the narration fields of the spec's table; spoken
lines with their speakers; the bracket tags on the captain's replies and encounter labels; the
dialogue trees; and the person names. Pure Python over the JSON files and the source text (read
with ``ast``), with no ``spacegame`` import, so aurelia's ``tools/gate.py`` can lift the data
half at cutover.

A path names one string inside its file: ``.key`` for an object field, ``[id=X]`` for the list
element whose ``id`` (or ``entry_id``, or ``lens_id``) is X when no sibling shares it, and
``[n]`` for any other list element. Id selectors keep an allowlist row on its string when a
record is inserted above it. A string built in code has the path ``Scope|text``
(``strings_in_source``).
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from fnmatch import fnmatch
from functools import cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# Art prompts for the sprite pipeline; never shown to the player.
EXCLUDED_FILES = frozenset({"data/assets/sprite_manifest.json"})
# Authoring fields of narrative/lenses.json that no view renders: spacegame/models/lens.py
# stores them, and capstone_view.py shows only name, core_fantasy and tier_unlocks.
LENS_AUTHORING_KEYS = frozenset({"question", "sees", "wants", "trades", "voice", "minigame_shape"})
ID_KEYS = ("id", "entry_id", "lens_id")
DIALOGUE_FILES = ("data/dialogue/dialogues.json", "data/dialogue/crew_quest_dialogues.json")
# Files whose strings with a space are spoken lines (G11's speech rules), less the auction
# voices' narration (AUCTION_NARRATION).
SPOKEN_FILES = (
    "data/combat/captains.json",
    "data/combat/captain_variants.json",
    "data/auctions/stellaris_voices.json",
    "data/auctions/crimson_reach_voices.json",
    "data/economy/first_sale_lines.json",
    "data/narrative/lens_reactions.json",
)
# Code strings the spec's narration table names (spacegame/views/capstone_view.py's frame).
CODE_NARRATION = (("spacegame/views/capstone_view.py", "_TEMPLATE"),)
# The auction voices' narration subtrees (spec 5.1's narration table): never speech.
AUCTION_NARRATION = (".post_session.", ".player_listing_post_session.")
# Strings built in code (spec 5.1 scopes G1 to G3, G5 and G10 to every player-facing string):
# every string constant under these folders, f-string parts included. Docstrings and logger
# arguments never reach a player and are skipped, as test_code_prose_dashes.py skips them; so
# are blank strings and lowercase identifiers.
CODE_DIRS = ("spacegame/views", "spacegame/models")
_LOG_METHODS = frozenset({"debug", "info", "warning", "error", "exception", "critical", "log"})

_IDENTIFIER = re.compile(r"^[a-z0-9_.:/-]+$")
_SEGMENT = re.compile(r"\.([^.\[]+)|\[id=([^\]]+)\]|\[(\d+)\]")
_LAST_SEGMENT = re.compile(r"(?:\.[^.\[]+|\[[^\]]+\])$")
_I = r"\[[^\]]+\]"


@dataclass(frozen=True)
class Text:
    """One string: the repo-relative file, the path inside it, and the value."""

    file: str
    path: str
    text: str


@dataclass(frozen=True)
class Line:
    """A spoken string with its speaker id ("captain" for a reply, "" when unknown)."""

    file: str
    path: str
    speaker: str
    text: str


@dataclass(frozen=True)
class Surface:
    """A narration field: files matching a glob and paths matching a pattern.

    ``where`` keeps only strings whose owning record holds that field and value (a node
    whose ``speaker_id`` is ``narrator``, a chatter line whose ``category`` is
    ``atmosphere``).
    """

    files: str
    paths: str
    where: tuple[str, str] | None = None


@dataclass(frozen=True)
class Person:
    """A named person record: its file and path, the display name, and its home system."""

    file: str
    path: str
    name: str
    system: str


NARRATION: tuple[Surface, ...] = (
    Surface("data/encounters/*.json", rf"\.encounters{_I}\.description"),
    Surface(
        "data/encounters/*.json",
        rf"\.encounters{_I}\.choices{_I}\."
        r"(?:description|outcome\.description|failure_outcome\.description)",
    ),
    Surface(
        "data/dialogue/*.json", rf"\.dialogues{_I}\.nodes{_I}\.text", ("speaker_id", "narrator")
    ),
    Surface("data/dialogue/*.json", rf"\.dialogues{_I}\.nodes{_I}\.subtext"),
    Surface(
        "data/missions/*.json", rf"\.missions{_I}\.(?:description|hint|discovery_text|receipt)"
    ),
    Surface("data/journal/entries.json", rf"\.journal_entries{_I}\.text"),
    Surface("data/journal/travel_log_templates.json", r".*"),
    Surface(
        "data/ground/campaign/*.json",
        rf"\.story_triggers{_I}\.text|\.interactables{_I}\.description",
    ),
    Surface("data/combat/complications.json", r".*\.narration"),
    Surface("data/progression/timed_threads.json", r".*\.narration"),
    Surface(
        "data/crew/station_chatter.json", rf"\.chatter_lines{_I}\.text", ("category", "atmosphere")
    ),
    Surface(
        "data/narrative/dilemmas/*.json",
        rf"\.dilemmas{_I}\.outcomes{_I}\.(?:narration_summary|tier_unlocks{_I})",
    ),
    Surface("data/galaxy/locations.json", r".*\.flavor_text"),
    Surface("data/ships/modules.json", r".*\.discovery_flavor"),
    Surface("data/auctions/*_voices.json", r"\.(?:post_session|player_listing_post_session)\..*"),
    Surface("data/endings/endings.json", r".*"),
    Surface("data/narrative/lenses.json", rf"\.lenses{_I}\.core_fantasy"),
)


def _id_of(item: object) -> str | None:
    """The record's id under the first of ID_KEYS it holds as a string, else None."""
    if isinstance(item, dict):
        for key in ID_KEYS:
            value = item.get(key)
            if isinstance(value, str):
                return value
    return None


def segments(items: list[object]) -> list[str]:
    """The path segment of each list element: ``[id=X]`` for a unique id, else ``[n]``."""
    ids = [_id_of(item) for item in items]
    counts = Counter(item_id for item_id in ids if item_id is not None)
    return [
        f"[id={item_id}]" if item_id is not None and counts[item_id] == 1 else f"[{index}]"
        for index, item_id in enumerate(ids)
    ]


def walk(node: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield ``(path, value)`` for every string under node, skipping keys that start with "_"."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            if not key.startswith("_"):
                yield from walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for segment, item in zip(segments(node), node, strict=True):
            yield from walk(item, f"{path}{segment}")


def resolve(document: object, path: str) -> object | None:
    """The value at path inside document, or None when a segment no longer resolves."""
    node = document
    position = 0
    while position < len(path):
        match = _SEGMENT.match(path, position)
        if match is None:
            return None
        key, item_id, index = match.groups()
        if key is not None:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        elif item_id is not None:
            found = (
                [item for item in node if _id_of(item) == item_id] if isinstance(node, list) else []
            )
            if len(found) != 1:
                return None
            node = found[0]
        else:
            if not isinstance(node, list) or int(index) >= len(node):
                return None
            node = node[int(index)]
        position = match.end()
    return node


def parent_path(path: str) -> str:
    """The path of the object or list that holds path's value."""
    return _LAST_SEGMENT.sub("", path)


def last_key(path: str) -> str:
    """The last ``.key`` segment of path, past any trailing list segments."""
    keys = re.findall(r"\.([^.\[]+)", path)
    return keys[-1] if keys else ""


def data_files() -> list[str]:
    """Every JSON file under data/ the gates read, repo-relative, sorted."""
    files = (path.relative_to(PROJECT_ROOT).as_posix() for path in DATA_DIR.rglob("*.json"))
    return sorted(file for file in files if file not in EXCLUDED_FILES)


@cache
def load(file: str) -> object:
    """The parsed JSON of a repo-relative file (cached for the session)."""
    return json.loads((PROJECT_ROOT / file).read_text(encoding="utf-8"))


@cache
def player_facing() -> tuple[Text, ...]:
    """Every player-facing string: all of data/ less identifiers and lens authoring fields."""
    rows: list[Text] = []
    for file in data_files():
        for path, value in walk(load(file)):
            if file == "data/narrative/lenses.json" and last_key(path) in LENS_AUTHORING_KEYS:
                continue
            if _IDENTIFIER.match(value) and "{" not in value:
                continue
            rows.append(Text(file, path, value))
    return tuple(rows)


def _matches(row: Text, surface: Surface) -> bool:
    if not fnmatch(row.file, surface.files) or not re.fullmatch(surface.paths, row.path):
        return False
    if surface.where is None:
        return True
    owner = resolve(load(row.file), parent_path(row.path))
    return isinstance(owner, dict) and owner.get(surface.where[0]) == surface.where[1]


def code_narration() -> tuple[Text, ...]:
    """The narration strings that live in code, read from each module's assignment."""
    rows: list[Text] = []
    for file, name in CODE_NARRATION:
        tree = ast.parse((PROJECT_ROOT / file).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets
            ):
                value = ast.literal_eval(node.value)
                if isinstance(value, str):
                    rows.append(Text(file, name, value))
    return tuple(rows)


def _skipped(tree: ast.AST) -> set[int]:
    """The ids of docstring constants and of every node inside a logger call's arguments."""
    skipped: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                skipped.add(id(body[0].value))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _LOG_METHODS
            and isinstance(node.func.value, ast.Name)
            and "log" in node.func.value.id.lower()
        ):
            for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
                skipped |= {id(sub) for sub in ast.walk(argument)}
    return skipped


def _scoped_constants(tree: ast.Module) -> list[tuple[str, ast.Constant]]:
    """Every string constant in source order, with the dotted name of the defs around it."""
    found: list[tuple[str, ast.Constant]] = []
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, scope = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                stack.append((child, f"{scope}.{child.name}" if scope else child.name))
                continue
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                found.append((scope, child))
            stack.append((child, scope))
    return sorted(found, key=lambda item: (item[1].lineno, item[1].col_offset))


def strings_in_source(source: str) -> list[tuple[str, str]]:
    """``(path, text)`` for every string a module's code builds, in source order.

    A path is ``Scope|text``: the dotted class and function names around the string
    (``<module>`` outside any def), then the text, with ``#n`` for its n-th repeat in one
    scope. The key holds no line number, so a row stays on its string when lines move.
    """
    tree = ast.parse(source)
    skipped = _skipped(tree)
    seen: Counter[tuple[str, str]] = Counter()
    rows: list[tuple[str, str]] = []
    for scope, node in _scoped_constants(tree):
        text = node.value
        if not isinstance(text, str) or id(node) in skipped or not text.strip():
            continue
        if _IDENTIFIER.match(text) and "{" not in text:
            continue
        seen[(scope, text)] += 1
        repeat = seen[(scope, text)]
        suffix = f"#{repeat}" if repeat > 1 else ""
        rows.append((f"{scope or '<module>'}|{text}{suffix}", text))
    return rows


@cache
def code_strings() -> tuple[Text, ...]:
    """Every string built in code under CODE_DIRS, keyed by ``strings_in_source``."""
    rows: list[Text] = []
    for folder in CODE_DIRS:
        for source in sorted((PROJECT_ROOT / folder).rglob("*.py")):
            file = source.relative_to(PROJECT_ROOT).as_posix()
            for path, text in strings_in_source(source.read_text(encoding="utf-8")):
                rows.append(Text(file, path, text))
    return tuple(rows)


@cache
def narration() -> tuple[Text, ...]:
    """The narration fields of spec 5.1's table, the code frame included."""
    rows = [row for row in player_facing() if any(_matches(row, s) for s in NARRATION)]
    return tuple(rows) + code_narration()


@cache
def speech() -> tuple[Line, ...]:
    """Every spoken line with its speaker: dialogue nodes (not the narrator's), the captain's
    replies, ambient lines, interjections, overheard chatter, and the spoken files (the auction
    voices less their narration)."""
    rows: list[Line] = []
    for file in DIALOGUE_FILES:
        trees = load(file)["dialogues"]  # type: ignore[index]
        for tree_segment, tree in zip(segments(trees), trees, strict=True):
            nodes = tree["nodes"]
            for node_segment, node in zip(segments(nodes), nodes, strict=True):
                base = f".dialogues{tree_segment}.nodes{node_segment}"
                speaker = node.get("speaker_id", "")
                if speaker != "narrator":
                    rows.append(Line(file, f"{base}.text", speaker, node.get("text", "")))
                responses = node.get("responses", [])
                for reply_segment, reply in zip(segments(responses), responses, strict=True):
                    path = f"{base}.responses{reply_segment}.text"
                    rows.append(Line(file, path, "captain", reply.get("text", "")))
    ambient_file = "data/crew/ambient_dialogue.json"
    ambient = load(ambient_file)["ambient_lines"]  # type: ignore[index]
    for segment, line in zip(segments(ambient), ambient, strict=True):
        path = f".ambient_lines{segment}.text"
        rows.append(Line(ambient_file, path, line.get("crew_id", ""), line.get("text", "")))
    banks_file = "data/combat/crew_interjections.json"
    banks = load(banks_file)["interjections"]  # type: ignore[index]
    for bank_segment, bank in zip(segments(banks), banks, strict=True):
        for line_segment, text in zip(segments(bank["lines"]), bank["lines"], strict=True):
            path = f".interjections{bank_segment}.lines{line_segment}"
            rows.append(Line(banks_file, path, bank.get("crew_id", ""), text))
    chatter_file = "data/crew/station_chatter.json"
    chatter = load(chatter_file)["chatter_lines"]  # type: ignore[index]
    for segment, line in zip(segments(chatter), chatter, strict=True):
        if line.get("category") != "atmosphere":
            rows.append(Line(chatter_file, f".chatter_lines{segment}.text", "", line["text"]))
    for file in SPOKEN_FILES:
        for path, value in walk(load(file)):
            if " " in value and not path.startswith(AUCTION_NARRATION):
                rows.append(Line(file, path, "", value))
    return tuple(rows)


@cache
def option_texts() -> tuple[Text, ...]:
    """The captain's replies and the encounter choice labels, where bracket tags live."""
    replies = tuple(Text(r.file, r.path, r.text) for r in speech() if r.speaker == "captain")
    labels = tuple(
        row
        for row in player_facing()
        if fnmatch(row.file, "data/encounters/*.json")
        and re.fullmatch(rf"\.encounters{_I}\.choices{_I}\.label", row.path)
    )
    return replies + labels


@cache
def trees() -> tuple[tuple[str, str, dict[str, object]], ...]:
    """Every dialogue tree as ``(file, path, tree)``."""
    rows: list[tuple[str, str, dict[str, object]]] = []
    for file in DIALOGUE_FILES:
        found = load(file)["dialogues"]  # type: ignore[index]
        for segment, tree in zip(segments(found), found, strict=True):
            rows.append((file, f".dialogues{segment}", tree))
    return tuple(rows)


@cache
def people() -> tuple[Person, ...]:
    """The person records G4's near-collision measures compare (spec 5.1, as scoped in W1)."""
    sources = (
        ("data/characters/npcs.json", "npcs", "home_system_id"),
        ("data/crew/crew_members.json", "crew_templates", "home_system_id"),
        ("data/combat/captains.json", "captains", "home_sector"),
    )
    rows: list[Person] = []
    for file, key, system_key in sources:
        records = load(file)[key]  # type: ignore[index]
        for segment, record in zip(segments(records), records, strict=True):
            rows.append(
                Person(file, f".{key}{segment}.name", record["name"], record.get(system_key) or "")
            )
    for path in sorted((DATA_DIR / "politics").glob("*_disputes.json")):
        file = path.relative_to(PROJECT_ROOT).as_posix()
        disputes = load(file)["disputes"]  # type: ignore[index]
        for dispute_segment, dispute in zip(segments(disputes), disputes, strict=True):
            delegates = dispute.get("delegates", [])
            for segment, delegate in zip(segments(delegates), delegates, strict=True):
                path_text = f".disputes{dispute_segment}.delegates{segment}.name"
                rows.append(Person(file, path_text, delegate["name"], ""))
    return tuple(rows)
