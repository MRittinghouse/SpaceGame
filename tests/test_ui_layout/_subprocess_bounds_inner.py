"""Subprocess inner: run bounds checks at a specific resolution.

This module is intentionally NOT a pytest test file (leading underscore
prevents pytest discovery). It is invoked by the parent driver in
``test_subprocess_bounds.py`` as a standalone Python process, one per
resolution in the compatibility matrix.

The child process:

  1. Reads SPACEGAME_TEST_W / SPACEGAME_TEST_H from the environment.
  2. Sets the game resolution BEFORE any view import, so all module-level
     captures of WINDOW_WIDTH / WINDOW_HEIGHT bind to the target value.
     This is the production-faithful part — in production, resolution is
     set at startup and every subsequent import sees the final value.
  3. Imports every registered view factory, drives on_enter, and collects
     pygame_gui element rects.
  4. Asserts that every rect falls within the screen bounds.
  5. Writes a JSON result object to stdout for the parent to parse.

Exit codes:
  0 — every view passed bounds check
  1 — at least one violation found (see JSON output for detail)
  2 — subprocess error (import failure, factory error, etc.)

Design notes:

  - Separate process boundary. No risk of sys.modules pollution affecting
    other tests.
  - No pytest dependency inside the child. Pure Python so the parent can
    trust stdout to be JSON.
  - Stderr is reserved for genuine errors; parent treats stderr content
    as diagnostic.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any


def main() -> int:
    try:
        width = int(os.environ["SPACEGAME_TEST_W"])
        height = int(os.environ["SPACEGAME_TEST_H"])
    except (KeyError, ValueError) as exc:
        print(
            f"ERROR: missing/invalid SPACEGAME_TEST_W or SPACEGAME_TEST_H: {exc}", file=sys.stderr
        )
        return 2

    # Headless SDL must be set before pygame imports anywhere.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    # CRITICAL ORDER: set resolution before any view module imports. This
    # is what makes the subprocess production-faithful. Every view's
    # module-level ``from spacegame.config import WINDOW_WIDTH`` resolves
    # to the target resolution because no views have been imported yet.
    import spacegame.config as config

    config.set_resolution(width, height)

    import pygame

    pygame.init()
    pygame.display.set_mode((width, height))

    # Now safe to import the harness and view factories.
    from tests.test_scenarios._view_harness import (
        VIEW_FACTORIES,
        fresh_ui_manager,
    )

    violations: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for view_name, factory in sorted(VIEW_FACTORIES.items()):
        try:
            ui = fresh_ui_manager()
            view = factory(ui)
            view.on_enter()

            # Collect every UIElement rect.
            root = ui.get_root_container()
            for elem in root.elements:
                rect = getattr(elem, "rect", None)
                if rect is None:
                    continue
                kind = type(elem).__name__
                r = pygame.Rect(rect)
                v_flags: list[str] = []
                if r.left < 0:
                    v_flags.append(f"left={r.left} (< 0)")
                if r.top < 0:
                    v_flags.append(f"top={r.top} (< 0)")
                if r.right > width:
                    v_flags.append(f"right={r.right} (> {width})")
                if r.bottom > height:
                    v_flags.append(f"bottom={r.bottom} (> {height})")
                if v_flags:
                    violations.append(
                        {
                            "view": view_name,
                            "element_kind": kind,
                            "rect": [r.left, r.top, r.width, r.height],
                            "flags": v_flags,
                        }
                    )

            view.on_exit()
        except Exception as exc:
            errors.append(
                {
                    "view": view_name,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

    result = {
        "resolution": {"width": width, "height": height},
        "views_tested": len(VIEW_FACTORIES),
        "violations": violations,
        "errors": errors,
    }

    # Emit JSON after a sentinel so the parent can parse past any log
    # output produced during data loading or view construction.
    print("===BOUNDS_RESULT_JSON===")
    print(json.dumps(result, indent=2))

    if errors:
        return 2
    if violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
