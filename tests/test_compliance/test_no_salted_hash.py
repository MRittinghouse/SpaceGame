"""Compliance Scanner: no ``hash()`` calls anywhere in the spacegame package.

Python salts ``hash()`` of a string per process, so a seed or choice derived from it
changes on every launch and under every pytest-xdist worker. That made
``TestDebrisRendering`` fail under PYTHONHASHSEED=22: the debris streak's lane came
from ``random.Random(hash(danger_level) + 777)``. Use ``spacegame.sim_rng.stable_seed``.

The models scanner (``test_no_global_random_in_models.py``) already covers models/;
this one covers the engine, the views, and everything else. ``__hash__`` methods are
exempt. No allowlist.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "spacegame"

# spacegame/ holds over 200 modules; a scan of fewer means the glob missed
# (a moved directory, a wrong root) and the pass would be vacuous.
MIN_FILES_SCANNED = 150


def _hash_calls(path: Path, label: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__hash__":
            exempt.update(id(n) for n in ast.walk(node))
    return [
        f"{label}:{node.lineno}: hash(...)"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "hash"
        and id(node) not in exempt
    ]


def test_spacegame_never_calls_salted_hash() -> None:
    paths = sorted(PACKAGE_ROOT.rglob("*.py"))
    assert len(paths) >= MIN_FILES_SCANNED, (
        f"scanned only {len(paths)} files under {PACKAGE_ROOT}; the scanner is not looking "
        "at the package"
    )
    hits: list[str] = []
    for path in paths:
        hits.extend(_hash_calls(path, path.relative_to(PACKAGE_ROOT).as_posix()))
    assert not hits, (
        "hash() is salted per process (use spacegame.sim_rng.stable_seed):\n" + "\n".join(hits)
    )


def test_scanner_flags_a_planted_call_and_spares_dunder_hash(tmp_path: Path) -> None:
    canary = tmp_path / "canary.py"
    canary.write_text(
        "class Key:\n"
        "    def __hash__(self) -> int:\n"
        "        return hash(('key', 1))\n"
        "\n"
        "\n"
        "def seed_for(name: str) -> int:\n"
        "    return hash(name) + 777\n",
        encoding="utf-8",
    )
    hits = _hash_calls(canary, "canary.py")
    assert hits == ["canary.py:7: hash(...)"], f"expected only the seed_for call: {hits}"
