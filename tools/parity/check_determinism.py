"""Prove the goldens do not depend on PYTHONHASHSEED (SP2 spec Section 7.6).

Runs ``tools.parity.regen`` twice in fresh processes with PYTHONHASHSEED=1
and =2 into temporary directories, then compares every file byte for byte.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.parity.driver import REPO_ROOT


def _regen(out: Path, hash_seed: str) -> None:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    subprocess.run(
        [sys.executable, "-m", "tools.parity.regen", "--out", str(out), "--allow-dirty"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _files(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def main(argv: list[str] | None = None) -> int:
    """Return 0 when both runs match, 1 otherwise (printing the differing files)."""
    with tempfile.TemporaryDirectory() as tmp:
        first, second = Path(tmp) / "one", Path(tmp) / "two"
        _regen(first, "1")
        _regen(second, "2")
        a, b = _files(first), _files(second)
        differing = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    if differing:
        print("Goldens differ between hash seeds:")
        for name in differing:
            print(f"  {name}")
        return 1
    print(f"Byte-identical across hash seeds: {len(a)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
