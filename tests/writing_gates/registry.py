"""The token registry (writing discipline spec 2.7): the braces each surface's code fills.

A ``{...}`` may appear in a data file only once the code that prints that file's lines fills
it; G5 fails any other. Each surface's own fill is listed with its file. The captain's tokens
(spec 2.5 and 2.6, with ``{day}``) are filled by ``spacegame.models.captain_tokens.captain_line``
where a surface prints its lines; an entry joins this table with ``CAPTAIN_TOKENS`` in the same
commit that wires its print path, and ``tests/test_compliance/test_captain_token_render_sites.py``
names those paths.

``{player}``, the captain's name, is filled only by the news fill today (spec 2.7). A line that
wants the name on another surface extends ``captain_line``, the port's ``CaptainTokens`` and
this table together, in both builds.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch

CAPTAIN_TOKENS = frozenset(
    "they They them their Their theirs themself v sir Sir son Son day".split()
)


@dataclass(frozen=True)
class Renders:
    """The files a set of renderers prints and the token names they fill."""

    files: str
    tokens: frozenset[str]
    where: str


REGISTRY: tuple[Renders, ...] = (
    Renders("data/dialogue/*.json", CAPTAIN_TOKENS, "dialogue_view; the inline dialogue panels"),
    Renders("data/combat/crew_interjections.json", CAPTAIN_TOKENS, "combat_view interjections"),
    Renders("data/combat/captains.json", CAPTAIN_TOKENS, "encounter_view hail; combat_view line"),
    Renders("data/combat/captain_variants.json", CAPTAIN_TOKENS, "as captains.json"),
    Renders("data/encounters/*.json", CAPTAIN_TOKENS, "encounter_view, before its format_map"),
    Renders("data/crew/ambient_dialogue.json", CAPTAIN_TOKENS, "game.py banner; crew commentary"),
    Renders("data/crew/station_chatter.json", CAPTAIN_TOKENS, "station_hub_view flavor lines"),
    Renders("data/economy/news_templates.json", CAPTAIN_TOKENS, "galaxy_map_view's ticker"),
    Renders(
        "data/economy/news_templates.json",
        frozenset(
            "system faction commodity description event_type milestone player ship amount"
            " detail".split()
        ),
        "news_ticker._fill",
    ),
    Renders(
        "data/journal/travel_log_templates.json",
        frozenset({"commodity", "profit", "system", "event_type", "description"}),
        "travel_log.py, str.format",
    ),
    Renders(
        "data/economy/galaxy_events.json", frozenset({"system"}), "galaxy_event.py, str.format"
    ),
    Renders(
        "data/ground/contract_templates.json",
        frozenset({"faction", "system"}),
        "ground_contracts.py, str.format",
    ),
    Renders(
        "data/narrative/post_capstone_templates.json",
        frozenset({"system_name", "outcome_label", "quantity", "commodity_name"}),
        "post_capstone_content.py, str.format",
    ),
    Renders(
        "data/auctions/*_voices.json",
        frozenset({"lot_headline", "current_high_bid", "amount", "gap_days", "display_name"}),
        "auction_view, str.format",
    ),
    Renders(
        "data/encounters/*.json", frozenset({"shakedown_demand"}), "encounter_view, format_map"
    ),
)


def tokens_for(file: str) -> frozenset[str]:
    """Every token name some renderer of a repo-relative data file fills."""
    names: set[str] = set()
    for entry in REGISTRY:
        if fnmatch(file, entry.files):
            names |= entry.tokens
    return frozenset(names)
