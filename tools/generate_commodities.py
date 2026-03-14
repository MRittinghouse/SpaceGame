"""Batch generate all commodity icons through the full sprite pipeline.

Generates 16x16 pixel art icons for every commodity in the game.
Uses DALL-E 3 with green-screen prompting for clean background removal,
then processes through the pixel pipeline (resize, quantize, outline).

Usage:
    python tools/generate_commodities.py              # Generate all
    python tools/generate_commodities.py iron_ore      # Generate one
    python tools/generate_commodities.py --list        # List all commodity IDs
    python tools/generate_commodities.py --skip-existing  # Skip already generated
"""

import argparse
import json
import sys
import time
import pathlib
from io import BytesIO

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.pixel_pipeline import (
    remove_background,
    resize_nearest,
    quantize_to_palette,
    clean_alpha,
    enforce_outline,
)

# ---------------------------------------------------------------------------
# Style constants — shared across ALL commodity prompts for consistency
# ---------------------------------------------------------------------------

_STYLE_SUFFIX = (
    "Style: 16-bit SNES-era pixel art, limited color palette, "
    "clean 1px dark outlines around the object. "
    "Single small centered object, large bright green margin around it. "
    "No text, no label, no frame, no border, no shadow, no ground plane, "
    "no other objects, no UI elements."
)

_BG_PREFIX = "on a pure bright green background (#00FF00). "
_VIEW = "Flat top-down 2D view, NOT isometric, NOT 3D. "

# ---------------------------------------------------------------------------
# Per-commodity visual descriptions
# ---------------------------------------------------------------------------

COMMODITY_PROMPTS: dict[str, str] = {
    # --- Basic trade goods ---
    "food": (
        "A sealed ration container icon " + _BG_PREFIX + _VIEW +
        "Compact silver-gray box with a small blue nutrition label strip. "
        "Clean, utilitarian, military-style food packaging. " + _STYLE_SUFFIX
    ),
    "textiles": (
        "A rolled bolt of fabric icon " + _BG_PREFIX + _VIEW +
        "Tightly rolled colorful cloth bundle with visible weave texture, "
        "tied with a thin cord. Warm earthy tones — tan, rust, cream. " + _STYLE_SUFFIX
    ),
    "common_metals": (
        "A stack of metal ingots icon " + _BG_PREFIX + _VIEW +
        "Three small stacked rectangular steel-gray ingots with subtle "
        "metallic sheen. Industrial, clean, simple. " + _STYLE_SUFFIX
    ),
    "fuel": (
        "A glowing fuel cell canister icon " + _BG_PREFIX + _VIEW +
        "Small cylindrical canister with bright orange-yellow energy glow "
        "visible through a viewport slit. Dark metal housing. " + _STYLE_SUFFIX
    ),
    "machinery": (
        "A compact gear mechanism icon " + _BG_PREFIX + _VIEW +
        "Interlocking steel gears and mechanical parts, small and compact. "
        "Gunmetal gray with brass accent pieces. " + _STYLE_SUFFIX
    ),
    "electronics": (
        "A circuit board module icon " + _BG_PREFIX + _VIEW +
        "Small green PCB with visible copper traces, tiny chip components, "
        "and solder points. Tech-dense but readable at small size. " + _STYLE_SUFFIX
    ),
    "rare_metals": (
        "A gleaming rare metal ingot icon " + _BG_PREFIX + _VIEW +
        "Single polished ingot with an iridescent blue-silver sheen. "
        "Visibly more precious than common metal — subtle glow effect. " + _STYLE_SUFFIX
    ),
    "manufactured_goods": (
        "A sealed shipping crate icon " + _BG_PREFIX + _VIEW +
        "Small cargo crate with reinforced corners, neutral gray-brown, "
        "with a generic trade stamp marking on top. Standard freight. " + _STYLE_SUFFIX
    ),
    "precious_metals": (
        "A gold bar icon " + _BG_PREFIX + _VIEW +
        "Small trapezoidal gold ingot with rich warm yellow-gold color "
        "and subtle highlight. Valuable, dense, heavy-looking. " + _STYLE_SUFFIX
    ),
    "art": (
        "A small ornate artifact icon " + _BG_PREFIX + _VIEW +
        "Alien antiquity — a small carved statuette or decorative object "
        "with intricate purple and gold details. Mysterious and valuable. " + _STYLE_SUFFIX
    ),
    "exotic_goods": (
        "A sealed luxury container icon " + _BG_PREFIX + _VIEW +
        "Ornate small chest or case with deep blue finish and gold trim. "
        "Exotic and expensive-looking. Mysterious contents implied. " + _STYLE_SUFFIX
    ),
    "medical": (
        "A medical supply kit icon " + _BG_PREFIX + _VIEW +
        "Compact white case with a bright red cross/medical symbol. "
        "Clean, sterile appearance. Small vials visible inside. " + _STYLE_SUFFIX
    ),
    # --- Raw ores (from mining) ---
    "raw_ore": (
        "A rough unprocessed rock icon " + _BG_PREFIX + _VIEW +
        "Jagged dark brown-gray rock chunk, unrefined, dusty. "
        "Cheapest ore tier — dull and unremarkable. " + _STYLE_SUFFIX
    ),
    "iron_ore": (
        "A single iron ore rock icon " + _BG_PREFIX + _VIEW +
        "Dark gray rough rock with rust-brown patches and metallic silver flecks. "
        "Mid-tier ore — heavier and denser than raw ore. " + _STYLE_SUFFIX
    ),
    "crystal_ore": (
        "A crystalline ore chunk icon " + _BG_PREFIX + _VIEW +
        "Rock with bright teal-cyan crystal formations protruding from "
        "dark stone matrix. Luminous, valuable, eye-catching. " + _STYLE_SUFFIX
    ),
    "rare_ore": (
        "A rare glowing ore chunk icon " + _BG_PREFIX + _VIEW +
        "Dark rock veined with bright purple-violet luminous mineral. "
        "Highest tier ore — visibly rare and energy-rich. Subtle glow. " + _STYLE_SUFFIX
    ),
    # --- Salvage materials ---
    "scrap_metal": (
        "A pile of scrap metal icon " + _BG_PREFIX + _VIEW +
        "Small heap of bent, twisted metal scraps — hull fragments, "
        "bolts, torn plating. Rusty gray-brown, clearly junk. " + _STYLE_SUFFIX
    ),
    "salvaged_electronics": (
        "A salvaged circuit board icon " + _BG_PREFIX + _VIEW +
        "Damaged PCB with exposed wiring, some components missing, "
        "scorch marks. Salvageable but clearly second-hand. " + _STYLE_SUFFIX
    ),
    "rare_parts": (
        "A high-tech component icon " + _BG_PREFIX + _VIEW +
        "Pristine small mechanical part with precision engineering — "
        "chrome and blue accents, complex micro-structure. Valuable salvage. " + _STYLE_SUFFIX
    ),
    # --- Refined materials ---
    "alloy_composite": (
        "A refined alloy plate icon " + _BG_PREFIX + _VIEW +
        "Smooth polished metal plate, layered silver and dark gray, "
        "with visible laminated structure at edge. Industrial, processed. " + _STYLE_SUFFIX
    ),
    "purified_crystal": (
        "A cut crystal gem icon " + _BG_PREFIX + _VIEW +
        "Faceted translucent teal-white crystal, geometrically perfect. "
        "Refined from raw crystal ore — clean, brilliant, valuable. " + _STYLE_SUFFIX
    ),
    # --- Weapons & restricted ---
    "weapons_components": (
        "A weapons part icon " + _BG_PREFIX + _VIEW +
        "Small weapon assembly component — barrel segment or targeting "
        "module. Dark gunmetal with red hazard accent stripe. Dangerous. " + _STYLE_SUFFIX
    ),
    "restricted_tech": (
        "A classified technology device icon " + _BG_PREFIX + _VIEW +
        "Small sealed black box with a glowing red indicator light and "
        "a biometric lock pad. Secretive, high-tech, forbidden. " + _STYLE_SUFFIX
    ),
    # --- Contraband ---
    "stolen_data": (
        "An encrypted data chip icon " + _BG_PREFIX + _VIEW +
        "Tiny dark memory chip with flickering red-orange data indicator. "
        "Sleek, ominous, clearly illicit. Micro-sized. " + _STYLE_SUFFIX
    ),
    "combat_stims": (
        "A combat stimulant injector icon " + _BG_PREFIX + _VIEW +
        "Small auto-injector syringe with bright yellow-green glowing "
        "liquid visible through a window. Military, aggressive coloring. " + _STYLE_SUFFIX
    ),
    "contraband_medicine": (
        "A diverted medicine vial icon " + _BG_PREFIX + _VIEW +
        "Medical vial with clear blue liquid, but the label is scratched "
        "off. Looks legitimate but clearly tampered with. Illicit. " + _STYLE_SUFFIX
    ),
    "data_chip": (
        "A secure data chip icon " + _BG_PREFIX + _VIEW +
        "Small chip/card with a subtle blue circuit pattern glow. "
        "Encrypted, important, story-critical feel. Dark with blue accents. " + _STYLE_SUFFIX
    ),
}

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

NATIVE_SIZE = (16, 16)
PREVIEW_SCALE = 8
OUTLINE_COLOR = (10, 10, 15)


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


def generate_and_process(
    client: OpenAI,
    commodity_id: str,
    prompt: str,
    palette: list[tuple[int, int, int]],
    output_dir: pathlib.Path,
) -> bool:
    """Generate one commodity icon end-to-end.

    Returns True on success, False on failure.
    """
    import httpx

    try:
        # Generate
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            response_format="url",
        )
        image_url = response.data[0].url

        # Download
        resp = httpx.get(image_url, timeout=30.0)
        resp.raise_for_status()
        raw = Image.open(BytesIO(resp.content)).convert("RGBA")

        # Save raw for reference
        raw.save(str(output_dir / f"{commodity_id}_raw.png"))

        # Pipeline: bg removal → resize → clean alpha → quantize → outline
        img = remove_background(raw)
        img = resize_nearest(img, NATIVE_SIZE)
        img = clean_alpha(img)
        img = quantize_to_palette(img, palette)
        img = enforce_outline(img, OUTLINE_COLOR)

        # Save final
        img.save(str(output_dir / f"{commodity_id}.png"))

        # Save preview
        preview = resize_nearest(img, (NATIVE_SIZE[0] * PREVIEW_SCALE, NATIVE_SIZE[1] * PREVIEW_SCALE))
        preview.save(str(output_dir / f"{commodity_id}_preview.png"))

        return True

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate commodity icon sprites.")
    parser.add_argument("commodities", nargs="*", help="Commodity IDs to generate (default: all)")
    parser.add_argument("--list", action="store_true", help="List all commodity IDs and exit")
    parser.add_argument("--skip-existing", action="store_true", help="Skip commodities that already have a .png")
    args = parser.parse_args()

    if args.list:
        for cid in sorted(COMMODITY_PROMPTS.keys()):
            print(f"  {cid}")
        print(f"\n{len(COMMODITY_PROMPTS)} commodities total.")
        return

    load_dotenv()
    client = OpenAI()

    palette = load_master_palette()
    output_dir = PROJECT_ROOT / "spacegame" / "data" / "assets" / "sprites" / "commodities"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which commodities to generate
    if args.commodities:
        targets = args.commodities
        unknown = [t for t in targets if t not in COMMODITY_PROMPTS]
        if unknown:
            print(f"Unknown commodity IDs: {unknown}")
            print(f"Use --list to see available IDs.")
            sys.exit(1)
    else:
        targets = list(COMMODITY_PROMPTS.keys())

    if args.skip_existing:
        targets = [t for t in targets if not (output_dir / f"{t}.png").exists()]
        if not targets:
            print("All commodities already generated. Nothing to do.")
            return

    print(f"Generating {len(targets)} commodity icons...")
    print(f"Output: {output_dir}")
    print(f"Palette: {len(palette)} colors")
    print(f"Estimated cost: ~${len(targets) * 0.04:.2f}")
    print()

    succeeded = 0
    failed = []

    for i, cid in enumerate(targets, 1):
        prompt = COMMODITY_PROMPTS[cid]
        print(f"[{i}/{len(targets)}] {cid}...")

        ok = generate_and_process(client, cid, prompt, palette, output_dir)
        if ok:
            succeeded += 1
            print(f"    OK")
        else:
            failed.append(cid)
            print(f"    FAILED")

        # Brief pause between API calls to be respectful
        if i < len(targets):
            time.sleep(1)

    # Summary
    print(f"\n{'=' * 40}")
    print(f"Done: {succeeded}/{len(targets)} succeeded")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        print(f"Re-run with: python tools/generate_commodities.py {' '.join(failed)}")

    # Count final assets
    final_count = len(list(output_dir.glob("*.png"))) - len(list(output_dir.glob("*_raw.png"))) - len(list(output_dir.glob("*_preview.png")))
    print(f"Asset directory: {final_count} final icons in {output_dir}")


if __name__ == "__main__":
    main()
