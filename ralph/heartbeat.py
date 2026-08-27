"""Liveness signal for the harness.

A dead harness and a wedged harness are indistinguishable by PID: both are "a
process that is not progressing". That ambiguity is what let SH-3 sit unnoticed
for 19 hours and run 7 hang for 8.5 -- in the second case the process was very
much alive, blocked on a child, burning 0.5 seconds of CPU.

A timestamp written on a timer resolves it. Alive plus a fresh beat is working;
alive plus a stale beat is wedged. The supervisor acts on the difference.

Written on a TIMER rather than on phase transitions on purpose: a legitimate
90-minute implement phase must stay visibly alive, and a phase-transition beat
would make it look wedged for 90 minutes.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from ralph.config import PROJECT_ROOT
from ralph.proc import atomic_write

HEARTBEAT_PATH: Path = PROJECT_ROOT / "ralph" / "heartbeat.json"


def write_heartbeat(sprint: Optional[str], phase: Optional[str]) -> None:
    """Record that the harness is alive, and what it believes it is doing."""
    payload: dict[str, object] = {
        "pid": os.getpid(),
        "timestamp": time.time(),
        "sprint": sprint,
        "phase": phase,
    }
    atomic_write(HEARTBEAT_PATH, json.dumps(payload, indent=2))


def read_heartbeat() -> Optional[dict[str, object]]:
    """Return the heartbeat payload, or None if absent or unreadable.

    Never raises. The supervisor calls this in its main loop and must not die
    because a file was half-written or hand-edited.
    """
    try:
        data = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def seconds_since_beat() -> Optional[float]:
    """Age of the last heartbeat in seconds, or None if unavailable."""
    data = read_heartbeat()
    if data is None:
        return None
    ts = data.get("timestamp")
    if not isinstance(ts, (int, float)):
        return None
    return max(0.0, time.time() - float(ts))


def start_heartbeat_thread(
    get_context: Callable[[], tuple[Optional[str], Optional[str]]],
    interval_seconds: float = 30.0,
) -> threading.Event:
    """Beat every *interval_seconds* until the returned event is set.

    Args:
        get_context: Called each beat; returns (sprint_id, phase) so the
            heartbeat reflects what the harness is doing right now.
        interval_seconds: Seconds between beats.

    Returns:
        An Event; set it to stop the thread.
    """
    stop = threading.Event()

    def _loop() -> None:
        while not stop.is_set():
            try:
                sprint, phase = get_context()
                write_heartbeat(sprint, phase)
            except Exception:
                # Never let a heartbeat failure kill the run it is monitoring.
                pass
            stop.wait(interval_seconds)

    threading.Thread(target=_loop, name="ralph-heartbeat", daemon=True).start()
    return stop
