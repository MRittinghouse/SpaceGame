"""The captain's tokens in all three renders (writing discipline spec 2.5 to 2.7)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from spacegame.models.captain_tokens import TOKEN_NAMES, WORDS, Pronouns, captain_line, fill
from tests.writing_gates.registry import CAPTAIN_TOKENS

HE, SHE, THEY = Pronouns.HE, Pronouns.SHE, Pronouns.THEY


class TestTheSpecsWorkedLines:
    """Spec 2.5's two worked lines, verbatim."""

    CREW_TALK = "{They}{v:'s|'re} asleep in the pilot's chair again. Leave {them}."
    BULLETIN = (
        "Dock records list Ash as master of record. {They} {v:holds|hold} a provisional license."
    )

    @pytest.mark.parametrize(
        ("choice", "expected"),
        [
            (HE, "He's asleep in the pilot's chair again. Leave him."),
            (SHE, "She's asleep in the pilot's chair again. Leave her."),
            (THEY, "They're asleep in the pilot's chair again. Leave them."),
        ],
    )
    def test_crew_talk(self, choice: Pronouns, expected: str) -> None:
        assert fill(self.CREW_TALK, choice) == expected

    @pytest.mark.parametrize(
        ("choice", "expected"),
        [
            (HE, "He holds a provisional license."),
            (SHE, "She holds a provisional license."),
            (THEY, "They hold a provisional license."),
        ],
    )
    def test_bulletin(self, choice: Pronouns, expected: str) -> None:
        assert fill(self.BULLETIN, choice).endswith(expected)


class TestTheTable:
    @pytest.mark.parametrize(
        ("token", "renders"),
        [
            ("they", ("he", "she", "they")),
            ("They", ("He", "She", "They")),
            ("them", ("him", "her", "them")),
            ("their", ("his", "her", "their")),
            ("Their", ("His", "Her", "Their")),
            ("theirs", ("his", "hers", "theirs")),
            ("themself", ("himself", "herself", "themself")),
            ("sir", ("sir", "ma'am", "Captain")),
            ("Sir", ("Sir", "Ma'am", "Captain")),
            ("son", ("son", "girl", "kid")),
            ("Son", ("Son", "Girl", "Kid")),
        ],
    )
    def test_every_token_in_all_three_renders(self, token: str, renders: tuple[str, ...]) -> None:
        assert tuple(fill(f"{{{token}}}", choice) for choice in (HE, SHE, THEY)) == renders

    def test_the_contractions_of_spec_2_5(self) -> None:
        """Spec 2.5's forms; doesn't and wasn't take a space after the pronoun."""
        line = "{they}{v:'s|'ve} gone. {they} {v:doesn't|don't} know. {they} {v:wasn't|weren't}."
        assert fill(line, SHE) == "she's gone. she doesn't know. she wasn't."
        assert fill(line, THEY) == "they've gone. they don't know. they weren't."
        assert fill("{they}'ll go. {they}'d go.", HE) == "he'll go. he'd go."

    def test_the_neutral_sir_is_a_capitalized_captain_mid_sentence(self) -> None:
        assert fill("Those are the rules, {sir}.", THEY) == "Those are the rules, Captain."

    def test_every_word_token_has_three_renders(self) -> None:
        assert all(len(renders) == 3 for renders in WORDS.values())


class TestOtherBraces:
    def test_a_surfaces_own_brace_is_left_for_its_fill(self) -> None:
        assert fill("{They} docked at {system}.", HE) == "He docked at {system}."

    def test_day_renders_only_when_given(self) -> None:
        assert fill("Day {day}. Fourteen-oh-six.", THEY, 61) == "Day 61. Fourteen-oh-six."
        assert fill("Day {day}.", THEY) == "Day {day}."

    def test_a_line_without_tokens_is_unchanged(self) -> None:
        line = "Good luck out there. Fly smart."
        assert fill(line, SHE) == line

    def test_rendering_twice_changes_nothing(self) -> None:
        once = fill("{They}{v:'s|'re} here, {sir}.", SHE)
        assert fill(once, HE) == once


class TestCaptainLine:
    def test_no_player_renders_they_them(self) -> None:
        """The intro narration plays before a player exists."""
        assert captain_line("{They} {v:waits|wait}.", None) == "They wait."

    def test_the_players_choice_and_day(self) -> None:
        player = SimpleNamespace(pronouns=SHE, game_day=12)
        assert captain_line("{They} logged day {day}.", player) == "She logged day 12."

    def test_a_stub_without_a_choice_renders_they_them(self) -> None:
        assert captain_line("{they}", SimpleNamespace(game_day="x")) == "they"


class TestPronounsParse:
    def test_saved_values(self) -> None:
        assert [Pronouns.parse(c.value) for c in Pronouns] == [HE, SHE, THEY]

    def test_anything_else_is_they_them(self) -> None:
        for value in (None, "", "xe/xem", 3, "He/Him"):
            assert Pronouns.parse(value) is THEY


def test_the_gate_registry_names_the_renderers_tokens() -> None:
    """tests/writing_gates/registry.py allows exactly the tokens this renderer fills."""
    assert CAPTAIN_TOKENS == TOKEN_NAMES
