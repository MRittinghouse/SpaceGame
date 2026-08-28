"""Package-wide isolation of every ralph runtime path.

No test in this package may read or write the *real* files the harness and the
supervisor use at runtime. Autouse, because the failure this prevents is
silent: a test that pollutes a live runtime file leaves no failing assertion
behind, it just makes the operator's evidence wrong.

Two measured incidents motivate it, both introduced by the very fixes that were
meant to make an unattended run legible:

1. ``ralph/logs/supervisor.log``. The harness's own pytest gate runs the whole
   suite once per sprint from the repo root, and the supervisor tests drive
   ``supervisor._log`` for real. One full-suite run appended ~88 lines to the
   live log, including ``stopping: 3 consecutive failures``,
   ``6 consecutive infrastructure failures``, ``all work complete`` and
   ``heartbeat is 700s stale ... killing`` -- byte-identical in shape to real
   supervisor output and carrying live timestamps. ``silent_exit_reason`` sends
   the operator to that exact file by name, so the one on-disk channel the run
   has would have contained mostly fiction, indistinguishable from fact.

2. ``ralph/heartbeat.json``. Tests that drive ``harness.main()`` start a real
   heartbeat thread, which stamped the live beat file with an xdist worker's
   PID. ``status.beat_pid_liveness`` then probes that dead PID and
   ``render_status`` emits ``## NO LIVE HARNESS`` -- a false "the harness is
   not running" banner, committed and pushed to the operator's phone during a
   perfectly healthy run.

Everything else here is the same class of hazard closed pre-emptively:
``ralph/state.json`` (found holding a test sprint id), ``ralph/logs/<sprint>/``
summaries, ``ralph/logs/_agency_probe.log``, ``STATUS.md``,
``ralph/push_state.json``, ``ralph/.running``, ``STOP`` and
``ralph/supervisor_stop.json``.

The redirection is by module attribute, not by environment, because every one
of these paths is bound at import time (``from ralph.config import LOGS_DIR``),
so patching ``ralph.config`` alone would not reach the module-local binding the
code actually reads. Tests that want their own location still win: this fixture
runs first, and a ``monkeypatch.setattr`` in the test body (or in a non-autouse
fixture such as ``isolated_roadmap``) overrides it.

Deliberately NOT redirected: ``PROJECT_ROOT`` and ``ROADMAP_PATH``. The
pre-flight tests must run ``git status`` against the real repository -- that is
the behaviour under test -- and the roadmap is only ever read here.
"""

from __future__ import annotations

import pytest

from ralph import agents as agents_module
from ralph import config as config_module
from ralph import harness as harness_module
from ralph import heartbeat as heartbeat_module
from ralph import status as status_module
from ralph import supervisor as supervisor_module


@pytest.fixture(autouse=True)
def isolate_ralph_runtime_paths(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point every ralph runtime path at a private temp dir for one test.

    Uses ``tmp_path_factory`` rather than ``tmp_path`` on purpose: several
    tests assert over the exact contents of their ``tmp_path`` (``assert
    list(tmp_path.iterdir()) == [target]``), so creating directories in it
    would break them for a reason that has nothing to do with what they test.
    """
    base = tmp_path_factory.mktemp("ralph_isolated")
    logs_dir = base / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir = base / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    # LOGS_DIR is imported by name into three modules; each holds its own
    # binding, so each must be patched.
    for module in (config_module, agents_module, harness_module, supervisor_module):
        monkeypatch.setattr(module, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(supervisor_module, "SUPERVISOR_LOG_PATH", logs_dir / "supervisor.log")
    monkeypatch.setattr(supervisor_module, "HARNESS_LOG_PATH", logs_dir / "harness.log")

    monkeypatch.setattr(heartbeat_module, "HEARTBEAT_PATH", runtime_dir / "heartbeat.json")
    monkeypatch.setattr(status_module, "STATUS_PATH", runtime_dir / "STATUS.md")
    monkeypatch.setattr(status_module, "PUSH_STATE_PATH", runtime_dir / "push_state.json")

    for module in (config_module, harness_module):
        monkeypatch.setattr(module, "STATE_FILE", runtime_dir / "state.json")
        monkeypatch.setattr(module, "LOCK_FILE", runtime_dir / ".running")
        monkeypatch.setattr(module, "STOP_FILE", runtime_dir / "STOP")

    # `main()` refuses to launch when this marker exists, so a test that left
    # one behind would silently turn every later `main()` test into a no-op --
    # the vacuous-test failure mode this branch keeps producing.
    monkeypatch.setattr(
        supervisor_module, "SUPERVISOR_STOP_PATH", runtime_dir / "supervisor_stop.json"
    )
