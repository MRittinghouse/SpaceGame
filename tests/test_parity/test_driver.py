"""The golden writer's rules (SP2 spec Section 7.3)."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

import pytest

from tools.parity import driver
from tools.parity.driver import Case, normalize


class _Color(Enum):
    RED = "red"


class TestNormalize:
    def test_scalars_pass_through(self) -> None:
        assert normalize({"a": 1, "b": 2.5, "c": "x", "d": None, "e": True}) == {
            "a": 1,
            "b": 2.5,
            "c": "x",
            "d": None,
            "e": True,
        }

    def test_tuples_become_lists_and_enums_values(self) -> None:
        assert normalize((1, _Color.RED, (2, 3))) == [1, "red", [2, 3]]

    def test_sets_are_rejected(self) -> None:
        with pytest.raises(TypeError, match="sort"):
            normalize({1, 2})

    def test_non_string_keys_are_rejected(self) -> None:
        with pytest.raises(TypeError, match="keys"):
            normalize({1: "x"})

    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_nan_and_infinity_are_rejected(self, bad: float) -> None:
        with pytest.raises(ValueError):
            normalize(bad)


class TestFloatTags:
    def test_float_tag_carries_repr_and_int64_bits(self) -> None:
        assert driver.float_tag(0.1) == "f:0.1:4591870180066957722"
        assert driver.float_tag(1.5) == "f:1.5:4609434218613702656"
        assert driver.float_tag(-0.0) == "f:-0.0:-9223372036854775808"

    def test_tag_floats_walks_containers_and_leaves_other_scalars(self) -> None:
        assert driver.tag_floats({"x": [1.5, 2, True, None, "s"]}) == {
            "x": ["f:1.5:4609434218613702656", 2, True, None, "s"]
        }


class TestCaseJson:
    def test_sorted_keys_two_space_indent_trailing_newline(self) -> None:
        case = Case("demo", "one", {"z": 1, "a": 2})
        case.record("call", [1, (2, 3)], None, {"b": 0.1, "a": 1})
        text = case.to_json("abc123")
        doc = json.loads(text)
        assert doc["format"] == 1
        assert doc["source_commit"] == "abc123"
        assert doc["steps"] == [
            {
                "call": "call",
                "args": [1, [2, 3]],
                "result": None,
                "state": {"a": 1, "b": "f:0.1:4591870180066957722"},
            }
        ]
        assert case.steps[0]["state"] == {"a": 1, "b": 0.1}, "steps keep raw floats"
        assert text.endswith("\n")
        assert text.index('"a"') < text.index('"z"'), "keys must be sorted"

    def test_write_cases_layout(self, tmp_path: Path) -> None:
        paths = driver.write_cases([Case("demo", "one", {})], tmp_path, "abc123")
        assert paths == [tmp_path / "demo" / "one.json"]
        assert paths[0].read_bytes().endswith(b"\n")
        assert b"\r\n" not in paths[0].read_bytes()


class TestRegenRefusesDirtyTree:
    def test_refuses_when_files_outside_parity_are_modified(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from tools.parity import regen

        monkeypatch.setattr(regen, "dirty_paths_outside", lambda prefix: ["spacegame/x.py"])
        assert regen.main(["--out", str(tmp_path)]) == 2

    def test_allow_dirty_writes(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from tools.parity import regen

        monkeypatch.setattr(regen, "dirty_paths_outside", lambda prefix: ["spacegame/x.py"])
        assert regen.main(["--out", str(tmp_path), "--allow-dirty"]) == 0
        assert (tmp_path / "golden" / "sim_rng").is_dir()
