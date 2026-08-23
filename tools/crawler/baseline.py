"""Crash-baseline load / compare / write helpers (QF-7, Task 2).

The baseline is a JSON file tracking known crash signatures so the CI gate
can fail on *new* signatures without failing on the established corpus.
Schema mirrors the mypy-baseline pattern: fingerprint-keyed, sorted for
stable diffs, human-readable ``note`` field for triage context.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.crawler.crash_record import CrashRecord


def load_baseline(path: str) -> set[str]:
    """Load the set of known crash signatures from a baseline file.

    Missing file → returns empty set (with a note to stderr).
    Malformed JSON → raises ``json.JSONDecodeError``.

    Args:
        path: Path to the baseline JSON file.

    Returns:
        Set of 16-char signature strings from the baseline.
    """
    p = Path(path)
    if not p.exists():
        print(f"baseline not found at {path!r}; treating all crashes as new", file=sys.stderr)
        return set()
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    signatures = data.get("signatures", [])
    return {entry["signature"] for entry in signatures}


def compare(crashes: dict[str, CrashRecord], known: set[str]) -> list[CrashRecord]:
    """Return crashes whose signature is not in *known*, sorted by signature.

    Args:
        crashes: Dict of signature → CrashRecord from the current session.
        known: Set of baseline-known signature strings.

    Returns:
        List of novel CrashRecords, sorted by signature for stable output.
    """
    novel = [record for sig, record in crashes.items() if sig not in known]
    return sorted(novel, key=lambda r: r.signature)


def write_baseline(
    path: str,
    crashes: dict[str, CrashRecord],
    generated_from: list[tuple[int, Optional[str], int]],
    include_from: list[str] | None = None,
) -> None:
    """Write (or overwrite) a crash-baseline JSON file.

    The file is sorted by signature and uses a fixed key order so diffs
    remain stable across regenerations.

    Args:
        path: Destination path for the baseline file. Overwritten if present.
        crashes: Crash records from the current (or primary) session.
        generated_from: List of ``(seed, checkpoint, actions)`` tuples
            describing the sessions that produced the baseline.
        include_from: Optional list of ``crashes.json`` paths to merge
            into the baseline. Useful for aggregating multi-session sweeps.
    """
    # Start with records from the primary crashes dict.
    merged: dict[str, CrashRecord] = dict(crashes)

    # Merge any additional crashes.json files.
    for extra_path in (include_from or []):
        p = Path(extra_path)
        if not p.exists():
            print(f"include_from path not found: {extra_path!r}", file=sys.stderr)
            continue
        with p.open("r", encoding="utf-8") as f:
            extra_data = json.load(f)
        for entry in extra_data.get("crashes", []):
            sig = entry["signature"]
            if sig not in merged:
                merged[sig] = CrashRecord(
                    signature=sig,
                    exception_class=entry.get("exception_class", ""),
                    first_seed=entry.get("first_seed", 0),
                    first_action_index=entry.get("first_action_index", 0),
                    occurrence_count=entry.get("occurrence_count", 1),
                    action_trace=[],
                    full_traceback=entry.get("full_traceback", ""),
                    state_at_crash=entry.get("state_at_crash", ""),
                    oracle=entry.get("oracle", "exception"),
                    extra=entry.get("extra", {}),
                )

    # Produce entries sorted by signature for stable diffs.
    sorted_records = sorted(merged.values(), key=lambda r: r.signature)

    entries = []
    for record in sorted_records:
        entry: dict = {
            "signature": record.signature,
            "exception_class": record.exception_class,
            "oracle": record.oracle,
            "state_at_crash": record.state_at_crash,
            "first_seed": record.first_seed,
            "first_action_index": record.first_action_index,
            "occurrence_count": record.occurrence_count,
        }
        # Include note if present in extra.
        note = record.extra.get("note")
        if note:
            entry["note"] = note
        entries.append(entry)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "generated_at": now_utc,
        "generated_from": [list(t) for t in generated_from],
        "signatures": entries,
    }

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")
