"""The prose gates' baseline allowlist (writing discipline spec 5.1): rows that may only shrink.

Every gate starts with a row per offence shipped when the gates landed (plan W1-S), keyed by
gate, rule, file and path (a JSON path, or a code string's ``Scope|text``), each with a reason.
``tests/test_writing_bible_compliance.py`` fails a new offence that has no row, and fails a row
whose string no longer offends, so a fixed line must leave the list in the same commit.

Usage, from the repo root:
    python -m tests.writing_gates.allowlist --write   # the baseline; refuses an existing file
    python -m tests.writing_gates.allowlist --prune   # drop rows that no longer offend
    python -m tests.writing_gates.allowlist --counts  # rows by gate and rule
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import cache
from pathlib import Path

from tests.writing_gates.rules import GATES, Offence, offences

ALLOWLIST_FILE = Path(__file__).resolve().parent / "allowlist.json"
FORMAT = 1


@dataclass(frozen=True)
class Row:
    """One allowed offence and why it stays for now."""

    gate: str
    rule: str
    file: str
    path: str
    match: str
    reason: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        """The offence key the row allows: gate, rule, file, path."""
        return (self.gate, self.rule, self.file, self.path)


@dataclass(frozen=True)
class Reason:
    """A baseline reason for the offences it matches: ``gate`` and ``rule`` match exactly or
    by "*", ``file`` is a glob ("*" matches every file), and ``path`` matches any path that
    contains it ("" matches every path)."""

    gate: str
    rule: str
    file: str
    path: str
    text: str


_AUTHOR = "the author's ruling, 2026-10-02: a habit the speaker uses with anyone (spec 2.6)"
_TABLE = (
    "the captain's address, routed through the table or reworded by this plan (spec 2.6);"
    " Task 9 prunes it"
)
_QUOTE = "a Read quoting Arna's words, not a feeling of the captain's; W2 restates it (impact 7c)"
_COLLAPSE = "a stage tag in the collapse sequence; SP10 rewrites the sequence"
_MOOD = "the tag names a mood; W2 makes it an act or the exact line (impact 7d)"
_NOT_ACT = (
    "bracketed speech or a tag that is not an act; W2 makes it the line or an act (impact 7d)"
)
_OBSERVATION = (
    "an Observation check followed by unquoted speech or an unspoken insight; W2 quotes it or"
    " makes it an act (impact 7e)"
)
_NAMES = "a near-collision of shipped names; the naming pass, or the author accepts it (spec 11.3)"
_NAVY = "naval facility becomes a Guild yard or an enforcement term (impact 10.8); W2"
_COLLAPSE_WARP = "warp in the collapse sequence; SP10 rewrites the sequence (impact 5.1)"
_WARP = "warp is out of the Expanse's lexicon; W2 rewrites the line"
_MARCUS = "Marcus never says Captain (polish design 3.1, content rule 7); his slice, W4 to W8"
_GESTURE = "without looking up is Marcus's gesture alone; W2 gives this speaker another"
_PRICE = "a literal price in speech becomes a record token (spec 3.7, 2.7); W2 or W3"
_EXITS = "more than four nodes without an exit; the tree's rewrite restructures it (W2 to W8, SP10)"
_PLAYER = "Act II v1 archive text, the flag off; W2 rewrites it"
_DASH = "a double hyphen used as a dash (BB-35's wave B files); W2 rewrites it"
_NEGATION = "a paired negation; W2 rewrites it"
_WORD = "an overused word (spec G3); W2 rewrites it"
_AUDIT = "the narrator audit's finding (audit.md); W2 rewrites it"
_CODE = (
    "a dash or a paired negation in a string built in code, outside the narrator audit"
    " (spec 9.4); register F-016 names its owner"
)
_TAGLINE = (
    "the Crimson Reach tagline, exempt by name as in character outlaw bravado"
    " (requirements/station_legibility.md, 2026-04-26)"
)

# The first match wins, so specific reasons come first. Every reason names the chunk or the
# decision that removes its rows, or the ruling that keeps them (_AUTHOR, _TAGLINE), and a G5
# pronoun row names its referent (spec 5.1, G5). An offence no reason matches raises: the
# narrator audit's reason covers G6 to G8 alone.
REASONS: tuple[Reason, ...] = (
    Reason("G5", "vocative", "data/combat/captains.json", "", _AUTHOR),
    Reason("G5", "vocative", "data/encounters/system_specific.json", "", _AUTHOR),
    Reason("G5", "vocative", "*", "", _TABLE),
    Reason(
        "G5", "pronoun", "*", "ransom_pirate_corvette_01", "his: the corvette's captain, an NPC"
    ),
    Reason("G5", "pronoun", "*", "merchant_trader_01", "herself: the trader's captain, an NPC"),
    Reason("G5", "pronoun", "*", "refugee_transport_01", "she: the transport's captain, an NPC"),
    Reason("G5", "pronoun", "*", "sys_haven_supply_run_01", "her: Captain Okonkwo, an NPC"),
    Reason("G8", "not your problem", "*", "arna_post_payback", _QUOTE),
    Reason("G9", "*", "*", "the_collapse_sequence", _COLLAPSE),
    Reason("G9", "mood", "*", "", _MOOD),
    Reason("G9", "not an act", "*", "", _NOT_ACT),
    Reason("G9", "observation unquoted", "*", "", _OBSERVATION),
    Reason("G4", "near collision", "*", "", _NAMES),
    Reason("G11", "navy", "*", "", _NAVY),
    Reason("G11", "warp", "*", "the_collapse_sequence", _COLLAPSE_WARP),
    Reason("G11", "warp", "*", "", _WARP),
    Reason("G11", "captain from marcus", "*", "", _MARCUS),
    Reason("G11", "without looking up", "*", "", _GESTURE),
    Reason("G11", "price in speech", "*", "", _PRICE),
    Reason("G13", "exits", "*", "", _EXITS),
    Reason("G10", "the player", "*", "", _PLAYER),
    Reason("G2", "*", "spacegame/views/station_layouts.py", "No laws. No mercy.", _TAGLINE),
    Reason("G1", "*", "spacegame/*", "", _CODE),
    Reason("G2", "*", "spacegame/*", "", _CODE),
    Reason("G1", "*", "data/*", "", _DASH),
    Reason("G2", "*", "data/*", "", _NEGATION),
    Reason("G3", "*", "data/*", "", _WORD),
    Reason("G6", "*", "*", "", _AUDIT),
    Reason("G7", "*", "*", "", _AUDIT),
    Reason("G8", "*", "*", "", _AUDIT),
)


def reason_for(offence: Offence) -> str:
    """The baseline reason for an offence: the first of REASONS that matches it."""
    for reason in REASONS:
        if (
            reason.gate in ("*", offence.gate)
            and reason.rule in ("*", offence.rule)
            and fnmatchcase(offence.file, reason.file)
            and reason.path in offence.path
        ):
            return reason.text
    raise AssertionError(f"no reason for {offence.key}")


@cache
def rows() -> tuple[Row, ...]:
    """The committed allowlist rows."""
    document = json.loads(ALLOWLIST_FILE.read_text(encoding="utf-8"))
    return tuple(Row(**row) for row in document["rows"])


def _write(found: list[Row]) -> None:
    document = {
        "format": FORMAT,
        "about": "Prose gate baseline (writing discipline spec 5.1); rows may only be removed.",
        "rows": [row.__dict__ for row in sorted(found, key=lambda r: r.key)],
    }
    # ASCII escapes, so a quoted offender's dash never appears in the file as the character.
    text = json.dumps(document, indent=2, ensure_ascii=True) + "\n"
    ALLOWLIST_FILE.write_text(text, encoding="utf-8")


def unlisted(found: list[Offence], allowed: tuple[Row, ...]) -> list[Offence]:
    """The offences no row allows: each is new, and fails its gate."""
    keys = {row.key for row in allowed}
    return [offence for offence in found if offence.key not in keys]


def stale(allowed: tuple[Row, ...], found: list[Offence]) -> list[Row]:
    """The rows whose offence is gone: the line was fixed, so its row must go."""
    keys = {offence.key for offence in found}
    return [row for row in allowed if row.key not in keys]


def baseline() -> list[Row]:
    """A row for every offence of every gate today, each with its REASONS reason."""
    found: list[Row] = []
    for gate in GATES:
        for offence in offences(gate):
            found.append(Row(*offence.key, offence.match, reason_for(offence)))
    return found


def counts(found: tuple[Row, ...] | list[Row]) -> Counter[tuple[str, str]]:
    """Rows by gate and rule."""
    return Counter((row.gate, row.rule) for row in found)


def main(argv: list[str] | None = None) -> int:
    """Write the baseline, prune fixed rows, or print the counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--prune", action="store_true")
    action.add_argument("--counts", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        if ALLOWLIST_FILE.exists():
            print(f"{ALLOWLIST_FILE.name} exists; rows may only shrink (use --prune).")
            return 2
        result = baseline()
        _write(result)
    elif args.prune:
        live = [offence for gate in GATES for offence in offences(gate)]
        gone = set(stale(rows(), live))
        result = [row for row in rows() if row not in gone]
        print(f"pruned {len(gone)} rows")
        _write(result)
    else:
        result = list(rows())
    for (gate, rule), number in sorted(
        counts(result).items(), key=lambda item: (int(item[0][0][1:]), item[0][1])
    ):
        print(f"{gate:4} {rule:24} {number}")
    print(f"total {len(result)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
