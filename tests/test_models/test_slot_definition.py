"""Tests for SlotDefinition dataclass."""

from spacegame.models.slot_definition import (
    SIZE_ORDER,
    SLOT_SIZES,
    SLOT_TYPES,
    SlotDefinition,
)


class TestSlotDefinitionConstants:
    def test_slot_types_defined(self) -> None:
        assert "weapon" in SLOT_TYPES
        assert "defense" in SLOT_TYPES
        assert "engine" in SLOT_TYPES
        assert "utility" in SLOT_TYPES
        assert "cargo" in SLOT_TYPES
        assert "crew_quarters" in SLOT_TYPES
        assert "reactor" in SLOT_TYPES
        assert len(SLOT_TYPES) == 9

    def test_slot_sizes_defined(self) -> None:
        assert "small" in SLOT_SIZES
        assert "medium" in SLOT_SIZES
        assert "large" in SLOT_SIZES
        assert len(SLOT_SIZES) == 3

    def test_size_order(self) -> None:
        assert SIZE_ORDER["small"] < SIZE_ORDER["medium"]
        assert SIZE_ORDER["medium"] < SIZE_ORDER["large"]


class TestSlotDefinitionCreation:
    def _make_slot(self, **overrides) -> SlotDefinition:
        defaults = {
            "id": "weapon_small",
            "slot_type": "weapon",
            "size": "small",
            "footprint_w": 2,
            "footprint_h": 2,
            "weight": 3.0,
            "placement_cost": 500,
            "color": (200, 60, 60),
        }
        defaults.update(overrides)
        return SlotDefinition(**defaults)

    def test_basic_creation(self) -> None:
        slot = self._make_slot()
        assert slot.id == "weapon_small"
        assert slot.slot_type == "weapon"
        assert slot.size == "small"
        assert slot.footprint_w == 2
        assert slot.footprint_h == 2
        assert slot.weight == 3.0
        assert slot.placement_cost == 500

    def test_to_dict(self) -> None:
        slot = self._make_slot()
        d = slot.to_dict()
        assert d["id"] == "weapon_small"
        assert d["slot_type"] == "weapon"
        assert d["size"] == "small"
        assert d["footprint_w"] == 2
        assert d["footprint_h"] == 2
        assert d["weight"] == 3.0
        assert d["placement_cost"] == 500
        assert d["color"] == [200, 60, 60]

    def test_from_dict(self) -> None:
        d = {
            "id": "cargo_large",
            "slot_type": "cargo",
            "size": "large",
            "footprint_w": 4,
            "footprint_h": 6,
            "weight": 8.0,
            "placement_cost": 2000,
            "color": [220, 170, 50],
        }
        slot = SlotDefinition.from_dict(d)
        assert slot.id == "cargo_large"
        assert slot.slot_type == "cargo"
        assert slot.size == "large"
        assert slot.footprint_w == 4
        assert slot.footprint_h == 6
        assert slot.color == (220, 170, 50)

    def test_round_trip(self) -> None:
        original = self._make_slot(
            id="reactor_medium",
            slot_type="reactor",
            size="medium",
            footprint_w=3,
            footprint_h=3,
            weight=6.0,
            placement_cost=2500,
            color=(255, 200, 50),
        )
        restored = SlotDefinition.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.slot_type == original.slot_type
        assert restored.size == original.size
        assert restored.footprint_w == original.footprint_w
        assert restored.footprint_h == original.footprint_h
        assert restored.weight == original.weight
        assert restored.placement_cost == original.placement_cost
        assert restored.color == original.color

    def test_grid_area(self) -> None:
        slot = self._make_slot(footprint_w=3, footprint_h=4)
        assert slot.grid_area == 12

    def test_display_name(self) -> None:
        slot = self._make_slot(slot_type="crew_quarters", size="medium")
        assert "Crew Quarters" in slot.display_name
        assert "M" in slot.display_name or "Medium" in slot.display_name


class TestSizeCompatibility:
    def test_strict_size_matching(self) -> None:
        """Parts must match the slot's exact size."""
        assert SlotDefinition.part_fits_slot("small", "small")
        assert not SlotDefinition.part_fits_slot("small", "medium")
        assert not SlotDefinition.part_fits_slot("small", "large")

        assert not SlotDefinition.part_fits_slot("medium", "small")
        assert SlotDefinition.part_fits_slot("medium", "medium")
        assert not SlotDefinition.part_fits_slot("medium", "large")

        assert not SlotDefinition.part_fits_slot("large", "small")
        assert not SlotDefinition.part_fits_slot("large", "medium")
        assert SlotDefinition.part_fits_slot("large", "large")
