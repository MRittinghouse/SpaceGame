"""Data-integrity and architectural compliance tests for the capstone registry (A2-20).

AC6: sixteen records, bijective lens-to-capstone mapping, uniform threshold of
95, all cutscene_ref null, all ids snake_case.

AC11: grep guard — ``GameState.CAPSTONE`` must never appear as a
``change_state`` target in ``spacegame/`` source files (push-only overlay).
"""

from __future__ import annotations

import pathlib
import re

from spacegame.data_loader import get_data_loader

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestCapstoneRegistryDataIntegrity:
    """AC6 — data integrity assertions on the shipped capstones.json."""

    def setup_method(self) -> None:
        self.dl = get_data_loader()
        self.dl.load_all()

    def test_sixteen_capstones_loaded(self) -> None:
        assert len(self.dl.capstones) == 16, (
            f"Expected 16 capstones, got {len(self.dl.capstones)}: "
            f"{sorted(self.dl.capstones.keys())}"
        )

    def test_bijective_lens_to_capstone_mapping(self) -> None:
        capstone_lens_ids = {c.lens_id for c in self.dl.capstones.values()}
        lens_ids = set(self.dl.lenses.keys())
        assert capstone_lens_ids == lens_ids, (
            f"Capstone lens_ids do not match loaded lenses.\n"
            f"  In capstones but not lenses: {capstone_lens_ids - lens_ids}\n"
            f"  In lenses but not capstones: {lens_ids - capstone_lens_ids}"
        )

    def test_uniform_capstone_threshold_of_95(self) -> None:
        bad = {
            cid: c.capstone_threshold
            for cid, c in self.dl.capstones.items()
            if c.capstone_threshold != 95
        }
        assert not bad, f"Capstones with threshold != 95: {bad}"

    def test_all_cutscene_refs_are_null(self) -> None:
        non_null = {cid for cid, c in self.dl.capstones.items() if c.cutscene_ref is not None}
        assert not non_null, f"Capstones with non-null cutscene_ref: {non_null}"

    def test_all_capstone_ids_are_snake_case(self) -> None:
        bad = [cid for cid in self.dl.capstones if not _SNAKE_CASE_RE.match(cid)]
        assert not bad, f"capstone_ids not snake_case: {bad}"

    def test_all_capstone_lens_ids_are_snake_case(self) -> None:
        bad = [
            (cid, c.lens_id)
            for cid, c in self.dl.capstones.items()
            if not _SNAKE_CASE_RE.match(c.lens_id)
        ]
        assert not bad, f"lens_ids not snake_case: {bad}"


class TestCapstoneChangeStateGuard:
    """AC11 — CAPSTONE must never be a change_state target in spacegame/ source."""

    def test_no_change_state_capstone_in_source(self) -> None:
        src_root = pathlib.Path(__file__).parent.parent.parent / "spacegame"
        forbidden_patterns = [
            "change_state(GameState.CAPSTONE)",
            'change_state(GameState("capstone"))',
        ]
        offenders: list[str] = []
        for py_file in src_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if pattern in text:
                    offenders.append(f"{py_file}: '{pattern}'")
        assert not offenders, (
            "CAPSTONE must only be a push_state target, never change_state:\n"
            + "\n".join(offenders)
        )
