"""Compliance Scanner A: dialogue-flag string discipline.

SI-1d (see ``requirements/stability_initiative.md``); broadened in
SI-3 Pass 3.4 (2026-04-24).

The bug class this guards against: a flag name exists as a raw string
in two different files; one site writes ``tutorial_bought_X`` while the
other reads ``tutorial_bought_part_X``. Build succeeds, tests pass,
crash fires later in a rarely-exercised path.

The defense: every reference to a flag name whose contract crosses a
module boundary goes through ``spacegame/constants/flags.py``. The
registry is the single source of truth; both setters and readers
import from it. A mismatch becomes impossible.

**Auto-discovered prefixes.** Every non-private, non-``extract_*``
helper in the registry is introspected with a sentinel value to
extract its prefix. Any raw string starting with that prefix, outside
the registry file itself, fails the test.

Currently covers (as of the most recent helper additions):
- ``tutorial_bought_part_`` — tutorial shop purchases
- ``completed_mission_`` — campaign milestone crossings
- ``met_`` — NPC introductions

Scanner tightens as new helpers are added — no per-cluster code here
needs to change. See ``requirements/si3_flag_registry_cookbook.md``.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPACEGAME_ROOT = REPO_ROOT / "spacegame"

# Files that are *allowed* to mention raw registry strings — the registry
# itself and the compliance scanner module.
REGISTRY_FILES = {
    SPACEGAME_ROOT / "constants" / "flags.py",
}


# ---------------------------------------------------------------------------
# Allowlist — raw strings that survive for content-data reasons (JSON
# mirrors, test fixtures mirroring schema, etc.). Format:
# "<rel_path>::<line>: <flag_name>". The goal is an empty set; every
# entry should be justified in a comment right next to it.
# ---------------------------------------------------------------------------
KNOWN_ORPHANS: set[str] = set()


def _discover_registry_patterns() -> list[tuple[str, str, str]]:
    """Return ``[(helper_name, prefix, suffix), ...]`` for every
    parameterized setter helper in the flag registry.

    Runtime-introspective: calls each helper with a string then an int
    sentinel and locates the substitution point in the returned
    string. Captures both the prefix (text before the substitution)
    AND the suffix (text after) so scanners can match the full flag
    pattern, not just the prefix. Without the suffix, helpers that
    sandwich the arg (e.g. ``f"dual_tech_{tech_id}_revealed"``) would
    over-match unrelated strings starting with ``dual_tech_`` (such as
    the ``"dual_tech_moves"`` attribute name).

    Skips ``extract_*`` (extractors) and private names.
    """
    from spacegame.constants import flags

    string_sentinel = "__SI3_FLAG_SENTINEL__"
    int_sentinel = 123456789
    result: list[tuple[str, str, str]] = []

    for name, obj in inspect.getmembers(flags):
        if name.startswith(("_", "extract_")):
            continue
        if not callable(obj):
            continue
        for sentinel in (string_sentinel, int_sentinel):
            try:
                returned = obj(sentinel)
            except Exception:
                continue
            if isinstance(returned, str) and str(sentinel) in returned:
                idx = returned.index(str(sentinel))
                prefix = returned[:idx]
                suffix = returned[idx + len(str(sentinel)):]
                if prefix or suffix:
                    result.append((name, prefix, suffix))
                break
    return result


def _scan_raw_registered_strings() -> list[str]:
    """Return offenders: raw string literals matching a registered
    prefix+suffix pattern, outside the registry and this scanner module.

    Skips comments (full-line). Docstrings and other in-line string
    literals are caught — flagging them is intentional, since a flag
    name in a docstring example can drift from the helper's real
    output and mislead readers.
    """
    patterns = _discover_registry_patterns()
    if not patterns:
        return []
    # One combined alternation: each helper contributes
    # ``['"]<prefix>[a-z0-9_]+<suffix>['"]`` so a match requires the
    # full flag shape, not just the prefix.
    alts: list[str] = []
    for _name, prefix, suffix in patterns:
        alts.append(rf"""['"]{re.escape(prefix)}[a-z0-9_]+{re.escape(suffix)}['"]""")
    pattern = re.compile("|".join(alts))

    offenders: list[str] = []
    for pyfile in SPACEGAME_ROOT.rglob("*.py"):
        if pyfile in REGISTRY_FILES:
            continue
        try:
            source = pyfile.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if not pattern.search(line):
                continue
            rel = pyfile.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel}:{i}: {line.strip()}")
    return offenders


class TestFlagStringDiscipline:
    def test_no_raw_registered_strings_outside_registry(self) -> None:
        """Every flag prefix that has a registry helper must be accessed
        through that helper — raw strings in ``spacegame/`` fail.

        If this test fails, you wrote a raw string like ``"met_arna"`` or
        ``"completed_mission_5"`` in a file other than
        ``spacegame/constants/flags.py``. Replace it with the helper call
        (``met_npc("arna")``, ``campaign_mission_milestone(5)``, etc.).
        """
        offenders = [
            o for o in _scan_raw_registered_strings() if o not in KNOWN_ORPHANS
        ]
        assert not offenders, (
            "Raw flag string matching a registered prefix detected outside "
            "the registry. Use the helper from spacegame.constants.flags "
            "(cookbook: requirements/si3_flag_registry_cookbook.md). "
            "Offenders:\n  " + "\n  ".join(offenders)
        )

    def test_allowlist_not_stale(self) -> None:
        """Every entry in ``KNOWN_ORPHANS`` must still match a live
        raw-string offender. Stops the allowlist from accumulating
        entries for strings that have since been migrated."""
        live = set(_scan_raw_registered_strings())
        stale = KNOWN_ORPHANS - live
        assert not stale, (
            "Stale allowlist entries — the raw strings below are gone. "
            "Remove them from KNOWN_ORPHANS:\n  " + "\n  ".join(sorted(stale))
        )

    def test_registry_exposes_tutorial_helpers(self) -> None:
        """Sanity: the original SI-1 helpers still exist."""
        from spacegame.constants import flags

        assert callable(flags.tutorial_bought_part)
        assert callable(flags.extract_tutorial_bought_part_id)

    def test_helpers_round_trip(self) -> None:
        """Any flag produced by the tutorial setter must be recognized
        by the extractor."""
        from spacegame.constants.flags import (
            extract_tutorial_bought_part_id,
            tutorial_bought_part,
        )

        for part_id in (
            "scrapyard_thruster",
            "scrapyard_reactor",
            "scrapyard_fuel_cell",
            "scrapyard_hold",
            "salvaged_pulse_emitter",
        ):
            flag = tutorial_bought_part(part_id)
            assert extract_tutorial_bought_part_id(flag) == part_id

    def test_non_matching_flag_returns_none(self) -> None:
        from spacegame.constants.flags import extract_tutorial_bought_part_id

        assert extract_tutorial_bought_part_id("some_other_flag") is None
        assert extract_tutorial_bought_part_id("") is None

    def test_discovery_finds_every_parameterized_helper(self) -> None:
        """Self-test: the discovery picks up the known helpers and
        captures both the prefix and the suffix (where present)."""
        discovered = {name: (p, s) for name, p, s in _discover_registry_patterns()}
        assert discovered.get("tutorial_bought_part") == ("tutorial_bought_part_", "")
        assert discovered.get("campaign_mission_milestone") == ("completed_mission_", "")
        assert discovered.get("met_npc") == ("met_", "")
        assert discovered.get("talked_to_npc") == ("talked_to_", "")
        assert discovered.get("encounter_seen") == ("encounter_seen_", "")
        # dual_tech_revealed sandwiches the arg — both ends matter.
        assert discovered.get("dual_tech_revealed") == ("dual_tech_", "_revealed")
