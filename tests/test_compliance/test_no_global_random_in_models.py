"""Compliance Scanner: simulation randomness in models goes through SimRng.

See ``docs/superpowers/specs/2026-09-26-sp2-foundation-design.md`` Section 4.3.

The Godot port replays model behavior against golden traces. That only works
if every draw comes from ``spacegame.sim_rng.SimRng``: the global ``random``
module is shared with particles (frame-rate dependent) and ``hash()`` is
salted per process. No allowlist.
"""

from __future__ import annotations

import ast
from pathlib import Path

MODELS_ROOT = Path(__file__).resolve().parent.parent.parent / "spacegame" / "models"


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    hash_methods: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__hash__":
            hash_methods.update(id(n) for n in ast.walk(node))
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random" or alias.name.startswith("numpy.random"):
                    hits.append(f"{path.name}:{line}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module in ("random", "numpy.random"):
            hits.append(f"{path.name}:{line}: from {node.module} import ...")
        elif isinstance(node, ast.Attribute):
            base = node.value
            if isinstance(base, ast.Name) and base.id in ("random", "_rng"):
                hits.append(f"{path.name}:{line}: {base.id}.{node.attr}")
            if isinstance(base, ast.Attribute) and base.attr == "random":
                if isinstance(base.value, ast.Name) and base.value.id in ("np", "numpy"):
                    hits.append(f"{path.name}:{line}: numpy.random.{node.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "hash" and id(node) not in hash_methods:
                hits.append(f"{path.name}:{line}: hash(...)")
    return hits


# spacegame/models/ holds over 100 modules; a scan of fewer means the glob
# missed (a moved directory, a wrong root) and the pass would be vacuous.
MIN_FILES_SCANNED = 30


def test_models_use_only_sim_rng() -> None:
    paths = sorted(MODELS_ROOT.glob("*.py"))
    assert len(paths) >= MIN_FILES_SCANNED, (
        f"scanned only {len(paths)} files under {MODELS_ROOT}; the scanner is not looking "
        "at the models"
    )
    hits: list[str] = []
    for path in paths:
        hits.extend(_violations(path))
    assert not hits, "Global randomness in models (use spacegame.sim_rng.SimRng):\n" + "\n".join(
        hits
    )


def test_scanner_flags_a_planted_violation(tmp_path: Path) -> None:
    canary = tmp_path / "canary.py"
    canary.write_text(
        "import random\n\n\ndef roll(x: object) -> int:\n    return hash(x)\n",
        encoding="utf-8",
    )
    hits = _violations(canary)
    assert "canary.py:1: import random" in hits, f"import random not flagged: {hits}"
    assert "canary.py:5: hash(...)" in hits, f"hash(x) not flagged: {hits}"
