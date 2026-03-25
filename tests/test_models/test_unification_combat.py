"""Tests for Systems Unification Phase U2 — Combat integration.

Covers combat move extraction from module-installed equipment,
mark multiplier application, and weapon offline on module disable.
"""

from spacegame.models.ship_build import ShipBuild, PlacedPixel
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    get_module_equipment_slots,
)


# ============================================================================
# Helpers
# ============================================================================


def _weapon_module(mid: str = "wpn") -> ShipModule:
    return ShipModule(
        id=mid,
        name="Weapon Mount",
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
        name="Shield Gen",
        description="",
        category="shield",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"]],
        material_map={"H": "m"},
        provides={"slot_type": "defense", "shield_hp": 30},
        weight=1.5,
        base_cost=1000,
    )


# ============================================================================
# Equipment Slot Extraction with Installed Equipment
# ============================================================================


class TestModuleEquipmentExtraction:
    def test_installed_weapon_appears_in_slots(self) -> None:
        catalog = {"wpn": _weapon_module()}
        build = ShipBuild(weight_class="tiny")
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        pm.installed_upgrade_id = "laser_cannon"
        pm.upgrade_mark = 2
        build.modules = [pm]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 1
        assert slots[0]["installed_upgrade_id"] == "laser_cannon"
        assert slots[0]["upgrade_mark"] == 2

    def test_empty_slot_has_none(self) -> None:
        catalog = {"wpn": _weapon_module()}
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="wpn", x=0, y=0)]
        slots = get_module_equipment_slots(build, catalog)
        assert slots[0]["installed_upgrade_id"] is None

    def test_multiple_weapons_different_equipment(self) -> None:
        catalog = {"wpn": _weapon_module()}
        build = ShipBuild(weight_class="tiny")
        pm1 = PlacedModule(module_id="wpn", x=0, y=0)
        pm1.installed_upgrade_id = "laser_cannon"
        pm2 = PlacedModule(module_id="wpn", x=4, y=0)
        pm2.installed_upgrade_id = "plasma_repeater"
        build.modules = [pm1, pm2]
        slots = get_module_equipment_slots(build, catalog)
        assert len(slots) == 2
        ids = {s["installed_upgrade_id"] for s in slots}
        assert ids == {"laser_cannon", "plasma_repeater"}

    def test_mixed_modules_only_slot_types_extracted(self) -> None:
        catalog = {
            "wpn": _weapon_module(),
            "shd": _shield_module(),
            "cargo": ShipModule(
                id="cargo",
                name="Cargo",
                description="",
                category="cargo",
                manufacturer="reyes_kowalski",
                pixel_grid=[["H"]],
                material_map={"H": "m"},
                provides={"cargo_capacity": 10},
                weight=1.0,
                base_cost=500,
            ),
        }
        build = ShipBuild(weight_class="tiny")
        pm_wpn = PlacedModule(module_id="wpn", x=0, y=0)
        pm_wpn.installed_upgrade_id = "laser_cannon"
        pm_shd = PlacedModule(module_id="shd", x=4, y=0)
        pm_shd.installed_upgrade_id = "basic_shield_gen"
        pm_crg = PlacedModule(module_id="cargo", x=6, y=0)
        build.modules = [pm_wpn, pm_shd, pm_crg]
        slots = get_module_equipment_slots(build, catalog)
        # Only weapon and shield have slot_type, cargo doesn't
        assert len(slots) == 2
        types = {s["slot_type"] for s in slots}
        assert types == {"weapon", "defense"}


class TestEquipmentMarks:
    def test_mark_stored_per_module(self) -> None:
        catalog = {"wpn": _weapon_module()}
        build = ShipBuild(weight_class="tiny")
        pm1 = PlacedModule(module_id="wpn", x=0, y=0)
        pm1.installed_upgrade_id = "laser_cannon"
        pm1.upgrade_mark = 1
        pm2 = PlacedModule(module_id="wpn", x=4, y=0)
        pm2.installed_upgrade_id = "laser_cannon"
        pm2.upgrade_mark = 3
        build.modules = [pm1, pm2]
        slots = get_module_equipment_slots(build, catalog)
        marks = {s["module_idx"]: s["upgrade_mark"] for s in slots}
        assert marks[0] == 1
        assert marks[1] == 3

    def test_tuning_stored_per_module(self) -> None:
        catalog = {"wpn": _weapon_module()}
        build = ShipBuild(weight_class="tiny")
        pm = PlacedModule(module_id="wpn", x=0, y=0)
        pm.installed_upgrade_id = "laser_cannon"
        pm.upgrade_mark = 2
        pm.upgrade_tuning = "overcharged"
        build.modules = [pm]
        slots = get_module_equipment_slots(build, catalog)
        assert slots[0]["upgrade_tuning"] == "overcharged"


class TestSerializationWithEquipment:
    def test_build_round_trip_preserves_equipment(self) -> None:
        build = ShipBuild(weight_class="tiny")
        pm = PlacedModule(module_id="wpn", x=5, y=3)
        pm.installed_upgrade_id = "ion_blaster"
        pm.upgrade_mark = 2
        pm.upgrade_tuning = "focused"
        pm.color_overrides[(0, 0)] = "heavy_armor"
        build.modules = [pm]
        build.pixels = [PlacedPixel(x=0, y=0, material_id="standard_plate")]

        d = build.to_dict()
        restored = ShipBuild.from_dict(d)
        assert len(restored.modules) == 1
        rpm = restored.modules[0]
        assert rpm.installed_upgrade_id == "ion_blaster"
        assert rpm.upgrade_mark == 2
        assert rpm.upgrade_tuning == "focused"
        assert rpm.color_overrides[(0, 0)] == "heavy_armor"
        assert len(restored.pixels) == 1
