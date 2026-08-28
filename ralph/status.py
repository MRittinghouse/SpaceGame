"""Render STATUS.md -- the operator's view while away.

Ralph already pushes to origin, so a committed markdown file is readable on
GitHub from a phone: no app, no service, no port to expose, nothing extra that
can itself fail. The bar is "can the operator tell from a beach whether it is
working" in five seconds of squinting: STARVED is the loudest word in the
file, an absent heartbeat is stated rather than silently omitted, a stale one
is flagged rather than left indistinguishable from a fresh one (a heartbeat
file can outlive the process that wrote it -- a reboot mid-sprint leaves it
behind), a heartbeat's age is spelled out in words instead of a raw
timestamp the reader has to do arithmetic on, and a run that died on an
unhandled exception renders as a distinct CRASHED banner rather than the
same calm queue summary a clean exit produces -- the two are indistinguishable
otherwise, and that difference is the single most valuable thing this file
can tell someone on a beach.

Everything here is derived from state that already exists (the queue, the
heartbeat, the roadmap's own `Blocks:` claims). This module adds no new
source of truth, so it cannot disagree with the harness -- and the `Blocks:`
cross-check it surfaces is reporting only: it never feeds back into which
sprint runs next.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

from ralph.config import IN_PROGRESS_STALE_MINUTES, PROJECT_ROOT
from ralph.proc import atomic_write
from ralph.triage import QueueState, starvation_report

STATUS_PATH = PROJECT_ROOT / "STATUS.md"

# "the first few lines" of Blocks: drift -- enough to see the shape of the
# problem without turning a five-second phone check into a scroll.
_MAX_DISAGREEMENT_LINES = 5

# Git's rejection text can be long; STATUS.md is a five-second phone read.
_MAX_PUSH_DETAIL_CHARS = 300


PUSH_STATE_PATH = PROJECT_ROOT / "ralph" / "push_state.json"


@dataclass(frozen=True)
class PushState:
    """Outcome of the harness's last `git push`, persisted across runs.

    STATUS.md is only a remote signal once it is pushed, so a push that starts
    failing freezes the operator's view at the last good state while the
    harness keeps working perfectly -- committing locally, rendering STATUS.md
    locally, for the rest of the week. The realistic trigger is divergence, not
    a network blip: one push to `master` from anywhere else makes every
    subsequent `git push origin HEAD` a non-fast-forward, and the harness never
    pulls, so it never recovers.

    Nothing can make that visible on GitHub while push is broken -- the file
    carrying the news is the file that cannot be sent. What this makes possible
    is that the frozen board is self-evident from the file itself: the local
    copy names the failure and its reason, and the moment push recovers the
    pushed copy still says how long the gap was and when the last successful
    push actually happened.

    Attributes:
        ok: Whether the most recent push attempt succeeded.
        timestamp: Unix time of that most recent attempt.
        detail: Git's failure text, empty on success.
        last_success_timestamp: Unix time of the last SUCCESSFUL push, carried
            forward across failures. None if this repo has never pushed.
        consecutive_failures: Failed attempts since the last success.
    """

    ok: bool
    timestamp: float
    detail: str = ""
    last_success_timestamp: Optional[float] = None
    consecutive_failures: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "timestamp": self.timestamp,
            "detail": self.detail,
            "last_success_timestamp": self.last_success_timestamp,
            "consecutive_failures": self.consecutive_failures,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PushState":
        last_success = data.get("last_success_timestamp")
        return cls(
            ok=bool(data.get("ok", False)),
            timestamp=float(data.get("timestamp", 0.0)),  # type: ignore[arg-type]
            detail=str(data.get("detail", "")),
            last_success_timestamp=(
                float(last_success) if isinstance(last_success, (int, float)) else None
            ),
            consecutive_failures=int(data.get("consecutive_failures", 0)),  # type: ignore[arg-type]
        )


def read_push_state() -> Optional[PushState]:
    """The last recorded push outcome, or None if there is none to read.

    A missing, unreadable, or corrupt file degrades to None ("no push
    recorded") rather than raising: this feeds a status render whose whole
    purpose is to still say something useful when things are broken.
    """
    try:
        raw = json.loads(PUSH_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return PushState.from_dict(raw)
    except (TypeError, ValueError):
        return None


def record_push(ok: bool, detail: str = "", now: Optional[float] = None) -> PushState:
    """Persist the outcome of a `git push` attempt.

    Carries `last_success_timestamp` forward across failures so STATUS.md can
    answer the question that actually matters -- "when did anything I am
    looking at last reach GitHub" -- rather than only "did the last attempt
    work".

    Args:
        ok: Whether the push succeeded.
        detail: Git's failure text; ignored when *ok*.
        now: Injectable clock for tests.

    Returns:
        The state that was written.

    Raises:
        OSError: If the file cannot be written. Call sites degrade this to a
            log line; it is deliberately not swallowed here so the failure is
            observable in tests.
    """
    stamp = time.time() if now is None else now
    previous = read_push_state()
    if ok:
        state = PushState(
            ok=True,
            timestamp=stamp,
            detail="",
            last_success_timestamp=stamp,
            consecutive_failures=0,
        )
    else:
        state = PushState(
            ok=False,
            timestamp=stamp,
            detail=detail.strip()[:_MAX_PUSH_DETAIL_CHARS],
            last_success_timestamp=(previous.last_success_timestamp if previous else None),
            consecutive_failures=(previous.consecutive_failures + 1 if previous else 1),
        )
    PUSH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(PUSH_STATE_PATH, json.dumps(state.to_dict(), indent=2))
    return state


@dataclass(frozen=True)
class CrashInfo:
    """Captured at the moment an unhandled exception escapes `main()`'s loop.

    Deliberately minimal -- exception type/message plus which sprint/phase
    was in flight. A full traceback belongs in the harness's own log file,
    not in a five-second phone read; this is enough to tell "died on a bug"
    from "exited cleanly" and to know roughly where to start looking.
    """

    exc_type: str
    exc_message: str
    sprint: Optional[str] = None
    phase: Optional[str] = None


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
    crash: Optional[CrashInfo] = None,
    decline_reason: Optional[str] = None,
    push: Optional[PushState] = None,
    gate_failure: Optional[str] = None,
    infra_failure: Optional[str] = None,
    crash_loop_reason: Optional[str] = None,
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
        crash: Set when an unhandled exception escaped the main loop.
            Rendered as a distinct CRASHED banner -- a crash must not read
            as the same calm queue summary a clean exit produces.
        decline_reason: Set when the harness declined to run at all (a
            forced-sprint validation failure, a baseline-capture failure).
            An intentional, clean abort -- not a crash -- but STATUS.md
            must still say why, not just exist with a generic snapshot.
        push: Outcome of the last `git push`. Rendered as a PUSH FAILING
            banner plus a Push section, because a push that starts failing
            freezes this file's *remote* copy while the harness looks
            perfectly healthy -- the operator would otherwise have no way
            to tell a frozen board from a dead machine.
        gate_failure: Set when the per-sprint test gate found the suite red
            and the run stopped. Louder than the queue summary on purpose:
            a red tree is the one state where the correct response is to
            stop authoring, and it must not be reported only to a log the
            Scheduled Task discards.
        infra_failure: Set when consecutive sprints failed with INFRA_ERROR
            and the run gave up. `## Recent` already showed the individual
            outcomes, but nothing said the run had stopped, or why, or that
            the supervisor is now backing off rather than retrying.
        crash_loop_reason: The supervisor's own words for why it stopped,
            shown inside the CRASH-LOOP banner. "3 consecutive failures" and
            "6 consecutive infrastructure failures" call for entirely
            different responses from the operator.

    Returns:
        The full Markdown text of STATUS.md.
    """
    disagreements = disagreements or []
    # Computed once up front so the banner and the "Now" line agree on the
    # same age -- and so a stale beat gets flagged, not rendered as if a run
    # were live. A heartbeat file can outlive the process that wrote it (a
    # reboot mid-sprint leaves it behind); its age alone must not read as
    # health. Reuses IN_PROGRESS_STALE_MINUTES rather than a second
    # threshold constant.
    age: Optional[float] = _beat_age_seconds(beat) if beat is not None else None
    beat_is_stale = age is not None and age >= IN_PROGRESS_STALE_MINUTES * 60

    lines = ["# Ralph Status", ""]
    lines.append(f"_Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    lines.append("")

    if crash_loop:
        lines += ["## CRASH-LOOP", "", "Supervisor stopped after repeated failures."]
        if crash_loop_reason:
            lines.append(f"Reason: {crash_loop_reason}")
        lines += ["Nothing will resume until a human intervenes.", ""]
    if push is not None and not push.ok:
        last_ok = (
            _humanize_age(max(0.0, time.time() - push.last_success_timestamp))
            if push.last_success_timestamp is not None
            else "never"
        )
        lines += [
            "## PUSH FAILING",
            "",
            f"The last {push.consecutive_failures} `git push` attempt(s) failed, so the "
            "copy of this file on GitHub is FROZEN at whatever it said when push last "
            f"worked ({last_ok}). A frozen board is not a dead machine -- but from "
            "GitHub alone the two look identical, which is why this says so here.",
            "",
        ]
    if infra_failure is not None:
        lines += [
            "## INFRASTRUCTURE FAILING",
            "",
            "The harness stopped because the agent CLI, the network or the auth token "
            "is down -- not because of anything in the repo. It reported failure rather "
            "than success so the supervisor backs off (5m, 15m, 30m, then hourly) "
            "instead of relaunching every 30 seconds for the rest of the week.",
            "",
            "```",
            infra_failure,
            "```",
            "",
        ]
    if gate_failure is not None:
        lines += [
            "## TEST SUITE FAILING",
            "",
            "The harness stopped: the test-suite gate found a red tree, so no further "
            "sprint will be authored on top of it. Nothing is broken about the harness "
            "itself -- this is it refusing to build on a break.",
            "",
            "```",
            gate_failure,
            "```",
            "",
        ]
    if crash is not None:
        if crash.sprint and crash.phase:
            in_flight = f"{crash.sprint} ({crash.phase})"
        elif crash.sprint:
            in_flight = crash.sprint
        else:
            in_flight = "(no sprint was in flight)"
        lines += [
            "## CRASHED",
            "",
            f"The harness died on an unhandled `{crash.exc_type}`: {crash.exc_message}",
            f"In flight: {in_flight}",
            "",
        ]
    if decline_reason is not None:
        lines += ["## Harness Did Not Run", "", decline_reason, ""]
    if queue.is_starved:
        lines += ["## STARVED", "", "```", starvation_report(queue), "```", ""]
    if beat_is_stale:
        assert age is not None  # narrows for mypy; beat_is_stale implies age is not None
        lines += [
            "## STALE HEARTBEAT",
            "",
            f"No beat in over {IN_PROGRESS_STALE_MINUTES} minutes ({_humanize_age(age)}). "
            "The harness process may have died, or the machine rebooted mid-sprint and left "
            "this file behind -- its age alone does not mean a run is live.",
            "",
        ]

    lines.append("## Now")
    lines.append("")
    if beat is None:
        lines.append(
            "- **no heartbeat** -- harness is not running, or died without stopping cleanly"
        )
    else:
        sprint = beat.get("sprint") or "(between sprints)"
        phase = beat.get("phase") or "-"
        age_text = _humanize_age(age) if age is not None else "unknown"
        stale_suffix = " -- **STALE**" if beat_is_stale else ""
        lines.append(f"- Sprint: **{sprint}**")
        lines.append(f"- Phase: **{phase}**")
        lines.append(f"- Last beat: **{age_text}**{stale_suffix}")
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

    lines += ["## Push", ""]
    if push is None:
        lines.append("- no push recorded yet")
    else:
        attempt_age = _humanize_age(max(0.0, time.time() - push.timestamp))
        if push.ok:
            lines.append(f"- last push: **OK** ({attempt_age})")
        else:
            lines.append(
                f"- last push: **FAILED** ({attempt_age}, "
                f"{push.consecutive_failures} consecutive failure(s))"
            )
        if push.last_success_timestamp is None:
            lines.append("- last successful push: **never** -- nothing has reached GitHub")
        else:
            success_age = _humanize_age(max(0.0, time.time() - push.last_success_timestamp))
            lines.append(f"- last successful push: {success_age}")
        if not push.ok and push.detail:
            lines += ["- reason:", "", "```", push.detail, "```"]
    lines.append("")

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
    crash: Optional[CrashInfo] = None,
    decline_reason: Optional[str] = None,
    push: Optional[PushState] = None,
    gate_failure: Optional[str] = None,
    infra_failure: Optional[str] = None,
    crash_loop_reason: Optional[str] = None,
) -> None:
    """Write STATUS.md atomically.

    Does not catch exceptions itself -- the harness's call site is
    responsible for degrading a failure to a logged warning, so a rendering
    bug can never take down (or mask a real error ending) a week-long
    unattended run.

    *push* defaults to whatever `record_push` last persisted. Every caller
    wants the real push state and none of them is in a position to know it
    (the harness writes STATUS.md before it pushes; the supervisor does not
    push at all until after the write), so reading it here is what keeps the
    three call sites from each having to remember.
    """
    if push is None:
        push = read_push_state()
    atomic_write(
        STATUS_PATH,
        render_status(
            queue,
            beat,
            recent,
            crash_loop,
            disagreements,
            crash=crash,
            decline_reason=decline_reason,
            push=push,
            gate_failure=gate_failure,
            infra_failure=infra_failure,
            crash_loop_reason=crash_loop_reason,
        ),
    )
