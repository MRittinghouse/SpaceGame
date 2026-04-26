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
_SPRINT_HEADER_RE = re.compile(
    r"^(####?) ([A-Z][A-Z0-9-]+)\s+—\s+(.+?)\s*$", re.MULTILINE
)

# Status line within a sprint section. Must be on its own line, prefixed
# with `**Status**:`. Captures the value (which may include parens for
# sub-state, e.g., `in-progress (planning)`).
_STATUS_LINE_RE = re.compile(r"^\*\*Status\*\*:\s*(.+?)\s*$", re.MULTILINE)

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


def parse_sprints() -> dict[str, Sprint]:
    """Parse all sprints from ROADMAP.md.

    Returns a dict keyed by sprint ID. Section offsets are byte indices
    into the raw file content; use `_read_roadmap()` to access them.
    """
    content = _read_roadmap()
    headers = list(_SPRINT_HEADER_RE.finditer(content))
    sprints: dict[str, Sprint] = {}

    for i, m in enumerate(headers):
        # group(1) = "###" or "####" (header depth, kept for future use)
        # group(2) = sprint ID
        # group(3) = sprint title
        sprint_id = m.group(2)
        title = m.group(3).strip()
        section_start = m.start()
        # Section ends at the next `### ` or `## ` header, whichever comes first.
        # Look for the next h3 or h2 after this position.
        next_header_pos: int | None = None
        if i + 1 < len(headers):
            next_header_pos = headers[i + 1].start()
        # Also check for `## ` between this h3 and the next h3.
        h2_match = re.search(r"^## ", content[m.end() :], re.MULTILINE)
        if h2_match is not None:
            h2_pos = m.end() + h2_match.start()
            if next_header_pos is None or h2_pos < next_header_pos:
                next_header_pos = h2_pos
        section_end = next_header_pos if next_header_pos is not None else len(content)

        section_text = content[section_start:section_end]

        # Extract status (first match — there's exactly one per sprint).
        status_match = _STATUS_LINE_RE.search(section_text)
        status = status_match.group(1).strip() if status_match else "unknown"

        # Extract depends-on (handle both pipe-terminated and end-of-line forms).
        depends_match = _DEPENDS_RE.search(section_text) or _DEPENDS_RE_END.search(section_text)
        depends_on: list[str] = []
        if depends_match:
            raw = depends_match.group(1).strip()
            if raw.lower() != "none":
                depends_on = [
                    tok.strip() for tok in raw.split(",") if tok.strip()
                ]

        sprints[sprint_id] = Sprint(
            sprint_id=sprint_id,
            title=title,
            status=status,
            depends_on=depends_on,
            section_start=section_start,
            section_end=section_end,
        )

    return sprints


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
    new_section = _STATUS_LINE_RE.sub(
        f"**Status**: {new_status}", section_text, count=1
    )

    new_content = (
        content[: sprint.section_start] + new_section + content[sprint.section_end :]
    )
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
        new_section = section_text.rstrip() + (
            f"\n\n**Activity log.**\n- {timestamp} — {line}\n"
        )
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

    new_content = (
        content[: sprint.section_start] + new_section + content[sprint.section_end :]
    )
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
