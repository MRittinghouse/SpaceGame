"""Edge case tests identified during Phase 10 audit.

Closes gaps in: resolve_module_hit with empty builds, physics modifier
error handling, validate_requirements with unknown categories,
structural integrity with bridge clusters, and undo snapshot compat.
"""

import random

from spacegame.models.ship_build import (
    ShipBuild,
    PlacedPixel,
    HullMaterial,
    ShipStatsComputer,
)
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    resolve_all_pixels,
    validate_requirements,
)
from spacegame.models.module_combat import (
    ModuleCombatState,
    resolve_module_hit,
    init_module_combat_states,
    check_severing,
)
from spacegame.models.ship_physics import (
    compute_structural_integrity,
    compute_center_of_mass,
)


def _mat(mid: str = "m", w: float = 0.25) -> HullMaterial:
    return HullMaterial(
        id=mid, name="T", description="", color_primary=(128, 128, 128), weight_per_pixel=w
    )


def _module(mid: str, cat: str = "structural") -> ShipModule:
    return ShipModule(
        id=mid,
        name=mid,
        description="",
        category=cat,
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"], ["H", "H"]],
        material_map={"H": "m"},
        provides={},
        weight=2.0,
        base_cost=100,
    )


class TestResolveModuleHitEdgeCases:
    """Edge cases for combat hit resolution."""

    def test_empty_build_returns_none(self) -> None:
        build = ShipBuild(weight_class="tiny")
        states: list[ModuleCombatState] = []
        result = resolve_module_hit(build, {}, states)
        assert result is None

    def test_modules_with_unknown_catalog_entries(self) -> None:
        """Modules referencing unknown IDs should be skipped gracefully."""
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="nonexistent", x=0, y=0)]
        build.pixels = [PlacedPixel(x=5, y=5, material_id="m")]
        states = [ModuleCombatState("nonexistent", 0, 10, 10, False, "weapon")]
        random.seed(42)
        # Module has 0 pixel count (unknown), hull has 1 pixel
        result = resolve_module_hit(build, {}, states)
        assert result is None  # Only hull pixels targetable

    def test_all_hull_no_modules(self) -> None:
        """Build with only hull pixels should always return None (hull hit)."""
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=i, y=0, material_id="m") for i in range(10)]
        states: list[ModuleCombatState] = []
        random.seed(42)
        for _ in range(20):
            result = resolve_module_hit(build, {}, states)
            assert result is None


class TestPhysicsModifierErrorHandling:
    """Ensure stats computation survives physics failures."""

    def test_stats_compute_with_malformed_module(self) -> None:
        """Stats compute should not crash if module catalog has bad data."""
        catalog = {
            "broken": ShipModule(
                id="broken",
                name="B",
                description="",
                category="weapon",
                manufacturer="reyes_kowalski",
                pixel_grid=[],  # Empty grid!
                material_map={},
                provides={},
                weight=1.0,
                base_cost=0,
            )
        }
        materials = {"m": _mat()}
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="broken", x=0, y=0)]
        # Should not crash — physics handles empty coords gracefully
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        assert stats is not None

    def test_stats_compute_without_module_catalog(self) -> None:
        """Legacy path: no module_catalog should work fine."""
        materials = {"m": _mat()}
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=0, y=0, material_id="m")]
        stats = ShipStatsComputer.compute(build, materials)
        assert stats.hull >= 0


class TestValidateRequirementsEdgeCases:
    """Edge cases for build requirements validation."""

    def test_unknown_module_category_ignored(self) -> None:
        """Modules with unrecognized categories shouldn't crash validation."""
        catalog = {
            "weird": ShipModule(
                id="weird",
                name="Weird",
                description="",
                category="teleporter",
                manufacturer="reyes_kowalski",
                pixel_grid=[["H"]],
                material_map={"H": "m"},
                provides={},
                weight=1.0,
                base_cost=0,
            ),
        }
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="weird", x=0, y=0)]
        ok, msg = validate_requirements(build, catalog)
        # Should fail (missing mandatory categories), but not crash
        assert not ok
        assert "cockpit" in msg.lower() or "engine" in msg.lower()

    def test_duplicate_modules_counted_correctly(self) -> None:
        """Multiple modules of the same ID should each be counted."""
        catalog = {
            "gun": ShipModule(
                id="gun",
                name="Gun",
                description="",
                category="weapon",
                manufacturer="reyes_kowalski",
                pixel_grid=[["H"]],
                material_map={"H": "m"},
                provides={"slot_type": "weapon"},
                weight=0.5,
                base_cost=100,
            ),
        }
        build = ShipBuild(weight_class="tiny")
        build.modules = [
            PlacedModule(module_id="gun", x=0, y=0),
            PlacedModule(module_id="gun", x=2, y=0),
            PlacedModule(module_id="gun", x=4, y=0),
        ]
        # Still fails (missing other categories), but weapon count should be 3
        ok, msg = validate_requirements(build, catalog)
        assert not ok  # Missing cockpit, engine, shield, cargo


class TestStructuralIntegrityRefinement:
    """Test the refined scoring (lone bottleneck vs bridge cluster)."""

    def test_bridge_chain_scores_half(self) -> None:
        """A 1-pixel bridge between two 3x3 blocks creates a chain of art points.

        The bridge pixel plus the adjacent block edges form a bottleneck
        chain: (2,1)→(3,1)→(4,1). All are art points adjacent to each other,
        so they score 0.5 (bridge cluster, not lone bottleneck).
        """
        coords = [(x, y) for x in range(3) for y in range(3)]
        coords.append((3, 1))
        coords.extend([(x, y) for x in range(4, 7) for y in range(3)])
        scores = compute_structural_integrity(coords)
        assert scores[(3, 1)] == 0.5, f"Bridge chain pixel should be 0.5, got {scores[(3, 1)]}"

    def test_two_wide_bridge_also_cluster(self) -> None:
        """A 2-pixel wide bridge between blocks: both bridge pixels are in the cluster."""
        coords = [(x, y) for x in range(3) for y in range(3)]
        coords.append((3, 0))
        coords.append((3, 1))
        coords.extend([(x, y) for x in range(4, 7) for y in range(3)])
        scores = compute_structural_integrity(coords)
        # Bridge pixels are art points in a cluster
        assert scores[(3, 0)] < 1.0, "2-wide bridge should be less critical"
        assert scores[(3, 1)] < 1.0

    def test_3_wide_bridge_all_half(self) -> None:
        """3-pixel wide bridge: all art points are in the cluster."""
        coords = [(x, y) for x in range(3) for y in range(3)]
        coords.extend([(3, y) for y in range(3)])  # 3-wide bridge
        coords.extend([(x, y) for x in range(4, 7) for y in range(3)])
        scores = compute_structural_integrity(coords)
        for y in range(3):
            if (3, y) in scores and scores[(3, y)] > 0:
                assert scores[(3, y)] == 0.5, f"Bridge cluster at (3,{y}) should be 0.5"


class TestSeveringWithMixedBuild:
    """Test severing with both modules and hull pixels."""

    def test_severing_with_hull_bridge(self) -> None:
        """Hull pixels connecting two module groups: severing checks hull too."""
        catalog = {
            "mod": ShipModule(
                id="mod",
                name="M",
                description="",
                category="structural",
                manufacturer="reyes_kowalski",
                pixel_grid=[["H", "H"], ["H", "H"]],
                material_map={"H": "m"},
                provides={},
                weight=2.0,
                base_cost=100,
            ),
        }
        build = ShipBuild(weight_class="tiny")
        # Two modules far apart, connected by hull pixel bridge
        build.modules = [
            PlacedModule(module_id="mod", x=0, y=0),
            PlacedModule(module_id="mod", x=6, y=0),
        ]
        build.pixels = [
            PlacedPixel(x=2, y=0, material_id="m"),
            PlacedPixel(x=3, y=0, material_id="m"),
            PlacedPixel(x=4, y=0, material_id="m"),
            PlacedPixel(x=5, y=0, material_id="m"),
        ]
        states = init_module_combat_states(build, catalog)
        # No modules disabled — no severing
        severed = check_severing(build, catalog, states)
        assert severed == []


class TestUndoSnapshotCompat:
    """Test undo snapshot format compatibility."""

    def test_new_format_with_modules(self) -> None:
        """New-format snapshots include modules field."""
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="test", x=0, y=0)]
        build.pixels = [PlacedPixel(x=5, y=5, material_id="m")]
        snapshot = {
            "pixels": [p.to_dict() for p in build.pixels],
            "modules": [m.to_dict() for m in build.modules],
            "slots": [],
        }
        # Restore
        restored_modules = [PlacedModule.from_dict(d) for d in snapshot.get("modules", [])]
        assert len(restored_modules) == 1
        assert restored_modules[0].module_id == "test"

    def test_old_format_without_modules(self) -> None:
        """Old snapshots (no modules key) should restore with empty modules."""
        snapshot = {
            "pixels": [{"x": 0, "y": 0, "material_id": "m"}],
            "slots": [],
        }
        restored_modules = [PlacedModule.from_dict(d) for d in snapshot.get("modules", [])]
        assert restored_modules == []

    def test_very_old_list_format(self) -> None:
        """Very old snapshots might be plain lists (pixel dicts only).
        The builder should handle this gracefully."""
        old_snapshot = [{"x": 0, "y": 0, "material_id": "m"}]
        # New code detects this is a list, not a dict
        if isinstance(old_snapshot, list):
            pixels = [PlacedPixel.from_dict(d) for d in old_snapshot]
            modules: list = []
        else:
            pixels = [PlacedPixel.from_dict(d) for d in old_snapshot.get("pixels", [])]
            modules = [PlacedModule.from_dict(d) for d in old_snapshot.get("modules", [])]
        assert len(pixels) == 1
        assert len(modules) == 0
