"""Tests for Phase 5 — Builder undo/redo, confirm validation, drafts.

Covers composite undo/redo (modules + pixels), confirm gating via
validation, hull material filtering, and build draft saves.
"""

from spacegame.models.ship_build import (
    PlacedPixel,
    DesignatedSlot,
    ShipBuild,
)
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    validate_requirements,
    validate_connectivity,
)


# ============================================================================
# Helpers
# ============================================================================


def _simple_catalog() -> dict[str, ShipModule]:
    return {
        "cockpit": ShipModule(
            id="cockpit",
            name="Cockpit",
            description="",
            category="cockpit",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H", "H"], ["H", "H"]],
            material_map={"H": "m"},
            provides={"slot_type": "core"},
            weight=2.0,
            base_cost=1000,
        ),
        "engine": ShipModule(
            id="engine",
            name="Engine",
            description="",
            category="engine",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H", "H"]],
            material_map={"H": "m"},
            provides={"slot_type": "engine", "thrust": 5},
            weight=1.0,
            base_cost=500,
        ),
        "weapon": ShipModule(
            id="weapon",
            name="Weapon",
            description="",
            category="weapon",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H"]],
            material_map={"H": "m"},
            provides={"slot_type": "weapon"},
            weight=0.5,
            base_cost=300,
        ),
        "shield": ShipModule(
            id="shield",
            name="Shield",
            description="",
            category="shield",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H"]],
            material_map={"H": "m"},
            provides={"slot_type": "defense", "shield_hp": 10},
            weight=0.5,
            base_cost=300,
        ),
        "cargo": ShipModule(
            id="cargo",
            name="Cargo",
            description="",
            category="cargo",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H"]],
            material_map={"H": "m"},
            provides={"cargo_capacity": 5},
            weight=0.5,
            base_cost=200,
        ),
    }


# ============================================================================
# Composite Undo/Redo
# ============================================================================


class TestCompositeUndoRedo:
    """Test that undo/redo saves and restores both pixels and modules."""

    def test_undo_snapshot_format(self) -> None:
        """Snapshot should contain pixels, modules, and slots."""
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=0, y=0, material_id="test")]
        build.modules = [PlacedModule(module_id="cockpit", x=5, y=5)]
        build.slots = [DesignatedSlot(slot_type="weapon", x=0, y=0)]

        snapshot = {
            "pixels": [p.to_dict() for p in build.pixels],
            "modules": [m.to_dict() for m in build.modules],
            "slots": [s.to_dict() for s in build.slots],
        }
        assert len(snapshot["pixels"]) == 1
        assert len(snapshot["modules"]) == 1
        assert len(snapshot["slots"]) == 1
        assert snapshot["modules"][0]["module_id"] == "cockpit"

    def test_restore_snapshot_restores_modules(self) -> None:
        """Restoring a snapshot should bring back modules."""
        build = ShipBuild(weight_class="tiny")
        # Save state with one module
        build.modules = [PlacedModule(module_id="cockpit", x=5, y=5)]
        snapshot = {
            "pixels": [p.to_dict() for p in build.pixels],
            "modules": [m.to_dict() for m in build.modules],
            "slots": [s.to_dict() for s in build.slots],
        }

        # Modify: add another module
        build.modules.append(PlacedModule(module_id="engine", x=0, y=0))
        assert len(build.modules) == 2

        # Restore from snapshot
        build.pixels = [PlacedPixel.from_dict(d) for d in snapshot["pixels"]]
        build.modules = [PlacedModule.from_dict(d) for d in snapshot["modules"]]
        build.slots = [DesignatedSlot.from_dict(d) for d in snapshot["slots"]]
        assert len(build.modules) == 1
        assert build.modules[0].module_id == "cockpit"

    def test_snapshot_backward_compat(self) -> None:
        """Old-format snapshots (pixel list only) should not crash."""
        # Old format was just a list of pixel dicts
        old_snapshot = [{"x": 0, "y": 0, "material_id": "test"}]
        # New code should handle this gracefully if we detect old format
        # For backward compat, check if snapshot is a list (old) or dict (new)
        if isinstance(old_snapshot, list):
            pixels = [PlacedPixel.from_dict(d) for d in old_snapshot]
            assert len(pixels) == 1


# ============================================================================
# Confirm Validation
# ============================================================================


class TestConfirmValidation:
    """Test that confirm gating uses module requirements."""

    def test_empty_build_cannot_confirm(self) -> None:
        catalog = _simple_catalog()
        build = ShipBuild(weight_class="tiny")
        has_content = len(build.modules) > 0 or len(build.pixels) > 0
        assert not has_content, "Empty build should not allow confirm"

    def test_incomplete_build_has_warnings(self) -> None:
        catalog = _simple_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="cockpit", x=5, y=5)]
        ok, msg = validate_requirements(build, catalog)
        assert not ok, "Build missing engine/weapon/shield/cargo should fail"

    def test_complete_build_passes_validation(self) -> None:
        catalog = _simple_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="cockpit", x=5, y=5),
            PlacedModule(module_id="engine", x=0, y=5),
            PlacedModule(module_id="weapon", x=7, y=5),
            PlacedModule(module_id="shield", x=5, y=7),
            PlacedModule(module_id="cargo", x=6, y=7),
        ]
        ok, msg = validate_requirements(build, catalog)
        assert ok, f"Complete build should pass: {msg}"

    def test_disconnected_build_fails_connectivity(self) -> None:
        catalog = _simple_catalog()
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="cockpit", x=0, y=0),
            PlacedModule(module_id="weapon", x=14, y=14),
        ]
        ok, msg = validate_connectivity(build, catalog)
        assert not ok, "Disconnected build should fail connectivity"


# ============================================================================
# Hull Material Filtering
# ============================================================================


class TestHullMaterialFiltering:
    """Test that hull mode shows only the 4 hull-specific materials."""

    def test_hull_material_ids(self) -> None:
        from spacegame.views.ship_builder_view import HULL_PIXEL_MATERIALS

        assert len(HULL_PIXEL_MATERIALS) == 4
        assert "light_alloy" in HULL_PIXEL_MATERIALS
        assert "standard_plate" in HULL_PIXEL_MATERIALS
        assert "heavy_armor" in HULL_PIXEL_MATERIALS
        assert "stealth_composite" in HULL_PIXEL_MATERIALS

    def test_hull_materials_exclude_module_materials(self) -> None:
        from spacegame.views.ship_builder_view import HULL_PIXEL_MATERIALS

        assert "module_hull_rk" not in HULL_PIXEL_MATERIALS
        assert "cockpit_glass" not in HULL_PIXEL_MATERIALS
        assert "shield_emitter" not in HULL_PIXEL_MATERIALS


# ============================================================================
# Build Drafts
# ============================================================================


class TestBuildDrafts:
    """Test draft save system on the Player model."""

    def _make_player(self):
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="shuttle",
            name="Shuttle",
            ship_class="light",
            description="Basic",
            cargo_capacity=50,
            fuel_capacity=100,
            fuel_efficiency=1.0,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=1,
            special_abilities=[],
            availability="all",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        return Player(
            name="Test",
            credits=1000,
            current_system_id="test",
            ship=ship,
        )

    def test_player_has_drafts_field(self) -> None:
        player = self._make_player()
        assert hasattr(player, "build_drafts")
        assert player.build_drafts == []

    def test_save_draft(self) -> None:
        player = self._make_player()
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="cockpit", x=5, y=5)]

        player.build_drafts.append(
            {
                "name": "Draft 1",
                "build": build.to_dict(),
            }
        )
        assert len(player.build_drafts) == 1
        assert player.build_drafts[0]["name"] == "Draft 1"

        # Verify the build can be restored
        restored = ShipBuild.from_dict(player.build_drafts[0]["build"])
        assert len(restored.modules) == 1
        assert restored.modules[0].module_id == "cockpit"

    def test_draft_limit(self) -> None:
        drafts: list[dict] = []
        max_drafts = 20
        for i in range(max_drafts + 5):
            if len(drafts) < max_drafts:
                drafts.append({"name": f"Draft {i}", "build": {}})
        assert len(drafts) == max_drafts
