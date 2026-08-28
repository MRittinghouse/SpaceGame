"""Fail the build when authored prose in `data/` contains AI writing tells.

## Why this exists

`tests/test_data/test_dialogue_integrity.py` already checks dialogue text for
these patterns, but it reads a hardcoded file list::

    for filename in ["dialogues.json", "crew_quest_dialogues.json"]:

That covered every dialogue-bearing file that existed when it was written. It
stops covering anything the moment content lands in a new file, and it never
covered the 73 other JSON files under `data/` at all: three em-dashes were
sitting in `complications.json` and `timed_threads.json`, unseen, until this
test was added.

That gap matters more than it used to. The Act II arc authors content into new
files with their own schemas (`data/narrative/dilemmas/<id>.json` among them),
much of it written by agents with no human reading every line as it lands. A
gate keyed to a fixed list of filenames, or to one schema's shape, would not
see any of it.

So this check is deliberately **schema-agnostic**: it walks every string value
in every JSON file under `data/`, whatever the surrounding structure. A new
content type is covered the day it is created, with nothing to remember to
register. Measured cost of that breadth at the time of writing: 75 files, and
zero false positives.

The patterns come from CLAUDE.md's "Narrative & Writing" rules, which name them
as GenAI tells.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# An em-dash is U+2014. Spelled as an escape so this file does not trip its own
# check when the scanner is pointed at the test suite.
EM_DASH = "—"

_NO_X_NO_Y = re.compile(r"[Nn]o \w+,\s*no \w+")


def _strings(obj: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield (json_path, value) for every string anywhere in a decoded document."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _strings(value, f"{path}[{index}]")


def _data_files() -> list[Path]:
    return sorted(DATA_DIR.rglob("*.json"))


def _violations(check: object) -> list[str]:
    """Run one predicate over every string in every data file."""
    assert callable(check)
    errors: list[str] = []
    for path in _data_files():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: unreadable ({exc})")
            continue
        for json_path, value in _strings(document):
            if check(value):
                errors.append(f"{path.relative_to(PROJECT_ROOT)}{json_path}: {value[:90]}")
    return errors


def test_data_directory_is_present_and_populated() -> None:
    """Guard the guard.

    Every other test here passes vacuously if the glob returns nothing, which
    would make a broken path look like a clean bill of health.
    """
    files = _data_files()
    assert DATA_DIR.is_dir(), f"data directory missing at {DATA_DIR}"
    assert len(files) >= 50, f"expected the full data corpus, found {len(files)} json files"


def test_no_em_dashes_in_data() -> None:
    """No em-dash in any authored string. CLAUDE.md names it a GenAI tell."""
    errors = _violations(lambda s: EM_DASH in s)
    assert not errors, "em-dash (U+2014) found in authored data:\n" + "\n".join(errors)


def test_no_no_x_no_y_constructions() -> None:
    """No "no X, no Y" constructions."""
    errors = _violations(lambda s: bool(_NO_X_NO_Y.search(s)))
    assert not errors, '"no X, no Y" construction found:\n' + "\n".join(errors)


def test_no_testament_to() -> None:
    """No "a testament to"."""
    errors = _violations(lambda s: "testament to" in s.lower())
    assert not errors, '"testament to" found:\n' + "\n".join(errors)


def test_no_couldnt_help_but() -> None:
    """No "couldn't help but"."""
    errors = _violations(lambda s: "couldn't help but" in s.lower())
    assert not errors, '"couldn\'t help but" found:\n' + "\n".join(errors)


BANNED_NPC_NAMES = (
    "yara",
    "elara",
    "kael",
    "mara",
    "lydia",
    "clive",
    "magnus",
    "ambrose",
)


@pytest.mark.parametrize("banned", BANNED_NPC_NAMES)
def test_no_banned_npc_names_anywhere_in_data(banned: str) -> None:
    """Banned names must not appear in any data file.

    `test_dialogue_integrity.test_no_banned_npc_names` already checks parsed
    NPCs via the loader, which auto-discovers correctly. This is the wider net:
    a banned name in a dialogue line, a mission brief, or a location blurb is
    still a banned name, and none of those go through `loader.npcs`.

    Matched on word boundaries so real words containing a banned name as a
    substring do not trip it.
    """
    pattern = re.compile(rf"\b{banned}\b", re.IGNORECASE)
    errors = _violations(lambda s: bool(pattern.search(s)))
    assert not errors, f"banned NPC name '{banned}' found in data:\n" + "\n".join(errors)
