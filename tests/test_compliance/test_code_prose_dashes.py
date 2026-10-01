"""No em dash in a string built by model or engine code (BB-59).

The data gates never see text code builds (milestones, notices, fight log lines, display
names). This scans every string constant under spacegame/models and spacegame/engine,
f-string parts included, with escapes decoded by the parser. Docstrings and the arguments
of logger calls are exempt: neither reaches a player.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCANNED = ("spacegame/models", "spacegame/engine")
EM_DASH = "\u2014"
_LOG_METHODS = frozenset({"debug", "info", "warning", "error", "exception", "critical", "log"})


def _exempt_ids(tree: ast.AST) -> set[int]:
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                exempt.add(id(body[0].value))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _LOG_METHODS
            and isinstance(node.func.value, ast.Name)
            and "log" in node.func.value.id.lower()
        ):
            for arg in [*node.args, *(k.value for k in node.keywords)]:
                exempt |= {id(sub) for sub in ast.walk(arg)}
    return exempt


def violations(source: str, label: str) -> list[str]:
    tree = ast.parse(source)
    exempt = _exempt_ids(tree)
    return [
        f"{label}:{node.lineno}: {node.value[:80]!r}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and EM_DASH in node.value
        and id(node) not in exempt
    ]


def test_the_scanner_sees_escapes_and_skips_logs_and_docstrings() -> None:
    assert violations('x = "a \\u2014 b"', "t")
    assert violations('x = f"{y} \\u2014 z"', "t")
    assert not violations('logger.info("a \\u2014 b")', "t")
    assert not violations('_combat_log.warning(f"a \\u2014 {b}")', "t")
    assert not violations('def f():\n    """A \\u2014 docstring."""\n', "t")


def test_no_em_dash_in_code_built_text() -> None:
    found: list[str] = []
    for folder in SCANNED:
        for path in sorted((PROJECT_ROOT / folder).rglob("*.py")):
            label = path.relative_to(PROJECT_ROOT).as_posix()
            found += violations(path.read_text(encoding="utf-8"), label)
    assert not found, "em dash in code-built text:\n" + "\n".join(found)
