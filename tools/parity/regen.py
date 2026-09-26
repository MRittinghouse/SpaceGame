"""Regenerate every parity golden file (SP2 spec Section 7.7).

Usage:
    python -m tools.parity.regen [--out DIR] [--allow-dirty]

Refuses to run when files outside ``parity/`` are modified, so a golden's
``source_commit`` always names the code that produced it. Review the git diff
of ``parity/`` before committing a regen; a regen commit holds only goldens.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from tools.parity import rng_vectors
from tools.parity.driver import REPO_ROOT, Case, dirty_paths_outside, source_commit, write_cases

DRIVERS: list[Callable[[], list[Case]]] = [rng_vectors.build_cases]


def main(argv: list[str] | None = None) -> int:
    """Run every driver and write the goldens.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on success, 2 when the tree is dirty.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "parity"))
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    dirty = dirty_paths_outside("parity/")
    if dirty and not args.allow_dirty:
        print("Refusing to regenerate goldens with uncommitted changes outside parity/:")
        for path in dirty:
            print(f"  {path}")
        return 2

    out = Path(args.out)
    commit = source_commit()
    cases = [case for build in DRIVERS for case in build()]
    written = write_cases(cases, out / "golden", commit)
    print(f"Wrote {len(written)} golden files under {out / 'golden'} from {commit[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
