"""Dialogue goldens cover every tree node, both profiles, and the line pickers."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from tools.parity.drivers import dialogue


def _named() -> dict:
    return {case.name: case for case in dialogue.build_cases()}


def test_every_node_of_every_tree_is_visited() -> None:
    cases = _named()
    for tree_id, tree in get_data_loader().dialogue_trees.items():
        visited = {s["args"][1] for s in cases[f"tree_{tree_id}"].steps}
        with_responses = {nid for nid, node in tree.nodes.items() if node.responses}
        assert with_responses <= visited, tree_id


def test_skill_checks_pass_and_fail() -> None:
    checks = [
        s["result"]["check"]
        for name, c in _named().items()
        if name.startswith("tree_")
        for s in c.steps
        if s["result"]["check"] is not None
    ]
    assert any(c[0] for c in checks) and any(not c[0] for c in checks)


def test_line_pickers_and_interjections_are_recorded() -> None:
    cases = _named()
    assert any(s["result"] for s in cases["ambient"].steps)
    assert any(s["result"] for s in cases["chatter"].steps)
    assert any(s["result"] for s in cases["interjections"].steps)


def test_cases_are_stable() -> None:
    assert [c.to_json("x") for c in dialogue.build_cases()] == [
        c.to_json("x") for c in dialogue.build_cases()
    ]
