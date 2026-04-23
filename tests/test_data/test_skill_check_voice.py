"""NV-5: compliance tests for skill-gated dialogue response voice.

Gates every skill-gated response against the Grading Rubric established
in ``requirements/dialogue_writing_guide.md`` section 8. Any violation
here is a rewrite task for the authoring pass that introduced it, not a
false positive to add to an allowlist.

Categories scanned:
  1. Responses with a ``skill_check`` field.
  2. Responses whose text starts with a known-skill bracket prefix
     ``[Persuasion]`` / ``[Persuasion 2]`` / ``[Observation]`` etc.
     even when no ``skill_check`` is attached (knowledge-flag-gated
     responses are the canonical case).

Enforces:
  - Structure: every scanned response starts with a valid bracket prefix.
  - Skill name in prefix is a registered ``skill_check`` skill.
  - When a ``skill_check`` is attached, the prefix skill MUST match
    ``skill_check.skill``.
  - When a ``skill_check`` is attached, the prefix difficulty MUST be
    present and MUST equal ``skill_check.difficulty``.
  - Body (text after the bracket) is not a bare declarative like
    "Yes.", "I disagree.", "OK." — grade-D violations.
  - Body is at least ``MIN_BODY_WORDS`` words long. Below that floor
    the response is by definition not carrying insight.

Failure diagnostics name the dialogue_id, node_id, response_index, the
current text, and the specific rule violated — authors should be able
to fix every violation without reading the test source.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DIALOGUES_PATH = PROJECT_ROOT / "data" / "dialogue" / "dialogues.json"

# Registered skill_check skills as of NV-6.5. Keep in sync with
# ``spacegame.models.social.SOCIAL_SKILL_DEFINITIONS``.
VALID_SKILLS = {
    "persuasion",
    "intimidation",
    "observation",
    "deception",
    "technical",
    "piloting",
    "leadership",
}

# Grade-D bare declaratives — single-clause acknowledgments that carry no
# skill-derived insight. Match against the stripped, lowercased body.
BARE_DECLARATIVES = {
    "yes.",
    "no.",
    "sure.",
    "ok.",
    "okay.",
    "fine.",
    "right.",
    "correct.",
    "agreed.",
    "understood.",
    "got it.",
    "i see.",
    "i agree.",
    "i disagree.",
    "i know.",
    "yeah.",
    "nope.",
}

# Minimum body word count. Tight enough to catch D-grade acknowledgments,
# loose enough to allow sharp 6-word reads when they earn it.
MIN_BODY_WORDS = 6

# Matches `[Skill]` or `[Skill N]` at the very start of a response.
# Group 1: skill name (word chars only). Group 2: optional difficulty digits.
# Group 3: remaining body text.
_BRACKET_RE = re.compile(r"^\[(\w+)(?:\s+(\d+))?\]\s*(.*)$", re.DOTALL)


# ---------------------------------------------------------------------------
# Data load + iteration
# ---------------------------------------------------------------------------


@dataclass
class _Scanned:
    """One response that needs voice compliance."""

    dialogue_id: str
    node_id: str
    response_index: int
    text: str
    skill_check: Optional[dict]  # raw dict from JSON or None
    prefix_skill: Optional[str]  # lowercase; None if no bracket match
    prefix_difficulty: Optional[int]  # None if no number in bracket
    body: str  # text after the bracket (may be empty if prefix-only)


def _load_dialogues() -> dict:
    with open(DIALOGUES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_prefix(text: str) -> tuple[Optional[str], Optional[int], str]:
    """Extract (skill, difficulty, body) from a text starting with ``[...]``.

    Returns (None, None, text) if the text doesn't begin with a bracket
    pattern or the bracket doesn't name a registered skill.
    """
    match = _BRACKET_RE.match(text)
    if not match:
        return None, None, text
    raw_skill = match.group(1).lower()
    if raw_skill not in VALID_SKILLS:
        # Not a skill prefix — could be an action-tag like [Stay silent.]
        # or a future skill that isn't yet registered. Don't claim it.
        return None, None, text
    difficulty = int(match.group(2)) if match.group(2) else None
    body = match.group(3).strip()
    return raw_skill, difficulty, body


def _iter_scanned() -> Iterator[_Scanned]:
    """Yield every dialogue response that must be voice-checked."""
    data = _load_dialogues()
    for tree in data.get("dialogues", []):
        tid = tree["id"]
        for node in tree.get("nodes", []):
            nid = node["id"]
            for idx, resp in enumerate(node.get("responses", [])):
                text = resp.get("text", "") or ""
                skill_check = resp.get("skill_check")
                prefix_skill, prefix_diff, body = _parse_prefix(text)
                if skill_check is None and prefix_skill is None:
                    continue  # Not skill-gated — ignore.
                yield _Scanned(
                    dialogue_id=tid,
                    node_id=nid,
                    response_index=idx,
                    text=text,
                    skill_check=skill_check,
                    prefix_skill=prefix_skill,
                    prefix_difficulty=prefix_diff,
                    body=body,
                )


def _loc(s: _Scanned) -> str:
    """Human-readable location header for diagnostic lines."""
    return f"{s.dialogue_id}::{s.node_id}[{s.response_index}]"


# ---------------------------------------------------------------------------
# Compliance tests
# ---------------------------------------------------------------------------


class TestSkillCheckStructure:
    """Every scanned response must open with a recognized bracket prefix."""

    def test_bracket_prefix_required_when_skill_check_present(self) -> None:
        violations: list[str] = []
        for s in _iter_scanned():
            if s.skill_check is not None and s.prefix_skill is None:
                violations.append(
                    f"  {_loc(s)} — has skill_check but text doesn't start "
                    f"with [Skill N] prefix: {s.text!r}"
                )
        assert not violations, (
            f"{len(violations)} response(s) with skill_check missing the "
            "canonical [Skill N] prefix (see dialogue_writing_guide.md §8 "
            "'Canonical Format'):\n" + "\n".join(violations)
        )

    def test_bracket_skill_is_registered(self) -> None:
        """Bracket prefix skill name must be a registered skill_check skill."""
        violations: list[str] = []
        for s in _iter_scanned():
            if s.prefix_skill is not None and s.prefix_skill not in VALID_SKILLS:
                violations.append(
                    f"  {_loc(s)} — unknown skill {s.prefix_skill!r}. "
                    f"Valid: {sorted(VALID_SKILLS)}. Text: {s.text!r}"
                )
        assert not violations, (
            f"{len(violations)} response(s) reference unregistered skill "
            "names:\n" + "\n".join(violations)
        )


class TestSkillCheckConsistency:
    """When a skill_check is attached, the prefix must agree with it."""

    def test_prefix_skill_matches_skill_check_skill(self) -> None:
        violations: list[str] = []
        for s in _iter_scanned():
            if s.skill_check is None or s.prefix_skill is None:
                continue
            sc_skill = str(s.skill_check.get("skill", "")).lower()
            if sc_skill and s.prefix_skill != sc_skill:
                violations.append(
                    f"  {_loc(s)} — prefix says [{s.prefix_skill.title()}] "
                    f"but skill_check.skill is {sc_skill!r}. Text: {s.text!r}"
                )
        assert not violations, (
            f"{len(violations)} response(s) with prefix/skill_check skill "
            "mismatch:\n" + "\n".join(violations)
        )

    def test_prefix_difficulty_required_when_skill_check_present(self) -> None:
        """Canonical format: skill_check → prefix must include difficulty N."""
        violations: list[str] = []
        for s in _iter_scanned():
            if s.skill_check is None or s.prefix_skill is None:
                continue
            if s.skill_check.get("difficulty") is not None and s.prefix_difficulty is None:
                expected = s.skill_check["difficulty"]
                violations.append(
                    f"  {_loc(s)} — skill_check has difficulty={expected} "
                    f"but prefix is [{s.prefix_skill.title()}] with no number. "
                    f"Update to [{s.prefix_skill.title()} {expected}]. "
                    f"Text: {s.text!r}"
                )
        assert not violations, (
            f"{len(violations)} response(s) missing difficulty in prefix "
            "(see dialogue_writing_guide.md §8 'Canonical Format'):\n"
            + "\n".join(violations)
        )

    def test_prefix_difficulty_matches_skill_check_difficulty(self) -> None:
        violations: list[str] = []
        for s in _iter_scanned():
            if s.skill_check is None or s.prefix_difficulty is None:
                continue
            expected = s.skill_check.get("difficulty")
            if expected is not None and s.prefix_difficulty != expected:
                violations.append(
                    f"  {_loc(s)} — prefix difficulty {s.prefix_difficulty} "
                    f"!= skill_check.difficulty {expected}. Text: {s.text!r}"
                )
        assert not violations, (
            f"{len(violations)} response(s) with prefix/skill_check "
            "difficulty mismatch:\n" + "\n".join(violations)
        )


class TestSkillCheckVoice:
    """Body content must carry insight — not bare acknowledgments."""

    def test_no_bare_declarative_body(self) -> None:
        """Grade-D: the body after the bracket must not be a one-clause
        acknowledgment like 'Yes.' or 'I disagree.'"""
        violations: list[str] = []
        for s in _iter_scanned():
            if s.prefix_skill is None:
                continue  # Only evaluate bracket-prefixed responses
            body_lc = s.body.lower().strip().strip('"')
            if body_lc in BARE_DECLARATIVES:
                violations.append(
                    f"  {_loc(s)} — bare declarative body {s.body!r}. "
                    "Rewrite per §8 rubric: skill should produce insight, "
                    "not acknowledgment."
                )
        assert not violations, (
            f"{len(violations)} grade-D bare-declarative violation(s):\n"
            + "\n".join(violations)
        )

    def test_body_meets_minimum_word_count(self) -> None:
        """Body must be at least ``MIN_BODY_WORDS`` words. Below that floor,
        the response can't carry a skill-derived read."""
        violations: list[str] = []
        for s in _iter_scanned():
            if s.prefix_skill is None:
                continue
            body = s.body.strip('"').strip()
            word_count = len([w for w in body.split() if w.strip()])
            if word_count < MIN_BODY_WORDS:
                violations.append(
                    f"  {_loc(s)} — body is {word_count} words (min "
                    f"{MIN_BODY_WORDS}). Text: {s.text!r}"
                )
        assert not violations, (
            f"{len(violations)} response(s) below minimum body length:\n"
            + "\n".join(violations)
        )


class TestScannerSelfCheck:
    """Sanity checks on the scanner itself — catches regressions in the
    test infrastructure rather than in content."""

    def test_scanner_finds_known_skill_gated_responses(self) -> None:
        """At least the known explicit skill checks are detected."""
        scanned = list(_iter_scanned())
        assert len(scanned) >= 9, (
            f"Scanner found only {len(scanned)} skill-gated responses; "
            "expected at least 9 from the NV-1 audit baseline. Scanner "
            "pattern may be broken."
        )

    def test_every_scanned_response_has_nonempty_text(self) -> None:
        """Data-integrity sanity."""
        for s in _iter_scanned():
            assert s.text.strip(), (
                f"{_loc(s)} has empty text — data corruption?"
            )
