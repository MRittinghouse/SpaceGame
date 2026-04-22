"""Tests for Phase A1 — Ship Builder data models and computation.

Covers shape rotation, grid validation, stat computation, weight
modifiers, identity detection, and serialization.
"""

from spacegame.models.ship_build import (
    WEIGHT_CLASSES,
    HullMaterial,
    HullShape,
    PlacedPixel,
    ShipBuild,
    ShipGridManager,
    ShipStatsComputer,
)

# ============================================================================
# Helpers
# ============================================================================


def _shape_2x2() -> HullShape:
    """A simple 2x2 square shape."""
    return HullShape(
        id="square",
        name="Square",
        description="2x2 square",
        pixel_mask=[[True, True], [True, True]],
    )


def _shape_triangle() -> HullShape:
    """A right triangle (2x2, 3 pixels)."""
    return HullShape(
        id="triangle",
        name="Triangle",
        description="Right triangle",
        pixel_mask=[[True, True], [False, True]],
    )


def _shape_bar() -> HullShape:
    """A 3x1 horizontal bar."""
    return HullShape(
        id="bar",
        name="Bar",
        description="3x1 bar",
        pixel_mask=[[True, True, True]],
    )


def _mat_standard() -> HullMaterial:
    """Standard plate material."""
    return HullMaterial(
        id="standard_plate",
        name="Standard Plate",
        description="Balanced",
        shade_band="steel",
        hull_per_pixel=2.5,
        weight_per_pixel=0.25,
        cost_per_pixel=15,
    )


def _mat_heavy() -> HullMaterial:
    """Heavy armor material (juggernaut identity)."""
    return HullMaterial(
        id="heavy_armor",
        name="Heavy Armor",
        description="Tank",
        shade_band="union_ceramic",
        category_offset=1,
        hull_per_pixel=3.0,
        armor_per_pixel=0.06,
        weight_per_pixel=0.55,
        cost_per_pixel=25,
    )


def _mat_shield() -> HullMaterial:
    """Shield crystal material (sentinel identity)."""
    return HullMaterial(
        id="shield_crystal",
        name="Shield Crystal",
        description="Shields",
        shade_band="collective_composite",
        emissive_role="cryo_fractal",
        hull_per_pixel=1.0,
        shield_per_pixel=0.6,
        shield_regen_per_pixel=0.03,
        weight_per_pixel=0.6,
        cost_per_pixel=22,
    )


def _mat_light() -> HullMaterial:
    """Light alloy material (ghost identity)."""
    return HullMaterial(
        id="light_alloy",
        name="Light Alloy",
        description="Evasion",
        shade_band="steel",
        hull_per_pixel=1.5,
        evasion_per_pixel=0.08,
        weight_per_pixel=0.4,
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
        existing = [
            PlacedPixel(5, 5, "standard_plate"),
            PlacedPixel(6, 5, "standard_plate"),
            PlacedPixel(5, 6, "standard_plate"),
            PlacedPixel(6, 6, "standard_plate"),
        ]
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
        mgr = ShipGridManager("tiny")  # max_weight=55
        mat = _mat_heavy()  # weight 0.55 per pixel
        # Fill 96 pixels at 0.55 = 52.8 weight. Adding 4 more = 55 + 2.2 > 55
        existing = [PlacedPixel(i % 16, i // 16, "heavy_armor") for i in range(98)]
        # 98 * 0.55 = 53.9. Adding 4 * 0.55 = 2.2 → 56.1 > 55
        ok, msg = mgr.can_place_shape(
            _shape_2x2(), 14, 7, mat, existing, materials_catalog={"heavy_armor": mat}
        )
        assert not ok
        assert "weight" in msg.lower()

    def test_canvas_size(self) -> None:
        assert ShipGridManager("tiny").get_canvas_w() == 16
        assert ShipGridManager("medium").get_canvas_w() == 40
        assert ShipGridManager("xlarge").get_canvas_w() == 72


class TestAreaFilled:
    """Grid area fill checks (used by module placement)."""

    def test_is_area_filled(self) -> None:
        mgr = ShipGridManager("medium")
        pixels = [PlacedPixel(x, y, "standard_plate") for y in range(3) for x in range(3)]
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
        build = ShipBuild(weight_class="tiny")  # max_weight=55
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 0, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        # 10 * 0.25 weight = 2.5, ratio = 2.5/55 ≈ 0.045
        assert stats.weight_ratio < 0.10
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
        build = ShipBuild(weight_class="tiny")  # max_weight=55
        # Need ~85% weight → 46.75 weight
        # Heavy armor: 0.55 weight/px → 85 pixels = 46.75 weight = 85%
        for i in range(85):
            build.pixels.append(PlacedPixel(i % 16, i // 16, "heavy_armor"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.weight_label == "HEAVY", (
            f"Expected HEAVY, got {stats.weight_label} ({stats.weight_ratio:.2f})"
        )

    def test_identity_juggernaut(self) -> None:
        """35%+ heavy_armor ratio AND >=100 heavy pixels → Juggernaut identity.

        Sprint 5c playtest follow-up: juggernaut now additionally requires
        bulk (MIN_JUGGERNAUT_PIXELS=100). A small ship with high armor
        ratio but low absolute armor-pixel count does NOT qualify —
        juggernaut implies real mass, not just composition.
        """
        build = ShipBuild(weight_class="medium")
        # 110 heavy_armor + 40 standard = 150 total, 110/150 = 73% heavy_armor
        # and heavy_armor count (110) clears the MIN_JUGGERNAUT_PIXELS gate.
        for i in range(110):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "heavy_armor"))
        for i in range(40):
            build.pixels.append(PlacedPixel((i + 10) % 32, 5 + i // 32, "standard_plate"))
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
        """When multiple cross threshold (and size gates), highest ratio wins.

        Uses large pixel counts so both families clear their size gates;
        heavy_armor's higher ratio wins.
        """
        build = ShipBuild(weight_class="medium")
        # 110 heavy + 55 shield + 25 standard = 190 total
        # heavy: 110/190 = 57.9% (clears 35% and MIN_JUGGERNAUT_PIXELS=100)
        # shield: 55/190 = 28.9% (below 35%, so ratio-gate excludes)
        # heavy wins.
        for i in range(110):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "heavy_armor"))
        for i in range(55):
            build.pixels.append(PlacedPixel(i % 32, 5 + i // 32, "shield_crystal"))
        for i in range(25):
            build.pixels.append(PlacedPixel(i, 10, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "juggernaut"

    def test_tiny_shuttle_never_gets_juggernaut_identity(self) -> None:
        """Sprint 5c playtest regression: a 16x16 shuttle's worth of heavy
        armor must not be classified as JUGGERNAUT.

        Playtester report: a tiny scrapyard-build shuttle was being labeled
        JUGGERNAUT, which is thematically wrong — juggernaut implies bulk.
        Even at 100% heavy_armor composition, a ship under
        MIN_JUGGERNAUT_PIXELS (100) should not receive the identity.
        """
        build = ShipBuild(weight_class="light")
        # 40 heavy_armor pixels (representative of a small tutorial build).
        # Ratio is 100%, well above IDENTITY_THRESHOLD, but absolute count
        # is well below MIN_JUGGERNAUT_PIXELS.
        for i in range(40):
            build.pixels.append(PlacedPixel(i % 16, i // 16, "heavy_armor"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity is None, (
            f"Tiny shuttle with all-heavy-armor should not be a juggernaut. "
            f"Got: {stats.defensive_identity}"
        )

    def test_very_small_ship_gets_no_identity(self) -> None:
        """A build below MIN_IDENTITY_PIXELS (50) gets no identity regardless
        of material family.
        """
        build = ShipBuild(weight_class="light")
        # 30 shield crystal — 100% ratio but below MIN_IDENTITY_PIXELS.
        for i in range(30):
            build.pixels.append(PlacedPixel(i, 0, "shield_crystal"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity is None

    def test_small_sentinel_still_qualifies(self) -> None:
        """Sentinel has no bulk gate — a small shield-focused ship qualifies
        as long as it clears MIN_IDENTITY_PIXELS and the 35% ratio.
        """
        build = ShipBuild(weight_class="light")
        # 55 shield_crystal + 15 standard = 70 total.
        # ratio 78.6% (above 35%), total 70 (above MIN_IDENTITY_PIXELS=50).
        for i in range(55):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "shield_crystal"))
        for i in range(15):
            build.pixels.append(PlacedPixel(i, 3, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "sentinel"

    def test_small_ghost_still_qualifies(self) -> None:
        """Ghost has no bulk gate — a small stealth build qualifies.

        This matches the genre: scout shuttles, runners, and reconnaissance
        craft can legitimately carry a ghost (stealth) identity without
        needing the mass of a juggernaut.
        """
        build = ShipBuild(weight_class="light")
        # 60 light_alloy + 10 standard = 70 total.
        for i in range(60):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "light_alloy"))
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 3, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "ghost"

    def test_juggernaut_size_gate_boundary(self) -> None:
        """A build at exactly MIN_JUGGERNAUT_PIXELS qualifies; one below does not."""
        # Just above the threshold: 100 heavy armor + 20 standard = 120 total
        build = ShipBuild(weight_class="heavy")
        for i in range(100):
            build.pixels.append(PlacedPixel(i % 32, i // 32, "heavy_armor"))
        for i in range(20):
            build.pixels.append(PlacedPixel(i, 5, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        assert stats.defensive_identity == "juggernaut"

        # Just below: 99 heavy + 20 standard = 119 total.
        build2 = ShipBuild(weight_class="heavy")
        for i in range(99):
            build2.pixels.append(PlacedPixel(i % 32, i // 32, "heavy_armor"))
        for i in range(20):
            build2.pixels.append(PlacedPixel(i, 5, "standard_plate"))
        stats2 = ShipStatsComputer.compute(build2, _materials())
        assert stats2.defensive_identity is None

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
        """Total cost includes material pixels."""
        build = ShipBuild(weight_class="medium")
        for i in range(10):
            build.pixels.append(PlacedPixel(i, 0, "standard_plate"))
        stats = ShipStatsComputer.compute(build, _materials())
        # 10 pixels * 15 cost/px = 150
        assert stats.total_cost == 150


# ============================================================================
# Serialization Tests
# ============================================================================


class TestSerialization:
    """Round-trip serialization for all data types."""

    def test_ship_build_round_trip(self) -> None:
        from spacegame.models.ship_build import PlacedSlot

        build = ShipBuild(
            weight_class="medium",
            pixels=[PlacedPixel(5, 5, "standard_plate"), PlacedPixel(6, 5, "heavy_armor")],
            placed_slots=[PlacedSlot(slot_def_id="weapon_small", x=5, y=5)],
            preset_name="My Ship",
        )
        data = build.to_dict()
        restored = ShipBuild.from_dict(data)
        assert restored.weight_class == build.weight_class
        assert len(restored.pixels) == 2
        assert restored.pixels[0].x == 5
        assert restored.pixels[1].material_id == "heavy_armor"
        assert len(restored.placed_slots) == 1
        assert restored.placed_slots[0].slot_def_id == "weapon_small"
        assert restored.preset_name == "My Ship"

    def test_material_round_trip(self) -> None:
        mat = _mat_heavy()
        data = mat.to_dict()
        restored = HullMaterial.from_dict(data)
        assert restored.id == mat.id
        assert restored.hull_per_pixel == mat.hull_per_pixel
        assert restored.weight_per_pixel == mat.weight_per_pixel
        assert restored.shade_band == mat.shade_band
        assert restored.category_offset == mat.category_offset
        assert restored.color_primary == mat.color_primary


class TestHullMaterialBandSchema:
    """Verify the new palette-band schema drives HullMaterial visuals."""

    def test_shade_band_is_required(self) -> None:
        mat = HullMaterial(
            id="x",
            name="x",
            description="",
            shade_band="steel",
        )
        assert mat.shade_band == "steel"

    def test_color_properties_derive_from_band(self) -> None:
        from spacegame.engine.material_palette import get_band

        mat = HullMaterial(id="x", name="x", description="", shade_band="steel")
        steel = get_band("steel")
        midpoint = len(steel) // 2
        assert mat.color_primary == steel[midpoint]
        assert mat.color_accent == steel[midpoint - 1]
        assert mat.color_highlight == steel[midpoint + 1]

    def test_default_render_params(self) -> None:
        mat = HullMaterial(id="x", name="x", description="", shade_band="steel")
        assert mat.category_offset == 0
        assert mat.noise_intensity == 0.15
        assert mat.rivet_density == 40.0
        assert mat.wear_intensity == 0.10
        assert mat.gloss == 0.30
        assert mat.emissive_role is None
        assert mat.signature_stripe_role is None

    def test_emissive_role_stored(self) -> None:
        mat = HullMaterial(
            id="x",
            name="x",
            description="",
            shade_band="collective_composite",
            emissive_role="cryo_fractal",
        )
        assert mat.emissive_role == "cryo_fractal"

    def test_signature_stripe_role_stored(self) -> None:
        mat = HullMaterial(
            id="x",
            name="x",
            description="",
            shade_band="steel",
            signature_stripe_role="hud_accent_warm",
        )
        assert mat.signature_stripe_role == "hud_accent_warm"

    def test_from_dict_loads_new_schema(self) -> None:
        data = {
            "id": "m",
            "name": "Example",
            "description": "Test",
            "shade_band": "reach_crimson",
            "category_offset": -1,
            "noise_intensity": 0.22,
            "rivet_density": 55.0,
            "wear_intensity": 0.18,
            "gloss": 0.40,
            "emissive_role": "plasma_core",
            "signature_stripe_role": "hud_warning",
            "hull_per_pixel": 2.0,
        }
        mat = HullMaterial.from_dict(data)
        assert mat.shade_band == "reach_crimson"
        assert mat.category_offset == -1
        assert mat.noise_intensity == 0.22
        assert mat.rivet_density == 55.0
        assert mat.wear_intensity == 0.18
        assert mat.gloss == 0.40
        assert mat.emissive_role == "plasma_core"
        assert mat.signature_stripe_role == "hud_warning"
        assert mat.hull_per_pixel == 2.0

    def test_glass_viewport_band_derives_valid_colors(self) -> None:
        """Glass band has 4 stops; midpoint derivation must still work."""
        from spacegame.engine.material_palette import get_band

        mat = HullMaterial(id="x", name="x", description="", shade_band="glass_viewport")
        glass = get_band("glass_viewport")
        assert mat.color_primary in glass
        assert mat.color_accent in glass
        assert mat.color_highlight in glass

    def test_invalid_shade_band_falls_back_gracefully(self) -> None:
        """Unknown shade_band returns a safe placeholder, not a crash."""
        mat = HullMaterial(id="x", name="x", description="", shade_band="nonexistent_band")
        assert isinstance(mat.color_primary, tuple)
        assert len(mat.color_primary) == 3


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
        widths = [
            WEIGHT_CLASSES[k]["canvas_w"] for k in ["tiny", "small", "medium", "large", "xlarge"]
        ]
        assert widths == sorted(widths)
        heights = [
            WEIGHT_CLASSES[k]["canvas_h"] for k in ["tiny", "small", "medium", "large", "xlarge"]
        ]
        assert heights == sorted(heights)

    def test_tiny_is_free(self) -> None:
        assert WEIGHT_CLASSES["tiny"]["unlock_cost"] == 0
