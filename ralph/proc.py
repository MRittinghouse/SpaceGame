"""Process and file primitives shared by the harness and the agent runner.

This module exists because ``harness.py`` imports ``agents.py``, so anything both
need cannot live in either without a circular import.

It deliberately holds no ralph domain knowledge -- no sprints, no roadmap, no
config beyond what is passed in. That keeps it small enough to be obviously
correct, which matters because both primitives here exist to survive failures
that are hard to reproduce.

``run_with_hard_timeout`` serves both pytest runs (the harness's own baseline
capture) and agent invocations (Task 4) -- both need a subprocess call that
cannot be left blocking past its timeout by a grandchild holding a pipe open.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from pathlib import Path


def atomic_write(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write *text* to *path* atomically.

    A plain ``Path.write_text`` truncates the target and then writes. A power
    cut in between leaves a truncated file. For ``ROADMAP.md`` (~9,000 lines
    holding every sprint definition) and ``state.json`` (how the harness knows
    where it was), that is unrecoverable without git.

    Writes to a sibling temp file, flushes and fsyncs it, then ``os.replace``,
    which is atomic on both Windows and POSIX. The temp is a sibling rather than
    in the system temp dir because ``os.replace`` cannot cross volumes on
    Windows.

    If any step fails (e.g., disk full during write), the temp file is unlinked
    before the exception propagates, so no .tmp sibling is left behind.

    Args:
        path: Destination file.
        text: Full contents to write.
        encoding: Text encoding.
    """
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        # If anything fails, clean up the temp file before re-raising.
        # This prevents a single transient error from leaving a .tmp file
        # that would block harness launches on subsequent runs.
        tmp.unlink(missing_ok=True)
        raise


def run_with_hard_timeout(
    cmd: list[str],
    timeout_seconds: float,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run *cmd* with a hard process-tree kill on timeout.

    Unlike ``subprocess.run(timeout=...)``, this helper does NOT block on
    ``communicate()`` after killing the direct child — the root cause of the
    8.5-hour hang where grandchildren held pipe handles open. It serves both
    pytest runs (the harness's baseline capture) and agent invocations, since
    both need a subprocess call that cannot be left blocking past its timeout
    by a grandchild holding a pipe open.

    Stdout and stderr are drained by background threads; those threads are
    abandoned (daemon) after a brief join window if the process kill did not
    release their file handles.

    Args:
        cmd: Command to run (passed directly to ``subprocess.Popen``).
        timeout_seconds: Wall-clock seconds before the tree is killed.
        cwd: Working directory (defaults to the current working directory).

    Returns:
        A ``CompletedProcess`` with captured stdout/stderr (as decoded str).

    Raises:
        subprocess.TimeoutExpired: After killing the process tree on timeout.
    """
    effective_cwd = cwd or os.getcwd()

    popen_kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "cwd": effective_cwd,
    }
    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP lets taskkill /T kill the full tree.
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True  # os.setsid() equivalent

    proc = subprocess.Popen(cmd, **popen_kwargs)

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    def _drain(pipe: object, buf: list[bytes]) -> None:
        try:
            for chunk in iter(lambda: pipe.read(4096), b""):  # type: ignore[attr-defined]
                buf.append(chunk)
        except Exception:
            pass

    t_out = threading.Thread(target=_drain, args=(proc.stdout, stdout_chunks), daemon=True)
    t_err = threading.Thread(target=_drain, args=(proc.stderr, stderr_chunks), daemon=True)
    t_out.start()
    t_err.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
            )
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                proc.kill()
        # Brief window for drain threads to flush before abandoning.
        t_out.join(timeout=2)
        t_err.join(timeout=2)

    if not timed_out:
        t_out.join(timeout=2)
        t_err.join(timeout=2)

    stdout_str = b"".join(stdout_chunks).decode("utf-8", errors="replace")
    stderr_str = b"".join(stderr_chunks).decode("utf-8", errors="replace")

    if timed_out:
        raise subprocess.TimeoutExpired(
            cmd=cmd,
            timeout=timeout_seconds,
            output=stdout_str.encode(),
            stderr=stderr_str.encode(),
        )

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout_str,
        stderr=stderr_str,
    )
