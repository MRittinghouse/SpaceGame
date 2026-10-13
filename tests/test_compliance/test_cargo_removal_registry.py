"""Every named way the Python build lowers the hold, each reviewed (bug bash BB-1, BB-11).

A mission's accept cargo is reserved for it (``MissionManager.reserved_units``): a sale
the captain names may draw a campaign or authored mission's units, a board contract's
are sealed, and Sell All, Sell Max, refining, the auction house and the Wreckers' Guild
leave every reserved unit aboard. This scan finds every call of a named removal
(``LOWERING_CALLS``). A new one fails until it is reviewed here: name the guard it
references, or "" and why it needs none. A guard that lives in a helper is pinned in
``HELPER_GUARDS``. The hidden compartment's retrieve (``remove_from_hidden``) is a scanned
removal too. The scan cannot see a direct write to a hold dictionary; the three that
exist are reviewed by hand in ``OUTSIDE_THE_SCAN``. The Godot port's
``cargo_removal_registry_test.gd`` is its twin (plan B2).
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPACEGAME = ROOT / "spacegame"
LOWERING_CALLS = frozenset(
    {
        "remove_cargo",
        "sell_commodity",
        "create_listing",
        "start_job",
        "start_batch",
        "start_on_free_cargo",
        "remove_from_hidden",
    }
)

# (file, function) -> (a name the function must reference as its guard, or "", why)
REVIEWED: dict[tuple[str, str], tuple[str, str]] = {
    ("spacegame/engine/game.py", "Game._route_from_mission_log"): (
        "",
        "an abandon takes back the abandoned mission's own accept cargo",
    ),
    ("spacegame/models/bidding.py", "AuctionState.create_listing"): (
        "reserved",
        "its caller passes the reserved count",
    ),
    ("spacegame/models/encounter.py", "apply_encounter_outcome"): (
        "",
        "a confiscation is a loss the captain does not choose",
    ),
    ("spacegame/models/iron_consignment.py", "take_back"): (
        "",
        "the iron job's close and filing take back Odom's consigned ore, at most ten units, "
        "from both holds, the main hold first (polish design 2.2 rule 6; the author's read "
        "2026-10-13)",
    ),
    ("spacegame/models/mission.py", "MissionManager.apply_rewards"): (
        "_delivery_share",
        "a hand-over takes its own mission's units and the captain's, from both holds, the main "
        "hold first; a remove_cargo reward takes only what its mission's collect leg counted "
        "on free units in the same check (pinned by "
        "test_each_remove_cargo_reward_has_its_collect_leg; the board, smuggling and "
        "post-capstone generators build the same pair)",
    ),
    ("spacegame/models/player.py", "Player.apply_combat_defeat"): (
        "",
        "a defeat's loss is not chosen, and counts cannot pick a lot",
    ),
    ("spacegame/models/player.py", "Player.sell_commodity"): (
        "",
        "the trading view guards each of its three callers",
    ),
    ("spacegame/models/refining.py", "start_on_free_cargo"): (
        "",
        "runs the session on the free hold its caller passes",
    ),
    ("spacegame/views/refining_view.py", "RefiningView._start_selected_recipe"): (
        "_free_hold",
        "a recipe draws only free units (HELPER_GUARDS)",
    ),
    ("spacegame/views/sell_lot_view.py", "SellLotView.confirm_listing"): (
        "free_units",
        "a listing draws only free units",
    ),
    ("spacegame/views/trading_view.py", "TradingView._execute_hide_cargo"): (
        "hidable",
        "hiding moves units between the ship's two holds; held_units reads both, so the "
        "reserved count, the seal and the sale sensor still see a hidden unit (plan B1 ruling), "
        "and Odom's consigned ore stays in the main hold (iron_consignment.hidable)",
    ),
    ("spacegame/views/trading_view.py", "TradingView._execute_retrieve_cargo"): (
        "",
        "retrieving moves units from the hidden compartment back to the main hold; held_units "
        "reads both holds, so the reserved count, the seal and the sale sensor see no change "
        "(mirrors _execute_hide_cargo)",
    ),
    ("spacegame/views/trading_view.py", "TradingView._execute_sell"): (
        "sale_draws_sealed",
        "a named sale may draw a campaign consignment; a board contract's cargo is sealed",
    ),
    ("spacegame/views/trading_view.py", "TradingView._execute_sell_all"): (
        "free_units",
        "Sell All leaves every reserved unit aboard",
    ),
    ("spacegame/views/trading_view.py", "TradingView._execute_sell_max"): (
        "free_units",
        "Sell Max leaves every reserved unit aboard",
    ),
    ("spacegame/views/wreckers_guild_view.py", "WreckersGuildView._turn_in_active_contract"): (
        "_cargo_satisfies_mission",
        "its check counts only free units (HELPER_GUARDS)",
    ),
}

# A reviewed site's guard that lives in a helper: (file, helper) -> the name it references.
HELPER_GUARDS: dict[tuple[str, str], str] = {
    ("spacegame/views/refining_view.py", "RefiningView._free_hold"): "free_cargo",
    ("spacegame/views/wreckers_guild_view.py", "WreckersGuildView._cargo_satisfies_mission"): (
        "free_units"
    ),
}

# Direct writes to a hold dictionary, which the call scan cannot see: (file, function) -> why.
OUTSIDE_THE_SCAN: dict[tuple[str, str], str] = {
    ("spacegame/views/refining_view.py", "RefiningView._handle_schematic_click"): (
        "it spends schematic_data, which no mission loads as accept cargo"
    ),
    ("spacegame/views/shipyard_view.py", "ShipyardView._uninstall_hidden_compartment"): (
        "the uninstall moves every hidden unit into the main hold before it drops the "
        "compartment, so nothing aboard changes"
    ),
    ("spacegame/models/player.py", "Player.swap_ship"): (
        "a ship swap drops only what the new hold cannot fit, a loss the shipyard warns of; "
        "counts cannot pick which units go"
    ),
}


class _Sites(ast.NodeVisitor):
    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.stack: list[str] = []
        self.calls: set[tuple[str, str]] = set()
        self.nodes: dict[str, ast.AST] = {}

    def _scope(self, node: ast.AST, name: str) -> None:
        self.stack.append(name)
        self.nodes[".".join(self.stack)] = node
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope(node, node.name)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, (ast.Attribute, ast.Name)):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            if name in LOWERING_CALLS and self.stack:
                self.calls.add((self.rel, ".".join(self.stack)))
        self.generic_visit(node)


def _scan() -> tuple[set[tuple[str, str]], dict[tuple[str, str], ast.AST]]:
    sites: set[tuple[str, str]] = set()
    nodes: dict[tuple[str, str], ast.AST] = {}
    for path in sorted(SPACEGAME.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        visitor = _Sites(rel)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        sites |= visitor.calls
        for name, node in visitor.nodes.items():
            nodes[(rel, name)] = node
    return sites, nodes


def _names(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
    return found


def test_every_way_to_lower_the_hold_is_reviewed() -> None:
    sites, _ = _scan()
    assert sites == set(REVIEWED), (
        "A new way to lower the hold, or a reviewed one gone. Route it through "
        "MissionManager.free_units, free_cargo or sale_draws_sealed, or review it here: "
        f"new {sorted(sites - set(REVIEWED))}, gone {sorted(set(REVIEWED) - sites)}"
    )


def test_each_reviewed_site_references_its_guard() -> None:
    _, nodes = _scan()
    guards = {site: guard for site, (guard, _why) in REVIEWED.items() if guard}
    guards |= HELPER_GUARDS
    missing = [
        f"{site[0]}::{site[1]} needs {guard}"
        for site, guard in guards.items()
        if guard not in _names(nodes[site])
    ]
    assert not missing


def test_the_direct_writes_reviewed_by_hand_still_exist() -> None:
    """A rename or a move of one forces a fresh review."""
    _, nodes = _scan()
    assert [site for site in OUTSIDE_THE_SCAN if site not in nodes] == []
