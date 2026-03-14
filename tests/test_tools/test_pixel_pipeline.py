"""Tests for the pixel art asset processing pipeline.

Covers downscaling, palette quantization, alpha cleanup,
outline enforcement, sprite sheet packing, palette swapping,
and the high-quality sprite processing pipeline.
"""

import pytest
from PIL import Image

from tools.pixel_pipeline import (
    resize_nearest,
    quantize_to_palette,
    clean_alpha,
    enforce_outline,
    pack_sheet,
    unpack_sheet,
    palette_swap,
    resize_for_pixel_art,
    process_sprite,
)


# ============================================================================
# Resize (Nearest Neighbor)
# ============================================================================


class TestResizeNearest:
    """Resize images using nearest-neighbor interpolation (no anti-aliasing)."""

    def test_downscale_to_target(self) -> None:
        """Downscales to exact target dimensions."""
        img = Image.new("RGBA", (128, 128), (255, 0, 0, 255))
        result = resize_nearest(img, (32, 32))
        assert result.size == (32, 32)

    def test_upscale(self) -> None:
        """Upscales to target dimensions."""
        img = Image.new("RGBA", (16, 16), (0, 255, 0, 255))
        result = resize_nearest(img, (64, 64))
        assert result.size == (64, 64)

    def test_preserves_hard_edges(self) -> None:
        """Nearest-neighbor preserves pixel boundaries (no blending)."""
        # 2x2 checkerboard
        img = Image.new("RGBA", (2, 2))
        img.putpixel((0, 0), (255, 0, 0, 255))
        img.putpixel((1, 0), (0, 0, 255, 255))
        img.putpixel((0, 1), (0, 255, 0, 255))
        img.putpixel((1, 1), (255, 255, 0, 255))

        result = resize_nearest(img, (4, 4))

        # Each pixel should be doubled, no blending
        assert result.getpixel((0, 0)) == (255, 0, 0, 255)
        assert result.getpixel((1, 1)) == (255, 0, 0, 255)
        assert result.getpixel((2, 0)) == (0, 0, 255, 255)
        assert result.getpixel((3, 1)) == (0, 0, 255, 255)

    def test_non_square_dimensions(self) -> None:
        """Handles non-square target sizes (50x60 portraits)."""
        img = Image.new("RGBA", (200, 240), (100, 100, 100, 255))
        result = resize_nearest(img, (50, 60))
        assert result.size == (50, 60)

    def test_preserves_alpha(self) -> None:
        """Transparent pixels stay transparent after resize."""
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        # Fill top-left quadrant so downscale reliably keeps some opaque
        for x in range(2):
            for y in range(2):
                img.putpixel((x, y), (255, 0, 0, 255))

        result = resize_nearest(img, (2, 2))
        pixels = [result.getpixel((x, y)) for x in range(2) for y in range(2)]
        assert any(p[3] == 255 for p in pixels)
        assert any(p[3] == 0 for p in pixels)


# ============================================================================
# Palette Quantization
# ============================================================================


class TestQuantizeToPalette:
    """Map every pixel to the nearest color in a defined palette."""

    def test_exact_colors_unchanged(self) -> None:
        """Pixels that are already palette colors stay unchanged."""
        palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        img = Image.new("RGBA", (3, 1))
        img.putpixel((0, 0), (255, 0, 0, 255))
        img.putpixel((1, 0), (0, 255, 0, 255))
        img.putpixel((2, 0), (0, 0, 255, 255))

        result = quantize_to_palette(img, palette)
        assert result.getpixel((0, 0))[:3] == (255, 0, 0)
        assert result.getpixel((1, 0))[:3] == (0, 255, 0)
        assert result.getpixel((2, 0))[:3] == (0, 0, 255)

    def test_off_colors_mapped_to_nearest(self) -> None:
        """Non-palette colors map to nearest palette color."""
        palette = [(255, 0, 0), (0, 0, 255)]
        img = Image.new("RGBA", (1, 1), (200, 10, 10, 255))  # Near red

        result = quantize_to_palette(img, palette)
        assert result.getpixel((0, 0))[:3] == (255, 0, 0)

    def test_transparent_pixels_stay_transparent(self) -> None:
        """Pixels with alpha=0 are not quantized."""
        palette = [(255, 0, 0)]
        img = Image.new("RGBA", (2, 1))
        img.putpixel((0, 0), (0, 255, 0, 0))  # Transparent green
        img.putpixel((1, 0), (0, 255, 0, 255))  # Opaque green

        result = quantize_to_palette(img, palette)
        assert result.getpixel((0, 0))[3] == 0  # Still transparent
        assert result.getpixel((1, 0))[:3] == (255, 0, 0)  # Mapped to red

    def test_all_output_colors_in_palette(self) -> None:
        """Every opaque pixel in output uses a palette color."""
        palette = [(0, 0, 0), (128, 128, 128), (255, 255, 255)]
        img = Image.new("RGBA", (10, 10), (100, 150, 200, 255))

        result = quantize_to_palette(img, palette)
        for x in range(10):
            for y in range(10):
                pixel = result.getpixel((x, y))
                if pixel[3] > 0:
                    assert pixel[:3] in palette

    def test_empty_palette_raises(self) -> None:
        img = Image.new("RGBA", (1, 1), (100, 100, 100, 255))
        with pytest.raises(ValueError):
            quantize_to_palette(img, [])


# ============================================================================
# Alpha Cleanup
# ============================================================================


class TestCleanAlpha:
    """Enforce binary alpha: fully opaque or fully transparent."""

    def test_low_alpha_becomes_transparent(self) -> None:
        """Alpha < threshold becomes 0."""
        img = Image.new("RGBA", (1, 1), (255, 0, 0, 50))
        result = clean_alpha(img, threshold=128)
        assert result.getpixel((0, 0))[3] == 0

    def test_high_alpha_becomes_opaque(self) -> None:
        """Alpha >= threshold becomes 255."""
        img = Image.new("RGBA", (1, 1), (255, 0, 0, 200))
        result = clean_alpha(img, threshold=128)
        assert result.getpixel((0, 0))[3] == 255

    def test_exact_threshold_is_opaque(self) -> None:
        """Alpha equal to threshold becomes opaque."""
        img = Image.new("RGBA", (1, 1), (255, 0, 0, 128))
        result = clean_alpha(img, threshold=128)
        assert result.getpixel((0, 0))[3] == 255

    def test_already_binary_unchanged(self) -> None:
        """Already-binary alpha (0 or 255) passes through."""
        img = Image.new("RGBA", (2, 1))
        img.putpixel((0, 0), (255, 0, 0, 0))
        img.putpixel((1, 0), (255, 0, 0, 255))

        result = clean_alpha(img)
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((1, 0))[3] == 255

    def test_color_channels_preserved(self) -> None:
        """RGB values are not modified by alpha cleanup."""
        img = Image.new("RGBA", (1, 1), (42, 84, 126, 200))
        result = clean_alpha(img)
        r, g, b, a = result.getpixel((0, 0))
        assert (r, g, b) == (42, 84, 126)
        assert a == 255


# ============================================================================
# Outline Enforcement
# ============================================================================


class TestEnforceOutline:
    """Add 1px dark outline around non-transparent pixels."""

    def test_outline_added_around_opaque_region(self) -> None:
        """Transparent pixels adjacent to opaque ones get outline color."""
        img = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        # Place a single opaque pixel in the center
        img.putpixel((2, 2), (255, 0, 0, 255))

        outline_color = (20, 22, 30)
        result = enforce_outline(img, outline_color)

        # The 4 cardinal neighbors should have the outline color
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            px = result.getpixel((2 + dx, 2 + dy))
            assert px[:3] == outline_color
            assert px[3] == 255

    def test_original_pixels_preserved(self) -> None:
        """Opaque pixels in the original are not overwritten."""
        img = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        img.putpixel((2, 2), (255, 0, 0, 255))

        result = enforce_outline(img, (20, 22, 30))
        assert result.getpixel((2, 2))[:3] == (255, 0, 0)

    def test_no_outline_in_interior(self) -> None:
        """Interior pixels (surrounded by opaque) are not outlined."""
        img = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        # Fill a 3x3 block
        for x in range(1, 4):
            for y in range(1, 4):
                img.putpixel((x, y), (255, 0, 0, 255))

        result = enforce_outline(img, (20, 22, 30))
        # Center pixel (2,2) is surrounded — should stay original
        assert result.getpixel((2, 2))[:3] == (255, 0, 0)


# ============================================================================
# Sprite Sheet Packing
# ============================================================================


class TestPackSheet:
    """Pack multiple frame images into a horizontal strip."""

    def test_pack_produces_correct_width(self) -> None:
        """Output width = frame_width * frame_count."""
        frames = [
            Image.new("RGBA", (32, 32), (255, 0, 0, 255)),
            Image.new("RGBA", (32, 32), (0, 255, 0, 255)),
            Image.new("RGBA", (32, 32), (0, 0, 255, 255)),
        ]
        sheet = pack_sheet(frames)
        assert sheet.size == (96, 32)

    def test_pack_preserves_frame_content(self) -> None:
        """Each frame's content is at the correct position."""
        frames = [
            Image.new("RGBA", (16, 16), (255, 0, 0, 255)),
            Image.new("RGBA", (16, 16), (0, 255, 0, 255)),
        ]
        sheet = pack_sheet(frames)
        assert sheet.getpixel((0, 0))[:3] == (255, 0, 0)
        assert sheet.getpixel((16, 0))[:3] == (0, 255, 0)

    def test_pack_single_frame(self) -> None:
        """Single frame produces a sheet of the same size."""
        frame = Image.new("RGBA", (32, 32), (100, 100, 100, 255))
        sheet = pack_sheet([frame])
        assert sheet.size == (32, 32)

    def test_pack_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            pack_sheet([])


# ============================================================================
# Sprite Sheet Unpacking
# ============================================================================


class TestUnpackSheet:
    """Unpack a horizontal strip into individual frame images."""

    def test_round_trip(self) -> None:
        """pack then unpack produces original frames."""
        frames = [
            Image.new("RGBA", (16, 16), (255, 0, 0, 255)),
            Image.new("RGBA", (16, 16), (0, 255, 0, 255)),
            Image.new("RGBA", (16, 16), (0, 0, 255, 255)),
        ]
        sheet = pack_sheet(frames)
        unpacked = unpack_sheet(sheet, frame_width=16)

        assert len(unpacked) == 3
        assert unpacked[0].getpixel((0, 0))[:3] == (255, 0, 0)
        assert unpacked[1].getpixel((0, 0))[:3] == (0, 255, 0)
        assert unpacked[2].getpixel((0, 0))[:3] == (0, 0, 255)


# ============================================================================
# Palette Swap
# ============================================================================


class TestPaletteSwap:
    """Recolor a sprite by mapping source palette colors to target palette."""

    def test_basic_swap(self) -> None:
        """Red pixels become blue when palette maps red->blue."""
        source_palette = [(255, 0, 0), (0, 255, 0)]
        target_palette = [(0, 0, 255), (255, 255, 0)]

        img = Image.new("RGBA", (2, 1))
        img.putpixel((0, 0), (255, 0, 0, 255))
        img.putpixel((1, 0), (0, 255, 0, 255))

        result = palette_swap(img, source_palette, target_palette)
        assert result.getpixel((0, 0))[:3] == (0, 0, 255)
        assert result.getpixel((1, 0))[:3] == (255, 255, 0)

    def test_transparent_unaffected(self) -> None:
        """Transparent pixels are not palette-swapped."""
        source_palette = [(255, 0, 0)]
        target_palette = [(0, 0, 255)]

        img = Image.new("RGBA", (1, 1), (255, 0, 0, 0))
        result = palette_swap(img, source_palette, target_palette)
        assert result.getpixel((0, 0))[3] == 0

    def test_unmapped_colors_use_nearest(self) -> None:
        """Colors not exactly in source palette map to nearest source, then swap."""
        source_palette = [(255, 0, 0), (0, 0, 255)]
        target_palette = [(0, 255, 0), (255, 255, 0)]

        img = Image.new("RGBA", (1, 1), (240, 10, 10, 255))  # Near red
        result = palette_swap(img, source_palette, target_palette)
        # Should map to source[0] (red) → target[0] (green)
        assert result.getpixel((0, 0))[:3] == (0, 255, 0)

    def test_palettes_must_be_same_length(self) -> None:
        with pytest.raises(ValueError):
            palette_swap(
                Image.new("RGBA", (1, 1)),
                [(255, 0, 0)],
                [(0, 0, 255), (0, 255, 0)],
            )


# ============================================================================
# Resize For Pixel Art (Two-Stage Averaging)
# ============================================================================


class TestResizeForPixelArt:
    """Two-stage downscale: LANCZOS averaging → nearest-neighbor crispness."""

    def test_output_has_correct_dimensions(self) -> None:
        """Result matches the requested target size."""
        img = Image.new("RGBA", (256, 256), (100, 150, 200, 255))
        result = resize_for_pixel_art(img, (32, 32))
        assert result.size == (32, 32)

    def test_non_square_dimensions(self) -> None:
        """Works for non-square targets like portraits (50x60)."""
        img = Image.new("RGBA", (200, 240), (100, 100, 100, 255))
        result = resize_for_pixel_art(img, (50, 60))
        assert result.size == (50, 60)

    def test_intermediate_scale_1_uses_single_lanczos(self) -> None:
        """With intermediate_scale=1, falls back to direct LANCZOS."""
        img = Image.new("RGBA", (128, 128), (80, 120, 200, 255))
        result = resize_for_pixel_art(img, (32, 32), intermediate_scale=1)
        assert result.size == (32, 32)

    def test_preserves_transparency(self) -> None:
        """Transparent regions remain transparent after resize."""
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        # Fill center quadrant opaque
        for x in range(32, 96):
            for y in range(32, 96):
                img.putpixel((x, y), (255, 0, 0, 255))

        result = resize_for_pixel_art(img, (32, 32))
        # Corners should be transparent
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((31, 31))[3] == 0
        # Center should be opaque
        assert result.getpixel((16, 16))[3] > 0

    def test_small_source_skips_intermediate(self) -> None:
        """Source smaller than intermediate target uses direct LANCZOS."""
        img = Image.new("RGBA", (48, 48), (200, 100, 50, 255))
        result = resize_for_pixel_art(img, (32, 32), intermediate_scale=2)
        assert result.size == (32, 32)

    def test_averaging_preserves_dominant_color(self) -> None:
        """Area averaging captures the dominant color of large regions.

        A mostly-red image downscaled should produce reddish pixels, not
        random samples that could land on a stray non-red pixel.
        """
        img = Image.new("RGBA", (128, 128), (200, 30, 30, 255))
        # Scatter a few blue pixels (minority)
        for x in range(0, 128, 16):
            img.putpixel((x, 0), (30, 30, 200, 255))

        result = resize_for_pixel_art(img, (8, 8))
        # Most pixels should be reddish (R > B)
        red_dominant = 0
        for x in range(8):
            for y in range(8):
                r, g, b, a = result.getpixel((x, y))
                if r > b:
                    red_dominant += 1
        assert red_dominant >= 60, f"Expected mostly red but got {red_dominant}/64"

    def test_no_dark_halo_on_edges(self) -> None:
        """Premultiplied alpha prevents dark fringing at transparent edges.

        A bright sprite on a transparent background should not develop
        darkened edge pixels from averaging with (0,0,0,0) neighbors.
        """
        # Bright circle on transparent background
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        # Fill a centered 64x64 block with bright yellow
        for x in range(32, 96):
            for y in range(32, 96):
                img.putpixel((x, y), (255, 255, 100, 255))

        result = resize_for_pixel_art(img, (32, 32))

        # Sample edge pixels that ended up opaque — they should still be bright,
        # not darkened by blending with (0,0,0,0)
        edge_dark_count = 0
        for x in range(32):
            for y in range(32):
                r, g, b, a = result.getpixel((x, y))
                if a > 0 and (r + g + b) < 150:
                    edge_dark_count += 1

        assert edge_dark_count == 0, (
            f"{edge_dark_count} opaque pixels are unexpectedly dark (dark halo)"
        )

    def test_large_downscale_not_muddy(self) -> None:
        """16x reduction still produces distinct regions, not uniform mud.

        A 512px image with four colored quadrants should still show color
        variation after downscaling to 32px.
        """
        img = Image.new("RGBA", (512, 512))
        # Four colored quadrants
        colors = [
            (255, 0, 0, 255),    # top-left: red
            (0, 0, 255, 255),    # top-right: blue
            (0, 255, 0, 255),    # bottom-left: green
            (255, 255, 0, 255),  # bottom-right: yellow
        ]
        for x in range(512):
            for y in range(512):
                qi = (1 if x >= 256 else 0) + (2 if y >= 256 else 0)
                img.putpixel((x, y), colors[qi])

        result = resize_for_pixel_art(img, (32, 32))

        # Sample center of each quadrant — should match the original quadrant color closely
        tl = result.getpixel((8, 8))
        tr = result.getpixel((24, 8))
        bl = result.getpixel((8, 24))
        br = result.getpixel((24, 24))

        assert tl[0] > 200 and tl[2] < 50, f"Top-left should be red: {tl}"
        assert tr[2] > 200 and tr[0] < 50, f"Top-right should be blue: {tr}"
        assert bl[1] > 200 and bl[0] < 50, f"Bottom-left should be green: {bl}"
        assert br[0] > 200 and br[1] > 200, f"Bottom-right should be yellow: {br}"


# ============================================================================
# Full Sprite Processing Pipeline
# ============================================================================


class TestProcessSprite:
    """End-to-end sprite pipeline: remove bg, resize, quantize, outline."""

    def _make_test_image(self, size: int = 256) -> Image.Image:
        """Create a test image simulating AI output: colored subject on green bg."""
        img = Image.new("RGBA", (size, size), (0, 220, 0, 255))  # Green background
        # Draw a centered "subject" in warm tones
        margin = size // 4
        for x in range(margin, size - margin):
            for y in range(margin, size - margin):
                img.putpixel((x, y), (180, 80, 40, 255))
        return img

    def test_output_has_correct_dimensions(self) -> None:
        """Pipeline produces sprite at the requested target size."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20), (220, 120, 60)]
        result = process_sprite(img, (32, 32), palette)
        assert result.size == (32, 32)

    def test_all_opaque_pixels_are_palette_colors_or_outline(self) -> None:
        """Every opaque pixel is either a palette color or the outline color."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20), (220, 120, 60)]
        outline_color = (20, 15, 25)
        result = process_sprite(img, (32, 32), palette, outline_color=outline_color)

        allowed_colors = set(palette) | {outline_color}
        for x in range(32):
            for y in range(32):
                r, g, b, a = result.getpixel((x, y))
                if a > 0:
                    assert (r, g, b) in allowed_colors, (
                        f"Pixel ({x},{y}) = ({r},{g},{b}) not in palette or outline"
                    )

    def test_alpha_is_binary(self) -> None:
        """Every pixel has alpha of exactly 0 or 255."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20)]
        result = process_sprite(img, (32, 32), palette)

        for x in range(32):
            for y in range(32):
                a = result.getpixel((x, y))[3]
                assert a in (0, 255), f"Pixel ({x},{y}) has non-binary alpha {a}"

    def test_has_transparent_background(self) -> None:
        """Green background is removed — corners should be transparent."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20)]
        result = process_sprite(img, (32, 32), palette)

        # Corners should be transparent (were green background)
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((31, 0))[3] == 0
        assert result.getpixel((0, 31))[3] == 0
        assert result.getpixel((31, 31))[3] == 0

    def test_has_opaque_center(self) -> None:
        """Subject in center survives the pipeline."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20)]
        result = process_sprite(img, (32, 32), palette)
        assert result.getpixel((16, 16))[3] == 255

    def test_has_outline_pixels(self) -> None:
        """Outline pixels exist at the border between subject and transparency."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20)]
        outline_color = (20, 15, 25)
        result = process_sprite(img, (32, 32), palette, outline_color=outline_color)

        # There should be at least some outline pixels
        outline_count = 0
        for x in range(32):
            for y in range(32):
                r, g, b, a = result.getpixel((x, y))
                if a > 0 and (r, g, b) == outline_color:
                    outline_count += 1

        assert outline_count > 0, "Expected outline pixels at subject boundary"

    def test_empty_palette_raises(self) -> None:
        """Empty palette raises ValueError."""
        img = self._make_test_image(64)
        with pytest.raises(ValueError):
            process_sprite(img, (32, 32), [])

    def test_converts_non_rgba_input(self) -> None:
        """RGB input is automatically converted to RGBA."""
        img = Image.new("RGB", (128, 128), (0, 220, 0))
        # Draw subject
        for x in range(32, 96):
            for y in range(32, 96):
                img.putpixel((x, y), (180, 80, 40))

        palette = [(180, 80, 40), (100, 50, 20)]
        result = process_sprite(img, (32, 32), palette)
        assert result.size == (32, 32)
        assert result.mode == "RGBA"

    def test_custom_intermediate_scale(self) -> None:
        """Higher intermediate_scale produces valid output."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20)]
        result = process_sprite(img, (32, 32), palette, intermediate_scale=3)
        assert result.size == (32, 32)

    def test_portrait_dimensions(self) -> None:
        """Works with non-square portrait sizes (50x60)."""
        img = Image.new("RGBA", (200, 240), (0, 220, 0, 255))
        for x in range(50, 150):
            for y in range(60, 180):
                img.putpixel((x, y), (140, 100, 80, 255))

        palette = [(140, 100, 80), (80, 60, 40), (200, 160, 120)]
        result = process_sprite(img, (50, 60), palette)
        assert result.size == (50, 60)

    def test_pipeline_quality_no_green_remnants(self) -> None:
        """No green pixels remain after background removal on green-screen source."""
        img = self._make_test_image(256)
        palette = [(180, 80, 40), (100, 50, 20), (220, 120, 60)]
        result = process_sprite(img, (32, 32), palette)

        for x in range(32):
            for y in range(32):
                r, g, b, a = result.getpixel((x, y))
                if a > 0:
                    # No pixel should be bright green (remnant background)
                    assert not (g > 150 and g > r + 50 and g > b + 50), (
                        f"Green remnant at ({x},{y}): ({r},{g},{b})"
                    )
