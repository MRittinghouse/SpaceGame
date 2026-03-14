"""Tests for journal system models."""

import pytest
from spacegame.models.journal import (
    JournalEntry,
    Journal,
    VALID_TAGS,
    PLAYER_ENTRY_MAX_LENGTH,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_auto_entry(
    entry_id: str = "auto_m01",
    text: str = "Acquired bill of landing at Nexus Prime.",
    game_day: int = 1,
    system_id: str = "nexus_prime",
    trigger_flag: str = "talked_to_officer_larsen",
    mission_id: str = "bill_of_landing",
) -> JournalEntry:
    return JournalEntry(
        entry_id=entry_id,
        text=text,
        game_day=game_day,
        system_id=system_id,
        source="auto",
        trigger_flag=trigger_flag,
        mission_id=mission_id,
    )


def _make_player_entry(
    entry_id: str = "player_0001",
    text: str = "Something feels off about Larsen.",
    game_day: int = 3,
    system_id: str = "nexus_prime",
    tag: str = "suspicions",
) -> JournalEntry:
    return JournalEntry(
        entry_id=entry_id,
        text=text,
        game_day=game_day,
        system_id=system_id,
        source="player",
        tag=tag,
    )


def _make_auto_templates() -> list[JournalEntry]:
    """Create a set of auto-entry templates for testing."""
    return [
        _make_auto_entry(
            entry_id="auto_m01",
            text="Acquired bill of landing.",
            trigger_flag="talked_to_officer_larsen",
        ),
        _make_auto_entry(
            entry_id="auto_m02",
            text="Delivered iron ore to Forgeworks.",
            trigger_flag="delivered_iron_ore",
            system_id="forgeworks",
        ),
        _make_auto_entry(
            entry_id="auto_m03",
            text="Met Elena Reeves at Nexus Prime.",
            trigger_flag="talked_to_elena_cantina",
        ),
    ]


# ============================================================================
# JournalEntry Tests
# ============================================================================


class TestJournalEntry:
    """Tests for JournalEntry dataclass."""

    def test_creation_auto(self) -> None:
        """Auto entry has correct defaults."""
        entry = _make_auto_entry()
        assert entry.entry_id == "auto_m01"
        assert entry.source == "auto"
        assert entry.trigger_flag == "talked_to_officer_larsen"
        assert entry.tag == ""

    def test_creation_player(self) -> None:
        """Player entry has correct fields."""
        entry = _make_player_entry()
        assert entry.entry_id == "player_0001"
        assert entry.source == "player"
        assert entry.tag == "suspicions"
        assert entry.trigger_flag == ""

    def test_defaults(self) -> None:
        """Minimal construction uses sensible defaults."""
        entry = JournalEntry(entry_id="test", text="Hello", game_day=1, system_id="nexus")
        assert entry.source == "auto"
        assert entry.tag == ""
        assert entry.trigger_flag == ""
        assert entry.mission_id == ""
        assert entry.created_at == 0

    def test_player_text_truncated(self) -> None:
        """Player entries exceeding 500 chars are truncated."""
        long_text = "x" * 600
        entry = JournalEntry(
            entry_id="p1", text=long_text, game_day=1, system_id="s",
            source="player",
        )
        assert len(entry.text) == PLAYER_ENTRY_MAX_LENGTH

    def test_auto_text_not_truncated(self) -> None:
        """Auto entries are not truncated (they're data-defined)."""
        long_text = "x" * 600
        entry = JournalEntry(
            entry_id="a1", text=long_text, game_day=1, system_id="s",
            source="auto",
        )
        assert len(entry.text) == 600

    def test_invalid_tag_cleared(self) -> None:
        """Invalid tag values are set to empty string."""
        entry = JournalEntry(
            entry_id="p1", text="test", game_day=1, system_id="s",
            source="player", tag="invalid_tag",
        )
        assert entry.tag == ""

    def test_valid_tags(self) -> None:
        """All valid tags are accepted."""
        for tag in ["people", "places", "suspicions", "goals", ""]:
            entry = JournalEntry(
                entry_id="p1", text="test", game_day=1, system_id="s",
                source="player", tag=tag,
            )
            assert entry.tag == tag

    def test_to_dict(self) -> None:
        """Serialization produces correct dict."""
        entry = _make_player_entry()
        data = entry.to_dict()
        assert data["entry_id"] == "player_0001"
        assert data["source"] == "player"
        assert data["tag"] == "suspicions"
        assert data["game_day"] == 3

    def test_from_dict(self) -> None:
        """Deserialization restores all fields."""
        data = {
            "entry_id": "auto_m05",
            "text": "Met Marcus Jin.",
            "game_day": 10,
            "system_id": "breakstone",
            "source": "auto",
            "trigger_flag": "met_marcus_jin",
            "mission_id": "m05",
            "tag": "",
            "created_at": 5,
        }
        entry = JournalEntry.from_dict(data)
        assert entry.entry_id == "auto_m05"
        assert entry.trigger_flag == "met_marcus_jin"
        assert entry.created_at == 5

    def test_roundtrip(self) -> None:
        """to_dict -> from_dict preserves all fields."""
        original = _make_player_entry(tag="goals")
        restored = JournalEntry.from_dict(original.to_dict())
        assert restored.entry_id == original.entry_id
        assert restored.text == original.text
        assert restored.game_day == original.game_day
        assert restored.system_id == original.system_id
        assert restored.source == original.source
        assert restored.tag == original.tag


# ============================================================================
# Journal Container Tests
# ============================================================================


class TestJournalAutoEntries:
    """Tests for auto-entry triggering."""

    def test_trigger_creates_entry(self) -> None:
        """Triggering a known flag creates an entry."""
        journal = Journal(auto_templates=_make_auto_templates())
        entry = journal.trigger_auto_entry("talked_to_officer_larsen", game_day=5, system_id="nexus_prime")
        assert entry is not None
        assert entry.entry_id == "auto_m01"
        assert entry.game_day == 5

    def test_trigger_idempotent(self) -> None:
        """Triggering the same flag twice returns None the second time."""
        journal = Journal(auto_templates=_make_auto_templates())
        first = journal.trigger_auto_entry("talked_to_officer_larsen", game_day=5)
        second = journal.trigger_auto_entry("talked_to_officer_larsen", game_day=6)
        assert first is not None
        assert second is None
        assert len(journal.get_entries()) == 1

    def test_trigger_unknown_flag(self) -> None:
        """Triggering an unknown flag returns None."""
        journal = Journal(auto_templates=_make_auto_templates())
        entry = journal.trigger_auto_entry("nonexistent_flag", game_day=1)
        assert entry is None
        assert len(journal.get_entries()) == 0

    def test_trigger_uses_template_text(self) -> None:
        """Triggered entry uses the template's text."""
        journal = Journal(auto_templates=_make_auto_templates())
        entry = journal.trigger_auto_entry("delivered_iron_ore", game_day=3)
        assert entry is not None
        assert entry.text == "Delivered iron ore to Forgeworks."

    def test_trigger_overrides_system_id(self) -> None:
        """Triggered entry uses provided system_id over template default."""
        journal = Journal(auto_templates=_make_auto_templates())
        entry = journal.trigger_auto_entry(
            "talked_to_officer_larsen", game_day=5, system_id="custom_system"
        )
        assert entry.system_id == "custom_system"

    def test_empty_templates(self) -> None:
        """Journal with no templates triggers nothing."""
        journal = Journal()
        entry = journal.trigger_auto_entry("any_flag", game_day=1)
        assert entry is None


class TestJournalPlayerEntries:
    """Tests for player-written entries."""

    def test_add_player_entry(self) -> None:
        """Adding a player entry returns the new entry."""
        journal = Journal()
        entry = journal.add_player_entry(
            text="I don't trust Dex.", game_day=10, system_id="nexus_prime", tag="suspicions"
        )
        assert entry is not None
        assert entry.source == "player"
        assert entry.tag == "suspicions"
        assert entry.text == "I don't trust Dex."

    def test_player_entry_auto_id(self) -> None:
        """Player entries get sequential auto-generated IDs."""
        journal = Journal()
        e1 = journal.add_player_entry(text="First", game_day=1, system_id="s")
        e2 = journal.add_player_entry(text="Second", game_day=2, system_id="s")
        assert e1.entry_id == "player_0001"
        assert e2.entry_id == "player_0002"

    def test_edit_player_entry_text(self) -> None:
        """Editing a player entry changes its text."""
        journal = Journal()
        entry = journal.add_player_entry(text="Original", game_day=1, system_id="s")
        success, msg = journal.edit_player_entry(entry.entry_id, text="Updated")
        assert success
        assert journal.get_entries()[0].text == "Updated"

    def test_edit_player_entry_tag(self) -> None:
        """Editing a player entry can change its tag."""
        journal = Journal()
        entry = journal.add_player_entry(text="Note", game_day=1, system_id="s", tag="people")
        success, msg = journal.edit_player_entry(entry.entry_id, tag="goals")
        assert success
        assert journal.get_entries()[0].tag == "goals"

    def test_edit_truncates_long_text(self) -> None:
        """Editing with text > 500 chars truncates."""
        journal = Journal()
        entry = journal.add_player_entry(text="Short", game_day=1, system_id="s")
        long_text = "y" * 600
        journal.edit_player_entry(entry.entry_id, text=long_text)
        assert len(journal.get_entries()[0].text) == PLAYER_ENTRY_MAX_LENGTH

    def test_cannot_edit_auto_entry(self) -> None:
        """Editing an auto entry fails."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1)
        success, msg = journal.edit_player_entry("auto_m01", text="Hacked")
        assert not success
        assert "auto" in msg.lower()

    def test_edit_nonexistent_entry(self) -> None:
        """Editing a nonexistent entry fails."""
        journal = Journal()
        success, msg = journal.edit_player_entry("no_such_id", text="test")
        assert not success

    def test_delete_player_entry(self) -> None:
        """Deleting a player entry removes it."""
        journal = Journal()
        entry = journal.add_player_entry(text="Temp", game_day=1, system_id="s")
        assert len(journal.get_entries()) == 1
        success, msg = journal.delete_player_entry(entry.entry_id)
        assert success
        assert len(journal.get_entries()) == 0

    def test_cannot_delete_auto_entry(self) -> None:
        """Deleting an auto entry fails."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1)
        success, msg = journal.delete_player_entry("auto_m01")
        assert not success

    def test_delete_nonexistent_entry(self) -> None:
        """Deleting a nonexistent entry fails."""
        journal = Journal()
        success, msg = journal.delete_player_entry("no_such_id")
        assert not success


class TestJournalFiltering:
    """Tests for entry retrieval and filtering."""

    def test_get_entries_chronological(self) -> None:
        """Entries are returned in insertion order."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1)
        journal.add_player_entry(text="Note", game_day=2, system_id="s")
        journal.trigger_auto_entry("delivered_iron_ore", game_day=3)
        entries = journal.get_entries()
        assert len(entries) == 3
        assert entries[0].game_day == 1
        assert entries[1].game_day == 2
        assert entries[2].game_day == 3

    def test_filter_by_tag(self) -> None:
        """Tag filter returns only matching player entries."""
        journal = Journal()
        journal.add_player_entry(text="NPC note", game_day=1, system_id="s", tag="people")
        journal.add_player_entry(text="Place note", game_day=2, system_id="s", tag="places")
        journal.add_player_entry(text="Theory", game_day=3, system_id="s", tag="suspicions")
        people = journal.get_entries(tag_filter="people")
        assert len(people) == 1
        assert people[0].tag == "people"

    def test_filter_empty_tag_returns_all(self) -> None:
        """Empty tag filter returns all entries."""
        journal = Journal()
        journal.add_player_entry(text="A", game_day=1, system_id="s", tag="people")
        journal.add_player_entry(text="B", game_day=2, system_id="s", tag="goals")
        entries = journal.get_entries(tag_filter="")
        assert len(entries) == 2

    def test_filter_no_match(self) -> None:
        """Tag filter with no matches returns empty list."""
        journal = Journal()
        journal.add_player_entry(text="A", game_day=1, system_id="s", tag="people")
        entries = journal.get_entries(tag_filter="suspicions")
        assert len(entries) == 0

    def test_filter_by_source(self) -> None:
        """Source filter returns only auto or player entries."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1)
        journal.add_player_entry(text="My note", game_day=2, system_id="s")
        auto_only = journal.get_entries(source_filter="auto")
        player_only = journal.get_entries(source_filter="player")
        assert len(auto_only) == 1
        assert len(player_only) == 1
        assert auto_only[0].source == "auto"
        assert player_only[0].source == "player"

    def test_combined_filters(self) -> None:
        """Tag and source filters can combine."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1)
        journal.add_player_entry(text="People note", game_day=2, system_id="s", tag="people")
        journal.add_player_entry(text="Goal note", game_day=3, system_id="s", tag="goals")
        result = journal.get_entries(tag_filter="people", source_filter="player")
        assert len(result) == 1
        assert result[0].tag == "people"

    def test_get_entries_returns_copy(self) -> None:
        """Returned list is a copy, not the internal list."""
        journal = Journal()
        journal.add_player_entry(text="Test", game_day=1, system_id="s")
        entries = journal.get_entries()
        entries.clear()
        assert len(journal.get_entries()) == 1


# ============================================================================
# Serialization Tests
# ============================================================================


class TestJournalSerialization:
    """Tests for get_state/load_state round-trip."""

    def test_empty_journal_state(self) -> None:
        """Empty journal produces minimal state."""
        journal = Journal()
        state = journal.get_state()
        assert state["entries"] == []
        assert state["triggered_flags"] == []
        assert state["next_player_id"] == 1

    def test_roundtrip_with_entries(self) -> None:
        """State round-trip preserves all entries and metadata."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1, system_id="nexus_prime")
        journal.add_player_entry(text="My suspicion", game_day=3, system_id="nexus_prime", tag="suspicions")
        journal.add_player_entry(text="Goal note", game_day=5, system_id="breakstone", tag="goals")

        state = journal.get_state()

        # Restore into new journal with same templates
        journal2 = Journal(auto_templates=_make_auto_templates())
        journal2.load_state(state)

        entries = journal2.get_entries()
        assert len(entries) == 3
        assert entries[0].source == "auto"
        assert entries[1].tag == "suspicions"
        assert entries[2].tag == "goals"

    def test_roundtrip_preserves_triggered_flags(self) -> None:
        """Triggered flags are preserved across save/load."""
        journal = Journal(auto_templates=_make_auto_templates())
        journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1)

        state = journal.get_state()
        journal2 = Journal(auto_templates=_make_auto_templates())
        journal2.load_state(state)

        # Should not re-trigger the same flag
        result = journal2.trigger_auto_entry("talked_to_officer_larsen", game_day=10)
        assert result is None

    def test_roundtrip_preserves_player_id_counter(self) -> None:
        """Player ID counter is preserved so IDs don't collide after load."""
        journal = Journal()
        journal.add_player_entry(text="First", game_day=1, system_id="s")
        journal.add_player_entry(text="Second", game_day=2, system_id="s")

        state = journal.get_state()
        journal2 = Journal()
        journal2.load_state(state)

        e3 = journal2.add_player_entry(text="Third", game_day=3, system_id="s")
        assert e3.entry_id == "player_0003"

    def test_load_empty_state(self) -> None:
        """Loading empty dict produces empty journal."""
        journal = Journal()
        journal.add_player_entry(text="Will be cleared", game_day=1, system_id="s")
        journal.load_state({})
        assert len(journal.get_entries()) == 0
