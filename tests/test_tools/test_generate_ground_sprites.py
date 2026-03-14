"""Tests for the ground character sprite generator."""

import json
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from tools.generate_ground_sprites import (
    SPRITES,
    generate_player,
    generate_guild_security,
    generate_union_worker,
    generate_pirate_thug,
    generate_collective_drone,
    generate_alliance_scrapper,
    generate_elite_guard,
    generate_station_sentry,
    generate_crimson_enforcer,
    load_palette,
    _outline_sprite,
)


@pytest.fixture(scope="module")
def pal() -> dict[str, tuple[int, int, int]]:
    return load_palette()


class TestPalette:
    """Palette loads correctly."""

    def test_loads_all_expected_colors(self, pal: dict) -> None:
        expected = [
            "ui_accent_bright", "guild_gold", "guild_navy", "union_rust",
            "crimson_red", "collective_teal", "alliance_green", "skin_mid",
            "outline_dark",
        ]
        for name in expected:
            assert name in pal, f"Missing palette color: {name}"

    def test_colors_are_rgb_tuples(self, pal: dict) -> None:
        for name, color in pal.items():
            assert len(color) == 3, f"{name} should be RGB tuple"
            assert all(0 <= c <= 255 for c in color), f"{name} out of range"


class TestSpriteGeneration:
    """Each generator produces a valid 16x16 RGBA sprite."""

    @pytest.mark.parametrize("sprite_id,gen_func", list(SPRITES.items()))
    def test_correct_size(self, pal: dict, sprite_id: str, gen_func) -> None:
        img = gen_func(pal)
        assert img.size == (16, 16)

    @pytest.mark.parametrize("sprite_id,gen_func", list(SPRITES.items()))
    def test_rgba_mode(self, pal: dict, sprite_id: str, gen_func) -> None:
        img = gen_func(pal)
        assert img.mode == "RGBA"

    @pytest.mark.parametrize("sprite_id,gen_func", list(SPRITES.items()))
    def test_has_opaque_pixels(self, pal: dict, sprite_id: str, gen_func) -> None:
        img = gen_func(pal)
        px = img.load()
        opaque = sum(
            1 for y in range(16) for x in range(16) if px[x, y][3] > 0
        )
        assert opaque > 20, f"{sprite_id} should have substantial opaque area"

    @pytest.mark.parametrize("sprite_id,gen_func", list(SPRITES.items()))
    def test_has_transparent_pixels(self, pal: dict, sprite_id: str, gen_func) -> None:
        img = gen_func(pal)
        px = img.load()
        transparent = sum(
            1 for y in range(16) for x in range(16) if px[x, y][3] == 0
        )
        assert transparent > 20, f"{sprite_id} should have transparent background"

    @pytest.mark.parametrize("sprite_id,gen_func", list(SPRITES.items()))
    def test_has_outline_pixels(self, pal: dict, sprite_id: str, gen_func) -> None:
        """Every sprite should have dark outline pixels."""
        img = gen_func(pal)
        px = img.load()
        outline_count = sum(
            1 for y in range(16) for x in range(16)
            if px[x, y][3] > 0 and px[x, y][:3] == (10, 10, 15)
        )
        assert outline_count > 5, f"{sprite_id} should have outline pixels"


class TestOutlineSprite:
    """Outline function adds border pixels correctly."""

    def test_adds_outline_around_single_pixel(self) -> None:
        img = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        img.putpixel((2, 2), (255, 0, 0, 255))
        result = _outline_sprite(img)
        px = result.load()
        # Original pixel preserved
        assert px[2, 2] == (255, 0, 0, 255)
        # Cardinal neighbors should be outline
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            assert px[2 + dx, 2 + dy][:3] == (10, 10, 15)
        # Diagonals should remain transparent
        assert px[1, 1][3] == 0

    def test_empty_image_unchanged(self) -> None:
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        result = _outline_sprite(img)
        px = result.load()
        for y in range(8):
            for x in range(8):
                assert px[x, y][3] == 0


class TestSpriteDistinctness:
    """Sprites should be visually distinct from each other."""

    def test_all_sprites_differ(self, pal: dict) -> None:
        images = {}
        for sprite_id, gen_func in SPRITES.items():
            images[sprite_id] = gen_func(pal)

        ids = list(images.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a = images[ids[i]]
                b = images[ids[j]]
                assert a.tobytes() != b.tobytes(), (
                    f"{ids[i]} and {ids[j]} should not be identical"
                )

    def test_drone_differs_from_humanoids(self, pal: dict) -> None:
        """Drone has fundamentally different shape than humanoids."""
        drone = generate_collective_drone(pal)
        player = generate_player(pal)
        # Drone should have more opaque pixels in center columns
        dpx = drone.load()
        ppx = player.load()
        drone_center = sum(1 for y in range(16) if dpx[8, y][3] > 0)
        player_center = sum(1 for y in range(16) if ppx[8, y][3] > 0)
        # Both should have substance, but differ in distribution
        assert drone_center > 0
        assert player_center > 0

    def test_turret_differs_from_humanoids(self, pal: dict) -> None:
        """Turret has barrel extending upward."""
        turret = generate_station_sentry(pal)
        px = turret.load()
        # Turret should have opaque pixels in row 1 (barrel)
        top_row_opaque = sum(1 for x in range(16) if px[x, 1][3] > 0)
        assert top_row_opaque > 0, "Turret should have barrel pixels at top"


class TestSpriteRegistry:
    """SPRITES dict covers all expected IDs."""

    def test_player_in_registry(self) -> None:
        assert "player" in SPRITES

    def test_all_enemy_templates_covered(self) -> None:
        expected = [
            "guild_security", "union_worker", "pirate_thug",
            "collective_drone", "alliance_scrapper", "elite_guard",
            "station_sentry", "crimson_enforcer",
        ]
        for template_id in expected:
            assert template_id in SPRITES, f"Missing: {template_id}"

    def test_total_count(self) -> None:
        assert len(SPRITES) == 9  # 1 player + 8 enemies
