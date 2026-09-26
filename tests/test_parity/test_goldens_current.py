"""The committed goldens and schema match what the code produces today (SP2 spec 7.7).

A change to ``spacegame/sim_rng.py``, ``spacegame/models/market.py``, or a
driver without a regen fails here, so the aurelia sync never copies stale
goldens. Each golden is rebuilt with the ``source_commit`` it carries, so the
comparison is byte for byte.
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.parity import regen
from tools.parity.driver import REPO_ROOT, Case
from tools.parity.export_schema import build_schema, write_schema

PARITY_ROOT = REPO_ROOT / "parity"
GOLDEN_ROOT = PARITY_ROOT / "golden"
REGEN_HINT = (
    "Run `python -m tools.parity.regen` from a clean tree, review the diff of parity/, "
    "and commit the goldens and schema on their own."
)


def _cases() -> list[Case]:
    return [case for build in regen.DRIVERS for case in build()]


def _golden_path(case: Case) -> Path:
    return GOLDEN_ROOT / case.subsystem / f"{case.name}.json"


def _relative(path: Path) -> str:
    return path.relative_to(PARITY_ROOT).as_posix()


class TestGoldensCurrent:
    def test_every_case_matches_its_committed_golden(self) -> None:
        missing: list[str] = []
        stale: list[str] = []
        dirty: list[str] = []
        for case in _cases():
            path = _golden_path(case)
            if not path.is_file():
                missing.append(_relative(path))
                continue
            committed = path.read_bytes()
            commit = json.loads(committed)["source_commit"]
            if commit.endswith("-dirty"):
                dirty.append(_relative(path))
            if case.to_json(commit).encode("utf-8") != committed:
                stale.append(_relative(path))
        assert not (missing or stale or dirty), (
            f"Goldens out of date. Missing: {missing}. Stale: {stale}. "
            f"Generated from a dirty tree: {dirty}. {REGEN_HINT}"
        )

    def test_no_orphan_goldens(self) -> None:
        produced = {_relative(_golden_path(case)) for case in _cases()}
        on_disk = {_relative(p) for p in GOLDEN_ROOT.rglob("*") if p.is_file()}
        orphans = sorted(on_disk - produced)
        assert not orphans, f"Golden files no driver produces: {orphans}. {REGEN_HINT}"

    def test_schema_matches_build_schema(self, tmp_path: Path) -> None:
        written_path = tmp_path / "schema.json"
        write_schema(written_path)
        written = written_path.read_bytes()
        assert written == (json.dumps(build_schema(), indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ), "write_schema must write sorted two-space JSON with a trailing LF and no CR"
        assert written == (PARITY_ROOT / "schema.json").read_bytes(), (
            f"parity/schema.json is out of date. {REGEN_HINT}"
        )
