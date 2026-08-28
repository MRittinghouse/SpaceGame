"""Compliance guard for the lens authoring guide.

Fails the build if:
  (a) any of the sixteen canonical lens_id tokens is missing from
      requirements/lens_authoring_guide.md
  (b) any banned NPC name appears as a whole word in the guide
  (c) any em-dash (U+2014) appears anywhere in the guide

Additionally, when DataLoader().lenses is non-empty (A2-5/A2-6 have landed and
populated the registry), asserts every registered lens_id is covered by the
guide, catching drift the day the registry populates.

Skips cleanly if the guide file does not yet exist.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

GUIDE_PATH = Path(__file__).parents[2] / "requirements" / "lens_authoring_guide.md"

# Canonical sixteen lens_ids from Spec F "The sixteen lenses" table.
# Source: docs/superpowers/specs/2026-08-27-act-two-ambition-design.md
# and the "Conventions this file assumes from A2-1 through A2-4" block in ROADMAP.md.
# Hardcoded here per the locked decision: gate the guide the day it lands,
# rather than waiting for A2-5/A2-6 to populate the registry.
CANONICAL_LENS_IDS: frozenset[str] = frozenset(
    {
        "vengeance",
        "wealth",
        "political_power",
        "exploration",
        "discovery",
        "justice",
        "crime",
        "revolution",
        "empire",
        "community",
        "legacy",
        "faith",
        "transcendence",
        "connection",
        "truth",
        "preservation",
    }
)

BANNED_NPC_NAMES: frozenset[str] = frozenset(
    {
        "Yara",
        "Elara",
        "Kael",
        "Mara",
        "Lydia",
        "Clive",
        "Magnus",
        "Ambrose",
    }
)

# U+2014 is the Unicode em-dash. Double-hyphens (--) are the permitted substitute
# in prose; the em-dash literal is banned in player-facing content and must not
# creep into the guide's sample lines.
EM_DASH = "—"


def _guide_text() -> str:
    """Read and return the guide file, or skip if it does not exist."""
    if not GUIDE_PATH.exists():
        pytest.skip(f"Lens authoring guide not yet written ({GUIDE_PATH})")
    return GUIDE_PATH.read_text(encoding="utf-8")


class TestLensAuthoringGuidePresence:
    def test_all_sixteen_lens_ids_covered(self) -> None:
        """Every canonical lens_id must appear in the guide."""
        text = _guide_text()
        missing = sorted(lid for lid in CANONICAL_LENS_IDS if lid not in text)
        assert not missing, (
            f"Lens authoring guide is missing coverage for: {missing!r}. "
            "Each of the sixteen canonical lens_ids must appear in the guide."
        )

    def test_no_banned_npc_names(self) -> None:
        """Banned NPC names must not appear as whole words in the guide."""
        text = _guide_text()
        found = sorted(
            name for name in BANNED_NPC_NAMES if re.search(rf"\b{re.escape(name)}\b", text)
        )
        assert not found, (
            f"Banned NPC name(s) found in lens authoring guide: {found!r}. "
            f"These names are AI-overused and must not appear. "
            f"Banned set: {sorted(BANNED_NPC_NAMES)!r}"
        )

    def test_no_em_dash(self) -> None:
        """No Unicode em-dash (U+2014) may appear in the guide."""
        text = _guide_text()
        offending_lines = [i + 1 for i, line in enumerate(text.splitlines()) if EM_DASH in line]
        assert not offending_lines, (
            f"Em-dash (U+2014) found at line(s) {offending_lines!r} in "
            f"{GUIDE_PATH.name}. Use ASCII double-hyphen in prose or rephrase."
        )

    def test_registry_drift_check(self) -> None:
        """When the lens registry is populated, every registered lens_id must appear in the guide."""
        from spacegame.data_loader import get_data_loader

        text = _guide_text()
        loader = get_data_loader()

        if not loader.lenses:
            pytest.skip(
                "Lens registry is empty (A2-5/A2-6 not yet landed). "
                "Registry drift check activates when the registry populates."
            )

        missing = sorted(lid for lid in loader.lenses if lid not in text)
        assert not missing, (
            f"Registered lens_id(s) not covered by lens authoring guide: {missing!r}. "
            "Add voice notes for each new lens before it ships."
        )
