"""Tests for tools/crawler/baseline.py (QF-7, Task 2)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def _make_crash_record(sig: str = "abcd1234efgh5678") -> Any:
    """Build a minimal CrashRecord-like object for testing baseline helpers."""
    from tools.crawler.crash_record import CrashRecord

    return CrashRecord(
        signature=sig,
        exception_class="RuntimeError",
        first_seed=42,
        first_action_index=10,
        occurrence_count=1,
        action_trace=[],
        full_traceback="Traceback: ...",
        state_at_crash="GALAXY_MAP",
        oracle="exception",
    )


class TestLoadBaseline:
    def test_load_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import load_baseline

        missing = tmp_path / "nonexistent.json"
        result = load_baseline(str(missing))
        assert result == set()

    def test_load_malformed_json_raises(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import load_baseline

        bad = tmp_path / "bad.json"
        bad.write_text("not valid json {{{{")
        with pytest.raises(Exception):
            load_baseline(str(bad))

    def test_load_valid_baseline_returns_signature_set(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import load_baseline

        data = {
            "generated_at": "2026-08-23T00:00:00Z",
            "generated_from": [[42, None, 5000]],
            "signatures": [
                {
                    "signature": "aaaa1111bbbb2222",
                    "exception_class": "RuntimeError",
                    "oracle": "exception",
                    "state_at_crash": "GALAXY_MAP",
                    "first_seed": 42,
                    "first_action_index": 0,
                    "occurrence_count": 1,
                },
                {
                    "signature": "cccc3333dddd4444",
                    "exception_class": "AttributeError",
                    "oracle": "exception",
                    "state_at_crash": "TRADING",
                    "first_seed": 42,
                    "first_action_index": 5,
                    "occurrence_count": 2,
                },
            ],
        }
        path = tmp_path / "baseline.json"
        path.write_text(json.dumps(data))
        result = load_baseline(str(path))
        assert result == {"aaaa1111bbbb2222", "cccc3333dddd4444"}


class TestCompare:
    def test_compare_returns_only_novel_signatures(self) -> None:
        from tools.crawler.baseline import compare

        known_sig = "aaaa1111bbbb2222"
        novel_sig = "cccc3333dddd4444"
        crashes = {
            known_sig: _make_crash_record(known_sig),
            novel_sig: _make_crash_record(novel_sig),
        }
        known = {known_sig}
        result = compare(crashes, known)
        assert len(result) == 1
        assert result[0].signature == novel_sig

    def test_compare_all_known_returns_empty(self) -> None:
        from tools.crawler.baseline import compare

        sig = "aaaa1111bbbb2222"
        crashes = {sig: _make_crash_record(sig)}
        result = compare(crashes, {sig})
        assert result == []

    def test_compare_output_is_sorted(self) -> None:
        from tools.crawler.baseline import compare

        sigs = ["zzzz9999aaaa0000", "aaaa1111bbbb2222", "mmmm5555nnnn6666"]
        crashes = {s: _make_crash_record(s) for s in sigs}
        result = compare(crashes, set())
        returned_sigs = [r.signature for r in result]
        assert returned_sigs == sorted(sigs)

    def test_compare_no_crashes_returns_empty(self) -> None:
        from tools.crawler.baseline import compare

        result = compare({}, {"some_sig"})
        assert result == []


class TestWriteBaseline:
    def test_write_baseline_is_deterministic(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import write_baseline

        sig1 = "aaaa1111bbbb2222"
        sig2 = "cccc3333dddd4444"
        crashes = {
            sig1: _make_crash_record(sig1),
            sig2: _make_crash_record(sig2),
        }
        path1 = tmp_path / "baseline1.json"
        path2 = tmp_path / "baseline2.json"
        generated_from = [(42, None, 5000)]
        write_baseline(str(path1), crashes, generated_from)
        write_baseline(str(path2), crashes, generated_from)
        assert path1.read_text() == path2.read_text()

    def test_write_baseline_then_load_roundtrips(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import load_baseline, write_baseline

        sig1 = "aaaa1111bbbb2222"
        sig2 = "cccc3333dddd4444"
        crashes = {
            sig1: _make_crash_record(sig1),
            sig2: _make_crash_record(sig2),
        }
        path = tmp_path / "baseline.json"
        write_baseline(str(path), crashes, [(42, None, 5000)])
        loaded = load_baseline(str(path))
        assert loaded == {sig1, sig2}

    def test_write_baseline_signatures_sorted(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import write_baseline

        sigs = ["zzzz9999aaaa0000", "aaaa1111bbbb2222", "mmmm5555nnnn6666"]
        crashes = {s: _make_crash_record(s) for s in sigs}
        path = tmp_path / "baseline.json"
        write_baseline(str(path), crashes, [(42, None, 5000)])
        data = json.loads(path.read_text())
        written_sigs = [e["signature"] for e in data["signatures"]]
        assert written_sigs == sorted(sigs)

    def test_write_baseline_has_required_top_level_fields(self, tmp_path: Path) -> None:
        from tools.crawler.baseline import write_baseline

        crashes = {"abcd1234abcd1234": _make_crash_record("abcd1234abcd1234")}
        path = tmp_path / "baseline.json"
        write_baseline(str(path), crashes, [(42, "mid", 5000)])
        data = json.loads(path.read_text())
        assert "generated_at" in data
        assert "generated_from" in data
        assert "signatures" in data

    def test_write_baseline_include_from_merges_extra_crashes(self, tmp_path: Path) -> None:
        """write_baseline should merge crash records from external crashes.json files."""
        from tools.crawler.baseline import write_baseline

        sig_main = "aaaa1111bbbb2222"
        sig_extra = "zzzz9999aaaa0000"

        extra_crashes_json = tmp_path / "extra_crashes.json"
        extra_crashes_json.write_text(
            json.dumps(
                {
                    "seed": 137,
                    "crashes": [
                        {
                            "signature": sig_extra,
                            "exception_class": "ValueError",
                            "first_seed": 137,
                            "first_action_index": 22,
                            "occurrence_count": 1,
                            "action_trace": [],
                            "full_traceback": "...",
                            "state_at_crash": "TRADING",
                            "oracle": "exception",
                            "extra": {},
                        }
                    ],
                }
            )
        )

        crashes = {sig_main: _make_crash_record(sig_main)}
        path = tmp_path / "baseline.json"
        write_baseline(
            str(path),
            crashes,
            [(42, None, 5000)],
            include_from=[str(extra_crashes_json)],
        )
        data = json.loads(path.read_text())
        written_sigs = {e["signature"] for e in data["signatures"]}
        assert sig_main in written_sigs
        assert sig_extra in written_sigs


class TestBaselineFileIsWellformed:
    def test_baseline_file_is_wellformed(self, tmp_path: Path) -> None:
        """Verify that a written baseline file matches the locked schema."""
        from tools.crawler.baseline import write_baseline

        sig = "abcd1234efgh5678"
        crashes = {sig: _make_crash_record(sig)}
        path = tmp_path / "baseline.json"
        write_baseline(str(path), crashes, [(42, "mid", 5000), (137, "early", 5000)])
        data = json.loads(path.read_text())

        # Top-level keys
        assert "generated_at" in data
        assert "generated_from" in data
        assert "signatures" in data

        # generated_at is a UTC ISO-8601 string (no microseconds)
        assert isinstance(data["generated_at"], str)
        assert "T" in data["generated_at"]
        assert "." not in data["generated_at"]  # no microseconds

        # generated_from is a list
        assert isinstance(data["generated_from"], list)

        # signatures is a sorted list of dicts with expected fields
        assert isinstance(data["signatures"], list)
        assert len(data["signatures"]) == 1
        entry = data["signatures"][0]
        for field in ("signature", "exception_class", "oracle", "state_at_crash",
                      "first_seed", "first_action_index", "occurrence_count"):
            assert field in entry, f"missing field {field!r} in baseline entry"
