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


def test_models_use_only_sim_rng() -> None:
    hits: list[str] = []
    for path in sorted(MODELS_ROOT.glob("*.py")):
        hits.extend(_violations(path))
    assert not hits, "Global randomness in models (use spacegame.sim_rng.SimRng):\n" + "\n".join(
        hits
    )
