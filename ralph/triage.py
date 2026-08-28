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


def analyse(sprints: dict[str, Sprint]) -> QueueState:
    """Summarise queue health."""
    todo = [s for s in sprints.values() if s.is_todo()]
    eligible = eligible_sprints(sprints)
    blocked = sorted(s.sprint_id for s in sprints.values() if s.status.strip().lower() == "blocked")
    return QueueState(
        total=len(sprints),
        todo=len(todo),
        eligible=len(eligible),
        blocked_ids=blocked,
        stranded_by={b: _transitively_stranded(b, sprints) for b in blocked},
    )


def starvation_report(state: QueueState) -> str:
    """Human-readable starvation summary, or empty string when healthy."""
    if not state.is_starved:
        return ""
    lines = [f"STARVED: {state.todo} todo, {state.eligible} eligible."]
    for blocker, stranded in state.stranded_by.items():
        if stranded:
            lines.append(f"  {blocker} (blocked) strands {', '.join(stranded)}")
    if not any(state.stranded_by.values()):
        lines.append("  No blocked sprint explains this -- check dependency IDs for typos.")
    return "\n".join(lines)
