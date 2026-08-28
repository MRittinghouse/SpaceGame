"""Tests for queue triage.

The harness logged "No eligible sprints. Exiting cleanly." for two completely
different situations: everything is done, and everything is stranded. On
2026-08-27 the second was true -- 15 todo, 0 eligible, five held by SA-F2, which
had been blocked since April on a transient failure -- and the harness reported
success. Four months of a stalled arc followed from one ambiguous log line.
"""

from __future__ import annotations

from ralph.roadmap_state import Sprint
from ralph.triage import (
    analyse,
    blocks_disagreements,
    is_in_flight,
    starvation_report,
    stranded_report,
)


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


class TestBlocksConsistency:
    def test_agreeing_blocks_and_depends_on_pass(self) -> None:
        sprints = {
            "A": _sprint("A", "done"),
            "B": _sprint("B", "todo", ["A"], pos=1),
        }
        sprints["A"].blocks = ["B"]
        assert blocks_disagreements(sprints) == []

    def test_blocks_claiming_a_nonexistent_edge_is_reported(self) -> None:
        """`Blocks:` was documentation nothing ever parsed, free to drift.

        Every sprint declares it and no code has ever read it, so it can claim
        an edge the real depends_on graph does not have and nobody would know.
        """
        sprints = {"A": _sprint("A", "done"), "B": _sprint("B", "todo", [], pos=1)}
        sprints["A"].blocks = ["B"]
        problems = blocks_disagreements(sprints)
        assert any("A" in p and "B" in p for p in problems)

    def test_blocks_referencing_unknown_sprint_is_reported(self) -> None:
        sprints = {"A": _sprint("A", "todo")}
        sprints["A"].blocks = ["GHOST"]
        assert any("GHOST" in p for p in blocks_disagreements(sprints))


class TestInFlight:
    """M2: a sprint someone started and nobody finished has to be counted.

    `in-progress (implementing)` is not todo, not done and not blocked. Before
    this existed it therefore counted toward NOTHING -- and an empty `eligible`
    list was read as "all work complete", which stopped the supervisor for good
    over a sprint that was never finished.
    """

    def test_in_progress_is_recognised_as_in_flight(self) -> None:
        assert is_in_flight("in-progress (implementing)") is True
        assert is_in_flight("in-progress (planning)") is True
        assert is_in_flight("in-progress (reviewing)") is True

    def test_review_is_recognised_as_in_flight(self) -> None:
        assert is_in_flight("review") is True, (
            "`review` is what a STOP honoured after implement leaves behind, and "
            "nothing reclaimed it -- not recovery, not triage"
        )

    def test_terminal_statuses_are_not_in_flight(self) -> None:
        for status in ("todo", "done", "blocked"):
            assert is_in_flight(status) is False, f"{status} is not half-done work"

    def test_analyse_counts_an_in_progress_sprint(self) -> None:
        state = analyse({"A": _sprint("A", "in-progress (implementing)")})
        assert state.in_flight == {"A": "in-progress (implementing)"}
        assert state.in_flight_count == 1
        assert state.todo == 0
        assert state.eligible == 0

    def test_a_lone_in_progress_sprint_is_not_completion(self) -> None:
        """The exact M2 state: one sprint, abandoned mid-implement.

        Everything the old code looked at reads zero here -- todo 0, eligible
        0, blocked none -- so the harness said "all work complete" and the
        supervisor stopped for the week.
        """
        state = analyse({"A": _sprint("A", "in-progress (implementing)")})
        assert state.is_complete is False, (
            "a sprint stranded at in-progress is abandoned work, not finished "
            "work; calling it complete is the false statement Spec E exists to "
            "eliminate, reached through a different door"
        )
        assert state.is_stranded is True
        assert state.is_starved is False, "nothing is todo, so this is not starvation"

    def test_a_lone_review_sprint_is_not_completion(self) -> None:
        state = analyse({"A": _sprint("A", "review")})
        assert state.is_complete is False
        assert state.is_stranded is True

    def test_everything_done_is_complete(self) -> None:
        state = analyse({"A": _sprint("A", "done"), "B": _sprint("B", "done", pos=1)})
        assert state.is_complete is True, "nothing todo, nothing eligible, nothing in flight"
        assert state.is_stranded is False

    def test_work_available_is_not_stranded(self) -> None:
        state = analyse(
            {
                "A": _sprint("A", "in-progress (implementing)"),
                "B": _sprint("B", "todo", pos=1),
            }
        )
        assert state.eligible == 1
        assert state.is_stranded is False, "B can start; the queue is not stuck"
        assert state.is_complete is False
        assert state.in_flight_count == 1, "A is still counted -- it is still half-done"


class TestStrandedReport:
    def test_report_names_the_sprint_and_its_status(self) -> None:
        text = stranded_report(analyse({"A": _sprint("A", "in-progress (implementing)")}))
        assert "STRANDED" in text
        assert "A" in text
        assert "in-progress (implementing)" in text
        assert "NOT completion" in text

    def test_report_is_empty_when_nothing_is_in_flight(self) -> None:
        assert stranded_report(analyse({"A": _sprint("A", "todo")})) == ""
        assert stranded_report(analyse({"A": _sprint("A", "done")})) == ""

    def test_starvation_report_names_an_in_flight_blocker(self) -> None:
        """The wrong-diagnosis case the reviewer called out.

        B is todo and waiting on A, which is stranded mid-implement. Nothing is
        `blocked`, no dependency id is a typo and there is no cycle -- so the
        report fell through to "No blocked sprint explains this -- check
        dependency IDs for typos" while the real cause sat in plain sight.
        """
        sprints = {
            "A": _sprint("A", "in-progress (implementing)"),
            "B": _sprint("B", "todo", ["A"], pos=1),
        }
        state = analyse(sprints)
        assert state.is_starved is True
        text = starvation_report(state)
        assert "A is IN FLIGHT" in text, (
            "the sprint holding B back must be named; it is the whole explanation"
        )
        assert "check dependency IDs for typos" not in text, (
            "there is no typo -- sending the operator to hunt one is the wrong "
            "diagnosis this test exists to prevent"
        )
