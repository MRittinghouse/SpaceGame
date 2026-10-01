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


def test_a_dialogue_starts_with_the_day() -> None:
    starts = _calls(_function("start_dialogue"), "start_dialogue")
    assert starts
    for call in starts:
        assert any(k.arg == "game_day" for k in call.keywords), ast.dump(call)


def test_every_availability_pass_reads_effective_standing() -> None:
    passes = _calls(_tree(), "update_availability")
    assert len(passes) == 4
    for call in passes:
        standing = next(k.value for k in call.keywords if k.arg == "player_reputation")
        assert isinstance(standing, ast.Call), ast.dump(standing)
        assert isinstance(standing.func, ast.Attribute), ast.dump(standing)
        assert standing.func.attr == "get_effective_reputations", ast.dump(standing)


def test_arrival_crew_lines_pass_the_player_flags() -> None:
    lines = [
        call
        for call in _calls(_tree(), "get_line")
        if call.args
        and isinstance(call.args[0], ast.Constant)
        and call.args[0].value in ("home_system", "faction_territory")
    ]
    assert len(lines) == 2
    for call in lines:
        assert any(k.arg == "player_flags" for k in call.keywords), ast.dump(call)


def test_after_fight_banter_needs_a_fought_fight() -> None:
    apply_result = _function("_apply_combat_result")
    guards = [
        node
        for node in ast.walk(apply_result)
        if isinstance(node, ast.If) and _calls(node, "mark_combat")
    ]
    assert guards, "_apply_combat_result no longer guards mark_combat"
    assert any(_calls(guard.test, "was_fought") for guard in guards)


def test_every_availability_pass_loads_the_cargo_it_accepts() -> None:
    """F-37: the new game, a dialogue exit, a load, and the check all load it."""
    for name in ("initialize_new_game", "_route_from_dialogue", "_load_game", "check_missions"):
        function = _function(name)
        assert _calls(function, "update_availability"), name
        assert _calls(function, "_load_auto_accept_cargo"), name


def test_a_save_lays_the_players_flags_over_the_dialogue_copy() -> None:
    """F-C09: a flag written outside a conversation survives the save."""
    save = _function("_save_game")
    assert _calls(save, "merged_flags")
    assert not _calls(save, "get_flags")


def test_a_new_game_reloads_the_dialogue_copy() -> None:
    """F-C09: a save before the first conversation keeps none of the last game's flags."""
    assert _calls(_function("initialize_new_game"), "load_flags")


def _any_calls(node: ast.AST, name: str) -> list[ast.Call]:
    """Calls of ``name`` as a bare function or as a method."""
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Call)
        and (
            (isinstance(n.func, ast.Name) and n.func.id == name)
            or (isinstance(n.func, ast.Attribute) and n.func.attr == name)
        )
    ]


def test_a_landing_runs_the_iron_clock_before_the_auto_triggers() -> None:
    """BB-4: Elena's trigger reads the flag the clock sets."""
    route = _function("_route_from_galaxy_map")
    clocks = _any_calls(route, "on_clock")
    triggers = _any_calls(route, "_check_auto_triggers")
    assert clocks and triggers
    assert min(c.lineno for c in clocks) < min(c.lineno for c in triggers)


def test_a_dialogue_exit_closes_the_iron_job_through_the_model() -> None:
    route = _function("_route_from_dialogue")
    assert _any_calls(route, "close_on_exit")
    literals = [n.value for n in ast.walk(route) if isinstance(n, ast.Constant)]
    assert "iron_delivery_failed" not in literals


def test_the_trading_view_gets_the_mission_manager() -> None:
    views = _function("_create_gameplay_views")
    built = [
        c
        for c in ast.walk(views)
        if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "TradingView"
    ]
    assert built
    assert any(k.arg == "mission_manager" for k in built[0].keywords)


def _the_one_construction(function: str, view: str) -> ast.Call:
    built = [
        c
        for c in ast.walk(_function(function))
        if isinstance(c, ast.Call) and getattr(c.func, "id", "") == view
    ]
    assert len(built) == 1, f"{function} builds {view} {len(built)} times"
    return built[0]


def _mission_manager_value(call: ast.Call) -> str:
    values = [ast.unparse(k.value) for k in call.keywords if k.arg == "mission_manager"]
    assert len(values) == 1, ast.dump(call)
    return values[0]


def test_the_refining_view_gets_the_mission_manager() -> None:
    call = _the_one_construction("_ensure_refining_view", "RefiningView")
    assert _mission_manager_value(call) == "self.mission_manager"


def test_the_sell_lot_view_gets_the_mission_manager() -> None:
    call = _the_one_construction("_ensure_sell_lot_view", "SellLotView")
    assert _mission_manager_value(call) == "self.mission_manager"


def test_odoms_opening_no_longer_counts_the_ore() -> None:
    """BB-1: the sale sensor replaces the count test, which accused a fight's loser."""
    start = _function("start_dialogue")
    assert not _calls(start, "get_cargo_quantity")
    literals = [n.value for n in ast.walk(start) if isinstance(n, ast.Constant)]
    assert "broker_ore_sold" not in literals
