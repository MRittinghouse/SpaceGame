"""The captain's tokens (writing discipline spec 2.5 to 2.7): pronouns, verb agreement, address.

The player picks he/him, she/her or they/them, and only the words change. A line names the
captain in the third person through tokens, and the surface that prints the line renders them
at its display edge with ``captain_line``, so models and parity goldens keep the raw line. Any
other brace (a surface's own ``{system}`` or ``{shakedown_demand}``) is left as written for that
surface's own fill. A surface whose own fill is ``str.format`` or ``format_map`` renders these
tokens first, since ``{v:A|B}`` reads as a format spec and raises.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from spacegame.models.player import Player


class Pronouns(str, Enum):
    """The captain's pronouns, as the save writes them."""

    HE = "he/him"
    SHE = "she/her"
    THEY = "they/them"

    @classmethod
    def parse(cls, value: object) -> "Pronouns":
        """The choice a saved value names; anything else (an old save, a stub) is they/them.

        Args:
            value: A saved value, a Pronouns, or anything a test stub holds.

        Returns:
            The matching Pronouns, else ``Pronouns.THEY``.
        """
        if isinstance(value, Pronouns):
            return value
        for choice in cls:
            if value == choice.value:
                return choice
        return cls.THEY


# Each token's renders for he/him, she/her and they/them (spec 2.5 and 2.6; the spelling is
# the spec's, and the {son} she/her entry is the author's ruling of 2026-10-02).
WORDS: dict[str, tuple[str, str, str]] = {
    "they": ("he", "she", "they"),
    "They": ("He", "She", "They"),
    "them": ("him", "her", "them"),
    "their": ("his", "her", "their"),
    "Their": ("His", "Her", "Their"),
    "theirs": ("his", "hers", "theirs"),
    "themself": ("himself", "herself", "themself"),
    "sir": ("sir", "ma'am", "Captain"),
    "Sir": ("Sir", "Ma'am", "Captain"),
    "son": ("son", "girl", "kid"),
    "Son": ("Son", "Girl", "Kid"),
}
# Every token name this renderer fills: the words, verb agreement ("v"), and today's day.
TOKEN_NAMES: frozenset[str] = frozenset(WORDS) | {"v", "day"}

_COLUMN = {Pronouns.HE: 0, Pronouns.SHE: 1, Pronouns.THEY: 2}
_VERB = re.compile(r"\{v:([^|{}]*)\|([^{}]*)\}")
_WORD = re.compile(r"\{([A-Za-z]+)\}")


def fill(text: str, pronouns: Pronouns, day: Optional[int] = None) -> str:
    """Render the captain's tokens in a line.

    ``{v:A|B}`` becomes A for he/him and she/her and B for they/them; each word token
    becomes its column of WORDS; ``{day}`` becomes the day when one is given. Any other
    brace is left as written.

    Args:
        text: A line that may hold tokens.
        pronouns: The captain's choice.
        day: Today's game-day, or None to leave ``{day}`` as written.

    Returns:
        The rendered line.
    """
    column = _COLUMN[pronouns]
    text = _VERB.sub(lambda m: m.group(2) if pronouns is Pronouns.THEY else m.group(1), text)

    def word(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in WORDS:
            return WORDS[name][column]
        if name == "day" and day is not None:
            return str(day)
        return match.group(0)

    return _WORD.sub(word, text)


def captain_line(text: str, player: Optional["Player"]) -> str:
    """Render a line for the player's pronouns and day; they/them with no player yet.

    The intro narration plays before a player exists, and views built in tests may hold a
    stub, so the choice and the day are read defensively.

    Args:
        text: A line that may hold tokens.
        player: The player, or None.

    Returns:
        The rendered line.
    """
    pronouns = Pronouns.parse(getattr(player, "pronouns", None))
    day = getattr(player, "game_day", None)
    return fill(text, pronouns, day if isinstance(day, int) else None)
