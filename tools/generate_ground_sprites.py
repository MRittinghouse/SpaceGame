"""Programmatic generator for 16x16 top-down ground character sprites.

Creates pixel-art character sprites using the master palette for:
- Player character (1 sprite)
- 8 enemy templates (guild_security, union_worker, pirate_thug,
  collective_drone, alliance_scrapper, elite_guard, station_sentry,
  crimson_enforcer)

All sprites are 16x16 RGBA with 1px dark outlines and faction-appropriate
colors drawn from the master palette.

Usage:
    python -m tools.generate_ground_sprites [--preview]
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).resolve().parent.parent / "spacegame" / "data" / "assets"
PALETTE_PATH = ASSETS_DIR / "palettes" / "master_palette.json"
GROUND_TILES_DIR = ASSETS_DIR / "sprites" / "ground_tiles"
ENEMIES_DIR = GROUND_TILES_DIR / "enemies"

# ---------------------------------------------------------------------------
# Palette loading
# ---------------------------------------------------------------------------


def load_palette() -> dict[str, tuple[int, int, int]]:
    """Load master palette as {name: (r, g, b)} dict."""
    with open(PALETTE_PATH) as f:
        data = json.load(f)
    return {k: tuple(v) for k, v in data["colors"].items()}


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

OUTLINE = (10, 10, 15, 255)  # outline_dark with full alpha
TRANSPARENT = (0, 0, 0, 0)


def _rgba(rgb: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
    return (*rgb, a)


def _outline_sprite(img: Image.Image) -> Image.Image:
    """Add 1px dark outline around all opaque pixels."""
    w, h = img.size
    px = img.load()
    result = img.copy()
    rpx = result.load()

    for y in range(h):
        for x in range(w):
            if px[x, y][3] == 0:
                # Check if any neighbor is opaque
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] > 0:
                        rpx[x, y] = OUTLINE
                        break
    return result


def _draw_humanoid(
    img: Image.Image,
    head_color: tuple[int, int, int],
    body_color: tuple[int, int, int],
    legs_color: tuple[int, int, int],
    accent_color: tuple[int, int, int] | None = None,
    visor_color: tuple[int, int, int] | None = None,
    shoulder_color: tuple[int, int, int] | None = None,
) -> None:
    """Draw a top-down humanoid figure centered in a 16x16 image.

    Top-down view: head at top, body in middle, legs at bottom.
    Viewed from above, so head is a circle, shoulders visible.
    """
    px = img.load()

    # Head (rows 2-5, cols 6-9) — 4x4 circle-ish
    for y in range(2, 6):
        for x in range(6, 10):
            # Round corners
            if (x == 6 or x == 9) and (y == 2 or y == 5):
                continue
            px[x, y] = _rgba(head_color)

    # Visor/eyes (row 3, cols 7-8)
    if visor_color:
        px[7, 3] = _rgba(visor_color)
        px[8, 3] = _rgba(visor_color)

    # Shoulders (row 6, cols 4-11)
    s_color = shoulder_color or body_color
    for x in range(5, 11):
        px[x, 6] = _rgba(s_color)

    # Body (rows 7-10, cols 5-10)
    for y in range(7, 11):
        for x in range(5, 11):
            px[x, y] = _rgba(body_color)

    # Accent stripe down center of body
    if accent_color:
        for y in range(7, 11):
            px[7, y] = _rgba(accent_color)
            px[8, y] = _rgba(accent_color)

    # Arms (rows 7-9, cols 4 and 11)
    for y in range(7, 10):
        px[4, y] = _rgba(body_color)
        px[11, y] = _rgba(body_color)

    # Legs (rows 11-13, cols 5-6 and 9-10)
    for y in range(11, 14):
        px[5, y] = _rgba(legs_color)
        px[6, y] = _rgba(legs_color)
        px[9, y] = _rgba(legs_color)
        px[10, y] = _rgba(legs_color)


def _draw_drone(
    img: Image.Image,
    body_color: tuple[int, int, int],
    accent_color: tuple[int, int, int],
    eye_color: tuple[int, int, int],
) -> None:
    """Draw a top-down robotic drone (octagonal shape, no legs)."""
    px = img.load()

    # Octagonal body (rows 3-12, centered)
    body_rows = {
        3: (6, 10),
        4: (5, 11),
        5: (4, 12),
        6: (4, 12),
        7: (4, 12),
        8: (4, 12),
        9: (4, 12),
        10: (4, 12),
        11: (5, 11),
        12: (6, 10),
    }
    for y, (x_start, x_end) in body_rows.items():
        for x in range(x_start, x_end):
            px[x, y] = _rgba(body_color)

    # Central sensor/eye (rows 6-8, cols 7-8)
    for y in range(6, 9):
        px[7, y] = _rgba(eye_color)
        px[8, y] = _rgba(eye_color)

    # Accent ring
    ring_pixels = [
        (6, 4), (7, 4), (8, 4), (9, 4),  # top
        (6, 12), (7, 12), (8, 12), (9, 12),  # bottom
        (4, 6), (4, 7), (4, 8), (4, 9),  # left
        (11, 6), (11, 7), (11, 8), (11, 9),  # right
    ]
    for x, y in ring_pixels:
        px[x, y] = _rgba(accent_color)


def _draw_turret(
    img: Image.Image,
    base_color: tuple[int, int, int],
    barrel_color: tuple[int, int, int],
    light_color: tuple[int, int, int],
) -> None:
    """Draw a top-down automated turret/sentry."""
    px = img.load()

    # Square base (rows 4-11, cols 4-11)
    for y in range(4, 12):
        for x in range(4, 12):
            px[x, y] = _rgba(base_color)

    # Corner posts (brighter)
    corners = [(4, 4), (11, 4), (4, 11), (11, 11)]
    lighter = tuple(min(255, c + 40) for c in base_color)
    for x, y in corners:
        px[x, y] = _rgba(lighter)

    # Barrel pointing up (rows 1-5, cols 7-8)
    for y in range(1, 5):
        px[7, y] = _rgba(barrel_color)
        px[8, y] = _rgba(barrel_color)

    # Center sensor light
    px[7, 7] = _rgba(light_color)
    px[8, 7] = _rgba(light_color)
    px[7, 8] = _rgba(light_color)
    px[8, 8] = _rgba(light_color)

    # Side panels
    for y in range(6, 10):
        px[3, y] = _rgba(barrel_color)
        px[12, y] = _rgba(barrel_color)


# ---------------------------------------------------------------------------
# Sprite definitions
# ---------------------------------------------------------------------------


def generate_player(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Player character: bright blue accent, recognizable."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["skin_mid"],
        body_color=pal["ui_bg_light"],
        legs_color=pal["ui_bg_mid"],
        accent_color=pal["ui_accent_bright"],
        visor_color=None,
        shoulder_color=pal["ui_accent"],
    )
    return _outline_sprite(img)


def generate_guild_security(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Commerce Guild guard: gold/navy uniform."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["skin_light"],
        body_color=pal["guild_navy"],
        legs_color=pal["guild_navy"],
        accent_color=pal["guild_gold"],
        visor_color=None,
        shoulder_color=pal["guild_gold"],
    )
    return _outline_sprite(img)


def generate_union_worker(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Miners Union worker: rust/brown overalls with yellow."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["skin_mid"],
        body_color=pal["union_brown"],
        legs_color=pal["union_gray"],
        accent_color=pal["union_yellow"],
        visor_color=None,
        shoulder_color=pal["union_rust"],
    )
    return _outline_sprite(img)


def generate_pirate_thug(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Pirate thug: dark with crimson accents."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["skin_dark"],
        body_color=pal["crimson_charcoal"],
        legs_color=pal["crimson_black"],
        accent_color=pal["crimson_red"],
        visor_color=None,
        shoulder_color=pal["crimson_charcoal"],
    )
    return _outline_sprite(img)


def generate_collective_drone(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Science Collective drone: robotic, white/teal."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_drone(
        img,
        body_color=pal["collective_steel"],
        accent_color=pal["collective_teal"],
        eye_color=pal["collective_green"],
    )
    return _outline_sprite(img)


def generate_alliance_scrapper(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Frontier Alliance scrapper: green/tan field gear."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["skin_mid"],
        body_color=pal["alliance_green"],
        legs_color=pal["alliance_brown"],
        accent_color=pal["alliance_tan"],
        visor_color=None,
        shoulder_color=pal["alliance_green"],
    )
    return _outline_sprite(img)


def generate_elite_guard(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Elite guard: heavy armored, gold/red imposing."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["guild_cream"],
        body_color=pal["guild_red"],
        legs_color=pal["guild_navy"],
        accent_color=pal["guild_gold"],
        visor_color=pal["guild_gold"],
        shoulder_color=pal["guild_gold"],
    )
    return _outline_sprite(img)


def generate_station_sentry(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Station sentry: automated turret, gray/steel."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_turret(
        img,
        base_color=pal["collective_steel"],
        barrel_color=pal["union_gray"],
        light_color=pal["ui_health_low"],
    )
    return _outline_sprite(img)


def generate_crimson_enforcer(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Crimson Reach enforcer: red/purple menacing."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    _draw_humanoid(
        img,
        head_color=pal["skin_dark"],
        body_color=pal["crimson_red"],
        legs_color=pal["crimson_charcoal"],
        accent_color=pal["crimson_purple"],
        visor_color=pal["crimson_toxic"],
        shoulder_color=pal["crimson_red"],
    )
    return _outline_sprite(img)


# ---------------------------------------------------------------------------
# Tile sprite generators (16x16 top-down)
# ---------------------------------------------------------------------------

NEUTRAL_DIR = GROUND_TILES_DIR / "neutral"


def generate_terminal(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Data terminal: floor panel with glowing cyan screen."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    px = img.load()

    # Floor base
    floor_color = (60, 65, 75)
    for y in range(16):
        for x in range(16):
            px[x, y] = _rgba(floor_color)

    # Terminal base (dark rectangle)
    base_color = (40, 42, 50)
    for y in range(4, 13):
        for x in range(4, 12):
            px[x, y] = _rgba(base_color)

    # Screen (cyan glow)
    screen_color = (60, 180, 200)
    screen_bright = (100, 220, 240)
    for y in range(5, 10):
        for x in range(5, 11):
            px[x, y] = _rgba(screen_color)
    # Bright center line
    for x in range(6, 10):
        px[x, 7] = _rgba(screen_bright)

    # Status dots at bottom
    px[6, 11] = _rgba((40, 200, 80))   # green dot
    px[9, 11] = _rgba((200, 180, 40))  # yellow dot

    return img


def generate_hazard(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Environmental hazard: damaged floor with orange-red glow."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    px = img.load()

    # Damaged floor base
    floor_color = (55, 50, 45)
    for y in range(16):
        for x in range(16):
            px[x, y] = _rgba(floor_color)

    # Warning stripes (top and bottom borders)
    stripe_color = (200, 160, 40)
    for i in range(16):
        if (i // 2) % 2 == 0:
            px[i, 0] = _rgba(stripe_color)
            px[i, 15] = _rgba(stripe_color)
            if i < 15:
                px[i, 1] = _rgba(stripe_color)
                px[i, 14] = _rgba(stripe_color)

    # Hazard glow (center)
    glow_outer = (180, 70, 30)
    glow_inner = (220, 100, 40)
    glow_core = (255, 140, 50)
    for y in range(4, 12):
        for x in range(4, 12):
            px[x, y] = _rgba(glow_outer)
    for y in range(5, 11):
        for x in range(5, 11):
            px[x, y] = _rgba(glow_inner)
    for y in range(6, 10):
        for x in range(6, 10):
            px[x, y] = _rgba(glow_core)

    # Crack lines
    crack = (100, 40, 20)
    px[3, 6] = _rgba(crack)
    px[4, 7] = _rgba(crack)
    px[11, 5] = _rgba(crack)
    px[12, 6] = _rgba(crack)

    return img


def generate_vent(pal: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Steam vent: metal grate with steam wisps."""
    img = Image.new("RGBA", (16, 16), TRANSPARENT)
    px = img.load()

    # Metal frame
    frame_color = (90, 95, 100)
    frame_dark = (60, 65, 70)
    for y in range(16):
        for x in range(16):
            if x == 0 or x == 15 or y == 0 or y == 15:
                px[x, y] = _rgba(frame_color)
            elif x == 1 or x == 14 or y == 1 or y == 14:
                px[x, y] = _rgba(frame_dark)
            else:
                px[x, y] = _rgba((30, 32, 40))  # dark grate interior

    # Grate slats (horizontal)
    slat_color = (70, 75, 80)
    for y in [3, 5, 7, 9, 11, 13]:
        for x in range(2, 14):
            px[x, y] = _rgba(slat_color)

    # Steam wisps
    steam = (180, 190, 210)
    steam_light = (200, 210, 230)
    px[5, 4] = _rgba(steam)
    px[6, 3] = _rgba(steam_light)
    px[9, 6] = _rgba(steam)
    px[10, 5] = _rgba(steam_light)
    px[7, 8] = _rgba(steam)
    px[8, 7] = _rgba(steam_light)
    px[4, 10] = _rgba(steam)
    px[11, 12] = _rgba(steam)

    return img


TILE_SPRITES = {
    "terminal": generate_terminal,
    "hazard": generate_hazard,
    "vent": generate_vent,
}


# ---------------------------------------------------------------------------
# Generation pipeline
# ---------------------------------------------------------------------------

SPRITES = {
    "player": generate_player,
    "guild_security": generate_guild_security,
    "union_worker": generate_union_worker,
    "pirate_thug": generate_pirate_thug,
    "collective_drone": generate_collective_drone,
    "alliance_scrapper": generate_alliance_scrapper,
    "elite_guard": generate_elite_guard,
    "station_sentry": generate_station_sentry,
    "crimson_enforcer": generate_crimson_enforcer,
}


def generate_all(preview: bool = False) -> None:
    """Generate all ground character and tile sprites."""
    pal = load_palette()

    # Ensure output directories exist
    GROUND_TILES_DIR.mkdir(parents=True, exist_ok=True)
    ENEMIES_DIR.mkdir(parents=True, exist_ok=True)
    NEUTRAL_DIR.mkdir(parents=True, exist_ok=True)

    # Character sprites
    for sprite_id, gen_func in SPRITES.items():
        img = gen_func(pal)

        if sprite_id == "player":
            out_path = GROUND_TILES_DIR / "player.png"
        else:
            out_path = ENEMIES_DIR / f"{sprite_id}.png"

        img.save(out_path)
        print(f"  {sprite_id:25s} -> {out_path.relative_to(ASSETS_DIR)}")

        if preview:
            preview_img = img.resize(
                (128, 128), Image.Resampling.NEAREST
            )
            preview_path = out_path.with_name(f"{sprite_id}_preview.png")
            preview_img.save(preview_path)

    # Tile sprites
    for tile_id, gen_func in TILE_SPRITES.items():
        img = gen_func(pal)
        out_path = NEUTRAL_DIR / f"{tile_id}.png"
        img.save(out_path)
        print(f"  {tile_id:25s} -> {out_path.relative_to(ASSETS_DIR)}")

        if preview:
            preview_img = img.resize(
                (128, 128), Image.Resampling.NEAREST
            )
            preview_path = out_path.with_name(f"{tile_id}_preview.png")
            preview_img.save(preview_path)

    total = len(SPRITES) + len(TILE_SPRITES)
    print(f"\nGenerated {total} ground sprites ({len(SPRITES)} characters, {len(TILE_SPRITES)} tiles).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 16x16 ground character sprites."
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Also generate 8x upscale preview images.",
    )
    args = parser.parse_args()

    print("Ground Character Sprite Generator")
    print(f"  Output: {GROUND_TILES_DIR}")
    print()

    generate_all(preview=args.preview)


if __name__ == "__main__":
    main()
