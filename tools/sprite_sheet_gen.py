"""Sprite sheet generator — creates animated sprite sheets from static PNGs.

Takes existing static sprite PNGs and applies algorithmic animation transforms
to produce multi-frame horizontal strip sprite sheets and animation config JSON.

Transforms are deterministic (same input -> same output), palette-consistent
(only modifies existing pixel colors), and frame-aligned (pixel-perfect
registration). No AI generation — pure pixel manipulation.

Usage:
    python -m tools.sprite_sheet_gen              # Generate all configured sheets
    python -m tools.sprite_sheet_gen --category ships  # Only ship sprites
    python -m tools.sprite_sheet_gen --dry-run     # Preview what would be generated

Available transforms:
    engine_glow  — Pulse engine-area pixels brighter (ships)
    breathe      — Subtle 1px vertical shift (portraits)
    blink        — Darken eye-region pixels in one frame (portraits)
    color_pulse  — Cycle brightness on bright pixels (commodities, upgrades)
    shimmer      — Shift highlight pixels between frames (factions, UI)
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image


# ============================================================================
# ANIMATION TRANSFORMS
# ============================================================================


def engine_glow(
    img: Image.Image,
    num_frames: int = 2,
    intensity: float = 0.4,
) -> list[Image.Image]:
    """Create frames with pulsing engine brightness.

    Detects 'engine' pixels (warm, bright pixels in the bottom third of the
    sprite) and cycles their brightness across frames.

    Args:
        img: Source RGBA image (typically 32x32 ship sprite).
        num_frames: Number of animation frames to generate.
        intensity: How much to vary brightness (0.0-1.0).

    Returns:
        List of RGBA frames.
    """
    w, h = img.size
    px_src = img.load()

    # Identify engine pixels: warm bright pixels in the bottom 40% of the sprite
    engine_zone_top = int(h * 0.6)
    engine_pixels: set[tuple[int, int]] = set()

    for y in range(engine_zone_top, h):
        for x in range(w):
            r, g, b, a = px_src[x, y]
            if a == 0:
                continue
            # "Warm bright" = high red/yellow, luminance > 120
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            warmth = r - b  # Positive = warm
            if luminance > 120 and warmth > 20:
                engine_pixels.add((x, y))

    frames: list[Image.Image] = []
    for i in range(num_frames):
        frame = img.copy()
        if not engine_pixels:
            frames.append(frame)
            continue

        px = frame.load()
        # Brightness cycle evenly spaced around the unit circle
        # For 2 frames: frame 0 = base (1.0), frame 1 = bright (1.0 + intensity)
        phase = (2 * math.pi * i) / num_frames
        glow = 1.0 + intensity * 0.5 * (1 + math.cos(phase))

        for x, y in engine_pixels:
            r, g, b, a = px_src[x, y]
            px[x, y] = (
                min(255, int(r * glow)),
                min(255, int(g * glow)),
                min(255, int(b * glow * 0.9)),  # Slightly less blue glow
                a,
            )

        frames.append(frame)

    return frames


def breathe(
    img: Image.Image,
    num_frames: int = 2,
) -> list[Image.Image]:
    """Create a subtle 1px vertical shift animation for breathing.

    Frame 0 is the original. Frame 1 shifts opaque content up by 1px
    (bottom row fills with the row above it). Creates a gentle breathing effect.

    Args:
        img: Source RGBA image (typically 50x60 portrait).
        num_frames: Number of frames (2 recommended).

    Returns:
        List of RGBA frames.
    """
    frames: list[Image.Image] = [img.copy()]

    for i in range(1, num_frames):
        frame = img.copy()
        w, h = frame.size
        px_src = img.load()
        px_dst = frame.load()

        # Determine shift: oscillate between 0 and 1px up
        shift = 1 if (i % 2 == 1) else 0

        if shift:
            for y in range(h):
                for x in range(w):
                    src_y = min(y + shift, h - 1)
                    px_dst[x, y] = px_src[x, src_y]

        frames.append(frame)

    return frames


def blink(
    img: Image.Image,
    num_frames: int = 2,
) -> list[Image.Image]:
    """Create frames where one has darkened 'eye' pixels.

    Detects the eye region (dark opaque pixels in the upper-middle area of the
    sprite) and creates a blink frame where those pixels and surrounding
    skin-tone pixels are darkened.

    Args:
        img: Source RGBA image (typically 50x60 portrait).
        num_frames: Number of frames (2 recommended — open, closed).

    Returns:
        List of RGBA frames.
    """
    w, h = img.size
    px_src = img.load()

    # Find eye candidates: dark opaque pixels in upper-middle region
    eye_zone = (int(w * 0.2), int(h * 0.25), int(w * 0.8), int(h * 0.5))
    eye_pixels: set[tuple[int, int]] = set()

    for y in range(eye_zone[1], eye_zone[3]):
        for x in range(eye_zone[0], eye_zone[2]):
            r, g, b, a = px_src[x, y]
            if a == 0:
                continue
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            if luminance < 80:  # Dark pixel = likely eye/eyebrow
                eye_pixels.add((x, y))

    # Expand eye region by 1px to include eyelid
    blink_pixels: set[tuple[int, int]] = set(eye_pixels)
    for ex, ey in eye_pixels:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = ex + dx, ey + dy
            if 0 <= nx < w and 0 <= ny < h and px_src[nx, ny][3] > 0:
                blink_pixels.add((nx, ny))

    frames: list[Image.Image] = [img.copy()]  # Frame 0 = eyes open

    for i in range(1, num_frames):
        frame = img.copy()
        if not blink_pixels:
            frames.append(frame)
            continue

        px = frame.load()
        # Darken blink pixels (simulate closed eyes)
        for x, y in blink_pixels:
            r, g, b, a = px_src[x, y]
            darken = 0.5  # 50% darker
            px[x, y] = (
                max(0, int(r * darken)),
                max(0, int(g * darken)),
                max(0, int(b * darken)),
                a,
            )

        frames.append(frame)

    return frames


def _expression_tint(
    img: Image.Image,
    r_shift: float = 0.0,
    g_shift: float = 0.0,
    b_shift: float = 0.0,
    brightness: float = 1.0,
) -> Image.Image:
    """Apply a color tint and brightness shift to create an expression variant.

    Args:
        img: Source RGBA image.
        r_shift: Red channel shift (-1.0 to 1.0).
        g_shift: Green channel shift (-1.0 to 1.0).
        b_shift: Blue channel shift (-1.0 to 1.0).
        brightness: Overall brightness multiplier.

    Returns:
        Tinted copy of the image.
    """
    result = img.copy()
    w, h = result.size
    px_src = img.load()
    px_dst = result.load()

    for y in range(h):
        for x in range(w):
            r, g, b, a = px_src[x, y]
            if a == 0:
                continue
            nr = min(255, max(0, int((r + r_shift * 40) * brightness)))
            ng = min(255, max(0, int((g + g_shift * 40) * brightness)))
            nb = min(255, max(0, int((b + b_shift * 40) * brightness)))
            px_dst[x, y] = (nr, ng, nb, a)

    return result


def expression_neutral(
    img: Image.Image, num_frames: int = 2
) -> list[Image.Image]:
    """Neutral expression with breathing animation (same as base)."""
    return breathe(img, num_frames)


def expression_happy(
    img: Image.Image, num_frames: int = 2
) -> list[Image.Image]:
    """Happy/confident expression: warmer, slightly brighter."""
    tinted = _expression_tint(img, r_shift=0.4, g_shift=0.2, b_shift=-0.2, brightness=1.06)
    return breathe(tinted, num_frames)


def expression_angry(
    img: Image.Image, num_frames: int = 2
) -> list[Image.Image]:
    """Angry/stern expression: redder, slightly darker."""
    tinted = _expression_tint(img, r_shift=0.5, g_shift=-0.3, b_shift=-0.3, brightness=0.92)
    return breathe(tinted, num_frames)


def expression_surprised(
    img: Image.Image, num_frames: int = 2
) -> list[Image.Image]:
    """Surprised expression: brighter, especially around eyes."""
    tinted = _expression_tint(img, r_shift=0.1, g_shift=0.1, b_shift=0.3, brightness=1.1)
    return breathe(tinted, num_frames)


def color_pulse(
    img: Image.Image,
    num_frames: int = 2,
    intensity: float = 0.25,
) -> list[Image.Image]:
    """Cycle brightness on bright opaque pixels.

    Good for crystals, ores, and glowing commodities. Bright pixels
    (luminance > 100) get a sinusoidal brightness shift.

    Args:
        img: Source RGBA image (typically 16x16 commodity/upgrade icon).
        num_frames: Number of animation frames.
        intensity: Brightness variation factor.

    Returns:
        List of RGBA frames.
    """
    w, h = img.size
    px_src = img.load()

    # Find bright opaque pixels
    bright_pixels: set[tuple[int, int]] = set()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px_src[x, y]
            if a == 0:
                continue
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            if luminance > 100:
                bright_pixels.add((x, y))

    frames: list[Image.Image] = []
    for i in range(num_frames):
        frame = img.copy()
        if not bright_pixels:
            frames.append(frame)
            continue

        px = frame.load()
        t = i / max(1, num_frames - 1) if num_frames > 1 else 0
        shift = 1.0 + intensity * math.sin(t * math.pi * 2)

        for x, y in bright_pixels:
            r, g, b, a = px_src[x, y]
            px[x, y] = (
                min(255, int(r * shift)),
                min(255, int(g * shift)),
                min(255, int(b * shift)),
                a,
            )

        frames.append(frame)

    return frames


def shimmer(
    img: Image.Image,
    num_frames: int = 2,
    intensity: float = 0.3,
) -> list[Image.Image]:
    """Shift highlight pixels between frames for a metallic shimmer.

    Creates a sweep effect where brightness moves across the sprite
    diagonally, like light reflecting off a surface.

    Args:
        img: Source RGBA image (typically 24x24 faction emblem).
        num_frames: Number of animation frames.
        intensity: How much to brighten the highlight band.

    Returns:
        List of RGBA frames.
    """
    w, h = img.size
    px_src = img.load()
    diag = w + h  # Diagonal distance for sweep

    frames: list[Image.Image] = []
    for i in range(num_frames):
        frame = img.copy()
        px = frame.load()

        # Sweep position along diagonal
        t = i / max(1, num_frames - 1) if num_frames > 1 else 0
        sweep_pos = t * diag
        band_width = max(3, diag // 4)

        for y in range(h):
            for x in range(w):
                r, g, b, a = px_src[x, y]
                if a == 0:
                    continue

                # Distance from sweep line (diagonal)
                d = abs((x + y) - sweep_pos)
                if d < band_width:
                    # Brighten based on proximity to sweep center
                    factor = 1.0 + intensity * (1.0 - d / band_width)
                    px[x, y] = (
                        min(255, int(r * factor)),
                        min(255, int(g * factor)),
                        min(255, int(b * factor)),
                        a,
                    )

        frames.append(frame)

    return frames


def destroy(
    img: Image.Image,
    num_frames: int = 4,
) -> list[Image.Image]:
    """Create a ship destruction sequence.

    Progressively breaks the ship apart: flash -> fragment -> scatter -> fade.
    Uses only the existing pixels — fragments them outward from center.

    Args:
        img: Source RGBA image (typically 32x32 ship sprite).
        num_frames: Number of destruction frames (4 recommended).

    Returns:
        List of RGBA frames showing progressive destruction.
    """
    import random as _rand

    w, h = img.size
    px_src = img.load()
    cx, cy = w // 2, h // 2

    # Collect all opaque pixels with their colors
    pixels: list[tuple[int, int, tuple[int, int, int, int]]] = []
    for y in range(h):
        for x in range(w):
            rgba = px_src[x, y]
            if rgba[3] > 0:
                pixels.append((x, y, rgba))

    # Assign each pixel a random "fragment group" and explosion direction
    rng = _rand.Random(42)  # Deterministic
    fragment_data = []
    for x, y, rgba in pixels:
        # Direction away from center with some randomness
        dx = (x - cx) + rng.uniform(-2, 2)
        dy = (y - cy) + rng.uniform(-2, 2)
        # Normalize and scale
        dist = max(1, (dx * dx + dy * dy) ** 0.5)
        dx, dy = dx / dist, dy / dist
        speed = rng.uniform(0.5, 2.0)
        fragment_data.append((x, y, rgba, dx * speed, dy * speed))

    frames: list[Image.Image] = []
    for i in range(num_frames):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = frame.load()

        # Progress: 0.0 (intact) -> 1.0 (fully scattered)
        t = (i + 1) / num_frames

        if t <= 0.25:
            # Frame 1: White flash — brighten all pixels
            flash = 1.0 + 2.0 * (t / 0.25)
            for x, y, rgba, _, _ in fragment_data:
                r, g, b, a = rgba
                px[x, y] = (
                    min(255, int(r * flash)),
                    min(255, int(g * flash)),
                    min(255, int(b * flash)),
                    a,
                )
        else:
            # Frames 2-4: Fragment and scatter with fading alpha
            scatter_t = (t - 0.25) / 0.75  # 0.0 to 1.0 over frames 2-4
            fade = max(0, int(255 * (1.0 - scatter_t * 0.8)))

            for x, y, rgba, vx, vy in fragment_data:
                # Move pixel outward
                displacement = scatter_t * 8  # Max 8 pixels outward
                nx = int(x + vx * displacement)
                ny = int(y + vy * displacement)

                if 0 <= nx < w and 0 <= ny < h:
                    r, g, b, a = rgba
                    # Tint orange/red for explosion coloring
                    fire_mix = scatter_t * 0.6
                    fr = min(255, int(r * (1 - fire_mix) + 255 * fire_mix))
                    fg = min(255, int(g * (1 - fire_mix) + 120 * fire_mix))
                    fb = max(0, int(b * (1 - fire_mix * 1.5)))
                    new_a = min(a, fade)
                    px[nx, ny] = (fr, fg, fb, new_a)

        frames.append(frame)

    return frames


# ============================================================================
# SHEET ASSEMBLY
# ============================================================================


def make_sprite_sheet(frames: list[Image.Image]) -> Image.Image:
    """Combine frames into a horizontal strip sprite sheet.

    Args:
        frames: List of same-sized RGBA frames.

    Returns:
        RGBA image with frames side-by-side (width = frame_w * count).
    """
    if not frames:
        raise ValueError("Cannot create sheet from empty frame list")

    fw, fh = frames[0].size
    sheet = Image.new("RGBA", (fw * len(frames), fh), (0, 0, 0, 0))

    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * fw, 0))

    return sheet


def generate_animation_config(
    num_frames: int,
    frame_duration: float,
    loop: bool = True,
) -> dict:
    """Generate a JSON-ready animation config dict.

    Creates an "idle" animation that cycles through all frames.

    Args:
        num_frames: Number of frames in the sheet.
        frame_duration: Seconds per frame.
        loop: Whether the animation loops.

    Returns:
        Dict suitable for writing to animation config JSON.
    """
    return {
        "idle": {
            "name": "idle",
            "frames": list(range(num_frames)),
            "frame_duration": frame_duration,
            "loop": loop,
        }
    }


# ============================================================================
# BATCH CONFIGURATION
# ============================================================================


# Transform function registry
TRANSFORMS = {
    "engine_glow": engine_glow,
    "breathe": breathe,
    "blink": blink,
    "color_pulse": color_pulse,
    "shimmer": shimmer,
    "destroy": destroy,
    "expression_neutral": expression_neutral,
    "expression_happy": expression_happy,
    "expression_angry": expression_angry,
    "expression_surprised": expression_surprised,
}

# Sprite sheet generation config
# Each entry defines: which sprites get which transform
SHEET_CONFIGS: list[dict] = [
    {
        "name": "Player Ships",
        "category": "ships/player",
        "transforms": [
            {"transform": "engine_glow", "num_frames": 2},
            {"transform": "destroy", "num_frames": 4},
        ],
        "frame_duration": 0.5,
        "anim_config_file": "ship_anims.json",
    },
    {
        "name": "Enemy Ships",
        "category": "ships/enemies",
        "transforms": [
            {"transform": "engine_glow", "num_frames": 2},
            {"transform": "destroy", "num_frames": 4},
        ],
        "frame_duration": 0.5,
        "anim_config_file": "ship_anims.json",
    },
    {
        "name": "Portraits",
        "category": "portraits",
        "transforms": [
            {"transform": "expression_neutral", "num_frames": 2, "anim_name": "idle", "aliases": ["neutral"]},
            {"transform": "expression_happy", "num_frames": 2, "anim_name": "happy", "aliases": ["confident"]},
            {"transform": "expression_angry", "num_frames": 2, "anim_name": "angry", "aliases": ["stern"]},
            {"transform": "expression_surprised", "num_frames": 2, "anim_name": "surprised"},
        ],
        "frame_duration": 0.8,
        "anim_config_file": "portrait_anims.json",
    },
    {
        "name": "Commodities",
        "category": "commodities",
        "transform": "color_pulse",
        "num_frames": 2,
        "frame_duration": 0.6,
        "anim_config_file": None,  # No shared anim config needed
    },
    {
        "name": "Ground Tiles (Neutral)",
        "category": "ground_tiles/neutral",
        "transform": "color_pulse",
        "num_frames": 2,
        "frame_duration": 0.6,
        "anim_config_file": "ground_tile_anims.json",
        "only": ["noisy_floor", "terminal", "hazard", "vent"],
    },
    {
        "name": "Faction Emblems",
        "category": "factions",
        "transform": "shimmer",
        "num_frames": 2,
        "frame_duration": 0.7,
        "anim_config_file": None,
    },
]


# ============================================================================
# GENERATION PIPELINE
# ============================================================================


def find_static_sprites(sprites_dir: Path, category: str) -> list[tuple[str, Path]]:
    """Find all static (non-sheet, non-raw, non-preview) PNGs in a category.

    Args:
        sprites_dir: Root sprites directory.
        category: Subdirectory path (e.g. "ships/player").

    Returns:
        List of (sprite_id, file_path) tuples.
    """
    cat_dir = sprites_dir / category
    if not cat_dir.exists():
        return []

    results = []
    for f in sorted(cat_dir.iterdir()):
        if not f.suffix == ".png":
            continue
        if f.name.startswith("_"):
            continue
        if f.name.endswith("_raw.png"):
            continue
        if f.name.endswith("_sheet.png"):
            continue
        sprite_id = f.stem
        results.append((sprite_id, f))

    return results


def generate_sheets(
    sprites_dir: Path,
    animations_dir: Path,
    configs: Optional[list[dict]] = None,
    category_filter: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Generate sprite sheets for all configured categories.

    Args:
        sprites_dir: Root sprites directory (spacegame/data/assets/sprites/).
        animations_dir: Animation configs directory (spacegame/data/assets/animations/).
        configs: Sheet configs to process. Defaults to SHEET_CONFIGS.
        category_filter: If set, only process this category.
        dry_run: If True, don't write files — just report what would be done.

    Returns:
        Summary dict with counts and details.
    """
    if configs is None:
        configs = SHEET_CONFIGS

    animations_dir.mkdir(parents=True, exist_ok=True)

    summary: dict = {
        "sheets_generated": 0,
        "sheets_skipped": 0,
        "anim_configs_written": 0,
        "details": [],
    }

    # Track anim configs to merge (multiple categories may share one file)
    anim_configs: dict[str, dict] = {}

    for config in configs:
        category = config["category"]
        if category_filter and category_filter not in category:
            continue

        frame_duration = config["frame_duration"]
        anim_file = config.get("anim_config_file")

        # Support both single-transform and multi-transform configs
        if "transforms" in config:
            transform_steps = config["transforms"]
        else:
            transform_steps = [
                {"transform": config["transform"], "num_frames": config["num_frames"]}
            ]

        sprites = find_static_sprites(sprites_dir, category)
        # Filter to only specific sprites if requested
        only_ids = config.get("only")
        if only_ids:
            sprites = [(sid, sp) for sid, sp in sprites if sid in only_ids]
        if not sprites:
            summary["details"].append(
                f"  {config['name']}: no sprites found in {category}/"
            )
            continue

        total_frames = sum(step["num_frames"] for step in transform_steps)
        transform_desc = "+".join(s["transform"] for s in transform_steps)

        generated = 0
        for sprite_id, sprite_path in sprites:
            sheet_path = sprite_path.parent / f"{sprite_id}_sheet.png"

            if dry_run:
                summary["details"].append(
                    f"  [DRY RUN] {category}/{sprite_id} "
                    f"-> {sheet_path.name} ({total_frames} frames, {transform_desc})"
                )
                summary["sheets_generated"] += 1
                continue

            # Load source sprite
            img = Image.open(sprite_path).convert("RGBA")

            # Apply all transforms and concatenate frames
            all_frames: list[Image.Image] = []
            for step in transform_steps:
                transform_fn = TRANSFORMS[step["transform"]]
                step_frames = transform_fn(img, num_frames=step["num_frames"])
                all_frames.extend(step_frames)

            # Assemble sheet
            sheet = make_sprite_sheet(all_frames)
            sheet.save(str(sheet_path), "PNG")

            generated += 1
            summary["sheets_generated"] += 1

            # Track anim config
            if anim_file and anim_file not in anim_configs:
                anim_configs[anim_file] = config

        if not dry_run and generated > 0:
            summary["details"].append(
                f"  {config['name']}: {generated} sheets "
                f"({total_frames} frames, {transform_desc})"
            )

    # Write animation config files
    for anim_file, source_config in anim_configs.items():
        anim_path = animations_dir / anim_file

        if "transforms" in source_config:
            # Multi-transform: build named animations with frame ranges
            anim_data = {}
            frame_offset = 0
            for step in source_config["transforms"]:
                n = step["num_frames"]
                name = step.get("anim_name", step["transform"])
                # Map transform names to animation names
                if name == "engine_glow":
                    name = "idle"
                entry = {
                    "name": name,
                    "frames": list(range(frame_offset, frame_offset + n)),
                    "frame_duration": source_config["frame_duration"]
                    if name != "destroy"
                    else 0.12,
                    "loop": name != "destroy",
                }
                anim_data[name] = entry
                # Add expression aliases
                for alias in step.get("aliases", []):
                    alias_entry = dict(entry)
                    alias_entry["name"] = alias
                    anim_data[alias] = alias_entry
                frame_offset += n
        else:
            anim_data = generate_animation_config(
                num_frames=source_config["num_frames"],
                frame_duration=source_config["frame_duration"],
            )

        if not dry_run:
            with open(anim_path, "w") as f:
                json.dump(anim_data, f, indent=2)
            summary["anim_configs_written"] += 1
            summary["details"].append(
                f"  Animation config: {anim_file}"
            )

    return summary


# ============================================================================
# CLI ENTRY POINT
# ============================================================================


def main() -> None:
    """CLI entry point for sprite sheet generation."""
    parser = argparse.ArgumentParser(
        description="Generate animated sprite sheets from static PNGs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--category",
        help="Only generate for this category (e.g. 'ships', 'portraits')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be generated without writing files",
    )
    parser.add_argument(
        "--assets-dir",
        default=None,
        help="Override assets directory path",
    )
    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent
    if args.assets_dir:
        assets_dir = Path(args.assets_dir)
    else:
        assets_dir = project_root / "spacegame" / "data" / "assets"

    sprites_dir = assets_dir / "sprites"
    animations_dir = assets_dir / "animations"

    if not sprites_dir.exists():
        print(f"Error: Sprites directory not found: {sprites_dir}")
        sys.exit(1)

    print(f"Sprite Sheet Generator")
    print(f"  Sprites:    {sprites_dir}")
    print(f"  Animations: {animations_dir}")
    if args.dry_run:
        print(f"  Mode:       DRY RUN")
    print()

    result = generate_sheets(
        sprites_dir=sprites_dir,
        animations_dir=animations_dir,
        category_filter=args.category,
        dry_run=args.dry_run,
    )

    for detail in result["details"]:
        print(detail)

    print()
    print(f"Generated: {result['sheets_generated']} sprite sheets")
    if result["anim_configs_written"]:
        print(f"Written:   {result['anim_configs_written']} animation configs")


if __name__ == "__main__":
    main()
