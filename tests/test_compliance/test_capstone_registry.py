"""A2-20: Data-integrity compliance tests for the capstone registry.

Covers AC6 (data integrity) and AC11 (GameState.CAPSTONE is push-only).
"""

from __future__ import annotations

import pathlib
import re

from spacegame.data_loader import get_data_loader

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestCapstoneRegistryIntegrity:
    """AC6: sixteen capstones, bijective lens mapping, uniform threshold, null cutscene_ref."""

    def setup_method(self) -> None:
        self.dl = get_data_loader()
        self.dl.load_all()

    def test_sixteen_capstones_loaded(self) -> None:
        assert len(self.dl.capstones) == 16, (
            f"Expected 16 capstones, got {len(self.dl.capstones)}. "
            "Add a capstone entry for any new lens."
        )

    def test_bijective_lens_mapping(self) -> None:
        capstone_lens_ids = {c.lens_id for c in self.dl.capstones.values()}
        lens_ids = set(self.dl.lenses.keys())
        assert capstone_lens_ids == lens_ids, (
            f"Capstone lens_ids do not match loaded lenses.\n"
            f"  Missing capstones for: {lens_ids - capstone_lens_ids}\n"
            f"  Capstones with unknown lens: {capstone_lens_ids - lens_ids}"
        )

    def test_uniform_threshold_95(self) -> None:
        wrong = {
            cid: c.capstone_threshold
            for cid, c in self.dl.capstones.items()
            if c.capstone_threshold != 95
        }
        assert not wrong, f"Non-95 thresholds: {wrong}"

    def test_all_cutscene_refs_null(self) -> None:
        non_null = {
            cid: c.cutscene_ref
            for cid, c in self.dl.capstones.items()
            if c.cutscene_ref is not None
        }
        assert not non_null, (
            f"Expected all cutscene_ref=null; got non-null: {non_null}. "
            "Authored cutscenes ship in a later sprint."
        )

    def test_all_ids_snake_case(self) -> None:
        bad_capstone_ids = [cid for cid in self.dl.capstones if not _SNAKE_CASE_RE.match(cid)]
        bad_lens_ids = [
            c.lens_id for c in self.dl.capstones.values() if not _SNAKE_CASE_RE.match(c.lens_id)
        ]
        assert not bad_capstone_ids, f"Non-snake_case capstone_ids: {bad_capstone_ids}"
        assert not bad_lens_ids, f"Non-snake_case lens_ids: {bad_lens_ids}"


class TestCapstoneStateNeverChangeState:
    """AC11: change_state(GameState.CAPSTONE) must never appear in spacegame/ source."""

    def test_no_change_state_capstone_in_source(self) -> None:
        source_root = pathlib.Path(__file__).parent.parent.parent / "spacegame"
        forbidden_patterns = [
            "change_state(GameState.CAPSTONE)",
            'change_state(GameState("capstone"))',
        ]
        violations: list[str] = []
        for py_file in source_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="replace")
            for pat in forbidden_patterns:
                if pat in text:
                    violations.append(f"{py_file.relative_to(source_root.parent)}: {pat!r}")
        assert not violations, (
            "GameState.CAPSTONE is push-only; change_state is forbidden:\n" + "\n".join(violations)
        )
