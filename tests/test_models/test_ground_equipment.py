"""Tests for ground equipment and loot table models.

Tests GroundEquipment serialization, loot table rolling, player
inventory persistence, and equipment effects in GroundCrewBonuses.
"""

import random

import pytest

from spacegame.models.ground_equipment import (
    GroundEquipment,
    GroundLootTable,
    EquipmentSlot,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_equipment(**overrides) -> GroundEquipment:
    """Create a test GroundEquipment with sensible defaults."""
    defaults = {
        "id": "test_item",
        "name": "Test Item",
        "description": "A test equipment item.",
        "slot": EquipmentSlot.UTILITY,
        "effects": {"vision_bonus": 1},
    }
    defaults.update(overrides)
    return GroundEquipment(**defaults)


def _make_loot_table(**overrides) -> GroundLootTable:
    """Create a test GroundLootTable with sensible defaults."""
    defaults = {
        "credit_range": (10, 50),
        "equipment_chance": 0.0,
        "equipment_pool": [],
        "commodity_drops": [],
    }
    defaults.update(overrides)
    return GroundLootTable(**defaults)


# ===========================================================================
# GroundEquipment
# ===========================================================================


class TestGroundEquipment:
    """GroundEquipment dataclass and serialization."""

    def test_construction(self):
        """Equipment stores all fields."""
        eq = _make_equipment(
            id="noise_dampener",
            name="Noise Dampener",
            slot=EquipmentSlot.UTILITY,
            effects={"noise_reduction": 1},
        )
        assert eq.id == "noise_dampener"
        assert eq.name == "Noise Dampener"
        assert eq.slot == EquipmentSlot.UTILITY
        assert eq.effects["noise_reduction"] == 1

    def test_serialization_round_trip(self):
        """to_dict/from_dict preserves all fields."""
        original = _make_equipment(
            id="personal_shield",
            name="Personal Shield Module",
            slot=EquipmentSlot.DEFENSE,
            effects={"hp_bonus": 2, "absorb_first_hit": 1},
        )
        data = original.to_dict()
        restored = GroundEquipment.from_dict(data)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.slot == original.slot
        assert restored.effects == original.effects

    def test_defense_slot(self):
        """Defense slot equipment is valid."""
        eq = _make_equipment(slot=EquipmentSlot.DEFENSE)
        assert eq.slot == EquipmentSlot.DEFENSE

    def test_utility_slot(self):
        """Utility slot equipment is valid."""
        eq = _make_equipment(slot=EquipmentSlot.UTILITY)
        assert eq.slot == EquipmentSlot.UTILITY


class TestEquipmentSlot:
    """EquipmentSlot enum values."""

    def test_slot_values(self):
        """Both slot types have expected string values."""
        assert EquipmentSlot.UTILITY.value == "utility"
        assert EquipmentSlot.DEFENSE.value == "defense"


# ===========================================================================
# GroundLootTable
# ===========================================================================


class TestGroundLootTable:
    """GroundLootTable rolling and determinism."""

    def test_credit_roll_in_range(self):
        """Credits rolled are within the specified range."""
        table = _make_loot_table(credit_range=(50, 100))
        rng = random.Random(42)
        loot = table.roll_container_loot(com_bonus=0.0, rng=rng)
        assert 50 <= loot["credits"] <= 100

    def test_com_bonus_increases_credits(self):
        """COM attribute bonus increases credit rolls."""
        table = _make_loot_table(credit_range=(100, 100))
        rng = random.Random(42)
        loot_base = table.roll_container_loot(com_bonus=0.0, rng=rng)
        rng2 = random.Random(42)
        loot_bonus = table.roll_container_loot(com_bonus=0.5, rng=rng2)
        # With 50% bonus applied to base of 100, should be 150
        assert loot_bonus["credits"] >= loot_base["credits"]

    def test_deterministic_with_same_seed(self):
        """Same seed produces same loot."""
        table = _make_loot_table(
            credit_range=(10, 100),
            equipment_chance=0.5,
            equipment_pool=["personal_shield", "noise_dampener"],
        )
        rng1 = random.Random(123)
        loot1 = table.roll_container_loot(com_bonus=0.0, rng=rng1)
        rng2 = random.Random(123)
        loot2 = table.roll_container_loot(com_bonus=0.0, rng=rng2)
        assert loot1 == loot2

    def test_no_equipment_when_chance_zero(self):
        """No equipment dropped when chance is 0."""
        table = _make_loot_table(
            equipment_chance=0.0,
            equipment_pool=["personal_shield"],
        )
        rng = random.Random(42)
        loot = table.roll_container_loot(com_bonus=0.0, rng=rng)
        assert loot.get("equipment") is None

    def test_equipment_dropped_when_chance_one(self):
        """Equipment always dropped when chance is 1.0."""
        table = _make_loot_table(
            equipment_chance=1.0,
            equipment_pool=["personal_shield", "noise_dampener"],
        )
        rng = random.Random(42)
        loot = table.roll_container_loot(com_bonus=0.0, rng=rng)
        assert loot["equipment"] in ["personal_shield", "noise_dampener"]

    def test_commodity_drops(self):
        """Commodity drops included when present."""
        table = _make_loot_table(
            commodity_drops=[("rare_mineral", 3), ("data_core", 1)],
        )
        rng = random.Random(42)
        loot = table.roll_container_loot(com_bonus=0.0, rng=rng)
        commodities = loot.get("commodities", {})
        # At least one commodity should be present
        assert len(commodities) > 0
        # Quantities should be within bounds
        for cid, qty in commodities.items():
            assert qty >= 1

    def test_empty_equipment_pool_no_drop(self):
        """Equipment chance > 0 but empty pool produces no equipment."""
        table = _make_loot_table(
            equipment_chance=1.0,
            equipment_pool=[],
        )
        rng = random.Random(42)
        loot = table.roll_container_loot(com_bonus=0.0, rng=rng)
        assert loot.get("equipment") is None

    def test_loot_table_serialization(self):
        """to_dict/from_dict round-trip on loot table."""
        original = _make_loot_table(
            credit_range=(50, 200),
            equipment_chance=0.3,
            equipment_pool=["vision_enhancer"],
            commodity_drops=[("iron_ore", 5)],
        )
        data = original.to_dict()
        restored = GroundLootTable.from_dict(data)
        assert restored.credit_range == original.credit_range
        assert restored.equipment_chance == original.equipment_chance
        assert restored.equipment_pool == original.equipment_pool
        assert restored.commodity_drops == original.commodity_drops


# ===========================================================================
# Player Ground Equipment Inventory
# ===========================================================================


class TestPlayerGroundEquipment:
    """Player ground_equipment field and save/load compatibility."""

    def test_default_empty_inventory(self):
        """Player starts with no ground equipment."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        ship_type = dl.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        player = Player(
            name="Test",
            credits=1000,
            current_system_id="nexus_prime",
            ship=ship,
        )
        assert player.ground_equipment == []

    def test_add_equipment(self):
        """Equipment IDs can be added to inventory."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        ship_type = dl.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        player = Player(
            name="Test",
            credits=1000,
            current_system_id="nexus_prime",
            ship=ship,
        )
        player.ground_equipment.append("noise_dampener")
        assert "noise_dampener" in player.ground_equipment


# ===========================================================================
# Equipment Effects in GroundCrewBonuses
# ===========================================================================


class TestEquipmentInCrewBonuses:
    """Equipment effects applied through GroundCrewBonuses.compute()."""

    def test_noise_dampener_reduces_noise(self):
        """Noise dampener equipment reduces noise by 1."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        bonuses = GroundCrewBonuses.compute(
            crew_ids=[],
            attributes=None,
            equipment_ids=["noise_dampener"],
        )
        assert bonuses.noise_reduction >= 1

    def test_vision_enhancer_adds_vision(self):
        """Vision enhancer adds +2 vision radius."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        bonuses = GroundCrewBonuses.compute(
            crew_ids=[],
            attributes=None,
            equipment_ids=["vision_enhancer"],
        )
        assert bonuses.vision_radius_bonus >= 2

    def test_personal_shield_adds_hp(self):
        """Personal shield adds HP bonus."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        bonuses = GroundCrewBonuses.compute(
            crew_ids=[],
            attributes=None,
            equipment_ids=["personal_shield"],
        )
        assert bonuses.hp_bonus >= 2

    def test_equipment_stacks_with_crew(self):
        """Equipment bonuses stack additively with crew bonuses."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        crew_only = GroundCrewBonuses.compute(
            crew_ids=["elena_reeves"],
            attributes=None,
        )
        crew_plus_equip = GroundCrewBonuses.compute(
            crew_ids=["elena_reeves"],
            attributes=None,
            equipment_ids=["vision_enhancer"],
        )
        # Vision: Elena gives +1, enhancer gives +2 = +3 total
        assert crew_plus_equip.vision_radius_bonus == crew_only.vision_radius_bonus + 2

    def test_no_equipment_no_change(self):
        """Empty equipment list doesn't affect bonuses."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        without = GroundCrewBonuses.compute(crew_ids=[], attributes=None)
        with_empty = GroundCrewBonuses.compute(
            crew_ids=[], attributes=None, equipment_ids=[]
        )
        assert without.vision_radius_bonus == with_empty.vision_radius_bonus
        assert without.noise_reduction == with_empty.noise_reduction

    def test_compute_backward_compatible(self):
        """compute() works without equipment_ids parameter."""
        from spacegame.models.ground_crew import GroundCrewBonuses

        # Should not raise — equipment_ids defaults to None/empty
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=None)
        assert bonuses.vision_radius_bonus == 0


# ===========================================================================
# DataLoader Equipment Loading
# ===========================================================================


class TestDataLoaderEquipment:
    """DataLoader loads ground equipment from JSON."""

    def test_loads_equipment(self):
        """DataLoader has ground_equipment populated."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        assert hasattr(dl, "ground_equipment")
        assert len(dl.ground_equipment) > 0

    def test_equipment_ids_match(self):
        """All expected equipment IDs are loaded."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        expected = {
            "personal_shield",
            "noise_dampener",
            "vision_enhancer",
            "lockpick_set",
            "emp_grenade",
        }
        loaded_ids = set(dl.ground_equipment.keys())
        assert expected.issubset(loaded_ids), f"Missing: {expected - loaded_ids}"

    def test_equipment_has_effects(self):
        """Each loaded equipment has non-empty effects dict."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        for eq_id, eq in dl.ground_equipment.items():
            assert len(eq.effects) > 0, f"{eq_id} has no effects"
