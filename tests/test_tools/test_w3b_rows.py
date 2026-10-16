"""Plan W3b-S's rows tool: a group's rows swap into the data and nothing else moves."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.writing import w3b_rows
from tools.writing.w3b_rows import Row

DOC = '{\r\n  "items": [\r\n    {\r\n      "id": "a",\r\n      "text": "Old \\u00e9 line."\r\n    },\r\n    {\r\n      "id": "b",\r\n      "text": "Old \\u00e9 line."\r\n    }\r\n  ]\r\n}\r\n'


def _root(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "f.json").write_bytes(DOC.encode("utf-8"))
    return tmp_path


def _row(path: str, old: str, new: str, group: str = "g") -> Row:
    return Row("data/f.json", path, old, new, group, "ref", "why")


def test_apply_swaps_only_the_row_and_keeps_the_bytes(tmp_path: Path) -> None:
    root = _root(tmp_path)
    rows = [_row(".items[id=b].text", "Old é line.", "New é line.")]
    assert w3b_rows.apply_rows(rows, root) == 1
    raw = (root / "data" / "f.json").read_bytes().decode("utf-8")
    assert raw == DOC.replace(
        '"Old \\u00e9 line."\r\n    }\r\n  ]', '"New \\u00e9 line."\r\n    }\r\n  ]'
    )
    assert w3b_rows.row_problems(rows, root) == []


def test_apply_refuses_a_row_whose_line_moved(tmp_path: Path) -> None:
    root = _root(tmp_path)
    rows = [_row(".items[id=a].text", "Something else.", "New line.")]
    with pytest.raises(ValueError, match=r"data/f\.json \.items\[id=a\]\.text"):
        w3b_rows.apply_rows(rows, root)


def test_apply_twice_changes_nothing_the_second_time(tmp_path: Path) -> None:
    root = _root(tmp_path)
    rows = [_row(".items[id=a].text", "Old é line.", "New line.")]
    w3b_rows.apply_rows(rows, root)
    assert w3b_rows.apply_rows(rows, root) == 0


def test_problems_name_a_row_not_applied(tmp_path: Path) -> None:
    root = _root(tmp_path)
    rows = [_row(".items[id=a].text", "Old é line.", "New line.")]
    assert w3b_rows.row_problems(rows, root) == [
        "data/f.json .items[id=a].text: the data does not hold the new line"
    ]


def test_the_shipped_rows_are_well_formed() -> None:
    rows = w3b_rows.load_rows()
    assert rows, "no rows"
    keys = [(row.file, row.path) for row in rows]
    assert len(keys) == len(set(keys)), "a path is listed twice"
    for row in rows:
        assert row.group in w3b_rows.GROUPS, row
        assert row.old != row.new, row
        assert row.file.startswith("data/") and row.path.startswith("."), row
        assert "\N{EM DASH}" not in row.new and "\N{EN DASH}" not in row.new, row


def test_render_shows_each_row_old_and_new() -> None:
    text = w3b_rows.render([_row(".items[id=a].text", "Old line.", "New line.", "price")])
    assert "Old line." in text and "New line." in text and ".items[id=a].text" in text
