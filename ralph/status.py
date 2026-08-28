"""Render STATUS.md -- the operator's view while away.

Ralph already pushes to origin, so a committed markdown file is readable on
GitHub from a phone: no app, no service, no port to expose, nothing extra that
can itself fail. The bar is "can the operator tell from a beach whether it is
working" in five seconds of squinting: STARVED is the loudest word in the
file, an absent heartbeat is stated rather than silently omitted, and a
heartbeat's age is spelled out in words instead of a raw timestamp the reader
has to do arithmetic on.

Everything here is derived from state that already exists (the queue, the
heartbeat, the roadmap's own `Blocks:` claims). This module adds no new
source of truth, so it cannot disagree with the harness -- and the `Blocks:`
cross-check it surfaces is reporting only: it never feeds back into which
sprint runs next.
"""

from __future__ import annotations

import time
from typing import Optional

from ralph.config import PROJECT_ROOT
from ralph.proc import atomic_write
from ralph.triage import QueueState, starvation_report

STATUS_PATH = PROJECT_ROOT / "STATUS.md"

# "the first few lines" of Blocks: drift -- enough to see the shape of the
# problem without turning a five-second phone check into a scroll.
_MAX_DISAGREEMENT_LINES = 5


def _humanize_age(seconds: float) -> str:
    """Render an age in seconds as a short phrase, e.g. "4 minutes ago".

    A raw number of seconds (or a bare timestamp) makes the reader do
    arithmetic on a phone. This does the arithmetic once, here, so STATUS.md
    doesn't have to.
    """
    seconds = max(0.0, seconds)
    if seconds < 5:
        return "just now"
    if seconds < 90:
        return f"{round(seconds)} seconds ago"
    minutes = seconds / 60
    if minutes < 90:
        n = round(minutes)
        return f"{n} minute{'s' if n != 1 else ''} ago"
    hours = minutes / 60
    if hours < 48:
        n = round(hours)
        return f"{n} hour{'s' if n != 1 else ''} ago"
    days = round(hours / 24)
    return f"{days} day{'s' if days != 1 else ''} ago"


def _beat_age_seconds(beat: dict[str, object]) -> Optional[float]:
    """Seconds since *beat* was written, or None if the timestamp is unusable.

    A hand-edited or corrupted heartbeat.json must degrade to "age unknown"
    rather than crash the render -- see the module docstring's bar.
    """
    ts = beat.get("timestamp")
    if not isinstance(ts, (int, float)):
        return None
    return max(0.0, time.time() - float(ts))


def render_status(
    queue: QueueState,
    beat: Optional[dict[str, object]],
    recent: list[str],
    crash_loop: bool = False,
    disagreements: Optional[list[str]] = None,
) -> str:
    """Build the STATUS.md body.

    Args:
        queue: Current queue health (from `triage.analyse`).
        beat: The harness's last heartbeat payload, or None if absent.
        recent: Recent `"<sprint-id> <outcome>"` strings, most-recent-last.
        crash_loop: True once the supervisor has given up after repeated
            restart failures. Rendered as a banner above STARVED.
        disagreements: `triage.blocks_disagreements()` output. A cross-check
            only -- shown here so it resurfaces without a human remembering
            to run a command, but it never gates which sprint runs.

    Returns:
        The full Markdown text of STATUS.md.
    """
    disagreements = disagreements or []
    lines = ["# Ralph Status", ""]
    lines.append(f"_Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    lines.append("")

    if crash_loop:
        lines += ["## CRASH-LOOP", "", "Supervisor stopped after repeated failures.", ""]
    if queue.is_starved:
        lines += ["## STARVED", "", "```", starvation_report(queue), "```", ""]

    lines.append("## Now")
    lines.append("")
    if beat is None:
        lines.append(
            "- **no heartbeat** -- harness is not running, or died without stopping cleanly"
        )
    else:
        age = _beat_age_seconds(beat)
        sprint = beat.get("sprint") or "(between sprints)"
        phase = beat.get("phase") or "-"
        age_text = _humanize_age(age) if age is not None else "unknown"
        lines.append(f"- Sprint: **{sprint}**")
        lines.append(f"- Phase: **{phase}**")
        lines.append(f"- Last beat: **{age_text}**")
    lines.append("")

    lines += [
        "## Queue",
        "",
        f"- total: {queue.total}",
        f"- todo: {queue.todo}",
        f"- eligible: {queue.eligible}",
        f"- blocked: {', '.join(queue.blocked_ids) if queue.blocked_ids else 'none'}",
        "",
    ]

    lines += ["## Blocks drift", ""]
    if disagreements:
        lines.append(
            f"- {len(disagreements)} disagreement(s) between `Blocks:` and `Depends on:` "
            "(cross-check only -- does not affect scheduling)"
        )
        shown = disagreements[:_MAX_DISAGREEMENT_LINES]
        lines += [f"- {d}" for d in shown]
        remaining = len(disagreements) - len(shown)
        if remaining > 0:
            lines.append(f"- (+{remaining} more)")
    else:
        lines.append("- 0 disagreements between `Blocks:` and `Depends on:`")
    lines.append("")

    if recent:
        lines += ["## Recent", ""] + [f"- {r}" for r in recent] + [""]
    return "\n".join(lines)


def write_status(
    queue: QueueState,
    beat: Optional[dict[str, object]],
    recent: list[str],
    crash_loop: bool = False,
    disagreements: Optional[list[str]] = None,
) -> None:
    """Write STATUS.md atomically.

    Does not catch exceptions itself -- the harness's sprint-boundary call
    site is responsible for degrading a failure to a logged warning, so a
    rendering bug can never take down a week-long unattended run.
    """
    atomic_write(STATUS_PATH, render_status(queue, beat, recent, crash_loop, disagreements))
