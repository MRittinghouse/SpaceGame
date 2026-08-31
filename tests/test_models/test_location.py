"""Tests for station location models and data loading."""

import json
import tempfile
from pathlib import Path

from spacegame.models.location import Location


def _make_location(**overrides: object) -> Location:
    """Create a test location with sensible defaults."""
    defaults: dict = {
        "id": "test_market",
        "name": "Test Market",
        "location_type": "market",
        "description": "A bustling marketplace.",
        "flavor_text": "Traders haggle over exotic goods.",
        "system_id": "nexus_prime",
        "repair_cost_per_hp": 0,
    }
    defaults.update(overrides)
    return Location(**defaults)


class TestLocationConstruction:
    """Tests for Location dataclass creation."""

    def test_create_market_location(self) -> None:
        loc = _make_location()
        assert loc.id == "test_market"
        assert loc.name == "Test Market"
        assert loc.location_type == "market"
        assert loc.system_id == "nexus_prime"

    def test_create_repair_bay_with_cost(self) -> None:
        loc = _make_location(
            id="test_repair",
            name="Dockside Repair",
            location_type="repair_bay",
            repair_cost_per_hp=12,
        )
        assert loc.location_type == "repair_bay"
        assert loc.repair_cost_per_hp == 12

    def test_create_cantina(self) -> None:
        loc = _make_location(
            id="test_cantina",
            location_type="cantina",
            flavor_text="The jukebox plays something unrecognizable.",
        )
        assert loc.location_type == "cantina"
        assert "jukebox" in loc.flavor_text

    def test_create_unique_location(self) -> None:
        loc = _make_location(
            id="financial_exchange",
            location_type="unique",
            name="Meridian Financial Exchange",
        )
        assert loc.location_type == "unique"

    def test_default_repair_cost_is_zero(self) -> None:
        loc = _make_location(location_type="market")
        assert loc.repair_cost_per_hp == 0


class TestLocationSerialization:
    """Tests for to_dict / from_dict round-trip."""

    def test_to_dict(self) -> None:
        loc = _make_location()
        d = loc.to_dict()
        assert d["id"] == "test_market"
        assert d["location_type"] == "market"
        assert d["system_id"] == "nexus_prime"
        assert d["repair_cost_per_hp"] == 0

    def test_from_dict(self) -> None:
        data = {
            "id": "repair_1",
            "name": "Repair Bay",
            "location_type": "repair_bay",
            "description": "Fix your hull.",
            "flavor_text": "Sparks fly.",
            "system_id": "breakstone",
            "repair_cost_per_hp": 8,
        }
        loc = Location.from_dict(data)
        assert loc.id == "repair_1"
        assert loc.repair_cost_per_hp == 8
        assert loc.system_id == "breakstone"

    def test_round_trip(self) -> None:
        original = _make_location(
            id="roundtrip",
            repair_cost_per_hp=10,
            flavor_text="Test flavor.",
        )
        restored = Location.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.location_type == original.location_type
        assert restored.description == original.description
        assert restored.flavor_text == original.flavor_text
        assert restored.system_id == original.system_id
        assert restored.repair_cost_per_hp == original.repair_cost_per_hp

    def test_from_dict_defaults_repair_cost(self) -> None:
        """Missing repair_cost_per_hp should default to 0."""
        data = {
            "id": "m1",
            "name": "Market",
            "location_type": "market",
            "description": "A market.",
            "flavor_text": "",
            "system_id": "nexus_prime",
        }
        loc = Location.from_dict(data)
        assert loc.repair_cost_per_hp == 0


class TestLocationDataLoading:
    """Tests for DataLoader location integration."""

    def test_load_locations_returns_dict(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        locations = loader.load_locations()
        assert isinstance(locations, dict)

    def test_all_systems_have_locations(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id, system in loader.systems.items():
            # AR-3: derelict systems are mission waypoints with no civic
            # infrastructure. They dock the player's ship but have no
            # services. Exempt.
            if system.type == "derelict":
                continue
            locs = loader.get_locations_for_system(system_id)
            assert len(locs) > 0, f"{system_id} should have at least one location"

    def test_every_system_has_market(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id, system in loader.systems.items():
            # AR-3: derelict systems are abandoned orbital platforms with no
            # civic infrastructure. Exempt them from the civic-location
            # requirements — they're mission waypoints, not service hubs.
            if system.type == "derelict":
                continue
            locs = loader.get_locations_for_system(system_id)
            types = [loc.location_type for loc in locs]
            assert "market" in types, f"{system_id} should have a market"

    def test_every_system_has_repair_bay(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id, system in loader.systems.items():
            if system.type == "derelict":
                continue
            locs = loader.get_locations_for_system(system_id)
            types = [loc.location_type for loc in locs]
            assert "repair_bay" in types, f"{system_id} should have a repair bay"

    def test_every_system_has_cantina(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id, system in loader.systems.items():
            if system.type == "derelict":
                continue
            locs = loader.get_locations_for_system(system_id)
            types = [loc.location_type for loc in locs]
            assert "cantina" in types, f"{system_id} should have a cantina"

    def test_repair_bays_have_positive_cost(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_locations()
        for system_id, locs in loader.locations.items():
            for loc in locs:
                if loc.location_type == "repair_bay":
                    assert loc.repair_cost_per_hp > 0, (
                        f"{system_id} repair bay should have positive cost"
                    )

    def test_location_ids_unique_per_system(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_locations()
        for system_id, locs in loader.locations.items():
            ids = [loc.id for loc in locs]
            assert len(ids) == len(set(ids)), f"{system_id} has duplicate location IDs"

    def test_location_types_are_valid(self) -> None:
        from spacegame.data_loader import DataLoader

        valid_types = {
            "market",
            "repair_bay",
            "cantina",
            "mining",
            "salvaging",
            "refining",
            "shipyard",
            "unique",
            "investment",
        }
        loader = DataLoader()
        loader.load_locations()
        for system_id, locs in loader.locations.items():
            for loc in locs:
                assert loc.location_type in valid_types, (
                    f"{system_id}/{loc.id} has invalid type: {loc.location_type}"
                )

    def test_get_locations_for_missing_system(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_locations()
        locs = loader.get_locations_for_system("nonexistent_system")
        assert locs == []

    def test_locations_loaded_in_load_all(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        assert len(loader.locations) > 0, "load_all should populate locations"


# ---------------------------------------------------------------------------
# Task 1 + 2 — lens_readings field and round-trip
# ---------------------------------------------------------------------------


class TestLocationLensReadings:
    """Tests for lens_readings field and reading_for() helper (A2-7)."""

    def test_default_lens_readings_is_empty_dict(self) -> None:
        """Location constructed without lens_readings has an empty dict."""
        loc = _make_location()
        assert loc.lens_readings == {}

    def test_lens_readings_may_be_populated(self) -> None:
        """lens_readings populated at construction is accessible."""
        loc = _make_location(lens_readings={"vengeance": "Old scores run deep here."})
        assert loc.lens_readings["vengeance"] == "Old scores run deep here."

    def test_reading_for_returns_string_when_present(self) -> None:
        """reading_for returns the reading string for a known lens."""
        loc = _make_location(lens_readings={"wealth": "Credits flow through every transaction."})
        assert loc.reading_for("wealth") == "Credits flow through every transaction."

    def test_reading_for_returns_empty_string_when_absent(self) -> None:
        """reading_for returns '' (not None) when the lens is not present."""
        loc = _make_location()
        result = loc.reading_for("vengeance")
        assert result == ""
        assert isinstance(result, str)

    def test_to_dict_includes_lens_readings(self) -> None:
        """to_dict emits lens_readings unconditionally."""
        loc = _make_location(
            lens_readings={"community": "The miners here look out for each other."}
        )
        d = loc.to_dict()
        assert "lens_readings" in d
        assert d["lens_readings"] == {"community": "The miners here look out for each other."}

    def test_to_dict_emits_empty_lens_readings_when_none(self) -> None:
        """to_dict emits an empty lens_readings dict even when there are no readings."""
        loc = _make_location()
        d = loc.to_dict()
        assert "lens_readings" in d
        assert d["lens_readings"] == {}

    def test_from_dict_accepts_lens_readings(self) -> None:
        """from_dict populates lens_readings from a dict that contains the key."""
        data = {
            "id": "test_loc",
            "name": "Test Location",
            "location_type": "market",
            "description": "A test.",
            "flavor_text": "Flavor.",
            "system_id": "test_system",
            "lens_readings": {"discovery": "There is always more to find."},
        }
        loc = Location.from_dict(data)
        assert loc.lens_readings == {"discovery": "There is always more to find."}

    def test_from_dict_defaults_lens_readings_when_missing(self) -> None:
        """from_dict on pre-A2-7 data (no lens_readings key) yields empty dict, not crash."""
        data = {
            "id": "old_loc",
            "name": "Old Location",
            "location_type": "market",
            "description": "Pre-A2-7 data.",
            "flavor_text": "",
            "system_id": "old_system",
        }
        loc = Location.from_dict(data)
        assert loc.lens_readings == {}

    def test_round_trip_preserves_lens_readings(self) -> None:
        """Location.from_dict(loc.to_dict()) preserves lens_readings exactly."""
        original = _make_location(
            lens_readings={
                "truth": "What happened here is buried under paperwork.",
                "justice": "Someone paid for this.",
            }
        )
        restored = Location.from_dict(original.to_dict())
        assert restored.lens_readings == original.lens_readings


# ---------------------------------------------------------------------------
# Task 4 — authored content quality checks
# ---------------------------------------------------------------------------


class TestLensReadingsContent:
    """Tests that authored lens_readings content meets AC 4 requirements."""

    _TARGET_IDS = {"breakstone_deep_mines", "nova_restricted_labs", "crimson_salvaging"}

    def test_authored_locations_have_lens_readings(self) -> None:
        """The three example locations each have at least 4 lens readings."""
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_locations()
        found: dict[str, int] = {}
        for _system_id, locs in loader.locations.items():
            for loc in locs:
                if loc.id in self._TARGET_IDS:
                    found[loc.id] = len(loc.lens_readings)
        for loc_id in self._TARGET_IDS:
            assert loc_id in found, f"Location '{loc_id}' not found in loaded locations"
            assert found[loc_id] >= 4, (
                f"Location '{loc_id}' should have at least 4 lens readings, got {found[loc_id]}"
            )

    def test_no_two_readings_for_the_same_location_share_more_than_half_their_words(self) -> None:
        """No two lens readings for the same location have Jaccard similarity >= 0.5."""
        import re
        from itertools import combinations

        from spacegame.data_loader import DataLoader

        STOPWORDS = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "of",
            "in",
            "to",
            "is",
            "are",
            "that",
            "this",
            "it",
            "on",
            "with",
            "for",
            "by",
            "as",
            "at",
            "from",
            "but",
        }

        def tokenize(text: str) -> set[str]:
            cleaned = re.sub(r"[.,;:!?\"()']+", "", text.lower())
            return {w for w in cleaned.split() if w not in STOPWORDS}

        loader = DataLoader()
        loader.load_locations()
        errors = []
        for _system_id, locs in loader.locations.items():
            for loc in locs:
                if len(loc.lens_readings) < 2:
                    continue
                readings = list(loc.lens_readings.items())
                for (lens_a, text_a), (lens_b, text_b) in combinations(readings, 2):
                    set_a = tokenize(text_a)
                    set_b = tokenize(text_b)
                    if not set_a or not set_b:
                        continue
                    jaccard = len(set_a & set_b) / len(set_a | set_b)
                    if jaccard >= 0.5:
                        errors.append(
                            f"Location '{loc.id}': readings '{lens_a}' and '{lens_b}' "
                            f"share too many words (Jaccard={jaccard:.2f} >= 0.5)"
                        )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Task 5 — extensibility proof
# ---------------------------------------------------------------------------


class TestLensReadingsExtensibility:
    """Tests that new lens readings load without any code changes."""

    def test_novel_lens_reading_loads_without_code_change(self) -> None:
        """A location with a lens reading for any valid lens_id loads correctly."""
        from spacegame.data_loader import DataLoader

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            galaxy_dir = tmp_path / "galaxy"
            galaxy_dir.mkdir()
            locations_data = {
                "locations": {
                    "test_system": [
                        {
                            "id": "test_loc",
                            "name": "Test Location",
                            "location_type": "market",
                            "description": "A test.",
                            "flavor_text": "",
                            "repair_cost_per_hp": 0,
                            "lens_readings": {
                                "exploration": "There are no clear maps of what lies beyond."
                            },
                        }
                    ]
                }
            }
            (galaxy_dir / "locations.json").write_text(json.dumps(locations_data), encoding="utf-8")
            loader = DataLoader(data_dir=tmp_path)
            loader.load_locations()
            locs = loader.get_locations_for_system("test_system")
            assert len(locs) == 1
            loc = locs[0]
            assert loc.reading_for("exploration") == "There are no clear maps of what lies beyond."
