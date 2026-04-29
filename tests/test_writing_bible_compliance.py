"""Sprint 5 — Writing Bible compliance across every UI text surface.

Existing voice tests (``test_tutorial_narrative_voice.py``,
``test_cockpit_hud.py::TestHUDVoiceCompliance``) cover tutorials and the
cockpit HUD. Sprint 5 generalises: scan every UI-surface text source
against the Writing Bible rules.

Text surfaces audited:

  A. **View source literals** — string arguments to ``font.render()`` and
     to pygame_gui element constructors in every file under
     ``spacegame/views/``. These are the buttons, labels, headers, empty
     states, error messages, and tooltips the player actually sees.

  B. **Dialogue content** — every node in every dialogue tree.

  C. **Mission content** — every mission name, description, objective.

  D. **Journal content** — every journal entry title and body.

  E. **Ambient + chatter content** — NPC ambient lines and station chatter.

  F. **News headlines** — ticker templates.

Writing Bible rules enforced (per ``requirements/dialogue_writing_guide.md``):

  - No em-dashes (``—``)
  - No "couldn't help but"
  - No "a testament to"
  - No parallel-negation rhetoric ("no X, no Y")

Violations in well-trafficked surfaces (view source, mission/journal
content) fail the test. Violations in looser-register surfaces (NPC
dialogue, ambient chatter) are reported via xfail so the catalog stays
visible without breaking the suite — voice in faction-character dialogue
follows its own calibration (see ``character_voices.md``).

See ``requirements/ui_sprint_5_findings.md`` for the detailed catalog.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VIEWS_DIR = _REPO_ROOT / "spacegame" / "views"


# ---------------------------------------------------------------------------
# Writing Bible patterns
# ---------------------------------------------------------------------------

# Em-dash unicode code points. Some codebases use the regular "--" too.
_EM_DASH = "\u2014"
_EM_DASHES = {_EM_DASH, "\u2013", " -- "}  # em-dash, en-dash, double-hyphen

_BANNED_PHRASES = [
    "couldn't help but",
    "a testament to",
]

_PARALLEL_NEGATION = re.compile(r"\bno \w+,\s*no \w+", re.IGNORECASE)

# Strings explicitly exempted from parallel-negation enforcement. Each entry
# requires a documented design rationale in a requirements doc. The check is
# whole-string equality after `.strip()`, not substring — exemptions don't
# leak into other content that happens to contain the string.
#
# Note: the current `_PARALLEL_NEGATION` regex requires comma-separated
# parallelism ("no X, no Y"). Period-separated forms ("No X. No Y.") slip
# through today, so listed strings using period parallelism are forward-
# defensive: they won't trip current tests, but if regex coverage tightens
# (or if a future per-surface scanner reads taglines directly), the
# exemption is already in place.
_PARALLEL_NEGATION_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Crimson Reach faction tagline. Exempted per
        # requirements/station_legibility.md (2026-04-26): in-character outlaw
        # bravado, intentional parallelism for atmospheric register. No other
        # taglines or content receive this exemption.
        "No laws. No mercy. No refunds.",
    }
)


def _find_violations(text: str) -> list[str]:
    """Return list of violation descriptions for a single text block."""
    violations: list[str] = []
    for dash in _EM_DASHES:
        if dash in text:
            violations.append(f"em-dash/en-dash ({dash!r})")
            break  # One em-dash report per block is enough.
    lowered = text.lower()
    for phrase in _BANNED_PHRASES:
        if phrase in lowered:
            violations.append(f"banned phrase {phrase!r}")
    if _PARALLEL_NEGATION.search(text) and text.strip() not in _PARALLEL_NEGATION_ALLOWLIST:
        violations.append("parallel-negation rhetoric ('no X, no Y')")
    return violations


# ---------------------------------------------------------------------------
# Text source extraction
# ---------------------------------------------------------------------------


# Matches strings inside UI-surface calls:
#   .render("...")      — font rendering
#   .set_text("...")    — pygame_gui element text updates
#   text="..."          — pygame_gui element construction kwarg
#   _show_message("...") — view-level transient message display
#   _show_feedback("...") — view-level feedback message
#
# ``\s*`` between the call and the quoted string allows multi-line calls
# where the string sits on a new line after the opening paren.
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


def _extract_view_strings() -> list[tuple[str, str]]:
    """Return (file:line, text) for every likely user-facing string in a view."""
    entries: list[tuple[str, str]] = []
    for path in sorted(_VIEWS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for match in _RENDER_STRING.finditer(line):
                literal = match.group(1)
                # Skip format-string templates (they'll be filled in at runtime).
                if literal.startswith("{") or literal.endswith("}"):
                    continue
                # Skip very short strings (single chars, whitespace, symbols).
                if len(literal) < 3:
                    continue
                # Skip strings that are clearly not natural language.
                if _looks_technical(literal):
                    continue
                entries.append((f"{path.name}:{lineno}", literal))
    return entries


def _looks_technical(text: str) -> bool:
    """Heuristic: skip strings that are clearly not natural-language UI copy."""
    # Path-like or identifier-like strings
    if "/" in text or "\\" in text:
        return True
    if text.count("_") >= 2 and " " not in text:  # snake_case identifiers
        return True
    # All caps with no spaces (likely section headers — keep these actually)
    # Keys, placeholders, format strings
    if text.startswith(("#_", "$")):
        return True
    return False


# ---------------------------------------------------------------------------
# JSON content extraction (uses the real DataLoader)
# ---------------------------------------------------------------------------


def _load_dl():
    """Load game data. Cached by DataLoader singleton."""
    from spacegame.data_loader import get_data_loader

    dl = get_data_loader()
    dl.load_all()
    return dl


def _extract_mission_strings() -> list[tuple[str, str]]:
    """Every mission name, description, objective text."""
    dl = _load_dl()
    entries: list[tuple[str, str]] = []
    for m in dl.missions:
        entries.append((f"mission:{m.id}:name", m.name))
        entries.append((f"mission:{m.id}:description", m.description))
        for i, obj in enumerate(m.objectives or []):
            # Objective can be a dict or object; normalize.
            desc = getattr(obj, "description", None)
            if not desc and isinstance(obj, dict):
                desc = obj.get("description")
            if desc:
                entries.append((f"mission:{m.id}:objective_{i}", desc))
    return entries


def _extract_journal_strings() -> list[tuple[str, str]]:
    """Every journal entry text. ``journal_entries`` is a list of
    ``JournalEntry`` records with ``entry_id`` and ``text`` fields."""
    dl = _load_dl()
    entries: list[tuple[str, str]] = []
    for j in dl.journal_entries:
        entries.append((f"journal:{j.entry_id}", j.text))
    return entries


def _extract_dialogue_strings() -> list[tuple[str, str]]:
    """Every dialogue node's text and response text across all trees."""
    dl = _load_dl()
    entries: list[tuple[str, str]] = []
    for dlg_id, dialogue in dl.dialogue_trees.items():
        for node_id, node in dialogue.nodes.items():
            if getattr(node, "text", None):
                entries.append((f"dialogue:{dlg_id}:{node_id}:text", node.text))
            for i, resp in enumerate(getattr(node, "responses", []) or []):
                resp_text = getattr(resp, "text", None)
                if resp_text:
                    entries.append((f"dialogue:{dlg_id}:{node_id}:response_{i}", resp_text))
    return entries


def _extract_interjection_strings() -> list[tuple[str, str]]:
    """CE-5: every authored crew interjection line."""
    dl = _load_dl()
    entries: list[tuple[str, str]] = []
    for entry in dl.crew_interjections:
        for i, line in enumerate(entry.lines):
            entries.append(
                (
                    f"interjection:{entry.crew_id}:{entry.trigger}:{i}",
                    line,
                )
            )
    return entries


def _extract_encounter_strings() -> list[tuple[str, str]]:
    """Every encounter definition's name, description, choice labels,
    choice descriptions, and outcome descriptions (success + failure)."""
    dl = _load_dl()
    entries: list[tuple[str, str]] = []
    for defn in dl.encounter_definitions:
        if defn.name:
            entries.append((f"encounter:{defn.id}:name", defn.name))
        if defn.description:
            entries.append((f"encounter:{defn.id}:description", defn.description))
        for choice in defn.choices:
            entries.append((f"encounter:{defn.id}:choice_{choice.id}:label", choice.label))
            if choice.description:
                entries.append(
                    (
                        f"encounter:{defn.id}:choice_{choice.id}:desc",
                        choice.description,
                    )
                )
            if choice.outcome.description:
                entries.append(
                    (
                        f"encounter:{defn.id}:choice_{choice.id}:outcome",
                        choice.outcome.description,
                    )
                )
            if choice.failure_outcome and choice.failure_outcome.description:
                entries.append(
                    (
                        f"encounter:{defn.id}:choice_{choice.id}:failure_outcome",
                        choice.failure_outcome.description,
                    )
                )
    return entries


def _extract_ambient_strings() -> list[tuple[str, str]]:
    """Station chatter + NPC ambient lines."""
    dl = _load_dl()
    entries: list[tuple[str, str]] = []
    for i, line in enumerate(dl.station_chatter_lines or []):
        text = getattr(line, "text", "")
        if text:
            entries.append((f"chatter:{getattr(line, 'id', i)}", text))
    for i, line in enumerate(dl.ambient_lines or []):
        text = getattr(line, "text", "")
        if text:
            entries.append((f"ambient:{i}", text))
    return entries


# ---------------------------------------------------------------------------
# Tests — view source
# ---------------------------------------------------------------------------


class TestViewSourceWritingBible:
    """UI strings in view source files must comply with the Writing Bible."""

    def test_no_em_dashes_in_view_strings(self) -> None:
        """No em-dashes in rendered text or pygame_gui element text."""
        offenders: list[str] = []
        for loc, text in _extract_view_strings():
            for dash in _EM_DASHES:
                if dash in text:
                    offenders.append(f"{loc}: {text!r}")
                    break
        if offenders:
            report = "\n  ".join(offenders[:30])
            pytest.fail(f"Em-dashes in view-source UI strings (first 30):\n  {report}")

    def test_no_banned_phrases_in_view_strings(self) -> None:
        """No 'couldn't help but' or 'a testament to' in view UI strings."""
        offenders: list[str] = []
        for loc, text in _extract_view_strings():
            lowered = text.lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    offenders.append(f"{loc}: {phrase!r} in {text!r}")
        assert not offenders, "Banned phrases in view UI strings:\n  " + "\n  ".join(offenders)

    def test_no_parallel_negation_in_view_strings(self) -> None:
        """No 'no X, no Y' rhetoric in view UI strings."""
        offenders: list[str] = []
        for loc, text in _extract_view_strings():
            if _PARALLEL_NEGATION.search(text):
                offenders.append(f"{loc}: {text!r}")
        assert not offenders, "Parallel-negation rhetoric in view UI strings:\n  " + "\n  ".join(
            offenders
        )


# ---------------------------------------------------------------------------
# Tests — mission + journal content (core narrative, strict)
# ---------------------------------------------------------------------------


class TestMissionAndJournalWritingBible:
    """Mission and journal content is core narrative and held strict."""

    def test_no_em_dashes_in_missions(self) -> None:
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_mission_strings()
            if any(d in text for d in _EM_DASHES)
        ]
        assert not offenders, "Em-dashes in mission content:\n  " + "\n  ".join(offenders[:20])

    def test_no_em_dashes_in_journal(self) -> None:
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_journal_strings()
            if any(d in text for d in _EM_DASHES)
        ]
        assert not offenders, "Em-dashes in journal content:\n  " + "\n  ".join(offenders[:20])

    def test_no_banned_phrases_in_missions(self) -> None:
        offenders: list[str] = []
        for loc, text in _extract_mission_strings():
            lowered = text.lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    offenders.append(f"{loc}: {phrase!r} in {text[:100]!r}")
        assert not offenders, "Banned phrases in mission content:\n  " + "\n  ".join(offenders[:20])

    def test_no_banned_phrases_in_journal(self) -> None:
        offenders: list[str] = []
        for loc, text in _extract_journal_strings():
            lowered = text.lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    offenders.append(f"{loc}: {phrase!r} in {text[:100]!r}")
        assert not offenders, "Banned phrases in journal content:\n  " + "\n  ".join(offenders[:20])


# ---------------------------------------------------------------------------
# Tests — dialogue + ambient content (looser register, advisory)
# ---------------------------------------------------------------------------


class TestDialogueAndAmbientWritingBible:
    """Dialogue and ambient lines enforce the same Writing Bible rules.

    Sprint 5 cleanup removed the five real offenders (1 dialogue response,
    4 ambient lines) so these tests now hold the line at zero tolerance.
    Future content that introduces em-dashes will fail the test with a
    clear per-offender report.
    """

    def test_no_em_dashes_in_dialogue(self) -> None:
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_dialogue_strings()
            if any(d in text for d in _EM_DASHES)
        ]
        assert not offenders, "Em-dashes in dialogue content:\n  " + "\n  ".join(offenders[:20])

    def test_no_em_dashes_in_ambient(self) -> None:
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_ambient_strings()
            if any(d in text for d in _EM_DASHES)
        ]
        assert not offenders, "Em-dashes in ambient/chatter content:\n  " + "\n  ".join(
            offenders[:20]
        )

    def test_no_banned_phrases_in_ambient(self) -> None:
        offenders: list[str] = []
        for loc, text in _extract_ambient_strings():
            lowered = text.lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    offenders.append(f"{loc}: {phrase!r} in {text[:100]!r}")
        assert not offenders, "Banned phrases in ambient content:\n  " + "\n  ".join(offenders[:20])

    def test_no_parallel_negation_in_ambient(self) -> None:
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_ambient_strings()
            if _PARALLEL_NEGATION.search(text) and text.strip() not in _PARALLEL_NEGATION_ALLOWLIST
        ]
        assert not offenders, "Parallel-negation in ambient content:\n  " + "\n  ".join(
            offenders[:20]
        )

    def test_no_em_dashes_in_encounters(self) -> None:
        """CE-4: encounter content held to the same Writing Bible rules."""
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_encounter_strings()
            if any(d in text for d in _EM_DASHES)
        ]
        assert not offenders, "Em-dashes in encounter content:\n  " + "\n  ".join(offenders[:20])

    def test_no_banned_phrases_in_encounters(self) -> None:
        """CE-4: encounters can't use 'couldn't help but', 'a testament to', etc."""
        offenders: list[str] = []
        for loc, text in _extract_encounter_strings():
            lowered = text.lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    offenders.append(f"{loc}: {phrase!r} in {text[:100]!r}")
        assert not offenders, "Banned phrases in encounter content:\n  " + "\n  ".join(
            offenders[:20]
        )

    def test_no_em_dashes_in_crew_interjections(self) -> None:
        """CE-5: crew interjections held to the same Writing Bible bar."""
        offenders = [
            f"{loc}: {text[:100]!r}"
            for loc, text in _extract_interjection_strings()
            if any(d in text for d in _EM_DASHES)
        ]
        assert not offenders, "Em-dashes in crew interjections:\n  " + "\n  ".join(offenders[:20])

    def test_no_banned_phrases_in_crew_interjections(self) -> None:
        offenders: list[str] = []
        for loc, text in _extract_interjection_strings():
            lowered = text.lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    offenders.append(f"{loc}: {phrase!r} in {text[:100]!r}")
        assert not offenders, "Banned phrases in crew interjections:\n  " + "\n  ".join(
            offenders[:20]
        )


# ---------------------------------------------------------------------------
# Tests — structural invariants + catalog coverage sanity
# ---------------------------------------------------------------------------


class TestCoverageSanity:
    """The scanner extracts the expected volume of content."""

    def test_view_scanner_finds_strings(self) -> None:
        """The view scanner finds a realistic number of UI strings."""
        entries = _extract_view_strings()
        assert len(entries) > 50, (
            f"View scanner found only {len(entries)} strings. Regex may have drifted."
        )

    def test_mission_scanner_finds_content(self) -> None:
        entries = _extract_mission_strings()
        assert len(entries) > 30, f"Mission scanner found only {len(entries)} strings."

    def test_journal_scanner_finds_content(self) -> None:
        entries = _extract_journal_strings()
        assert len(entries) > 10

    def test_dialogue_scanner_finds_content(self) -> None:
        entries = _extract_dialogue_strings()
        assert len(entries) > 50
