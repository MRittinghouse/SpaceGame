"""Tests for station location models and data loading."""

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
        for system_id in loader.systems:
            locs = loader.get_locations_for_system(system_id)
            assert len(locs) > 0, f"{system_id} should have at least one location"

    def test_every_system_has_market(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id in loader.systems:
            locs = loader.get_locations_for_system(system_id)
            types = [loc.location_type for loc in locs]
            assert "market" in types, f"{system_id} should have a market"

    def test_every_system_has_repair_bay(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id in loader.systems:
            locs = loader.get_locations_for_system(system_id)
            types = [loc.location_type for loc in locs]
            assert "repair_bay" in types, f"{system_id} should have a repair bay"

    def test_every_system_has_cantina(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_systems()
        loader.load_locations()
        for system_id in loader.systems:
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
