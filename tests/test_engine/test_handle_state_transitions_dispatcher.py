"""Structure contract tests for the ``_handle_state_transitions`` split.

SH-2 splits the 1,197-line ``Game._handle_state_transitions`` method into a
thin dispatcher plus 33 per-view route handlers named ``_route_from_X``. This
module verifies the mechanical shape of the split — dispatcher length, handler
lengths, routing order, and the public signature — without asserting anything
about run-time behaviour (the crawler and the full suite cover that).
"""

from __future__ import annotations

import ast
import inspect
import os
import textwrap

# Headless SDL so ``Game`` remains importable in CI worker environments.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from spacegame.engine.game import Game

# The 33 view-check blocks in their original top-to-bottom order inside the
# pre-split ``_handle_state_transitions`` method. Naming rule: strip the
# ``_view`` suffix from the origin attribute (``main_menu_view`` →
# ``_route_from_main_menu``, ``_tutorial_shop_view`` → ``_route_from_tutorial_shop``).
EXPECTED_ROUTE_HANDLERS: tuple[str, ...] = (
    "_route_from_main_menu",
    "_route_from_name_input",
    "_route_from_character_creation",
    "_route_from_tutorial_shop",
    "_route_from_galaxy_map",
    "_route_from_journal",
    "_route_from_crew_roster",
    "_route_from_character",
    "_route_from_mission_log",
    "_route_from_trading",
    "_route_from_dialogue",
    "_route_from_mining",
    "_route_from_salvage",
    "_route_from_refining",
    "_route_from_skill_tree",
    "_route_from_statistics",
    "_route_from_achievements",
    "_route_from_combat",
    "_route_from_encounter",
    "_route_from_ground_briefing",
    "_route_from_ground_exploration",
    "_route_from_ground_result",
    "_route_from_shipyard",
    "_route_from_ship_builder",
    "_route_from_station_hub",
    "_route_from_repair_bay",
    "_route_from_wreckers_guild",
    "_route_from_deep_shafts",
    "_route_from_auction",
    "_route_from_sell_lot",
    "_route_from_dispute",
    "_route_from_cantina",
    "_route_from_investment",
)


class TestDispatcherStructure:
    def test_dispatcher_under_200_lines(self) -> None:
        """The thin dispatcher's source body must be under 200 lines."""
        source_lines, _ = inspect.getsourcelines(Game._handle_state_transitions)
        assert len(source_lines) < 200, (
            f"Dispatcher grew to {len(source_lines)} lines; SH-2 requires under 200"
        )

    def test_all_route_handlers_under_250_lines(self) -> None:
        """Every ``_route_from_*`` handler's source must be under 250 lines."""
        offenders: list[tuple[str, int]] = []
        for name in EXPECTED_ROUTE_HANDLERS:
            handler = getattr(Game, name, None)
            assert handler is not None, f"Missing handler: {name}"
            source_lines, _ = inspect.getsourcelines(handler)
            if len(source_lines) >= 250:
                offenders.append((name, len(source_lines)))
        assert not offenders, f"Handlers exceed 250-line ceiling: {offenders}"

    def test_dispatcher_calls_routers_in_original_order(self) -> None:
        """Dispatcher body must invoke every ``_route_from_*`` in the pre-split order.

        The dispatcher body is parsed via ``ast``. Each top-level ``If`` node
        whose body is a bare ``return`` and whose condition is an attribute
        call (``self._route_from_X()``) contributes one router name; the
        sequence of names must equal :data:`EXPECTED_ROUTE_HANDLERS`.
        """
        source = inspect.getsource(Game._handle_state_transitions)
        # ``inspect.getsource`` includes leading indent from the class body.
        # Dedent so ``ast.parse`` sees a top-level ``def``.
        source = textwrap.dedent(source)
        module = ast.parse(source)
        func = module.body[0]
        assert isinstance(func, ast.FunctionDef), (
            f"Expected FunctionDef at module.body[0]; got {type(func).__name__}"
        )

        found: list[str] = []
        for node in func.body:
            if not isinstance(node, ast.If):
                continue
            # Only accept ``if <call>: return`` shape; the transition-active
            # guard uses ``self.transition_manager.active`` which is not a
            # ``Call`` and therefore skipped naturally.
            if not (
                isinstance(node.test, ast.Call)
                and isinstance(node.test.func, ast.Attribute)
                and isinstance(node.test.func.value, ast.Name)
                and node.test.func.value.id == "self"
                and node.test.func.attr.startswith("_route_from_")
            ):
                continue
            if not (len(node.body) == 1 and isinstance(node.body[0], ast.Return)):
                continue
            found.append(node.test.func.attr)

        assert tuple(found) == EXPECTED_ROUTE_HANDLERS, (
            "Dispatcher routing order diverged from pre-split view-check order.\n"
            f"Expected: {EXPECTED_ROUTE_HANDLERS}\n"
            f"Found:    {tuple(found)}"
        )

    def test_all_expected_route_handlers_exist(self) -> None:
        """Every expected ``_route_from_*`` handler must exist and be callable."""
        missing: list[str] = []
        not_callable: list[str] = []
        for name in EXPECTED_ROUTE_HANDLERS:
            attr = getattr(Game, name, None)
            if attr is None:
                missing.append(name)
            elif not callable(attr):
                not_callable.append(name)
        assert not missing, f"Missing route handlers: {missing}"
        assert not not_callable, f"Route handlers exist but are not callable: {not_callable}"

    def test_handle_state_transitions_public_signature_unchanged(self) -> None:
        """The public signature ``_handle_state_transitions(self) -> None`` must not change.

        The only direct external caller is
        ``TestCB2WarpArrivalBanterWiring`` in ``tests/test_engine/test_mission_notifications.py``;
        any signature drift breaks it.
        """
        sig = inspect.signature(Game._handle_state_transitions)
        params = list(sig.parameters.values())
        assert len(params) == 1, (
            f"Expected exactly one parameter (self); got {[p.name for p in params]}"
        )
        assert params[0].name == "self"
        # The return annotation is ``None`` (a type). Some Python configurations
        # surface it as ``NoneType``; both are acceptable.
        assert sig.return_annotation in (None, type(None)), (
            f"Expected return annotation None; got {sig.return_annotation!r}"
        )
