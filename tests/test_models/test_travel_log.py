"""Tests for travel log generator — journal entries from travel events."""

import pytest
from spacegame.models.travel_log import TravelLogGenerator
from spacegame.models.journal import JournalEntry, VALID_TAGS


SAMPLE_TEMPLATES = {
    "first_visit": {
        "nexus_prime": "First visit to Nexus Prime — commerce capital.",
        "breakstone": "Arrived at Breakstone — mining heartland.",
    },
    "major_trade": [
        "Sold {commodity} at {system} for {profit} CR profit.",
        "Major deal: {profit} CR on {commodity} at {system}.",
    ],
    "encounter_survived": [
        "Survived hostiles near {system}.",
        "Close call near {system}. Ship intact.",
    ],
    "galaxy_event_witnessed": [
        "Witnessed {event_type} at {system}. {description}",
    ],
}


def _make_gen(templates: dict = None) -> TravelLogGenerator:
    return TravelLogGenerator(templates or SAMPLE_TEMPLATES)


# === First Visit ===


class TestFirstVisit:
    """on_first_visit should produce a journal entry for known systems."""

    def test_known_system_returns_entry(self) -> None:
        gen = _make_gen()
        entry = gen.on_first_visit("nexus_prime", 5)
        assert entry is not None
        assert isinstance(entry, JournalEntry)
        assert "Nexus Prime" in entry.text
        assert entry.system_id == "nexus_prime"
        assert entry.game_day == 5

    def test_unknown_system_returns_none(self) -> None:
        gen = _make_gen()
        entry = gen.on_first_visit("deep_void", 5)
        assert entry is None

    def test_entry_tagged_as_travel(self) -> None:
        gen = _make_gen()
        entry = gen.on_first_visit("breakstone", 10)
        assert entry.tag == "travel"
        assert "travel" in VALID_TAGS

    def test_entry_has_unique_id(self) -> None:
        gen = _make_gen()
        e1 = gen.on_first_visit("nexus_prime", 1)
        e2 = gen.on_first_visit("breakstone", 2)
        assert e1.entry_id != e2.entry_id


# === Major Trade ===


class TestMajorTrade:
    """on_major_trade should format template with trade details."""

    def test_produces_entry_with_trade_details(self) -> None:
        gen = _make_gen()
        entry = gen.on_major_trade("food", 1500, "nexus_prime", 10)
        assert entry is not None
        assert "food" in entry.text
        assert "1500" in entry.text
        assert entry.tag == "travel"

    def test_empty_templates_returns_none(self) -> None:
        gen = _make_gen({"major_trade": []})
        entry = gen.on_major_trade("food", 500, "nexus_prime", 5)
        assert entry is None

    def test_entry_system_matches(self) -> None:
        gen = _make_gen()
        entry = gen.on_major_trade("ore", 800, "breakstone", 7)
        assert entry.system_id == "breakstone"


# === Encounter Survived ===


class TestEncounterSurvived:
    """on_encounter_survived should produce entries for combat survival."""

    def test_produces_entry(self) -> None:
        gen = _make_gen()
        entry = gen.on_encounter_survived("crimson_reach", 15)
        assert entry is not None
        assert entry.tag == "travel"

    def test_empty_templates_returns_none(self) -> None:
        gen = _make_gen({"encounter_survived": []})
        entry = gen.on_encounter_survived("nexus_prime", 5)
        assert entry is None


# === Galaxy Event Witnessed ===


class TestGalaxyEventWitnessed:
    """on_galaxy_event_witnessed should format event details."""

    def test_produces_entry_with_event_details(self) -> None:
        gen = _make_gen()
        entry = gen.on_galaxy_event_witnessed(
            "embargo", "Guild suspends ore imports", "nexus_prime", 20
        )
        assert entry is not None
        assert "embargo" in entry.text
        assert "Guild suspends" in entry.text
        assert entry.tag == "travel"

    def test_empty_templates_returns_none(self) -> None:
        gen = _make_gen({"galaxy_event_witnessed": []})
        entry = gen.on_galaxy_event_witnessed("festival", "Party time", "breakstone", 5)
        assert entry is None


# === Data Loading Integration ===


class TestDataLoading:
    """Travel log templates should load from data_loader."""

    def test_data_loader_has_travel_log_templates(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        templates = dl.travel_log_templates
        assert isinstance(templates, dict)
        assert "first_visit" in templates
        assert len(templates["first_visit"]) >= 10  # All 11 systems
