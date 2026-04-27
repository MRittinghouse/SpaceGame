"""Subprocess-per-resolution bounds test — Sprint 3a follow-up.

For each resolution in the compatibility matrix, spawn a fresh Python
subprocess that:

  1. Sets the game resolution BEFORE any view imports
  2. Imports every registered view factory
  3. Checks that every UIElement rect falls within screen bounds

This is the production-faithful complement to
``test_resolution_smoke.py``. It sidesteps the stale-module-level-capture
issue by giving each resolution a completely fresh Python process with
fresh module imports. The in-process smoke matrix remains useful as a
fast signal during development; this subprocess matrix is the stricter
CI-grade check that matches what a real player sees.

Trade-off: each subprocess incurs ~1-2s startup + data loading, so
this adds ~10-15 seconds of wall time per resolution (60-90s total for
six resolutions, sequentially). pytest-xdist can parallelize across the
six parametrized cases if the machine has cores.

See ``requirements/ui_sprint_3a_findings.md`` for the design rationale
and ``_subprocess_bounds_inner.py`` for the inner implementation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_ui_layout.conftest import RESOLUTIONS

_INNER_MODULE = "tests.test_ui_layout._subprocess_bounds_inner"
_SUBPROCESS_TIMEOUT_SECONDS = 60


def _run_inner(width: int, height: int) -> tuple[int, dict, str]:
    """Invoke the inner subprocess at (width, height). Return (returncode, parsed_json, stderr)."""
    repo_root = Path(__file__).resolve().parents[2]

    env = {
        **_inherited_env(),
        "SPACEGAME_TEST_W": str(width),
        "SPACEGAME_TEST_H": str(height),
        "SDL_VIDEODRIVER": "dummy",
        "PYTHONPATH": str(repo_root),
    }

    proc = subprocess.run(
        [sys.executable, "-m", _INNER_MODULE],
        env=env,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        cwd=str(repo_root),
    )

    # Inner script emits its JSON result after a sentinel so we can
    # parse past any log output produced during data loading.
    sentinel = "===BOUNDS_RESULT_JSON==="
    parsed: dict = {}
    if sentinel in proc.stdout:
        _, _, tail = proc.stdout.partition(sentinel)
        try:
            parsed = json.loads(tail.strip())
        except json.JSONDecodeError as exc:
            parsed = {"_parse_error": str(exc), "_tail": tail[:500]}
    elif proc.stdout.strip():
        parsed = {"_raw_stdout": proc.stdout[:2000]}

    return proc.returncode, parsed, proc.stderr


def _inherited_env() -> dict[str, str]:
    """Pass through essential env vars for the subprocess."""
    import os

    # Keep the basics the child needs to run Python and find resources.
    keys = [
        "PATH",
        "SYSTEMROOT",  # Windows: pygame needs this
        "TEMP",
        "TMP",
        "USERPROFILE",
        "HOMEPATH",
        "HOMEDRIVE",
        "APPDATA",
        "LOCALAPPDATA",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
    ]
    return {k: os.environ[k] for k in keys if k in os.environ}


def _format_violation_report(result: dict) -> str:
    """Human-readable report from the JSON result object."""
    lines: list[str] = []
    res = result.get("resolution", {})
    lines.append(
        f"Resolution {res.get('width')}x{res.get('height')}: "
        f"{len(result.get('violations', []))} violation(s), "
        f"{len(result.get('errors', []))} error(s)"
    )
    for v in result.get("violations", [])[:20]:
        rect = v.get("rect", [0, 0, 0, 0])
        flags = ", ".join(v.get("flags", []))
        lines.append(
            f"  {v['view']}: {v['element_kind']} "
            f"rect=(x={rect[0]}, y={rect[1]}, w={rect[2]}, h={rect[3]}) "
            f"[{flags}]"
        )
    if len(result.get("violations", [])) > 20:
        lines.append(f"  ... and {len(result['violations']) - 20} more")
    for e in result.get("errors", [])[:5]:
        lines.append(f"  ERROR in {e['view']}: {e['error_type']}: {e['error_message']}")
    return "\n".join(lines)


class TestSubprocessBoundsMatrix:
    """Production-faithful bounds check via subprocess per resolution.

    Each parametrized case runs in a fresh Python process so that all view
    module imports resolve WINDOW_WIDTH to the target resolution at import
    time. This matches what a real player sees on startup.
    """

    @pytest.mark.parametrize(
        ("width", "height", "label", "category"),
        RESOLUTIONS,
        ids=[r[2] for r in RESOLUTIONS],
    )
    def test_bounds_at_resolution(self, width: int, height: int, label: str, category: str) -> None:
        returncode, result, stderr = _run_inner(width, height)

        if returncode == 2:
            # Subprocess raised — surface the traceback.
            errors = result.get("errors", [])
            error_report = "\n".join(
                f"{e['view']}: {e['error_type']}: {e['error_message']}" for e in errors[:5]
            )
            pytest.fail(
                f"Subprocess error at {label} ({width}x{height}):\n"
                f"{error_report}\n"
                f"stderr:\n{stderr[:2000]}"
            )

        if returncode == 1:
            # Bounds violations — show them.
            pytest.fail(
                f"Bounds violations at {label} ({width}x{height}):\n"
                f"{_format_violation_report(result)}"
            )

        if returncode != 0:
            pytest.fail(
                f"Unexpected subprocess exit code {returncode} at {label}:\n"
                f"stdout:\n{json.dumps(result, indent=2)[:2000]}\n"
                f"stderr:\n{stderr[:2000]}"
            )

        # returncode == 0: every view passed bounds at this resolution.
        assert result.get("views_tested", 0) > 0, (
            f"Subprocess reported zero views tested at {label}; "
            f"something is wrong with the harness."
        )
