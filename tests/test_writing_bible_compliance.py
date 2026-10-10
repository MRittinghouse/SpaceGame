"""The Writing Bible, enforced on every text surface (writing discipline spec 5.1).

Two layers:

  A. The prose gates G1 to G11 and G13 (``tests/writing_gates``) run over every player-facing
     string in ``data/``, and the gates whose scope is every string also over the strings built
     in code under ``spacegame/views`` and ``spacegame/models``: dashes, paired negation,
     tells, names, the captain's pronoun and address and tokens, filter verbs, body tells,
     feelings and motives, option tags, "the player", the lexicon, and dialogue structure.
     Each gate starts from a baseline allowlist of the offences shipped when the gates landed
     (``tests/writing_gates/allowlist.json``), keyed by gate, rule, file and path (a JSON path,
     or a code string's scope and text), each with a reason. A new offence fails, and a row
     whose string no longer offends fails too, so the list only shrinks. Every surface fails
     against the allowlist alike: dialogue and ambient lines get no softer treatment.

  B. Two older checks on strings in code stay below: view source literals and the station
     taglines are checked for dashes, the banned phrases, and paired negation (the spec's G2
     regex), with the Crimson Reach tagline exempt by name.

The gates' rules are pinned on synthetic strings in
``tests/test_compliance/test_writing_gates_engine.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.writing_gates import allowlist
from tests.writing_gates.rules import G2_PAIRED_NEGATION, GATES, Offence, offences

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VIEWS_DIR = _REPO_ROOT / "spacegame" / "views"

# ---------------------------------------------------------------------------
# Writing Bible patterns for strings in code
# ---------------------------------------------------------------------------

_EM_DASH = "\N{EM DASH}"
_EM_DASHES = {_EM_DASH, "\N{EN DASH}", " -- "}

_BANNED_PHRASES = [
    "couldn't help but",
    "a testament to",
    # AI register markers (see requirements/aurelia_voice_examples.md diagnostic #4).
    "remarkable",
    "wonderful",
]

# Strings exempted from the banned-phrase check, each with a documented rationale. Whole-string
# equality after `.strip().lower()`, not substring, so exemptions do not leak.
_BANNED_PHRASES_ALLOWLIST: frozenset[str] = frozenset()

# The spec's G2 regex: one rule for data and code.
_PARALLEL_NEGATION = G2_PAIRED_NEGATION

# Strings exempted from paired-negation enforcement, by whole-string equality after `.strip()`.
_PARALLEL_NEGATION_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Crimson Reach faction tagline, exempted per requirements/station_legibility.md
        # (2026-04-26): in-character outlaw bravado. No other tagline is exempt.
        "No laws. No mercy. No refunds.",
    }
)


def _find_violations(text: str) -> list[str]:
    """Return a description of every violation in one block of text."""
    violations: list[str] = []
    for dash in _EM_DASHES:
        if dash in text:
            violations.append(f"em-dash/en-dash ({dash!r})")
            break
    lowered = text.lower()
    if lowered.strip() not in _BANNED_PHRASES_ALLOWLIST:
        for phrase in _BANNED_PHRASES:
            if phrase in lowered:
                violations.append(f"banned phrase {phrase!r}")
    if _PARALLEL_NEGATION.search(text) and text.strip() not in _PARALLEL_NEGATION_ALLOWLIST:
        violations.append("parallel-negation rhetoric")
    return violations


class TestParallelNegationRegex:
    """The spec's G2 regex across every separator form (spec 5.1, G2: keep these self-tests)."""

    def test_matches_comma_form(self) -> None:
        assert _PARALLEL_NEGATION.search("No laws, no mercy.")

    def test_matches_period_form(self) -> None:
        assert _PARALLEL_NEGATION.search("No beacon. No transponder.")

    def test_matches_em_dash_form(self) -> None:
        assert _PARALLEL_NEGATION.search("No middlemen \N{EM DASH} no fees.")

    def test_matches_en_dash_form(self) -> None:
        assert _PARALLEL_NEGATION.search("No signal \N{EN DASH} no response.")

    def test_matches_double_hyphen_form(self) -> None:
        assert _PARALLEL_NEGATION.search("No power -- no heat.")

    def test_matches_two_word_form(self) -> None:
        """The spec's regex allows a second word after the first "no"."""
        assert _PARALLEL_NEGATION.search("No mapped systems, no trade routes.")

    def test_does_not_match_unrelated_no_clauses(self) -> None:
        text = "There is no captain. The ship has no crew problems."
        assert not _PARALLEL_NEGATION.search(text)


# ---------------------------------------------------------------------------
# Strings in code: view source literals and station taglines
# ---------------------------------------------------------------------------

# Strings inside UI-surface calls: .render("..."), .set_text("..."), text="...",
# _show_message("..."), _show_feedback("..."). ``\s*`` lets the string sit on the next line.
_RENDER_STRING = re.compile(
    r"""(?:
        \.render\(
        | \.set_text\(
        | \btext\s*=\s*
        | _show_message\(
        | _show_feedback\(
    )
    \s*
    ["']([^"'\n]+)["']""",
    re.VERBOSE,
)


def _looks_technical(text: str) -> bool:
    """Heuristic: skip strings that are clearly not natural-language UI copy."""
    if "/" in text or "\\" in text:
        return True
    if text.count("_") >= 2 and " " not in text:
        return True
    return text.startswith(("#_", "$"))


def _extract_view_strings() -> list[tuple[str, str]]:
    """Return (file:line, text) for every likely user-facing string in a view."""
    entries: list[tuple[str, str]] = []
    for path in sorted(_VIEWS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for match in _RENDER_STRING.finditer(line):
                literal = match.group(1)
                if literal.startswith("{") or literal.endswith("}"):
                    continue
                if len(literal) < 3 or _looks_technical(literal):
                    continue
                entries.append((f"{path.name}:{lineno}", literal))
    return entries


def _extract_tagline_strings() -> list[tuple[str, str]]:
    """Return (loc, tagline) for every non-empty faction_tagline on a StationLayout subclass."""
    import spacegame.views.station_layouts as _sl

    entries: list[tuple[str, str]] = []
    for cls in _sl.StationLayout.__subclasses__():
        tagline: str = getattr(cls, "faction_tagline", "")
        if tagline.strip():
            entries.append((f"tagline:{cls.__name__}", tagline))
    return entries


class TestViewSourceWritingBible:
    """UI strings in view source files comply with the Writing Bible."""

    def test_view_scanner_finds_strings(self) -> None:
        entries = _extract_view_strings()
        assert len(entries) > 50, f"View scanner found only {len(entries)} strings."

    def test_no_em_dashes_in_view_strings(self) -> None:
        offenders = [
            f"{loc}: {text!r}"
            for loc, text in _extract_view_strings()
            if any(dash in text for dash in _EM_DASHES)
        ]
        assert not offenders, "Dashes in view UI strings:\n  " + "\n  ".join(offenders[:30])

    def test_no_banned_phrases_in_view_strings(self) -> None:
        offenders = [
            f"{loc}: {phrase!r} in {text!r}"
            for loc, text in _extract_view_strings()
            for phrase in _BANNED_PHRASES
            if phrase in text.lower()
        ]
        assert not offenders, "Banned phrases in view UI strings:\n  " + "\n  ".join(offenders)

    def test_no_parallel_negation_in_view_strings(self) -> None:
        offenders = [
            f"{loc}: {text!r}"
            for loc, text in _extract_view_strings()
            if _PARALLEL_NEGATION.search(text)
        ]
        assert not offenders, "Paired negation in view UI strings:\n  " + "\n  ".join(offenders)


class TestStationTaglineWritingBible:
    """Station faction taglines comply with the Writing Bible."""

    def test_tagline_scanner_finds_content(self) -> None:
        assert len(_extract_tagline_strings()) >= 5

    def test_taglines_comply(self) -> None:
        offenders = [
            f"{loc}: {text!r}: {_find_violations(text)}"
            for loc, text in _extract_tagline_strings()
            if _find_violations(text)
        ]
        assert not offenders, "Writing Bible violations in taglines:\n  " + "\n  ".join(offenders)

    def test_allowlist_suppresses_reach_tagline(self) -> None:
        """The regex matches the Reach tagline; the allowlist suppresses it, and only it."""
        reach_tagline = "No laws. No mercy. No refunds."
        assert _PARALLEL_NEGATION.search(reach_tagline)
        assert not [v for v in _find_violations(reach_tagline) if "parallel-negation" in v]
        assert [v for v in _find_violations("No power. No heat.") if "parallel-negation" in v]


# ---------------------------------------------------------------------------
# The prose gates over data/ and the strings built in code (spec 5.1)
# ---------------------------------------------------------------------------

GATE_IDS = sorted(GATES, key=lambda gate: int(gate[1:]))


@pytest.fixture(scope="module")
def live() -> dict[str, list[Offence]]:
    """Today's offences, gate by gate, computed once for the module."""
    return {gate: offences(gate) for gate in GATE_IDS}


def _rows_of(gate: str) -> tuple[allowlist.Row, ...]:
    return tuple(row for row in allowlist.rows() if row.gate == gate)


class TestProseGates:
    @pytest.mark.parametrize("gate", GATE_IDS)
    def test_no_new_offence(self, gate: str, live: dict[str, list[Offence]]) -> None:
        """Every offence of the gate has its allowlist row; a new one names its string."""
        new = allowlist.unlisted(live[gate], _rows_of(gate))
        report = "\n  ".join(
            f"{o.rule} | {o.file} {o.path} | {o.match!r} in {o.text[:140]!r}" for o in new[:40]
        )
        assert not new, (
            f"{gate}: {len(new)} new offences. Rewrite the line (spec 5.1); the baseline "
            f"allowlist only shrinks:\n  {report}"
        )

    @pytest.mark.parametrize("gate", GATE_IDS)
    def test_every_allowlist_row_still_offends(
        self, gate: str, live: dict[str, list[Offence]]
    ) -> None:
        """A row whose line was fixed fails until it leaves the list."""
        gone = allowlist.stale(_rows_of(gate), live[gate])
        report = "\n  ".join(f"{r.rule} | {r.file} {r.path}" for r in gone[:40])
        assert not gone, (
            f"{gate}: {len(gone)} allowlist rows no longer offend. Delete them "
            f"(python -m tests.writing_gates.allowlist --prune):\n  {report}"
        )


class TestTheAllowlist:
    def test_every_row_names_a_known_gate_a_rule_and_a_reason(self) -> None:
        for row in allowlist.rows():
            assert row.gate in GATES, row
            assert row.rule and row.path and row.reason.strip(), row

    def test_rows_are_unique(self) -> None:
        keys = [row.key for row in allowlist.rows()]
        assert len(keys) == len(set(keys))

    def test_a_fixed_line_is_reported_stale_and_a_new_one_unlisted(self) -> None:
        """The shrink rule itself, on a synthetic row and offence."""
        row = allowlist.Row("G2", "paired negation", "data/x.json", ".a", "old line", "test")
        offence = Offence("G2", "paired negation", "data/x.json", ".b", "new line", "new line")
        assert allowlist.stale((row,), [offence]) == [row]
        assert allowlist.unlisted([offence], (row,)) == [offence]
        assert allowlist.stale((row,), [Offence(*row.key, "old line", "old line")]) == []

    def test_every_offence_has_a_baseline_reason(self, live: dict[str, list[Offence]]) -> None:
        for found in live.values():
            for offence in found:
                assert allowlist.reason_for(offence)
