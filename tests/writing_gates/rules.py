"""The prose gates G1 to G11 and G13 (writing discipline spec 5.1).

Each gate is a function that returns today's offences. An offence is keyed by gate, rule,
file and path, which is the key of its allowlist row (``tests/writing_gates/allowlist.json``).
The regexes are the spec's, verbatim where it prints one. The gates whose scope is every
player-facing string (G1 to G3, G4's banned names, G5's pronoun and address, G10, and G11's
"warp", "navy" and Marcus's gesture) read the strings built in code too; G5's token rule reads
data only, since the registry names data files.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from tests.writing_gates import surfaces
from tests.writing_gates.registry import tokens_for

ACT_VERBS_FILE = Path(__file__).resolve().parent / "act_verbs.txt"


@dataclass(frozen=True)
class Offence:
    """One string that breaks one rule of one gate."""

    gate: str
    rule: str
    file: str
    path: str
    text: str
    match: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        """The allowlist key: gate, rule, file, path."""
        return (self.gate, self.rule, self.file, self.path)


# G1: U+2014 anywhere; U+2013 except between digits; a double hyphen, or a spaced hyphen
# between words, used as a dash; the BB-35 splice.
G1_FORMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("em dash", re.compile("\N{EM DASH}")),
    ("en dash", re.compile(r"(?<!\d)\N{EN DASH}|\N{EN DASH}(?!\d)")),
    ("double hyphen", re.compile(r"--")),
    ("spaced hyphen", re.compile(r"(?<=\w) - (?=\w)")),
    ("splice", re.compile(r"\S \. \S")),
)
G2_PAIRED_NEGATION = re.compile(r"(?i)\bno \w+(?: \w+)?\s*[,.;:\-\N{EN DASH}\N{EM DASH}]+\s*no \w+")
G3_WORDS: tuple[tuple[str, str], ...] = (
    ("couldn't help but", r"couldn['\N{RIGHT SINGLE QUOTATION MARK}]t help but"),
    ("a testament to", r"an? testaments? to"),
    ("remarkable", r"remarkabl[ey]"),
    ("wonderful", r"wonderful(?:ly)?"),
    ("delve", r"delv(?:e|es|ed|ing)"),
    ("tapestry", r"tapestr(?:y|ies)"),
    ("amidst", r"amidst"),
    ("whilst", r"whilst"),
    ("henceforth", r"henceforth"),
    ("nonetheless", r"nonetheless"),
    ("juxtaposition", r"juxtapos(?:e|es|ed|ing|ition|itions)"),
    ("visceral", r"visceral(?:ly)?"),
    ("palpable", r"palpabl[ey]"),
    ("resonate", r"resonat(?:e|es|ed|ing|ion)"),
    ("nuance", r"nuanc(?:e|es|ed)"),
)
BANNED_NAMES = ("yara", "elara", "kael", "mara", "lydia", "clive", "magnus", "ambrose")
G4_BANNED = re.compile(rf"(?i)\b(?:{'|'.join(BANNED_NAMES)})\b")
# Words dropped before a person's first name when G4 compares names.
TITLES = frozenset(
    "admiral auntie brother broker captain chaplain chief commander councillor cpl"
    " customs delegate director doctor dr elder father foreman inspector magistrate mayor"
    " mother mr mrs ms officer old professor representative sergeant sgt sister the uncle".split()
)
G5_PRONOUN = re.compile(r"(?i)\b(?:he|him|his|himself|she|her|hers|herself)\b")
G5_CAPTAIN = re.compile(r"(?i)\bthe captain\b|\{player\}")
G5_VOCATIVE = re.compile(
    r"(?i)(?:^|[,.!?;:]\s+|['\"])(sir|ma'am|madam|son|lad|lass|girl|boy|mister|miss"
    r"|sweetheart|darling)(?=\s*[,.!?])"
)
BRACE = re.compile(r"\{([^{}]*)\}")
# A verb token's body is two forms around one pipe (spec 2.5); a BRACE body holds no brace.
VERB_TOKEN = re.compile(r"v:[^|]*\|[^|]*")
# A record token's body is a reward kind and a mission id (spec 3.7).
RECORD_TOKEN = re.compile(r"(pay|fee):[a-z0-9_]+")
G6_FILTER_VERBS = re.compile(
    r"(?i)\byou(?:'d|'ll|'ve| would| will| can't| could)? (?:\w+ly )?(?:notice|realize"
    r"|remember|recall|sense|feel|wonder|decide|see that|can't help)"
)
G7_BODY_TELLS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("your body", re.compile(r"(?i)\byour (?:heart|pulse|stomach|breath|throat|chest)\b")),
    ("shaking hands", re.compile(r"(?i)\byour hands? (?:are |is )?shak(?:e|es|ing)\b")),
)
G8_FEELINGS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("you feel", re.compile(r"(?i)\byou (?:feel|felt) \w+")),
    ("you'd rather", re.compile(r"(?i)\byou(?:'d| would) rather\b")),
    ("not your problem", re.compile(r"(?i)\bnot your (?:problem|business|concern|fault)\b")),
    ("you can't", re.compile(r"(?i)\byou can't (?:afford|stop|help)\b")),
    ("you don't", re.compile(r"(?i)\byou don't (?:owe|need|want)\b")),
    ("you have earned", re.compile(r"(?i)\byou(?: have|'ve) earned\b")),
    ("makes you nervous", re.compile(r"(?i)\bmakes? you nervous\b")),
    ("you prefer", re.compile(r"(?i)\byou (?:prefer|won't let)\b")),
)
TAG = re.compile(r"\[([^\]]+)\]")
MOOD_WORDS = frozenset(
    "feel feels feeling heavy angry sad sarcastic nervous annoyed happy scared guilty"
    " worried".split()
)
# The registered skill checks, kept equal to spacegame.models.social.SOCIAL_SKILL_DEFINITIONS
# by test_writing_gates_engine.py::TestG9Tags::test_the_skills_match_the_social_model.
SKILLS = frozenset(
    "persuasion intimidation observation deception technical piloting leadership".split()
)
KNOWN_TAGS = frozenset({"say nothing", "leave"})
# What may follow an [Observation N] check besides an act verb: a quote mark, or another
# bracket tag, which is judged on its own.
OBSERVATION_FOLLOWERS = (
    "[",
    '"',
    "'",
    "\N{LEFT DOUBLE QUOTATION MARK}",
    "\N{LEFT SINGLE QUOTATION MARK}",
)
G10_THE_PLAYER = re.compile(r"(?i)\bthe player\b")
G11_WARP = re.compile(r"(?i)\bwarp\b")
G11_NAVY = re.compile(r"(?i)\b(?:navy|naval)\b")
G11_CAPTAIN = re.compile(r"\bCaptain\b")
G11_LOOKING_UP = re.compile(r"(?i)\b(?:without looking up|(?:does|do|did)(?: not|n't) look up)\b")
G11_PRICE = re.compile(r"(?i)\b\d[\d,]*\s?(?:CR|credits?)\b")
MARCUS = "marcus_jin"
# G13: no run of more than this many consecutive nodes without an exit.
MAX_RUN_WITHOUT_EXIT = 4
# G13's disposition half applies to a tree of at least this many nodes.
MIN_NODES_FOR_CHANGE = 4


def _first(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(0) if match else ""


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s]


@cache
def act_verbs() -> frozenset[str]:
    """The act-verb list: one lowercase verb a line, "#" lines are comments."""
    lines = ACT_VERBS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def _every_string() -> tuple[surfaces.Text, ...]:
    """Every player-facing string: the data's, then the strings built in code."""
    return surfaces.player_facing() + surfaces.code_strings()


@cache
def marcus_lines() -> frozenset[tuple[str, str]]:
    """Every string that is Marcus Jin's own: his spoken lines, and the Reads on his nodes."""
    own = {(line.file, line.path) for line in surfaces.speech() if line.speaker == MARCUS}
    for row in surfaces.narration():
        if not row.path.endswith(".subtext"):
            continue
        node = surfaces.resolve(surfaces.load(row.file), surfaces.parent_path(row.path))
        if isinstance(node, dict) and node.get("speaker_id") == MARCUS:
            own.add((row.file, row.path))
    return frozenset(own)


def g1() -> list[Offence]:
    """G1, dashes, over every player-facing string, the strings built in code included."""
    found: list[Offence] = []
    for row in _every_string():
        for rule, pattern in G1_FORMS:
            if pattern.search(row.text):
                found.append(
                    Offence("G1", rule, row.file, row.path, row.text, _first(pattern, row.text))
                )
    return found


def g2() -> list[Offence]:
    """G2, paired negation, over every player-facing string."""
    return [
        Offence("G2", "paired negation", r.file, r.path, r.text, _first(G2_PAIRED_NEGATION, r.text))
        for r in _every_string()
        if G2_PAIRED_NEGATION.search(r.text)
    ]


def g3() -> list[Offence]:
    """G3, tells: whole words, any case, with inflections."""
    found: list[Offence] = []
    for row in _every_string():
        for rule, word in G3_WORDS:
            pattern = re.compile(rf"(?i)\b{word}\b")
            if pattern.search(row.text):
                found.append(
                    Offence("G3", rule, row.file, row.path, row.text, _first(pattern, row.text))
                )
    return found


def first_name(name: str) -> str:
    """A name's first word after any titles, case-folded, quotes and nicknames dropped."""
    words = re.sub(r"\"[^\"]*\"|'[^']*'(?=\s)", " ", name).split()
    while words and words[0].lower().strip(".,") in TITLES:
        words = words[1:]
    return (words[0] if words else name).lower().strip(".,'")


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two strings."""
    row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        previous, row[0] = row[0], i
        for j, char_b in enumerate(b, 1):
            previous, row[j] = (
                row[j],
                min(row[j] + 1, row[j - 1] + 1, previous + (char_a != char_b)),
            )
    return row[-1]


def _near(a: surfaces.Person, b: surfaces.Person) -> str:
    """Why two person names collide (spec G4), or "" when they do not."""
    fa, fb = first_name(a.name), first_name(b.name)
    reasons: list[str] = []
    if len(fa) >= 4 and len(fb) >= 4 and fa[:4] == fb[:4]:
        reasons.append("shared stem")
    distance = edit_distance(fa, fb)
    if distance <= 2:
        reasons.append(f"edit distance {distance}")
    if a.system and a.system == b.system and fa[:2] == fb[:2]:
        reasons.append("same system, same first two letters")
    return ", ".join(reasons)


def name_pairs() -> dict[str, tuple[str, str, str]]:
    """Every colliding pair of first names: ``"a|b"`` to (one name, the other, the reason)."""
    distinct: dict[str, surfaces.Person] = {}
    for person in surfaces.people():
        distinct.setdefault(person.name, person)
    pairs: dict[str, tuple[str, str, str]] = {}
    for a, b in itertools.combinations(sorted(distinct.values(), key=lambda p: p.name), 2):
        reason = _near(a, b)
        if reason:
            key = "|".join(sorted((first_name(a.name), first_name(b.name))))
            pairs.setdefault(key, (a.name, b.name, reason))
    return pairs


def g4() -> list[Offence]:
    """G4, names: the banned names in any string, code-built included, and near-collisions
    among person names."""
    found = [
        Offence("G4", "banned name", r.file, r.path, r.text, _first(G4_BANNED, r.text))
        for r in _every_string()
        if G4_BANNED.search(r.text)
    ]
    for key, (name_a, name_b, reason) in sorted(name_pairs().items()):
        found.append(
            Offence("G4", "near collision", "(person names)", key, f"{name_a} / {name_b}", reason)
        )
    return found


def token_names(text: str) -> list[str]:
    """The name of every ``{...}`` in text, as the G5 registry check sees it.

    A brace is named ``v`` only when its body has the verb token's form, ``v:`` and two forms
    around exactly one pipe (spec 2.5). A body whose part before the first colon is ``v`` but
    that lacks that form is named by the whole brace, braces kept (``{v:is}``), so it equals no
    registry name and fails G5 as an unknown token on every surface, as the renderer would
    leave it unfilled (spec 2.7). A record token (``pay:`` or ``fee:`` and a mission id) is
    named by its kind. Any other body is named as written.

    Args:
        text: The string to scan.

    Returns:
        One name per brace, in order.
    """
    names: list[str] = []
    for body in BRACE.findall(text):
        if VERB_TOKEN.fullmatch(body):
            names.append("v")
        elif body.split(":", 1)[0] == "v":
            names.append("{" + body + "}")
        elif RECORD_TOKEN.fullmatch(body):
            names.append(body.split(":", 1)[0])
        else:
            names.append(body)
    return names


def g5() -> list[Offence]:
    """G5, the captain's pronoun, address, and tokens (the tokens in data files only)."""
    found: list[Offence] = []
    for row in _every_string():
        for sentence in _sentences(row.text):
            if G5_CAPTAIN.search(sentence) and G5_PRONOUN.search(sentence):
                found.append(Offence("G5", "pronoun", row.file, row.path, row.text, sentence))
                break
        match = G5_VOCATIVE.search(row.text)
        if match:
            found.append(Offence("G5", "vocative", row.file, row.path, row.text, match.group(1)))
        if not row.file.startswith("data/"):
            continue  # the registry names data files; code fills its own braces
        allowed = tokens_for(row.file)
        unknown = [name for name in token_names(row.text) if name not in allowed]
        if unknown:
            found.append(Offence("G5", "token", row.file, row.path, row.text, ", ".join(unknown)))
    return found


def _narration_gate(gate: str, rules: tuple[tuple[str, re.Pattern[str]], ...]) -> list[Offence]:
    found: list[Offence] = []
    for row in surfaces.narration():
        for rule, pattern in rules:
            if pattern.search(row.text):
                found.append(
                    Offence(gate, rule, row.file, row.path, row.text, _first(pattern, row.text))
                )
    return found


def g6() -> list[Offence]:
    """G6, filter verbs, over the narration fields."""
    return _narration_gate("G6", (("filter verb", G6_FILTER_VERBS),))


def g7() -> list[Offence]:
    """G7, body tells, over the narration fields."""
    return _narration_gate("G7", G7_BODY_TELLS)


def g8() -> list[Offence]:
    """G8, feelings and motives, over the narration fields and the option hints in them."""
    return _narration_gate("G8", G8_FEELINGS)


def tag_verdict(tag: str) -> str:
    """Why a bracket tag fails G9 ("mood" or "not an act"), or "" when it passes."""
    words = re.findall(r"[a-z']+", tag.lower())
    if set(words) & MOOD_WORDS:
        return "mood"
    if re.fullmatch(r"[A-Z][a-z]+ \d+", tag) and words and words[0] in SKILLS:
        return ""
    if tag.lower().rstrip(".") in KNOWN_TAGS:
        return ""
    if words and words[0] in act_verbs():
        return ""
    return "not an act"


def option_verdict(text: str) -> tuple[str, str]:
    """The first bracket tag of an option that fails G9 and why, or ("", "") (spec 5.1, G9).

    A tag fails on a mood word, or when it is neither a registered skill check, a known tag,
    nor an act. An ``[Observation N]`` check passes only when quoted words or an act follow
    it: a quote mark, another bracket tag (judged on its own), or a verb from the act-verb
    list.
    """
    for match in TAG.finditer(text):
        tag = match.group(1).strip()
        verdict = tag_verdict(tag)
        if not verdict and re.fullmatch(r"Observation \d+", tag):
            rest = text[match.end() :].lstrip()
            words = re.findall(r"[a-z']+", rest.lower())
            followed_by_an_act = bool(words) and words[0] in act_verbs()
            if not rest.startswith(OBSERVATION_FOLLOWERS) and not followed_by_an_act:
                verdict = "observation unquoted"
        if verdict:
            return verdict, match.group(0)
    return "", ""


def g9() -> list[Offence]:
    """G9, the bracket tags on the captain's replies and choice labels (``option_verdict``)."""
    found: list[Offence] = []
    for row in surfaces.option_texts():
        verdict, tag = option_verdict(row.text)
        if verdict:
            found.append(Offence("G9", verdict, row.file, row.path, row.text, tag))
    return found


def g10() -> list[Offence]:
    """G10, "the player", over every player-facing string."""
    return [
        Offence("G10", "the player", r.file, r.path, r.text, _first(G10_THE_PLAYER, r.text))
        for r in _every_string()
        if G10_THE_PLAYER.search(r.text)
    ]


def g11() -> list[Offence]:
    """G11, the lexicon: warp and navy, and Marcus's gesture in any form outside his own lines,
    in every string; in speech, Marcus's "Captain" and prices."""
    found: list[Offence] = []
    for row in _every_string():
        for rule, pattern in (("warp", G11_WARP), ("navy", G11_NAVY)):
            if pattern.search(row.text):
                found.append(
                    Offence("G11", rule, row.file, row.path, row.text, _first(pattern, row.text))
                )
        if (row.file, row.path) not in marcus_lines() and G11_LOOKING_UP.search(row.text):
            match = _first(G11_LOOKING_UP, row.text)
            found.append(Offence("G11", "without looking up", row.file, row.path, row.text, match))
    for line in surfaces.speech():
        if line.speaker == MARCUS and G11_CAPTAIN.search(line.text):
            found.append(
                Offence("G11", "captain from marcus", line.file, line.path, line.text, "Captain")
            )
        if G11_PRICE.search(line.text):
            match = _first(G11_PRICE, line.text)
            found.append(Offence("G11", "price in speech", line.file, line.path, line.text, match))
    return found


def _is_exit(reply: dict[str, object]) -> bool:
    check = reply.get("skill_check")
    branches = (
        (check.get("success_node_id"), check.get("failure_node_id"))
        if isinstance(check, dict)
        else ()
    )
    return reply.get("next_node_id") is None and not any(branches)


def _successors(node: dict[str, object], ids: set[str]) -> list[str]:
    found: list[str] = []
    for reply in node.get("responses", []):  # type: ignore[attr-defined]
        check = reply.get("skill_check")
        if isinstance(check, dict):
            targets = [check.get("success_node_id"), check.get("failure_node_id")]
        else:
            targets = [reply.get("next_node_id")]
        found += [t for t in targets if isinstance(t, str) and t in ids and t not in found]
    return found


def longest_run_without_exit(tree: dict[str, object]) -> float:
    """The longest run of consecutive reachable nodes with no exit; a loop of them is inf."""
    nodes = {node["id"]: node for node in tree["nodes"]}  # type: ignore[attr-defined]
    ids = set(nodes)
    memo: dict[str, float] = {}
    on_path: set[str] = set()

    def run(node_id: str) -> float:
        node = nodes[node_id]
        replies = node.get("responses", [])
        if not replies or any(_is_exit(reply) for reply in replies):
            return 0
        if node_id in memo:
            return memo[node_id]
        if node_id in on_path:
            return float("inf")
        on_path.add(node_id)
        best = 1 + max((run(n) for n in _successors(node, ids)), default=0)
        on_path.discard(node_id)
        memo[node_id] = best
        return best

    reachable: set[str] = set()
    stack: list[str] = [tree["start_node_id"]]  # type: ignore[list-item]
    while stack:
        node_id = stack.pop()
        if node_id in reachable or node_id not in nodes:
            continue
        reachable.add(node_id)
        stack.extend(_successors(nodes[node_id], ids))
    return max((run(node_id) for node_id in reachable), default=0)


def change_verdict(tree: dict[str, object]) -> str:
    """Why a tree fails G13's disposition half, or "" (spec 5.1, G13).

    The half is live for a tree once it marks a node ``"change": true``: a tree of four
    nodes or more marks one node, and that node carries the disposition change.
    """
    nodes: list[dict[str, object]] = tree["nodes"]  # type: ignore[assignment]
    marked = [node for node in nodes if node.get("change") is True]
    if len(nodes) < MIN_NODES_FOR_CHANGE or not marked:
        return ""
    if len(marked) > 1:
        return f"{len(marked)} nodes marked change"
    replies: list[dict[str, object]] = marked[0].get("responses", [])  # type: ignore[assignment]
    if not any(reply.get("disposition_change") for reply in replies):
        return f"{marked[0]['id']} carries no disposition change"
    return ""


def g13() -> list[Offence]:
    """G13: no run of more than four nodes without an exit, and the change node's disposition."""
    found: list[Offence] = []
    for file, path, tree in surfaces.trees():
        longest = longest_run_without_exit(tree)
        if longest > MAX_RUN_WITHOUT_EXIT:
            shown = "a loop" if longest == float("inf") else f"{int(longest)} nodes"
            found.append(Offence("G13", "exits", file, path, str(tree["id"]), shown))
        verdict = change_verdict(tree)
        if verdict:
            found.append(Offence("G13", "change", file, path, str(tree["id"]), verdict))
    return found


GATES: dict[str, Callable[[], list[Offence]]] = {
    "G1": g1,
    "G2": g2,
    "G3": g3,
    "G4": g4,
    "G5": g5,
    "G6": g6,
    "G7": g7,
    "G8": g8,
    "G9": g9,
    "G10": g10,
    "G11": g11,
    "G13": g13,
}


def offences(gate: str) -> list[Offence]:
    """Today's offences of one gate."""
    return GATES[gate]()
