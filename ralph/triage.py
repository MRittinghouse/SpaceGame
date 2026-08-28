"""Queue analysis: is there work, and if not, why not.

The harness used to log the same line -- "No eligible sprints. Exiting cleanly."
-- whether every sprint was done or every sprint was stranded. Those are
opposite outcomes. On 2026-08-27 the second was true: 15 todo, 0 eligible, five
of them held by SA-F2, blocked since April on a transient bail. The harness
called it clean and exited, and had been doing so for four months.

The same false statement had a second door (M2). A sprint reading
`in-progress (implementing)` or `review` is not `todo`, not `done` and not
`blocked`, so until this module learned about it, it counted toward NOTHING:
not `todo`, not `eligible`, not `blocked_ids`. A run killed mid-sprint left
exactly that, and if it was the last outstanding item the harness announced
"all work complete" and the supervisor stopped for good -- over a sprint nobody
had finished. `in_flight` exists so that state has somewhere to be counted, and
so "complete" can mean what it says: nothing todo, nothing eligible, and
nothing left half-done.

Pure functions over already-parsed sprints. No I/O, so it is cheap to call and
cheap to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ralph.config import STATUS_BLOCKED, STATUS_REVIEW
from ralph.roadmap_state import Sprint, eligible_sprints

# A sprint someone started and nobody finished. `in-progress (planning)`,
# `in-progress (implementing)` and `in-progress (reviewing)` are all prefixed;
# `review` (a STOP honoured after implement) is its own literal and, until M2,
# was reclaimed by nothing at all -- not even `_recover_stuck_sprints`.
_IN_FLIGHT_PREFIX = "in-progress"


def is_in_flight(status: str) -> bool:
    """True when *status* means "started, not finished, nobody obviously on it".

    A single definition, because the harness's stuck-sprint recovery and this
    module's queue accounting must agree about which statuses are in flight.
    They did not: recovery matched `in-progress` only, so a sprint parked at
    `review` was invisible to both the recovery that would reclaim it and the
    triage that would report it.
    """
    normalised = status.strip().lower()
    return normalised.startswith(_IN_FLIGHT_PREFIX) or normalised == STATUS_REVIEW


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
    # sprint id -> its status, for every sprint that is started but not
    # finished (`in-progress (*)` or `review`). Work that belongs to nobody.
    in_flight: dict[str, str] = field(default_factory=dict)

    @property
    def is_starved(self) -> bool:
        """True when there is work to do and none of it can start.

        Deliberately NOT "eligible == 0" -- an empty queue with nothing todo is
        success. Conflating the two is the original defect.
        """
        return self.todo > 0 and self.eligible == 0

    @property
    def in_flight_count(self) -> int:
        """How many sprints are started but unfinished."""
        return len(self.in_flight)

    @property
    def is_stranded(self) -> bool:
        """True when the only outstanding work is half-done and nothing can start.

        The counterpart to `is_starved`, and the reason "all work complete" is
        no longer decidable from `eligible` alone: a sprint abandoned at
        `in-progress (implementing)` makes `eligible` 0 without making the
        queue finished.
        """
        return self.eligible == 0 and bool(self.in_flight)

    @property
    def is_complete(self) -> bool:
        """True only when there is genuinely nothing left, anywhere.

        Not "eligible == 0". That was M2: the supervisor read an empty eligible
        list as completion and stopped permanently, with a sprint sitting at
        `in-progress` that no run would ever come back for.
        """
        return self.todo == 0 and self.eligible == 0 and not self.in_flight


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
        in_flight={
            s.sprint_id: s.status.strip()
            for s in sorted(sprints.values(), key=lambda s: s.sprint_id)
            if is_in_flight(s.status)
        },
    )


def blocks_disagreements(sprints: dict[str, Sprint]) -> list[str]:
    """Report `Blocks:` claims that the real dependency graph does not support.

    `Blocks:` is declared on every sprint and, until now, parsed by nothing. It
    reads as structural but was a comment, free to drift from `depends_on`
    without anyone noticing. It is a CROSS-CHECK, never a second source of
    truth -- eligibility still comes from `depends_on` alone, so there is only
    one graph to keep correct.
    """
    problems: list[str] = []
    for sprint in sprints.values():
        for claimed in sprint.blocks:
            target = sprints.get(claimed)
            if target is None:
                problems.append(f"{sprint.sprint_id}: Blocks names unknown sprint {claimed!r}")
            elif sprint.sprint_id not in target.depends_on:
                problems.append(
                    f"{sprint.sprint_id}: Blocks claims {claimed}, but {claimed} "
                    f"does not list {sprint.sprint_id} in Depends on"
                )
    return sorted(problems)


def _in_flight_lines(state: QueueState) -> list[str]:
    """One line per started-but-unfinished sprint, for either report."""
    return [
        f"  {sprint_id} is IN FLIGHT ({status}) and nothing is running it"
        for sprint_id, status in sorted(state.in_flight.items())
    ]


def starvation_report(state: QueueState) -> str:
    """Human-readable starvation summary, or empty string when healthy."""
    if not state.is_starved:
        return ""
    lines = [f"STARVED: {state.todo} todo, {state.eligible} eligible."]
    # Named first, and on every path: an abandoned in-progress sprint is the
    # most actionable thing this report can carry, and it used to be the one
    # thing that could not appear in it at all -- a sprint stranded at
    # `in-progress` while holding dependents produced the "check dependency IDs
    # for typos" line below, with the real cause sitting in plain sight.
    lines += _in_flight_lines(state)
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

    if state.in_flight:
        # Already named above. Falling through to the typo line would send the
        # operator hunting a dependency bug that does not exist.
        return "\n".join(lines)

    lines.append("  No blocked sprint explains this -- check dependency IDs for typos.")
    return "\n".join(lines)


def stranded_report(state: QueueState) -> str:
    """Half-done work with nothing eligible, or empty string when not stranded.

    The report that had nowhere to come from before M2. Its whole job is to be
    what gets printed INSTEAD of "all work complete" when the queue looks empty
    only because a sprint nobody is working on is still marked started.
    """
    if not state.is_stranded:
        return ""
    lines = [
        f"STRANDED: {state.in_flight_count} sprint(s) started and unfinished, "
        f"{state.eligible} eligible. This is NOT completion."
    ]
    lines += _in_flight_lines(state)
    lines.append(
        "  A run was killed or stopped mid-sprint. Stuck-sprint recovery resets "
        "these to todo once they have gone untouched for IN_PROGRESS_STALE_MINUTES, "
        "so the next harness launch reclaims them; nothing further happens until "
        "then."
    )
    return "\n".join(lines)
