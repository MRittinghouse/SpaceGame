"""Tests for the sprite sheet, animation, and sprite manager systems.

Covers SpriteSheet frame extraction, nearest-neighbor scaling,
AnimatedSprite timing/looping/callbacks, AnimationDef configuration,
SpriteManager loading/caching/fallback, and scale_pixel_art utility.
"""

import json
import os
import tempfile

import pygame
import pytest

from spacegame.engine.sprites import (
    SpriteSheet,
    AnimatedSprite,
    AnimationDef,
    SpriteManager,
    scale_pixel_art,
)


# Ensure pygame is initialized for Surface creation
pygame.init()


def _make_sheet_surface(frame_width: int, frame_height: int, frame_count: int) -> pygame.Surface:
    """Create a test sprite sheet surface with distinct colors per frame.

    Each frame is filled with a unique color so we can verify extraction.
    """
    width = frame_width * frame_count
    surface = pygame.Surface((width, frame_height), pygame.SRCALPHA)
    for i in range(frame_count):
        color = ((i * 60 + 40) % 256, (i * 90 + 80) % 256, (i * 120 + 20) % 256, 255)
        rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
        surface.fill(color, rect)
    return surface


# ============================================================================
# SpriteSheet
# ============================================================================


class TestSpriteSheet:
    """SpriteSheet extracts and scales frames from a horizontal strip."""

    def test_frame_count(self) -> None:
        """Frame count computed from surface width / frame_width."""
        surface = _make_sheet_surface(32, 32, 4)
        sheet = SpriteSheet(surface, frame_width=32, frame_height=32)
        assert sheet.frame_count == 4

    def test_single_frame(self) -> None:
        """Single-frame sheet works correctly."""
        surface = _make_sheet_surface(32, 32, 1)
        sheet = SpriteSheet(surface, frame_width=32, frame_height=32)
        assert sheet.frame_count == 1
        frame = sheet.get_frame(0)
        assert frame is not None

    def test_frame_dimensions_at_native_scale(self) -> None:
        """At scale=1, frames match native size."""
        surface = _make_sheet_surface(32, 32, 3)
        sheet = SpriteSheet(surface, frame_width=32, frame_height=32, scale=1)
        frame = sheet.get_frame(0)
        assert frame.get_width() == 32
        assert frame.get_height() == 32

    def test_frame_dimensions_at_2x_scale(self) -> None:
        """At scale=2, frames are doubled."""
        surface = _make_sheet_surface(32, 32, 3)
        sheet = SpriteSheet(surface, frame_width=32, frame_height=32, scale=2)
        frame = sheet.get_frame(0)
        assert frame.get_width() == 64
        assert frame.get_height() == 64

    def test_frame_dimensions_at_3x_scale(self) -> None:
        """At scale=3, frames are tripled."""
        surface = _make_sheet_surface(16, 16, 2)
        sheet = SpriteSheet(surface, frame_width=16, frame_height=16, scale=3)
        frame = sheet.get_frame(0)
        assert frame.get_width() == 48
        assert frame.get_height() == 48

    def test_frames_have_distinct_content(self) -> None:
        """Each extracted frame has different pixel content."""
        surface = _make_sheet_surface(8, 8, 3)
        sheet = SpriteSheet(surface, frame_width=8, frame_height=8, scale=1)
        f0 = sheet.get_frame(0)
        f1 = sheet.get_frame(1)
        # Compare center pixel of each frame
        c0 = f0.get_at((4, 4))
        c1 = f1.get_at((4, 4))
        assert c0 != c1

    def test_get_frame_wraps_index(self) -> None:
        """Frame index wraps around using modulo."""
        surface = _make_sheet_surface(32, 32, 3)
        sheet = SpriteSheet(surface, frame_width=32, frame_height=32, scale=1)
        f0 = sheet.get_frame(0)
        f3 = sheet.get_frame(3)  # Should wrap to frame 0
        # Same content
        assert f0.get_at((16, 16)) == f3.get_at((16, 16))

    def test_non_square_frames(self) -> None:
        """Handles non-square frame dimensions (e.g., 50x60 portraits)."""
        surface = _make_sheet_surface(50, 60, 4)
        sheet = SpriteSheet(surface, frame_width=50, frame_height=60, scale=2)
        frame = sheet.get_frame(0)
        assert frame.get_width() == 100
        assert frame.get_height() == 120

    def test_scaling_uses_nearest_neighbor(self) -> None:
        """Scaling preserves hard pixel edges (no anti-aliasing)."""
        # Create a 2x2 checkerboard pattern
        surface = pygame.Surface((2, 2), pygame.SRCALPHA)
        surface.set_at((0, 0), (255, 0, 0, 255))
        surface.set_at((1, 0), (0, 0, 255, 255))
        surface.set_at((0, 1), (0, 255, 0, 255))
        surface.set_at((1, 1), (255, 255, 0, 255))

        sheet = SpriteSheet(surface, frame_width=2, frame_height=2, scale=4)
        frame = sheet.get_frame(0)
        # At 4x scale, pixel (0,0) should still be pure red at (0,0) through (3,3)
        assert frame.get_at((0, 0)) == pygame.Color(255, 0, 0, 255)
        assert frame.get_at((3, 3)) == pygame.Color(255, 0, 0, 255)
        # Pixel (1,0) at native = blue, at 4x should be at (4,0)
        assert frame.get_at((4, 0)) == pygame.Color(0, 0, 255, 255)

    def test_alpha_preserved(self) -> None:
        """Transparent pixels remain transparent after extraction and scaling."""
        surface = pygame.Surface((8, 4), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))  # Fully transparent
        surface.fill((255, 0, 0, 255), pygame.Rect(0, 0, 4, 4))  # Frame 0: red

        sheet = SpriteSheet(surface, frame_width=4, frame_height=4, scale=2)
        f0 = sheet.get_frame(0)
        f1 = sheet.get_frame(1)
        # Frame 0 should have opaque red
        assert f0.get_at((0, 0)).a == 255
        # Frame 1 should be transparent
        assert f1.get_at((0, 0)).a == 0


# ============================================================================
# AnimationDef
# ============================================================================


class TestAnimationDef:
    """AnimationDef defines a named frame sequence."""

    def test_basic_creation(self) -> None:
        anim = AnimationDef(name="idle", frames=[0, 1], frame_duration=0.5)
        assert anim.name == "idle"
        assert anim.frames == [0, 1]
        assert anim.frame_duration == 0.5
        assert anim.loop is True  # Default

    def test_one_shot(self) -> None:
        anim = AnimationDef(name="hit", frames=[2, 3, 2], frame_duration=0.08, loop=False)
        assert anim.loop is False

    def test_from_dict(self) -> None:
        data = {
            "name": "destroy",
            "frames": [4, 5, 6, 7],
            "frame_duration": 0.15,
            "loop": False,
        }
        anim = AnimationDef.from_dict(data)
        assert anim.name == "destroy"
        assert anim.frames == [4, 5, 6, 7]
        assert anim.frame_duration == 0.15
        assert anim.loop is False

    def test_from_dict_defaults_to_loop(self) -> None:
        data = {"name": "idle", "frames": [0, 1], "frame_duration": 1.0}
        anim = AnimationDef.from_dict(data)
        assert anim.loop is True


# ============================================================================
# AnimatedSprite
# ============================================================================


class TestAnimatedSprite:
    """AnimatedSprite manages frame-based animation on a SpriteSheet."""

    def _make_sprite(self, frame_count: int = 8) -> AnimatedSprite:
        """Create a test AnimatedSprite with idle + hit animations."""
        surface = _make_sheet_surface(16, 16, frame_count)
        sheet = SpriteSheet(surface, frame_width=16, frame_height=16, scale=1)
        anims = {
            "idle": AnimationDef(name="idle", frames=[0, 1], frame_duration=0.5),
            "hit": AnimationDef(name="hit", frames=[2, 3, 2], frame_duration=0.1, loop=False),
            "destroy": AnimationDef(
                name="destroy", frames=[4, 5, 6, 7], frame_duration=0.15, loop=False
            ),
        }
        return AnimatedSprite(sheet=sheet, animations=anims)

    def test_no_animation_initially(self) -> None:
        """Before play() is called, get_surface returns None."""
        sprite = self._make_sprite()
        assert sprite.get_surface() is None

    def test_play_starts_animation(self) -> None:
        """After play(), get_surface returns the first frame."""
        sprite = self._make_sprite()
        sprite.play("idle")
        surface = sprite.get_surface()
        assert surface is not None
        assert surface.get_width() == 16

    def test_frame_advances_on_update(self) -> None:
        """update(dt) advances to the next frame after frame_duration."""
        sprite = self._make_sprite()
        sprite.play("idle")

        # Frame 0 initially
        s0 = sprite.get_surface()
        c0 = s0.get_at((8, 8))

        # Advance past frame_duration (0.5s)
        sprite.update(0.6)

        # Should be on frame 1 now
        s1 = sprite.get_surface()
        c1 = s1.get_at((8, 8))
        assert c0 != c1

    def test_looping_animation_wraps(self) -> None:
        """Looping animation wraps back to first frame."""
        sprite = self._make_sprite()
        sprite.play("idle")  # 2 frames at 0.5s each

        # Advance through both frames
        sprite.update(1.1)  # Past 2 frames (1.0s total)

        # Should be back on frame 0
        surface = sprite.get_surface()
        assert surface is not None

    def test_one_shot_stops_on_last_frame(self) -> None:
        """Non-looping animation stops on the last frame."""
        sprite = self._make_sprite()
        sprite.play("hit")  # 3 frames at 0.1s

        # Advance past all frames
        sprite.update(0.5)

        # Should be on last frame, not advancing further
        assert sprite.is_finished() is True
        surface = sprite.get_surface()
        assert surface is not None

    def test_one_shot_callback_fires(self) -> None:
        """on_complete callback fires when one-shot animation finishes."""
        sprite = self._make_sprite()
        callback_fired = [False]

        def on_done() -> None:
            callback_fired[0] = True

        sprite.play("hit", on_complete=on_done)
        sprite.update(0.5)

        assert callback_fired[0] is True

    def test_callback_fires_exactly_once(self) -> None:
        """Callback doesn't fire repeatedly on continued updates."""
        sprite = self._make_sprite()
        call_count = [0]

        def on_done() -> None:
            call_count[0] += 1

        sprite.play("hit", on_complete=on_done)
        sprite.update(0.5)
        sprite.update(0.5)
        sprite.update(0.5)

        assert call_count[0] == 1

    def test_play_resets_animation(self) -> None:
        """Calling play() again resets to the first frame."""
        sprite = self._make_sprite()
        sprite.play("idle")
        sprite.update(0.6)  # Advance to frame 1

        sprite.play("idle")  # Reset
        # Should be on frame 0 again
        assert sprite.is_finished() is False

    def test_play_different_animation(self) -> None:
        """Can switch between animations."""
        sprite = self._make_sprite()
        sprite.play("idle")
        sprite.update(0.3)

        sprite.play("hit")
        # Should now be on hit's first frame
        assert sprite.is_finished() is False

    def test_play_nonexistent_animation_no_crash(self) -> None:
        """Playing a non-existent animation is a no-op."""
        sprite = self._make_sprite()
        sprite.play("nonexistent")
        assert sprite.get_surface() is None

    def test_multiple_small_updates(self) -> None:
        """Many small dt values accumulate correctly."""
        sprite = self._make_sprite()
        sprite.play("idle")  # 0.5s per frame

        for _ in range(60):
            sprite.update(1 / 60)  # ~1s of 60fps updates

        # Should have looped at least once
        surface = sprite.get_surface()
        assert surface is not None

    def test_zero_dt_no_advance(self) -> None:
        """Zero dt doesn't advance the animation."""
        sprite = self._make_sprite()
        sprite.play("idle")
        s0 = sprite.get_surface()

        sprite.update(0.0)
        s1 = sprite.get_surface()

        assert s0.get_at((8, 8)) == s1.get_at((8, 8))

    def test_destroy_animation_full_sequence(self) -> None:
        """4-frame destroy animation plays through completely."""
        sprite = self._make_sprite()
        sprite.play("destroy")  # 4 frames at 0.15s

        frames_seen = set()
        for step in range(10):
            surface = sprite.get_surface()
            if surface:
                frames_seen.add(surface.get_at((8, 8))[:3])
            sprite.update(0.16)

        # Should have seen at least 3 distinct frames
        assert len(frames_seen) >= 3
        assert sprite.is_finished() is True

    def test_get_current_anim_name(self) -> None:
        """Can query the currently playing animation name."""
        sprite = self._make_sprite()
        assert sprite.current_animation is None

        sprite.play("idle")
        assert sprite.current_animation == "idle"

        sprite.play("hit")
        assert sprite.current_animation == "hit"


# ============================================================================
# scale_pixel_art Utility
# ============================================================================


class TestScalePixelArt:
    """scale_pixel_art scales using nearest-neighbor only."""

    def test_doubles_size(self) -> None:
        surface = pygame.Surface((16, 16), pygame.SRCALPHA)
        result = scale_pixel_art(surface, 2)
        assert result.get_size() == (32, 32)

    def test_triples_size(self) -> None:
        surface = pygame.Surface((16, 16), pygame.SRCALPHA)
        result = scale_pixel_art(surface, 3)
        assert result.get_size() == (48, 48)

    def test_scale_1_returns_copy(self) -> None:
        """Scale factor 1 returns a surface of the same size."""
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        result = scale_pixel_art(surface, 1)
        assert result.get_size() == (32, 32)

    def test_preserves_hard_edges(self) -> None:
        """Nearest-neighbor preserves pixel boundaries (no blending)."""
        surface = pygame.Surface((2, 2), pygame.SRCALPHA)
        surface.set_at((0, 0), (255, 0, 0, 255))
        surface.set_at((1, 0), (0, 0, 255, 255))
        surface.set_at((0, 1), (0, 255, 0, 255))
        surface.set_at((1, 1), (255, 255, 0, 255))

        result = scale_pixel_art(surface, 4)
        # 4x scale: pixel (0,0) fills (0,0)-(3,3)
        assert result.get_at((0, 0)) == pygame.Color(255, 0, 0, 255)
        assert result.get_at((3, 3)) == pygame.Color(255, 0, 0, 255)
        # Pixel (1,0) at 4x starts at (4,0)
        assert result.get_at((4, 0)) == pygame.Color(0, 0, 255, 255)


# ============================================================================
# SpriteManager — Test Helpers
# ============================================================================


def _save_test_png(
    path: str, width: int, height: int, color: tuple[int, int, int, int] = (255, 0, 0, 255)
) -> None:
    """Create a minimal RGBA PNG file using pygame."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill(color)
    pygame.image.save(surface, path)


def _save_test_sheet_png(path: str, frame_width: int, frame_height: int, frame_count: int) -> None:
    """Create a sprite sheet PNG with distinct colors per frame."""
    total_width = frame_width * frame_count
    surface = pygame.Surface((total_width, frame_height), pygame.SRCALPHA)
    for i in range(frame_count):
        color = ((i * 60 + 40) % 256, (i * 90 + 80) % 256, (i * 120 + 20) % 256, 255)
        rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
        surface.fill(color, rect)
    pygame.image.save(surface, path)


def _write_anim_config(dir_path: str, filename: str, config: dict) -> None:
    """Write an animation config JSON file."""
    anims_dir = os.path.join(dir_path, "animations")
    os.makedirs(anims_dir, exist_ok=True)
    with open(os.path.join(anims_dir, filename), "w") as f:
        json.dump(config, f)


# ============================================================================
# SpriteManager
# ============================================================================


class TestSpriteManager:
    """SpriteManager loads, caches, and provides access to sprites."""

    def test_construction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            assert mgr is not None

    # --- Sheet loading ---

    def test_get_sheet_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            result = mgr.get_sheet("ships/player", "nonexistent", 32, 32)
            assert result is None

    def test_get_sheet_loads_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)

            mgr = SpriteManager(tmpdir)
            sheet = mgr.get_sheet("ships/player", "shuttle", 32, 32)
            assert sheet is not None
            assert isinstance(sheet, SpriteSheet)
            assert sheet.frame_count == 4

    def test_get_sheet_caches_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)

            mgr = SpriteManager(tmpdir)
            sheet1 = mgr.get_sheet("ships/player", "shuttle", 32, 32)
            sheet2 = mgr.get_sheet("ships/player", "shuttle", 32, 32)
            assert sheet1 is sheet2

    def test_get_sheet_with_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 2)

            mgr = SpriteManager(tmpdir)
            sheet = mgr.get_sheet("ships/player", "shuttle", 32, 32, scale=2)
            frame = sheet.get_frame(0)
            assert frame.get_size() == (64, 64)

    def test_get_sheet_different_scales_cached_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 2)

            mgr = SpriteManager(tmpdir)
            sheet_1x = mgr.get_sheet("ships/player", "shuttle", 32, 32, scale=1)
            sheet_2x = mgr.get_sheet("ships/player", "shuttle", 32, 32, scale=2)
            assert sheet_1x is not sheet_2x
            assert sheet_1x.get_frame(0).get_size() == (32, 32)
            assert sheet_2x.get_frame(0).get_size() == (64, 64)

    # --- Animated sprite creation ---

    def test_get_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            result = mgr.get_sprite("ships/player", "nonexistent", 32, 32)
            assert result is None

    def test_get_sprite_creates_animated_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)

            anims = {
                "idle": AnimationDef(name="idle", frames=[0, 1], frame_duration=0.3),
            }
            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_sprite("ships/player", "shuttle", 32, 32, animations=anims)
            assert sprite is not None
            assert isinstance(sprite, AnimatedSprite)

    def test_get_sprite_each_call_returns_new_instance(self) -> None:
        """Each get_sprite call returns a fresh AnimatedSprite (lightweight)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)

            anims = {
                "idle": AnimationDef(name="idle", frames=[0, 1], frame_duration=0.3),
            }
            mgr = SpriteManager(tmpdir)
            s1 = mgr.get_sprite("ships/player", "shuttle", 32, 32, animations=anims)
            s2 = mgr.get_sprite("ships/player", "shuttle", 32, 32, animations=anims)
            assert s1 is not s2  # Different AnimatedSprite instances

    # --- Static sprite loading ---

    def test_get_static_sprite_loads_and_scales(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "commodities")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "iron_ore.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_static_sprite("commodities", "iron_ore", scale=2)
            assert surface is not None
            assert surface.get_size() == (32, 32)

    def test_get_static_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            result = mgr.get_static_sprite("commodities", "nonexistent")
            assert result is None

    def test_get_static_sprite_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "commodities")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "iron_ore.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            s1 = mgr.get_static_sprite("commodities", "iron_ore", scale=2)
            s2 = mgr.get_static_sprite("commodities", "iron_ore", scale=2)
            assert s1 is s2

    def test_get_static_sprite_scale_1(self) -> None:
        """Scale 1 returns native-size surface."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "commodities")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "iron_ore.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_static_sprite("commodities", "iron_ore", scale=1)
            assert surface.get_size() == (16, 16)

    # --- Animation config loading ---

    def test_load_animation_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "idle": {
                    "name": "idle",
                    "frames": [0, 1],
                    "frame_duration": 0.3,
                    "loop": True,
                },
                "hit": {
                    "name": "hit",
                    "frames": [2, 3, 2],
                    "frame_duration": 0.08,
                    "loop": False,
                },
            }
            _write_anim_config(tmpdir, "ship_anims.json", config)

            mgr = SpriteManager(tmpdir)
            defs = mgr.load_animation_config("ship_anims.json")
            assert "idle" in defs
            assert "hit" in defs
            assert defs["idle"].frames == [0, 1]
            assert defs["idle"].frame_duration == 0.3
            assert defs["hit"].loop is False

    def test_load_animation_config_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            defs = mgr.load_animation_config("nonexistent.json")
            assert defs == {}

    def test_load_animation_config_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "idle": {
                    "name": "idle",
                    "frames": [0, 1],
                    "frame_duration": 0.5,
                },
            }
            _write_anim_config(tmpdir, "ship_anims.json", config)

            mgr = SpriteManager(tmpdir)
            d1 = mgr.load_animation_config("ship_anims.json")
            d2 = mgr.load_animation_config("ship_anims.json")
            assert d1 is d2

    # --- Cache clearing ---

    def test_clear_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "commodities")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "iron_ore.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            mgr.get_static_sprite("commodities", "iron_ore")
            assert len(mgr._static_cache) > 0

            mgr.clear_cache()
            assert len(mgr._sheet_cache) == 0
            assert len(mgr._static_cache) == 0
            assert len(mgr._anim_cache) == 0

    # --- Convenience: ship sprites ---

    def test_get_ship_sprite_from_sheet(self) -> None:
        """Ship sprite from animation sheet returns a Surface."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)
            _write_anim_config(
                tmpdir,
                "ship_anims.json",
                {
                    "idle": {"name": "idle", "frames": [0, 1], "frame_duration": 0.3, "loop": True},
                },
            )

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ship_sprite("shuttle")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)
            assert surface.get_size() == (64, 64)  # 32x32 at 2x

    def test_get_ship_sprite_static_fallback(self) -> None:
        """Ship sprite falls back to static PNG when no sheet exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "shuttle.png"), 32, 32)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ship_sprite("shuttle")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)
            assert surface.get_size() == (64, 64)  # 32x32 at 2x

    def test_get_ship_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            assert mgr.get_ship_sprite("nonexistent") is None

    def test_get_ship_sprite_no_anims_uses_default(self) -> None:
        """If ship_anims.json is missing, creates default idle animation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ship_sprite("shuttle")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)

    # --- Convenience: enemy sprites ---

    def test_get_enemy_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "enemies")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "pirate_base_sheet.png"), 32, 32, 4)
            _write_anim_config(
                tmpdir,
                "ship_anims.json",
                {
                    "idle": {"name": "idle", "frames": [0, 1], "frame_duration": 0.3, "loop": True},
                },
            )

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_enemy_sprite("pirate_base")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)
            assert surface.get_size() == (64, 64)

    def test_get_enemy_sprite_static_fallback(self) -> None:
        """Enemy sprite falls back to static PNG when no sheet exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "enemies")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "pirate_scout.png"), 32, 32)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_enemy_sprite("pirate_scout")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)

    def test_get_enemy_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            assert mgr.get_enemy_sprite("nonexistent") is None

    # --- Convenience: portrait sprites ---

    def test_get_portrait_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "portraits")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "officer_larsen_sheet.png"), 50, 60, 8)
            _write_anim_config(
                tmpdir,
                "portrait_anims.json",
                {
                    "idle": {"name": "idle", "frames": [0, 1], "frame_duration": 1.0, "loop": True},
                },
            )

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_portrait_sprite("officer_larsen")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)
            assert surface.get_size() == (100, 120)  # 50x60 at 2x

    def test_get_portrait_sprite_static_fallback(self) -> None:
        """Portrait sprite falls back to static PNG when no sheet exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "portraits")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "officer_larsen.png"), 50, 60)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_portrait_sprite("officer_larsen")
            assert surface is not None
            assert isinstance(surface, pygame.Surface)
            assert surface.get_size() == (100, 120)  # 50x60 at 2x

    def test_get_portrait_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            assert mgr.get_portrait_sprite("nonexistent") is None

    # --- Convenience: static icons ---

    def test_get_commodity_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "commodities")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "iron_ore.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_commodity_icon("iron_ore")
            assert surface is not None
            assert surface.get_size() == (32, 32)  # 16x16 at 2x

    def test_get_commodity_icon_custom_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "commodities")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "iron_ore.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_commodity_icon("iron_ore", scale=1)
            assert surface.get_size() == (16, 16)  # Native size

    def test_get_faction_emblem(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "factions")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "commerce_guild.png"), 24, 24)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_faction_emblem("commerce_guild")
            assert surface is not None
            assert surface.get_size() == (48, 48)  # 24x24 at 2x

    def test_get_ground_tile_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles", "neutral")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "floor.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_tile("floor")
            assert surface is not None
            assert surface.get_size() == (48, 48)  # 16x16 at 3x

    def test_get_ground_tile_faction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles", "commerce_guild")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "wall.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_tile("wall", faction_id="commerce_guild")
            assert surface is not None
            assert surface.get_size() == (48, 48)

    def test_get_upgrade_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "upgrades")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "cargo_bay_ext.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_upgrade_icon("cargo_bay_ext")
            assert surface is not None
            assert surface.get_size() == (32, 32)  # 16x16 at 2x

    # --- Convenience: ground player sprite ---

    def test_get_ground_player_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "player.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_player_sprite()
            assert surface is not None
            assert surface.get_size() == (48, 48)  # 16x16 at 3x

    def test_get_ground_player_sprite_custom_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "player.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_player_sprite(scale=2)
            assert surface is not None
            assert surface.get_size() == (32, 32)  # 16x16 at 2x

    def test_get_ground_player_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            assert mgr.get_ground_player_sprite() is None

    # --- Convenience: ground enemy sprite ---

    def test_get_ground_enemy_sprite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles", "enemies")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "guild_security.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_enemy_sprite("guild_security")
            assert surface is not None
            assert surface.get_size() == (48, 48)  # 16x16 at 3x

    def test_get_ground_enemy_sprite_custom_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles", "enemies")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "guild_security.png"), 16, 16)

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_enemy_sprite("guild_security", scale=2)
            assert surface is not None
            assert surface.get_size() == (32, 32)  # 16x16 at 2x

    def test_get_ground_enemy_sprite_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            assert mgr.get_ground_enemy_sprite("nonexistent") is None

    def test_get_ground_enemy_sprite_delegates_to_get_static_sprite(self) -> None:
        """Ground enemy sprite uses ground_tiles/enemies category path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Place file at the expected path
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles", "enemies")
            os.makedirs(sprites_dir)
            _save_test_png(
                os.path.join(sprites_dir, "pirate_thug.png"),
                16,
                16,
                color=(0, 255, 0, 255),
            )

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_enemy_sprite("pirate_thug")
            assert surface is not None
            # Verify it loaded correctly by checking pixel color
            assert surface.get_at((0, 0))[:3] == (0, 255, 0)

    def test_get_ground_player_sprite_delegates_to_get_static_sprite(self) -> None:
        """Ground player sprite uses ground_tiles category path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ground_tiles")
            os.makedirs(sprites_dir)
            _save_test_png(
                os.path.join(sprites_dir, "player.png"),
                16,
                16,
                color=(0, 0, 255, 255),
            )

            mgr = SpriteManager(tmpdir)
            surface = mgr.get_ground_player_sprite()
            assert surface is not None
            # Verify it loaded correctly by checking pixel color
            assert surface.get_at((0, 0))[:3] == (0, 0, 255)

    # --- Convenience: animated ship sprites ---

    def test_get_ship_animated_from_static_png(self) -> None:
        """When only a static PNG exists, wraps it in AnimatedSprite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "shuttle.png"), 32, 32)

            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_ship_animated("shuttle", category="player", scale=1)
            assert sprite is not None
            assert isinstance(sprite, AnimatedSprite)
            surface = sprite.get_surface()
            assert surface is not None
            assert surface.get_size() == (32, 32)

    def test_get_ship_animated_from_sheet(self) -> None:
        """When a sprite sheet exists, returns AnimatedSprite from sheet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)
            _write_anim_config(
                tmpdir,
                "ship_anims.json",
                {
                    "idle": {"name": "idle", "frames": [0, 1], "frame_duration": 0.3, "loop": True},
                },
            )

            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_ship_animated("shuttle", category="player", scale=2)
            assert sprite is not None
            assert isinstance(sprite, AnimatedSprite)
            surface = sprite.get_surface()
            assert surface is not None
            assert surface.get_size() == (64, 64)

    def test_get_ship_animated_enemy_category(self) -> None:
        """Can load enemy ships via category parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "enemies")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "pirate_scout.png"), 32, 32)

            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_ship_animated("pirate_scout", category="enemies", scale=1)
            assert sprite is not None
            assert isinstance(sprite, AnimatedSprite)

    def test_get_ship_animated_missing_returns_none(self) -> None:
        """Missing ship returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_ship_animated("nonexistent", category="player")
            assert sprite is None

    def test_get_ship_animated_updates_frame(self) -> None:
        """AnimatedSprite from sheet advances frames on update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "ships", "player")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "shuttle_sheet.png"), 32, 32, 4)

            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_ship_animated("shuttle", category="player", scale=1)
            assert sprite is not None
            s0 = sprite.get_surface()
            c0 = s0.get_at((16, 16))
            sprite.update(0.6)
            s1 = sprite.get_surface()
            c1 = s1.get_at((16, 16))
            assert c0 != c1

    # --- Convenience: animated portrait sprites ---

    def test_get_portrait_animated_from_static_png(self) -> None:
        """When only a static PNG exists, wraps it in AnimatedSprite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "portraits")
            os.makedirs(sprites_dir)
            _save_test_png(os.path.join(sprites_dir, "officer_larsen.png"), 50, 60)

            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_portrait_animated("officer_larsen", scale=1)
            assert sprite is not None
            assert isinstance(sprite, AnimatedSprite)
            surface = sprite.get_surface()
            assert surface is not None
            assert surface.get_size() == (50, 60)

    def test_get_portrait_animated_from_sheet(self) -> None:
        """When a sprite sheet exists, returns AnimatedSprite from sheet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sprites_dir = os.path.join(tmpdir, "sprites", "portraits")
            os.makedirs(sprites_dir)
            _save_test_sheet_png(os.path.join(sprites_dir, "officer_larsen_sheet.png"), 50, 60, 4)
            _write_anim_config(
                tmpdir,
                "portrait_anims.json",
                {
                    "idle": {"name": "idle", "frames": [0, 1], "frame_duration": 1.0, "loop": True},
                },
            )

            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_portrait_animated("officer_larsen", scale=2)
            assert sprite is not None
            assert isinstance(sprite, AnimatedSprite)
            surface = sprite.get_surface()
            assert surface is not None
            assert surface.get_size() == (100, 120)

    def test_get_portrait_animated_missing_returns_none(self) -> None:
        """Missing portrait returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SpriteManager(tmpdir)
            sprite = mgr.get_portrait_animated("nonexistent")
            assert sprite is None
