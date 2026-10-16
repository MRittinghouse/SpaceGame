"""Plan W2's worklist for the narrator audit (writing-discipline spec 9.4; plan W2-S).

The audit (aurelia's docs/design/writing-discipline/audit.md) gives each finding as a verbatim
excerpt of a shipped string and a suggested rewrite. ``build`` reads the audit, the data and the
gates' allowlist and writes one entry for each string W2 rewrites or leaves to another owner:
the old line, the audit's rows on it, the gate rows on it, the flags plan W2-S's rulings name, a
disposition (adopt: the tool composed the audit's mechanical rewrite; draft: a writer writes the
line; skip: another owner keeps it) and the new line. ``draft`` merges a writer's lines,
``apply`` swaps finished lines into the data keeping each file's escaping and line endings
(a redraft replaces whatever line the data holds), ``check`` proves finished entries, ``files``
lists the files, and ``read`` renders the before-and-after reading copy the author reads before
W2 merges. ``residue`` is the check that outlives W2: no audit excerpt has come back.

Usage, from the repo root:
    python -m tools.writing.w2_audit build --audit ../aurelia/docs/design/writing-discipline/audit.md
    python -m tools.writing.w2_audit draft --from ../w2-drafts/task02.json
    python -m tools.writing.w2_audit apply --file data/encounters/generic.json
    python -m tools.writing.w2_audit check [--file data/encounters/generic.json]
    python -m tools.writing.w2_audit files
    python -m tools.writing.w2_audit read --out ../w2-read.md [--file data/encounters/generic.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatchcase
from itertools import pairwise
from pathlib import Path

from tests.writing_gates import allowlist, surfaces

WORKLIST = Path(__file__).resolve().parent / "w2_rows.json"
ROOT = surfaces.PROJECT_ROOT
ADOPT = "adopt"
DRAFT = "draft"
SKIP = "skip"
# The flags whose lines a writer drafts whatever the audit suggests (plan W2-S's rulings).
DRAFT_FLAGS = frozenset({"DECIDES", "KOREN", "KORVATH", "LOG", "PRONOUN", "SCRAPING", "SENSATION"})
# (owner, file glob, gate path part): the strings W2 leaves to another owner.
SKIPS: tuple[tuple[str, str, str], ...] = (
    ("archive", "data/narrative/*", ""),
    ("W3", "data/journal/entries.json", "[id=auto_m13_oren]"),
    ("W3", "data/journal/entries.json", "[id=auto_iron_betrayal]"),
    ("W3", "data/missions/*.json", "[id=iron_delivery]"),
    ("SP10", "data/dialogue/dialogues.json", "[id=the_collapse_sequence]"),
)
# (flag, gate path part): the entries a ruling names.
FLAGS: tuple[tuple[str, str], ...] = (
    ("DECIDES", "[id=humor_space_junk_art_01].choices[id=salvage]"),
    ("DECIDES", "[id=lore_earth_broadcast_01].choices[id=record]"),
    ("DECIDES", "[id=collective_artifact_01].choices[id=ask_about_artifact]"),
    ("DECIDES", "[id=collective_nova_test_01].choices[id=ask_details]"),
    ("DECIDES", "[id=bait_patrol_officer_01].choices[id=verify_id]"),
    ("DECIDES", "[id=trader_contraband_01].choices[id=verify]"),
    ("DECIDES", "[id=bait_mining_rig_01].choices[id=scan_drive]"),
    ("KORVATH", "[id=humor_cooking_show_01].choices[id=call_in].outcome"),
    ("KORVATH", "[id=humor_wrong_number_01].choices[id=play_along].outcome"),
    ("KOREN", "[id=elena_charting_stars]"),
    ("KOREN", "[id=elena_old_charts]"),
    ("PRONOUN", "[id=ransom_guild_audit_01]"),
    ("SCRAPING", ".major_trade[4]"),
    ("SENSATION", "[id=campaign_anomaly_deepens_01].choices[id=approach].outcome"),
)
LOG_FILES = frozenset({"data/journal/entries.json", "data/journal/travel_log_templates.json"})
# Gate rows a composed audit fix would leave standing on its line: a writer clears them too.
_WRITER_GATES = frozenset({"G1", "G2", "G3", "G9", "G10"})
_WRITER_RULES = frozenset({"G11:warp", "G11:navy", "G11:without looking up"})
# Five words in a row shared by a suggestion and the line around its excerpt: a restatement.
_SHARED_WORDS = 5


@dataclass(frozen=True)
class Named:
    """A line the hand-offs, the impact inventory or a plan W2-S ruling names with no audit row:
    the gate path parts it holds, the suffix its path ends with (the record's id and field, so an
    objective's own description never matches), and its exact text where the path alone is not
    enough."""

    parts: tuple[str, ...]
    suffix: str
    text: str
    why: str


_FAREWELL = "a spoken farewell in brackets (hand-offs, the writing pass)"
NAMED: tuple[Named, ...] = (
    Named((), "[id=elena_old_charts].description", "", "Koren is she everywhere (impact 6.8)"),
    Named(
        (),
        "[id=the_foremans_son].description",
        "",
        "the last sentence states Marcus's inner state (hand-offs)",
    ),
    Named((), "[id=marcus_steel_holds].description", "", "impact 7.58"),
    Named(
        (),
        "[id=reinforcement_arrival].description",
        "",
        "the words ruling: 'warps in', a travel warp G11's whole word misses",
    ),
    Named(("[id=arna_post_completion]",), "[id=retire_early].subtext", "", "impact 7.75"),
    Named(("[id=arna_post_ore_tip]",), "[id=about_site].subtext", "", "impact 7.77"),
    Named(("[id=arna_post_refining]",), "[id=start].subtext", "", "impact 7.80"),
    Named(("[id=arna_stays_closeout]",), "[id=farewell].subtext", "", "impact 7.92"),
    Named(
        ("[id=bait_mining_rig_01]",),
        "[id=scan_drive].failure_outcome.description",
        "",
        "spec 9.4: narration that decides for the player",
    ),
    Named(("[id=arna_post_payback]", "[id=what_now]"), "", "[Take care of yourself.]", _FAREWELL),
    Named(
        ("[id=arna_last_freight_out_closeout]", "[id=brother]"),
        "",
        "[Take care of yourself.]",
        _FAREWELL,
    ),
    Named(
        ("[id=arna_last_freight_out_closeout]", "[id=help_offer]"),
        "",
        "[Take care of yourself.]",
        _FAREWELL,
    ),
    Named(("[id=arna_stays_closeout]", "[id=check]"), "", "[Take care.]", _FAREWELL),
    Named(("[id=merchant_delivery]", "[id=odom_arna_branch_a]"), "", "[Leave it.]", _FAREWELL),
    Named(("[id=merchant_delivery]", "[id=odom_arna_branch_b]"), "", "[Leave it.]", _FAREWELL),
    Named(("[id=merchant_delivery]", "[id=odom_arna_branch_c]"), "", "[Leave it.]", _FAREWELL),
)
_SECTION = re.compile(r"^### `\.\./SpaceGame/(data/[^`]+)` \(\d+\)")
_END_THERE = "(end there)"
_CUT_END = re.compile(r'^\(cut; end on "(.+)"\)$')
_CUT_OPEN = re.compile(r'^\(cut; open on "(.+)"\)$')
_SPOKEN = re.compile(r"^\[([^\[\]]+[.?!])\]$")
# Quote marks that close a speech the cut ends on.
_CLOSERS = "'\"’”"
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_BRACE = re.compile(r"\{[^{}]*\}")
_TOKEN = re.compile(r"\.([^.\[]+)|\[id=([^\]]+)\]|\[(\d+)\]")


@dataclass
class Row:
    """One audit finding on a string."""

    row: int
    classes: str
    excerpt: str
    suggestion: str
    note: str


@dataclass
class Entry:
    """One string W2 rewrites or leaves to another owner."""

    file: str
    gate_path: str
    old: str
    new: str = ""
    disposition: str = DRAFT
    owner: str = ""
    flags: list[str] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)
    gates: list[str] = field(default_factory=list)
    why: str = ""

    @property
    def id(self) -> str:
        """The entry's key: its file and its gate path."""
        return f"{self.file}|{self.gate_path}"


def parse_audit(text: str) -> list[tuple[str, str, Row]]:
    """Every audit row as (repo-relative file, audit path, row)."""
    found: list[tuple[str, str, Row]] = []
    file = ""
    for line in text.splitlines():
        section = _SECTION.match(line)
        if section:
            file = section.group(1)
            continue
        if not file or not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].isdigit():
            row = Row(int(cells[0]), cells[2], cells[3], cells[4], cells[5])
            found.append((file, cells[1].strip("`"), row))
    return found


def _clean(text: str) -> str:
    text = re.sub(r" {2,}", " ", text).strip()
    return re.sub(r" +([.,;:!?])", r"\1", text)


def _starts_a_sentence(text: str, index: int) -> bool:
    before = text[:index].rstrip(" ")
    return before == "" or before[-1] in ".!?\n"


def _whole_sentences(text: str, at: int, excerpt: str) -> bool:
    """Whether excerpt, found at at, opens a sentence and ends one."""
    end = at + len(excerpt)
    closes = excerpt.rstrip(_CLOSERS).endswith((".", "!", "?"))
    return _starts_a_sentence(text, at) and closes and (end == len(text) or text[end] in " \n")


def compose(text: str, excerpt: str, suggestion: str) -> str | None:
    """text with one audit row's mechanical rewrite applied: a plain replacement or one that ends
    there (each only where the excerpt is whole sentences), or a cut that ends on or opens on a
    quoted phrase. None when the suggestion needs a writer."""
    at = text.find(excerpt)
    if at < 0:
        return None
    suggestion = suggestion.strip()
    cut_end = _CUT_END.match(suggestion)
    if cut_end:
        end = text.find(cut_end.group(1))
        stop = end + len(cut_end.group(1))
        while 0 <= end and stop < len(text) and text[stop] in _CLOSERS:
            stop += 1
        return _clean(text[:stop]) if end >= 0 and at >= stop else None
    cut_open = _CUT_OPEN.match(suggestion)
    if cut_open:
        start = text.find(cut_open.group(1))
        return _clean(text[start:]) if start >= 0 and at + len(excerpt) <= start else None
    if not _whole_sentences(text, at, excerpt):
        return None
    ends_there = suggestion.endswith(_END_THERE)
    line = suggestion[: -len(_END_THERE)].strip() if ends_there else suggestion
    rest = text[:at] + text[at + len(excerpt) :]
    # A note in parentheses, or a suggestion that restates the line around it, needs a writer.
    if "(" in line or _restates(line, rest):
        return None
    if ends_there:
        return _clean(text[:at] + line)
    return _clean(text[:at] + line + text[at + len(excerpt) :])


def _restates(line: str, rest: str) -> bool:
    """Whether line repeats rest, whole or by _SHARED_WORDS words in a row."""
    if line in rest:
        return True
    words = re.findall(r"[\w']+", line.lower())
    around = " ".join(re.findall(r"[\w']+", rest.lower()))
    return any(
        " ".join(words[i : i + _SHARED_WORDS]) in around
        for i in range(len(words) - _SHARED_WORDS + 1)
    )


def _needs_gate_fix(entry: Entry) -> bool:
    """Whether a gate row on entry's line is one a composed audit fix would leave standing."""
    return any(tag.split(":")[0] in _WRITER_GATES or tag in _WRITER_RULES for tag in entry.gates)


def _repeats(text: str) -> bool:
    """Whether a sentence of text appears twice."""
    sentences = [part for part in _SENTENCE_BREAK.split(text) if part]
    return len(sentences) != len(set(sentences))


def _awkward(text: str) -> bool:
    """Whether a composed line reads broken: a sentence that opens in lower case, or two sentences
    in a row that open on the same two words ("Log the coordinates. Log the coordinates and ...")."""
    sentences = [part for part in _SENTENCE_BREAK.split(text) if part]
    if any(sentence.lstrip(_CLOSERS)[:1].islower() for sentence in sentences):
        return True
    openings = [" ".join(re.findall(r"[\w']+", sentence.lower())[:2]) for sentence in sentences]
    return any(first == second for first, second in pairwise(openings))


def _is_hint(entry: Entry) -> bool:
    return ".choices[" in entry.gate_path and entry.gate_path.endswith("].description")


def _new_figures(old: str, new: str) -> bool:
    """Whether new holds a number old does not (spec 3.7: a figure is a record, never written in)."""
    figures = re.compile(r"\d[\d,]*")
    return bool(set(figures.findall(new)) - set(figures.findall(old)))


def decide(entry: Entry) -> None:
    """Set entry's disposition and, where the tool can compose it, its new line."""
    if entry.disposition == SKIP:
        return
    if DRAFT_FLAGS.intersection(entry.flags) or entry.why:
        entry.disposition, entry.new = DRAFT, ""
        return
    if entry.rows and _needs_gate_fix(entry):
        entry.disposition, entry.new = DRAFT, ""
        return
    if not entry.rows:
        spoken = _SPOKEN.match(entry.old)
        if entry.gates == ["G9:not an act"] and spoken:
            entry.disposition, entry.new = ADOPT, spoken.group(1)
        else:
            entry.disposition, entry.new = DRAFT, ""
        return
    # The audit's hint suggestions replace the whole hint: one adopts only where its excerpt is it.
    if _is_hint(entry) and [row.excerpt for row in entry.rows] != [entry.old.strip()]:
        entry.disposition, entry.new = DRAFT, ""
        return
    line: str | None = entry.old
    for row in entry.rows:
        if line is not None and row.excerpt in line:
            line = compose(line, row.excerpt, row.suggestion)
    if line is None or line == entry.old or _repeats(line) or _awkward(line):
        entry.disposition, entry.new = DRAFT, ""
    elif _new_figures(entry.old, line):
        entry.disposition, entry.new = DRAFT, ""
    else:
        entry.disposition, entry.new = ADOPT, line


def _tokens(path: str) -> list[str]:
    return [key or item_id or index for key, item_id, index in _TOKEN.findall(path)]


def _fits(path: str, parts: list[str]) -> bool:
    """Whether a gate path ends with the audit path's parts: a key or an id matches its own
    name, and an audit index matches any element (the audit numbers a list the gates key by id)."""
    tokens = _tokens(path)
    if len(tokens) < len(parts):
        return False
    tail = tokens[len(tokens) - len(parts) :]
    return all(part == token or part.isdigit() for part, token in zip(parts, tail, strict=True))


def _locate(file: str, audit_path: str, excerpt: str) -> str:
    parts = audit_path.split("/")
    found = [
        path
        for path, text in surfaces.walk(surfaces.load(file))
        if excerpt in text and _fits(path, parts)
    ]
    if len(found) != 1:
        raise LookupError(f"{file} {audit_path}: {len(found)} strings hold the excerpt")
    return found[0]


def _string_at(file: str, path: str) -> str:
    value = surfaces.resolve(surfaces.load(file), path)
    if not isinstance(value, str):
        raise LookupError(f"{file} {path}: no string")
    return value


def _waits_on_w2(reason: str) -> bool:
    return "W2" in reason and "W2 or W3" not in reason and "W2 to W8" not in reason


def _named(entries: dict[str, Entry]) -> None:
    for named in NAMED:
        found = [
            (file, path, text)
            for file in surfaces.data_files()
            for path, text in surfaces.walk(surfaces.load(file))
            if all(part in path for part in named.parts)
            and path.endswith(named.suffix)
            and (not named.text or text == named.text)
        ]
        if len(found) != 1:
            raise LookupError(f"{named.parts}: {len(found)} strings match")
        file, path, text = found[0]
        entry = entries.setdefault(f"{file}|{path}", Entry(file, path, text))
        entry.why = named.why


def _mark(entry: Entry) -> None:
    for owner, glob, part in SKIPS:
        if fnmatchcase(entry.file, glob) and part in entry.gate_path:
            entry.disposition, entry.owner = SKIP, owner
    flags = [flag for flag, part in FLAGS if part in entry.gate_path]
    if entry.file in LOG_FILES or entry.gate_path.endswith(".discovery_text"):
        flags.append("LOG")
    if any(row.note.startswith("edge") for row in entry.rows):
        flags.append("EDGE")
    entry.flags = sorted(set(flags))


def build(audit_text: str) -> list[Entry]:
    """The worklist: an entry for each open audit row's string, each string the allowlist holds
    for W2 alone, and each named line, marked, flagged and decided."""
    entries: dict[str, Entry] = {}
    for file, audit_path, row in parse_audit(audit_text):
        if file == "data/dialogue/dialogues.json" and audit_path.startswith("intro_narration/"):
            continue
        path = _locate(file, audit_path, row.excerpt)
        entry = entries.setdefault(f"{file}|{path}", Entry(file, path, _string_at(file, path)))
        entry.rows.append(row)
    allowed_rows = [allowed for allowed in allowlist.rows() if allowed.file.startswith("data/")]
    matches: dict[str, list[str]] = {}
    for allowed in allowed_rows:
        key = f"{allowed.file}|{allowed.path}"
        if key not in entries and _waits_on_w2(allowed.reason):
            entries[key] = Entry(allowed.file, allowed.path, _string_at(allowed.file, allowed.path))
    for allowed in allowed_rows:
        held = entries.get(f"{allowed.file}|{allowed.path}")
        if held is not None:
            held.gates = sorted({*held.gates, f"{allowed.gate}:{allowed.rule}"})
            matches.setdefault(held.id, []).append(allowed.match)
    _named(entries)
    for entry in entries.values():
        _mark(entry)
        decide(entry)
        # An adoption that keeps a gate row's offending text would leave the row standing.
        if entry.disposition == ADOPT and any(
            m and m in entry.new for m in matches.get(entry.id, [])
        ):
            entry.disposition, entry.new = DRAFT, ""
    return sorted(entries.values(), key=lambda entry: (entry.file, entry.gate_path))


def load_worklist(path: Path = WORKLIST) -> list[Entry]:
    """The committed worklist."""
    document = json.loads(path.read_text(encoding="utf-8"))
    entries: list[Entry] = []
    for item in document["entries"]:
        rows = [Row(**row) for row in item.pop("rows")]
        entries.append(Entry(**item, rows=rows))
    return entries


def save_worklist(entries: list[Entry], path: Path = WORKLIST) -> None:
    """Write the worklist, sorted, as ASCII-escaped JSON with LF endings."""
    document = {"format": 1, "entries": [asdict(entry) for entry in entries]}
    text = json.dumps(document, indent=1, ensure_ascii=True) + "\n"
    path.write_bytes(text.encode("utf-8"))


def merge_drafts(entries: list[Entry], drafts: dict[str, str]) -> int:
    """Set each drafted line; a redrafted adoption becomes a draft. Refuses a skipped entry."""
    by_id = {entry.id: entry for entry in entries}
    for entry_id, line in drafts.items():
        entry = by_id[entry_id]
        if entry.disposition == SKIP:
            raise ValueError(f"{entry_id} is skipped ({entry.owner})")
        entry.new, entry.disposition = line, DRAFT
    return len(drafts)


def swap(raw: str, old: str, new: str, ordinal: int = 0, expected: int = 1) -> str:
    """raw with its ordinal-th JSON string old (counting in file order) replaced by new, in the
    escaping raw uses; the file must hold old exactly expected times."""
    for ascii_only in (False, True):
        before = json.dumps(old, ensure_ascii=ascii_only)
        positions = [match.start() for match in re.finditer(re.escape(before), raw)]
        if len(positions) == expected:
            at = positions[ordinal]
            after = json.dumps(new, ensure_ascii=ascii_only)
            return raw[:at] + after + raw[at + len(before) :]
    raise ValueError(f"the string does not occur {expected} times: {old[:60]!r}")


def _strings(node: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Every string value under node in file order with its gate path, keys starting with "_"
    included (surfaces.walk skips them, and the raw file holds them)."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for segment, item in zip(surfaces.segments(node), node, strict=True):
            yield from _strings(item, f"{path}{segment}")


def swap_at(raw: str, path: str, old: str, new: str) -> str:
    """raw with the string old at path replaced by new, however often old occurs in the file."""
    hits = [found for found, text in _strings(json.loads(raw)) if text == old]
    return swap(raw, old, new, hits.index(path), len(hits))


def _fresh(root: Path, file: str) -> object:
    return json.loads((root / file).read_bytes().decode("utf-8"))


def apply_file(entries: list[Entry], file: str, root: Path = ROOT) -> int:
    """Swap every finished entry of file into the data: its new line replaces whatever line its
    path holds (the old one, or an earlier draft). The count swapped."""
    target = root / file
    raw = target.read_bytes().decode("utf-8")
    swapped = 0
    for entry in entries:
        if entry.file != file or entry.disposition == SKIP or not entry.new:
            continue
        held = surfaces.resolve(json.loads(raw), entry.gate_path)
        if isinstance(held, str) and held != entry.new:
            raw = swap_at(raw, entry.gate_path, held, entry.new)
            swapped += 1
    target.write_bytes(raw.encode("utf-8"))
    return swapped


def check(entries: list[Entry], files: set[str], root: Path = ROOT) -> list[str]:
    """What is wrong with the entries of files: each must hold its new line, with every excerpt
    gone and the braces kept; a skipped entry must hold its old line."""
    problems: list[str] = []
    documents: dict[str, object] = {}
    for entry in entries:
        if entry.file not in files:
            continue
        if entry.file not in documents:
            documents[entry.file] = _fresh(root, entry.file)
        document = documents[entry.file]
        value = surfaces.resolve(document, entry.gate_path)
        if entry.disposition == SKIP:
            if value != entry.old:
                problems.append(f"{entry.id}: a skipped line changed")
            continue
        if not entry.new or entry.new == entry.old:
            problems.append(f"{entry.id}: no new line")
            continue
        if value != entry.new:
            problems.append(f"{entry.id}: the data does not hold the new line")
            continue
        problems.extend(
            f"{entry.id}: row {row.row}'s excerpt is still there"
            for row in entry.rows
            if row.excerpt in entry.new
        )
        if sorted(_BRACE.findall(entry.old)) != sorted(_BRACE.findall(entry.new)):
            problems.append(f"{entry.id}: the braces changed")
    return problems


def residue(entries: list[Entry], files: set[str], root: Path = ROOT) -> list[str]:
    """Every audit excerpt that is back in its string: the check that outlives W2, when later
    chunks (W3 to W8, SP10) rewrite these lines freely but must not restore an offending clause."""
    found: list[str] = []
    documents: dict[str, object] = {}
    for entry in entries:
        if entry.file not in files or entry.disposition == SKIP:
            continue
        if entry.file not in documents:
            documents[entry.file] = _fresh(root, entry.file)
        value = surfaces.resolve(documents[entry.file], entry.gate_path)
        found.extend(
            f"{entry.id}: row {row.row}'s excerpt is back"
            for row in entry.rows
            if isinstance(value, str) and row.excerpt in value
        )
    return found


def _quoted(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.split("\n"))


def render(entries: list[Entry], files: set[str] | None = None) -> str:
    """The reading copy: each file's entries, old line beside new, with flags and rows."""
    out = [
        "# W2: the narrator audit's lines, before and after",
        "",
        "Every line plan W2-S rewrites or leaves, by file. Flags: EDGE (spec 11.2, the author"
        " rules), SENSATION (spec 2.2 edge 1, the author rules), DECIDES, LOG, KOREN, KORVATH,"
        " PRONOUN, SCRAPING. Dispositions: adopt (the audit's suggestion), draft (written in W2),"
        " skip (left to its owner).",
    ]
    shown = sorted({entry.file for entry in entries if files is None or entry.file in files})
    for file in shown:
        out += ["", f"## {file}"]
        for entry in (entry for entry in entries if entry.file == file):
            tags = [*entry.flags, entry.disposition] + ([entry.owner] if entry.owner else [])
            gates = ", ".join(entry.gates) or "none"
            why = f"; {entry.why}" if entry.why else ""
            out += ["", f"### `{entry.gate_path}`", "", f"{', '.join(tags)}; gates {gates}{why}"]
            out += [
                f"- Row {row.row} ({row.classes}). Excerpt: {row.excerpt} Suggestion:"
                f" {row.suggestion}{' Note: ' + row.note if row.note else ''}"
                for row in entry.rows
            ]
            out += ["", "Before:", "", _quoted(entry.old), "", "After:", ""]
            out += [_quoted(entry.new or entry.old)]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run one command; see the module's usage."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build").add_argument("--audit", required=True, type=Path)
    commands.add_parser("draft").add_argument("--from", dest="source", required=True, type=Path)
    commands.add_parser("apply").add_argument("--file", required=True)
    commands.add_parser("check").add_argument("--file")
    commands.add_parser("files")
    read = commands.add_parser("read")
    read.add_argument("--out", required=True, type=Path)
    read.add_argument("--file")
    args = parser.parse_args(argv)
    if args.command == "build":
        entries = build(args.audit.read_text(encoding="utf-8"))
        save_worklist(entries)
        counts = {
            kind: sum(entry.disposition == kind for entry in entries)
            for kind in (ADOPT, DRAFT, SKIP)
        }
        rows = sum(len(entry.rows) for entry in entries)
        print(f"built {len(entries)} entries holding {rows} audit rows; {counts}")
        return 0
    entries = load_worklist()
    if args.command == "draft":
        drafts = json.loads(args.source.read_text(encoding="utf-8"))
        print(f"drafted {merge_drafts(entries, drafts)} lines")
        save_worklist(entries)
    elif args.command == "apply":
        print(f"applied {apply_file(entries, args.file)} lines to {args.file}")
    elif args.command == "check":
        files = {args.file} if args.file else {entry.file for entry in entries}
        problems = check(entries, files)
        print("\n".join(problems) or f"{len(files)} files checked: every entry landed")
        return 1 if problems else 0
    elif args.command == "files":
        for file in sorted({entry.file for entry in entries}):
            total = sum(entry.file == file for entry in entries)
            print(f"{file} {total}")
    else:
        shown = {args.file} if args.file else None
        args.out.write_bytes(render(entries, shown).encode("utf-8"))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
