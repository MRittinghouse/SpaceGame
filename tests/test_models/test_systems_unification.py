"""Tests for Systems Unification Phase U1 — Data Model Extension.

Covers PlacedModule equipment fields, serialization round-trips,
equipment slot extraction from builds, and backward compatibility.
"""

from spacegame.models.ship_build import ShipBuild
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    get_module_equipment_slots,
)


# ============================================================================
# Helpers
# ============================================================================


def _weapon_module() -> ShipModule:
    return ShipModule(
        id="wpn",
        name="Weapon",
        description="",
        category="weapon",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"], ["H", "H"]],
        material_map={"H": "m"},
        provides={"slot_type": "weapon"},
        weight=2.0,
        base_cost=1000,
    )


def _shield_module() -> ShipModule:
    return ShipModule(
        id="shd",
        name="Shield",
        description="",
        category="shield",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"]],
        material_map={"H": "m"},
        provides={"slot_type": "defense"},
        weight=1.5,
        base_cost=1000,
    )


def _cargo_module() -> ShipModule:
    return ShipModule(
        id="crg",
        name="Cargo",
        description="",
        category="cargo",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"]],
        material_map={"H": "m"},
        provides={"cargo_capacity": 15},
        weight=2.0,
        base_cost=500,
    )


def _structural_module() -> ShipModule:
    return ShipModule(
        id="str",
        name="Struct",
        description="",
        category="structural",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H"]],
        material_map={"H": "m"},
        provides={},
        weight=0.5,
        base_cost=100,
    )


def _catalog() -> dict[str, ShipModule]:
    return {
        m.id: m for m in [_weapon_module(), _shield_module(), _cargo_module(), _structural_module()]
    }


# ============================================================================
# PlacedModule Equipment Fields
# ============================================================================


class TestPlacedModuleEquipmentFields:
    def test_default_no_equipment(self) -> None:
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        assert pm.installed_upgrade_id is None
        assert pm.upgrade_mark == 1
        assert pm.upgrade_tuning is None

    def test_set_equipment(self) -> None:
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        pm.installed_upgrade_id = "laser_cannon"
        pm.upgrade_mark = 2
        pm.upgrade_tuning = "overcharged"
        assert pm.installed_upgrade_id == "laser_cannon"
        assert pm.upgrade_mark == 2
        assert pm.upgrade_tuning == "overcharged"

    def test_to_dict_includes_equipment(self) -> None:
        pm = PlacedModule(module_id="wpn", x=5, y=3)
        pm.installed_upgrade_id = "plasma_repeater"
        pm.upgrade_mark = 3
        pm.upgrade_tuning = "precision"
        d = pm.to_dict()
        assert d["installed_upgrade_id"] == "plasma_repeater"
        assert d["upgrade_mark"] == 3
        assert d["upgrade_tuning"] == "precision"

    def test_to_dict_omits_empty_equipment(self) -> None:
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        d = pm.to_dict()
        # Empty equipment fields should either be absent or None
        assert d.get("installed_upgrade_id") is None

    def test_from_dict_round_trip(self) -> None:
        pm = PlacedModule(module_id="wpn", x=5, y=3, rotation=1, flipped=True)
        pm.installed_upgrade_id = "ion_blaster"
        pm.upgrade_mark = 2
        pm.upgrade_tuning = "focused"
        d = pm.to_dict()
        restored = PlacedModule.from_dict(d)
        assert restored.installed_upgrade_id == "ion_blaster"
        assert restored.upgrade_mark == 2
        assert restored.upgrade_tuning == "focused"
        assert restored.rotation == 1
        assert restored.flipped is True

    def test_from_dict_backward_compat(self) -> None:
        """Old saves without equipment fields load with defaults."""
        d = {"module_id": "wpn", "x": 0, "y": 0}
        pm = PlacedModule.from_dict(d)
        assert pm.installed_upgrade_id is None
        assert pm.upgrade_mark == 1
        assert pm.upgrade_tuning is None

    def test_from_dict_with_color_overrides_and_equipment(self) -> None:
        """Both color overrides and equipment fields coexist."""
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        pm.color_overrides[(0, 0)] = "heavy_armor"
        pm.installed_upgrade_id = "laser_cannon"
        pm.upgrade_mark = 2
        d = pm.to_dict()
        restored = PlacedModule.from_dict(d)
        assert restored.color_overrides[(0, 0)] == "heavy_armor"
        assert restored.installed_upgrade_id == "laser_cannon"
        assert restored.upgrade_mark == 2


# ============================================================================
# Equipment Slot Extraction
# ============================================================================


class TestGetModuleEquipmentSlots:
    def test_extracts_weapon_slots(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="wpn", x=0, y=0),
            PlacedModule(module_id="wpn", x=4, y=0),
        ]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 2
        assert all(s["slot_type"] == "weapon" for s in slots)

    def test_extracts_mixed_slot_types(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="wpn", x=0, y=0),
            PlacedModule(module_id="shd", x=4, y=0),
        ]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 2
        types = {s["slot_type"] for s in slots}
        assert types == {"weapon", "defense"}

    def test_cargo_has_no_equipment_slot(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="crg", x=0, y=0),
        ]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 0  # Cargo provides cargo_capacity, not slot_type

    def test_structural_has_no_slot(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="str", x=0, y=0)]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 0

    def test_slot_includes_module_index(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="str", x=0, y=0),  # idx 0, no slot
            PlacedModule(module_id="wpn", x=2, y=0),  # idx 1, weapon slot
        ]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 1
        assert slots[0]["module_idx"] == 1

    def test_slot_includes_installed_equipment(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        pm.installed_upgrade_id = "laser_cannon"
        pm.upgrade_mark = 2
        pm.upgrade_tuning = "precision"
        build.modules = [pm]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 1
        assert slots[0]["installed_upgrade_id"] == "laser_cannon"
        assert slots[0]["upgrade_mark"] == 2
        assert slots[0]["upgrade_tuning"] == "precision"

    def test_empty_slot(self) -> None:
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="wpn", x=0, y=0)]
        slots = get_module_equipment_slots(build, catalog)
        assert slots[0]["installed_upgrade_id"] is None

    def test_empty_build(self) -> None:
        slots = get_module_equipment_slots(ShipBuild(weight_class="tiny"), {})
        assert slots == []
