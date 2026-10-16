"""Writing chunk W3b's rows hold in the data (plan W3b-S; writing-discipline spec 9.2 rows 10, 11).

APPLIED lists the groups this branch has swapped in; each task that applies a group adds it.
"""

from __future__ import annotations

import re

from tests.writing_gates import surfaces
from tools.writing import w3b_rows

APPLIED: tuple[str, ...] = ()
BRACE = re.compile(r"\{[^{}]*\}")
RECORD = re.compile(r"\{(?:pay|fee):[a-z0-9_]+\}")


def test_every_applied_group_holds_its_new_lines() -> None:
    assert w3b_rows.problems(APPLIED) == []


def test_every_group_not_applied_still_holds_its_old_lines() -> None:
    for group in w3b_rows.GROUPS:
        if group in APPLIED:
            continue
        rows = [row for row in w3b_rows.load_rows() if row.group == group]
        for row in rows:
            held = surfaces.resolve(surfaces.load(row.file), row.path)
            assert held == row.old, (row.file, row.path)
        assert len(w3b_rows.problems((group,))) == len(rows), group


def test_a_row_keeps_its_braces_but_a_price_row_gains_a_record_token() -> None:
    for row in w3b_rows.load_rows():
        kept = sorted(BRACE.findall(row.old))
        now = sorted(token for token in BRACE.findall(row.new) if not RECORD.fullmatch(token))
        assert now == kept, (row.file, row.path)
        if RECORD.search(row.new):
            assert row.group == "price", (row.file, row.path)
