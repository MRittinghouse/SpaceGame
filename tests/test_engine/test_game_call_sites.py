"""AST checks that game.py calls the bug-bash model functions where it must (plan A1)."""

from __future__ import annotations

import ast
from pathlib import Path

GAME = Path(__file__).resolve().parents[2] / "spacegame" / "engine" / "game.py"


def _tree() -> ast.Module:
    return ast.parse(GAME.read_text(encoding="utf-8"))


def _function(name: str) -> ast.FunctionDef:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"game.py has no function {name}")


def _calls(node: ast.AST, attr: str) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == attr
    ]


def test_a_dialogue_exit_records_the_conversation_before_the_availability_pass() -> None:
    route = _function("_route_from_dialogue")
    records = _calls(route, "record_conversation")
    passes = _calls(route, "update_availability")
    assert records and passes
    assert min(c.lineno for c in records) < min(c.lineno for c in passes)


def test_every_mission_manager_knows_the_content_producers() -> None:
    built = [
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Attribute) and t.attr == "mission_manager" for t in node.targets)
    ]
    assert built, "game.py assigns no mission manager"
    for value in built:
        assert isinstance(value, ast.Call), ast.dump(value)
        assert isinstance(value.func, ast.Attribute), ast.dump(value)
        assert value.func.attr == "_build_mission_manager", ast.dump(value)
