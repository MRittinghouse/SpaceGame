"""Compliance Scanner B: module-level untyped content discipline.

SI-1d (see ``requirements/stability_initiative.md``); broadened in
SI-2 Pass 2.4 (2026-04-24).

The bug class this guards against: content declared as a dict-shaped
literal at module scope without a typed schema. Readers index those
dicts with string keys (``item['name']``, ``hint['description']``),
and MyPy cannot catch a typo when the value type is ``Any`` (or when
the declaration is un-annotated at all). The SI origin crashes —
``p['slot_def_id']`` on a dict that keyed ``'part_id'`` — were two
instances of this exact class.

Four shapes covered:

1. ``X: list[dict[...]] = [...]``            (annotated list-of-dict)
2. ``X = [{...}, {...}, ...]``                (un-annotated list-of-dict-literals)
3. ``X: dict[str, dict[...]] = {...}``       (annotated dict-of-dict)
4. ``X = {"k": {...}, "k2": {...}}``         (un-annotated dict-of-dict-literals)

Shape 2 in particular is what let ``TUTORIAL_STEPS`` slip through the
original SI-1d scanner. Shape 3/4 is what let ``MINIGAME_HINTS``
(``dict[str, dict[str, str]]``) slip. Both caught by this broadened
version.

The defense: module-level content tables use ``@dataclass`` (or
``TypedDict``). Attribute access replaces dict indexing and MyPy
catches the typo at import time. See
``requirements/si2_dataclass_migration_cookbook.md`` for the recipe.

This scanner runs in **allowlist mode**: known-old declarations are
catalogued in ``KNOWN_ORPHANS``. New ones outside the allowlist fail
the test. Entries are deleted as each table migrates.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPACEGAME_ROOT = REPO_ROOT / "spacegame"


# ---------------------------------------------------------------------------
# Allowlist — migrated out as SI-2 backfills each table.
#
# Format: set of "<rel_path>::<variable_name>". Keep this list sorted and
# small; the goal is always to drain it. A new entry is added only by a
# deliberate PR that says "acknowledged, migration deferred to SI-2 item
# <X>". Otherwise the expectation is: new content dicts MUST be dataclass
# or TypedDict.
# ---------------------------------------------------------------------------
# SI-1d baseline (2026-04-24, list[dict] only): drained in Pass 2.2.
# SI-2 Pass 2.3: TUTORIAL_STEPS, MINIGAME_HINTS migrated.
# SI-2 Pass 2.4 (this file's broadened scope, 2026-04-24): scanner now
# catches dict-of-dict and un-annotated list/dict-of-dict literals. The
# entries below are the baseline it surfaced on first run — each is a
# candidate for future SI-2 dataclass migration. Drop a line when the
# corresponding table migrates (see
# requirements/si2_dataclass_migration_cookbook.md).
KNOWN_ORPHANS: set[str] = {
    # --- Schema tables (strong migration candidates) ---
    "spacegame/models/attributes.py::ATTRIBUTE_DEFINITIONS",
    "spacegame/models/drone.py::DRONE_TIER_CONFIGS",
    "spacegame/models/ship_build.py::WEIGHT_CLASSES",
    "spacegame/models/ship_build.py::FRAME_VARIANTS",
    "spacegame/models/ship_build.py::FRAME_SLOT_LIMITS",
    "spacegame/models/ship_build.py::_INFRA_MINS",
    "spacegame/models/ground_combat.py::GROUND_ENEMY_TEMPLATES",
    "spacegame/models/ground_contracts.py::_REWARD_RANGES",
    "spacegame/models/ground_mapgen.py::_TIER_PARAMS",
    "spacegame/models/ground_mapgen.py::_DEFAULT_ROOMS",
    "spacegame/models/smuggling.py::_CONTRACT_PARAMS",
    "spacegame/models/encounter.py::_NON_HOSTILE_WEIGHTS",
    # --- Config / tier tables ---
    "spacegame/config.py::_COLORBLIND_PALETTES",
    "spacegame/config.py::DISPOSITION_TIERS",
    # --- Visual profile tables (lower urgency — accessed via fixed-
    # vocabulary keys, lower risk of typo-at-read-site drift) ---
    "spacegame/engine/combat_vfx.py::_ATMOSPHERE",
    "spacegame/engine/mining_vfx.py::_DEPTH_LAYERS",
    "spacegame/engine/refining_vfx.py::_HEAT_LEVELS",
    "spacegame/engine/salvage_vfx.py::_DERELICT_PROFILES",
    "spacegame/engine/ui_chrome.py::_STAMP_PALETTE",
}


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _name_is(node: ast.AST, name: str) -> bool:
    """True if ``node`` is ``ast.Name(id=name)``."""
    return isinstance(node, ast.Name) and node.id == name


def _is_dict_subscript(node: ast.AST) -> bool:
    """True if ``node`` is ``dict[...]`` of any shape, or bare ``dict``."""
    if _name_is(node, "dict"):
        return True
    if isinstance(node, ast.Subscript):
        return _name_is(node.value, "dict")
    return False


def _is_list_of_dict_annotation(node: ast.AST) -> bool:
    """True if annotation is ``list[dict[...]]``."""
    if not isinstance(node, ast.Subscript):
        return False
    if not _name_is(node.value, "list"):
        return False
    return _is_dict_subscript(node.slice)


def _is_dict_of_dict_annotation(node: ast.AST) -> bool:
    """True if annotation is ``dict[str, dict[...]]`` (or bare dict in value)."""
    if not isinstance(node, ast.Subscript):
        return False
    if not _name_is(node.value, "dict"):
        return False
    slice_ = node.slice
    # ``dict[str, dict[...]]`` lowers to Subscript(slice=Tuple(elts=[str, dict[...]]))
    if isinstance(slice_, ast.Tuple) and len(slice_.elts) == 2:
        return _is_dict_subscript(slice_.elts[1])
    return False


def _is_list_of_dict_literals(node: ast.AST) -> bool:
    """True if ``node`` is ``[{...}, {...}, ...]`` with at least one entry."""
    if not isinstance(node, ast.List):
        return False
    if not node.elts:
        return False
    return all(isinstance(e, ast.Dict) for e in node.elts)


def _is_dict_of_dict_literals(node: ast.AST) -> bool:
    """True if ``node`` is ``{"k": {...}, "k2": {...}}`` with dict values."""
    if not isinstance(node, ast.Dict):
        return False
    if not node.values:
        return False
    return all(isinstance(v, ast.Dict) for v in node.values)


def _ann_target_name(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    return None


def _assign_target_name(assign: ast.Assign) -> str | None:
    if len(assign.targets) != 1:
        return None
    return _ann_target_name(assign.targets[0])


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _has_content_literal_value(value: ast.AST | None) -> bool:
    """True if ``value`` is a non-empty list-of-dict-literals or dict-of-dict-literals.

    Guard against flagging empty runtime caches like
    ``_cache: dict[str, dict[...]] = {}`` — the shape is dict-of-dict but
    there's no static content to mistype. Real schema tables have at
    least one entry at declaration time.
    """
    if value is None:
        return False
    return _is_list_of_dict_literals(value) or _is_dict_of_dict_literals(value)


def _scan_module_level_untyped_content() -> list[tuple[str, str, int]]:
    """Return [(rel_path, var_name, line_no), ...] for offenders.

    Walks every module-scope statement in ``spacegame/`` looking for one
    of the four shapes listed in the module docstring. Empty literal
    values (e.g. ``= {}`` runtime caches) are excluded.
    """
    findings: list[tuple[str, str, int]] = []
    for pyfile in SPACEGAME_ROOT.rglob("*.py"):
        try:
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = pyfile.relative_to(REPO_ROOT).as_posix()
        for node in tree.body:
            name: str | None = None
            if isinstance(node, ast.AnnAssign) and node.annotation is not None:
                annotation_matches = _is_list_of_dict_annotation(
                    node.annotation
                ) or _is_dict_of_dict_annotation(node.annotation)
                # Annotated-but-empty declarations are runtime caches, not
                # content — skip them.
                if annotation_matches and _has_content_literal_value(node.value):
                    name = _ann_target_name(node.target)
            elif isinstance(node, ast.Assign):
                if _has_content_literal_value(node.value):
                    name = _assign_target_name(node)
            if name is not None:
                findings.append((rel, name, node.lineno))
    return findings


def _fingerprint(rel_path: str, var_name: str) -> str:
    return f"{rel_path}::{var_name}"


class TestUntypedContentDiscipline:
    def test_no_new_untyped_content_outside_allowlist(self) -> None:
        """Module-level untyped content declarations outside the allowlist fail.

        If this test fails, you declared a new content table as one of:

        * ``X: list[dict[...]] = [...]``
        * ``X = [{...}, {...}]``
        * ``X: dict[str, dict[...]] = {...}``
        * ``X = {"k": {...}, "k2": {...}}``

        Convert it to a ``@dataclass`` (frozen) or a ``TypedDict`` so
        attribute access replaces dict indexing — MyPy then catches
        key-name typos at import time rather than at runtime in a cold
        code path. See ``requirements/si2_dataclass_migration_cookbook.md``.
        """
        findings = _scan_module_level_untyped_content()
        new_offenders = [
            f"{rel}:{line}: {name}"
            for rel, name, line in findings
            if _fingerprint(rel, name) not in KNOWN_ORPHANS
        ]
        assert not new_offenders, (
            "New module-level untyped content declaration(s) detected "
            "outside the SI-1d/2.4 allowlist. Convert to @dataclass or "
            "TypedDict (cookbook: requirements/si2_dataclass_migration_cookbook.md). "
            "Offenders:\n  " + "\n  ".join(new_offenders)
        )

    def test_allowlist_does_not_include_stale_entries(self) -> None:
        """Every entry in the allowlist must still match real code.

        Prevents the allowlist from becoming a forever-free-pass: if a
        table was migrated and someone forgot to delete the allowlist
        entry, this test catches it and forces the cleanup.
        """
        live_fingerprints = {
            _fingerprint(rel, name)
            for rel, name, _line in _scan_module_level_untyped_content()
        }
        stale = KNOWN_ORPHANS - live_fingerprints
        assert not stale, (
            "Stale SI-1d/2.4 allowlist entries — the underlying content "
            "is gone (migrated?). Remove these from KNOWN_ORPHANS:\n  "
            + "\n  ".join(sorted(stale))
        )


# ---------------------------------------------------------------------------
# Self-test: the detection helpers catch each of the four shapes.
# These tests don't depend on production code — they verify the scanner's
# AST pattern matching is working for every shape we claim to cover.
# ---------------------------------------------------------------------------


class TestScannerSelfTest:
    def test_catches_annotated_list_of_dict(self) -> None:
        src = "X: list[dict[str, int]] = [{'a': 1}]"
        tree = ast.parse(src)
        assert _is_list_of_dict_annotation(tree.body[0].annotation)

    def test_catches_annotated_dict_of_dict(self) -> None:
        src = "X: dict[str, dict[str, str]] = {}"
        tree = ast.parse(src)
        assert _is_dict_of_dict_annotation(tree.body[0].annotation)

    def test_catches_unannotated_list_of_dict_literals(self) -> None:
        src = "X = [{'a': 1}, {'b': 2}]"
        tree = ast.parse(src)
        assert _is_list_of_dict_literals(tree.body[0].value)

    def test_catches_unannotated_dict_of_dict_literals(self) -> None:
        src = "X = {'key': {'a': 1}, 'key2': {'b': 2}}"
        tree = ast.parse(src)
        assert _is_dict_of_dict_literals(tree.body[0].value)

    def test_ignores_list_of_non_dict(self) -> None:
        """A list of scalars or tuples shouldn't flag."""
        src = "X = [1, 2, 3]"
        tree = ast.parse(src)
        assert not _is_list_of_dict_literals(tree.body[0].value)

    def test_ignores_dict_of_scalars(self) -> None:
        """A flat string→int dict (e.g. a constants table) shouldn't flag."""
        src = "X = {'a': 1, 'b': 2}"
        tree = ast.parse(src)
        assert not _is_dict_of_dict_literals(tree.body[0].value)

    def test_ignores_empty_list(self) -> None:
        src = "X = []"
        tree = ast.parse(src)
        assert not _is_list_of_dict_literals(tree.body[0].value)

    def test_ignores_empty_dict(self) -> None:
        src = "X = {}"
        tree = ast.parse(src)
        assert not _is_dict_of_dict_literals(tree.body[0].value)
