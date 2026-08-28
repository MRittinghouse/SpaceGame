"""Restart policy and process loop for unattended runs.

Nothing supervises the supervisor, so it is deliberately the dumbest component
in the system: start a process, watch a heartbeat file, apply a bounded policy,
never touch the repo. Every capability added here is one that can fail with
nobody watching.

Bounded is the operative word. A harness that dies instantly and is relaunched
instantly burns a week of API budget in an afternoon, so the backoff and the
hard stop are load-bearing, not politeness.

Two failure modes drive most of this module's shape:

1. Liveness must be PID-based, not beat-age-based. A heartbeat file outlives
   the process that wrote it: a power cut mid-sprint leaves ``heartbeat.json``
   on disk with a timestamp whose age keeps climbing while nothing is running
   at all. Beat age alone cannot tell a live-but-slow run (must not be killed
   or double-started) from a dead run's leftover file (must be restarted).
   The fix is to check whether the beat's PID is *actually alive*, and that
   the live process is *actually ralph* rather than an unrelated process that
   happened to inherit a recycled PID -- existence alone is not identity.
   Beat age is used only as a secondary signal, to detect a hang in a
   process we already know is alive (see ``_supervise``).

2. Two of the harness's eleven exits happen before its own STATUS.md-writing
   ``finally`` block even starts: a pre-flight failure (``return rc``) and a
   lock-acquisition failure (``return 2``), both in ``harness.main()`` before
   its ``try``. The harness says nothing on either path. The supervisor is
   the layer that sees the exit code, so it is the layer that must report
   why -- except a lock conflict is *normal* (another instance is already
   running) and must stay quiet, not be reported as though it were a crash.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ralph import heartbeat, status, triage
from ralph.config import LOCK_FILE, PROJECT_ROOT
from ralph.roadmap_state import parse_sprints

# ---------------------------------------------------------------------------
# Restart policy (pure functions)
# ---------------------------------------------------------------------------

_BACKOFF_LADDER = (30.0, 120.0, 480.0)
MAX_CONSECUTIVE_FAILURES = 3
HEARTBEAT_STALE_SECONDS = 600.0

# How often the supervisor checks the heartbeat while the harness runs.
HEARTBEAT_POLL_SECONDS = 30.0

# argv used to launch the harness. A list, not a string, so no shell is
# ever invoked.
HARNESS_CMD: tuple[str, ...] = (sys.executable, "-m", "ralph.harness")


def backoff_seconds(consecutive_failures: int) -> float:
    """Delay before the next relaunch: 30s, 2m, then 8m thereafter."""
    idx = min(max(consecutive_failures, 0), len(_BACKOFF_LADDER) - 1)
    return _BACKOFF_LADDER[idx]


def should_restart(
    consecutive_failures: int,
    eligible: int,
    starved: bool,
) -> tuple[bool, str]:
    """Decide whether to relaunch the harness.

    Returns (restart, reason). Reason is always populated so the log explains
    itself without the reader inferring intent.
    """
    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        return False, f"stopping: {consecutive_failures} consecutive failures"
    if starved:
        return False, "stopping: queue is STARVED — restarting cannot help"
    if eligible <= 0:
        return False, "stopping: all work complete"
    return True, f"restarting: {eligible} sprint(s) eligible"


@dataclass
class RestartPolicy:
    """Tracks consecutive-failure count across a supervisor's lifetime.

    A dumb counter, not a wall-clock rate limiter: consecutive failures reset
    the moment a harness makes it into its main loop and exits 0
    (``record_success``), so a harness that fails once after running cleanly
    for six hours is not penalised the same as one that fails three times in
    three minutes.
    """

    consecutive_failures: int = 0
    max_consecutive_failures: int = MAX_CONSECUTIVE_FAILURES

    def record_success(self) -> None:
        """A harness run that exited 0 (whatever sprints it processed)."""
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    @property
    def exhausted(self) -> bool:
        """True once ``should_restart`` would refuse on failure count alone."""
        return self.consecutive_failures >= self.max_consecutive_failures


# ---------------------------------------------------------------------------
# PID liveness -- existence is not identity
# ---------------------------------------------------------------------------

# Substring that identifies a process as "the ralph harness", present in the
# command line the supervisor itself uses to launch it (``HARNESS_CMD``:
# ``python -m ralph.harness``). Kept as a marker (not an exact-cmd match) so
# it still matches when args are appended (--max-sprints, --dry-run, ...).
_HARNESS_IDENTITY_MARKER = "ralph.harness"


def _pid_command_line(pid: int) -> Optional[str]:
    """Return the full command line of *pid*, or None if it cannot be read.

    None covers both "no such process" and "process exists but the command
    line could not be determined" -- both must be treated as "not provably
    the harness", never as "assume it's fine".

    Windows-only (WMI via PowerShell's ``Get-CimInstance``); this project's
    supervisor targets Windows exclusively (see module docstring / the task
    brief's platform constraint). A POSIX fallback reads ``/proc`` for
    environments that happen to run the test suite there.
    """
    if sys.platform != "win32":
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except OSError:
            return None
        text = raw.decode("utf-8", errors="replace").replace("\x00", " ").strip()
        return text or None

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}" '
                "-ErrorAction SilentlyContinue).CommandLine",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = result.stdout.strip()
    return line or None


def looks_like_ralph_process(command_line: Optional[str]) -> bool:
    """Pure identity check: does *command_line* identify the ralph harness?

    Separated from ``_pid_command_line`` so the identity rule itself -- the
    part that actually encodes "recycled PID vs. real ralph process" -- is
    testable without spawning anything.
    """
    if not command_line:
        return False
    return _HARNESS_IDENTITY_MARKER in command_line.lower()


def is_harness_alive(pid: int) -> bool:
    """True iff *pid* both refers to a running process AND that process is
    identifiably the ralph harness -- not merely a PID that still resolves to
    *something* (existence is not identity; a recycled PID can belong to any
    unrelated process by the time this is checked)."""
    if pid <= 0:
        return False
    return looks_like_ralph_process(_pid_command_line(pid))


def heartbeat_pid_alive() -> Optional[int]:
    """The heartbeat's PID, if it names a currently-alive ralph process.

    None means either there is no heartbeat, its PID field is unusable, or
    the PID it names is not (or no longer) a live harness -- in every one of
    those cases the supervisor must treat this as "no live run", never as
    "unknown, assume alive".
    """
    beat = heartbeat.read_heartbeat()
    if beat is None:
        return None
    pid = beat.get("pid")
    if not isinstance(pid, int):
        return None
    return pid if is_harness_alive(pid) else None


# ---------------------------------------------------------------------------
# The two silent exits: pre-flight failure and lock conflict
# ---------------------------------------------------------------------------


def _status_mtime() -> Optional[float]:
    """mtime of STATUS.md, or None if it does not exist."""
    try:
        return status.STATUS_PATH.stat().st_mtime
    except OSError:
        return None


def harness_exited_silently(
    mtime_before: Optional[float],
    mtime_after: Optional[float],
) -> bool:
    """True when STATUS.md's mtime did not advance across a harness run.

    ``harness.main()`` writes STATUS.md in its outer ``finally`` -- but two
    exits happen before that ``try`` even begins (pre-flight failure, lock
    conflict), so on those paths STATUS.md is untouched. An unchanged mtime
    (including both being None, i.e. STATUS.md has never existed) is exactly
    that signature.
    """
    return mtime_before == mtime_after


def _read_lock_pid() -> Optional[int]:
    """The PID recorded in the harness lock file, or None if absent/unusable."""
    try:
        return int(LOCK_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def silent_exit_reason(rc: int, lock_holder_alive: bool) -> Optional[str]:
    """Why the harness exited without writing STATUS.md, or None to stay quiet.

    ``lock_holder_alive`` is whether the PID currently in the lock file is a
    live, identity-confirmed ralph process (see ``is_harness_alive``).

    Lock-acquisition failure is NORMAL: another instance is already running,
    the harness correctly declined to start a second one, and the right
    response is to do nothing and exit quietly -- returning None here means
    "do not report this". Anything else silent (a pre-flight failure) is
    reported with the exit code, since a repeating pre-flight failure would
    otherwise be complete silence for seven days.
    """
    if lock_holder_alive:
        return None
    return (
        f"harness exited with code {rc} without writing STATUS.md. This happens on "
        "two paths, both before the harness's main loop starts: a pre-flight check "
        "failure, or a lock already held by another instance. The supervisor checked "
        "the lock file and found no other live harness holding it, so this is most "
        "likely a pre-flight failure -- check ralph/logs, or run "
        "`python -m ralph.harness` by hand to see the pre-flight message."
    )


def _report_silent_exit(rc: int, recent: list[str]) -> None:
    """Write STATUS.md's decline_reason for a silent harness exit, unless the
    silence is a normal lock conflict (see ``silent_exit_reason``).

    Best-effort: a failure here (a roadmap-parsing bug, a disk error) must
    never crash the supervisor -- it is the one thing keeping the run alive.
    """
    lock_pid = _read_lock_pid()
    lock_holder_alive = lock_pid is not None and is_harness_alive(lock_pid)
    reason = silent_exit_reason(rc, lock_holder_alive)
    if reason is None:
        return
    try:
        sprints = parse_sprints()
        status.write_status(
            triage.analyse(sprints),
            heartbeat.read_heartbeat(),
            recent[-5:],
            disagreements=triage.blocks_disagreements(sprints),
            decline_reason=reason,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Process loop
# ---------------------------------------------------------------------------


def _kill_tree(pid: int) -> None:
    """Hard-kill *pid* and its whole process tree.

    A plain ``Popen.kill()`` only kills the direct child; a hung agent
    subprocess (the same class of bug ``proc.run_with_hard_timeout`` exists
    for) can leave grandchildren behind holding pipes/handles open. Windows
    only: this supervisor is a Windows-only deployment.
    """
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        return
    import os
    import signal

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _supervise(
    proc: "subprocess.Popen[bytes]",
    *,
    poll_interval: float = HEARTBEAT_POLL_SECONDS,
    stale_seconds: float = HEARTBEAT_STALE_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    beat_age: Callable[[], Optional[float]] = heartbeat.seconds_since_beat,
    kill: Callable[[int], None] = _kill_tree,
) -> int:
    """Wait for *proc* to exit, hard-killing it if its heartbeat goes stale.

    Dependency-injected (poll interval, sleep, beat age, kill) so the
    decision logic -- when to kill -- is testable without a real 600-second
    wait and without a real hung subprocess.
    """
    while proc.poll() is None:
        sleep(poll_interval)
        age = beat_age()
        if age is not None and age > stale_seconds:
            kill(proc.pid)
            break
    return proc.wait()


def _write_crash_loop_status(recent: list[str]) -> None:
    """Write STATUS.md with crash_loop=True before the supervisor gives up.

    Best-effort for the same reason as ``_report_silent_exit``: STATUS.md is
    the operator's only window into a week-long unattended run, so a bug
    producing it must never mask the real stop condition.
    """
    try:
        sprints = parse_sprints()
        status.write_status(
            triage.analyse(sprints),
            heartbeat.read_heartbeat(),
            recent[-5:],
            crash_loop=True,
            disagreements=triage.blocks_disagreements(sprints),
        )
    except Exception:
        pass


def _wait_for_foreign_harness(
    pid: int,
    *,
    poll_interval: float = HEARTBEAT_POLL_SECONDS,
    stale_seconds: float = HEARTBEAT_STALE_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    alive: Callable[[int], bool] = is_harness_alive,
    beat_age: Callable[[], Optional[float]] = heartbeat.seconds_since_beat,
    kill: Callable[[int], None] = _kill_tree,
) -> None:
    """Monitor a harness this supervisor did not launch (adopted at startup
    because its heartbeat's PID is alive and identity-confirmed), applying
    the same stale-heartbeat kill as a harness we did launch.

    This is the "supervisor itself was restarted by Scheduled Tasks while its
    child harness kept running" case: this supervisor instance has no Popen
    handle for that process, only its PID, so it cannot ``.wait()`` on it --
    it polls liveness instead. Dependency-injected for the same reason as
    ``_supervise``: the decision logic is testable without a real 600-second
    wait.
    """
    while alive(pid):
        sleep(poll_interval)
        age = beat_age()
        if age is not None and age > stale_seconds:
            kill(pid)
            return


def main() -> int:
    """Relaunch the harness under a bounded restart policy until there is no
    more work, the queue is starved, or failures exceed the cap.

    Deliberately thin: all the decisions above are pure functions, tested in
    isolation. This just wires them to real subprocesses and real time.
    """
    policy = RestartPolicy()
    recent: list[str] = []

    while True:
        live_pid = heartbeat_pid_alive()
        if live_pid is not None:
            print(
                f"supervisor: harness already alive (pid={live_pid}); "
                "adopting rather than double-launching.",
                flush=True,
            )
            _wait_for_foreign_harness(live_pid)
            continue

        mtime_before = _status_mtime()
        print(f"supervisor: launching {' '.join(HARNESS_CMD)}", flush=True)
        proc = subprocess.Popen(list(HARNESS_CMD), cwd=str(PROJECT_ROOT))
        rc = _supervise(proc)
        mtime_after = _status_mtime()
        print(f"supervisor: harness exited rc={rc}", flush=True)

        if harness_exited_silently(mtime_before, mtime_after):
            _report_silent_exit(rc, recent)

        if rc == 0:
            policy.record_success()
        else:
            policy.record_failure()
        recent.append(f"harness exit rc={rc}")

        sprints = parse_sprints()
        queue = triage.analyse(sprints)
        restart, reason = should_restart(
            policy.consecutive_failures, queue.eligible, queue.is_starved
        )
        print(f"supervisor: {reason}", flush=True)

        if not restart:
            if policy.exhausted:
                _write_crash_loop_status(recent)
            return 0

        time.sleep(backoff_seconds(policy.consecutive_failures))


if __name__ == "__main__":
    sys.exit(main())
