"""Tests for resolution configuration and font scaling."""

import spacegame.config as config
from spacegame.config import scale_x, scale_y
from spacegame.engine.fonts import (
    FONT_XS,
    FONT_SM,
    FONT_MD,
    FONT_BODY,
    FONT_LG,
    FONT_SUBTITLE,
    FONT_XL,
    FONT_HEADING,
    FONT_TITLE,
    FONT_SECTION,
    FONT_DISPLAY,
    FONT_RATING,
    scaled_font_size,
)


class TestResolutionConfig:
    """Tests for resolution infrastructure."""

    def test_supported_resolutions_exist(self) -> None:
        """SUPPORTED_RESOLUTIONS contains expected entries."""
        assert len(config.SUPPORTED_RESOLUTIONS) >= 3
        assert (1280, 720) in config.SUPPORTED_RESOLUTIONS
        assert (1920, 1080) in config.SUPPORTED_RESOLUTIONS

    def test_default_resolution_is_720p(self) -> None:
        """Default resolution should be 1280x720."""
        assert config.DEFAULT_RESOLUTION == (1280, 720)

    def test_set_resolution_updates_globals(self) -> None:
        """set_resolution() updates WINDOW_WIDTH and WINDOW_HEIGHT."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1920, 1080)
            assert config.WINDOW_WIDTH == 1920
            assert config.WINDOW_HEIGHT == 1080
        finally:
            config.set_resolution(original_w, original_h)

    def test_set_resolution_restores(self) -> None:
        """Verify resolution is restored after test."""
        # This test verifies cleanup worked in the previous test
        assert config.WINDOW_WIDTH == config.DEFAULT_RESOLUTION[0]
        assert config.WINDOW_HEIGHT == config.DEFAULT_RESOLUTION[1]

    def test_all_supported_resolutions_are_16_9(self) -> None:
        """All supported resolutions should be 16:9 aspect ratio."""
        for w, h in config.SUPPORTED_RESOLUTIONS:
            ratio = w / h
            assert abs(ratio - 16 / 9) < 0.01, f"Resolution {w}x{h} is not 16:9 (ratio={ratio:.3f})"


class TestScaleHelpers:
    """Tests for scale_x / scale_y resolution helpers."""

    def test_scale_x_identity_at_720p(self) -> None:
        """At 1280x720, scale_x returns the input unchanged."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1280, 720)
            assert scale_x(220) == 220
            assert scale_x(800) == 800
            assert scale_x(10) == 10
        finally:
            config.set_resolution(original_w, original_h)

    def test_scale_y_identity_at_720p(self) -> None:
        """At 1280x720, scale_y returns the input unchanged."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1280, 720)
            assert scale_y(55) == 55
            assert scale_y(460) == 460
        finally:
            config.set_resolution(original_w, original_h)

    def test_scale_x_at_1080p(self) -> None:
        """At 1920x1080, scale_x returns 1.5x the input."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1920, 1080)
            assert scale_x(220) == 330
            assert scale_x(800) == 1200
        finally:
            config.set_resolution(original_w, original_h)

    def test_scale_y_at_1080p(self) -> None:
        """At 1920x1080, scale_y returns 1.5x the input."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1920, 1080)
            assert scale_y(55) == 82  # round(55 * 1.5) = 82
            assert scale_y(460) == 690
        finally:
            config.set_resolution(original_w, original_h)

    def test_scale_at_900p(self) -> None:
        """At 1600x900, scale returns 1.25x the input."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1600, 900)
            assert scale_x(1280) == 1600
            assert scale_y(720) == 900
        finally:
            config.set_resolution(original_w, original_h)


class TestFontScaling:
    """Tests for resolution-aware font scaling."""

    def test_font_constants_ordered(self) -> None:
        """Semantic font constants should be in ascending order."""
        sizes = [
            FONT_XS,
            FONT_SM,
            FONT_MD,
            FONT_BODY,
            FONT_LG,
            FONT_SUBTITLE,
            FONT_XL,
            FONT_HEADING,
            FONT_TITLE,
            FONT_SECTION,
            FONT_DISPLAY,
            FONT_RATING,
        ]
        for i in range(len(sizes) - 1):
            assert sizes[i] < sizes[i + 1], f"Font sizes out of order: {sizes[i]} >= {sizes[i + 1]}"

    def test_scaled_font_size_at_720p(self) -> None:
        """At 720p, scaled size should equal base size."""
        original_h = config.WINDOW_HEIGHT
        try:
            config.set_resolution(1280, 720)
            assert scaled_font_size(24) == 24
            assert scaled_font_size(16) == 16
            assert scaled_font_size(72) == 72
        finally:
            config.set_resolution(config.DEFAULT_RESOLUTION[0], original_h)

    def test_scaled_font_size_at_1080p(self) -> None:
        """At 1080p, scaled size should be 1.5x base size."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1920, 1080)
            assert scaled_font_size(24) == 36  # 24 * 1.5
            assert scaled_font_size(16) == 24  # 16 * 1.5
            assert scaled_font_size(20) == 30  # 20 * 1.5
        finally:
            config.set_resolution(original_w, original_h)

    def test_scaled_font_size_minimum(self) -> None:
        """Scaled font size should never be below 10."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1280, 720)
            assert scaled_font_size(5) == 10  # Clamped to minimum
        finally:
            config.set_resolution(original_w, original_h)


class TestResolutionConsistency:
    """Tests that layout arithmetic stays consistent across resolutions."""

    def test_scale_helpers_identity_at_base(self) -> None:
        """At 720p, scale helpers return input unchanged."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            config.set_resolution(1280, 720)
            assert scale_x(100) == 100
            assert scale_y(100) == 100
        finally:
            config.set_resolution(original_w, original_h)

    def test_scale_helpers_proportional_at_all_resolutions(self) -> None:
        """Verify scale helpers produce proportional results at each supported resolution."""
        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            for w, h in config.SUPPORTED_RESOLUTIONS:
                config.set_resolution(w, h)
                # A full-width value should scale to the full window width
                assert scale_x(1280) == w, f"scale_x(1280) at {w}x{h}"
                assert scale_y(720) == h, f"scale_y(720) at {w}x{h}"
                # Margins should scale proportionally
                margin = scale_x(10)
                assert margin >= 10, f"Margin too small at {w}x{h}: {margin}"
        finally:
            config.set_resolution(original_w, original_h)

    def test_res_scale_at_all_resolutions(self) -> None:
        """Verify sprite res_scale produces valid integers at all resolutions."""
        from spacegame.engine.sprites import res_scale

        original_w, original_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        try:
            for w, h in config.SUPPORTED_RESOLUTIONS:
                config.set_resolution(w, h)
                for base in [1, 2, 3]:
                    result = res_scale(base)
                    assert isinstance(result, int), (
                        f"res_scale({base}) at {w}x{h} returned {type(result)}"
                    )
                    assert result >= base, (
                        f"res_scale({base}) at {w}x{h} = {result}, should be >= {base}"
                    )
        finally:
            config.set_resolution(original_w, original_h)

    def test_dialogue_portrait_size_scales(self) -> None:
        """DIALOGUE_PORTRAIT_SIZE should be proportional to resolution."""
        # At default 720p, should be (100, 120)
        assert config.DIALOGUE_PORTRAIT_SIZE == (100, 120)
