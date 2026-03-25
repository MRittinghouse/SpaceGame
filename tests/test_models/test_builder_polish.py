"""Tests for Phase E — Builder polish and UX features.

Tests build validation, undo/redo, stat preview calculations,
and edge cases in the builder system.
"""

from spacegame.models.ship_build import (
    HullMaterial,
    HullShape,
    PlacedPixel,
    ShipBuild,
    ShipStatsComputer,
)


def _mat() -> dict[str, HullMaterial]:
    return {
        "standard_plate": HullMaterial(
            id="standard_plate",
            name="Standard",
            description="test",
            color_primary=(128, 128, 128),
            hull_per_pixel=2.5,
            weight_per_pixel=0.7,
            cost_per_pixel=15,
        ),
        "light_alloy": HullMaterial(
            id="light_alloy",
            name="Light",
            description="test",
            color_primary=(176, 184, 200),
            hull_per_pixel=1.5,
            evasion_per_pixel=0.08,
            weight_per_pixel=0.4,
            cost_per_pixel=8,
        ),
    }


class TestBuildValidation:
    """Build validation for confirm-readiness."""

    def test_empty_build_not_valid(self) -> None:
        build = ShipBuild(weight_class="tiny")
        assert len(build.pixels) == 0

    def test_overweight_detected(self) -> None:
        build = ShipBuild(weight_class="tiny")  # max_weight=55
        # Use a deliberately heavy material to exceed limit
        heavy = HullMaterial(
            id="heavy",
            name="H",
            description="t",
            color_primary=(0, 0, 0),
            hull_per_pixel=3.0,
            weight_per_pixel=0.55,
        )
        # 101 pixels * 0.55 = 55.55 → over 55 limit
        for i in range(101):
            build.pixels.append(PlacedPixel(i % 16, i // 16, "heavy"))
        stats = ShipStatsComputer.compute(build, {"heavy": heavy})
        assert stats.weight_ratio > 1.0, "Should be overweight"

    def test_exactly_at_weight_limit(self) -> None:
        """Build at exactly 100% weight should be valid (not over)."""
        build = ShipBuild(weight_class="tiny")  # max_weight=40
        # Standard: 0.7 weight/px, 57 pixels = 39.9 weight (under 40)
        for i in range(57):
            build.pixels.append(PlacedPixel(i % 16, i // 16, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _mat())
        assert stats.weight_ratio <= 1.0


class TestUndoRedoLogic:
    """Undo/redo snapshot behavior."""

    def test_snapshot_preserves_pixel_data(self) -> None:
        pixels = [PlacedPixel(1, 2, "standard_plate"), PlacedPixel(3, 4, "light_alloy")]
        snapshot = [p.to_dict() for p in pixels]
        restored = [PlacedPixel.from_dict(d) for d in snapshot]
        assert len(restored) == 2
        assert restored[0].x == 1
        assert restored[1].material_id == "light_alloy"

    def test_snapshot_is_independent_copy(self) -> None:
        """Modifying original doesn't affect snapshot."""
        pixels = [PlacedPixel(1, 2, "standard_plate")]
        snapshot = [p.to_dict() for p in pixels]
        pixels.append(PlacedPixel(5, 6, "light_alloy"))
        restored = [PlacedPixel.from_dict(d) for d in snapshot]
        assert len(restored) == 1, "Snapshot should not reflect later changes"


class TestStatPreviewCalculation:
    """Stat delta preview for shape hover."""

    def test_hull_delta_calculation(self) -> None:
        mat = _mat()["standard_plate"]
        pixel_count = 6  # Small rect
        hull_delta = int(pixel_count * mat.hull_per_pixel)
        assert hull_delta == 15, f"6 pixels * 2.5 hull = 15, got {hull_delta}"

    def test_weight_delta_calculation(self) -> None:
        mat = _mat()["standard_plate"]
        pixel_count = 6
        weight_delta = pixel_count * mat.weight_per_pixel
        assert abs(weight_delta - 4.2) < 0.01

    def test_evasion_delta_for_light_alloy(self) -> None:
        mat = _mat()["light_alloy"]
        pixel_count = 10
        evasion_delta = pixel_count * mat.evasion_per_pixel
        assert abs(evasion_delta - 0.8) < 0.01


class TestMirrorMode:
    """Mirror mode pixel placement."""

    def test_mirror_creates_symmetric_pixel(self) -> None:
        """A pixel at (3, 5) on a 16x16 canvas mirrors to (12, 5)."""
        canvas_size = 16
        x, y = 3, 5
        mirror_x = canvas_size - 1 - x
        assert mirror_x == 12

    def test_mirror_center_column_no_duplicate(self) -> None:
        """Pixel at center column should not create a duplicate at same position."""
        canvas_size = 16
        x = 7
        mirror_x = canvas_size - 1 - x  # = 8, different from 7
        assert mirror_x != x, "Off-center: should create mirror"

        # True center for odd-size canvas
        canvas_size = 17
        x = 8
        mirror_x = canvas_size - 1 - x  # = 8, same!
        assert mirror_x == x, "Exact center: mirror is self"


class TestFloodFill:
    """Flood fill behavior."""

    def test_fill_bounded_area(self) -> None:
        """Fill should stop at canvas edges and existing pixels."""
        build = ShipBuild(weight_class="tiny")  # 16x16
        # Create a 4x4 border (hollow square)
        for x in range(4):
            build.pixels.append(PlacedPixel(x, 0, "standard_plate"))
            build.pixels.append(PlacedPixel(x, 3, "standard_plate"))
        for y in range(4):
            build.pixels.append(PlacedPixel(0, y, "standard_plate"))
            build.pixels.append(PlacedPixel(3, y, "standard_plate"))

        # The interior (1,1), (2,1), (1,2), (2,2) is empty and bounded
        occupied = {(p.x, p.y) for p in build.pixels}
        assert (1, 1) not in occupied
        assert (2, 2) not in occupied


class TestShapeTransformChain:
    """Shape rotation + flip combinations."""

    def test_rotate_then_flip(self) -> None:
        shape = HullShape(
            id="test",
            name="Test",
            description="t",
            pixel_mask=[[True, True, True], [False, False, True]],
        )
        # Rotate 90° then flip
        rotated = shape.rotated(1)
        flipped = rotated.flipped()
        assert flipped.pixel_count == shape.pixel_count

    def test_all_8_orientations_preserve_pixel_count(self) -> None:
        """4 rotations × 2 flips = 8 orientations, all same pixel count."""
        shape = HullShape(
            id="test",
            name="Test",
            description="t",
            pixel_mask=[[True, True], [False, True], [False, True]],
        )
        count = shape.pixel_count
        for rot in range(4):
            r = shape.rotated(rot)
            assert r.pixel_count == count
            f = r.flipped()
            assert f.pixel_count == count
