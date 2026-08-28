"""Tests for queue triage.

The harness logged "No eligible sprints. Exiting cleanly." for two completely
different situations: everything is done, and everything is stranded. On
2026-08-27 the second was true -- 15 todo, 0 eligible, five held by SA-F2, which
had been blocked since April on a transient failure -- and the harness reported
success. Four months of a stalled arc followed from one ambiguous log line.
"""

from __future__ import annotations

from ralph.roadmap_state import Sprint
from ralph.triage import analyse, starvation_report


def _sprint(sid: str, status: str, deps: list[str] | None = None, pos: int = 0) -> Sprint:
    return Sprint(
        sprint_id=sid,
        title=sid,
        status=status,
        depends_on=deps or [],
        section_start=pos,
    )


class TestAnalyse:
    def test_all_done_is_not_starvation(self) -> None:
        sprints = {"A": _sprint("A", "done"), "B": _sprint("B", "done")}
        state = analyse(sprints)
        assert state.todo == 0
        assert state.is_starved is False, "finishing all work is success, not starvation"

    def test_todo_with_none_eligible_is_starvation(self) -> None:
        sprints = {
            "A": _sprint("A", "blocked"),
            "B": _sprint("B", "todo", ["A"], pos=1),
        }
        state = analyse(sprints)
        assert state.todo == 1
        assert state.eligible == 0
        assert state.is_starved is True

    def test_work_available_is_not_starvation(self) -> None:
        sprints = {"A": _sprint("A", "todo")}
        state = analyse(sprints)
        assert state.eligible == 1
        assert state.is_starved is False

    def test_cascade_names_what_each_blocker_strands(self) -> None:
        sprints = {
            "F2": _sprint("F2", "blocked"),
            "F3": _sprint("F3", "todo", ["F2"], pos=1),
            "F4": _sprint("F4", "todo", ["F2"], pos=2),
            "X1": _sprint("X1", "todo", ["F3"], pos=3),
        }
        state = analyse(sprints)
        assert state.blocked_ids == ["F2"]
        assert set(state.stranded_by["F2"]) == {"F3", "F4", "X1"}, (
            "cascade must be transitive -- X1 depends on F3 which depends on F2, "
            "so F2 strands X1 too, which is exactly the case that hid for months"
        )


class TestStarvationReport:
    def test_report_names_blocker_and_stranded(self) -> None:
        sprints = {
            "F2": _sprint("F2", "blocked"),
            "F3": _sprint("F3", "todo", ["F2"], pos=1),
        }
        text = starvation_report(analyse(sprints))
        assert "STARVED" in text
        assert "F2" in text and "F3" in text

    def test_report_is_empty_when_not_starved(self) -> None:
        assert starvation_report(analyse({"A": _sprint("A", "todo")})) == ""


class TestUnresolvedDependency:
    """A typo'd dependency ID must be named, not swallowed into a generic warning.

    Agents author new sprints unattended -- a typo'd `depends_on` entry is a
    realistic way to starve the queue mid-week, and the operator needs the
    sprint id and the bad dependency id to grep for, not a shrug.
    """

    def test_unknown_dependency_id_is_recorded_on_state(self) -> None:
        sprints = {"X11": _sprint("X11", "todo", ["F8"])}
        state = analyse(sprints)
        assert state.is_starved is True
        assert state.unresolved_deps == {"X11": ["F8"]}

    def test_report_names_sprint_and_missing_id(self) -> None:
        sprints = {"X11": _sprint("X11", "todo", ["F8"])}
        text = starvation_report(analyse(sprints))
        assert "STARVED" in text
        assert "X11" in text, "the sprint with the bad dependency must be named"
        assert "F8" in text, "the missing dependency id must be named"
        assert "typos" not in text, (
            "an unresolved dependency IS the typo case -- it must get its own "
            "specific line, not the generic fallback"
        )


class TestDependencyCycle:
    """Two sprints depending on each other is not a typo -- the report must say so."""

    def test_cycle_is_recorded_on_state(self) -> None:
        sprints = {
            "A": _sprint("A", "todo", ["B"]),
            "B": _sprint("B", "todo", ["A"], pos=1),
        }
        state = analyse(sprints)
        assert state.is_starved is True
        assert set(state.cycle) == {"A", "B"}

    def test_report_names_the_cycle_members(self) -> None:
        sprints = {
            "A": _sprint("A", "todo", ["B"]),
            "B": _sprint("B", "todo", ["A"], pos=1),
        }
        text = starvation_report(analyse(sprints))
        assert "cycle" in text.lower()
        assert "A" in text and "B" in text
        assert "typos" not in text, (
            "a cycle is not a typo -- blaming typos here is actively misleading"
        )


class TestBlockedPathUnchanged:
    """The verified blocked/stranded path must not gain unrelated noise."""

    def test_blocked_explanation_does_not_mention_unresolved_or_cycle(self) -> None:
        sprints = {
            "F2": _sprint("F2", "blocked"),
            "F3": _sprint("F3", "todo", ["F2"], pos=1),
        }
        text = starvation_report(analyse(sprints))
        assert "unknown sprint" not in text
        assert "cycle" not in text.lower()
