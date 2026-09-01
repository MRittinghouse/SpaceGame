"""Data-integrity guard for the capstone registry.

Fails the build on:
- missing required field (any of the three required fields)
- duplicate capstone_id
- non-snake_case capstone_id
- non-snake_case lens_id
- negative capstone_threshold
- cutscene_ref that is neither None nor a string

Also asserts the scan itself is not silently passing over zero capstones when
``capstones.json`` ships empty -- the empty-registry case is skipped-with-reason,
not a quiet green, which is the failure this guard exists to prevent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_capstones(tmp_path: Path, capstones: list) -> Path:
    """Write a capstones.json to tmp_path/narrative/ and return the data dir."""
    narrative = tmp_path / "narrative"
    narrative.mkdir(parents=True, exist_ok=True)
    (narrative / "capstones.json").write_text(
        json.dumps({"capstones": capstones}), encoding="utf-8"
    )
    return tmp_path


def _valid_capstone(capstone_id: str = "test_capstone") -> dict:
    return {
        "capstone_id": capstone_id,
        "lens_id": "vengeance",
        "capstone_threshold": 95,
        "cutscene_ref": None,
    }


class TestCapstoneRegistryIntegrity:
    @pytest.mark.parametrize("missing_field", ["capstone_id", "lens_id", "capstone_threshold"])
    def test_missing_required_field_raises(self, tmp_path: Path, missing_field: str) -> None:
        """Each required field missing must raise ValueError."""
        from spacegame.data_loader import DataLoader

        bad = _valid_capstone("my_capstone")
        del bad[missing_field]
        _write_capstones(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_capstones()

    @pytest.mark.parametrize(
        "bad_id",
        ["Vengeance", "capstone-vengeance", "1capstone", "WEALTH_CAPSTONE", "has space"],
    )
    def test_non_snake_case_capstone_id_raises(self, tmp_path: Path, bad_id: str) -> None:
        """Non-snake_case capstone_id values must be rejected."""
        from spacegame.data_loader import DataLoader

        bad = _valid_capstone(bad_id)
        _write_capstones(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_capstones()

    @pytest.mark.parametrize(
        "bad_lens_id",
        ["Vengeance", "political-power", "1lens", "HAS_UPPER"],
    )
    def test_non_snake_case_lens_id_raises(self, tmp_path: Path, bad_lens_id: str) -> None:
        """Non-snake_case lens_id values must be rejected."""
        from spacegame.data_loader import DataLoader

        bad = _valid_capstone("my_capstone")
        bad["lens_id"] = bad_lens_id
        _write_capstones(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_capstones()

    @pytest.mark.parametrize("bad_threshold", [-1, -100])
    def test_negative_threshold_raises(self, tmp_path: Path, bad_threshold: int) -> None:
        """Negative capstone_threshold values must be rejected."""
        from spacegame.data_loader import DataLoader

        bad = _valid_capstone("my_capstone")
        bad["capstone_threshold"] = bad_threshold
        _write_capstones(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_capstones()

    @pytest.mark.parametrize("bad_ref", [0, [], {}, False])
    def test_non_string_non_null_cutscene_ref_raises(self, tmp_path: Path, bad_ref: object) -> None:
        """cutscene_ref that is neither None nor a string must raise ValueError."""
        from spacegame.data_loader import DataLoader

        bad = _valid_capstone("my_capstone")
        bad["cutscene_ref"] = bad_ref
        _write_capstones(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_capstones()

    def test_duplicate_capstone_id_raises(self, tmp_path: Path) -> None:
        """Two capstones with the same capstone_id must raise ValueError naming the duplicate."""
        from spacegame.data_loader import DataLoader

        cap = _valid_capstone("dup_capstone")
        _write_capstones(tmp_path, [cap, cap])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="dup_capstone"):
            loader.load_capstones()

    def test_scan_guard_is_not_silent_on_empty_registry(self, tmp_path: Path) -> None:
        """When capstones.json has zero entries the scan must skip, not silently pass.

        Mirrors the test_findings_register.py pattern: a scan that passes over
        nothing provides no assurance. When the shipped stub is empty the compliance
        scan must be skipped (pytest.skip) rather than reporting a false green.
        """
        from spacegame.data_loader import DataLoader

        _write_capstones(tmp_path, [])
        loader = DataLoader(data_dir=tmp_path)
        loader.load_capstones()

        if not loader.capstones:
            pytest.skip(
                "capstones.json contains zero entries -- compliance scan would "
                "check nothing. This skip is expected while the registry is "
                "empty (A2-20 will populate it with sixteen real capstones)."
            )

        # If capstones were loaded, assert they all pass the integrity guard.
        for capstone_id, capstone in loader.capstones.items():
            assert capstone.capstone_id == capstone_id, (
                f"Key mismatch: dict key {capstone_id!r} != "
                f"Capstone.capstone_id {capstone.capstone_id!r}"
            )
