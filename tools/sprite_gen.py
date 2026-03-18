"""Manifest-driven sprite generation pipeline.

Reads sprite_manifest.json and generates game-ready sprites using
Google NanoBanano (high-value art) or Gemini 2.5 Flash (icons/functional),
with Pillow post-processing to match existing game asset style.

Usage:
    python -m tools.sprite_gen                          # Generate all sprites
    python -m tools.sprite_gen --category mining        # Only mining sprites
    python -m tools.sprite_gen --id rock_iron_ore       # Single sprite
    python -m tools.sprite_gen --dry-run                # Preview without generating
    python -m tools.sprite_gen --skip-existing          # Skip sprites that already exist
    python -m tools.sprite_gen --validate               # One sprite per category to verify
"""

import argparse
import base64
import json
import os
import sys
import time
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from PIL import Image

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SPRITES_DIR = PROJECT_ROOT / "spacegame" / "data" / "assets" / "sprites"
RAW_DIR = PROJECT_ROOT / "spacegame" / "data" / "assets" / "sprites" / "_raw"
MANIFEST_PATH = PROJECT_ROOT / "data" / "assets" / "sprite_manifest.json"

# Rate limiting (seconds between API calls)
RATE_LIMITS = {"openai": 1.0, "gemini": 1.5, "nano": 2.0}

# Max retries on API failure
MAX_RETRIES = 2


# ============================================================================
# BACKENDS
# ============================================================================


def generate_openai(prompt: str, size: tuple[int, int]) -> Optional[Image.Image]:
    """Generate an image using OpenAI DALL-E 3.

    Args:
        prompt: Image generation prompt.
        size: Target (width, height) — used for aspect ratio hinting.

    Returns:
        PIL Image or None on failure.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ERROR: OPENAI_API_KEY not found in environment")
        return None

    client = OpenAI(api_key=api_key)

    # DALL-E 3 only supports specific sizes
    dall_e_size = "1024x1024"
    if size[0] > size[1] * 1.5:
        dall_e_size = "1792x1024"
    elif size[1] > size[0] * 1.5:
        dall_e_size = "1024x1792"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=dall_e_size,
            quality="standard",
            n=1,
            response_format="b64_json",
        )
        b64_data = response.data[0].b64_json
        img_bytes = base64.b64decode(b64_data)
        return Image.open(BytesIO(img_bytes)).convert("RGBA")
    except Exception as e:
        print(f"  ERROR (OpenAI): {e}")
        return None


def _gemini_generate(
    prompt: str, model: str, label: str, timeout: int = 120
) -> Optional[Image.Image]:
    """Shared Gemini API image generation logic.

    Args:
        prompt: Image generation prompt.
        model: Gemini model name.
        label: Display label for error messages.
        timeout: Request timeout in seconds.

    Returns:
        PIL Image or None on failure.
    """
    import requests

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(f"  ERROR: GEMINI_API_KEY not found in environment")
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    b64_data = part["inlineData"]["data"]
                    img_bytes = base64.b64decode(b64_data)
                    return Image.open(BytesIO(img_bytes)).convert("RGBA")

        print(f"  ERROR ({label}): No image in response")
        return None
    except Exception as e:
        print(f"  ERROR ({label}): {e}")
        return None


def generate_gemini(prompt: str, size: tuple[int, int]) -> Optional[Image.Image]:
    """Generate via Gemini 2.5 Flash Image (fast, good for icons)."""
    return _gemini_generate(prompt, "gemini-2.5-flash-image", "Gemini")


def generate_nano(prompt: str, size: tuple[int, int]) -> Optional[Image.Image]:
    """Generate via NanoBanano (higher quality, best for detailed art)."""
    return _gemini_generate(prompt, "nano-banana-pro-preview", "NanoBanano")


BACKENDS = {
    "openai": generate_openai,
    "gemini": generate_gemini,
    "nano": generate_nano,
}


# ============================================================================
# POST-PROCESSING
# ============================================================================


def _has_transparency(img: Image.Image, threshold: float = 0.05) -> bool:
    """Check if image already has significant transparency.

    Args:
        img: RGBA image.
        threshold: Fraction of pixels that must be transparent.

    Returns:
        True if the image already has transparency baked in.
    """
    alpha = img.split()[3]
    pixels = list(alpha.tobytes())
    transparent_count = sum(1 for a in pixels if a < 128)
    return (transparent_count / len(pixels)) > threshold


def _remove_background_flood(img: Image.Image, tolerance: int = 35) -> Image.Image:
    """Remove background using edge-flood approach.

    Starts from all edge pixels, marks connected pixels within color
    tolerance of the seed as transparent. More robust than corner-only
    sampling for centered sprites with varied backgrounds.

    Args:
        img: RGBA image.
        tolerance: Color distance threshold.

    Returns:
        Image with background made transparent.
    """
    w, h = img.size
    px = img.load()
    visited = set()
    to_clear = set()

    # Seed from all edge pixels
    edge_pixels = set()
    for x in range(w):
        edge_pixels.add((x, 0))
        edge_pixels.add((x, h - 1))
    for y in range(h):
        edge_pixels.add((0, y))
        edge_pixels.add((w - 1, y))

    # Find dominant edge color
    edge_colors = [px[x, y][:3] for x, y in edge_pixels if px[x, y][3] > 128]
    if not edge_colors:
        return img  # Already transparent edges

    bg_color = Counter(
        tuple((c // 16) * 16 for c in col) for col in edge_colors
    ).most_common(1)[0][0]
    # Use the actual average of the dominant bucket
    matching = [c for c in edge_colors if all(abs(a - b) < 24 for a, b in zip(c, bg_color))]
    if matching:
        bg_color = tuple(sum(c[i] for c in matching) // len(matching) for i in range(3))

    # Flood fill from edges
    stack = list(edge_pixels)
    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        visited.add((x, y))

        r, g, b, a = px[x, y]
        if a < 128:
            to_clear.add((x, y))
            # Continue flood through transparent pixels
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((x + dx, y + dy))
            continue

        dist = abs(r - bg_color[0]) + abs(g - bg_color[1]) + abs(b - bg_color[2])
        if dist < tolerance:
            to_clear.add((x, y))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((x + dx, y + dy))

    result = img.copy()
    rpx = result.load()
    for x, y in to_clear:
        rpx[x, y] = (0, 0, 0, 0)

    return result


def _quantize_palette(img: Image.Image, max_colors: int = 16) -> Image.Image:
    """Reduce color count while preserving transparency.

    Args:
        img: RGBA image.
        max_colors: Maximum number of opaque colors.

    Returns:
        Palette-reduced RGBA image.
    """
    alpha = img.split()[3]
    rgb = img.convert("RGB")
    quantized = rgb.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
    quantized_rgb = quantized.convert("RGB")
    result = quantized_rgb.convert("RGBA")
    result.putalpha(alpha)
    return result


def post_process(
    img: Image.Image,
    target_size: tuple[int, int],
) -> Image.Image:
    """Post-process a generated image into a game-ready sprite.

    Intelligent pipeline that adapts based on the input:
    1. Crop to target aspect ratio from center
    2. Downscale to intermediate size (2x target) with LANCZOS for quality
    3. Final resize to target with NEAREST for crisp pixel edges
    4. Remove background only if image lacks existing transparency
    5. Quantize palette (scaled to sprite size)

    Args:
        img: Raw generated image (large, from API).
        target_size: Final (width, height) in pixels.

    Returns:
        Processed RGBA image at target_size.
    """
    w, h = img.size
    tw, th = target_size

    # Step 1: Crop to target aspect ratio from center
    target_aspect = tw / th
    current_aspect = w / h

    if abs(current_aspect - target_aspect) > 0.05:
        if current_aspect > target_aspect:
            new_w = int(h * target_aspect)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_aspect)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

    # Step 2: Two-stage downscale for best quality
    # First pass: LANCZOS to 4x target (preserves detail while reducing noise)
    # Second pass: NEAREST to final (gives crisp pixel edges)
    intermediate = (tw * 4, th * 4)
    if img.size[0] > intermediate[0]:
        img = img.resize(intermediate, Image.LANCZOS)

    # Step 3: Background removal (only if image doesn't already have transparency)
    if not _has_transparency(img):
        img = _remove_background_flood(img)

    # Step 4: Final resize with NEAREST for pixel-perfect output
    img = img.resize(target_size, Image.NEAREST)

    # Step 5: Palette quantization (more colors for larger sprites)
    max_colors = 12 if tw <= 8 else 16 if tw <= 16 else 24 if tw <= 32 else 32
    img = _quantize_palette(img, max_colors)

    return img


# ============================================================================
# MANIFEST
# ============================================================================


def load_manifest(manifest_path: Path) -> list[dict]:
    """Load sprite manifest from JSON, filtering out section markers.

    Args:
        manifest_path: Path to sprite_manifest.json.

    Returns:
        List of sprite definition dicts.
    """
    with open(manifest_path) as f:
        data = json.load(f)
    return [s for s in data["sprites"] if "id" in s]


# ============================================================================
# GENERATION
# ============================================================================


def generate_sprite(
    sprite_def: dict,
    output_dir: Path,
    raw_dir: Path,
    backend_override: Optional[str] = None,
    skip_existing: bool = False,
    dry_run: bool = False,
) -> dict:
    """Generate a single sprite (possibly with variants).

    Saves both raw API output and processed game-ready sprite.

    Args:
        sprite_def: Sprite definition from manifest.
        output_dir: Root sprites directory for processed output.
        raw_dir: Directory for raw API output preservation.
        backend_override: Force a specific backend.
        skip_existing: Skip if output file already exists.
        dry_run: Don't actually generate, just report.

    Returns:
        Result dict with status and details.
    """
    sprite_id = sprite_def["id"]
    category = sprite_def["category"]
    target_size = tuple(sprite_def["size"])
    variants = sprite_def.get("variants", 1)
    backend_name = backend_override or sprite_def.get("backend", "gemini")
    prompt = sprite_def["prompt"]

    cat_dir = output_dir / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    raw_cat_dir = raw_dir / category
    raw_cat_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "id": sprite_id,
        "category": category,
        "backend": backend_name,
        "size": target_size,
        "generated": 0,
        "skipped": 0,
        "failed": 0,
        "files": [],
    }

    for v in range(variants):
        if variants > 1:
            filename = f"{sprite_id}_v{v + 1}.png"
            variant_prompt = f"{prompt} Unique variation {v + 1} of {variants}, distinct shape and detail placement."
        else:
            filename = f"{sprite_id}.png"
            variant_prompt = prompt

        output_path = cat_dir / filename
        raw_path = raw_cat_dir / f"{filename.replace('.png', '_raw.png')}"

        if skip_existing and output_path.exists():
            results["skipped"] += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {category}/{filename} ({target_size[0]}x{target_size[1]}, {backend_name})")
            results["generated"] += 1
            results["files"].append(str(output_path))
            continue

        print(f"  Generating {category}/{filename} via {backend_name}...", end=" ", flush=True)

        backend_fn = BACKENDS.get(backend_name)
        if not backend_fn:
            print(f"UNKNOWN BACKEND: {backend_name}")
            results["failed"] += 1
            continue

        # Generate with retry logic
        raw_img = None
        for attempt in range(MAX_RETRIES):
            raw_img = backend_fn(variant_prompt, target_size)
            if raw_img is not None:
                break
            if attempt < MAX_RETRIES - 1:
                wait = (attempt + 1) * 3
                print(f"retrying in {wait}s...", end=" ", flush=True)
                time.sleep(wait)

        if raw_img is None:
            print("FAILED")
            results["failed"] += 1
            continue

        # Save raw output for review
        raw_img.save(str(raw_path), "PNG")

        # Post-process to game-ready sprite
        processed = post_process(raw_img, target_size)
        processed.save(str(output_path), "PNG")

        print(f"OK ({raw_img.size[0]}x{raw_img.size[1]} -> {target_size[0]}x{target_size[1]})")

        results["generated"] += 1
        results["files"].append(str(output_path))

        # Rate limiting
        delay = RATE_LIMITS.get(backend_name, 1.5)
        time.sleep(delay)

    return results


def run_pipeline(
    manifest_path: Path,
    sprites_dir: Path,
    raw_dir: Path,
    category_filter: Optional[str] = None,
    id_filter: Optional[str] = None,
    backend_override: Optional[str] = None,
    skip_existing: bool = False,
    dry_run: bool = False,
    validate_mode: bool = False,
) -> dict:
    """Run the full sprite generation pipeline.

    Args:
        manifest_path: Path to sprite_manifest.json.
        sprites_dir: Root output directory for processed sprites.
        raw_dir: Directory for raw API outputs.
        category_filter: Only generate sprites in this category.
        id_filter: Only generate this specific sprite ID.
        backend_override: Force all sprites to use this backend.
        skip_existing: Skip sprites whose files already exist.
        dry_run: Preview without generating.
        validate_mode: Generate one sprite per category for quality check.

    Returns:
        Summary dict with totals.
    """
    sprites = load_manifest(manifest_path)

    # Apply filters
    if category_filter:
        sprites = [s for s in sprites if s["category"] == category_filter]
    if id_filter:
        sprites = [s for s in sprites if s["id"] == id_filter]
    if validate_mode:
        # Pick one sprite per (category, backend) combination
        seen = set()
        validation_set = []
        for s in sprites:
            key = (s["category"], s.get("backend", "gemini"))
            if key not in seen:
                seen.add(key)
                # Override variants to 1 for validation
                s = dict(s)
                s["variants"] = 1
                validation_set.append(s)
        sprites = validation_set

    total_images = sum(s.get("variants", 1) for s in sprites)

    backend_counts: dict[str, int] = {}
    for s in sprites:
        b = backend_override or s.get("backend", "gemini")
        backend_counts[b] = backend_counts.get(b, 0) + s.get("variants", 1)

    cost_per = {"openai": 0.04, "gemini": 0.02, "nano": 0.044}
    est_cost = sum(count * cost_per.get(b, 0.04) for b, count in backend_counts.items())

    # Estimate time (generation + rate limiting)
    time_per = {"openai": 8, "gemini": 6, "nano": 10}  # seconds per image including delay
    est_time = sum(count * time_per.get(b, 8) for b, count in backend_counts.items())
    est_min = est_time / 60

    print(f"Sprite Generation Pipeline")
    print(f"  Manifest:  {manifest_path}")
    print(f"  Output:    {sprites_dir}")
    print(f"  Raw saves: {raw_dir}")
    print(f"  Sprites:   {len(sprites)} definitions, {total_images} total images")
    backends_str = ", ".join(f"{count} {name}" for name, count in sorted(backend_counts.items()))
    print(f"  Backends:  {backends_str}")
    print(f"  Est. cost: ~${est_cost:.2f}")
    print(f"  Est. time: ~{est_min:.0f} minutes")
    if dry_run:
        print(f"  Mode:      DRY RUN")
    if validate_mode:
        print(f"  Mode:      VALIDATION (one per category+backend)")
    print()

    summary = {
        "total_definitions": len(sprites),
        "total_generated": 0,
        "total_skipped": 0,
        "total_failed": 0,
        "results": [],
    }

    start_time = time.time()

    for i, sprite_def in enumerate(sprites, 1):
        desc = sprite_def.get("description", sprite_def.get("prompt", "")[:50])
        elapsed = time.time() - start_time
        if i > 1 and not dry_run:
            rate = elapsed / (i - 1)
            remaining = rate * (len(sprites) - i + 1)
            eta_str = f" [ETA: {remaining / 60:.0f}m]"
        else:
            eta_str = ""

        print(f"[{i}/{len(sprites)}] {sprite_def['id']}{eta_str}")

        result = generate_sprite(
            sprite_def,
            sprites_dir,
            raw_dir,
            backend_override=backend_override,
            skip_existing=skip_existing,
            dry_run=dry_run,
        )
        summary["results"].append(result)
        summary["total_generated"] += result["generated"]
        summary["total_skipped"] += result["skipped"]
        summary["total_failed"] += result["failed"]

    elapsed_total = time.time() - start_time
    print()
    print(f"=== RESULTS ({elapsed_total / 60:.1f} minutes) ===")
    print(f"  Generated: {summary['total_generated']}")
    print(f"  Skipped:   {summary['total_skipped']}")
    print(f"  Failed:    {summary['total_failed']}")

    if summary["total_failed"] > 0:
        print()
        print("  Failed sprites:")
        for r in summary["results"]:
            if r["failed"] > 0:
                print(f"    - {r['id']} ({r['backend']})")

    return summary


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate game sprites from manifest using AI image generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--category", help="Only generate sprites in this category")
    parser.add_argument("--id", help="Only generate this specific sprite ID")
    parser.add_argument(
        "--backend",
        choices=["openai", "gemini", "nano"],
        help="Force all sprites to use this backend",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip sprites whose output files already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be generated without calling APIs",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Generate one sprite per category+backend for quality verification",
    )
    parser.add_argument(
        "--manifest",
        default=str(MANIFEST_PATH),
        help="Path to sprite manifest JSON",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest not found: {manifest_path}")
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    result = run_pipeline(
        manifest_path=manifest_path,
        sprites_dir=SPRITES_DIR,
        raw_dir=RAW_DIR,
        category_filter=args.category,
        id_filter=args.id,
        backend_override=args.backend,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        validate_mode=args.validate,
    )

    if result["total_failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
