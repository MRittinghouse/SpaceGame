"""Tests for ShipPart dataclass."""

from spacegame.models.ship_part import ShipPart


class TestShipPartCreation:
    def _make_part(self, **overrides) -> ShipPart:
        defaults = {
            "id": "light_laser",
            "name": "Light Laser",
            "description": "A basic energy weapon.",
            "slot_type": "weapon",
            "min_size": "small",
            "manufacturer": "sung_dynamics",
            "provides": {"damage": 15, "accuracy": 80, "energy_cost": 2},
            "base_cost": 1000,
        }
        defaults.update(overrides)
        return ShipPart(**defaults)

    def test_basic_creation(self) -> None:
        part = self._make_part()
        assert part.id == "light_laser"
        assert part.slot_type == "weapon"
        assert part.min_size == "small"
        assert part.provides["damage"] == 15

    def test_to_dict(self) -> None:
        part = self._make_part()
        d = part.to_dict()
        assert d["id"] == "light_laser"
        assert d["slot_type"] == "weapon"
        assert d["min_size"] == "small"
        assert d["base_cost"] == 1000
        assert d["provides"]["damage"] == 15

    def test_from_dict(self) -> None:
        d = {
            "id": "heavy_railgun",
            "name": "Heavy Railgun",
            "description": "A devastating kinetic weapon.",
            "slot_type": "weapon",
            "min_size": "large",
            "manufacturer": "reyes_kowalski",
            "provides": {"damage": 45, "accuracy": 65, "energy_cost": 5},
            "base_cost": 8000,
            "mark": 2,
        }
        part = ShipPart.from_dict(d)
        assert part.id == "heavy_railgun"
        assert part.min_size == "large"
        assert part.mark == 2
        assert part.provides["damage"] == 45

    def test_round_trip(self) -> None:
        original = self._make_part(
            id="fusion_core",
            slot_type="reactor",
            min_size="medium",
            manufacturer="nexus_corp",
            provides={"power_output": 30},
            base_cost=5000,
            legendary=True,
        )
        restored = ShipPart.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.slot_type == original.slot_type
        assert restored.min_size == original.min_size
        assert restored.provides == original.provides
        assert restored.legendary == original.legendary

    def test_defaults(self) -> None:
        part = self._make_part()
        assert part.mark == 1
        assert part.legendary is False
        assert part.weight == 0.0


class TestPartSizeCompatibility:
    def _make_part(self, min_size: str) -> ShipPart:
        return ShipPart(
            id="test",
            name="Test",
            description="",
            slot_type="weapon",
            min_size=min_size,
            manufacturer="",
            provides={},
            base_cost=0,
        )

    def test_strict_size_matching(self) -> None:
        """Parts must match the slot's exact size."""
        small = self._make_part("small")
        assert small.fits_in_slot_size("small")
        assert not small.fits_in_slot_size("medium")
        assert not small.fits_in_slot_size("large")

        medium = self._make_part("medium")
        assert not medium.fits_in_slot_size("small")
        assert medium.fits_in_slot_size("medium")
        assert not medium.fits_in_slot_size("large")

        large = self._make_part("large")
        assert not large.fits_in_slot_size("small")
        assert not large.fits_in_slot_size("medium")
        assert large.fits_in_slot_size("large")
