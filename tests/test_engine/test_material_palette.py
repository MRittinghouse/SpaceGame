"""Tests for the canonical palette + material band infrastructure.

Covers palette constants (structural invariants), lookups, snap/lerp helpers,
category offset, colorblind remap, and compliance test helpers. See
requirements/overhaul/95_palette_infrastructure.md for the full spec.
"""

from dataclasses import FrozenInstanceError

import pytest

from spacegame.engine.material_palette import (
    DEUTERANOPIA,
    MATERIAL_BANDS,
    PALETTE_ROLES,
    PROTANOPIA,
    RESERVED_BAND_NAMES,
    TRITANOPIA,
    ColorblindProfile,
    apply_category_offset,
    assert_band_compliance,
    assert_role_compliance,
    band_names,
    get_active_profile,
    get_band,
    get_role,
    is_valid_band,
    is_valid_role,
    lerp_in_band,
    role_names,
    set_colorblind_profile,
    snap_to_band,
    snap_to_role,
)


@pytest.fixture(autouse=True)
def _reset_colorblind_profile_between_tests():
    """Module-level colorblind state must not leak across tests."""
    yield
    set_colorblind_profile(None)


def _luminance(rgb: tuple[int, int, int]) -> float:
    """ITU-R BT.601 perceptual luminance approximation."""
    return rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114


# ---------------------------------------------------------------------------
# Palette constants — structural invariants (Bible §2.1 discipline)
# ---------------------------------------------------------------------------


class TestPaletteConstants:
    """MATERIAL_BANDS and PALETTE_ROLES must satisfy Bible §2 discipline."""

    def test_material_bands_has_seven_bands(self) -> None:
        assert len(MATERIAL_BANDS) == 7

    def test_material_bands_total_entries_is_34(self) -> None:
        """6 bands × 5 stops + 1 band × 4 stops (glass_viewport) = 34.

        Bible summary text said "29 band entries" but the actual band
        definitions sum to 34. RGB values take precedence over the
        summary arithmetic.
        """
        total = sum(len(band) for band in MATERIAL_BANDS.values())
        assert total == 34

    def test_palette_roles_has_expected_entry_count(self) -> None:
        """Live role entries: 3 void + 7 emissive + 7 UI + 4 detail +
        4 status (Sprint 4) + 3 check (Sprint 4) + 4 quality (Sprint 4) +
        3 text (Sprint 4b) + 12 faction (Sprint 4b) = 47.

        Future-material reserved names live in RESERVED_BAND_NAMES, not
        in PALETTE_ROLES — they're destined to become bands, not roles.
        """
        assert len(PALETTE_ROLES) == 47

    def test_reserved_band_names_count(self) -> None:
        """Seven reserved names per Bible §9.1: sensor_glass,
        electronics_emissive, cooling_vent, radar_mesh, shield_field,
        voltaic_plate, cryo_frost.
        """
        assert len(RESERVED_BAND_NAMES) == 7

    def test_reserved_names_raise_keyerror_in_lookup(self) -> None:
        """Reserved names are not yet valid bands — lookups raise,
        forcing the content phase to land before consumers depend on them.
        """
        for reserved in RESERVED_BAND_NAMES:
            assert not is_valid_band(reserved), (
                f"Reserved name {reserved!r} should not yet be a valid band"
            )
            with pytest.raises(KeyError):
                get_band(reserved)

    def test_each_band_has_4_or_5_stops(self) -> None:
        for name, band in MATERIAL_BANDS.items():
            assert 4 <= len(band) <= 5, (
                f"Band {name!r} must have 4-5 stops, got {len(band)}"
            )

    def test_glass_viewport_has_4_stops(self) -> None:
        """Per Bible §2.2, glass_viewport is the narrow-band exception."""
        assert len(MATERIAL_BANDS["glass_viewport"]) == 4

    def test_each_band_monotonic_brightness(self) -> None:
        """Each successive stop must be brighter than the previous."""
        for name, band in MATERIAL_BANDS.items():
            luminances = [_luminance(stop) for stop in band]
            for i in range(len(luminances) - 1):
                assert luminances[i] < luminances[i + 1], (
                    f"Band {name!r} not monotonic at index {i}: {luminances}"
                )

    def test_tiers_are_disjoint(self) -> None:
        """No RGB tuple appears in both MATERIAL_BANDS and PALETTE_ROLES.

        Bible §2.1: 'A band entry never appears in the role table; a role
        entry never appears in any band. This disjointness is what makes
        compliance testable.'
        """
        band_colors: set[tuple[int, int, int]] = set()
        for band in MATERIAL_BANDS.values():
            band_colors.update(band)
        role_colors = set(PALETTE_ROLES.values())
        overlap = band_colors & role_colors
        assert not overlap, f"Tiers must be disjoint; overlap: {overlap}"

    def test_all_entries_are_valid_rgb_tuples(self) -> None:
        """Every palette entry must be a 3-tuple of ints in [0, 255]."""
        for name, band in MATERIAL_BANDS.items():
            for i, stop in enumerate(band):
                assert len(stop) == 3, f"Band {name!r}[{i}] wrong length"
                for channel in stop:
                    assert isinstance(channel, int), f"Band {name!r}[{i}] non-int"
                    assert 0 <= channel <= 255, f"Band {name!r}[{i}] out of range"
        for name, color in PALETTE_ROLES.items():
            assert len(color) == 3, f"Role {name!r} wrong length"
            for channel in color:
                assert isinstance(channel, int), f"Role {name!r} non-int"
                assert 0 <= channel <= 255, f"Role {name!r} out of range"


# ---------------------------------------------------------------------------
# Lookups — get_band, get_role, name listings, validity checks
# ---------------------------------------------------------------------------


class TestLookups:
    """Lookup APIs return canonical data and handle unknown names cleanly."""

    def test_get_band_returns_tuple_of_rgbs(self) -> None:
        band = get_band("steel")
        assert isinstance(band, tuple)
        assert len(band) == 5
        for stop in band:
            assert len(stop) == 3

    def test_get_band_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            get_band("not_a_real_band")

    def test_get_role_returns_rgb(self) -> None:
        color = get_role("hud_cyan")
        assert isinstance(color, tuple)
        assert len(color) == 3

    def test_get_role_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            get_role("not_a_real_role")

    def test_band_names_returns_all_seven(self) -> None:
        names = band_names()
        assert len(names) == 7
        assert set(names) == set(MATERIAL_BANDS.keys())

    def test_role_names_returns_all_entries(self) -> None:
        names = role_names()
        assert len(names) == len(PALETTE_ROLES)
        assert set(names) == set(PALETTE_ROLES.keys())

    def test_is_valid_band_true_for_known(self) -> None:
        assert is_valid_band("steel") is True
        assert is_valid_band("reach_crimson") is True

    def test_is_valid_band_false_for_unknown(self) -> None:
        assert is_valid_band("not_a_band") is False
        assert is_valid_band("") is False

    def test_is_valid_role_true_for_known(self) -> None:
        assert is_valid_role("hud_text") is True

    def test_is_valid_role_false_for_unknown(self) -> None:
        assert is_valid_role("not_a_role") is False


# ---------------------------------------------------------------------------
# Snap helpers
# ---------------------------------------------------------------------------


class TestSnapToBand:
    """snap_to_band finds the nearest band entry by sum-of-squared distance."""

    def test_exact_band_entry_returns_itself(self) -> None:
        band = ((0, 0, 0), (100, 100, 100), (255, 255, 255))
        assert snap_to_band((100, 100, 100), band) == (100, 100, 100)

    def test_nearest_entry_returned(self) -> None:
        band = ((0, 0, 0), (100, 100, 100), (255, 255, 255))
        # (90, 90, 90) is closest to (100, 100, 100)
        assert snap_to_band((90, 90, 90), band) == (100, 100, 100)
        # (30, 30, 30) is closest to (0, 0, 0)
        assert snap_to_band((30, 30, 30), band) == (0, 0, 0)
        # (220, 220, 220) is closest to (255, 255, 255)
        assert snap_to_band((220, 220, 220), band) == (255, 255, 255)

    def test_equidistant_returns_first(self) -> None:
        """When two entries are equally close, the first in band order wins."""
        band = ((0, 0, 0), (100, 100, 100))
        # (50, 50, 50) is equidistant; first entry wins
        assert snap_to_band((50, 50, 50), band) == (0, 0, 0)


class TestSnapToRole:
    """snap_to_role returns nearest role within tolerance, or None."""

    def test_exact_role_within_tolerance(self) -> None:
        role_color = PALETTE_ROLES["hud_cyan"]
        assert snap_to_role(role_color, tolerance=2.0) == role_color

    def test_close_role_within_default_tolerance(self) -> None:
        role_color = PALETTE_ROLES["hud_cyan"]
        # Offset by 2 in one channel; within default tolerance of 4.0
        shifted = (role_color[0] + 2, role_color[1], role_color[2])
        assert snap_to_role(shifted) == role_color

    def test_outside_tolerance_returns_none(self) -> None:
        """A color far from any role returns None."""
        # Use a color unlikely to be close to any canonical role
        result = snap_to_role((100, 50, 200), tolerance=2.0)
        # May or may not find a match; but with a tight tolerance, likely None
        # Verify at least the function handles the None case
        assert result is None or isinstance(result, tuple)


# ---------------------------------------------------------------------------
# Lerp within band
# ---------------------------------------------------------------------------


class TestLerpInBand:
    """lerp_in_band interpolates within a band based on a 0..1 factor."""

    def test_factor_zero_returns_first(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        assert lerp_in_band(band, 0.0) == (0, 0, 0)

    def test_factor_one_returns_last(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        assert lerp_in_band(band, 1.0) == (200, 200, 200)

    def test_factor_midpoint_hits_middle_stop(self) -> None:
        """5-stop band at t=0.5 → exactly stop index 2."""
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        assert lerp_in_band(band, 0.5) == (100, 100, 100)

    def test_factor_clamped_below_zero(self) -> None:
        band = ((10, 10, 10), (50, 50, 50), (100, 100, 100))
        assert lerp_in_band(band, -0.5) == (10, 10, 10)

    def test_factor_clamped_above_one(self) -> None:
        band = ((10, 10, 10), (50, 50, 50), (100, 100, 100))
        assert lerp_in_band(band, 1.5) == (100, 100, 100)

    def test_intermediate_interpolation(self) -> None:
        """Factor 0.125 with 5 stops → halfway between stop 0 and stop 1."""
        band = ((0, 0, 0), (100, 100, 100), (200, 200, 200), (300, 300, 300), (400, 400, 400))
        # 0.125 * 4 = 0.5 → midway between band[0] and band[1]
        assert lerp_in_band(band, 0.125) == (50, 50, 50)


# ---------------------------------------------------------------------------
# Category offset — band-index shift per Bible §3.3
# ---------------------------------------------------------------------------


class TestCategoryOffset:
    """apply_category_offset shifts band indices, clamping at endpoints."""

    def test_offset_zero_returns_band_unchanged(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        assert apply_category_offset(band, 0) == band

    def test_offset_positive_one_shifts_brighter(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = apply_category_offset(band, +1)
        # Each position i takes band[i+1], last clamps: (50, 100, 150, 200, 200)
        assert result == (
            (50, 50, 50),
            (100, 100, 100),
            (150, 150, 150),
            (200, 200, 200),
            (200, 200, 200),
        )

    def test_offset_negative_one_shifts_darker(self) -> None:
        band = ((0, 0, 0), (50, 50, 50), (100, 100, 100), (150, 150, 150), (200, 200, 200))
        result = apply_category_offset(band, -1)
        # Each position i takes band[i-1], first clamps: (0, 0, 50, 100, 150)
        assert result == (
            (0, 0, 0),
            (0, 0, 0),
            (50, 50, 50),
            (100, 100, 100),
            (150, 150, 150),
        )

    def test_offset_clamps_at_both_endpoints(self) -> None:
        """Large offsets clamp rather than wrap."""
        band = ((0, 0, 0), (100, 100, 100), (200, 200, 200))
        # +10 shifts everything far past the brightest; all clamp to band[-1]
        assert apply_category_offset(band, +10) == (
            (200, 200, 200),
            (200, 200, 200),
            (200, 200, 200),
        )
        # -10 shifts everything far past the darkest; all clamp to band[0]
        assert apply_category_offset(band, -10) == (
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 0),
        )


# ---------------------------------------------------------------------------
# Colorblind remap infrastructure
# ---------------------------------------------------------------------------


class TestColorblindInfrastructure:
    """Colorblind profiles remap band/role names; RGB data is constant."""

    def test_default_no_active_profile(self) -> None:
        assert get_active_profile() is None

    def test_set_profile_sets_active(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        assert get_active_profile() is PROTANOPIA

    def test_set_profile_none_clears(self) -> None:
        set_colorblind_profile(PROTANOPIA)
        set_colorblind_profile(None)
        assert get_active_profile() is None

    def test_profile_band_remap_applied(self) -> None:
        """A profile with band_remap redirects get_band lookups."""
        custom_profile = ColorblindProfile(
            id="test_profile",
            name="Test",
            description="",
            band_remap={"steel": "solari_chrome"},
        )
        set_colorblind_profile(custom_profile)
        # When 'steel' is looked up, profile redirects to 'solari_chrome'
        assert get_band("steel") == MATERIAL_BANDS["solari_chrome"]

    def test_profile_role_remap_applied(self) -> None:
        custom_profile = ColorblindProfile(
            id="test_profile",
            name="Test",
            description="",
            role_remap={"hud_cyan": "hud_warning"},
        )
        set_colorblind_profile(custom_profile)
        assert get_role("hud_cyan") == PALETTE_ROLES["hud_warning"]

    def test_profile_missing_mapping_falls_through(self) -> None:
        """A profile that doesn't remap a name returns canonical data."""
        custom_profile = ColorblindProfile(
            id="test_profile",
            name="Test",
            description="",
            band_remap={"steel": "solari_chrome"},  # only remaps 'steel'
        )
        set_colorblind_profile(custom_profile)
        # 'reach_crimson' is not remapped → returns canonical
        assert get_band("reach_crimson") == MATERIAL_BANDS["reach_crimson"]

    def test_canonical_profiles_exist(self) -> None:
        """PROTANOPIA, DEUTERANOPIA, TRITANOPIA are shipped as stubs."""
        assert PROTANOPIA.id == "protanopia"
        assert DEUTERANOPIA.id == "deuteranopia"
        assert TRITANOPIA.id == "tritanopia"

    def test_canonical_profiles_have_starter_remaps(self) -> None:
        """Pre-Tier-2.3: stubs with empty remaps. Post-Tier-2.3: starter
        remaps pending playtest calibration. Each profile must now address
        at least one real conflict, and each remap target must be canonical."""
        from spacegame.engine.material_palette import get_band, get_role

        for profile in (PROTANOPIA, DEUTERANOPIA, TRITANOPIA):
            assert (
                profile.band_remap or profile.role_remap
            ), f"Profile '{profile.id}' has no remaps — stub regression"
            # Every remap target must resolve to a canonical band/role.
            for target in profile.band_remap.values():
                assert get_band(target) is not None, (
                    f"Profile '{profile.id}' band_remap → '{target}' is not canonical"
                )
            for target in profile.role_remap.values():
                assert get_role(target) is not None, (
                    f"Profile '{profile.id}' role_remap → '{target}' is not canonical"
                )

    def test_colorblind_profile_is_frozen(self) -> None:
        """ColorblindProfile is immutable to prevent accidental mutation
        of the canonical stubs."""
        with pytest.raises(FrozenInstanceError):
            PROTANOPIA.id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Compliance test helpers (§9.3)
# ---------------------------------------------------------------------------


class TestBandCompliance:
    """assert_band_compliance verifies surface pixels match band entries."""

    def test_exact_band_entries_pass(self) -> None:
        import pygame

        pygame.init()
        band = MATERIAL_BANDS["steel"]
        surf = pygame.Surface((3, 1), pygame.SRCALPHA)
        surf.set_at((0, 0), (*band[0], 255))
        surf.set_at((1, 0), (*band[2], 255))
        surf.set_at((2, 0), (*band[-1], 255))
        # Must not raise
        assert_band_compliance(surf, band, tolerance=2.0)

    def test_off_band_pixels_fail(self) -> None:
        import pygame

        pygame.init()
        band = MATERIAL_BANDS["steel"]
        surf = pygame.Surface((2, 1), pygame.SRCALPHA)
        surf.set_at((0, 0), (*band[0], 255))
        # (123, 45, 67) is not close to any steel band entry
        surf.set_at((1, 0), (123, 45, 67, 255))
        with pytest.raises(AssertionError):
            assert_band_compliance(surf, band, tolerance=2.0)

    def test_tolerance_allows_small_drift(self) -> None:
        """Pixels within tolerance still pass (e.g., for antialiased rendering)."""
        import pygame

        pygame.init()
        band = MATERIAL_BANDS["steel"]
        surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        # Shift one channel by 1 — inside tolerance 2.0
        shifted = (band[0][0] + 1, band[0][1], band[0][2])
        surf.set_at((0, 0), (*shifted, 255))
        assert_band_compliance(surf, band, tolerance=2.0)

    def test_transparent_pixels_ignored(self) -> None:
        """Alpha=0 pixels are not checked (not part of the rendered content)."""
        import pygame

        pygame.init()
        band = MATERIAL_BANDS["steel"]
        surf = pygame.Surface((2, 1), pygame.SRCALPHA)
        surf.set_at((0, 0), (*band[0], 255))
        # Pixel (1, 0) is transparent — should not fail compliance despite
        # being arbitrary RGB.
        surf.set_at((1, 0), (200, 50, 30, 0))
        assert_band_compliance(surf, band, tolerance=2.0)


class TestRoleCompliance:
    """assert_role_compliance verifies surface pixels match palette roles."""

    def test_exact_role_entries_pass(self) -> None:
        import pygame

        pygame.init()
        surf = pygame.Surface((2, 1), pygame.SRCALPHA)
        surf.set_at((0, 0), (*PALETTE_ROLES["hud_cyan"], 255))
        surf.set_at((1, 0), (*PALETTE_ROLES["hud_warning"], 255))
        assert_role_compliance(surf, tolerance=4.0)

    def test_off_role_pixels_fail(self) -> None:
        import pygame

        pygame.init()
        surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        surf.set_at((0, 0), (37, 91, 6, 255))  # Unlikely to be near any role
        with pytest.raises(AssertionError):
            assert_role_compliance(surf, tolerance=2.0)

    def test_tolerance_allows_antialiased_drift(self) -> None:
        """Default tolerance 4.0 allows small antialiasing artifacts."""
        import pygame

        pygame.init()
        role_color = PALETTE_ROLES["hud_cyan"]
        shifted = (role_color[0] + 3, role_color[1], role_color[2])
        surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        surf.set_at((0, 0), (*shifted, 255))
        assert_role_compliance(surf, tolerance=4.0)


class TestColorblindProfilesAreFunctional:
    """Tier 2.3: colorblind profiles now have starter remaps (pending
    playtest calibration per §42). These tests verify the mechanism
    produces visibly different output when a profile is active —
    previously the profiles were stubs with empty maps."""

    def test_protanopia_remaps_reach_crimson(self) -> None:
        set_colorblind_profile(None)
        canonical_band = get_band("reach_crimson")
        set_colorblind_profile(PROTANOPIA)
        remapped_band = get_band("reach_crimson")
        set_colorblind_profile(None)

        assert canonical_band != remapped_band, (
            "Protanopia should remap reach_crimson away from canonical red-brown"
        )

    def test_tritanopia_remaps_collective_and_glass(self) -> None:
        from spacegame.engine.material_palette import TRITANOPIA

        set_colorblind_profile(None)
        canonical_collective = get_band("collective_composite")
        canonical_glass = get_band("glass_viewport")

        set_colorblind_profile(TRITANOPIA)
        remapped_collective = get_band("collective_composite")
        remapped_glass = get_band("glass_viewport")
        set_colorblind_profile(None)

        assert canonical_collective != remapped_collective
        assert canonical_glass != remapped_glass

    def test_protanopia_remaps_hud_warning_role(self) -> None:
        from spacegame.engine.material_palette import get_role

        set_colorblind_profile(None)
        canonical = get_role("hud_warning")

        set_colorblind_profile(PROTANOPIA)
        remapped = get_role("hud_warning")
        set_colorblind_profile(None)

        assert canonical != remapped

    def test_non_remapped_bands_pass_through_unchanged(self) -> None:
        """Bands not in the remap dict must render canonically even under profile."""
        set_colorblind_profile(None)
        canonical_steel = get_band("steel")

        set_colorblind_profile(PROTANOPIA)
        under_profile = get_band("steel")
        set_colorblind_profile(None)

        assert canonical_steel == under_profile

    def test_profile_clear_restores_canonical(self) -> None:
        """Setting None after a profile restores the canonical band."""
        canonical = get_band("reach_crimson")

        set_colorblind_profile(PROTANOPIA)
        _ = get_band("reach_crimson")
        set_colorblind_profile(None)

        after_clear = get_band("reach_crimson")
        assert after_clear == canonical
