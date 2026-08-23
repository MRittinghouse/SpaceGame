"""Compliance Scanner: import-boundary guard for models and constants.

See ``docs/superpowers/specs/2026-08-23-quality-foundation-design.md``,
"Additional deliverable: import-boundary guard".

WHY THIS BOUNDARY EXISTS
------------------------
``spacegame/models/`` and ``spacegame/constants/`` are intentionally free of
pygame (and pygame_gui) imports. This is the only property that keeps a future
engine port feasible: all game logic and data structures can be extracted and
driven by a different renderer without touching models or constants.

If this boundary breaks, porting the engine requires untangling rendering
primitives (Surfaces, Fonts, Rects, Colors) from business logic — a rewrite,
not a port.

This scanner enforces the boundary mechanically via AST-level import analysis.
It catches every import form:

  import pygame
  import pygame.font
  import pygame as pg
  from pygame import Surface
  from pygame_gui.elements import UIButton
  ... and the equivalent four forms for pygame_gui.

The scanner is intentionally strict:
- No allowlist. One exception is a leak; a "temporary" exception becomes
  permanent. A future sprint that needs to open this boundary must modify
  the scanner explicitly — there is no soft path.
- TYPE_CHECKING-guarded imports are also banned. A ``if TYPE_CHECKING:
  import pygame`` still requires pygame's type stubs during any port and
  defeats the strategic value. Type hints that reference pygame types must
  use string annotations or be moved to the caller side.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPACEGAME_ROOT = REPO_ROOT / "spacegame"

SCAN_ROOTS = [SPACEGAME_ROOT / "models", SPACEGAME_ROOT / "constants"]

BANNED_TOP_LEVEL: set[str] = {"pygame", "pygame_gui"}


# ---------------------------------------------------------------------------
# Core AST helpers
# ---------------------------------------------------------------------------


def _check_ast(tree: ast.Module, source: str) -> list[tuple[int, str]]:
    """Walk an already-parsed AST and return banned import hits.

    Args:
        tree: Parsed AST module.
        source: Original source text (used to reconstruct the offending line).

    Returns:
        List of (lineno, stripped_line_text) for each offending import.
    """
    lines = source.splitlines()
    hits: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in BANNED_TOP_LEVEL:
                    line_text = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                    hits.append((node.lineno, line_text))
                    break  # only one entry per Import node

        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                # relative import — skip
                continue
            top = node.module.split(".")[0]
            if top in BANNED_TOP_LEVEL:
                line_text = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                hits.append((node.lineno, line_text))

    return hits


def _find_pygame_imports(py_path: Path) -> list[tuple[int, str]]:
    """Parse a .py file and return banned pygame/pygame_gui import hits.

    Args:
        py_path: Absolute path to a Python source file.

    Returns:
        List of (lineno, stripped_line_text) for each offending import.
        Empty list if the file cannot be parsed.
    """
    try:
        source = py_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    return _check_ast(tree, source)


def _assert_scan_roots_valid() -> None:
    """Raise AssertionError if any scan root is missing or contains no .py files.

    Raises:
        AssertionError: If a root directory does not exist or is empty.
    """
    for root in SCAN_ROOTS:
        assert root.is_dir(), (
            f"Scan root does not exist: {root}. "
            "If models/ or constants/ was renamed, update SCAN_ROOTS in "
            "tests/test_compliance/test_import_boundaries.py."
        )
        py_files = list(root.rglob("*.py"))
        assert py_files, (
            f"Scan root is empty (no .py files): {root}. "
            "If the directory was emptied or renamed, update SCAN_ROOTS."
        )


def _scan_all_offenders() -> list[str]:
    """Walk all scan roots and return formatted offender lines.

    Returns:
        Sorted list of strings in the format
        ``<repo-relative-path>:<lineno>: <stripped import statement>``.
    """
    offenders: list[str] = []
    for root in SCAN_ROOTS:
        for py_path in sorted(root.rglob("*.py")):
            hits = _find_pygame_imports(py_path)
            for lineno, line_text in hits:
                rel = py_path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel}:{lineno}: {line_text}")
    return sorted(offenders)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImportBoundaries:
    def test_scan_roots_exist_and_non_empty(self) -> None:
        """Each declared scan root must be a non-empty directory.

        Prevents a future rename of ``models/`` or ``constants/`` from
        silently turning this scanner into a vacuous pass.
        """
        _assert_scan_roots_valid()

    def test_no_pygame_imports_in_models_or_constants(self) -> None:
        """No module under ``spacegame/models/`` or ``spacegame/constants/`` may
        import pygame or pygame_gui in any form.

        See the module docstring for the strategic rationale. If this test
        fails, the offending import must be removed or moved to a view/engine
        layer. There is no allowlist — every hit is a violation.
        """
        offenders = _scan_all_offenders()
        assert not offenders, (
            "pygame/pygame_gui import detected in models/ or constants/. "
            "These layers must remain engine-free to keep engine-port "
            "optionality intact. See the module docstring for rationale. "
            "Offenders:\n  " + "\n  ".join(offenders)
        )

    def test_detector_flags_synthetic_violation(self) -> None:
        """Self-test: the AST detector catches all eight banned import forms.

        This is the permanent proof of acceptance criterion 2 — no disk
        pollution required. Each of the four ``import`` forms and four
        ``from ... import`` forms for both ``pygame`` and ``pygame_gui``
        must be flagged.
        """
        synthetic_source = "\n".join(
            [
                "# synthetic violation fixture — not a real module",
                "import pygame",
                "import pygame.font",
                "import pygame as pg",
                "from pygame import Surface",
                "import pygame_gui",
                "import pygame_gui.core",
                "import pygame_gui as pgui",
                "from pygame_gui.elements import UIButton",
            ]
        )
        tree = ast.parse(synthetic_source, filename="<synthetic>")
        hits = _check_ast(tree, synthetic_source)

        found_lines = {line for _, line in hits}
        expected = {
            "import pygame",
            "import pygame.font",
            "import pygame as pg",
            "from pygame import Surface",
            "import pygame_gui",
            "import pygame_gui.core",
            "import pygame_gui as pgui",
            "from pygame_gui.elements import UIButton",
        }
        missing = expected - found_lines
        assert not missing, (
            "Detector failed to flag these banned import forms:\n  "
            + "\n  ".join(sorted(missing))
            + "\nAll eight forms (4 × pygame + 4 × pygame_gui) must be caught."
        )
