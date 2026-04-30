"""Parse and update `requirements/roadmap/ROADMAP.md`.

Single-file roadmap with `<h3>` per-sprint sections. Each section starts
with `### SPRINT-ID — Title` and ends at the next `### ` or `## ` header.

This module:
  - Parses the index table at the top to find sprint IDs and statuses
  - Locates a specific sprint section by ID
  - Reads/writes the Status line for a given sprint
  - Appends to a sprint's Activity log
  - Computes eligibility (todo + all dependencies done)
  - Handles roadmap changes the agents make (new sprints added) gracefully
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ralph.config import ROADMAP_PATH, STATUS_DONE, STATUS_TODO

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Sprint section header: `### SA-1 — ...` (h3) or `#### SA-1 — ...` (h4).
# The ID is the token before " — " (an em-dash, deliberate; matches the
# Writing Bible exempt design-doc context). The ID character class
# (uppercase + digits + dashes) excludes phase-level headers like
# `### Phase 0 — Pre-arc Preparation` because "Phase" contains lowercase.
_SPRINT_HEADER_RE = re.compile(r"^(####?) ([A-Z][A-Z0-9-]+)\s+—\s+(.+?)\s*$", re.MULTILINE)

# Status line within a sprint section. Must be on its own line, prefixed
# with `**Status**:`. Captures the value (which may include parens for
# sub-state, e.g., `in-progress (planning)`).
_STATUS_LINE_RE = re.compile(r"^\*\*Status\*\*:\s*(.+?)\s*$", re.MULTILINE)

# Phase line: `**Phase**: Phase I — Cluster B Anchors | **Size**: L | ...`
_PHASE_RE = re.compile(r"\*\*Phase\*\*:\s*(.+?)\s*\|", re.MULTILINE)
_PHASE_RE_END = re.compile(r"\*\*Phase\*\*:\s*(.+?)\s*$", re.MULTILINE)

# Size line: `**Size**: L` or in metadata line `| **Size**: L |`.
_SIZE_RE = re.compile(r"\*\*Size\*\*:\s*([SMLX]+)", re.MULTILINE)

# Depends-on line. Captures the comma-separated list (or "none").
_DEPENDS_RE = re.compile(r"^\*\*Depends on\*\*:\s*(.+?)\s*\|", re.MULTILINE)
_DEPENDS_RE_END = re.compile(r"^\*\*Depends on\*\*:\s*(.+?)\s*$", re.MULTILINE)

# Activity log line. We append underneath the existing items.
_ACTIVITY_LOG_HEADER_RE = re.compile(r"^\*\*Activity log\.\*\*\s*$", re.MULTILINE)


@dataclass
class Sprint:
    """A single sprint section parsed from ROADMAP.md."""

    sprint_id: str
    title: str
    status: str
    depends_on: list[str] = field(default_factory=list)
    phase: str = ""
    size: str = ""
    section_start: int = 0  # byte offset of `### SA-1 ...`
    section_end: int = 0  # byte offset of next `### ` or `## `

    def is_done(self) -> bool:
        return self.status.strip().lower() == STATUS_DONE

    def is_todo(self) -> bool:
        return self.status.strip().lower() == STATUS_TODO


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _read_roadmap() -> str:
    return ROADMAP_PATH.read_text(encoding="utf-8")


def _write_roadmap(content: str) -> None:
    ROADMAP_PATH.write_text(content, encoding="utf-8")


def parse_sprints_from_text(content: str) -> dict[str, Sprint]:
    """Parse sprints from a roadmap-content string.

    Used by validation paths that need to compare snapshots without
    re-reading from disk. Public consumers usually want `parse_sprints`.
    """
    headers = list(_SPRINT_HEADER_RE.finditer(content))
    sprints: dict[str, Sprint] = {}

    for i, m in enumerate(headers):
        # group(1) = "###" or "####" (header depth)
        # group(2) = sprint ID
        # group(3) = sprint title
        sprint_id = m.group(2)
        title = m.group(3).strip()
        section_start = m.start()
        next_header_pos: int | None = None
        if i + 1 < len(headers):
            next_header_pos = headers[i + 1].start()
        h2_match = re.search(r"^## ", content[m.end() :], re.MULTILINE)
        if h2_match is not None:
            h2_pos = m.end() + h2_match.start()
            if next_header_pos is None or h2_pos < next_header_pos:
                next_header_pos = h2_pos
        section_end = next_header_pos if next_header_pos is not None else len(content)

        section_text = content[section_start:section_end]

        status_match = _STATUS_LINE_RE.search(section_text)
        status = status_match.group(1).strip() if status_match else "unknown"

        depends_match = _DEPENDS_RE.search(section_text) or _DEPENDS_RE_END.search(section_text)
        depends_on: list[str] = []
        if depends_match:
            raw = depends_match.group(1).strip()
            if raw.lower() != "none":
                depends_on = [tok.strip() for tok in raw.split(",") if tok.strip()]

        phase_match = _PHASE_RE.search(section_text) or _PHASE_RE_END.search(section_text)
        phase = phase_match.group(1).strip() if phase_match else ""

        size_match = _SIZE_RE.search(section_text)
        size = size_match.group(1).strip() if size_match else ""

        sprints[sprint_id] = Sprint(
            sprint_id=sprint_id,
            title=title,
            status=status,
            depends_on=depends_on,
            phase=phase,
            size=size,
            section_start=section_start,
            section_end=section_end,
        )

    return sprints


def parse_sprints() -> dict[str, Sprint]:
    """Parse all sprints from ROADMAP.md.

    Returns a dict keyed by sprint ID. Section offsets are byte indices
    into the raw file content; use `_read_roadmap()` to access them.
    """
    return parse_sprints_from_text(_read_roadmap())


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def eligible_sprints(sprints: dict[str, Sprint]) -> list[Sprint]:
    """Return the sprints that are `todo` AND have all dependencies `done`.

    Order: same as document order (which preserves the author's intended
    sequencing). The dispatcher takes the first eligible sprint.
    """
    eligible: list[Sprint] = []
    for sprint in sprints.values():
        if not sprint.is_todo():
            continue
        deps_satisfied = True
        for dep_id in sprint.depends_on:
            dep = sprints.get(dep_id)
            if dep is None:
                # Unknown dependency — treat as not-satisfied (safer than
                # silently picking up the sprint).
                deps_satisfied = False
                break
            if not dep.is_done():
                deps_satisfied = False
                break
        if deps_satisfied:
            eligible.append(sprint)

    # Preserve document order (insertion order in dict).
    eligible.sort(key=lambda s: s.section_start)
    return eligible


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------


def update_status(sprint_id: str, new_status: str) -> None:
    """Rewrite the Status line of a sprint section in place.

    Re-reads the file each call so we don't fight concurrent edits from
    the agent. Atomic swap via write-temp + rename would be safer; for
    now the harness is single-threaded so a direct write is fine.
    """
    content = _read_roadmap()
    sprints = parse_sprints()
    sprint = sprints.get(sprint_id)
    if sprint is None:
        raise KeyError(f"Sprint {sprint_id} not found in roadmap")

    section_text = content[sprint.section_start : sprint.section_end]
    new_section = _STATUS_LINE_RE.sub(f"**Status**: {new_status}", section_text, count=1)

    new_content = content[: sprint.section_start] + new_section + content[sprint.section_end :]
    _write_roadmap(new_content)


def append_activity_log(sprint_id: str, line: str) -> None:
    """Append a single line to the sprint's Activity log.

    Format: `- 2026-MM-DD HH:MM — <line>`. The harness uses this for
    its own annotations (phase transitions); agents append separately
    inside their work.
    """
    from datetime import datetime

    content = _read_roadmap()
    sprints = parse_sprints()
    sprint = sprints.get(sprint_id)
    if sprint is None:
        raise KeyError(f"Sprint {sprint_id} not found in roadmap")

    section_text = content[sprint.section_start : sprint.section_end]

    # Find `**Activity log.**` header within this section.
    log_match = _ACTIVITY_LOG_HEADER_RE.search(section_text)
    if log_match is None:
        # Section doesn't have an Activity log block — append one at end.
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_section = section_text.rstrip() + (f"\n\n**Activity log.**\n- {timestamp} — {line}\n")
    else:
        # Find the end of the existing log block (continuous `- ` lines after the header).
        after_header = section_text[log_match.end() :]
        # Take consecutive lines starting with `- ` or empty.
        log_block_match = re.match(r"\n((?:- .*\n|\n)*)", after_header)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        if log_block_match:
            existing_log_block = log_block_match.group(0)
            insert_pos = log_match.end() + len(existing_log_block)
            # If the existing block ends with two newlines, insert our
            # line before them; else insert at the end of the block.
            new_log_line = f"- {timestamp} — {line}\n"
            new_section = (
                section_text[:insert_pos].rstrip("\n")
                + "\n"
                + new_log_line
                + section_text[insert_pos:].lstrip("\n")
            )
            # Ensure we keep section structure (lstrip the rest correctly).
            if not new_section.endswith("\n"):
                new_section += "\n"
        else:
            new_section = section_text + f"\n- {timestamp} — {line}\n"

    new_content = content[: sprint.section_start] + new_section + content[sprint.section_end :]
    _write_roadmap(new_content)


# ---------------------------------------------------------------------------
# Sanity check helpers
# ---------------------------------------------------------------------------


def get_sprint(sprint_id: str) -> Sprint:
    sprints = parse_sprints()
    if sprint_id not in sprints:
        raise KeyError(f"Sprint {sprint_id} not found in roadmap")
    return sprints[sprint_id]


def roadmap_exists() -> bool:
    return ROADMAP_PATH.exists()


# ---------------------------------------------------------------------------
# Last phase report parsing (item 6 — telemetry)
# ---------------------------------------------------------------------------

# The agents are instructed to append a `**Last phase report.**` block at
# the end of each phase. The block has structured `- key: value` fields.
# We parse it so the harness can persist these fields in state.json for
# cross-run telemetry without scraping markdown after the fact.

_PHASE_REPORT_HEADER_RE = re.compile(r"^\*\*Last phase report\.\*\*\s*$", re.MULTILINE)
_PHASE_REPORT_FIELD_RE = re.compile(r"^-\s+([A-Za-z_][A-Za-z0-9_ ]*?)\s*:\s*(.+?)\s*$")


def parse_last_phase_report(sprint_id: str) -> dict[str, str]:
    """Extract the **Last phase report.** block fields for a sprint.

    Returns a dict of `{field_name_normalized: value}` where field names are
    lowercased and have spaces replaced with underscores (so "Findings_critical"
    becomes "findings_critical"). Returns empty dict if no report block.

    Field names are kept loose because agents have varied slightly (the
    same field appears as "Findings_critical", "Findings critical", etc.
    across runs). The normalization swallows that variance.
    """
    try:
        sprint = get_sprint(sprint_id)
    except KeyError:
        return {}
    content = _read_roadmap()
    section = content[sprint.section_start : sprint.section_end]
    return _parse_phase_report_from_section(section)


def _parse_phase_report_from_section(section_text: str) -> dict[str, str]:
    """Pure-function variant for testability (takes section text directly)."""
    headers = list(_PHASE_REPORT_HEADER_RE.finditer(section_text))
    if not headers:
        return {}
    # Use the LAST header — the agent prompts say to overwrite prior reports,
    # but if multiple slipped through we want the most recent.
    last_header = headers[-1]
    after_header = section_text[last_header.end() :]
    fields: dict[str, str] = {}
    for line in after_header.splitlines():
        if not line.strip():
            # Empty line — could be intentional whitespace before the next block.
            # Continue scanning rather than break, since some agents leave a
            # blank line between fields.
            continue
        if not line.startswith("-"):
            # Hit non-field content; stop parsing this report.
            break
        m = _PHASE_REPORT_FIELD_RE.match(line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            fields[key] = m.group(2).strip()
    return fields


# ---------------------------------------------------------------------------
# Snapshot + validation (items B + C)
# ---------------------------------------------------------------------------


def snapshot_roadmap() -> str:
    """Return the current ROADMAP.md content as a string (snapshot for restore)."""
    return _read_roadmap()


def restore_roadmap(snapshot: str) -> None:
    """Write a previously-captured snapshot back to ROADMAP.md."""
    _write_roadmap(snapshot)


class RoadmapValidationError(Exception):
    """Raised when post-agent validation detects roadmap corruption or
    out-of-claim modifications. The harness restores the snapshot and
    marks the sprint blocked with the validation reason.
    """


def validate_post_agent(
    snapshot: str,
    claimed_sprint_id: str,
    phase_allows_new_sprints: bool,
) -> None:
    """Validate the current ROADMAP.md against a pre-agent snapshot.

    Checks:
      1. The current file parses cleanly (no markdown corruption).
      2. The claimed sprint still exists.
      3. No sprint other than the claimed one was modified, EXCEPT new
         sprints added when the phase allows it (planner / reviewer).
      4. No sprint that existed in the snapshot was deleted.

    Raises RoadmapValidationError on violation. Caller is responsible
    for restoring the snapshot.
    """
    try:
        current_text = _read_roadmap()
    except OSError as e:
        raise RoadmapValidationError(f"could not read ROADMAP.md: {e}") from e

    try:
        snap_sprints = parse_sprints_from_text(snapshot)
        curr_sprints = parse_sprints_from_text(current_text)
    except Exception as e:  # broad: parsing should never raise but be defensive
        raise RoadmapValidationError(f"parse failure on validation: {e}") from e

    # Check 2: claimed sprint still exists.
    if claimed_sprint_id not in curr_sprints:
        raise RoadmapValidationError(f"claimed sprint {claimed_sprint_id} disappeared from roadmap")

    # Check 4: no snapshot sprint was deleted.
    deleted = set(snap_sprints.keys()) - set(curr_sprints.keys())
    if deleted:
        raise RoadmapValidationError(f"sprints deleted by agent: {sorted(deleted)}")

    # Check 3: no non-claimed existing sprint was modified.
    # Compare section text after stripping trailing whitespace, because
    # section_end byte offsets shift when new sprints are appended at end-of-file
    # even though the actual content of the existing sprint didn't change.
    modified_violations: list[str] = []
    for sid in snap_sprints:
        if sid == claimed_sprint_id:
            continue  # Agent owns its claimed sprint.
        if sid not in curr_sprints:
            continue  # Already covered by deletion check above.
        snap_section = snapshot[
            snap_sprints[sid].section_start : snap_sprints[sid].section_end
        ].rstrip()
        curr_section = current_text[
            curr_sprints[sid].section_start : curr_sprints[sid].section_end
        ].rstrip()
        if snap_section != curr_section:
            modified_violations.append(sid)
    if modified_violations:
        raise RoadmapValidationError(
            f"sprints modified outside claim: {sorted(modified_violations)}. "
            f"Claimed sprint was {claimed_sprint_id}."
        )

    # Check 5: new sprints added — only allowed in phases where it makes sense.
    new_sprints = set(curr_sprints.keys()) - set(snap_sprints.keys())
    if new_sprints and not phase_allows_new_sprints:
        raise RoadmapValidationError(
            f"agent added new sprints in a phase that disallows it: {sorted(new_sprints)}"
        )


# ---------------------------------------------------------------------------
# Index regeneration (item J)
# ---------------------------------------------------------------------------

# Markers around the auto-generated SA-arc index table. Anything between
# is replaced by `regenerate_index()`. Followups index stays
# hand-maintained because some columns (e.g., "Source") aren't structural.
_INDEX_MARKER_START = "<!-- AUTO_GENERATED_SA_INDEX_START -->"
_INDEX_MARKER_END = "<!-- AUTO_GENERATED_SA_INDEX_END -->"


def _build_sa_index_table(sprints: dict[str, Sprint]) -> str:
    """Build the markdown table of SA-prefixed sprints in document order."""
    sa_sprints = [s for s in sprints.values() if s.sprint_id.startswith("SA-")]
    sa_sprints.sort(key=lambda s: s.section_start)

    lines = [
        "| ID | Title | Phase | Size | Status | Depends on |",
        "|---|---|---|---|---|---|",
    ]
    for s in sa_sprints:
        anchor_slug = s.sprint_id.lower()
        title_slug = re.sub(r"[^a-z0-9 -]", "", s.title.lower()).replace(" ", "-")
        # Markdown anchors: GitHub-flavored uses lowercased text with hyphens.
        anchor = f"#{anchor_slug}--{title_slug}"
        deps = ", ".join(s.depends_on) if s.depends_on else "none"
        # Truncate phase to a short label for the table (the `Phase I — Cluster B`
        # format the doc uses gets noisy).
        phase_short = s.phase
        if "Phase " in phase_short:
            # Strip "Phase " prefix and take only the first token (e.g., "I", "0", "A").
            phase_short = phase_short.replace("Phase ", "").split(" ")[0]
        lines.append(
            f"| [{s.sprint_id}]({anchor}) | {s.title} | {phase_short} | "
            f"{s.size or '?'} | {s.status} | {deps} |"
        )
    return "\n".join(lines)


def regenerate_index() -> bool:
    """Rebuild the auto-generated SA-arc index table in ROADMAP.md.

    Looks for `<!-- AUTO_GENERATED_SA_INDEX_START -->` ...
    `<!-- AUTO_GENERATED_SA_INDEX_END -->` markers and replaces the
    content between with a freshly generated table from the parsed
    sprint sections.

    Returns True if regeneration ran (markers found and content updated),
    False if markers are absent (the harness logs and continues — the
    file's hand-maintained, that's fine).
    """
    content = _read_roadmap()
    start_idx = content.find(_INDEX_MARKER_START)
    end_idx = content.find(_INDEX_MARKER_END)
    if start_idx < 0 or end_idx < 0 or end_idx < start_idx:
        return False

    sprints = parse_sprints_from_text(content)
    new_table = _build_sa_index_table(sprints)

    new_content = (
        content[: start_idx + len(_INDEX_MARKER_START)]
        + "\n"
        + new_table
        + "\n"
        + content[end_idx:]
    )
    _write_roadmap(new_content)
    return True
