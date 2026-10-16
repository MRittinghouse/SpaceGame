"""Writing chunk W3b's rows hold in the data (plan W3b-S; writing-discipline spec 9.2 rows 10, 11).

APPLIED lists the groups this branch has swapped in; each task that applies a group adds it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.captain_tokens import RECORD_KINDS
from tests.writing_gates import surfaces
from tools.writing import w3b_rows

APPLIED: tuple[str, ...] = ("price", "gesture", "truth", "residual", "first_sale", "flags")
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


def test_a_record_token_names_a_mission_that_pays_it() -> None:
    missions = get_data_loader().missions_by_id
    found = 0
    for row in surfaces.player_facing():
        for kind, mission_id in re.findall(r"\{(pay|fee):([a-z0-9_]+)\}", row.text):
            found += 1
            mission = missions.get(mission_id)
            assert mission is not None, (row.file, row.path, mission_id)
            assert any(r.reward_type == RECORD_KINDS[kind] for r in mission.rewards), (
                row.file,
                row.path,
            )
    assert found == (12 if "price" in APPLIED else 0)


AMBIENT = Path(__file__).resolve().parents[2] / "data" / "crew" / "ambient_dialogue.json"
BARKS = [
    ("elena_reeves", "opened_market", 0),
    ("marcus_jin", "opened_market", 0),
    ("dr_priya_osei", "opened_market", 0),
    ("tomas_drifter", "opened_market", 40),
    ("kai_torren", "opened_market", 0),
    ("tomas_drifter", "sold_back", 0),
    ("elena_reeves", "sold_back", 0),
    ("marcus_jin", "sold_back", 0),
    ("dr_priya_osei", "sold_back", 0),
]


def test_the_nine_barks_are_appended() -> None:
    """Polish design 5.2 and 5.4's beats, nine by the ruling of 2026-10-13, appended so no index
    moves (polish design 8.2 row 5.1); Kai's loyalty never moves, so his line takes no gate."""
    lines = json.loads(AMBIENT.read_text(encoding="utf-8"))["ambient_lines"]
    assert len(lines) == 339
    assert lines[329]["crew_id"] == "tomas_drifter" and lines[329]["context"] == "flag_triggered"
    for index, (crew_id, action, loyalty) in enumerate(BARKS, start=330):
        line = lines[index]
        assert line["crew_id"] == crew_id, index
        assert line["context"] == "player_action", index
        assert line["action_type"] == action, index
        assert line.get("min_loyalty", 0) == loyalty, index
        assert set(line) == {"crew_id", "text", "context", "action_type"} | (
            {"min_loyalty"} if loyalty else set()
        ), index
        assert line["text"].strip(), index
