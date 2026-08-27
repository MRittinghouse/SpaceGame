# Harness Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the ralph harness survive seven days unattended — through process death, machine reboot, hung subprocesses, and an exhausted queue — without a human noticing and recovering.

**Architecture:** A new dependency-free `ralph/proc.py` holds two primitives (atomic file write, hard-timeout subprocess run) that both `harness.py` and `agents.py` consume. A heartbeat thread makes "alive but wedged" detectable. A deliberately dumb `ralph/supervisor.py` watches the heartbeat and restarts the harness under a bounded policy. Triage changes make starvation and blocked-dependency cascades visible instead of silent.

**Tech Stack:** Python 3.13, stdlib only (`os.replace`, `subprocess.Popen`, `threading`), pytest, Windows Task Scheduler for boot survival.

**Spec:** `docs/superpowers/specs/2026-08-27-harness-resilience-design.md`

## Global Constraints

- Python 3.13. Type hints on all functions (`disallow_untyped_defs = true`).
- Ruff format, 100-char lines. `ruff check spacegame/` must stay clean; `ralph/` is not in the lint gate but do not add new violations.
- MyPy runs against `mypy-baseline.txt`. Do NOT regenerate the baseline in these commits.
- Full suite must stay green at or above **10,586 passing**. Run with `pytest -n 8`, never `-n auto` (see `ralph.config.TEST_WORKERS`; `-n auto` hangs 6 runs in 10).
- `harness.py` imports `agents.py`. Therefore **`agents.py` must never import from `harness.py`** — shared code goes in `ralph/proc.py`.
- Every new file needs a module docstring explaining *why*, per the project's existing convention.

---

## File Structure

| File | Responsibility |
|---|---|
| `ralph/proc.py` (NEW) | Process and file primitives shared by harness and agents: `atomic_write`, `run_with_hard_timeout`. No ralph domain knowledge. |
| `ralph/heartbeat.py` (NEW) | Write/read the liveness file. Small enough to be obviously correct. |
| `ralph/supervisor.py` (NEW) | Restart policy. Starts the harness, watches the heartbeat, backs off, hard-stops. Never touches the repo. |
| `ralph/triage.py` (NEW) | Queue analysis: starvation detection, blocked-dependency cascade, `Blocks:` consistency. Pure functions over parsed sprints. |
| `ralph/status.py` (NEW) | Renders `STATUS.md` from harness state + triage. |
| `ralph/roadmap_state.py` | Modify: use `atomic_write`; parse the `Blocks:` field. |
| `ralph/harness.py` | Modify: use `atomic_write`; start the heartbeat; wire triage + retry grace; write `STATUS.md`. |
| `ralph/agents.py` | Modify: use `run_with_hard_timeout` instead of `subprocess.run`. |
| `scripts/install_supervisor_task.ps1` (NEW) | Registers the Windows Scheduled Task (At startup). |

---

## Task 1: Atomic file writes

**Files:**
- Create: `ralph/proc.py`
- Test: `tests/test_ralph/test_proc.py`

**Interfaces:**
- Consumes: nothing (leaf module)
- Produces: `atomic_write(path: Path, text: str, encoding: str = "utf-8") -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ralph/test_proc.py
"""Tests for ralph.proc — the process/file primitives shared by harness and agents."""

from __future__ import annotations

from pathlib import Path

from ralph.proc import atomic_write


class TestAtomicWrite:
    def test_writes_content(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert target.read_text(encoding="utf-8") == "hello"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        target.write_text("old", encoding="utf-8")
        atomic_write(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_leaves_no_temp_file_behind(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert list(tmp_path.iterdir()) == [target], (
            "atomic_write must clean up its temp file; a leftover .tmp means a "
            "future write could collide or a reader could pick up a partial file"
        )

    def test_temp_file_is_same_directory(self, tmp_path: Path, monkeypatch) -> None:
        """os.replace is only atomic within a volume; the temp must be a sibling.

        On Windows a cross-volume replace raises OSError, so writing the temp to
        the system temp dir would break on any machine where the repo is not on
        C:.
        """
        seen: list[Path] = []
        real_replace = __import__("os").replace

        def spy(src, dst):  # type: ignore[no-untyped-def]
            seen.append(Path(src))
            return real_replace(src, dst)

        monkeypatch.setattr("ralph.proc.os.replace", spy)
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert seen and seen[0].parent == target.parent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_proc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ralph.proc'`

- [ ] **Step 3: Write minimal implementation**

```python
# ralph/proc.py
"""Process and file primitives shared by the harness and the agent runner.

This module exists because ``harness.py`` imports ``agents.py``, so anything both
need cannot live in either without a circular import.

It deliberately holds no ralph domain knowledge -- no sprints, no roadmap, no
config beyond what is passed in. That keeps it small enough to be obviously
correct, which matters because both primitives here exist to survive failures
that are hard to reproduce.
"""

from __future__ import annotations

import os
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

    Args:
        path: Destination file.
        text: Full contents to write.
        encoding: Text encoding.
    """
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding=encoding, newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ralph/test_proc.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add ralph/proc.py tests/test_ralph/test_proc.py
git commit -m "ralph: add atomic_write primitive

A plain write_text truncates then writes; a power cut between those two
steps leaves a truncated file. ROADMAP.md is ~9,000 lines holding every
sprint definition and state.json is how the harness knows where it was.

Temp file is a sibling, not in the system temp dir: os.replace cannot
cross volumes on Windows."
```

---

## Task 2: Generalise the hard-timeout runner

`_run_pytest_with_hard_timeout` already does the right thing but lives in `harness.py` and is named for pytest. `agents.py` cannot import from `harness.py` (circular), so it moves to `ralph/proc.py`.

**Files:**
- Modify: `ralph/proc.py`
- Modify: `ralph/harness.py` (delete the old helper, import the new one)
- Test: `tests/test_ralph/test_proc.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `run_with_hard_timeout(cmd: list[str], timeout_seconds: float, cwd: str | None = None) -> subprocess.CompletedProcess[str]`, raising `subprocess.TimeoutExpired` after killing the process tree

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_ralph/test_proc.py
import subprocess
import sys
import time

import pytest

from ralph.proc import run_with_hard_timeout


class TestRunWithHardTimeout:
    def test_returns_completed_process_on_success(self) -> None:
        result = run_with_hard_timeout([sys.executable, "-c", "print(1)"], timeout_seconds=30)
        assert result.returncode == 0
        assert "1" in result.stdout

    def test_captures_stderr(self) -> None:
        code = "import sys; sys.stderr.write('boom')"
        result = run_with_hard_timeout([sys.executable, "-c", code], timeout_seconds=30)
        assert "boom" in result.stderr

    def test_raises_timeout_and_returns_promptly(self) -> None:
        """The whole point: a hung child must not hold us past the timeout.

        subprocess.run(timeout=...) kills the direct child but keeps blocking in
        communicate() while grandchildren hold the pipe. That produced an
        8.5-hour stall on 2026-08-26. This asserts WALL CLOCK, not just that the
        exception is raised -- the exception was never the missing part.
        """
        started = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired):
            run_with_hard_timeout(
                [sys.executable, "-c", "import time; time.sleep(60)"], timeout_seconds=3
            )
        elapsed = time.monotonic() - started
        assert elapsed < 20, f"returned after {elapsed:.1f}s; the kill did not take effect"

    def test_kills_grandchildren_not_just_the_child(self) -> None:
        """A child that spawns a sleeping grandchild holding the pipe open.

        This is the exact shape of the real failure. Without a process-tree kill
        the grandchild keeps stdout open and the read never ends.
        """
        script = (
            "import subprocess, sys, time; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
            "time.sleep(60)"
        )
        started = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired):
            run_with_hard_timeout([sys.executable, "-c", script], timeout_seconds=3)
        elapsed = time.monotonic() - started
        assert elapsed < 20, f"returned after {elapsed:.1f}s; grandchild held the pipe"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_proc.py::TestRunWithHardTimeout -v`
Expected: FAIL with `ImportError: cannot import name 'run_with_hard_timeout'`

- [ ] **Step 3: Move the implementation**

Cut the body of `_run_pytest_with_hard_timeout` from `ralph/harness.py` (starts around line 383) into `ralph/proc.py`, renamed `run_with_hard_timeout`. **Its logic is already correct and generic — do not rewrite it.** Only these changes:

1. Rename the function.
2. Replace the `PROJECT_ROOT` default with `cwd or os.getcwd()`. `proc.py` must not import ralph config.
3. Add `subprocess`, `sys`, `threading` to the imports at the top of `proc.py`.
4. Update the docstring to say it serves both pytest runs and agent invocations.

In `ralph/harness.py`, delete the old function and add:

```python
from ralph.proc import atomic_write, run_with_hard_timeout
```

Update its one existing call site in `_capture_test_baseline` to `run_with_hard_timeout(..., cwd=str(PROJECT_ROOT))`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/ -v -k "proc or aseline"`
Expected: all pass, including pre-existing baseline-capture tests

- [ ] **Step 5: Commit**

```bash
git add ralph/proc.py ralph/harness.py tests/test_ralph/test_proc.py
git commit -m "ralph: move hard-timeout runner to proc.py and generalise it"
```

---

## Task 3: Wire atomic writes into harness and roadmap

**Files:**
- Modify: `ralph/roadmap_state.py` (`_write_roadmap`, around line 82)
- Modify: `ralph/harness.py` (`HarnessState.save`, around line 113; SUMMARY.md write ~1234; index sync write ~1481)
- Test: `tests/test_ralph/test_roadmap_state.py`, `tests/test_ralph/test_harness.py`

**Interfaces:**
- Consumes: `atomic_write` from Task 1
- Produces: no new public API; both write paths become crash-safe

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_ralph/test_roadmap_state.py
from unittest.mock import patch


class TestRoadmapWritesAreAtomic:
    def test_write_roadmap_uses_atomic_write(self, tmp_path) -> None:
        """A truncated ROADMAP.md loses every sprint definition.

        We cannot cut power in a test, so assert we never call the unsafe path.
        """
        from ralph import roadmap_state

        target = tmp_path / "ROADMAP.md"
        target.write_text("original", encoding="utf-8")
        with patch.object(roadmap_state, "ROADMAP_PATH", target):
            with patch("ralph.roadmap_state.atomic_write") as mock_atomic:
                roadmap_state._write_roadmap("new content")
        mock_atomic.assert_called_once()
        assert mock_atomic.call_args[0][1] == "new content"
```

```python
# append to tests/test_ralph/test_harness.py
class TestStateWritesAreAtomic:
    def test_state_save_uses_atomic_write(self, tmp_path) -> None:
        """A truncated state.json means the harness cannot start."""
        from unittest.mock import patch

        from ralph import harness

        target = tmp_path / "state.json"
        state = harness.HarnessState()
        with patch.object(harness, "STATE_FILE", target):
            with patch("ralph.harness.atomic_write") as mock_atomic:
                state.save()
        mock_atomic.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ralph/ -v -k "Atomic"`
Expected: FAIL — `atomic_write` is not imported in either module yet

- [ ] **Step 3: Write the implementation**

In `ralph/roadmap_state.py`:

```python
from ralph.proc import atomic_write


def _write_roadmap(content: str) -> None:
    atomic_write(ROADMAP_PATH, content)
```

In `ralph/harness.py`:

```python
    def save(self) -> None:
        payload = {
            "sprints": {sid: asdict(s) for sid, s in self.sprints.items()},
            "total_sprints_processed": self.total_sprints_processed,
            "last_run_started_at": self.last_run_started_at,
        }
        atomic_write(STATE_FILE, json.dumps(payload, indent=2, ensure_ascii=False))
```

Also swap the `SUMMARY.md` write and the index-sync write to `atomic_write`.

**Leave the lock file alone.** It holds a PID, is recreated every run, and a truncated one is already handled by the existing stale-lock check. Changing it adds risk for no gain.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/ -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add ralph/roadmap_state.py ralph/harness.py tests/test_ralph/
git commit -m "ralph: atomic writes for ROADMAP.md, state.json, SUMMARY.md"
```

---

## Task 4: Wire the hard timeout into agent invocation

This is the single highest-value change in the plan. `RALPH_TIMEOUT_IMPLEMENT` is currently an intention, not a guarantee.

**Files:**
- Modify: `ralph/agents.py` (the `subprocess.run` call around line 202, inside `_invoke_claude`)
- Test: `tests/test_ralph/test_agents.py`

**Interfaces:**
- Consumes: `run_with_hard_timeout` from Task 2
- Produces: no new API; `_invoke_claude` now honours its timeout even when the agent leaves grandchildren holding pipes

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_ralph/test_agents.py
class TestAgentInvocationUsesHardTimeout:
    def test_invoke_claude_uses_run_with_hard_timeout(self, tmp_path) -> None:
        """Agent phases are where the harness spends hours, so this is where a
        days-long stall comes from.

        subprocess.run(timeout=...) kills the direct child but keeps blocking in
        communicate() while grandchildren hold the pipe. SUITE-1 fixed that for
        baseline capture only; the agent path kept the broken construct.
        """
        from unittest.mock import MagicMock, patch

        from ralph import agents

        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "PHASE_OK"
        fake.stderr = ""

        with patch("ralph.agents.run_with_hard_timeout", return_value=fake) as mock_run:
            with patch("ralph.agents.subprocess.run") as mock_plain:
                agents._invoke_claude(
                    prompt="x", log_path=tmp_path / "l.log", phase=agents.Phase.PLAN
                )
        mock_run.assert_called_once()
        assert not mock_plain.called, (
            "the agent path must not use subprocess.run -- that is the construct "
            "that hung for 8.5 hours on 2026-08-26"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_agents.py::TestAgentInvocationUsesHardTimeout -v`
Expected: FAIL — `ralph.agents` has no attribute `run_with_hard_timeout`

- [ ] **Step 3: Write the implementation**

Add to the imports in `ralph/agents.py`:

```python
from ralph.proc import run_with_hard_timeout
```

Replace the `subprocess.run(...)` call inside `_invoke_claude` with:

```python
            result = run_with_hard_timeout(
                cmd,
                timeout_seconds=timeout,
                cwd=str(PROJECT_ROOT),
            )
```

Keep the surrounding `try` / `except subprocess.TimeoutExpired` intact — `run_with_hard_timeout` raises the same exception type, so the existing timeout handling still works. Do not change how the log file is written.

**Do not** remove `import subprocess` from `agents.py`; it is still needed for the `TimeoutExpired` type and the `git rev-parse` call at line ~404.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/ -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add ralph/agents.py tests/test_ralph/test_agents.py
git commit -m "ralph: hard timeout on the agent path, not just baseline capture

RALPH_TIMEOUT_* was an intention, not a guarantee. agents.py used plain
subprocess.run(timeout=...) -- the construct that hung for 8.5 hours on
2026-08-26, where the timeout killed the direct child but communicate()
kept blocking on grandchildren holding the pipe.

Agent phases are where the harness spends hours, so this is where a
days-long stall actually originates."
```

---

## Task 5: Heartbeat

A timeout only fires when the harness is *waiting*. SH-3 died between phases; run 7 sat alive at 0.5s CPU blocked on a child. Both look identical to healthy work if you only check whether the process exists — the mistake that cost 19 hours.

**Files:**
- Create: `ralph/heartbeat.py`
- Modify: `ralph/harness.py` (start the beat in `main`, update it on phase transitions)
- Test: `tests/test_ralph/test_heartbeat.py`

**Interfaces:**
- Consumes: `atomic_write` from Task 1
- Produces:
  - `HEARTBEAT_PATH: Path`
  - `write_heartbeat(sprint: str | None, phase: str | None) -> None`
  - `read_heartbeat() -> dict[str, object] | None`
  - `seconds_since_beat() -> float | None` (None when no readable heartbeat)
  - `start_heartbeat_thread(get_context: Callable[[], tuple[str | None, str | None]], interval_seconds: float = 30.0) -> threading.Event` — returns a stop event

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ralph/test_heartbeat.py
"""Tests for the liveness heartbeat.

A dead harness and a wedged harness look identical from the outside -- both are
"a process that is not making progress". Checking whether the PID exists cannot
tell them apart, which is why SH-3 sat unnoticed for 19 hours. The heartbeat is
what makes "alive but stuck" a detectable state.
"""

from __future__ import annotations

import time
from pathlib import Path

from ralph import heartbeat


class TestHeartbeat:
    def test_write_then_read_roundtrip(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        heartbeat.write_heartbeat("SH-2", "implement")
        data = heartbeat.read_heartbeat()
        assert data is not None
        assert data["sprint"] == "SH-2"
        assert data["phase"] == "implement"
        assert isinstance(data["pid"], int)

    def test_seconds_since_beat_is_small_right_after_write(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        heartbeat.write_heartbeat("SH-2", "implement")
        age = heartbeat.seconds_since_beat()
        assert age is not None and age < 5

    def test_missing_heartbeat_reads_as_none(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "absent.json")
        assert heartbeat.read_heartbeat() is None
        assert heartbeat.seconds_since_beat() is None

    def test_corrupt_heartbeat_reads_as_none_not_crash(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A truncated heartbeat must not take down the supervisor.

        The supervisor is the thing that restarts everything else; it has to be
        the most defensive code in the system.
        """
        hb = tmp_path / "hb.json"
        hb.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", hb)
        assert heartbeat.read_heartbeat() is None

    def test_thread_beats_repeatedly_then_stops(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(heartbeat, "HEARTBEAT_PATH", tmp_path / "hb.json")
        stop = heartbeat.start_heartbeat_thread(lambda: ("S", "plan"), interval_seconds=0.05)
        time.sleep(0.3)
        first = heartbeat.read_heartbeat()
        assert first is not None
        stop.set()
        time.sleep(0.2)
        frozen = heartbeat.read_heartbeat()
        time.sleep(0.3)
        assert heartbeat.read_heartbeat() == frozen, "thread kept beating after stop"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_heartbeat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ralph.heartbeat'`

- [ ] **Step 3: Write the implementation**

```python
# ralph/heartbeat.py
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
    payload = {
        "pid": os.getpid(),
        "timestamp": time.time(),
        "sprint": sprint,
        "phase": phase,
    }
    atomic_write(HEARTBEAT_PATH, json.dumps(payload, indent=2))


def read_heartbeat() -> Optional[dict]:
    """Return the heartbeat payload, or None if absent or unreadable.

    Never raises. The supervisor calls this in its main loop and must not die
    because a file was half-written or hand-edited.
    """
    try:
        return json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/test_heartbeat.py -v`
Expected: 5 passed

- [ ] **Step 5: Wire it into the harness**

In `ralph/harness.py`, add module-level tracking of the current sprint and phase, and start the thread in `main()` before the sprint loop:

```python
_current_context: tuple[Optional[str], Optional[str]] = (None, None)


def _set_context(sprint: Optional[str], phase: Optional[str]) -> None:
    global _current_context
    _current_context = (sprint, phase)
```

Call `_set_context(sprint_id, "plan")` / `"implement"` / `"review"` at each existing `log(f"{sprint_id}: phase=... starting")` site in `execute_sprint`, and `_set_context(None, None)` when the loop ends.

In `main()`, immediately after pre-flight passes:

```python
    heartbeat_stop = heartbeat.start_heartbeat_thread(lambda: _current_context)
```

and set it in the exit path: `heartbeat_stop.set()`.

Add `from ralph import heartbeat` to the imports.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -n 8 -q`
Expected: 10,586+ passed

- [ ] **Step 7: Commit**

```bash
git add ralph/heartbeat.py ralph/harness.py tests/test_ralph/test_heartbeat.py
git commit -m "ralph: heartbeat so a wedged harness is distinguishable from a busy one

A dead harness and a wedged one look identical by PID. SH-3 sat unnoticed
for 19 hours; run 7 hung 8.5 hours very much alive, blocked on a child at
0.5s CPU. Checking whether the process exists cannot tell them apart.

Beat is written on a TIMER, not on phase transitions: a legitimate
90-minute implement phase must stay visibly alive."
```

---

## Task 6: Triage — starvation detection and blocked-dependency cascade

**Files:**
- Create: `ralph/triage.py`
- Modify: `ralph/harness.py` (replace the bare `"No eligible sprints. Exiting cleanly."` at line ~1422)
- Test: `tests/test_ralph/test_triage.py`

**Interfaces:**
- Consumes: `roadmap_state.Sprint`, `roadmap_state.eligible_sprints`
- Produces:
  - `QueueState` dataclass: `total: int`, `todo: int`, `eligible: int`, `blocked_ids: list[str]`, `stranded_by: dict[str, list[str]]`, `is_starved: bool`
  - `analyse(sprints: dict[str, Sprint]) -> QueueState`
  - `starvation_report(state: QueueState) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ralph/test_triage.py
"""Tests for queue triage.

The harness logged "No eligible sprints. Exiting cleanly." for two completely
different situations: everything is done, and everything is stranded. On
2026-08-27 the second was true -- 15 todo, 0 eligible, five held by SA-F2, which
had been blocked since April on a transient failure -- and the harness reported
success. Four months of a stalled arc followed from one ambiguous log line.
"""

from __future__ import annotations

from ralph.roadmap_state import Sprint
from ralph.triage import analyse, starvation_report


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_triage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ralph.triage'`

- [ ] **Step 3: Write the implementation**

```python
# ralph/triage.py
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
    blocked = sorted(
        s.sprint_id for s in sprints.values() if s.status.strip().lower() == "blocked"
    )
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/test_triage.py -v`
Expected: 6 passed

- [ ] **Step 5: Wire it into the harness**

In `ralph/harness.py`, add `from ralph import triage` and replace the bare exit around line 1422:

```python
                    queue = triage.analyse(sprints)
                    if queue.is_starved:
                        log(triage.starvation_report(queue))
                        log("STARVED -- exiting. This is NOT completion.")
                    else:
                        log("No eligible sprints; all work complete. Exiting cleanly.")
                    break
```

- [ ] **Step 6: Verify against the real roadmap**

Run:
```bash
python -c "from ralph import roadmap_state, triage; s=roadmap_state.parse_sprints(); print(triage.starvation_report(triage.analyse(s)))"
```
Expected: names SA-F2 and the sprints it strands. This is the live case — the same state that produced "Exiting cleanly" on 2026-08-27.

- [ ] **Step 7: Commit**

```bash
git add ralph/triage.py ralph/harness.py tests/test_ralph/test_triage.py
git commit -m "ralph: distinguish starvation from completion

The harness logged the same line whether every sprint was done or every
sprint was stranded. On 2026-08-27: 15 todo, 0 eligible, five held by
SA-F2 (blocked since April on a transient bail) -- and it reported
'Exiting cleanly'. Four months of a stalled arc followed from one
ambiguous log line.

Cascade is transitive: a sprint two hops downstream of the blocker is
just as stranded, and that is the part that stayed invisible."
```

---

## Task 7: Triage — retry grace and `Blocks:` consistency

**Files:**
- Modify: `ralph/roadmap_state.py` (parse `**Blocks**:` into `Sprint.blocks`)
- Modify: `ralph/triage.py` (add `blocks_disagreements`)
- Modify: `ralph/harness.py` (`_mark_terminal_outcome` gains the retry grace)
- Test: `tests/test_ralph/test_triage.py`, `tests/test_ralph/test_harness.py`

**Interfaces:**
- Consumes: `QueueState`, `SprintState.last_outcome` (existing)
- Produces:
  - `Sprint.blocks: list[str]` (new field, default empty)
  - `triage.blocks_disagreements(sprints: dict[str, Sprint]) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_ralph/test_triage.py
from ralph.triage import blocks_disagreements


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
```

```python
# append to tests/test_ralph/test_harness.py
class TestRetryGrace:
    def test_first_failure_retries_rather_than_blocking(self) -> None:
        """SA-F2 died on returncode 1 with 135 bytes of output and stayed
        blocked for four months. One retry absorbs that entire class."""
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        assert harness._should_retry(sprint_state, Outcome.ERROR) is True

    def test_second_failure_blocks(self) -> None:
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        sprint_state.retry_count = 1
        assert harness._should_retry(sprint_state, Outcome.ERROR) is False

    def test_blocked_outcome_is_never_retried(self) -> None:
        """A deliberate PHASE_BLOCKED is a judgement, not a failure."""
        from ralph import harness
        from ralph.agents import Outcome

        state = harness.HarnessState()
        sprint_state = state.for_sprint("T-1")
        assert harness._should_retry(sprint_state, Outcome.BLOCKED) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ralph/ -v -k "BlocksConsistency or RetryGrace"`
Expected: FAIL — `blocks_disagreements` and `_should_retry` do not exist

- [ ] **Step 3: Write the implementation**

In `ralph/roadmap_state.py`, add to the `Sprint` dataclass:

```python
    blocks: list[str] = field(default_factory=list)
```

and parse it in the same place `depends_on` is parsed (around line 118-122), using the `**Blocks**:` label with the identical comma-splitting logic. Treat the literal `none` as an empty list.

In `ralph/triage.py`:

```python
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
                problems.append(
                    f"{sprint.sprint_id}: Blocks names unknown sprint {claimed!r}"
                )
            elif sprint.sprint_id not in target.depends_on:
                problems.append(
                    f"{sprint.sprint_id}: Blocks claims {claimed}, but {claimed} "
                    f"does not list {sprint.sprint_id} in Depends on"
                )
    return sorted(problems)
```

In `ralph/harness.py`, add `retry_count: int = 0` to `SprintState`, and:

```python
_RETRYABLE_OUTCOMES = frozenset({Outcome.ERROR, Outcome.TIMEOUT, Outcome.INFRA_ERROR})


def _should_retry(sprint_state: SprintState, outcome: Outcome) -> bool:
    """One retry before a failure becomes a block.

    SA-F2 failed once in April with returncode 1 and 135 bytes of output -- a
    transient bail -- and stayed blocked for four months, stranding five
    sprints. A single retry absorbs that class entirely.

    BLOCKED is never retried: an agent writing PHASE_BLOCKED made a judgement,
    and repeating the phase will not change it.
    """
    if outcome not in _RETRYABLE_OUTCOMES:
        return False
    return sprint_state.retry_count < 1
```

Call it in `_mark_terminal_outcome`'s caller: when `_should_retry` is true, increment `sprint_state.retry_count`, log the retry, set status back to `todo`, and let the loop pick it up again rather than marking blocked.

**Retry safety:** before retrying, check whether the phase already produced commits referencing the sprint (the harness already computes this for sentinel cross-validation). If it did, do NOT retry — mark blocked, because the work is partially done and re-running risks duplicating it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/ -v`
Expected: all pass

- [ ] **Step 5: Check the live roadmap for Blocks drift**

Run:
```bash
python -c "from ralph import roadmap_state, triage; print('\n'.join(triage.blocks_disagreements(roadmap_state.parse_sprints())) or 'Blocks consistent')"
```
Record the output in the commit message. Existing drift is expected — this is the first time the field has ever been read.

- [ ] **Step 6: Commit**

```bash
git add ralph/roadmap_state.py ralph/triage.py ralph/harness.py tests/test_ralph/
git commit -m "ralph: one retry before blocking; wire Blocks as a consistency check

SA-F2 failed once in April (returncode 1, 135 bytes of output -- a
transient bail) and stayed blocked four months, stranding five sprints.
One retry absorbs that class. BLOCKED is never retried: that is an
agent's judgement, not a failure. A phase that already committed is not
retried either -- partial work must not be duplicated.

Blocks: was declared on every sprint and parsed by nothing. Now a
cross-check against depends_on, never a second source of truth."
```

---

## Task 8: STATUS.md — visible from a phone

**Files:**
- Create: `ralph/status.py`
- Modify: `ralph/harness.py` (write + commit `STATUS.md` at each sprint boundary)
- Test: `tests/test_ralph/test_status.py`

**Interfaces:**
- Consumes: `triage.QueueState`, `heartbeat.read_heartbeat`, `atomic_write`
- Produces: `render_status(queue: QueueState, beat: dict | None, recent: list[str]) -> str`, `write_status(...) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ralph/test_status.py
"""Tests for STATUS.md rendering.

The bar is: can the operator tell from a beach whether it is working. Ralph
already pushes to origin, so a committed markdown file is readable on GitHub
from a phone with no app, no service, and nothing new to keep running.
"""

from __future__ import annotations

from ralph.status import render_status
from ralph.triage import QueueState


class TestRenderStatus:
    def test_shows_current_sprint_and_phase(self) -> None:
        beat = {"pid": 1, "timestamp": 0.0, "sprint": "SH-2", "phase": "implement"}
        text = render_status(QueueState(total=3, todo=1, eligible=1), beat, [])
        assert "SH-2" in text and "implement" in text

    def test_starvation_is_a_loud_banner(self) -> None:
        state = QueueState(
            total=16, todo=15, eligible=0, blocked_ids=["SA-F2"],
            stranded_by={"SA-F2": ["SA-F3", "SA-F4"]},
        )
        text = render_status(state, None, [])
        assert "STARVED" in text
        assert "SA-F2" in text and "SA-F3" in text

    def test_healthy_queue_has_no_starved_banner(self) -> None:
        text = render_status(QueueState(total=2, todo=1, eligible=1), None, [])
        assert "STARVED" not in text

    def test_missing_heartbeat_is_stated_not_omitted(self) -> None:
        """Silence must not read as health -- an absent heartbeat is a fact
        worth showing, since it is what a dead harness looks like."""
        text = render_status(QueueState(total=1, todo=1, eligible=1), None, [])
        assert "no heartbeat" in text.lower()

    def test_recent_outcomes_are_listed(self) -> None:
        text = render_status(
            QueueState(total=2, todo=0, eligible=0), None, ["SH-2 ok", "SUITE-2 ok"]
        )
        assert "SH-2 ok" in text and "SUITE-2 ok" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_status.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ralph.status'`

- [ ] **Step 3: Write the implementation**

```python
# ralph/status.py
"""Render STATUS.md -- the operator's view while away.

Ralph already pushes to origin, so a committed markdown file is readable on
GitHub from a phone: no app, no service, no port to expose, nothing extra that
can itself fail. The bar is "can the operator tell from a beach whether it is
working", and this clears it.

Everything here is derived from state that already exists. This module adds no
new source of truth, so it cannot disagree with the harness.
"""

from __future__ import annotations

import time
from typing import Optional

from ralph.config import PROJECT_ROOT
from ralph.proc import atomic_write
from ralph.triage import QueueState, starvation_report

STATUS_PATH = PROJECT_ROOT / "STATUS.md"


def render_status(
    queue: QueueState,
    beat: Optional[dict],
    recent: list[str],
    crash_loop: bool = False,
) -> str:
    """Build the STATUS.md body."""
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
        lines.append("- **no heartbeat** — harness is not running, or died without stopping cleanly")
    else:
        age = max(0.0, time.time() - float(beat.get("timestamp", 0.0)))
        sprint = beat.get("sprint") or "(between sprints)"
        phase = beat.get("phase") or "-"
        lines.append(f"- Sprint: **{sprint}**")
        lines.append(f"- Phase: **{phase}**")
        lines.append(f"- Last beat: {age:.0f}s ago")
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

    if recent:
        lines += ["## Recent", ""] + [f"- {r}" for r in recent] + [""]
    return "\n".join(lines)


def write_status(
    queue: QueueState,
    beat: Optional[dict],
    recent: list[str],
    crash_loop: bool = False,
) -> None:
    """Write STATUS.md atomically."""
    atomic_write(STATUS_PATH, render_status(queue, beat, recent, crash_loop))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/test_status.py -v`
Expected: 5 passed

- [ ] **Step 5: Wire into the harness**

In `ralph/harness.py`, after each sprint finalises (next to the existing index-sync call), write and stage `STATUS.md` so it rides along with the bookkeeping commit that already happens:

```python
            try:
                from ralph import heartbeat, status

                sprints_now = roadmap_state.parse_sprints()
                status.write_status(
                    triage.analyse(sprints_now),
                    heartbeat.read_heartbeat(),
                    recent_outcomes[-5:],
                )
            except Exception as e:
                log(f"{picked.sprint_id}: STATUS.md write failed: {e}")
```

Maintain `recent_outcomes: list[str]` in the main loop, appending `f"{sprint_id} {outcome.value}"` per sprint. Add `STATUS.md` to the paths staged by `_commit_harness_bookkeeping`.

- [ ] **Step 6: Commit**

```bash
git add ralph/status.py ralph/harness.py tests/test_ralph/test_status.py
git commit -m "ralph: STATUS.md so progress is visible from a phone

Ralph already pushes to origin, so a committed markdown file is readable
on GitHub with no app, no service, and nothing new that can itself fail.

An absent heartbeat is stated explicitly rather than omitted -- silence
must not read as health, since silence is exactly what a dead harness
produces."
```

---

## Task 9: Supervisor and boot survival

**Files:**
- Create: `ralph/supervisor.py`
- Create: `scripts/install_supervisor_task.ps1`
- Test: `tests/test_ralph/test_supervisor.py`

**Interfaces:**
- Consumes: `heartbeat.seconds_since_beat`, `triage.analyse`, `roadmap_state.parse_sprints`
- Produces: `RestartPolicy` dataclass, `should_restart(...) -> tuple[bool, str]`, `backoff_seconds(consecutive_failures: int) -> float`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ralph/test_supervisor.py
"""Tests for the restart policy.

The supervisor is the only thing with nothing supervising it, so it stays as
dumb as possible: start a process, watch a file, apply a policy, never touch the
repo. Every feature added here is a feature that can fail unwatched.

The policy is tested as pure functions; the process loop around them is
deliberately thin.
"""

from __future__ import annotations

from ralph.supervisor import backoff_seconds, should_restart


class TestBackoff:
    def test_escalates(self) -> None:
        assert backoff_seconds(0) == 30
        assert backoff_seconds(1) == 120
        assert backoff_seconds(2) == 480

    def test_caps_at_final_step(self) -> None:
        assert backoff_seconds(99) == 480


class TestShouldRestart:
    def test_restarts_when_work_remains(self) -> None:
        ok, _ = should_restart(consecutive_failures=0, eligible=3, starved=False)
        assert ok is True

    def test_stops_after_three_consecutive_failures(self) -> None:
        ok, reason = should_restart(consecutive_failures=3, eligible=3, starved=False)
        assert ok is False
        assert "consecutive" in reason.lower()

    def test_stops_when_starved(self) -> None:
        """Restarting into starvation burns a week of API budget achieving
        nothing -- the harness would pick up no sprint and exit, forever."""
        ok, reason = should_restart(consecutive_failures=0, eligible=0, starved=True)
        assert ok is False
        assert "starved" in reason.lower()

    def test_stops_when_all_work_complete(self) -> None:
        ok, reason = should_restart(consecutive_failures=0, eligible=0, starved=False)
        assert ok is False
        assert "complete" in reason.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ralph/test_supervisor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ralph.supervisor'`

- [ ] **Step 3: Write the policy**

```python
# ralph/supervisor.py
"""Restart policy for unattended runs.

Nothing supervises the supervisor, so it is deliberately the dumbest component
in the system: start a process, watch a heartbeat file, apply a bounded policy,
never touch the repo. Every capability added here is one that can fail with
nobody watching.

Bounded is the operative word. A harness that dies instantly and is relaunched
instantly burns a week of API budget in an afternoon, so the backoff and the
hard stop are load-bearing, not politeness.
"""

from __future__ import annotations

_BACKOFF_LADDER = (30.0, 120.0, 480.0)
MAX_CONSECUTIVE_FAILURES = 3
HEARTBEAT_STALE_SECONDS = 600.0


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ralph/test_supervisor.py -v`
Expected: 6 passed

- [ ] **Step 5: Add the process loop**

Append a `main()` to `ralph/supervisor.py` that loops: launch `python -m ralph.harness` as a subprocess; while it runs, poll `heartbeat.seconds_since_beat()` every 30s and kill the tree (via `ralph.proc.run_with_hard_timeout`'s kill helper, or `taskkill /F /T`) if it exceeds `HEARTBEAT_STALE_SECONDS`; on exit, consult `should_restart` using freshly parsed sprints; sleep `backoff_seconds` on failure; write `STATUS.md` with `crash_loop=True` before stopping on the failure cap.

- [ ] **Step 6: Write the Scheduled Task installer**

```powershell
# scripts/install_supervisor_task.ps1
# Registers the ralph supervisor to start at boot, so a power cut resumes work
# without anyone logging in. Run once, elevated.
$action  = New-ScheduledTaskAction -Execute "python" `
    -Argument "-m ralph.supervisor" `
    -WorkingDirectory "C:\Users\matth\PyCharmProjects\SpaceGame"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "RalphSupervisor" -Action $action -Trigger $trigger `
    -Settings $settings -RunLevel Highest -Description "Ralph harness supervisor (Spec E)"
```

- [ ] **Step 7: Commit**

```bash
git add ralph/supervisor.py scripts/install_supervisor_task.ps1 tests/test_ralph/test_supervisor.py
git commit -m "ralph: supervisor with bounded restart policy and boot survival

Nothing supervises the supervisor, so it stays dumb: start a process,
watch a heartbeat, apply a policy, never touch the repo.

Bounded is load-bearing. A harness that dies instantly and relaunches
instantly burns a week of API budget in an afternoon. Stops after 3
consecutive failures, and refuses to restart into a STARVED queue --
where it would pick up nothing and exit, forever."
```

---

## Task 10: Pre-deployment smoke drill

Nothing ships to a seven-day run because the code reads correctly. Every failure mode gets injected and observed.

**Files:**
- Create: `docs/superpowers/plans/2026-08-27-smoke-drill-results.md` (record actual observations)

- [ ] **Step 1: Run each drill and record the result**

| # | Inject | Expected |
|---|---|---|
| 1 | `taskkill /PID <harness>` mid-implement | supervisor relaunches within backoff; sprint reclaimed, no hand repair |
| 2 | `taskkill /F` during a roadmap write | `ROADMAP.md` + `state.json` still parse |
| 3 | Reboot the machine | Scheduled Task starts the supervisor unprompted |
| 4 | Agent subprocess that sleeps past its phase timeout | killed at timeout, phase marked `timeout` |
| 5 | Freeze the heartbeat, leave process alive | detected inside 10 min, restarted |
| 6 | Empty the eligible queue | `STARVED` named with blockers — not "exiting cleanly" |
| 7 | A sprint that fails once | retried once, then blocked |
| 8 | Harness that dies instantly, repeatedly | stops after 3 |
| 9 | Any of the above | `STATUS.md` reflects it on GitHub |

- [ ] **Step 2: Record honestly**

For each drill write what actually happened, not what should have. **A drill that cannot be run means that component is unproven, not assumed working** — say so explicitly.

Drill 4 matters most: the 8.5-hour hang happened because a timeout that *looked* correct never fired, and no amount of reading `subprocess.run(timeout=...)` reveals that. Only hanging something does.

- [ ] **Step 3: Commit the results**

```bash
git add docs/superpowers/plans/2026-08-27-smoke-drill-results.md
git commit -m "docs: smoke drill results for Spec E"
```

---

## Self-review notes

**Spec coverage.** Component 1 (durability) → Tasks 1, 3. Component 2 (liveness) → Tasks 2, 4, 5. Component 3 (supervision) → Task 9. Component 4 (triage) → Tasks 6, 7. Component 5 (observability) → Task 8. Smoke drill → Task 10. Component 6 (queue depth) is deliberately **not** here — it is content work, queued as sprints, and the spec's open question.

**Naming consistency checked.** `atomic_write` (Tasks 1, 3, 5, 8), `run_with_hard_timeout` (Tasks 2, 4), `QueueState`/`analyse`/`starvation_report` (Tasks 6, 8), `should_restart`/`backoff_seconds` (Task 9). `Sprint.blocks` introduced in Task 7 and used only there.

**Known gap, stated deliberately.** Task 9's Step 5 (the supervisor process loop) is prose rather than code. Its behaviour is fully specified by the tested pure functions it calls plus the drill in Task 10, and writing a speculative loop here would be less useful than one written against the real `main()` it has to launch. If the implementer wants it pinned first, that is a reasonable request — say so rather than guessing.
