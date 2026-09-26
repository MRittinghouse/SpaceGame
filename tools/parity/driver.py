"""Golden trace recording for the Godot parity harness (SP2 spec Section 7)."""

from __future__ import annotations

import json
import math
import struct
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = 1


def float_tag(value: float) -> str:
    """Encode a float as ``f:<repr>:<int64 bits>``.

    Godot's JSON parser misrounds about a quarter of long decimals by one bit, so the
    Godot harness rebuilds each double from its bits; the repr keeps goldens readable.
    """
    bits: int = struct.unpack("<q", struct.pack("<d", value))[0]
    return f"f:{value!r}:{bits}"


def tag_floats(value: object) -> object:
    """Replace every float inside an already-normalized value with its ``float_tag``."""
    if isinstance(value, float):
        return float_tag(value)
    if isinstance(value, dict):
        return {key: tag_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [tag_floats(item) for item in value]
    return value


def normalize(value: object) -> object:
    """Convert a Python value into the JSON shape the Godot comparator expects.

    Args:
        value: A result, argument, or state value.

    Returns:
        JSON-ready value: tuples become lists, enums their value.

    Raises:
        TypeError: For sets (unordered; sort them in the driver), non-string
            dict keys, and unsupported types.
        ValueError: For NaN and infinity.
    """
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"goldens cannot hold {value!r}")
        return value
    if isinstance(value, Enum):
        return normalize(value.value)
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"golden dict keys must be str, got {key!r}")
            out[key] = normalize(item)
        return out
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError("sets are unordered; sort them into a list in the driver")
    raise TypeError(f"cannot write {type(value).__name__} to a golden: {value!r}")


@dataclass
class Case:
    """One golden file: a setup and the recorded calls."""

    subsystem: str
    name: str
    setup: dict[str, object]
    steps: list[dict[str, object]] = field(default_factory=list)

    def record(
        self, call: str, args: list[object], result: object, state: dict[str, object]
    ) -> None:
        """Append one step: the call, its arguments, its result, and the state after it."""
        self.steps.append(
            {
                "call": call,
                "args": normalize(args),
                "result": normalize(result),
                "state": normalize(state),
            }
        )

    def to_json(self, source_commit: str) -> str:
        """Serialize with tagged floats, sorted keys, two-space indent, and a trailing newline."""
        document = {
            "format": FORMAT_VERSION,
            "subsystem": self.subsystem,
            "case": self.name,
            "source_commit": source_commit,
            "setup": tag_floats(normalize(self.setup)),
            "steps": tag_floats(self.steps),
        }
        return (
            json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
            + "\n"
        )


def source_commit() -> str:
    """The commit the goldens are generated from."""
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def porcelain_paths(text: str) -> list[str]:
    """Extract every path named by ``git status --porcelain`` output.

    A rename or copy line (``R`` or ``C`` in either status column) names two
    paths, separated by ``" -> "``; both the old and the new path are
    returned so a boundary crossing (a golden moved out of ``parity/``, or
    unrelated code moved in) is never missed. A quoted path -- git
    C-quotes paths containing spaces or unusual characters -- has its
    surrounding double quotes stripped.

    Args:
        text: The raw stdout of ``git status --porcelain``.

    Returns:
        Every path named by the porcelain output, in order. Rename and
        copy lines contribute both their old and new path.
    """
    paths: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        status, path_part = line[:2], line[3:]
        if "R" in status or "C" in status:
            old, _, new = path_part.partition(" -> ")
            paths.append(old.strip().strip('"'))
            paths.append(new.strip().strip('"'))
        else:
            paths.append(path_part.strip().strip('"'))
    return paths


def dirty_paths_outside(prefix: str) -> list[str]:
    """Modified or untracked paths that do not start with ``prefix``."""
    done = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return [p for p in porcelain_paths(done.stdout) if not p.startswith(prefix)]


def write_cases(cases: list[Case], golden_root: Path, commit: str) -> list[Path]:
    """Write each case to ``golden_root/<subsystem>/<name>.json`` with LF endings."""
    written: list[Path] = []
    for case in cases:
        path = golden_root / case.subsystem / f"{case.name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(case.to_json(commit))
        written.append(path)
    return written
