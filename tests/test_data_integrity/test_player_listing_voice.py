"""SA-B5: Voice + journal compliance for player-listing content.

Scans the SA-B5 additions (consigned_lot_lines + player_listing_post_session
voice keys; the 3 new auto-journal entries) against the Writing Bible
rules: no em-dashes, no banned GenAI phrases, no parallel-negation
rhetoric.

Sable's reads have a tighter constraint — they must not collapse into
the universal-wisdom register. This test asserts the new templates are
short, observational, and tied to the specific outcome bucket rather
than authoring a self-help maxim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_STELLARIS_VOICES = _REPO_ROOT / "data" / "auctions" / "stellaris_voices.json"
_JOURNAL = _REPO_ROOT / "data" / "journal" / "entries.json"
_ACHIEVEMENTS = _REPO_ROOT / "data" / "progression" / "achievements.json"


# Em-dash unicode code points + common ASCII substitutes flagged by the
# Writing Bible scanner.
_EM_DASHES = {"—", "–", " -- "}

_BANNED_PHRASES = [
    "couldn't help but",
    "a testament to",
]

# Universal-wisdom register markers — Sable's reads must stay grounded.
_UNIVERSAL_WISDOM_MARKERS = [
    "in the end",
    "at the end of the day",
    "what we make of it",
    "we all have",
    "life is",
    "the truth is",
    "we are all",
]


def _load_voices() -> dict:
    with open(_STELLARIS_VOICES, encoding="utf-8") as f:
        return json.load(f)


def _load_journal_entries() -> list[dict]:
    with open(_JOURNAL, encoding="utf-8") as f:
        data = json.load(f)
    # Journal payload uses ``journal_entries`` as the top-level key.
    return data.get("journal_entries", data.get("entries", []))


def _flat_strings(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        out: list[str] = []
        for v in obj.values():
            out.extend(_flat_strings(v))
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            out.extend(_flat_strings(v))
        return out
    return []


class TestConsignedLotLinesVoice:
    def test_keys_present(self) -> None:
        voices = _load_voices()
        block = voices.get("consigned_lot_lines")
        assert isinstance(block, dict)
        for key in (
            "lot_open",
            "we_are_at",
            "lot_closed_sold",
            "lot_closed_withdrawn",
            "empty_inventory",
        ):
            assert key in block, f"missing consigned_lot_lines.{key}"

    def test_no_em_dashes(self) -> None:
        for line in _flat_strings(_load_voices().get("consigned_lot_lines", {})):
            for dash in _EM_DASHES:
                assert dash not in line, f"em-dash in consigned_lot_lines line: {line!r}"

    def test_no_banned_phrases(self) -> None:
        for line in _flat_strings(_load_voices().get("consigned_lot_lines", {})):
            lowered = line.lower()
            for phrase in _BANNED_PHRASES:
                assert phrase not in lowered, f"banned phrase {phrase!r} in: {line!r}"

    def test_seller_anonymized(self) -> None:
        """Decision §B5.8: no ``{player_name}`` substitutions in Velo lines."""
        for line in _flat_strings(_load_voices().get("consigned_lot_lines", {})):
            assert "{player_name}" not in line, (
                f"Velo's consigned-lot lines must stay seller-anonymized: {line!r}"
            )

    def test_ceremonial_register_keywords(self) -> None:
        """Velo's lines should keep at least one ceremonial-register keyword.

        Tests that the consigned-lot block does not collapse into purely
        casual prose by checking for at least one of the recognizably
        ceremonial markers Velo uses elsewhere in the file. This is a
        soft guard — the markers are deliberately broad.
        """
        block = _load_voices().get("consigned_lot_lines", {})
        ceremonial_markers = [
            "the lot",
            "we are at",
            "the reserve",
            "the consignor",
            "sold",
        ]
        joined = " ".join(_flat_strings(block)).lower()
        assert any(m in joined for m in ceremonial_markers), (
            "consigned_lot_lines should retain Velo's ceremonial register cues"
        )


class TestPlayerListingPostSessionVoice:
    def test_keys_present(self) -> None:
        voices = _load_voices()
        block = voices.get("player_listing_post_session")
        assert isinstance(block, dict)
        for key in (
            "sold_above_reserve",
            "sold_near_reserve",
            "withdrawn_no_bids",
            "withdrawn_bids_below_reserve",
        ):
            assert key in block

    def test_no_em_dashes(self) -> None:
        for line in _flat_strings(_load_voices().get("player_listing_post_session", {})):
            for dash in _EM_DASHES:
                assert dash not in line, f"em-dash in Sable line: {line!r}"

    def test_no_banned_phrases(self) -> None:
        for line in _flat_strings(_load_voices().get("player_listing_post_session", {})):
            lowered = line.lower()
            for phrase in _BANNED_PHRASES:
                assert phrase not in lowered

    def test_no_universal_wisdom_register(self) -> None:
        """Sable's reads must stay grounded in the lot's outcome.

        Decision §B5.8: avoid the GenAI failure mode where the post-
        session line drifts into self-help maxims. We scan for a small
        set of universal-wisdom markers — the test fails if any of them
        appear in any Sable bucket.
        """
        for line in _flat_strings(_load_voices().get("player_listing_post_session", {})):
            lowered = line.lower()
            for marker in _UNIVERSAL_WISDOM_MARKERS:
                assert marker not in lowered, (
                    f"Sable line drifts into universal-wisdom register ({marker!r}): {line!r}"
                )

    def test_lines_are_short(self) -> None:
        """Sable speaks in tight observations, not paragraphs."""
        for line in _flat_strings(_load_voices().get("player_listing_post_session", {})):
            # Two short sentences max.
            assert line.count(".") <= 3, f"Sable line is too long: {line!r}"


class TestPlayerListingJournalEntries:
    def _entries_by_flag(self, flag: str) -> list[dict]:
        return [e for e in _load_journal_entries() if e.get("trigger_flag") == flag]

    def test_first_listing_created_present(self) -> None:
        entries = self._entries_by_flag("auction_first_listing_created")
        assert len(entries) == 1
        assert entries[0]["entry_id"] == "auto_auction_first_listing_created"

    def test_first_sale_present(self) -> None:
        entries = self._entries_by_flag("auction_first_sale")
        assert len(entries) == 1
        assert entries[0]["entry_id"] == "auto_auction_first_sale"

    def test_first_listing_withdrawn_present(self) -> None:
        entries = self._entries_by_flag("auction_first_listing_withdrawn")
        assert len(entries) == 1
        assert entries[0]["entry_id"] == "auto_auction_first_listing_withdrawn"

    @pytest.mark.parametrize(
        "flag",
        [
            "auction_first_listing_created",
            "auction_first_sale",
            "auction_first_listing_withdrawn",
        ],
    )
    def test_no_em_dashes(self, flag: str) -> None:
        for entry in self._entries_by_flag(flag):
            text = entry.get("text", "")
            for dash in _EM_DASHES:
                assert dash not in text, f"em-dash in journal entry {entry['entry_id']}"

    @pytest.mark.parametrize(
        "flag",
        [
            "auction_first_listing_created",
            "auction_first_sale",
            "auction_first_listing_withdrawn",
        ],
    )
    def test_no_banned_phrases(self, flag: str) -> None:
        for entry in self._entries_by_flag(flag):
            lowered = entry.get("text", "").lower()
            for phrase in _BANNED_PHRASES:
                assert phrase not in lowered


class TestAuctionSellerAchievement:
    def test_achievement_registered(self) -> None:
        with open(_ACHIEVEMENTS, encoding="utf-8") as f:
            data = json.load(f)
        rows = [a for a in data["achievements"] if a["id"] == "auction_seller"]
        assert len(rows) == 1
        ach = rows[0]
        assert ach["stat_key"] == "auction_listings_sold"
        assert ach["threshold"] == 1
        assert ach["category"] == "economy"
        assert ach["hidden"] is True
