"""Queue analysis: is there work, and if not, why not.

The harness used to log the same line -- "No eligible sprints. Exiting cleanly."
-- whether every sprint was done or every sprint was stranded. Those are
opposite outcomes. On 2026-08-27 the second was true: 15 todo, 0 eligible, five
of them held by SA-F2, blocked since April on a transient bail. The harness
called it clean and exited, and had been doing so for four months.

Pure functions over already-parsed sprints. No I/O, so it is cheap to call and
cheap to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ralph.config import STATUS_BLOCKED
from ralph.roadmap_state import Sprint, eligible_sprints


@dataclass
class QueueState:
    """A snapshot of whether the queue can make progress."""

    total: int = 0
    todo: int = 0
    eligible: int = 0
    blocked_ids: list[str] = field(default_factory=list)
    # blocker sprint id -> transitively stranded sprint ids
    stranded_by: dict[str, list[str]] = field(default_factory=dict)
    # todo sprint id -> dependency ids that name no known sprint (e.g. a typo)
    unresolved_deps: dict[str, list[str]] = field(default_factory=dict)
    # sprint ids forming a dependency cycle (e.g. ["A", "B", "A"]), or []
    cycle: list[str] = field(default_factory=list)

    @property
    def is_starved(self) -> bool:
        """True when there is work to do and none of it can start.

        Deliberately NOT "eligible == 0" -- an empty queue with nothing todo is
        success. Conflating the two is the original defect.
        """
        return self.todo > 0 and self.eligible == 0


def _transitively_stranded(blocker: str, sprints: dict[str, Sprint]) -> list[str]:
    """Every todo sprint that cannot run because *blocker* is not done."""
    stranded: set[str] = set()
    frontier = [blocker]
    while frontier:
        current = frontier.pop()
        for sprint in sprints.values():
            if current in sprint.depends_on and sprint.sprint_id not in stranded:
                if not sprint.is_done():
                    stranded.add(sprint.sprint_id)
                    frontier.append(sprint.sprint_id)
    return sorted(stranded)


def _unresolved_dependencies(
    todo: list[Sprint], sprints: dict[str, Sprint]
) -> dict[str, list[str]]:
    """Todo sprint id -> sorted dependency ids that name no known sprint.

    This is the typo case: `depends_on` references an id that does not exist
    in the parsed roadmap at all, as opposed to a `blocked` sprint (which
    exists and is handled by `_transitively_stranded`).
    """
    result: dict[str, list[str]] = {}
    for sprint in todo:
        missing = sorted(dep for dep in sprint.depends_on if dep not in sprints)
        if missing:
            result[sprint.sprint_id] = missing
    return result


def _find_cycle(todo: list[Sprint], sprints: dict[str, Sprint]) -> list[str]:
    """Find a dependency cycle among todo sprints whose dependency ids all exist.

    Restricted to todo sprints with fully-resolvable dependency ids: an
    unresolvable id is reported separately by `_unresolved_dependencies`, and a
    `blocked` dependency is reported separately by `_transitively_stranded`. A
    cycle can only exist among sprints that are mutually waiting on each other,
    i.e. todo sprints depending on other todo sprints.

    Returns the cycle as a list of sprint ids ending back at the start (e.g.
    `["A", "B", "A"]`), or `[]` if no such cycle exists.
    """
    todo_ids = {sprint.sprint_id for sprint in todo}
    graph: dict[str, list[str]] = {
        sprint.sprint_id: sorted(dep for dep in sprint.depends_on if dep in todo_ids)
        for sprint in todo
        if all(dep in sprints for dep in sprint.depends_on)
    }

    unvisited, in_progress, done = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, unvisited)
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = in_progress
        path.append(node)
        for dep in graph.get(node, ()):
            if dep not in graph:
                continue
            if color[dep] == in_progress:
                start = path.index(dep)
                return [*path[start:], dep]
            if color[dep] == unvisited:
                found = visit(dep)
                if found:
                    return found
        path.pop()
        color[node] = done
        return None

    for node in sorted(graph):
        if color[node] == unvisited:
            found = visit(node)
            if found:
                return found
    return []


def analyse(sprints: dict[str, Sprint]) -> QueueState:
    """Summarise queue health."""
    todo = [s for s in sprints.values() if s.is_todo()]
    eligible = eligible_sprints(sprints)
    blocked = sorted(
        s.sprint_id for s in sprints.values() if s.status.strip().lower() == STATUS_BLOCKED
    )
    return QueueState(
        total=len(sprints),
        todo=len(todo),
        eligible=len(eligible),
        blocked_ids=blocked,
        stranded_by={b: _transitively_stranded(b, sprints) for b in blocked},
        unresolved_deps=_unresolved_dependencies(todo, sprints),
        cycle=_find_cycle(todo, sprints),
    )


def starvation_report(state: QueueState) -> str:
    """Human-readable starvation summary, or empty string when healthy."""
    if not state.is_starved:
        return ""
    lines = [f"STARVED: {state.todo} todo, {state.eligible} eligible."]
    for blocker, stranded in state.stranded_by.items():
        if stranded:
            lines.append(f"  {blocker} (blocked) strands {', '.join(stranded)}")
    if any(state.stranded_by.values()):
        # A blocked sprint fully explains the starvation -- verified path,
        # unchanged. Don't dilute it with unresolved-dep/cycle diagnostics.
        return "\n".join(lines)

    if state.unresolved_deps:
        for sprint_id in sorted(state.unresolved_deps):
            for dep_id in state.unresolved_deps[sprint_id]:
                lines.append(f"  {sprint_id} depends on unknown sprint '{dep_id}'")
        return "\n".join(lines)

    if state.cycle:
        lines.append(f"  dependency cycle: {' -> '.join(state.cycle)}")
        return "\n".join(lines)

    lines.append("  No blocked sprint explains this -- check dependency IDs for typos.")
    return "\n".join(lines)
