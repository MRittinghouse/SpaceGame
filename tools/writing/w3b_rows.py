"""Plan W3b-S's rows: every line of data/ the writing chunk W3b rewrites.

Each row names a data file, a gate path (``tests.writing_gates.surfaces``' convention), the line
there at SpaceGame 9c0be571, the new line, its group, its reference (a flag, a ruling or a
residual) and why. ``apply --group G`` swaps each of the group's rows into the data in the file's
own escaping and line endings (``tools.writing.w2_audit.swap_at``), refusing a row whose line is
neither its old nor its new one; ``check`` proves the groups applied hold their new lines;
``read`` renders the reading copy the author reads before W3b merges (the chunk map).

Usage, from the repo root:
    python -m tools.writing.w3b_rows apply --group price
    python -m tools.writing.w3b_rows check --group price --group gesture
    python -m tools.writing.w3b_rows read --out ../w3b-read.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tests.writing_gates import surfaces
from tools.writing.w2_audit import swap_at

ROWS = Path(__file__).resolve().parent / "w3b_rows.json"
ROOT = surfaces.PROJECT_ROOT
GROUPS = (
    "price",
    "gesture",
    "truth",
    "residual",
    "first_sale",
    "flags",
    "log",
    "surrender",
    "skill",
    "data",
)


@dataclass(frozen=True)
class Row:
    """One rewritten line: where it is, what it was, what it becomes, and why."""

    file: str
    path: str
    old: str
    new: str
    group: str
    ref: str
    why: str


def load_rows(path: Path = ROWS) -> list[Row]:
    """The rows, in file order.

    Args:
        path: The rows file.

    Returns:
        Every row.
    """
    return [Row(**entry) for entry in json.loads(path.read_text(encoding="utf-8"))]


def _held(root: Path, file: str, path: str) -> object:
    return surfaces.resolve(json.loads((root / file).read_bytes().decode("utf-8")), path)


def apply_rows(rows: Iterable[Row], root: Path = ROOT) -> int:
    """Swap each row's new line into its file; a row already applied is skipped.

    Args:
        rows: The rows to apply.
        root: The repo root.

    Returns:
        How many lines changed.

    Raises:
        ValueError: A row's path holds neither its old nor its new line.
    """
    changed = 0
    for row in rows:
        target = root / row.file
        raw = target.read_bytes().decode("utf-8")
        held = surfaces.resolve(json.loads(raw), row.path)
        if held == row.new:
            continue
        if held != row.old:
            raise ValueError(f"{row.file} {row.path}: the line moved since the plan: {held!r}")
        target.write_bytes(swap_at(raw, row.path, row.old, row.new).encode("utf-8"))
        changed += 1
    return changed


def apply_group(group: str, root: Path = ROOT) -> int:
    """Apply every row of a group.

    Args:
        group: One of GROUPS.
        root: The repo root.

    Returns:
        How many lines changed.

    Raises:
        ValueError: The group is not one of GROUPS.
    """
    if group not in GROUPS:
        raise ValueError(f"no group {group}")
    return apply_rows([row for row in load_rows() if row.group == group], root)


def row_problems(rows: Iterable[Row], root: Path = ROOT) -> list[str]:
    """What is wrong with applied rows: each path must hold its new line.

    Args:
        rows: The rows that should be applied.
        root: The repo root.

    Returns:
        One message per row whose path does not hold its new line.
    """
    return [
        f"{row.file} {row.path}: the data does not hold the new line"
        for row in rows
        if _held(root, row.file, row.path) != row.new
    ]


def problems(groups: Iterable[str], root: Path = ROOT) -> list[str]:
    """``row_problems`` for every row of the groups.

    Args:
        groups: Groups that should be applied.
        root: The repo root.

    Returns:
        The messages.

    Raises:
        ValueError: A group is not one of GROUPS.
    """
    wanted = set(groups)
    unknown = sorted(wanted - set(GROUPS))
    if unknown:
        raise ValueError(f"no group {', '.join(unknown)}")
    return row_problems([row for row in load_rows() if row.group in wanted], root)


def render(rows: list[Row]) -> str:
    """The reading copy: each row's file, path, reference, old line, new line and why.

    Args:
        rows: The rows to show.

    Returns:
        Markdown.
    """
    out = ["# Writing W3b: the lines, old and new", ""]
    for group in GROUPS:
        chosen = [row for row in rows if row.group == group]
        if not chosen:
            continue
        out += [f"## {group} ({len(chosen)})", ""]
        for row in chosen:
            out += [
                f"### {row.file} `{row.path}` ({row.ref})",
                "",
                f"- Was: {row.old}",
                f"- Now: {row.new}",
                f"- Why: {row.why}",
                "",
            ]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    """The command line.

    Args:
        argv: Arguments, or None for sys.argv.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(prog="python -m tools.writing.w3b_rows")
    commands = parser.add_subparsers(dest="command", required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--group", required=True, choices=GROUPS)
    check = commands.add_parser("check")
    check.add_argument("--group", action="append", required=True, choices=GROUPS)
    read = commands.add_parser("read")
    read.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "apply":
        print(f"{apply_group(args.group)} lines changed")
        return 0
    if args.command == "check":
        found = problems(args.group)
        print("\n".join(found) if found else "every row holds its new line")
        return 1 if found else 0
    args.out.write_text(render(load_rows()), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
