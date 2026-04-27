"""Catalog test: views that capture WINDOW_WIDTH / WINDOW_HEIGHT at module scope.

Pattern-scan test. Identifies views that bind ``WINDOW_WIDTH`` or
``WINDOW_HEIGHT`` to a module-level name. Such views are incompatible with
runtime resolution changes because Python's ``from X import NAME`` captures
the value at import time, not a live reference.

Today this is not a production bug: the game disallows runtime resolution
changes (settings_view explicitly tells players "Restart required to apply
display changes"). The catalog is informational and blocks nothing — it
is a todo list for any future pass that wants to enable runtime resolution
switching. The findings go to ``requirements/ui_sprint_3a_findings.md``.

If the game ever adds mid-session resolution switching, this list becomes
the refactor target: replace ``from spacegame.config import WINDOW_WIDTH``
with ``from spacegame.config import ...`` + ``config.WINDOW_WIDTH`` at use.

The test FAILS only if the catalog GROWS beyond the known-accepted count.
This lets us hold a snapshot baseline while the code is refactored.
"""

from __future__ import annotations

import re
from pathlib import Path

_VIEWS_DIR = Path(__file__).resolve().parents[2] / "spacegame" / "views"

# Captures like:
#   from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT
#   from spacegame.config import WINDOW_WIDTH
# Does NOT catch: config.WINDOW_WIDTH references (those read live).
_CAPTURE_PATTERN = re.compile(
    r"^from\s+spacegame\.config\s+import\s+[^#\n]*\bWINDOW_(?:WIDTH|HEIGHT)\b",
    re.MULTILINE,
)

# Baseline as of Sprint 3a: how many views currently capture module-level
# WINDOW_WIDTH / WINDOW_HEIGHT. If this number drops, great — update the
# baseline. If it grows, the test fails and the new offender must either
# refactor or update this baseline with a reason.
BASELINE_COUNT = 27


def test_catalog_of_window_dim_captures() -> None:
    """Count views that capture WINDOW_WIDTH / WINDOW_HEIGHT at module scope."""
    offenders: list[str] = []
    for path in sorted(_VIEWS_DIR.glob("*.py")):
        if path.name == "__init__.py" or path.name == "layout.py":
            # layout.py legitimately captures; its constants are the
            # intended indirection for views.
            continue
        text = path.read_text(encoding="utf-8")
        if _CAPTURE_PATTERN.search(text):
            offenders.append(path.name)

    assert len(offenders) <= BASELINE_COUNT, (
        f"Module-level WINDOW_WIDTH/HEIGHT captures increased above "
        f"baseline {BASELINE_COUNT}. Current count: {len(offenders)}.\n"
        f"Offenders:\n  " + "\n  ".join(offenders)
    )


def test_catalog_is_advisory_only() -> None:
    """Sanity: a view using ``config.WINDOW_WIDTH`` at use-time is fine."""
    # This test documents the intended pattern: read the config module
    # attribute at call time, don't import the name at module scope.
    #
    #   GOOD:
    #     import spacegame.config as config
    #     ...
    #     x = config.WINDOW_WIDTH // 2
    #
    #   BAD (stale after runtime resolution change):
    #     from spacegame.config import WINDOW_WIDTH
    #     ...
    #     x = WINDOW_WIDTH // 2
    #
    # No assertion — this test exists so the test body reads like living
    # documentation. Having it here means the pattern guide travels with
    # the catalog.
    assert True
