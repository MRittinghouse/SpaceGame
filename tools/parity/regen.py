"""Regenerate every parity golden file (SP2 spec Section 7.7).

Usage:
    python -m tools.parity.regen [--out DIR] [--allow-dirty]

Refuses to run when files outside ``parity/`` are modified, so a golden's
``source_commit`` always names the code that produced it. ``--allow-dirty``
(used by the determinism check) writes anyway and stamps ``<sha>-dirty``.
Each run clears ``<out>/golden/`` first, so a case a driver no longer produces
leaves no file behind. Review the git diff of ``parity/`` before committing a
regen; a regen commit holds only goldens.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from tools.parity import rng_vectors
from tools.parity.driver import REPO_ROOT, Case, dirty_paths_outside, source_commit, write_cases
from tools.parity.drivers import combat as combat_driver
from tools.parity.drivers import crew as crew_driver
from tools.parity.drivers import dialogue as dialogue_driver
from tools.parity.drivers import encounters as encounters_driver
from tools.parity.drivers import galaxy as galaxy_driver
from tools.parity.drivers import market as market_driver
from tools.parity.drivers import missions as missions_driver
from tools.parity.drivers import player as player_driver
from tools.parity.drivers import skills as skills_driver
from tools.parity.drivers import trade as trade_driver
from tools.parity.drivers import travel as travel_driver
from tools.parity.export_schema import write_schema

DRIVERS: list[Callable[[], list[Case]]] = [
    rng_vectors.build_cases,
    market_driver.build_cases,
    skills_driver.build_cases,
    galaxy_driver.build_cases,
    crew_driver.build_cases,
    trade_driver.build_cases,
    player_driver.build_cases,
    travel_driver.build_cases,
    encounters_driver.build_cases,
    combat_driver.build_cases,
    missions_driver.build_cases,
    dialogue_driver.build_cases,
]


def main(argv: list[str] | None = None) -> int:
    """Run every driver and write the goldens and the schema.

    Clears ``<out>/golden/`` before writing. With ``--allow-dirty`` on a tree
    that has changes outside ``parity/``, stamps ``<sha>-dirty`` as each
    golden's ``source_commit``.

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
    head = source_commit()
    commit = f"{head}-dirty" if dirty else head
    cases = [case for build in DRIVERS for case in build()]
    golden_root = out / "golden"
    if golden_root.exists():
        shutil.rmtree(golden_root)
    written = write_cases(cases, golden_root, commit)
    label = f"{head[:10]}-dirty" if dirty else head[:10]
    print(f"Wrote {len(written)} golden files under {golden_root} from {label}")
    write_schema(out / "schema.json")
    print(f"Wrote schema to {out / 'schema.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
