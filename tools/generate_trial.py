"""Trial run: generate one commodity icon through the full pipeline.

Generates a single 'iron_ore' icon (16x16 pixel art) to validate:
  1. DALL-E API call + image download
  2. Resize to native resolution
  3. Palette quantization
  4. Alpha cleanup
  5. Outline enforcement
  6. Save to correct asset directory

Usage:
    python tools/generate_trial.py
"""

import json
import sys
import pathlib
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# Add project root to path for pipeline imports
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.pixel_pipeline import (
    remove_background,
    resize_nearest,
    quantize_to_palette,
    clean_alpha,
    enforce_outline,
)


def load_master_palette() -> list[tuple[int, int, int]]:
    """Load the master palette colors from JSON."""
    palette_path = (
        PROJECT_ROOT
        / "spacegame"
        / "data"
        / "assets"
        / "palettes"
        / "master_palette.json"
    )
    with open(palette_path) as f:
        data = json.load(f)
    return [tuple(v) for v in data["colors"].values()]


def generate_image(client: OpenAI, prompt: str) -> Image.Image:
    """Call DALL-E 3 and return the result as a PIL Image."""
    print(f"  Calling DALL-E 3...")
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    image_url = response.data[0].url
    revised_prompt = response.data[0].revised_prompt
    print(f"  Revised prompt: {revised_prompt[:100]}...")

    # Download the image
    import httpx

    print(f"  Downloading image...")
    resp = httpx.get(image_url)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGBA")


def process_sprite(
    raw: Image.Image,
    target_size: tuple[int, int],
    palette: list[tuple[int, int, int]],
    outline_color: tuple[int, int, int] = (10, 10, 15),
) -> Image.Image:
    """Run the full pixel pipeline on a raw image."""
    print(f"  Raw image: {raw.size}")

    print(f"  Removing background...")
    img = remove_background(raw)

    print(f"  Resizing to {target_size}...")
    img = resize_nearest(img, target_size)

    print(f"  Cleaning alpha (binary)...")
    img = clean_alpha(img)

    print(f"  Quantizing to {len(palette)}-color palette...")
    img = quantize_to_palette(img, palette)

    print(f"  Enforcing outline...")
    img = enforce_outline(img, outline_color)

    return img


def main() -> None:
    load_dotenv()

    # Verify API key
    client = OpenAI()
    print("OpenAI client initialized.")

    # Load palette
    palette = load_master_palette()
    print(f"Master palette loaded: {len(palette)} colors.")

    # Define the trial sprite
    sprite_id = "iron_ore"
    target_size = (16, 16)
    output_dir = (
        PROJECT_ROOT / "spacegame" / "data" / "assets" / "sprites" / "commodities"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt = (
        "A single small iron ore rock icon on a pure bright green background (#00FF00). "
        "Flat top-down 2D view, NOT isometric, NOT 3D. "
        "Dark gray rough rock with rust-brown patches and metallic silver flecks. "
        "Style: 16-bit SNES-era pixel art, limited color palette, clean 1px dark outlines. "
        "Single small centered object, large green margin around it. "
        "No text, no frame, no border, no shadow, no ground, no other objects."
    )

    # Step 1: Generate
    print(f"\n[1/2] Generating '{sprite_id}'...")
    raw_image = generate_image(client, prompt)

    # Save raw for comparison
    raw_path = output_dir / f"{sprite_id}_raw.png"
    raw_image.save(str(raw_path))
    print(f"  Raw saved: {raw_path}")

    # Step 2: Process
    print(f"\n[2/2] Processing through pixel pipeline...")
    final = process_sprite(raw_image, target_size, palette)

    # Save final
    final_path = output_dir / f"{sprite_id}.png"
    final.save(str(final_path))
    print(f"  Final saved: {final_path}")

    # Also save a scaled-up preview (4x) for easy visual inspection
    preview = resize_nearest(final, (target_size[0] * 8, target_size[1] * 8))
    preview_path = output_dir / f"{sprite_id}_preview.png"
    preview.save(str(preview_path))
    print(f"  Preview (8x): {preview_path}")

    # Summary
    print(f"\n--- Trial Complete ---")
    print(f"  Raw:     {raw_path} ({raw_image.size})")
    print(f"  Final:   {final_path} ({final.size})")
    print(f"  Preview: {preview_path} ({preview.size})")
    print(f"\nOpen the preview to visually inspect the result.")
    print(f"If it looks good, we're ready to scale up.")


if __name__ == "__main__":
    main()
