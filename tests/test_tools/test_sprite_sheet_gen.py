"""Tests for the sprite sheet generator transforms."""

import pytest
from PIL import Image

from tools.sprite_sheet_gen import (
    engine_glow,
    breathe,
    blink,
    color_pulse,
    shimmer,
    make_sprite_sheet,
    generate_animation_config,
)


def _make_test_image(w: int, h: int, color: tuple = (100, 150, 200, 255)) -> Image.Image:
    """Create a solid test image."""
    img = Image.new("RGBA", (w, h), color)
    return img


def _make_ship_image() -> Image.Image:
    """Create a 32x32 test ship with an 'engine' area (bright bottom row)."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    px = img.load()
    # Ship body (blue-gray hull)
    for y in range(5, 28):
        for x in range(8, 24):
            px[x, y] = (60, 80, 120, 255)
    # Engine area (bright warm pixels at bottom)
    for x in range(10, 22):
        px[x, 28] = (200, 150, 80, 255)
        px[x, 29] = (255, 200, 100, 255)
        px[x, 30] = (255, 220, 120, 255)
    return img


def _make_portrait_image() -> Image.Image:
    """Create a 50x60 test portrait with a face region."""
    img = Image.new("RGBA", (50, 60), (0, 0, 0, 0))
    px = img.load()
    # Skin area (face)
    for y in range(10, 45):
        for x in range(10, 40):
            px[x, y] = (180, 140, 110, 255)
    # Eyes (dark pixels in upper-middle area)
    for x in range(18, 22):
        px[x, 22] = (40, 30, 25, 255)
    for x in range(28, 32):
        px[x, 22] = (40, 30, 25, 255)
    return img


class TestEngineGlow:
    """engine_glow creates frames with pulsing engine brightness."""

    def test_returns_correct_frame_count(self) -> None:
        ship = _make_ship_image()
        frames = engine_glow(ship, num_frames=2)
        assert len(frames) == 2

    def test_frames_are_same_size(self) -> None:
        ship = _make_ship_image()
        frames = engine_glow(ship, num_frames=3)
        for frame in frames:
            assert frame.size == ship.size

    def test_frames_differ(self) -> None:
        ship = _make_ship_image()
        frames = engine_glow(ship, num_frames=2)
        # At least some pixels should differ between frames
        diff_count = 0
        px0, px1 = frames[0].load(), frames[1].load()
        for y in range(32):
            for x in range(32):
                if px0[x, y] != px1[x, y]:
                    diff_count += 1
        assert diff_count > 0, "Frames should have different engine pixels"

    def test_transparent_pixels_preserved(self) -> None:
        ship = _make_ship_image()
        frames = engine_glow(ship, num_frames=2)
        px_orig = ship.load()
        for frame in frames:
            px = frame.load()
            for y in range(32):
                for x in range(32):
                    if px_orig[x, y][3] == 0:
                        assert px[x, y][3] == 0, "Transparent pixels must stay transparent"

    def test_non_engine_pixels_unchanged(self) -> None:
        """Hull pixels (not in the engine zone) should not change."""
        ship = _make_ship_image()
        frames = engine_glow(ship, num_frames=2)
        px_orig = ship.load()
        px_frame = frames[0].load()
        # Check hull pixel at (15, 15) — well above engine zone
        assert px_frame[15, 15] == px_orig[15, 15]


class TestBreathe:
    """breathe creates a subtle 1px vertical shift animation."""

    def test_returns_correct_frame_count(self) -> None:
        portrait = _make_portrait_image()
        frames = breathe(portrait, num_frames=2)
        assert len(frames) == 2

    def test_frame_0_is_original(self) -> None:
        portrait = _make_portrait_image()
        frames = breathe(portrait, num_frames=2)
        assert list(frames[0].tobytes()) == list(portrait.tobytes())

    def test_frames_differ(self) -> None:
        portrait = _make_portrait_image()
        frames = breathe(portrait, num_frames=2)
        assert frames[0].tobytes() != frames[1].tobytes()

    def test_same_size(self) -> None:
        portrait = _make_portrait_image()
        frames = breathe(portrait, num_frames=2)
        for frame in frames:
            assert frame.size == portrait.size


class TestBlink:
    """blink creates frames where one has darkened 'eye' pixels."""

    def test_returns_correct_frame_count(self) -> None:
        portrait = _make_portrait_image()
        frames = blink(portrait, num_frames=2)
        assert len(frames) == 2

    def test_frame_0_is_original(self) -> None:
        portrait = _make_portrait_image()
        frames = blink(portrait, num_frames=2)
        assert list(frames[0].tobytes()) == list(portrait.tobytes())

    def test_blink_frame_has_darkened_pixels(self) -> None:
        portrait = _make_portrait_image()
        frames = blink(portrait, num_frames=2)
        # Some pixels should be darker in the blink frame
        px0, px1 = frames[0].load(), frames[1].load()
        darker_count = 0
        for y in range(60):
            for x in range(50):
                r0, g0, b0, a0 = px0[x, y]
                r1, g1, b1, a1 = px1[x, y]
                if a0 > 0 and (r1 < r0 or g1 < g0 or b1 < b0):
                    darker_count += 1
        assert darker_count > 0


class TestColorPulse:
    """color_pulse cycles brightness on bright opaque pixels."""

    def test_returns_correct_frame_count(self) -> None:
        img = _make_test_image(16, 16, (200, 100, 50, 255))
        frames = color_pulse(img, num_frames=2)
        assert len(frames) == 2

    def test_transparent_preserved(self) -> None:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        frames = color_pulse(img, num_frames=2)
        for frame in frames:
            px = frame.load()
            for y in range(16):
                for x in range(16):
                    assert px[x, y][3] == 0


class TestShimmer:
    """shimmer shifts highlight pixels between frames."""

    def test_returns_correct_frame_count(self) -> None:
        img = _make_test_image(24, 24)
        frames = shimmer(img, num_frames=2)
        assert len(frames) == 2

    def test_same_size(self) -> None:
        img = _make_test_image(24, 24)
        frames = shimmer(img, num_frames=2)
        for frame in frames:
            assert frame.size == img.size


class TestMakeSpriteSheet:
    """make_sprite_sheet combines frames into a horizontal strip."""

    def test_correct_dimensions(self) -> None:
        frames = [_make_test_image(32, 32) for _ in range(3)]
        sheet = make_sprite_sheet(frames)
        assert sheet.size == (96, 32)

    def test_single_frame(self) -> None:
        frames = [_make_test_image(16, 16)]
        sheet = make_sprite_sheet(frames)
        assert sheet.size == (16, 16)

    def test_pixel_data_preserved(self) -> None:
        """Frames should be pasted left-to-right."""
        f1 = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
        f2 = Image.new("RGBA", (8, 8), (0, 255, 0, 255))
        sheet = make_sprite_sheet([f1, f2])
        px = sheet.load()
        assert px[0, 0] == (255, 0, 0, 255)  # Frame 1 at x=0
        assert px[8, 0] == (0, 255, 0, 255)  # Frame 2 at x=8


class TestGenerateAnimationConfig:
    """generate_animation_config creates JSON-ready animation defs."""

    def test_basic_config(self) -> None:
        config = generate_animation_config(num_frames=2, frame_duration=0.5, loop=True)
        assert config["idle"]["name"] == "idle"
        assert config["idle"]["frames"] == [0, 1]
        assert config["idle"]["frame_duration"] == 0.5
        assert config["idle"]["loop"] is True

    def test_single_frame(self) -> None:
        config = generate_animation_config(num_frames=1, frame_duration=1.0)
        assert config["idle"]["frames"] == [0]

    def test_many_frames(self) -> None:
        config = generate_animation_config(num_frames=4, frame_duration=0.25)
        assert config["idle"]["frames"] == [0, 1, 2, 3]
