"""Restart policy and process loop for unattended runs.

Nothing supervises the supervisor, so it is deliberately the dumbest component
in the system: start a process, watch a heartbeat file, apply a bounded policy.
Every capability added here is one that can fail with nobody watching.

It touches the repo in exactly one narrow way, and only because leaving that
out was a defect: after it writes a STATUS.md of its own it commits and pushes
that file (``_publish_status``), reusing the harness's own commit/push helpers
rather than inventing a second mechanism. Every remote signal in this system is
emitted by the harness, so on the two paths where the harness cannot run --
a repeating pre-flight failure and a crash-loop stop, the two states that mean
the week is over -- a local-only report is no report at all: GitHub keeps
serving the last STATUS.md the harness pushed, and its beat age is re-rendered
at read time, so it reads as a healthy run forever. The publish is entirely
best-effort: it cannot crash the supervisor and cannot prevent a restart.

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

2. Two of the harness's exits happen before its own STATUS.md-writing
   ``finally`` block even starts: a pre-flight failure (``return 4``) and a
   lock-acquisition failure (``return 2``), both in ``harness.main()`` before
   its ``try``. The harness says nothing on either path. The supervisor is
   the layer that sees the exit code, so it is the layer that must report
   why -- except a lock conflict is *normal* (another instance is already
   running) and must stay quiet, not be reported as though it were a crash.
   The two are distinguishable by exit code alone (``silent_exit_reason``):
   an earlier version of this module disambiguated them by re-checking the
   lock file's live PID after the fact, which has its own TOCTOU race
   (something else could grab or release the lock in the gap). Reading the
   harness's own already-decided exit code has no such race.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Callable, Optional

from ralph import heartbeat, status, triage
from ralph.config import LOGS_DIR, PROJECT_ROOT, RALPH_DIR
from ralph.proc import atomic_write
from ralph.roadmap_state import parse_sprints

# ---------------------------------------------------------------------------
# Logging -- the supervisor's only durable channel on the machine
# ---------------------------------------------------------------------------

# Both components used to log exclusively via `print`, and the Scheduled Task
# redirects nothing, so under the deployment this code exists for NOTHING was
# written to disk. `ralph/logs/` held only per-phase agent transcripts, which
# meant `silent_exit_reason`'s own guidance ("check ralph/logs") pointed at a
# directory that structurally could not contain the pre-flight message it was
# telling the operator to look for.
SUPERVISOR_LOG_PATH: Path = LOGS_DIR / "supervisor.log"
HARNESS_LOG_PATH: Path = LOGS_DIR / "harness.log"

# Seven days of restarts is a lot of lines but not a lot of bytes. One
# rotation is enough to bound the disk while keeping recent history; a full
# rotating scheme would be more machinery than the problem deserves.
LOG_MAX_BYTES: int = 5 * 1024 * 1024


def _rotate_if_large(path: Path, max_bytes: int = LOG_MAX_BYTES) -> None:
    """Move *path* aside once it exceeds *max_bytes*, keeping one generation."""
    try:
        if path.stat().st_size < max_bytes:
            return
    except OSError:
        return
    try:
        path.replace(path.with_suffix(path.suffix + ".1"))
    except OSError:
        pass


def _log(message: str) -> None:
    """Print *message* and append it to the supervisor's log file.

    Best-effort on the file half: a supervisor that cannot write its log must
    still supervise. Printing is kept because a foreground smoke drill is the
    one context where stdout is actually read.
    """
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_if_large(SUPERVISOR_LOG_PATH)
        with open(SUPERVISOR_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _open_harness_log() -> Optional[IO[bytes]]:
    """Append-mode handle for the harness's stdout/stderr, or None.

    The harness logs via `print`, and `Popen` with no stdout/stderr makes it
    inherit the supervisor's handles -- which, under a Scheduled Task, are
    discarded. Handing it a file is what turns every `harness.log()` line,
    every traceback, and every pre-flight message into something the operator
    can read after the fact.
    """
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_if_large(HARNESS_LOG_PATH)
        return open(HARNESS_LOG_PATH, "ab")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Restart policy (pure functions)
# ---------------------------------------------------------------------------

_BACKOFF_LADDER = (30.0, 120.0, 480.0)
MAX_CONSECUTIVE_FAILURES = 3
HEARTBEAT_STALE_SECONDS = 600.0

# How often the supervisor checks the heartbeat while the harness runs.
HEARTBEAT_POLL_SECONDS = 30.0

# Upper bound on the `taskkill` in `_kill_tree`. The kill is the supervisor's
# only recovery action; an unbounded one could wedge the supervisor itself.
KILL_TIMEOUT_SECONDS = 60.0

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


# harness.main()'s two silent exits are now distinguishable by exit code
# alone: `_preflight_checks` returns HARNESS_RC_PREFLIGHT_FAILURE (4) on all
# nine of its failure paths (Task 9 fix round 1, Finding 2 -- previously
# these shared code 2 with the lock-conflict path below, which made the two
# genuinely ambiguous and forced disambiguation onto a lock-file liveness
# check with its own TOCTOU race). `_acquire_lock()` failing still returns
# HARNESS_RC_LOCK_CONFLICT (2), unchanged -- the harness's own choice of
# which code to return is synchronous with the exit itself, so reading it
# has no race the way reading the lock file's live state afterward does.
HARNESS_RC_LOCK_CONFLICT = 2
HARNESS_RC_PREFLIGHT_FAILURE = 4


def silent_exit_reason(rc: int) -> Optional[str]:
    """Why the harness exited without writing STATUS.md, or None to stay quiet.

    Lock-acquisition failure (``HARNESS_RC_LOCK_CONFLICT``) is NORMAL: another
    instance is already running, the harness correctly declined to start a
    second one, and the right response is to do nothing and exit quietly --
    returning None here means "do not report this". Any other silent exit
    (in practice, ``HARNESS_RC_PREFLIGHT_FAILURE``) is reported with the exit
    code, since a repeating pre-flight failure would otherwise be complete
    silence for seven days.
    """
    if rc == HARNESS_RC_LOCK_CONFLICT:
        return None
    return (
        f"harness exited with code {rc} without writing STATUS.md. This happens on "
        "two paths, both before the harness's main loop starts: a pre-flight check "
        "failure, or a lock already held by another instance. Exit code "
        f"{HARNESS_RC_LOCK_CONFLICT} means the latter (normal, not reported); any "
        "other code -- including this one -- means a pre-flight check failed. The "
        "pre-flight message itself is in `ralph/logs/harness.log` (the harness's "
        "stdout, captured by the supervisor); the supervisor's own account of the "
        "run is in `ralph/logs/supervisor.log`. Failing that, run "
        "`python -m ralph.harness` by hand."
    )


def _publish_status(label: str) -> bool:
    """Commit and push the STATUS.md this supervisor just wrote.

    The supervisor owns the two messages that matter most -- "the harness will
    not start" (a repeating pre-flight failure) and "nothing will resume"
    (crash-loop) -- and until this existed it wrote both to local disk only.
    Every remote signal in this system is emitted by the harness, so on exactly
    the paths where the harness cannot run, no channel remained: GitHub kept
    serving the last STATUS.md the harness pushed, whose beat age is
    re-rendered at read time and therefore reads as recent. A dead run and a
    working one were indistinguishable, forever.

    The module docstring's "never touch the repo" rule is narrowed rather than
    abandoned: this commits exactly the one file it just wrote (plus ROADMAP.md,
    which `_commit_harness_bookkeeping` stages alongside it -- desirable here,
    since a harness killed mid-sprint leaves roadmap edits that would otherwise
    fail the next pre-flight), and it reuses the harness's own commit/push
    helpers rather than inventing a second mechanism that could disagree with
    them.

    Every failure is caught and logged. A push that cannot run must never crash
    the supervisor or block a restart -- that would trade a reporting gap for
    the end of the run.

    Args:
        label: Short identifier for the commit message and the log line.

    Returns:
        True if the push was attempted and recorded as successful.
    """
    try:
        # Imported lazily: the supervisor must still start and supervise if
        # `harness` is unimportable, and that is precisely the situation in
        # which someone needs the supervisor most.
        from ralph import harness

        harness._commit_harness_bookkeeping(label, "supervisor status report")
        harness._push_after_sprint(label, harness.Outcome.OK, True)
    except Exception as exc:  # nothing supervises the supervisor: swallow, never crash
        _log(f"supervisor: could not publish STATUS.md ({label}): {exc!r}")
        return False

    pushed = status.read_push_state()
    if pushed is not None and pushed.ok:
        _log(f"supervisor: published STATUS.md ({label}) to origin")
        return True
    detail = pushed.detail if pushed is not None else "no push state recorded"
    _log(
        f"supervisor: STATUS.md ({label}) was committed but NOT pushed; the "
        f"GitHub copy is frozen. {detail}"
    )
    return False


def _report_silent_exit(rc: int, recent: list[str]) -> None:
    """Write, commit and push STATUS.md's decline_reason for a silent harness
    exit, unless the silence is a normal lock conflict (see
    ``silent_exit_reason``).

    A repeating pre-flight failure is the single most likely way an unattended
    run dies, and the pre-flight exit is the one path on which the harness
    writes no STATUS.md of its own -- so if this report stops at the local
    disk, the operator's GitHub view keeps showing the last healthy file the
    harness pushed and never changes again. Hence ``_publish_status``.

    Best-effort throughout: a failure here (a roadmap-parsing bug, a disk
    error, a rejected push) must never crash the supervisor -- it is the one
    thing keeping the run alive.
    """
    reason = silent_exit_reason(rc)
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
    except Exception as exc:  # nothing supervises the supervisor: swallow, never crash
        _log(f"supervisor: could not write STATUS.md for silent exit rc={rc}: {exc!r}")
        return
    _publish_status("supervisor-silent-exit")


# ---------------------------------------------------------------------------
# Terminal stop -- "decided to stop" is not the same as "was stopped"
# ---------------------------------------------------------------------------

# The Scheduled Task now has a repeating trigger, because an At-startup-only
# task cannot recover from anything short of a reboot. That trigger is what
# heals a supervisor that was KILLED -- by the 72-hour execution limit, by the
# OOM killer, by a stray taskkill.
#
# On its own, though, it would also resurrect a supervisor that stopped on
# purpose, and that would quietly destroy the bounded restart policy: the
# 3-consecutive-failure cap lives in an in-process counter, so a relaunched
# supervisor starts from zero and grants three more harness attempts every
# repetition, forever. The cap and the exponential backoff are the difference
# between a quiet week and an expensive one; a trigger that erases them is not
# an improvement.
#
# So a deliberate stop is recorded, and a fresh supervisor that finds the
# record exits without launching anything. A killed supervisor leaves no
# record and is relaunched normally.
SUPERVISOR_STOP_PATH: Path = RALPH_DIR / "supervisor_stop.json"


def read_terminal_stop() -> Optional[dict[str, object]]:
    """The recorded deliberate stop, or None if the supervisor may run.

    A missing or corrupt file reads as None: failing open is right here,
    because the alternative -- a parse bug silently preventing the supervisor
    from ever starting again -- is the very failure this module exists to
    prevent.
    """
    try:
        raw = json.loads(SUPERVISOR_STOP_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def record_terminal_stop(reason: str) -> None:
    """Record that this supervisor stopped on purpose. Best-effort."""
    try:
        SUPERVISOR_STOP_PATH.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(
            SUPERVISOR_STOP_PATH,
            json.dumps({"reason": reason, "at": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2),
        )
    except OSError as exc:
        _log(f"supervisor: could not record the stop reason: {exc}")


def clear_terminal_stop() -> None:
    """Forget a recorded stop, so the next launch runs. Best-effort."""
    try:
        SUPERVISOR_STOP_PATH.unlink(missing_ok=True)
    except OSError:
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
        # Bounded: this is the supervisor's only recovery action, and it had no
        # timeout at all. A `taskkill` that blocked would wedge the supervisor
        # itself, in the one moment it is the last thing still working.
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=KILL_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            _log(f"supervisor: taskkill on pid={pid} did not complete: {exc!r}")
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
    """Write, commit and push STATUS.md with crash_loop=True before the
    supervisor gives up.

    This is the most important message the system can send: the supervisor
    will not restart the harness again, so nothing further will happen until
    a human intervenes. Recording it only on local disk made "stopped for
    good" and "between sprints" identical from GitHub, which is the one
    distinction the operator is away and unable to make for themselves.

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
    except Exception as exc:  # nothing supervises the supervisor: swallow, never crash
        _log(f"supervisor: could not write crash-loop STATUS.md: {exc!r}")
        return
    _publish_status("supervisor-crash-loop")


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
    stopped = read_terminal_stop()
    if stopped is not None:
        _log(
            f"supervisor: a previous instance stopped deliberately "
            f"({stopped.get('reason', 'reason not recorded')} at "
            f"{stopped.get('at', 'unknown time')}); not relaunching. The repeating "
            "Scheduled Task trigger exists to recover a supervisor that was "
            "KILLED, not to grant a fresh 3-failure budget every few minutes to "
            f"one that gave up. Delete {SUPERVISOR_STOP_PATH} to resume."
        )
        return 0

    policy = RestartPolicy()
    recent: list[str] = []

    while True:
        live_pid = heartbeat_pid_alive()
        if live_pid is not None:
            _log(
                f"supervisor: harness already alive (pid={live_pid}); "
                "adopting rather than double-launching."
            )
            _wait_for_foreign_harness(live_pid)
            continue

        mtime_before = _status_mtime()
        _log(f"supervisor: launching {' '.join(HARNESS_CMD)} (stdout -> {HARNESS_LOG_PATH})")
        # The harness logs via `print`. Without these handles it inherits the
        # supervisor's, which a Scheduled Task discards -- so a pre-flight
        # failure, the most likely way this run dies, would be written down
        # nowhere at all.
        harness_log = _open_harness_log()
        try:
            proc = subprocess.Popen(
                list(HARNESS_CMD),
                cwd=str(PROJECT_ROOT),
                stdout=harness_log,
                stderr=subprocess.STDOUT if harness_log is not None else None,
            )
        finally:
            # Popen duplicates the handle into the child; the parent's copy is
            # dead weight and would keep the rotated file open.
            if harness_log is not None:
                harness_log.close()
        rc = _supervise(proc)
        mtime_after = _status_mtime()
        _log(f"supervisor: harness exited rc={rc}")

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
        _log(f"supervisor: {reason}")

        if not restart:
            if policy.exhausted:
                _write_crash_loop_status(recent)
            # Recorded BEFORE returning, so the repeating trigger's next
            # firing sees a deliberate stop rather than an absence.
            record_terminal_stop(reason)
            return 0

        time.sleep(backoff_seconds(policy.consecutive_failures))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as _exc:  # the supervisor's own death must not be silent
        import traceback

        _log(f"supervisor: DIED on {type(_exc).__name__}: {_exc}")
        _log(traceback.format_exc())
        raise
