"""Tests for Phase 13 — Module pixel customization (recoloring).

Covers color override storage, serialization, pixel resolution with
overrides, and validation of recolorable vs locked pixels.
"""

from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    resolve_placed_module,
    is_pixel_recolorable,
)
from spacegame.models.ship_build import PlacedPixel


def _test_module() -> ShipModule:
    return ShipModule(
        id="test_mod",
        name="Test",
        description="",
        category="cockpit",
        manufacturer="reyes_kowalski",
        pixel_grid=[
            [".", "H", "."],
            ["H", "G", "H"],
            ["H", "H", "H"],
        ],
        material_map={"H": "module_hull_rk", "G": "cockpit_glass"},
        provides={},
        weight=3.0,
        base_cost=0,
    )


def _catalog() -> dict[str, ShipModule]:
    return {"test_mod": _test_module()}


class TestColorOverrideStorage:
    def test_default_empty_overrides(self) -> None:
        pm = PlacedModule(module_id="test", x=0, y=0)
        assert pm.color_overrides == {}

    def test_set_override(self) -> None:
        pm = PlacedModule(module_id="test", x=0, y=0)
        pm.color_overrides[(1, 0)] = "heavy_armor"
        assert pm.color_overrides[(1, 0)] == "heavy_armor"

    def test_multiple_overrides(self) -> None:
        pm = PlacedModule(module_id="test", x=0, y=0)
        pm.color_overrides[(0, 1)] = "stealth_composite"
        pm.color_overrides[(2, 1)] = "light_alloy"
        assert len(pm.color_overrides) == 2


class TestColorOverrideSerialization:
    def test_to_dict_includes_overrides(self) -> None:
        pm = PlacedModule(module_id="test", x=5, y=3)
        pm.color_overrides[(1, 0)] = "heavy_armor"
        pm.color_overrides[(2, 2)] = "light_alloy"
        d = pm.to_dict()
        assert "color_overrides" in d
        assert d["color_overrides"]["1,0"] == "heavy_armor"
        assert d["color_overrides"]["2,2"] == "light_alloy"

    def test_to_dict_empty_overrides_omitted(self) -> None:
        pm = PlacedModule(module_id="test", x=0, y=0)
        d = pm.to_dict()
        # Empty overrides should be omitted or empty
        overrides = d.get("color_overrides", {})
        assert overrides == {}

    def test_from_dict_round_trip(self) -> None:
        pm = PlacedModule(module_id="test", x=5, y=3, rotation=1, flipped=True)
        pm.color_overrides[(1, 0)] = "heavy_armor"
        pm.color_overrides[(0, 2)] = "stealth_composite"
        d = pm.to_dict()
        restored = PlacedModule.from_dict(d)
        assert restored.module_id == "test"
        assert restored.x == 5
        assert restored.rotation == 1
        assert restored.flipped is True
        assert restored.color_overrides[(1, 0)] == "heavy_armor"
        assert restored.color_overrides[(0, 2)] == "stealth_composite"

    def test_from_dict_backward_compat(self) -> None:
        """Old saves without color_overrides load with empty dict."""
        d = {"module_id": "test", "x": 0, "y": 0}
        pm = PlacedModule.from_dict(d)
        assert pm.color_overrides == {}


class TestResolveWithOverrides:
    def test_no_overrides_uses_original(self) -> None:
        catalog = _catalog()
        pm = PlacedModule(module_id="test_mod", x=0, y=0)
        pixels = resolve_placed_module(pm, catalog)
        # Glass pixel at local (1,1) → world (1,1)
        glass_pixel = [p for p in pixels if p.x == 1 and p.y == 1][0]
        assert glass_pixel.material_id == "cockpit_glass"

    def test_override_changes_material(self) -> None:
        catalog = _catalog()
        pm = PlacedModule(module_id="test_mod", x=0, y=0)
        # Override hull pixel at local (1,0) to heavy_armor
        pm.color_overrides[(1, 0)] = "heavy_armor"
        pixels = resolve_placed_module(pm, catalog)
        overridden = [p for p in pixels if p.x == 1 and p.y == 0][0]
        assert overridden.material_id == "heavy_armor"

    def test_non_overridden_pixels_unchanged(self) -> None:
        catalog = _catalog()
        pm = PlacedModule(module_id="test_mod", x=0, y=0)
        pm.color_overrides[(1, 0)] = "heavy_armor"
        pixels = resolve_placed_module(pm, catalog)
        # Hull pixel at (0,1) should still be module_hull_rk
        hull_pixel = [p for p in pixels if p.x == 0 and p.y == 1][0]
        assert hull_pixel.material_id == "module_hull_rk"

    def test_override_with_rotation(self) -> None:
        """Overrides use local coords AFTER rotation/flip."""
        catalog = _catalog()
        pm = PlacedModule(module_id="test_mod", x=0, y=0, rotation=0)
        pm.color_overrides[(0, 2)] = "stealth_composite"
        pixels = resolve_placed_module(pm, catalog)
        bottom_left = [p for p in pixels if p.x == 0 and p.y == 2][0]
        assert bottom_left.material_id == "stealth_composite"

    def test_override_with_offset(self) -> None:
        catalog = _catalog()
        pm = PlacedModule(module_id="test_mod", x=5, y=3)
        pm.color_overrides[(1, 0)] = "heavy_armor"
        pixels = resolve_placed_module(pm, catalog)
        # Local (1,0) + offset (5,3) = world (6,3)
        overridden = [p for p in pixels if p.x == 6 and p.y == 3][0]
        assert overridden.material_id == "heavy_armor"


class TestRecolorablePixelCheck:
    def test_hull_pixel_is_recolorable(self) -> None:
        module = _test_module()
        assert is_pixel_recolorable(module, 1, 0) is True  # H at (1,0)
        assert is_pixel_recolorable(module, 0, 1) is True  # H at (0,1)

    def test_glass_pixel_is_locked(self) -> None:
        module = _test_module()
        assert is_pixel_recolorable(module, 1, 1) is False  # G at (1,1)

    def test_empty_pixel_is_not_recolorable(self) -> None:
        module = _test_module()
        assert is_pixel_recolorable(module, 0, 0) is False  # . at (0,0)

    def test_out_of_bounds_not_recolorable(self) -> None:
        module = _test_module()
        assert is_pixel_recolorable(module, 99, 99) is False
