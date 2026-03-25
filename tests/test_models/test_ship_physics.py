"""Tests for Phase 6 — Ship physics constraints and shape metrics.

Covers structural integrity (articulation point detection), center of mass,
hull efficiency (interior vs perimeter), and frontal profile computation.
"""

from spacegame.models.ship_physics import (
    compute_structural_integrity,
    compute_center_of_mass,
    compute_hull_efficiency,
    compute_frontal_profile,
    BalanceRating,
)
from spacegame.models.ship_build import PlacedPixel, HullMaterial, ShipBuild
from spacegame.models.ship_module import PlacedModule, ShipModule


# ============================================================================
# Helpers
# ============================================================================


def _pixels_from_coords(
    coords: list[tuple[int, int]], mat_id: str = "standard_plate"
) -> list[PlacedPixel]:
    return [PlacedPixel(x=x, y=y, material_id=mat_id) for x, y in coords]


def _mat(mat_id: str = "standard_plate", weight: float = 0.25) -> HullMaterial:
    return HullMaterial(
        id=mat_id,
        name="Test",
        description="",
        color_primary=(128, 128, 128),
        weight_per_pixel=weight,
    )


def _materials() -> dict[str, HullMaterial]:
    return {
        "standard_plate": _mat("standard_plate", 0.25),
        "heavy_armor": _mat("heavy_armor", 0.55),
        "light_alloy": _mat("light_alloy", 0.15),
        "m": _mat("m", 0.25),
    }


def _module(mid: str, weight: float = 2.0) -> ShipModule:
    return ShipModule(
        id=mid,
        name="Test",
        description="",
        category="structural",
        manufacturer="reyes_kowalski",
        pixel_grid=[["H", "H"], ["H", "H"]],
        material_map={"H": "m"},
        provides={},
        weight=weight,
        base_cost=0,
    )


# ============================================================================
# Structural Integrity — Articulation Points
# ============================================================================


class TestStructuralIntegrity:
    """Test articulation point detection and structural scoring."""

    def test_solid_rectangle_no_bottlenecks(self) -> None:
        """A solid 4x3 rectangle has no articulation points."""
        coords = [(x, y) for x in range(4) for y in range(3)]
        scores = compute_structural_integrity(coords)
        # All interior pixels should have score 0
        for (x, y), score in scores.items():
            assert score == 0.0, f"Pixel ({x},{y}) should have score 0 in solid rect, got {score}"

    def test_single_pixel_bridge(self) -> None:
        """Two blocks connected by a 1-pixel bridge form a bottleneck chain."""
        # Left block: 3x3 at (0,0)
        coords = [(x, y) for x in range(3) for y in range(3)]
        # Bridge pixel at (3, 1)
        coords.append((3, 1))
        # Right block: 3x3 starting at (4, 0)
        coords.extend([(x, y) for x in range(4, 7) for y in range(3)])
        scores = compute_structural_integrity(coords)
        # Bridge chain: (2,1)→(3,1)→(4,1) are all art points.
        # They form a cluster, so each scores 0.5 (not lone bottlenecks).
        assert scores[(3, 1)] > 0.0, f"Bridge pixel should be a bottleneck, got {scores[(3, 1)]}"
        assert scores[(3, 1)] == 0.5, "Bridge with adjacent art points scores 0.5"

    def test_two_pixel_bridge(self) -> None:
        """Two blocks connected by a 2-pixel wide bridge. Less critical than 1-pixel."""
        coords = [(x, y) for x in range(3) for y in range(3)]
        coords.append((3, 0))
        coords.append((3, 1))
        coords.extend([(x, y) for x in range(4, 7) for y in range(3)])
        scores = compute_structural_integrity(coords)
        # Bridge pixels should have moderate scores (not 1.0 because they're not single-point failures)
        assert scores[(3, 0)] < 1.0, "2-wide bridge pixel should not be critical"
        assert scores[(3, 1)] < 1.0

    def test_single_pixel_no_bottleneck(self) -> None:
        """A single pixel has no bottleneck (nothing to disconnect)."""
        scores = compute_structural_integrity([(5, 5)])
        assert scores[(5, 5)] == 0.0

    def test_line_of_pixels(self) -> None:
        """A straight line: interior pixels are articulation points.

        In a line, all interior art points are adjacent to other art points,
        forming a bridge cluster. They score 0.5 (less critical than a lone
        bottleneck) since removing one still leaves the others connecting.
        """
        coords = [(x, 0) for x in range(5)]
        scores = compute_structural_integrity(coords)
        # End pixels (0,0) and (4,0) are not articulation points
        assert scores[(0, 0)] == 0.0
        assert scores[(4, 0)] == 0.0
        # Interior pixels are art points, but adjacent to each other → 0.5
        assert scores[(1, 0)] > 0.0, "Line interior should be a bottleneck"
        assert scores[(2, 0)] > 0.0
        assert scores[(3, 0)] > 0.0
        assert scores[(1, 0)] <= 0.5, "Bridge cluster members should score 0.5"

    def test_empty_returns_empty(self) -> None:
        scores = compute_structural_integrity([])
        assert scores == {}


# ============================================================================
# Center of Mass
# ============================================================================


class TestCenterOfMass:
    """Test center of mass computation and balance rating."""

    def test_symmetric_build_centered(self) -> None:
        """A symmetric rectangle has CoM at geometric center."""
        build = ShipBuild(weight_class="tiny")
        # 4x4 solid block at (6, 6)
        for x in range(6, 10):
            for y in range(6, 10):
                build.pixels.append(PlacedPixel(x=x, y=y, material_id="standard_plate"))
        materials = _materials()
        com_x, com_y, offset_pct, rating = compute_center_of_mass(build, materials, {})
        assert abs(com_x - 7.5) < 0.1, f"CoM X should be ~7.5, got {com_x}"
        assert abs(com_y - 7.5) < 0.1, f"CoM Y should be ~7.5, got {com_y}"

    def test_offset_build_not_centered(self) -> None:
        """Heavy material on one side shifts CoM."""
        build = ShipBuild(weight_class="tiny")
        # Light pixels on left
        for x in range(0, 4):
            build.pixels.append(PlacedPixel(x=x, y=8, material_id="light_alloy"))
        # Heavy pixels on right
        for x in range(12, 16):
            build.pixels.append(PlacedPixel(x=x, y=8, material_id="heavy_armor"))
        materials = _materials()
        com_x, com_y, offset_pct, rating = compute_center_of_mass(build, materials, {})
        # CoM should be pulled toward heavy side (right, x > center)
        assert com_x > 8.0, f"CoM should be pulled right by heavy armor, got {com_x}"

    def test_balanced_rating(self) -> None:
        """Symmetric build should be rated Balanced."""
        build = ShipBuild(weight_class="tiny")
        for x in range(6, 10):
            for y in range(6, 10):
                build.pixels.append(PlacedPixel(x=x, y=y, material_id="standard_plate"))
        materials = _materials()
        _, _, offset_pct, rating = compute_center_of_mass(build, materials, {})
        assert rating == BalanceRating.BALANCED

    def test_empty_build(self) -> None:
        build = ShipBuild(weight_class="tiny")
        materials = _materials()
        com_x, com_y, offset_pct, rating = compute_center_of_mass(build, materials, {})
        assert offset_pct == 0.0
        assert rating == BalanceRating.BALANCED

    def test_modules_affect_com(self) -> None:
        """Modules should contribute to CoM based on their weight."""
        build = ShipBuild(weight_class="tiny")
        # Heavy module on the right
        build.modules = [PlacedModule(module_id="heavy_mod", x=12, y=7)]
        catalog = {"heavy_mod": _module("heavy_mod", weight=10.0)}
        materials = _materials()
        com_x, _, _, _ = compute_center_of_mass(build, materials, catalog)
        # CoM should be pulled right toward x=12-13
        assert com_x > 10.0, f"CoM should be pulled by heavy module, got {com_x}"


# ============================================================================
# Hull Efficiency
# ============================================================================


class TestHullEfficiency:
    """Test interior vs perimeter pixel classification."""

    def test_3x3_solid(self) -> None:
        """3x3 solid: 1 interior pixel (center), 8 perimeter."""
        coords = [(x, y) for x in range(3) for y in range(3)]
        interior, perimeter, ratio = compute_hull_efficiency(coords)
        assert interior == 1, f"3x3 has 1 interior pixel, got {interior}"
        assert perimeter == 8, f"3x3 has 8 perimeter pixels, got {perimeter}"
        assert abs(ratio - 1 / 9) < 0.01

    def test_4x4_solid(self) -> None:
        """4x4 solid: 4 interior, 12 perimeter."""
        coords = [(x, y) for x in range(4) for y in range(4)]
        interior, perimeter, ratio = compute_hull_efficiency(coords)
        assert interior == 4
        assert perimeter == 12
        assert abs(ratio - 4 / 16) < 0.01

    def test_line_all_perimeter(self) -> None:
        """A 1-pixel-wide line has 0 interior pixels."""
        coords = [(x, 0) for x in range(10)]
        interior, perimeter, ratio = compute_hull_efficiency(coords)
        assert interior == 0
        assert perimeter == 10
        assert ratio == 0.0

    def test_1x1_all_perimeter(self) -> None:
        """Single pixel is perimeter."""
        interior, perimeter, ratio = compute_hull_efficiency([(0, 0)])
        assert interior == 0
        assert perimeter == 1
        assert ratio == 0.0

    def test_empty(self) -> None:
        interior, perimeter, ratio = compute_hull_efficiency([])
        assert interior == 0
        assert perimeter == 0
        assert ratio == 0.0

    def test_large_solid_high_efficiency(self) -> None:
        """10x10 solid: 64 interior, 36 perimeter, ratio ~0.64."""
        coords = [(x, y) for x in range(10) for y in range(10)]
        interior, perimeter, ratio = compute_hull_efficiency(coords)
        assert interior == 64
        assert perimeter == 36
        assert abs(ratio - 0.64) < 0.01


# ============================================================================
# Frontal Profile
# ============================================================================


class TestFrontalProfile:
    """Test frontal cross-section computation."""

    def test_tall_ship_large_profile(self) -> None:
        """A tall, narrow ship has LARGE frontal profile (tall = easy to hit)."""
        # 2 wide, 10 tall — enemy sees the full 10-pixel height
        coords = [(x, y) for x in range(2) for y in range(10)]
        width, height, profile_ratio = compute_frontal_profile(coords, canvas_w=16)
        assert width == 2
        assert height == 10
        assert profile_ratio > 0.5  # 10/16 = 0.625

    def test_flat_ship_small_profile(self) -> None:
        """A wide, flat ship has SMALL frontal profile (flat = hard to hit)."""
        # 14 wide, 2 tall — enemy sees only the 2-pixel height
        coords = [(x, y) for x in range(14) for y in range(2)]
        width, height, profile_ratio = compute_frontal_profile(coords, canvas_w=16)
        assert width == 14
        assert height == 2
        assert profile_ratio < 0.2  # 2/16 = 0.125

    def test_square_ship(self) -> None:
        """A square ship has moderate frontal profile."""
        coords = [(x, y) for x in range(8) for y in range(8)]
        width, height, profile_ratio = compute_frontal_profile(coords, canvas_w=16)
        assert width == 8
        assert height == 8
        assert abs(profile_ratio - 0.5) < 0.01

    def test_empty(self) -> None:
        width, height, profile_ratio = compute_frontal_profile([], canvas_w=16)
        assert width == 0
        assert height == 0
        assert profile_ratio == 0.0
