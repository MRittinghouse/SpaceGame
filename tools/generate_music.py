"""Music track generation prompts and helper for SpaceGame.

Defines all music track prompts for use with Suno (suno.com) or compatible
AI music generators. Supports two workflows:

1. Manual: prints prompts to paste into suno.com web UI
2. API: uses a third-party Suno API wrapper (requires SUNO_API_URL and SUNO_API_KEY)

Usage:
    python tools/generate_music.py                  # Print all prompts
    python tools/generate_music.py --track main_theme  # Print one prompt
    python tools/generate_music.py --api             # Generate via API (requires env vars)

Environment variables for API mode:
    SUNO_API_URL  - Base URL of Suno API provider (e.g., https://api.sunoapi.org)
    SUNO_API_KEY  - API key for the provider
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).parent.parent / "spacegame" / "data" / "assets" / "audio" / "music"
MANIFEST_PATH = OUTPUT_DIR.parent / "manifest.json"


@dataclass
class TrackDef:
    """Definition of a music track to generate."""

    id: str
    context: str
    style: str
    prompt: str
    duration_hint: str
    instrumental: bool = True


# All game music tracks
TRACKS: list[TrackDef] = [
    TrackDef(
        id="main_theme",
        context="Main menu screen",
        style="atmospheric synth, space ambient, retro-futuristic",
        prompt=(
            "Atmospheric synthesizer space theme, hopeful and mysterious. "
            "Retro-futuristic electronic with gentle arpeggios and warm pads. "
            "Evokes the vastness of space exploration and new beginnings. "
            "Slow tempo, dreamy, cinematic. Loopable."
        ),
        duration_hint="2:00",
    ),
    TrackDef(
        id="galaxy_exploration",
        context="Galaxy map / space travel",
        style="ambient electronic, contemplative, vast",
        prompt=(
            "Ambient electronic exploration theme. Vast and contemplative. "
            "Gentle pulsing bass, ethereal synth pads, subtle twinkling high notes. "
            "Evokes drifting through star systems, charting unknown routes. "
            "Medium-slow tempo, peaceful but with underlying wonder. Loopable."
        ),
        duration_hint="2:30",
    ),
    TrackDef(
        id="station_hub",
        context="Space station / trading / docked",
        style="chill lo-fi, commercial bustle, warm synth",
        prompt=(
            "Chill lo-fi space station ambient. Warm synth pads with gentle beat. "
            "Muffled bass, soft percussion, occasional metallic chimes. "
            "Feels like a busy commercial hub — traders, mechanics, conversation. "
            "Relaxed but purposeful. Medium tempo. Loopable."
        ),
        duration_hint="2:00",
    ),
    TrackDef(
        id="combat_intense",
        context="Space combat encounters",
        style="driving electronic, tense, urgent",
        prompt=(
            "Intense space combat music. Driving electronic with urgent pulsing bass. "
            "Aggressive synth leads, rapid hi-hats, tension-building arpeggios. "
            "Fast tempo, adrenaline-pumping, dangerous. "
            "Think retro sci-fi action. Loopable."
        ),
        duration_hint="1:30",
    ),
    TrackDef(
        id="mining_rhythm",
        context="Mining mini-game",
        style="rhythmic industrial, percussive, energetic",
        prompt=(
            "Rhythmic industrial mining theme. Heavy percussive beats, metallic clangs. "
            "Steady driving rhythm like machinery in an asteroid mine. "
            "Electronic with industrial texture. Energetic and focused. "
            "Medium-fast tempo. Loopable."
        ),
        duration_hint="1:30",
    ),
    TrackDef(
        id="ground_stealth",
        context="Ground exploration missions",
        style="tense ambient, sneaky, suspenseful",
        prompt=(
            "Tense stealth infiltration music. Minimal and suspenseful. "
            "Low droning synth, quiet heartbeat-like pulse, occasional sharp accents. "
            "Sneaky and dangerous atmosphere. Sparse arrangement. "
            "Slow tempo, building unease. Loopable."
        ),
        duration_hint="2:00",
    ),
    TrackDef(
        id="frontier_danger",
        context="Dangerous/lawless star systems",
        style="dark ambient, ominous, gritty",
        prompt=(
            "Dark frontier ambient. Ominous and gritty. "
            "Deep droning bass, distant metallic echoes, low rumbling. "
            "Feels like the lawless edge of space — danger, desperation, fortune-seeking. "
            "Very slow tempo, threatening atmosphere. Loopable."
        ),
        duration_hint="2:00",
    ),
    TrackDef(
        id="dialogue_intimate",
        context="Story dialogue / character interactions",
        style="soft piano/synth, emotional, reflective",
        prompt=(
            "Soft emotional dialogue theme. Gentle piano with warm synth pad backing. "
            "Intimate and personal, reflective mood. Subtle strings. "
            "Evokes quiet conversation between characters with shared history. "
            "Slow tempo, understated. Loopable."
        ),
        duration_hint="2:00",
    ),
    TrackDef(
        id="victory_fanfare",
        context="Victory / mission complete",
        style="triumphant brass-synth, uplifting, short",
        prompt=(
            "Short triumphant victory fanfare. Bright brass-synth with ascending melody. "
            "Uplifting and celebratory, like winning a hard-fought battle. "
            "Quick build to a satisfying peak. Not loopable — one-shot stinger."
        ),
        duration_hint="0:30",
    ),
    TrackDef(
        id="defeat_somber",
        context="Defeat / mission failure",
        style="melancholic, descending, fading",
        prompt=(
            "Short somber defeat theme. Melancholic descending synth. "
            "Fading out slowly, regretful and heavy. Minor key. "
            "Brief but impactful — conveys loss without dragging. Not loopable — one-shot stinger."
        ),
        duration_hint="0:30",
    ),
]


def print_prompts(track_id: Optional[str] = None) -> None:
    """Print prompts for manual use in suno.com."""
    targets = TRACKS
    if track_id:
        targets = [t for t in TRACKS if t.id == track_id]
        if not targets:
            print(f"Unknown track: {track_id}")
            print(f"Available: {', '.join(t.id for t in TRACKS)}")
            return

    print("=" * 70)
    print("SPACEGAME MUSIC PROMPTS")
    print("Paste these into suno.com to generate tracks.")
    print(f"Save output as OGG to: {OUTPUT_DIR}")
    print("=" * 70)

    for t in targets:
        print(f"\n--- {t.id} ({t.context}) ---")
        print(f"Style: {t.style}")
        print(f"Duration: {t.duration_hint}")
        print(f"Instrumental: {'Yes' if t.instrumental else 'No'}")
        print(f"\nPrompt:\n{t.prompt}")
        print(f"\nSave as: {OUTPUT_DIR / (t.id + '.ogg')}")

    print(f"\n{'=' * 70}")
    print(f"Total tracks: {len(targets)}")
    print("\nAfter generating, run: python tools/generate_music.py --update-manifest")


def update_manifest() -> None:
    """Add music entries to the audio manifest for any .ogg files in music dir."""
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created {OUTPUT_DIR} — add .ogg files here.")
        return

    # Load existing manifest
    manifest: dict = {"sfx": {}, "music": {}, "ambient": {}}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)

    # Scan for music files (.ogg, .mp3)
    found = 0
    for ext in ("*.ogg", "*.mp3"):
        for music_file in sorted(OUTPUT_DIR.glob(ext)):
            track_id = music_file.stem
            rel_path = f"music/{music_file.name}"
            manifest.setdefault("music", {})[track_id] = {"file": rel_path}
            found += 1
            print(f"  {track_id} -> {rel_path}")

    if found == 0:
        print("No .ogg files found in music directory.")
        print(f"Add music files to: {OUTPUT_DIR}")
        return

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"\nManifest updated with {found} music tracks.")


def generate_via_api() -> None:
    """Generate tracks via a third-party Suno API provider."""
    api_url = os.environ.get("SUNO_API_URL")
    api_key = os.environ.get("SUNO_API_KEY")

    if not api_url or not api_key:
        print("API mode requires environment variables:")
        print("  SUNO_API_URL - Base URL of Suno API provider")
        print("  SUNO_API_KEY - API key")
        print()
        print("Example third-party providers:")
        print("  - sunoapi.org")
        print("  - apiframe.ai")
        print("  - aimlapi.com")
        print()
        print("For now, use manual mode: python tools/generate_music.py")
        sys.exit(1)

    try:
        import requests
    except ImportError:
        print("API mode requires 'requests' package: pip install requests")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for track in TRACKS:
        print(f"\nGenerating: {track.id} ({track.context})...")
        out_path = OUTPUT_DIR / f"{track.id}.ogg"

        if out_path.exists():
            print(f"  SKIP (already exists)")
            continue

        payload = {
            "prompt": track.prompt,
            "style": track.style,
            "title": f"SpaceGame - {track.id}",
            "instrumental": track.instrumental,
        }

        try:
            resp = requests.post(f"{api_url}/v1/generate", json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            result = resp.json()

            # Handle various API response formats
            audio_url = result.get("audio_url") or result.get("url") or result.get("data", {}).get("audio_url")
            if not audio_url:
                print(f"  ERROR: No audio URL in response: {json.dumps(result)[:200]}")
                continue

            # Download the audio
            audio_resp = requests.get(audio_url, timeout=60)
            audio_resp.raise_for_status()

            out_path.write_bytes(audio_resp.content)
            print(f"  OK -> {out_path}")

        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    print("\nDone! Run: python tools/generate_music.py --update-manifest")


def main() -> None:
    parser = argparse.ArgumentParser(description="SpaceGame music generation helper")
    parser.add_argument("--track", type=str, help="Print prompt for a specific track ID")
    parser.add_argument("--api", action="store_true", help="Generate via third-party Suno API")
    parser.add_argument("--update-manifest", action="store_true", help="Update manifest with existing .ogg files")
    parser.add_argument("--list", action="store_true", help="List all track IDs")
    args = parser.parse_args()

    if args.list:
        for t in TRACKS:
            print(f"  {t.id:25s} {t.duration_hint:>5s}  {t.context}")
        print(f"\nTotal: {len(TRACKS)} tracks")
    elif args.update_manifest:
        update_manifest()
    elif args.api:
        generate_via_api()
    else:
        print_prompts(args.track)


if __name__ == "__main__":
    main()
