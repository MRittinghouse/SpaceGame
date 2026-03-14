"""Generate a pixel art game icon (.ico) for the SpaceGame executable.

Creates a simple 32x32 pixel art icon depicting a spaceship silhouette
using the master palette colors.

Usage:
    python -m tools.generate_icon
"""

import json
from pathlib import Path

from PIL import Image

ASSETS_DIR = Path(__file__).resolve().parent.parent / "spacegame" / "data" / "assets"
PALETTE_PATH = ASSETS_DIR / "palettes" / "master_palette.json"
OUTPUT_PATH = ASSETS_DIR / "images" / "icon.ico"


def _rgba(rgb: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
    return (*rgb, a)


def generate_icon() -> None:
    """Generate a 32x32 pixel art .ico file."""
    # Load palette
    with open(PALETTE_PATH) as f:
        data = json.load(f)
    pal = {k: tuple(v) for k, v in data["colors"].items()}

    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    px = img.load()

    # Background: dark space with subtle stars
    bg = (10, 10, 20)
    for y in range(32):
        for x in range(32):
            px[x, y] = _rgba(bg)

    # Stars
    star_color = (180, 190, 220)
    star_dim = (100, 110, 140)
    stars = [(3, 5), (28, 3), (7, 27), (25, 22), (15, 2), (1, 18), (30, 14)]
    for sx, sy in stars:
        px[sx, sy] = _rgba(star_color)
    dim_stars = [(10, 8), (22, 28), (5, 15), (27, 9), (18, 25)]
    for sx, sy in dim_stars:
        px[sx, sy] = _rgba(star_dim)

    # Ship body (top-down, pointing up) — bright accent color
    hull = pal.get("ui_accent_bright", (100, 200, 255))
    hull_dark = pal.get("ui_accent", (60, 140, 200))
    engine = pal.get("engine_orange", (255, 160, 60))
    engine_glow = pal.get("engine_yellow", (255, 220, 100))

    # Ship hull (diamond/arrow shape centered)
    cx, cy = 16, 14
    # Nose (top)
    px[cx, cy - 6] = _rgba(hull)
    for dx in range(-1, 2):
        px[cx + dx, cy - 5] = _rgba(hull)
    for dx in range(-2, 3):
        px[cx + dx, cy - 4] = _rgba(hull)
    for dx in range(-2, 3):
        px[cx + dx, cy - 3] = _rgba(hull)
    # Body
    for dy in range(-2, 4):
        for dx in range(-3, 4):
            px[cx + dx, cy + dy] = _rgba(hull)
    # Wings
    for dy in range(-1, 3):
        px[cx - 4, cy + dy] = _rgba(hull_dark)
        px[cx + 4, cy + dy] = _rgba(hull_dark)
    px[cx - 5, cy] = _rgba(hull_dark)
    px[cx + 5, cy] = _rgba(hull_dark)
    px[cx - 5, cy + 1] = _rgba(hull_dark)
    px[cx + 5, cy + 1] = _rgba(hull_dark)

    # Cockpit (bright center line)
    cockpit = pal.get("ui_health_high", (80, 220, 120))
    px[cx, cy - 4] = _rgba(cockpit)
    px[cx, cy - 3] = _rgba(cockpit)

    # Engine glow (bottom)
    for dx in range(-2, 3):
        px[cx + dx, cy + 4] = _rgba(engine)
    for dx in range(-1, 2):
        px[cx + dx, cy + 5] = _rgba(engine_glow)
    px[cx, cy + 6] = _rgba(engine_glow)

    # Save as .ico with multiple sizes
    sizes = [img, img.resize((16, 16), Image.Resampling.NEAREST)]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT_PATH, format="ICO", sizes=[(32, 32), (16, 16)])
    print(f"Generated icon: {OUTPUT_PATH}")


def main() -> None:
    generate_icon()


if __name__ == "__main__":
    main()
