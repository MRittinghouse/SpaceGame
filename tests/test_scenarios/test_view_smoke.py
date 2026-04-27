"""QA Pass 4 Part A: view lifecycle smoke tests.

Every registered view is driven through:
  construct → on_enter → update → render → on_exit

Failure modes caught:
  - AttributeError / TypeError from missing constructor args
  - Exceptions during on_enter (UI creation, font loading, etc.)
  - render() crashes on the first frame
  - Leaked pygame_gui elements after on_exit (missing ``.kill()`` calls)

This is the first test coverage for many Tier D views (per Pass 1 audit):
ship_builder_view (2,300 stmts), shipyard_view (1,551), crew_roster_view,
dialogue_view, mission_log_view, skill_tree_view, etc.
"""

from __future__ import annotations

import pytest

from tests.test_scenarios._view_harness import (
    all_view_names,
    fresh_ui_manager,
    run_lifecycle,
    view_factory,
)


class TestViewLifecycleSmoke:
    """Every registered view survives a full lifecycle without exception."""

    @pytest.mark.parametrize("view_name", all_view_names())
    def test_view_lifecycle_completes(self, view_name: str) -> None:
        ui = fresh_ui_manager()
        factory = view_factory(view_name)
        view = factory(ui)
        result = run_lifecycle(view, ui)
        assert result.exception is None, (
            f"View '{view_name}' crashed during lifecycle: "
            f"{type(result.exception).__name__}: {result.exception}"
        )

    @pytest.mark.parametrize("view_name", all_view_names())
    def test_view_cleans_up_ui_elements(self, view_name: str) -> None:
        """After on_exit, the UIManager should hold no more elements than
        it did before on_enter (zero leakage)."""
        ui = fresh_ui_manager()
        factory = view_factory(view_name)
        view = factory(ui)
        result = run_lifecycle(view, ui)

        if result.exception is not None:
            pytest.skip("lifecycle crashed — covered by test_view_lifecycle_completes")

        assert result.ui_elements_after_exit <= result.ui_elements_before, (
            f"View '{view_name}' leaked UI elements: "
            f"before={result.ui_elements_before}, "
            f"after_enter={result.ui_elements_after_enter}, "
            f"after_exit={result.ui_elements_after_exit}. "
            f"Missing .kill() calls in _destroy_ui?"
        )


class TestViewConstructionRobustness:
    """Views must construct even when given minimal state — matches the
    reality of first-session play where many managers have empty state."""

    @pytest.mark.parametrize("view_name", all_view_names())
    def test_view_constructs_without_exception(self, view_name: str) -> None:
        ui = fresh_ui_manager()
        factory = view_factory(view_name)
        try:
            view = factory(ui)
            assert view is not None
        except Exception as exc:
            pytest.fail(f"View '{view_name}' failed to construct: {type(exc).__name__}: {exc}")
