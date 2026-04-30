"""Tests for ralph.roadmap_state.

Covers:
  - parse_sprints_from_text: header detection, status extraction, deps
  - eligible_sprints: dependency satisfaction, todo-only filter
  - snapshot/restore round-trip
  - validate_post_agent: every violation type
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from ralph import roadmap_state
from ralph.roadmap_state import RoadmapValidationError, Sprint


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_ROADMAP_TWO_SPRINTS = """\
# Test Roadmap

## Index

| ID | Title | Status |
|---|---|---|
| [SA-1](#sa-1) | First | todo |
| [SA-2](#sa-2) | Second | todo |

## Body

### SA-1 — First sprint

**Status**: todo
**Phase**: I | **Size**: M
**Depends on**: none | **Blocks**: SA-2

**Goal.** First sprint goal.

**Activity log.**
- 2026-04-26 — todo (created)


### SA-2 — Second sprint

**Status**: todo
**Phase**: I | **Size**: S
**Depends on**: SA-1 | **Blocks**: none

**Goal.** Second sprint goal.

**Activity log.**
- 2026-04-26 — todo (created)
"""


_ROADMAP_WITH_DONE = _ROADMAP_TWO_SPRINTS.replace(
    "**Status**: todo\n**Phase**: I | **Size**: M\n**Depends on**: none",
    "**Status**: done\n**Phase**: I | **Size**: M\n**Depends on**: none",
    1,
)


@pytest.fixture
def roadmap_in_tmp(tmp_path, monkeypatch):
    """Point ROADMAP_PATH at a temp file with controlled content."""
    roadmap_file = tmp_path / "ROADMAP.md"
    roadmap_file.write_text(_ROADMAP_TWO_SPRINTS, encoding="utf-8")
    monkeypatch.setattr(roadmap_state, "ROADMAP_PATH", roadmap_file)
    # roadmap_state imports ROADMAP_PATH from config; patching the module
    # attribute is sufficient for the helpers that read it directly.
    return roadmap_file


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseSprintsFromText:
    def test_finds_both_sprints(self) -> None:
        sprints = roadmap_state.parse_sprints_from_text(_ROADMAP_TWO_SPRINTS)
        assert set(sprints.keys()) == {"SA-1", "SA-2"}

    def test_status_extraction(self) -> None:
        sprints = roadmap_state.parse_sprints_from_text(_ROADMAP_WITH_DONE)
        assert sprints["SA-1"].status == "done"
        assert sprints["SA-2"].status == "todo"

    def test_depends_on_extraction_pipe_terminated(self) -> None:
        sprints = roadmap_state.parse_sprints_from_text(_ROADMAP_TWO_SPRINTS)
        # SA-1 has "Depends on: none |" — should parse to empty list
        assert sprints["SA-1"].depends_on == []
        # SA-2 has "Depends on: SA-1 |"
        assert sprints["SA-2"].depends_on == ["SA-1"]

    def test_phase_headers_not_parsed_as_sprints(self) -> None:
        """`### Phase 0 — Pre-arc Preparation` shouldn't be parsed as a sprint
        because the ID character class excludes lowercase like 'Phase'."""
        text = _ROADMAP_TWO_SPRINTS + "\n\n### Phase 0 — Pre-arc Preparation\n"
        sprints = roadmap_state.parse_sprints_from_text(text)
        assert "Phase" not in sprints
        assert set(sprints.keys()) == {"SA-1", "SA-2"}

    def test_h4_sprint_header_supported(self) -> None:
        """Sprints can be at h4 (under a phase h3)."""
        text = """\
## Arc

### Phase A

#### SA-A1 — Sub-sprint

**Status**: todo
**Depends on**: none
"""
        sprints = roadmap_state.parse_sprints_from_text(text)
        assert "SA-A1" in sprints

    def test_empty_text_returns_empty_dict(self) -> None:
        assert roadmap_state.parse_sprints_from_text("") == {}


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


class TestEligibleSprints:
    def test_todo_with_no_deps_is_eligible(self) -> None:
        sprints = roadmap_state.parse_sprints_from_text(_ROADMAP_TWO_SPRINTS)
        eligible = roadmap_state.eligible_sprints(sprints)
        assert any(s.sprint_id == "SA-1" for s in eligible)

    def test_todo_with_unmet_dep_not_eligible(self) -> None:
        sprints = roadmap_state.parse_sprints_from_text(_ROADMAP_TWO_SPRINTS)
        eligible = roadmap_state.eligible_sprints(sprints)
        assert not any(s.sprint_id == "SA-2" for s in eligible)

    def test_done_dep_unblocks(self) -> None:
        sprints = roadmap_state.parse_sprints_from_text(_ROADMAP_WITH_DONE)
        eligible = roadmap_state.eligible_sprints(sprints)
        # SA-1 is done now; SA-2 should be eligible.
        eligible_ids = {s.sprint_id for s in eligible}
        assert "SA-2" in eligible_ids
        # SA-1 not eligible (it's done, not todo).
        assert "SA-1" not in eligible_ids

    def test_unknown_dep_blocks(self) -> None:
        text = _ROADMAP_TWO_SPRINTS.replace("Depends on**: SA-1", "Depends on**: SA-MISSING")
        sprints = roadmap_state.parse_sprints_from_text(text)
        eligible = roadmap_state.eligible_sprints(sprints)
        assert not any(s.sprint_id == "SA-2" for s in eligible)


# ---------------------------------------------------------------------------
# Snapshot / restore
# ---------------------------------------------------------------------------


class TestSnapshotRestore:
    def test_round_trip(self, roadmap_in_tmp) -> None:
        original = roadmap_state.snapshot_roadmap()
        roadmap_in_tmp.write_text("CORRUPTED", encoding="utf-8")
        roadmap_state.restore_roadmap(original)
        assert roadmap_in_tmp.read_text(encoding="utf-8") == _ROADMAP_TWO_SPRINTS


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidatePostAgent:
    def test_no_changes_passes(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # No changes to the file. Validate.
        roadmap_state.validate_post_agent(
            snapshot=snapshot,
            claimed_sprint_id="SA-1",
            phase_allows_new_sprints=False,
        )

    def test_claimed_sprint_modification_passes(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # Modify SA-1's section (the claimed sprint).
        modified = roadmap_in_tmp.read_text(encoding="utf-8").replace(
            "**Goal.** First sprint goal.",
            "**Goal.** First sprint goal — updated by agent.",
        )
        roadmap_in_tmp.write_text(modified, encoding="utf-8")
        # Should pass — claimed sprint modifications are allowed.
        roadmap_state.validate_post_agent(
            snapshot=snapshot,
            claimed_sprint_id="SA-1",
            phase_allows_new_sprints=False,
        )

    def test_other_sprint_modification_fails(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # Modify SA-2's section while claiming SA-1.
        modified = roadmap_in_tmp.read_text(encoding="utf-8").replace(
            "**Goal.** Second sprint goal.",
            "**Goal.** SECOND SPRINT TAMPERED.",
        )
        roadmap_in_tmp.write_text(modified, encoding="utf-8")
        with pytest.raises(RoadmapValidationError, match="SA-2"):
            roadmap_state.validate_post_agent(
                snapshot=snapshot,
                claimed_sprint_id="SA-1",
                phase_allows_new_sprints=False,
            )

    def test_deletion_fails(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # Delete SA-2's section entirely.
        modified = roadmap_in_tmp.read_text(encoding="utf-8").split("### SA-2 — Second sprint")[0]
        roadmap_in_tmp.write_text(modified, encoding="utf-8")
        with pytest.raises(RoadmapValidationError, match="deleted"):
            roadmap_state.validate_post_agent(
                snapshot=snapshot,
                claimed_sprint_id="SA-1",
                phase_allows_new_sprints=False,
            )

    def test_new_sprint_disallowed_in_implement(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # Add a new sprint section.
        new_section = """

### SA-3 — Newly added by misbehaving agent

**Status**: todo
**Depends on**: none
"""
        modified = roadmap_in_tmp.read_text(encoding="utf-8") + new_section
        roadmap_in_tmp.write_text(modified, encoding="utf-8")
        with pytest.raises(RoadmapValidationError, match="new sprints"):
            roadmap_state.validate_post_agent(
                snapshot=snapshot,
                claimed_sprint_id="SA-1",
                phase_allows_new_sprints=False,
            )

    def test_new_sprint_allowed_in_plan_review(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # Add a new sprint — allowed when planner / reviewer.
        new_section = """

### SA-3 — New sprint authored by planner

**Status**: todo
**Depends on**: none
"""
        modified = roadmap_in_tmp.read_text(encoding="utf-8") + new_section
        roadmap_in_tmp.write_text(modified, encoding="utf-8")
        # Should pass.
        roadmap_state.validate_post_agent(
            snapshot=snapshot,
            claimed_sprint_id="SA-1",
            phase_allows_new_sprints=True,
        )

    def test_claimed_sprint_disappears_fails(self, roadmap_in_tmp) -> None:
        snapshot = roadmap_state.snapshot_roadmap()
        # Delete SA-1 entirely (the claimed sprint!).
        modified = roadmap_in_tmp.read_text(encoding="utf-8")
        # Replace the SA-1 section with nothing.
        sa1_start = modified.index("### SA-1")
        sa1_end = modified.index("### SA-2")
        modified = modified[:sa1_start] + modified[sa1_end:]
        roadmap_in_tmp.write_text(modified, encoding="utf-8")
        with pytest.raises(RoadmapValidationError, match="disappeared"):
            roadmap_state.validate_post_agent(
                snapshot=snapshot,
                claimed_sprint_id="SA-1",
                phase_allows_new_sprints=True,
            )


# ---------------------------------------------------------------------------
# Status mutations
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    def test_writes_new_status(self, roadmap_in_tmp) -> None:
        roadmap_state.update_status("SA-1", "in-progress (planning)")
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-1"].status == "in-progress (planning)"

    def test_only_target_sprint_changes(self, roadmap_in_tmp) -> None:
        roadmap_state.update_status("SA-1", "blocked")
        sprints = roadmap_state.parse_sprints()
        assert sprints["SA-1"].status == "blocked"
        assert sprints["SA-2"].status == "todo"  # untouched

    def test_unknown_sprint_raises(self, roadmap_in_tmp) -> None:
        with pytest.raises(KeyError):
            roadmap_state.update_status("SA-MISSING", "todo")


# ---------------------------------------------------------------------------
# parse_last_phase_report (item 6 — telemetry)
# ---------------------------------------------------------------------------


class TestParseLastPhaseReport:
    """Extract structured `**Last phase report.**` fields for cross-run telemetry."""

    _SECTION_WITH_REPORT = """\
### SA-1 — First sprint

**Status**: done

**Activity log.**
- 2026-04-26 — todo
- 2026-04-26 14:00 — review complete. PHASE_OK

**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 13:30
- Completed: 2026-04-26 14:00
- Files_changed: spacegame/models/foo.py
- Commits: abc1234
- Tests_passing: 8420
- Acceptance_criteria_verified: 8/8
- Findings_critical: 0
- Findings_minor_fixed_directly: 1
- Single_tighten: Comment at file.py:115 explains WHAT, not WHY.
- Notes: clean review
"""

    _SECTION_NO_REPORT = """\
### SA-1 — First

**Status**: todo

**Activity log.**
- 2026-04-26 — todo (created)
"""

    def test_parses_all_fields(self) -> None:
        fields = roadmap_state._parse_phase_report_from_section(self._SECTION_WITH_REPORT)
        assert fields["phase"] == "review"
        assert fields["outcome"] == "PHASE_OK"
        assert fields["tests_passing"] == "8420"
        assert fields["acceptance_criteria_verified"] == "8/8"
        assert fields["findings_critical"] == "0"
        assert fields["findings_minor_fixed_directly"] == "1"
        assert "WHAT" in fields["single_tighten"]
        assert fields["notes"] == "clean review"

    def test_normalizes_field_names(self) -> None:
        # "Findings_critical" -> "findings_critical", "Files_changed" -> "files_changed"
        fields = roadmap_state._parse_phase_report_from_section(self._SECTION_WITH_REPORT)
        assert "files_changed" in fields
        assert "findings_critical" in fields
        # No uppercase keys leaked through.
        assert all(k == k.lower() for k in fields)

    def test_returns_empty_when_no_report(self) -> None:
        fields = roadmap_state._parse_phase_report_from_section(self._SECTION_NO_REPORT)
        assert fields == {}

    def test_returns_empty_for_missing_sprint(self, roadmap_in_tmp) -> None:
        # Sprint that doesn't exist — should return empty dict, not raise.
        fields = roadmap_state.parse_last_phase_report("NONEXISTENT")
        assert fields == {}
