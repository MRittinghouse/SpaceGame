"""Plan W2-S's done-test (writing-discipline spec 9.4): the narrator audit's lines landed.

The gates prove the rows they read; this proves the rest. For each file in DONE_FILES, every
worklist entry's string is its new line, every audit excerpt is gone, every brace is kept, and
every skipped line (W3's, SP10's, the archive's) is exactly as shipped. Each rewrite task adds its
files; Task 11 requires every file of the worklist to be here.
"""

from __future__ import annotations

import pytest

from tools.writing import w2_audit

DONE_FILES: tuple[str, ...] = (
    "data/encounters/campaign.json",
    "data/encounters/ce4_pressure.json",
    "data/encounters/ce4_variety.json",
    "data/encounters/generic.json",
    "data/encounters/humor.json",
    "data/encounters/lore.json",
    "data/encounters/system_specific.json",
)


def test_the_worklist_holds_every_open_audit_row() -> None:
    entries = w2_audit.load_worklist()
    assert sum(len(entry.rows) for entry in entries) == 567
    assert len({entry.id for entry in entries}) == len(entries)


@pytest.mark.parametrize("file", DONE_FILES)
def test_every_entry_of_a_done_file_landed(file: str) -> None:
    assert w2_audit.check(w2_audit.load_worklist(), {file}) == []
