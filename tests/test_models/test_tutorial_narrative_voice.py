"""Writing-Bible compliance + narrative voice guards for tutorials.

Pre-playtest polish: the tutorial content was rewritten to be narrative
voice rather than 4th-wall-breaking exposition. These tests guard that:

  - No AI writing tells (em-dashes, "couldn't help but", "a testament to",
    "no X, no Y" constructions).
  - Each tutorial step has the expected trigger + reasonable length.
  - Key narrative threads (father, mining work, fuel economy) appear in
    the tutorial content so future edits don't accidentally drop the
    emotional framing.
  - No references to the player-as-trader identity that doesn't match
    the established "kid surviving after father's death" framing.

See ``requirements/dialogue_writing_guide.md §6`` for the full anti-pattern list.
"""

from __future__ import annotations

import re

from spacegame.tutorial_manager import MINIGAME_HINTS, TUTORIAL_STEPS

# Banned patterns from the Writing Bible §6 (AI anti-patterns).
# Em-dash replaced with period+space; "no X, no Y" construction; "couldn't
# help but"; "a testament to"; gratuitous sensory cataloging.
_EM_DASH_PATTERNS = ["—", " -- "]
_BANNED_PATTERNS = [
    r"couldn't help but",
    r"a testament to",
    r"\bno \w+,\s*no \w+",  # "no X, no Y"
]


def _all_tutorial_text() -> list[tuple[str, str]]:
    """Yield (identifier, body) for every tutorial string we own."""
    entries: list[tuple[str, str]] = []
    for step in TUTORIAL_STEPS:
        entries.append((f"step:{step['id']}:title", step["title"]))
        entries.append((f"step:{step['id']}:body", step["description"]))
    for key, hint in MINIGAME_HINTS.items():
        entries.append((f"hint:{key}:title", hint["title"]))
        entries.append((f"hint:{key}:body", hint["description"]))
    return entries


class TestWritingBibleCompliance:
    """No AI-writing tells in tutorial content."""

    def test_no_em_dashes(self) -> None:
        offenders = []
        for ident, body in _all_tutorial_text():
            for dash in _EM_DASH_PATTERNS:
                if dash in body:
                    offenders.append(f"{ident}: contains {dash!r}")
        assert not offenders, (
            "Writing Bible: no em-dashes. Use periods + new sentences.\n  "
            + "\n  ".join(offenders)
        )

    def test_no_banned_genai_constructions(self) -> None:
        offenders = []
        for ident, body in _all_tutorial_text():
            lowered = body.lower()
            for pattern in _BANNED_PATTERNS:
                if re.search(pattern, lowered):
                    offenders.append(f"{ident}: matches /{pattern}/")
        assert not offenders, (
            "Writing Bible: AI-tell construction found.\n  " + "\n  ".join(offenders)
        )


class TestTutorialStepContract:
    """Structural invariants on TUTORIAL_STEPS."""

    def test_exactly_five_steps(self) -> None:
        assert len(TUTORIAL_STEPS) == 5

    def test_each_step_has_required_keys(self) -> None:
        for step in TUTORIAL_STEPS:
            assert "id" in step
            assert "title" in step
            assert "description" in step
            assert "trigger" in step

    def test_triggers_cover_canonical_set(self) -> None:
        """Triggers map to events in the game loop; drift breaks firing."""
        expected = {
            "galaxy_map",
            "trading",
            "after_first_trade",
            "activity",
            "after_first_travel",
        }
        actual = {s["trigger"] for s in TUTORIAL_STEPS}
        assert actual == expected

    def test_bodies_are_substantive_but_not_bloated(self) -> None:
        """40-120 words per step — not a tooltip, not a lecture."""
        for step in TUTORIAL_STEPS:
            word_count = len(step["description"].split())
            assert 40 <= word_count <= 120, (
                f"Step {step['id']} '{step['title']}' has {word_count} words "
                f"(expect 40-120)"
            )


class TestNarrativeThreadsPresent:
    """Confirm the rewritten content actually weaves in the established
    backstory, so a future edit can't accidentally strip the emotional
    framing back to generic exposition."""

    def test_father_referenced_in_steps(self) -> None:
        """At least one TUTORIAL_STEPS entry mentions the father."""
        bodies = " ".join(s["description"] for s in TUTORIAL_STEPS).lower()
        assert "father" in bodies, (
            "Narrative tutorials must build on the intro_narration "
            "backstory — at least one step should reference the father."
        )

    def test_father_referenced_in_hints(self) -> None:
        """Mining hint specifically should connect to the father's mining "
        background (he worked mining rigs per intro_narration)."""
        assert "father" in MINIGAME_HINTS["mining"]["description"].lower()

    def test_fuel_as_economic_constraint_appears(self) -> None:
        """The 'every jump costs fuel' mental model is a core gameplay
        grounding — it should surface in the trading / map flow."""
        map_body = TUTORIAL_STEPS[0]["description"].lower()
        fuel_body = TUTORIAL_STEPS[2]["description"].lower()
        assert "fuel" in map_body or "fuel" in fuel_body


class TestNoLegacyTraderIdentity:
    """Pre-rewrite tutorials framed the player as "a trader in a galaxy
    of opportunity." New framing is "a kid surviving after father's death."
    Guard against regression to the old voice."""

    def test_step_0_title_is_not_generic_welcome(self) -> None:
        """'Welcome to Aurelia!' was the old 4th-wall opener. Confirm
        we've moved past it."""
        assert TUTORIAL_STEPS[0]["title"].lower() != "welcome to aurelia!"

    def test_step_0_body_does_not_assert_trader_identity(self) -> None:
        """'You are a trader in a galaxy of opportunity' was the old
        pre-narrative opening line."""
        body = TUTORIAL_STEPS[0]["description"].lower()
        assert "you are a trader" not in body
        assert "galaxy of opportunity" not in body


class TestMinigameHintInventory:
    """Every expected hint key is present (no silent removal during polish)."""

    EXPECTED_HINT_KEYS = {
        "mining",
        "salvage",
        "refining",
        "combat_momentum",
        "combat_crew_combo",
        "combat_ultimate",
        "combat_boss",
        "combat_elemental",
        "combat_defensive_identity",
        "builder_welcome",
        "builder_shapes",
        "builder_tools",
        "builder_confirm",
        "builder_module_welcome",
        "builder_module_engine",
        "builder_module_requirements",
        "builder_module_hull",
        "builder_module_confirm",
    }

    def test_all_expected_hints_present(self) -> None:
        missing = self.EXPECTED_HINT_KEYS - set(MINIGAME_HINTS.keys())
        assert not missing, f"Hints silently dropped: {missing}"

    def test_each_hint_has_title_and_description(self) -> None:
        for key, hint in MINIGAME_HINTS.items():
            assert hint.get("title"), f"Hint '{key}' missing title"
            assert hint.get("description"), (
                f"Hint '{key}' missing description"
            )

    def test_hint_bodies_are_substantive(self) -> None:
        """30-150 words per hint — too short = not useful, too long = a lecture."""
        for key, hint in MINIGAME_HINTS.items():
            word_count = len(hint["description"].split())
            assert 30 <= word_count <= 150, (
                f"Hint '{key}' has {word_count} words (expect 30-150)"
            )


class TestTutorialShopMechanicVoice:
    """The TutorialShopView mechanic dialogue was polished to reinforce
    the father thread. Verify the new closing line is present."""

    def test_mechanic_closing_line_references_father(self) -> None:
        """After choice made, the mechanic's farewell now carries a
        human recognition of the player's backstory."""
        # Read the view module and look for the expected phrasing.
        from pathlib import Path

        source_path = (
            Path(__file__).resolve().parents[2]
            / "spacegame"
            / "views"
            / "tutorial_shop_view.py"
        )
        text = source_path.read_text(encoding="utf-8")
        assert "your old man would have liked this build" in text.lower()
        assert "that's how he was when i knew him" in text.lower()
