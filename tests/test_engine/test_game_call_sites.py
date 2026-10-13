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
    starts = _calls(_function("_begin_dialogue"), "start_dialogue")
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


def test_every_dialogue_opening_refreshes_the_iron_state() -> None:
    """Polish design 2.2 rule 3: the state is written as any dialogue opens.

    start_dialogue and a crew scene both open their picked tree through _begin_dialogue.
    """
    assert _any_calls(_function("_begin_dialogue"), "refresh_state")


def test_the_dialogue_exit_refreshes_the_iron_state_after_the_close() -> None:
    route = _function("_route_from_dialogue")
    assert _any_calls(route, "close_on_exit")
    assert _any_calls(route, "refresh_state")


def test_a_defeat_runs_the_iron_defeat_sensor() -> None:
    assert _any_calls(_function("_apply_combat_result"), "note_defeat")


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


def test_opening_an_npc_sets_its_gate_before_its_tree_is_chosen() -> None:
    """BB-38: the scene is the scene whoever opens it, so the departure does not replay it."""
    start = _function("start_dialogue")
    gate_reads = [
        n.lineno
        for n in ast.walk(start)
        if isinstance(n, ast.Attribute) and n.attr == "auto_trigger_gate_flag"
    ]
    tree_picks = [c.lineno for c in _calls(start, "get_active_dialogue_id")]
    assert gate_reads and tree_picks
    assert min(gate_reads) < min(tree_picks)


def test_the_trading_view_posts_the_rests_iron_notice_through_the_game() -> None:
    call = _the_one_construction("_create_gameplay_views", "TradingView")
    values = [ast.unparse(k.value) for k in call.keywords if k.arg == "on_iron_notice"]
    assert values == ["self._after_iron_clock"]


def test_a_filing_at_the_clock_writes_its_log_entry_straight_away() -> None:
    """Polish 2.7: auto_iron_betrayal reads true after the filing, on that day and system."""
    assert _any_calls(_function("_after_iron_clock"), "_check_journal_triggers")


def _lines(node: ast.AST, name: str) -> list[int]:
    return [c.lineno for c in _any_calls(node, name)]


def test_a_dialogue_opening_refreshes_the_store_before_the_dialogue_loads_it() -> None:
    """The refresh writes the player's store; load_flags copies that store into the dialogue."""
    start = _function("_begin_dialogue")
    loads, refreshes = _lines(start, "load_flags"), _lines(start, "refresh_state")
    assert loads and refreshes
    assert max(refreshes) < min(loads)


def test_the_dialogue_exit_refreshes_after_the_close_and_mirrors_both() -> None:
    route = _function("_route_from_dialogue")
    closes, refreshes = _lines(route, "close_on_exit"), _lines(route, "refresh_state")
    assert closes and refreshes
    assert max(closes) < min(refreshes)
    args = [ast.unparse(c.args[0]) for c in _any_calls(route, "_mirror_dialogue_flags") if c.args]
    assert "notice.flags" in args
    assert any(a.startswith("refresh_state(") for a in args), args


def test_a_landing_hands_the_clock_notice_to_the_helper_after_the_clock() -> None:
    route = _function("_route_from_galaxy_map")
    clocks, helpers = _lines(route, "on_clock"), _lines(route, "_after_iron_clock")
    assert clocks and helpers
    assert min(helpers) > min(clocks)


def test_the_clock_helper_posts_and_mirrors_the_notice_and_the_state() -> None:
    helper = _function("_after_iron_clock")
    extends = [ast.unparse(c.args[0]) for c in _any_calls(helper, "extend") if c.args]
    assert "notice.lines" in extends or any("notice.lines" in e for e in extends), extends
    assert any(
        "_mission_notifications" in ast.unparse(c.func) for c in _any_calls(helper, "extend")
    )
    args = [ast.unparse(c.args[0]) for c in _any_calls(helper, "_mirror_dialogue_flags") if c.args]
    assert "notice.flags" in args
    assert any(a.startswith("refresh_state(") for a in args), args


def test_a_defeat_counts_the_ore_before_the_defeat_takes_it() -> None:
    apply = _function("_apply_combat_result")
    held, defeats = _lines(apply, "held_units"), _lines(apply, "apply_combat_defeat")
    notes = _any_calls(apply, "note_defeat")
    assert held and defeats and notes
    assert min(held) < min(defeats)
    assert min(c.lineno for c in notes) > min(defeats)
    assert any(
        _any_calls(a, "held_units")
        for c in notes
        for a in [*c.args, *(k.value for k in c.keywords)]
    )


def test_a_mission_complete_notice_is_followed_by_its_receipt() -> None:
    """Polish design 6: the Grand Bazaar's receipt follows Drifter's Delivery's notice."""
    check = _function("check_missions")
    names = [n.attr for n in ast.walk(check) if isinstance(n, ast.Attribute)]
    assert "receipt" in names
    appends = [
        c
        for c in _any_calls(check, "append")
        if ast.unparse(c.func) == "self._mission_notifications.append"
    ]

    def _arg(call: ast.Call) -> ast.expr:
        return call.args[0]

    notices = [
        c
        for c in appends
        if isinstance(_arg(c), ast.JoinedStr)
        and isinstance(_arg(c).values[0], ast.Constant)
        and str(_arg(c).values[0].value).startswith("Mission Complete")
    ]
    receipts = [c for c in appends if ast.unparse(_arg(c)) == "mission.receipt"]
    timeliness = [c for c in appends if ast.unparse(_arg(c)) == "timeliness_comment"]
    assert notices and timeliness
    assert len(receipts) == 1
    receipt = receipts[0]
    assert max(c.lineno for c in notices) < receipt.lineno < min(c.lineno for c in timeliness)
    guards = [
        n
        for n in ast.walk(check)
        if isinstance(n, ast.If)
        and "mission.receipt" in ast.unparse(n.test)
        and any(receipt in ast.walk(stmt) for stmt in n.body)
    ]
    assert guards, "the receipt append must sit under an `if mission.receipt` guard"
