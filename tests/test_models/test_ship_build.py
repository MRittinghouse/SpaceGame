"""Tests for Phase A1 — Ship Builder data models and computation.

Covers shape rotation, grid validation, stat computation, weight
modifiers, identity detection, and serialization.
"""

from spacegame.models.ship_build import (
    HullShape,
    HullMaterial,
    PlacedPixel,
    DesignatedSlot,
    ShipBuild,
    ComputedShipStats,
    ShipGridManager,
    ShipStatsComputer,
    WEIGHT_CLASSES,
    SLOT_POOLS,
    IDENTITY_THRESHOLD,
)


# ============================================================================
# Helpers
# ============================================================================


def _shape_2x2() -> HullShape:
    """A simple 2x2 square shape."""
    return HullShape(
        id="square", name="Square", description="2x2 square",
        pixel_mask=[[True, True], [True, True]],
    )


def _shape_triangle() -> HullShape:
    """A right triangle (2x2, 3 pixels)."""
    return HullShape(
        id="triangle", name="Triangle", description="Right triangle",
        pixel_mask=[[True, True], [False, True]],
    )


def _shape_bar() -> HullShape:
    """A 3x1 horizontal bar."""
    return HullShape(
        id="bar", name="Bar", description="3x1 bar",
        pixel_mask=[[True, True, True]],
    )


def _mat_standard() -> HullMaterial:
    """Standard plate material."""
    return HullMaterial(
        id="standard_plate", name="Standard Plate", description="Balanced",
        color_primary=(112, 120, 136),
        hull_per_pixel=2.5, weight_per_pixel=0.7, cost_per_pixel=15,
    )


def _mat_heavy() -> HullMaterial:
    """Heavy armor material (juggernaut identity)."""
    return HullMaterial(
        id="heavy_armor", name="Heavy Armor", description="Tank",
        color_primary=(152, 112, 64),
        hull_per_pixel=3.0, armor_per_pixel=0.06, weight_per_pixel=1.2,
        cost_per_pixel=25,
    )


def _mat_shield() -> HullMaterial:
    """Shield crystal material (sentinel identity)."""
    return HullMaterial(
        id="shield_crystal", name="Shield Crystal", description="Shields",
        color_primary=(64, 168, 208),
        hull_per_pixel=1.0, shield_per_pixel=0.6, shield_regen_per_pixel=0.03,
        weight_per_pixel=0.6, cost_per_pixel=22,
    )


def _mat_light() -> HullMaterial:
    """Light alloy material (ghost identity)."""
    return HullMaterial(
        id="light_alloy", name="Light Alloy", description="Evasion",
        color_primary=(176, 184, 200),
        hull_per_pixel=1.5, evasion_per_pixel=0.08, weight_per_pixel=0.4,
        cost_per_pixel=8,
    )


def _materials() -> dict[str, HullMaterial]:
    return {
        "standard_plate": _mat_standard(),
        "heavy_armor": _mat_heavy(),
        "shield_crystal": _mat_shield(),
        "light_alloy": _mat_light(),
    }


# ============================================================================
# Shape Tests
# ============================================================================


class TestHullShape:
    """Shape properties and transformations."""

    def test_dimensions(self) -> None:
        s = _shape_2x2()
        assert s.width == 2
        assert s.height == 2

    def test_pixel_count(self) -> None:
        assert _shape_2x2().pixel_count == 4
        assert _shape_triangle().pixel_count == 3
        assert _shape_bar().pixel_count == 3

    def test_rotation_90(self) -> None:
        """3x1 bar rotated 90° becomes 1x3 vertical bar."""
        bar = _shape_bar()
        rotated = bar.rotated(1)
        assert rotated.width == 1
        assert rotated.height == 3
        assert rotated.pixel_count == 3

    def test_rotation_180(self) -> None:
        """Triangle rotated 180° mirrors diagonally."""
        tri = _shape_triangle()
        rotated = tri.rotated(2)
        assert rotated.pixel_count == 3
        assert rotated.width == 2
        assert rotated.height == 2
        # Original: TT / .T → Rotated 180°: T. / TT
        assert rotated.pixel_mask[0] == [True, False]
        assert rotated.pixel_mask[1] == [True, True]

    def test_rotation_270(self) -> None:
        bar = _shape_bar()
        rotated = bar.rotated(3)
        assert rotated.width == 1
        assert rotated.height == 3
        assert rotated.pixel_count == 3

    def test_rotation_360_identity(self) -> None:
        """4 rotations = original."""
        tri = _shape_triangle()
        rotated = tri.rotated(4)
        assert rotated.pixel_mask == tri.pixel_mask

    def test_flip_horizontal(self) -> None:
        """Triangle flipped: TT/.T → TT/T."""
        tri = _shape_triangle()
        flipped = tri.flipped()
        assert flipped.pixel_mask[0] == [True, True]
        assert flipped.pixel_mask[1] == [True, False]

    def test_serialization_round_trip(self) -> None:
        s = _shape_triangle()
        data = s.to_dict()
        restored = HullShape.from_dict(data)
        assert restored.id == s.id
        assert restored.pixel_mask == s.pixel_mask
        assert restored.pixel_count == s.pixel_count


# ============================================================================
# Grid Manager Tests
# ============================================================================


class TestShipGridManager:
    """Placement validation on the ship grid."""

    def test_place_shape_succeeds_on_empty_grid(self) -> None:
        mgr = ShipGridManager("medium")
        ok, msg = mgr.can_place_shape(_shape_2x2(), 5, 5, _mat_standard(), [])
        assert ok, msg

    def test_place_shape_fails_on_overlap(self) -> None:
        mgr = ShipGridManager("medium")
        existing = [PlacedPixel(5, 5, "standard_plate"),
                    PlacedPixel(6, 5, "standard_plate"),
                    PlacedPixel(5, 6, "standard_plate"),
                    PlacedPixel(6, 6, "standard_plate")]
        ok, msg = mgr.can_place_shape(_shape_2x2(), 5, 5, _mat_standard(), existing)
        assert not ok
        assert "Overlap" in msg

    def test_place_shape_fails_beyond_canvas(self) -> None:
        mgr = ShipGridManager("medium")  # 32x32
        ok, msg = mgr.can_place_shape(_shape_2x2(), 31, 31, _mat_standard(), [])
        assert not ok
        assert "beyond canvas" in msg

    def test_place_shape_fails_negative_coords(self) -> None:
        mgr = ShipGridManager("medium")
        ok, msg = mgr.can_place_shape(_shape_2x2(), -1, 0, _mat_standard(), [])
        assert not ok

    def test_place_shape_fails_weight_exceeded(self) -> None:
        mgr = ShipGridManager("tiny")  # max_weight=40
        mat = _mat_heavy()  # weight 1.2 per pixel
        # Fill with enough weight to nearly max out
        existing = [PlacedPixel(i, 0, "heavy_armor") for i in range(16)]
        # 16 pixels * 1.2 weight = 19.2 weight. Adding 4 more = 24 total, still under 40.
        # Let's make it closer: fill 30 pixels = 36 weight
        existing = [PlacedPixel(i % 16, i // 16, "heavy_armor") for i in range(33)]
        # 33 * 1.2 = 39.6. Adding 4 pixels * 1.2 = 4.8 → 44.4 > 40
        ok, msg = mgr.can_place_shape(_shape_2x2(), 0, 3, mat, existing)
        assert not ok
        assert "weight" in msg.lower()

    def test_canvas_size(self) -> None:
        assert ShipGridManager("tiny").get_canvas_w() == 16
        assert ShipGridManager("medium").get_canvas_w() == 40
        assert ShipGridManager("xlarge").get_canvas_w() == 72


class TestSlotPlacement:
    """Slot designation validation."""

    def _filled_area(self, x: int, y: int, size: int) -> list[PlacedPixel]:
        """Create a filled area of pixels."""
        return [
            PlacedPixel(x + dx, y + dy, "standard_plate")
            for dy in range(size) for dx in range(size)
        ]

    def test_slot_succeeds_on_filled_area(self) -> None:
        mgr = ShipGridManager("medium")
        pixels = self._filled_area(5, 5, 4)
        ok, msg = mgr.can_place_slot("weapon", 5, 5, pixels, [])
        assert ok, msg

    def test_slot_fails_on_unfilled_area(self) -> None:
        mgr = ShipGridManager("medium")
        ok, msg = mgr.can_place_slot("weapon", 5, 5, [], [])
        assert not ok
        assert "filled pixels" in msg

    def test_slot_fails_on_overlap(self) -> None:
        mgr = ShipGridManager("medium")
        pixels = self._filled_area(5, 5, 6)
        existing_slot = DesignatedSlot(slot_type="weapon", x=5, y=5)
        ok, msg = mgr.can_place_slot("defense", 6, 6, pixels, [existing_slot])
        assert not ok
        assert "Overlaps" in msg

    def test_slot_fails_pool_exhausted(self) -> None:
        mgr = ShipGridManager("tiny")  # 1 weapon slot max
        pixels = self._filled_area(0, 0, 8)
        existing = [DesignatedSlot(slot_type="weapon", x=0, y=0)]
        ok, msg = mgr.can_place_slot("weapon", 4, 0, pixels, existing)
        assert not ok
        assert "remaining" in msg

    def test_engine_slot_fails_not_in_rear(self) -> None:
        mgr = ShipGridManager("medium")  # 32x32, rear = y >= 24
        pixels = self._filled_area(5, 5, 4)
        ok, msg = mgr.can_place_slot("engine", 5, 5, pixels, [])
        assert not ok
        assert "rear" in msg

    def test_engine_slot_succeeds_in_rear(self) -> None:
        mgr = ShipGridManager("medium")  # rear threshold at y=24
        pixels = self._filled_area(5, 24, 4)
        ok, msg = mgr.can_place_slot("engine", 5, 24, pixels, [])
        assert ok, msg

    def test_is_area_filled(self) -> None:
        mgr = ShipGridManager("medium")
        pixels = self._filled_area(0, 0, 3)
        assert mgr.is_area_filled(0, 0, 2, pixels)
        assert not mgr.is_area_filled(2, 2, 2, pixels)


# ============================================================================
# Stats Computation Tests
# ============================================================================


class TestShipStatsComputer:
    """Stat derivation from builds."""

    def test_hull_from_pixels(self) -> None:
        """Hull = sum of material hull_per_pixel."""
        build = ShipBuild(weight_class="medium")
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 0, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.hull == 25, f"10 pixels * 2.5 hull/px = 25, got {stats.hull}"

    def test_weight_ratio(self) -> None:
        """Weight ratio = current / max."""
        build = ShipBuild(weight_class="tiny")  # max_weight=40
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 0, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        # 10 * 0.7 weight = 7.0, ratio = 7/40 = 0.175
        assert abs(stats.weight_ratio - 0.175) < 0.01
        assert stats.weight_label == "ULTRALIGHT"

    def test_weight_modifier_ultralight(self) -> None:
        """ULTRALIGHT (0-40%): +15% evasion."""
        build = ShipBuild(weight_class="medium")
        # Add light alloy pixels for evasion
        for i in range(50):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "light_alloy"))
        stats = ShipStatsComputer.compute(build, _materials())
        # 50 * 0.08 evasion/px = 4 base evasion
        # 50 * 0.4 weight/px = 20 weight / 140 max = 14.3% → ULTRALIGHT
        # Evasion = 4 * 1.15 = 4.6 → 4 (int)
        assert stats.weight_label == "ULTRALIGHT"

    def test_weight_modifier_heavy(self) -> None:
        """HEAVY (80-95%): -10% evasion."""
        build = ShipBuild(weight_class="tiny")  # max_weight=40
        # Need ~85% weight → 34 weight
        # Heavy armor: 1.2 weight/px → 28 pixels = 33.6 weight = 84%
        for i in range(28):
            build.pixels.append(PlacedPixel(i % 16, i // 16, "heavy_armor"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.weight_label == "HEAVY", f"Expected HEAVY, got {stats.weight_label} ({stats.weight_ratio:.2f})"

    def test_identity_juggernaut(self) -> None:
        """35%+ heavy_armor pixels → Juggernaut identity."""
        build = ShipBuild(weight_class="medium")
        # 40 heavy_armor + 20 standard = 60 total, 40/60 = 67% heavy_armor
        for i in range(40):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "heavy_armor"))
        for i in range(20):
            build.pixels.append(PlacedPixel((i + 10) % 32, 2, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "juggernaut"

    def test_identity_sentinel(self) -> None:
        """35%+ shield_crystal pixels → Sentinel identity."""
        build = ShipBuild(weight_class="medium")
        for i in range(40):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "shield_crystal"))
        for i in range(20):
            build.pixels.append(PlacedPixel((i + 10) % 32, 2, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "sentinel"

    def test_identity_ghost(self) -> None:
        """35%+ light_alloy pixels → Ghost identity."""
        build = ShipBuild(weight_class="medium")
        for i in range(40):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "light_alloy"))
        for i in range(20):
            build.pixels.append(PlacedPixel((i + 10) % 32, 2, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "ghost"

    def test_identity_none_below_threshold(self) -> None:
        """No identity when no material reaches 35%."""
        build = ShipBuild(weight_class="medium")
        # Equal split: 20 each of 3 types = none reaches 35% of 60
        for i in range(20):
            build.pixels.append(PlacedPixel(i, 0, "heavy_armor"))
        for i in range(20):
            build.pixels.append(PlacedPixel(i, 1, "shield_crystal"))
        for i in range(20):
            build.pixels.append(PlacedPixel(i, 2, "light_alloy"))
        stats = ShipStatsComputer.compute(build, _materials())
        # 20/60 = 33.3% each → below 35% threshold
        assert stats.defensive_identity is None

    def test_identity_highest_wins(self) -> None:
        """When multiple cross threshold, highest ratio wins."""
        build = ShipBuild(weight_class="medium")
        # 25 heavy + 22 shield + 10 standard = 57 total
        # heavy: 25/57 = 43.9%, shield: 22/57 = 38.6%
        for i in range(25):
            build.pixels.append(PlacedPixel(i, 0, "heavy_armor"))
        for i in range(22):
            build.pixels.append(PlacedPixel(i, 1, "shield_crystal"))
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 2, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "juggernaut"

    def test_empty_build_zero_stats(self) -> None:
        """Empty build produces all-zero stats."""
        build = ShipBuild(weight_class="medium")
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.hull == 0
        assert stats.shields == 0
        assert stats.evasion == 0
        assert stats.weight_current == 0.0
        assert stats.defensive_identity is None

    def test_total_cost_computed(self) -> None:
        """Total cost includes material pixels and slot designation costs."""
        build = ShipBuild(weight_class="medium")
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 0, "standard_plate"))
        build.slots.append(DesignatedSlot(slot_type="weapon", x=0, y=0))
        stats = ShipStatsComputer.compute(build, _materials())
        # 10 pixels * 15 cost/px + 1 weapon slot * 3000 = 3150
        assert stats.total_cost == 3150


# ============================================================================
# Serialization Tests
# ============================================================================


class TestSerialization:
    """Round-trip serialization for all data types."""

    def test_ship_build_round_trip(self) -> None:
        build = ShipBuild(
            weight_class="medium",
            pixels=[PlacedPixel(5, 5, "standard_plate"), PlacedPixel(6, 5, "heavy_armor")],
            slots=[DesignatedSlot(slot_type="weapon", x=5, y=5, equipment_id="laser_cannon", mark=2)],
            preset_name="My Ship",
        )
        data = build.to_dict()
        restored = ShipBuild.from_dict(data)
        assert restored.weight_class == build.weight_class
        assert len(restored.pixels) == 2
        assert restored.pixels[0].x == 5
        assert restored.pixels[1].material_id == "heavy_armor"
        assert len(restored.slots) == 1
        assert restored.slots[0].equipment_id == "laser_cannon"
        assert restored.slots[0].mark == 2
        assert restored.preset_name == "My Ship"

    def test_material_round_trip(self) -> None:
        mat = _mat_heavy()
        data = mat.to_dict()
        restored = HullMaterial.from_dict(data)
        assert restored.id == mat.id
        assert restored.hull_per_pixel == mat.hull_per_pixel
        assert restored.weight_per_pixel == mat.weight_per_pixel
        assert restored.color_primary == mat.color_primary

    def test_designated_slot_round_trip(self) -> None:
        slot = DesignatedSlot(
            slot_type="core", x=10, y=10,
            equipment_id="power_core_t2", mark=3, tuning="overclocked",
        )
        data = slot.to_dict()
        restored = DesignatedSlot.from_dict(data)
        assert restored.slot_type == "core"
        assert restored.size == 3
        assert restored.equipment_id == "power_core_t2"
        assert restored.tuning == "overclocked"


# ============================================================================
# Weight Class Constants Tests
# ============================================================================


class TestWeightClassConstants:
    """Verify weight class data integrity."""

    def test_five_weight_classes(self) -> None:
        assert len(WEIGHT_CLASSES) == 5

    def test_all_have_required_fields(self) -> None:
        for wc_id, wc in WEIGHT_CLASSES.items():
            assert "canvas_w" in wc, f"{wc_id} missing canvas_w"
            assert "canvas_h" in wc, f"{wc_id} missing canvas_h"
            assert "max_weight" in wc, f"{wc_id} missing max_weight"
            assert "max_slots" in wc, f"{wc_id} missing max_slots"
            assert "unlock_cost" in wc, f"{wc_id} missing unlock_cost"

    def test_canvas_sizes_ascending(self) -> None:
        widths = [WEIGHT_CLASSES[k]["canvas_w"] for k in ["tiny", "small", "medium", "large", "xlarge"]]
        assert widths == sorted(widths)
        heights = [WEIGHT_CLASSES[k]["canvas_h"] for k in ["tiny", "small", "medium", "large", "xlarge"]]
        assert heights == sorted(heights)

    def test_slot_pools_match_weight_classes(self) -> None:
        for wc_id in WEIGHT_CLASSES:
            assert wc_id in SLOT_POOLS, f"{wc_id} missing from SLOT_POOLS"

    def test_tiny_is_free(self) -> None:
        assert WEIGHT_CLASSES["tiny"]["unlock_cost"] == 0
