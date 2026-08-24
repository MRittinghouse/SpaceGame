"""Sync the Status column of every ROADMAP.md index row to its sprint section.

## Why this exists

`ROADMAP.md` opens with index tables that the doc's own instructions tell a
human to "scan for arc-level progress." Only the SA-arc table is
auto-regenerated (``ralph.roadmap_state.regenerate_index`` works between
``AUTO_GENERATED_SA_INDEX`` markers). Every other table -- Followups, QF -- is
hand-maintained, so it drifts the moment a sprint's status changes.

On 2026-08-24 that drift was total: all ten QF sprints and five of six
Followups showed ``todo`` in the index while their sections said ``done``.
Anyone reading the index -- human or agent -- got a false picture of what was
left to do, which is exactly the failure the index exists to prevent.

## Why only the Status cell

The tables do not share a schema. SA uses ``| ID | Title | Phase | Size |
Status | Depends on |`` while Followups and QF use ``Source`` in the third
column. Rewriting whole rows would mean teaching this script every table's
shape and keeping that knowledge in sync too. Rewriting only the Status cell
needs no schema knowledge beyond locating a row by its sprint ID, so it works
for any table that exists now or later.

Run standalone to fix drift::

    python scripts/sync_roadmap_index.py            # rewrite in place
    python scripts/sync_roadmap_index.py --check    # exit 1 if drifted

``tests/test_compliance/test_roadmap_index_sync.py`` runs the check so drift
fails the suite rather than quietly misinforming the next reader.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = PROJECT_ROOT / "requirements" / "roadmap" / "ROADMAP.md"

# A sprint section heading. NOTE the level varies: the SA arc uses h4
# ("#### SA-1 — ...") because h3 is taken by its Phase groupings, while
# Followups and QF use h3 directly. CONVENTIONS.md documents only the h3 form,
# which is what made this drift invisible for so long -- a scan written from
# the docs finds no SA sprints at all and reports every SA row as orphaned.
_SECTION_RE = re.compile(r"^#{3,4} ([A-Z][A-Z0-9-]*) — ", re.MULTILINE)
# The Status line inside a section: "**Status**: done"
_STATUS_RE = re.compile(r"^\*\*Status\*\*:\s*(.+?)\s*$", re.MULTILINE)
# An index row: "| [QF-1](#anchor) | Title | Source | S | todo | none |"
_ROW_RE = re.compile(r"^\|\s*\[([A-Z][A-Z0-9-]*)\]\([^)]*\)\s*\|(.*)$", re.MULTILINE)


def section_statuses(text: str) -> dict[str, str]:
    """Map sprint ID -> the status declared in that sprint's own section."""
    statuses: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        sprint_id = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end]
        status_match = _STATUS_RE.search(body)
        if status_match:
            # Strip any parenthetical detail: "in-progress (implementing)".
            statuses[sprint_id] = status_match.group(1).split("(")[0].strip()
    return statuses


def sync(text: str) -> tuple[str, list[str]]:
    """Rewrite index-row Status cells to match sections.

    Returns:
        (new_text, drift_descriptions). ``drift_descriptions`` is empty when
        the index already agreed with every section.
    """
    statuses = section_statuses(text)
    drift: list[str] = []

    def fix_row(m: re.Match[str]) -> str:
        sprint_id = m.group(1)
        true_status = statuses.get(sprint_id)
        if true_status is None:
            # Row pointing at a sprint with no section at all. That is a
            # different (worse) defect than status drift, so report it and
            # leave the row alone rather than guessing. No such case exists
            # today -- SA-F2 looked like one only because this scan originally
            # missed h4 headings.
            drift.append(f"{sprint_id}: index row has no matching section")
            return m.group(0)

        cells = m.group(0).split("|")
        # cells[0] is "" (leading pipe). Status is the 5th data cell => index 5.
        if len(cells) < 7:
            return m.group(0)
        current = cells[5].strip()
        if current == true_status:
            return m.group(0)
        drift.append(f"{sprint_id}: index says {current!r}, section says {true_status!r}")
        cells[5] = f" {true_status} "
        return "|".join(cells)

    return _ROW_RE.sub(fix_row, text), drift


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift and exit 1 without writing.",
    )
    args = parser.parse_args()

    text = ROADMAP_PATH.read_text(encoding="utf-8")
    new_text, drift = sync(text)

    if not drift:
        print("roadmap index is in sync")
        return 0

    for d in drift:
        print(f"  drift: {d}")

    if args.check:
        print(f"\n{len(drift)} drifted row(s). Run scripts/sync_roadmap_index.py to fix.")
        return 1

    ROADMAP_PATH.write_text(new_text, encoding="utf-8")
    print(f"\nsynced {len(drift)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
