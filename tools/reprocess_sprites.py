"""Batch re-process raw AI concept art through the improved pixel pipeline.

Reads *_raw.png files from a sprite directory, runs each through
process_sprite(), and writes the result alongside the raw file.
Backs up the old processed sprite as *_old.png for comparison.

Usage:
    python tools/reprocess_sprites.py [--dir sprites/commodities] [--size 16]
"""

import argparse
import json
import glob
import os
import shutil
import sys

from PIL import Image

# Add project root to path so we can import tools.pixel_pipeline
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.pixel_pipeline import process_sprite


ASSETS_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "spacegame", "data", "assets",
)


def load_master_palette() -> list[tuple[int, int, int]]:
    """Load the master palette colors as a list of RGB tuples."""
    palette_path = os.path.join(ASSETS_BASE, "palettes", "master_palette.json")
    with open(palette_path, "r") as f:
        data = json.load(f)
    return [tuple(c) for c in data["colors"].values()]


def reprocess_directory(
    sprite_dir: str,
    size: tuple[int, int],
    palette: list[tuple[int, int, int]],
    intermediate_scale: int = 2,
) -> dict[str, str]:
    """Re-process all *_raw.png files in a directory.

    For each raw file:
    1. Back up existing processed sprite as *_old.png
    2. Run raw through process_sprite()
    3. Save result as the processed sprite

    Args:
        sprite_dir: Absolute path to the sprite directory.
        size: Target sprite dimensions (width, height).
        palette: List of (R, G, B) palette colors.
        intermediate_scale: Multiplier for two-stage resize.

    Returns:
        Dict mapping sprite name to status ("ok", "skipped", or error message).
    """
    results = {}
    raw_files = sorted(glob.glob(os.path.join(sprite_dir, "*_raw.png")))

    if not raw_files:
        print(f"No *_raw.png files found in {sprite_dir}")
        return results

    for raw_path in raw_files:
        basename = os.path.basename(raw_path)
        sprite_name = basename.replace("_raw.png", "")
        processed_path = os.path.join(sprite_dir, f"{sprite_name}.png")
        old_path = os.path.join(sprite_dir, f"{sprite_name}_old.png")

        try:
            # Back up existing processed sprite
            if os.path.exists(processed_path):
                shutil.copy2(processed_path, old_path)

            # Load raw and process
            raw_img = Image.open(raw_path)
            result = process_sprite(
                raw_img,
                size,
                palette,
                outline_color=(10, 10, 15),
                intermediate_scale=intermediate_scale,
            )
            result.save(processed_path)
            results[sprite_name] = "ok"
            print(f"  {sprite_name}: processed {raw_img.size} -> {size}")

        except Exception as e:
            results[sprite_name] = str(e)
            print(f"  {sprite_name}: ERROR - {e}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-process raw sprites through improved pipeline")
    parser.add_argument(
        "--dir",
        default="sprites/commodities",
        help="Sprite subdirectory relative to assets (default: sprites/commodities)",
    )
    parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        default=[16, 16],
        metavar=("W", "H"),
        help="Target sprite size (default: 16 16)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Intermediate scale factor for two-stage resize (default: 2)",
    )
    args = parser.parse_args()

    sprite_dir = os.path.join(ASSETS_BASE, args.dir)
    size = (args.size[0], args.size[1])

    if not os.path.isdir(sprite_dir):
        print(f"Directory not found: {sprite_dir}")
        sys.exit(1)

    print(f"Loading master palette...")
    palette = load_master_palette()
    print(f"  {len(palette)} colors loaded")

    print(f"\nRe-processing sprites in: {sprite_dir}")
    print(f"  Target size: {size[0]}x{size[1]}")
    print(f"  Intermediate scale: {args.scale}x")
    print()

    results = reprocess_directory(sprite_dir, size, palette, intermediate_scale=args.scale)

    ok_count = sum(1 for v in results.values() if v == "ok")
    err_count = len(results) - ok_count
    print(f"\nDone: {ok_count} processed, {err_count} errors")
    if ok_count > 0:
        print(f"Old sprites backed up as *_old.png for comparison")


if __name__ == "__main__":
    main()
